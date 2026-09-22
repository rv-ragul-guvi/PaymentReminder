from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
from app.models.enums import NotificationChannelType, ReminderType, ReminderDeliveryStatus


class ReminderLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_link_id: str
    reminder_type: ReminderType
    channel: NotificationChannelType
    recipient: str
    subject: str
    status: ReminderDeliveryStatus
    error_message: Optional[str] = None
    sent_at: datetime
    course_title: Optional[str] = None
    course_id: Optional[str] = None


class ReminderTriggerResponse(BaseModel):
    evaluated_count: int
    pending_reminders_sent: int
    overdue_alerts_sent: int
    dp_team_alerts_sent: int
    failed_count: int
    details: List[Dict[str, str]]
