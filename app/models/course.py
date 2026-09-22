from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.payment_link import PaymentLink


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    full_price: Mapped[float] = mapped_column(Float, nullable=False)
    down_payment_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    payment_links: Mapped[List["PaymentLink"]] = relationship(
        "PaymentLink", back_populates="course", cascade="all, delete-orphan"
    )
