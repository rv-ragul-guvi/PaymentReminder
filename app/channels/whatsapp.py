import logging
from typing import Dict, Any
from app.channels.base import BaseNotificationChannel
from app.core.config import settings
from app.models.enums import NotificationChannelType

logger = logging.getLogger("guvi.notification.whatsapp")


class WhatsAppNotificationChannel(BaseNotificationChannel):
    """
    Pluggable WhatsApp notification channel adapter.
    Can be wired to WhatsApp Cloud API, Gupshup, or Twilio WhatsApp by implementing the provider call below.
    """

    @property
    def channel_type(self) -> NotificationChannelType:
        return NotificationChannelType.WHATSAPP

    @property
    def is_enabled(self) -> bool:
        return settings.ENABLE_WHATSAPP_CHANNEL

    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
    ) -> bool:
        if not self.is_enabled:
            logger.warning(f"WhatsApp channel is disabled. Skipping WhatsApp message to {recipient}")
            return False

        # Pluggable provider integration point (e.g., WhatsApp Cloud API)
        logger.info(
            f"[WHATSAPP CHANNEL STUB] Sending WhatsApp message to {recipient}: {subject}. Context: {context.get('payment_link_url')}"
        )
        return True
