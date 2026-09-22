import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.channels.email import mock_sent_emails


@pytest.mark.asyncio
async def test_trigger_reminders_api_flow(client: AsyncClient):
    # 1. Create a payment link
    due_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create_res = await client.post(
        "/api/v1/payment-links",
        json={
            "user_name": "Arjun Das",
            "user_email": "arjun@example.com",
            "course_id": "COURSE-TEST-001",
            "due_date": due_date,
        },
    )
    assert create_res.status_code == 201
    link_id = create_res.json()["id"]

    mock_sent_emails.clear()

    # 2. Trigger reminders with force=True (simulates immediate cron/scan trigger)
    trigger_res = await client.post("/api/v1/reminders/trigger?force=true")
    assert trigger_res.status_code == 200
    summary = trigger_res.json()
    assert summary["evaluated_count"] >= 1
    assert summary["pending_reminders_sent"] >= 1

    # 3. Verify reminder logs endpoint
    logs_res = await client.get(f"/api/v1/reminders/logs?payment_link_id={link_id}")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert any(log["recipient"] == "arjun@example.com" for log in logs)


@pytest.mark.asyncio
async def test_dp_paid_not_converted_api_flow(client: AsyncClient):
    # 1. Create payment link
    due_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    res = await client.post(
        "/api/v1/payment-links",
        json={
            "user_name": "Divya Prakash",
            "user_email": "divya@example.com",
            "user_phone": "+919777788888",
            "course_id": "COURSE-TEST-001",
            "due_date": due_date,
        },
    )
    link_id = res.json()["id"]

    # 2. Update status to DOWN_PAYMENT_PAID
    update_res = await client.post(
        "/api/v1/payments/status-update",
        json={
            "payment_link_id": link_id,
            "new_status": "DOWN_PAYMENT_PAID",
            "amount_paid": 5000.0,
        },
    )
    assert update_res.status_code == 200

    mock_sent_emails.clear()

    # 3. Trigger reminder scan with force=True
    trigger_res = await client.post("/api/v1/reminders/trigger?force=true")
    assert trigger_res.status_code == 200
    summary = trigger_res.json()
    assert summary["dp_team_alerts_sent"] >= 1

    # 4. Verify team email was captured in mock buffer
    assert len(mock_sent_emails) >= 1
    team_email = next((e for e in mock_sent_emails if "courses-team@guvi.in" in e["recipient"]), None)
    assert team_email is not None
    assert "Divya Prakash" in team_email["html"]
    assert "+919777788888" in team_email["html"]
