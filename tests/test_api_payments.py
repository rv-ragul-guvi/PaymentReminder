import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_status_to_dp_paid(client: AsyncClient):
    due_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    link_res = await client.post(
        "/api/v1/payment-links",
        json={
            "user_name": "Suresh Kumar",
            "user_email": "suresh@example.com",
            "course_id": "COURSE-TEST-001",
            "due_date": due_date,
        },
    )
    link_id = link_res.json()["id"]

    # Status update to DOWN_PAYMENT_PAID
    payload = {
        "payment_link_id": link_id,
        "new_status": "DOWN_PAYMENT_PAID",
        "amount_paid": 5000.0,
        "transaction_reference": "TXN_DP_98765",
        "notes": "Paid initial token/DP via UPI",
    }
    update_res = await client.post("/api/v1/payments/status-update", json=payload)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["status"] == "DOWN_PAYMENT_PAID"
    assert updated["dp_paid_at"] is not None


@pytest.mark.asyncio
async def test_update_status_to_converted(client: AsyncClient):
    due_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    link_res = await client.post(
        "/api/v1/payment-links",
        json={
            "user_name": "Deepa R",
            "user_email": "deepa@example.com",
            "course_id": "COURSE-TEST-001",
            "due_date": due_date,
        },
    )
    link_id = link_res.json()["id"]

    # Full payment conversion
    payload = {
        "payment_link_id": link_id,
        "new_status": "CONVERTED",
        "amount_paid": 40000.0,
        "transaction_reference": "TXN_FULL_112233",
        "notes": "Full course fees cleared",
    }
    update_res = await client.post("/api/v1/payments/status-update", json=payload)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["status"] == "CONVERTED"
    assert updated["converted_at"] is not None
