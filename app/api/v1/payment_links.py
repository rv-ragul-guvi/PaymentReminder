from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.models.enums import PaymentStatus, PaymentSource
from app.schemas.payment_link import (
    PaymentLinkCreateInternal,
    PaymentLinkRecordExternal,
    PaymentLinkRead,
    PaymentLinkFilter,
)
from app.services.payment_service import payment_service

router = APIRouter(prefix="/payment-links", tags=["Payment Links"])


@router.post("", response_model=PaymentLinkRead, status_code=status.HTTP_201_CREATED)
async def create_internal_payment_link(
    payload: PaymentLinkCreateInternal, db: AsyncSession = Depends(get_db)
):
    """
    Generate an internal payment link for a user, store it in the DB,
    and dispatch the initial payment link email.
    """
    try:
        payment_link = await payment_service.create_internal_payment_link(db, payload)
        return payment_link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate payment link: {str(e)}",
        )


@router.post(
    "/external-event",
    response_model=PaymentLinkRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_external_payment_link_event(
    payload: PaymentLinkRecordExternal, db: AsyncSession = Depends(get_db)
):
    """
    Record payment link sent event in our DB when the payment link
    is generated or sent by an external portal/gateway.
    """
    try:
        payment_link = await payment_service.record_external_payment_link(db, payload)
        return payment_link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record external payment link: {str(e)}",
        )


@router.get("", response_model=List[PaymentLinkRead])
async def list_payment_links(
    status_filter: Optional[PaymentStatus] = Query(None, alias="status"),
    course_id: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    source: Optional[PaymentSource] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List and filter stored payment links.
    """
    filters = PaymentLinkFilter(
        status=status_filter,
        course_id=course_id,
        user_email=user_email,
        source=source,
    )
    return await payment_service.get_payment_links(
        db, filters=filters, limit=limit, offset=offset
    )


@router.get("/{payment_link_id}", response_model=PaymentLinkRead)
async def get_payment_link(
    payment_link_id: str, db: AsyncSession = Depends(get_db)
):
    """
    Retrieve full details of a specific payment link.
    """
    link = await payment_service.get_payment_link_by_id(db, payment_link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment link with ID '{payment_link_id}' not found.",
        )
    return link
