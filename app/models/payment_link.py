from sqlalchemy import String, Float, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
import uuid

from app.core.database import Base
from app.models.enums import PaymentStatus, PaymentSource

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.payment_event import PaymentEvent
    from app.models.reminder_log import ReminderLog


class PaymentLink(Base):
    __tablename__ = "payment_links"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("courses.id"), nullable=False, index=True)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    down_payment_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="INR")

    payment_link_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[PaymentSource] = mapped_column(
        SQLEnum(PaymentSource), default=PaymentSource.INTERNAL, nullable=False
    )
    external_reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Lifecycle milestones
    dp_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reminders tracking
    reminder_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dp_team_alerted: Mapped[bool] = mapped_column(Boolean, default=False)
    dp_team_alerted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="payment_links", lazy="selectin")
    events: Mapped[List["PaymentEvent"]] = relationship(
        "PaymentEvent", back_populates="payment_link", cascade="all, delete-orphan", order_by="PaymentEvent.created_at.desc()"
    )
    reminder_logs: Mapped[List["ReminderLog"]] = relationship(
        "ReminderLog", back_populates="payment_link", cascade="all, delete-orphan", order_by="ReminderLog.sent_at.desc()"
    )
