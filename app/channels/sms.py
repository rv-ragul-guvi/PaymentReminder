import logging
from typing import Dict, Any
from app.channels.base import BaseNotificationChannel
from app.core.config import settings
from app.models.enums import NotificationChannelType

logger = logging.getLogger("guvi.notification.sms")


class SMSNotificationChannel(BaseNotificationChannel):
    """
    Pluggable SMS notification channel adapter.
    Can be wired to Twilio, Gupshup, Kaleyra, or AWS SNS by implementing the provider call below.
    """

    @property
    def channel_type(self) -> NotificationChannelType:
        return NotificationChannelType.SMS

    @property
    def is_enabled(self) -> bool:
        return settings.ENABLE_SMS_CHANNEL

    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
    ) -> bool:
        if not self.is_enabled:
            logger.warning(f"SMS channel is disabled. Skipping SMS to {recipient}")
            return False

        # Pluggable provider integration point (e.g., Twilio/Gupshup SMS)
        logger.info(
            f"[SMS CHANNEL STUB] Sending SMS to {recipient}: {subject}. Context: {context.get('payment_link_url')}"
        )
        # In real integration, call SMS Gateway API here
        return True
