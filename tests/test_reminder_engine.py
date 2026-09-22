import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_link import PaymentLink
from app.models.enums import PaymentStatus, PaymentSource, ReminderType
from app.services.reminder_engine import reminder_engine
from app.channels.email import mock_sent_emails
from app.core.config import settings


@pytest.mark.asyncio
async def test_pending_payment_reminder(db_session: AsyncSession):
    # Create a pending payment link created 25 hours ago (beyond the 24h initial delay)
    created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    due_date = datetime.now(timezone.utc) + timedelta(days=2)

    link = PaymentLink(
        id="pending-link-1",
        user_name="Vijay Nathan",
        user_email="vijay@example.com",
        course_id="COURSE-TEST-001",
        amount_due=40000.0,
        payment_link_url="https://pay.guvi.in/checkout?link_id=pending-link-1",
        source=PaymentSource.INTERNAL,
        status=PaymentStatus.PENDING,
        created_at=created_at,
        due_date=due_date,
        reminder_count=0,
    )
    db_session.add(link)
    await db_session.commit()

    # Clear any previous mock emails
    mock_sent_emails.clear()

    # Run reminder evaluation
    response = await reminder_engine.evaluate_and_send_all_reminders(db_session)

    assert response.pending_reminders_sent == 1
    assert len(mock_sent_emails) == 1

    email = mock_sent_emails[0]
    assert email["recipient"] == "vijay@example.com"
    assert "Gentle Reminder" in email["subject"]
    assert "Full Stack Python Development" in email["html"]

    # Verify link record updated
    await db_session.refresh(link)
    assert link.reminder_count == 1
    assert link.last_reminder_sent_at is not None


@pytest.mark.asyncio
async def test_overdue_payment_alert(db_session: AsyncSession):
    # Create a link where due_date has passed 2 hours ago
    created_at = datetime.now(timezone.utc) - timedelta(days=5)
    due_date = datetime.now(timezone.utc) - timedelta(hours=2)

    link = PaymentLink(
        id="overdue-link-1",
        user_name="Meena Kumari",
        user_email="meena@example.com",
        course_id="COURSE-TEST-001",
        amount_due=40000.0,
        payment_link_url="https://pay.guvi.in/checkout?link_id=overdue-link-1",
        source=PaymentSource.INTERNAL,
        status=PaymentStatus.PENDING,
        created_at=created_at,
        due_date=due_date,
        reminder_count=1,
        last_reminder_sent_at=datetime.now(timezone.utc) - timedelta(hours=26),
    )
    db_session.add(link)
    await db_session.commit()

    mock_sent_emails.clear()

    # Run evaluation
    response = await reminder_engine.evaluate_and_send_all_reminders(db_session)

    assert response.overdue_alerts_sent == 1
    assert len(mock_sent_emails) == 1

    email = mock_sent_emails[0]
    assert email["recipient"] == "meena@example.com"
    assert "Payment Overdue" in email["subject"]
    assert "OVERDUE" in email["html"]

    # Verify link updated to OVERDUE status
    await db_session.refresh(link)
    assert link.status == PaymentStatus.OVERDUE


@pytest.mark.asyncio
async def test_dp_paid_not_converted_escalation_to_courses_team(db_session: AsyncSession):
    # Student paid DP 50 hours ago (> 48h conversion window) but full payment not received
    dp_paid_at = datetime.now(timezone.utc) - timedelta(hours=50)
    due_date = datetime.now(timezone.utc) + timedelta(days=5)

    link = PaymentLink(
        id="dp-unconverted-link-1",
        user_name="Rahul Dravid",
        user_email="rahul.student@example.com",
        user_phone="+919888877777",
        course_id="COURSE-TEST-001",
        amount_due=40000.0,
        down_payment_amount=5000.0,
        payment_link_url="https://pay.guvi.in/checkout?link_id=dp-unconverted-link-1",
        source=PaymentSource.INTERNAL,
        status=PaymentStatus.DOWN_PAYMENT_PAID,
        dp_paid_at=dp_paid_at,
        due_date=due_date,
        dp_team_alerted=False,
    )
    db_session.add(link)
    await db_session.commit()

    mock_sent_emails.clear()

    # Run evaluation
    response = await reminder_engine.evaluate_and_send_all_reminders(db_session)

    assert response.dp_team_alerts_sent == 1
    assert len(mock_sent_emails) == 1

    # CRITICAL: Verify recipient is the COURSES TEAM, not the student!
    email = mock_sent_emails[0]
    assert email["recipient"] == settings.COURSES_TEAM_EMAIL
    assert "[OPS ALERT] DP Paid but Not Converted" in email["subject"]
    assert "Rahul Dravid" in email["html"]
    assert "rahul.student@example.com" in email["html"]
    assert "+919888877777" in email["html"]

    # Verify flag set to true so the team is not duplicate-spammed on next scan
    await db_session.refresh(link)
    assert link.dp_team_alerted is True
    assert link.dp_team_alerted_at is not None

    # Run scan again to confirm idempotency
    mock_sent_emails.clear()
    second_run = await reminder_engine.evaluate_and_send_all_reminders(db_session)
    assert second_run.dp_team_alerts_sent == 0
    assert len(mock_sent_emails) == 0
