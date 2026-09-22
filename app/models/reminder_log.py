from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
import uuid

from app.core.database import Base
from app.models.enums import NotificationChannelType, ReminderType, ReminderDeliveryStatus

if TYPE_CHECKING:
    from app.models.payment_link import PaymentLink


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    payment_link_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("payment_links.id"), nullable=False, index=True
    )
    reminder_type: Mapped[ReminderType] = mapped_column(
        SQLEnum(ReminderType), nullable=False, index=True
    )
    channel: Mapped[NotificationChannelType] = mapped_column(
        SQLEnum(NotificationChannelType), nullable=False, index=True
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ReminderDeliveryStatus] = mapped_column(
        SQLEnum(ReminderDeliveryStatus), default=ReminderDeliveryStatus.SENT, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    payment_link: Mapped["PaymentLink"] = relationship("PaymentLink", back_populates="reminder_logs")

    @property
    def course_title(self) -> Optional[str]:
        if self.payment_link and self.payment_link.course:
            return self.payment_link.course.title
        return None

    @property
    def course_id(self) -> Optional[str]:
        if self.payment_link:
            return self.payment_link.course_id
        return None
