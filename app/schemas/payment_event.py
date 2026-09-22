from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from app.models.enums import PaymentStatus


class PaymentStatusUpdate(BaseModel):
    payment_link_id: str = Field(..., description="ID of payment link to update")
    new_status: PaymentStatus = Field(..., description="DOWN_PAYMENT_PAID, CONVERTED, CANCELLED, etc.")
    amount_paid: Optional[float] = Field(None, ge=0, description="Amount received in this transaction")
    transaction_reference: Optional[str] = Field(None, description="Gateway or Bank transaction ID")
    notes: Optional[str] = None


class PaymentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_link_id: str
    event_type: str
    description: str
    payload_json: Optional[str] = None
    created_at: datetime
