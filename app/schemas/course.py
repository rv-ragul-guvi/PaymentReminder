from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class CourseBase(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    full_price: float
    down_payment_amount: float
    currency: str = "INR"


class CourseCreate(CourseBase):
    pass


class CourseRead(CourseBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
