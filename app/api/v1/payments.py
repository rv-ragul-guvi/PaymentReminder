from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.payment_event import PaymentStatusUpdate
from app.schemas.payment_link import PaymentLinkRead
from app.services.payment_service import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/status-update", response_model=PaymentLinkRead)
async def update_payment_status(
    payload: PaymentStatusUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update payment status (e.g. DOWN_PAYMENT_PAID, CONVERTED, CANCELLED, EXPIRED).
    Can be invoked manually or configured as a webhook receiver from payment gateways.
    """
    try:
        updated_link = await payment_service.update_payment_status(db, payload)
        return updated_link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment status: {str(e)}",
        )
