import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.channels.email import mock_sent_emails


@pytest.mark.asyncio
async def test_create_internal_payment_link(client: AsyncClient):
    due_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    payload = {
        "user_name": "Karthik Raja",
        "user_email": "karthik@example.com",
        "user_phone": "+919876543210",
        "course_id": "COURSE-TEST-001",
        "due_date": due_date,
        "notes": "Spoke to candidate; interested in weekend batch",
    }
    response = await client.post("/api/v1/payment-links", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["user_name"] == "Karthik Raja"
    assert data["user_email"] == "karthik@example.com"
    assert data["source"] == "INTERNAL"
    assert data["status"] == "PENDING"
    assert "link_id=" in data["payment_link_url"]
    assert data["amount_due"] == 40000.0
    assert data["down_payment_amount"] == 5000.0

    # Verify initial email dispatch
    assert len(mock_sent_emails) == 1
    sent = mock_sent_emails[0]
    assert sent["recipient"] == "karthik@example.com"
    assert "Full Stack Python Development" in sent["subject"]


@pytest.mark.asyncio
async def test_record_external_payment_link(client: AsyncClient):
    due_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    payload = {
        "user_name": "Ananya Sharma",
        "user_email": "ananya@example.com",
        "user_phone": "+919123456780",
        "course_id": "COURSE-TEST-001",
        "amount_due": 42000.0,
        "down_payment_amount": 5000.0,
        "currency": "INR",
        "payment_link_url": "https://rzp.io/i/ext_guvi_12345",
        "external_reference_id": "plink_rzp_999888",
        "due_date": due_date,
        "notes": "Shared via external CRM Razorpay portal",
    }
    response = await client.post("/api/v1/payment-links/external-event", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["user_name"] == "Ananya Sharma"
    assert data["source"] == "EXTERNAL"
    assert data["external_reference_id"] == "plink_rzp_999888"
    assert data["payment_link_url"] == "https://rzp.io/i/ext_guvi_12345"
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_get_payment_link_details(client: AsyncClient):
    due_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    create_res = await client.post(
        "/api/v1/payment-links",
        json={
            "user_name": "Priya V",
            "user_email": "priya@example.com",
            "course_id": "COURSE-TEST-001",
            "due_date": due_date,
        },
    )
    link_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/payment-links/{link_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["id"] == link_id
    assert details["user_name"] == "Priya V"
    assert details["course"]["id"] == "COURSE-TEST-001"


@pytest.mark.asyncio
async def test_filter_payment_links(client: AsyncClient):
    due_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    await client.post(
        "/api/v1/payment-links",
        json={
            "user_name": "Filter User",
            "user_email": "filter_user@example.com",
            "course_id": "COURSE-TEST-001",
            "due_date": due_date,
        },
    )
    res = await client.get("/api/v1/payment-links?user_email=filter_user@example.com")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["user_email"] == "filter_user@example.com"
