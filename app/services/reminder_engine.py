import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.payment_link import PaymentLink
from app.models.reminder_log import ReminderLog
from app.models.payment_event import PaymentEvent
from app.models.enums import (
    PaymentStatus,
    ReminderType,
    NotificationChannelType,
    ReminderDeliveryStatus,
)
from app.channels.factory import notification_service
from app.schemas.reminder import ReminderTriggerResponse

logger = logging.getLogger("guvi.service.reminder_engine")


class ReminderEngine:
    async def evaluate_and_send_all_reminders(
        self, db: AsyncSession, force: bool = False
    ) -> ReminderTriggerResponse:
        """
        Scans all active payment links and triggers appropriate reminders:
        1. Pending follow-up reminders to users
        2. Overdue payment alerts to users
        3. DP paid not converted escalation alerts to internal courses team
        """
        now = datetime.now(timezone.utc)
        details: List[Dict[str, str]] = []
        pending_sent = 0
        overdue_sent = 0
        dp_team_sent = 0
        failed_count = 0

        # Query links that are PENDING, DOWN_PAYMENT_PAID, or OVERDUE
        query = (
            select(PaymentLink)
            .options(selectinload(PaymentLink.course))
            .where(
                PaymentLink.status.in_(
                    [PaymentStatus.PENDING, PaymentStatus.DOWN_PAYMENT_PAID, PaymentStatus.OVERDUE]
                )
            )
        )
        result = await db.execute(query)
        links = list(result.scalars().all())

        for link in links:
            # Ensure due_date has tzinfo for safe comparison
            due_date = link.due_date
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)

            # ----------------------------------------------------
            # CASE 3: Down Payment Paid but Not Converted (Team alert)
            # ----------------------------------------------------
            if link.status == PaymentStatus.DOWN_PAYMENT_PAID:
                dp_time = link.dp_paid_at or link.created_at
                if dp_time.tzinfo is None:
                    dp_time = dp_time.replace(tzinfo=timezone.utc)

                elapsed_since_dp = (now - dp_time).total_seconds()
                threshold_seconds = settings.DP_CONVERSION_WINDOW_HOURS * 3600

                if (elapsed_since_dp >= threshold_seconds or force) and not link.dp_team_alerted:
                    success = await self._send_dp_not_converted_team_alert(db, link, now, dp_time)
                    if success:
                        dp_team_sent += 1
                        details.append(
                            {
                                "link_id": link.id,
                                "type": ReminderType.DP_NOT_CONVERTED_TEAM_ALERT.value,
                                "status": "SENT",
                                "target": settings.COURSES_TEAM_EMAIL,
                            }
                        )
                    else:
                        failed_count += 1
                continue

            # ----------------------------------------------------
            # CASE 2: Overdue Payment Alert (User alert)
            # ----------------------------------------------------
            is_past_due = now > due_date
            if is_past_due:
                # Mark as OVERDUE if still PENDING
                if link.status == PaymentStatus.PENDING:
                    link.status = PaymentStatus.OVERDUE

                # Check if overdue alert was already sent recently
                cooldown_ok = self._is_cooldown_satisfied(link.last_reminder_sent_at, now)
                if (cooldown_ok or force) and link.reminder_count < (settings.MAX_PENDING_REMINDERS + 1):
                    success = await self._send_overdue_alert(db, link, now, due_date)
                    if success:
                        overdue_sent += 1
                        details.append(
                            {
                                "link_id": link.id,
                                "type": ReminderType.OVERDUE_ALERT.value,
                                "status": "SENT",
                                "target": link.user_email,
                            }
                        )
                    else:
                        failed_count += 1
                continue

            # ----------------------------------------------------
            # CASE 1: Pending Payment Follow-up (User reminder)
            # ----------------------------------------------------
            if link.status == PaymentStatus.PENDING and not is_past_due:
                created_at = link.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                elapsed_since_created = (now - created_at).total_seconds()
                initial_delay_seconds = settings.PENDING_REMINDER_INITIAL_DELAY_HOURS * 3600

                can_send_initial = elapsed_since_created >= initial_delay_seconds or force
                cooldown_ok = self._is_cooldown_satisfied(link.last_reminder_sent_at, now)
                within_max_reminders = link.reminder_count < settings.MAX_PENDING_REMINDERS

                if can_send_initial and (cooldown_ok or force) and within_max_reminders:
                    success = await self._send_pending_reminder(db, link, now, due_date)
                    if success:
                        pending_sent += 1
                        details.append(
                            {
                                "link_id": link.id,
                                "type": ReminderType.PENDING_REMINDER.value,
                                "status": "SENT",
                                "target": link.user_email,
                            }
                        )
                    else:
                        failed_count += 1

        await db.commit()

        return ReminderTriggerResponse(
            evaluated_count=len(links),
            pending_reminders_sent=pending_sent,
            overdue_alerts_sent=overdue_sent,
            dp_team_alerts_sent=dp_team_sent,
            failed_count=failed_count,
            details=details,
        )

    def _is_cooldown_satisfied(self, last_sent_at: datetime | None, now: datetime) -> bool:
        if not last_sent_at:
            return True
        if last_sent_at.tzinfo is None:
            last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
        elapsed = (now - last_sent_at).total_seconds()
        return elapsed >= (settings.REMINDER_COOLDOWN_HOURS * 3600)

    async def _send_pending_reminder(
        self, db: AsyncSession, link: PaymentLink, now: datetime, due_date: datetime
    ) -> bool:
        course_title = link.course.title if link.course else "GUVI Tech Course"
        subject = f"Gentle Reminder: Complete your enrollment for {course_title}"
        context = {
            "user_name": link.user_name,
            "course_title": course_title,
            "amount_due": link.amount_due,
            "currency": link.currency,
            "payment_link_url": link.payment_link_url,
            "due_date_str": due_date.strftime("%d %B %Y, %I:%M %p UTC"),
        }

        try:
            sent = await notification_service.send(
                channel_type=NotificationChannelType.EMAIL,
                recipient=link.user_email,
                subject=subject,
                template_name="pending_reminder.html",
                context=context,
            )
            log = ReminderLog(
                payment_link_id=link.id,
                reminder_type=ReminderType.PENDING_REMINDER,
                channel=NotificationChannelType.EMAIL,
                recipient=link.user_email,
                subject=subject,
                status=ReminderDeliveryStatus.SENT if sent else ReminderDeliveryStatus.FAILED,
            )
            db.add(log)

            if sent:
                link.reminder_count += 1
                link.last_reminder_sent_at = now
                event = PaymentEvent(
                    payment_link_id=link.id,
                    event_type="PENDING_REMINDER_SENT",
                    description=f"Follow-up reminder #{link.reminder_count} sent to {link.user_email}",
                )
                db.add(event)
            return sent
        except Exception as e:
            logger.error(f"Error sending pending reminder for link {link.id}: {e}")
            log = ReminderLog(
                payment_link_id=link.id,
                reminder_type=ReminderType.PENDING_REMINDER,
                channel=NotificationChannelType.EMAIL,
                recipient=link.user_email,
                subject=subject,
                status=ReminderDeliveryStatus.FAILED,
                error_message=str(e),
            )
            db.add(log)
            return False

    async def _send_overdue_alert(
        self, db: AsyncSession, link: PaymentLink, now: datetime, due_date: datetime
    ) -> bool:
        course_title = link.course.title if link.course else "GUVI Tech Course"
        subject = f"Urgent: Payment Overdue for {course_title} - Retain Your Seat"
        context = {
            "user_name": link.user_name,
            "course_title": course_title,
            "amount_due": link.amount_due,
            "currency": link.currency,
            "payment_link_url": link.payment_link_url,
            "due_date_str": due_date.strftime("%d %B %Y, %I:%M %p UTC"),
        }

        try:
            sent = await notification_service.send(
                channel_type=NotificationChannelType.EMAIL,
                recipient=link.user_email,
                subject=subject,
                template_name="overdue_alert.html",
                context=context,
            )
            log = ReminderLog(
                payment_link_id=link.id,
                reminder_type=ReminderType.OVERDUE_ALERT,
                channel=NotificationChannelType.EMAIL,
                recipient=link.user_email,
                subject=subject,
                status=ReminderDeliveryStatus.SENT if sent else ReminderDeliveryStatus.FAILED,
            )
            db.add(log)

            if sent:
                link.reminder_count += 1
                link.last_reminder_sent_at = now
                event = PaymentEvent(
                    payment_link_id=link.id,
                    event_type="OVERDUE_ALERT_SENT",
                    description=f"Overdue payment alert sent to {link.user_email}",
                )
                db.add(event)
            return sent
        except Exception as e:
            logger.error(f"Error sending overdue alert for link {link.id}: {e}")
            log = ReminderLog(
                payment_link_id=link.id,
                reminder_type=ReminderType.OVERDUE_ALERT,
                channel=NotificationChannelType.EMAIL,
                recipient=link.user_email,
                subject=subject,
                status=ReminderDeliveryStatus.FAILED,
                error_message=str(e),
            )
            db.add(log)
            return False

    async def _send_dp_not_converted_team_alert(
        self, db: AsyncSession, link: PaymentLink, now: datetime, dp_time: datetime
    ) -> bool:
        course_title = link.course.title if link.course else link.course_id
        subject = f"[OPS ALERT] DP Paid but Not Converted: {link.user_name} ({course_title})"
        elapsed_hours = int((now - dp_time).total_seconds() // 3600)
        balance_due = max(0.0, link.amount_due - link.down_payment_amount)

        context = {
            "user_name": link.user_name,
            "user_email": link.user_email,
            "user_phone": link.user_phone,
            "course_title": course_title,
            "course_id": link.course_id,
            "down_payment_amount": link.down_payment_amount,
            "balance_due": balance_due,
            "currency": link.currency,
            "dp_paid_at_str": dp_time.strftime("%d %B %Y, %I:%M %p UTC"),
            "elapsed_hours": elapsed_hours,
            "window_hours": settings.DP_CONVERSION_WINDOW_HOURS,
            "payment_link_url": link.payment_link_url,
            "payment_link_id": link.id,
        }

        try:
            sent = await notification_service.send(
                channel_type=NotificationChannelType.EMAIL,
                recipient=str(settings.COURSES_TEAM_EMAIL),
                subject=subject,
                template_name="dp_not_converted_team_alert.html",
                context=context,
            )
            log = ReminderLog(
                payment_link_id=link.id,
                reminder_type=ReminderType.DP_NOT_CONVERTED_TEAM_ALERT,
                channel=NotificationChannelType.EMAIL,
                recipient=str(settings.COURSES_TEAM_EMAIL),
                subject=subject,
                status=ReminderDeliveryStatus.SENT if sent else ReminderDeliveryStatus.FAILED,
            )
            db.add(log)

            if sent:
                link.dp_team_alerted = True
                link.dp_team_alerted_at = now
                event = PaymentEvent(
                    payment_link_id=link.id,
                    event_type="DP_NOT_CONVERTED_TEAM_ALERT_SENT",
                    description=f"Escalation email sent to Courses Team ({settings.COURSES_TEAM_EMAIL}) for lead {link.user_name}",
                )
                db.add(event)
            return sent
        except Exception as e:
            logger.error(f"Error sending DP escalation email to courses team: {e}")
            log = ReminderLog(
                payment_link_id=link.id,
                reminder_type=ReminderType.DP_NOT_CONVERTED_TEAM_ALERT,
                channel=NotificationChannelType.EMAIL,
                recipient=str(settings.COURSES_TEAM_EMAIL),
                subject=subject,
                status=ReminderDeliveryStatus.FAILED,
                error_message=str(e),
            )
            db.add(log)
            return False


reminder_engine = ReminderEngine()
