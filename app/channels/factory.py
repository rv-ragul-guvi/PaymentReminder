import logging
from typing import Dict, Optional
from app.channels.base import BaseNotificationChannel
from app.channels.email import EmailNotificationChannel
from app.channels.sms import SMSNotificationChannel
from app.channels.whatsapp import WhatsAppNotificationChannel
from app.models.enums import NotificationChannelType

logger = logging.getLogger("guvi.notification.factory")


class NotificationService:
    def __init__(self):
        self._channels: Dict[NotificationChannelType, BaseNotificationChannel] = {}
        # Register default supported channels
        self.register_channel(EmailNotificationChannel())
        self.register_channel(SMSNotificationChannel())
        self.register_channel(WhatsAppNotificationChannel())

    def register_channel(self, channel: BaseNotificationChannel):
        """Allows dynamic registration or replacement of notification channels"""
        self._channels[channel.channel_type] = channel
        logger.info(f"Registered notification channel: {channel.channel_type.value}")

    def get_channel(self, channel_type: NotificationChannelType) -> Optional[BaseNotificationChannel]:
        return self._channels.get(channel_type)

    async def send(
        self,
        channel_type: NotificationChannelType,
        recipient: str,
        subject: str,
        template_name: str,
        context: dict,
    ) -> bool:
        channel = self.get_channel(channel_type)
        if not channel:
            logger.error(f"No notification channel registered for type: {channel_type}")
            return False

        if not channel.is_enabled:
            logger.warning(f"Channel {channel_type} is not enabled in settings.")
            return False

        return await channel.send_notification(
            recipient=recipient,
            subject=subject,
            template_name=template_name,
            context=context,
        )


notification_service = NotificationService()
