from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.models.reminder_log import ReminderLog
from app.models.payment_link import PaymentLink
from app.models.enums import ReminderType, NotificationChannelType, ReminderDeliveryStatus
from app.schemas.reminder import ReminderTriggerResponse, ReminderLogRead
from app.services.reminder_engine import reminder_engine

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.post("/trigger", response_model=ReminderTriggerResponse)
async def trigger_reminder_evaluation(
    force: bool = Query(
        False,
        description="Bypass normal cooldown & delay thresholds (useful for automated testing or manual forced batches)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger evaluation of all active payment links:
    - Sends pending reminders to users if payment is not made
    - Sends overdue alerts to users if due date has passed
    - Sends escalation emails to the GUVI Courses Team if DP is paid but not converted
    """
    return await reminder_engine.evaluate_and_send_all_reminders(db, force=force)


@router.get("/logs", response_model=List[ReminderLogRead])
async def list_reminder_logs(
    reminder_type: Optional[ReminderType] = None,
    channel: Optional[NotificationChannelType] = None,
    status_filter: Optional[ReminderDeliveryStatus] = Query(None, alias="status"),
    payment_link_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs of all sent reminders across Email, SMS, and WhatsApp.
    """
    query = (
        select(ReminderLog)
        .options(selectinload(ReminderLog.payment_link).selectinload(PaymentLink.course))
        .order_by(ReminderLog.sent_at.desc())
    )
    if reminder_type:
        query = query.where(ReminderLog.reminder_type == reminder_type)
    if channel:
        query = query.where(ReminderLog.channel == channel)
    if status_filter:
        query = query.where(ReminderLog.status == status_filter)
    if payment_link_id:
        query = query.where(ReminderLog.payment_link_id == payment_link_id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())
