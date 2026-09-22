import pytest
from app.channels.factory import NotificationService
from app.channels.base import BaseNotificationChannel
from app.channels.email import EmailNotificationChannel
from app.models.enums import NotificationChannelType


class CustomMockWhatsAppChannel(BaseNotificationChannel):
    def __init__(self):
        self.sent_messages = []

    @property
    def channel_type(self) -> NotificationChannelType:
        return NotificationChannelType.WHATSAPP

    @property
    def is_enabled(self) -> bool:
        return True

    async def send_notification(self, recipient: str, subject: str, template_name: str, context: dict) -> bool:
        self.sent_messages.append({"recipient": recipient, "subject": subject, "context": context})
        return True


@pytest.mark.asyncio
async def test_pluggable_channel_architecture():
    service = NotificationService()

    # Verify default email channel is registered
    email_channel = service.get_channel(NotificationChannelType.EMAIL)
    assert isinstance(email_channel, EmailNotificationChannel)

    # Plug in custom WhatsApp channel
    custom_whatsapp = CustomMockWhatsAppChannel()
    service.register_channel(custom_whatsapp)

    # Send notification via the plugged-in WhatsApp channel
    success = await service.send(
        channel_type=NotificationChannelType.WHATSAPP,
        recipient="+919999988888",
        subject="Your GUVI Course Payment Link",
        template_name="dummy",
        context={"payment_link_url": "https://pay.guvi.in/test"},
    )
    assert success is True
    assert len(custom_whatsapp.sent_messages) == 1
    assert custom_whatsapp.sent_messages[0]["recipient"] == "+919999988888"


@pytest.mark.asyncio
async def test_email_template_rendering():
    email_channel = EmailNotificationChannel()
    context = {
        "user_name": "Test Candidate",
        "course_title": "Python Deep Dive",
        "amount_due": 30000.0,
        "currency": "INR",
        "payment_link_url": "https://pay.guvi.in/checkout?link_id=12345",
        "due_date_str": "25 September 2026",
    }
    # Test rendering pending reminder
    sent = await email_channel.send_notification(
        recipient="test@example.com",
        subject="Gentle Reminder",
        template_name="pending_reminder.html",
        context=context,
    )
    assert sent is True
