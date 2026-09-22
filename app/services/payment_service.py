import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.course import Course
from app.models.payment_link import PaymentLink
from app.models.payment_event import PaymentEvent
from app.models.reminder_log import ReminderLog
from app.models.enums import (
    PaymentStatus,
    PaymentSource,
    NotificationChannelType,
    ReminderType,
    ReminderDeliveryStatus,
)
from app.schemas.payment_link import (
    PaymentLinkCreateInternal,
    PaymentLinkRecordExternal,
    PaymentLinkFilter,
)
from app.schemas.payment_event import PaymentStatusUpdate
from app.channels.factory import notification_service

logger = logging.getLogger("guvi.service.payment")


class PaymentService:
    async def get_or_create_course(
        self,
        db: AsyncSession,
        course_id: str,
        title: str = "GUVI Premium Tech Program",
        full_price: float = 45000.0,
        down_payment_amount: float = 5000.0,
    ) -> Course:
        course = await db.get(Course, course_id)
        if not course:
            course = Course(
                id=course_id,
                title=title,
                full_price=full_price,
                down_payment_amount=down_payment_amount,
                currency="INR",
            )
            db.add(course)
            await db.flush()
        return course

    async def create_internal_payment_link(
        self, db: AsyncSession, payload: PaymentLinkCreateInternal
    ) -> PaymentLink:
        # Check course
        course = await db.get(Course, payload.course_id)
        if not course:
            raise ValueError(f"Course with ID '{payload.course_id}' not found.")

        amount_due = (
            payload.custom_amount_due
            if payload.custom_amount_due is not None
            else course.full_price
        )
        down_payment = (
            payload.custom_down_payment
            if payload.custom_down_payment is not None
            else course.down_payment_amount
        )

        link_id = str(uuid.uuid4())
        payment_link_url = f"{settings.BASE_PAYMENT_GATEWAY_URL}?link_id={link_id}"

        # If due_date is naive, make it aware (UTC)
        due_date = payload.due_date
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)

        expires_at = payload.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        payment_link = PaymentLink(
            id=link_id,
            user_name=payload.user_name,
            user_email=payload.user_email,
            user_phone=payload.user_phone,
            course_id=payload.course_id,
            amount_due=amount_due,
            down_payment_amount=down_payment,
            currency=course.currency,
            payment_link_url=payment_link_url,
            source=PaymentSource.INTERNAL,
            status=PaymentStatus.PENDING,
            due_date=due_date,
            expires_at=expires_at,
            notes=payload.notes,
        )
        db.add(payment_link)

        # Log creation event
        event = PaymentEvent(
            payment_link_id=payment_link.id,
            event_type="PAYMENT_LINK_GENERATED",
            description=f"Generated internal payment link for {payload.user_name} ({payload.user_email})",
            payload_json=json.dumps({"amount": amount_due, "down_payment": down_payment}),
        )
        db.add(event)
        await db.flush()

        # Send initial payment link email to user
        context = {
            "user_name": payload.user_name,
            "course_title": course.title,
            "amount_due": amount_due,
            "down_payment_amount": down_payment,
            "currency": course.currency,
            "payment_link_url": payment_link_url,
            "due_date_str": due_date.strftime("%d %B %Y, %I:%M %p UTC"),
        }
        subject = f"Your GUVI Course Payment Link - {course.title}"

        try:
            sent = await notification_service.send(
                channel_type=NotificationChannelType.EMAIL,
                recipient=payload.user_email,
                subject=subject,
                template_name="payment_link_initial.html",
                context=context,
            )
            reminder_log = ReminderLog(
                payment_link_id=payment_link.id,
                reminder_type=ReminderType.PENDING_REMINDER,
                channel=NotificationChannelType.EMAIL,
                recipient=payload.user_email,
                subject=subject,
                status=ReminderDeliveryStatus.SENT if sent else ReminderDeliveryStatus.FAILED,
            )
            db.add(reminder_log)
        except Exception as e:
            logger.error(f"Failed to dispatch initial email to {payload.user_email}: {e}")
            reminder_log = ReminderLog(
                payment_link_id=payment_link.id,
                reminder_type=ReminderType.PENDING_REMINDER,
                channel=NotificationChannelType.EMAIL,
                recipient=payload.user_email,
                subject=subject,
                status=ReminderDeliveryStatus.FAILED,
                error_message=str(e),
            )
            db.add(reminder_log)

        await db.commit()
        return await self.get_payment_link_by_id(db, payment_link.id)

    async def record_external_payment_link(
        self, db: AsyncSession, payload: PaymentLinkRecordExternal
    ) -> PaymentLink:
        # Check course exists, or create placeholder if external portal specifies a new ID
        course = await db.get(Course, payload.course_id)
        if not course:
            course = await self.get_or_create_course(
                db=db,
                course_id=payload.course_id,
                title=f"Course {payload.course_id}",
                full_price=payload.amount_due,
                down_payment_amount=payload.down_payment_amount,
            )

        due_date = payload.due_date
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)

        expires_at = payload.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        payment_link = PaymentLink(
            id=str(uuid.uuid4()),
            user_name=payload.user_name,
            user_email=payload.user_email,
            user_phone=payload.user_phone,
            course_id=payload.course_id,
            amount_due=payload.amount_due,
            down_payment_amount=payload.down_payment_amount,
            currency=payload.currency,
            payment_link_url=payload.payment_link_url,
            source=PaymentSource.EXTERNAL,
            external_reference_id=payload.external_reference_id,
            status=PaymentStatus.PENDING,
            due_date=due_date,
            expires_at=expires_at,
            notes=payload.notes,
        )
        db.add(payment_link)

        # Record ingestion event
        event = PaymentEvent(
            payment_link_id=payment_link.id,
            event_type="EXTERNAL_PAYMENT_LINK_RECORDED",
            description=f"External payment link recorded for {payload.user_name}. External Ref: {payload.external_reference_id}",
            payload_json=json.dumps(
                {
                    "external_reference_id": payload.external_reference_id,
                    "url": payload.payment_link_url,
                    "amount": payload.amount_due,
                }
            ),
        )
        db.add(event)
        await db.commit()
        return await self.get_payment_link_by_id(db, payment_link.id)

    async def update_payment_status(
        self, db: AsyncSession, payload: PaymentStatusUpdate
    ) -> PaymentLink:
        payment_link = await db.get(PaymentLink, payload.payment_link_id)
        if not payment_link:
            raise ValueError(f"Payment link with ID '{payload.payment_link_id}' not found.")

        old_status = payment_link.status
        now = datetime.now(timezone.utc)
        payment_link.status = payload.new_status

        if payload.new_status == PaymentStatus.DOWN_PAYMENT_PAID:
            payment_link.dp_paid_at = now
            event_desc = f"Down payment received: {payload.amount_paid or payment_link.down_payment_amount}"
        elif payload.new_status == PaymentStatus.CONVERTED:
            payment_link.converted_at = now
            event_desc = f"Full payment completed & converted. Tx: {payload.transaction_reference or 'N/A'}"
        elif payload.new_status == PaymentStatus.CANCELLED:
            event_desc = f"Payment link cancelled. Reason: {payload.notes or 'None'}"
        elif payload.new_status == PaymentStatus.EXPIRED:
            event_desc = "Payment link marked as expired."
        else:
            event_desc = f"Payment status changed from {old_status} to {payload.new_status}"

        event = PaymentEvent(
            payment_link_id=payment_link.id,
            event_type=f"STATUS_CHANGED_TO_{payload.new_status.value}",
            description=event_desc,
            payload_json=json.dumps(
                {
                    "old_status": old_status.value,
                    "new_status": payload.new_status.value,
                    "amount_paid": payload.amount_paid,
                    "transaction_ref": payload.transaction_reference,
                    "notes": payload.notes,
                }
            ),
        )
        db.add(event)
        await db.commit()
        return await self.get_payment_link_by_id(db, payment_link.id)

    async def get_payment_links(
        self, db: AsyncSession, filters: PaymentLinkFilter, limit: int = 50, offset: int = 0
    ) -> List[PaymentLink]:
        query = select(PaymentLink).options(selectinload(PaymentLink.course)).order_by(PaymentLink.created_at.desc())

        if filters.status:
            query = query.where(PaymentLink.status == filters.status)
        if filters.course_id:
            query = query.where(PaymentLink.course_id == filters.course_id)
        if filters.user_email:
            query = query.where(PaymentLink.user_email == filters.user_email)
        if filters.source:
            query = query.where(PaymentLink.source == filters.source)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_payment_link_by_id(
        self, db: AsyncSession, payment_link_id: str
    ) -> Optional[PaymentLink]:
        query = (
            select(PaymentLink)
            .options(
                selectinload(PaymentLink.course),
                selectinload(PaymentLink.events),
                selectinload(PaymentLink.reminder_logs),
            )
            .where(PaymentLink.id == payment_link_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


payment_service = PaymentService()
