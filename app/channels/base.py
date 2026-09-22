from abc import ABC, abstractmethod
from typing import Dict, Any
from app.models.enums import NotificationChannelType


class BaseNotificationChannel(ABC):
    """Abstract base class for all pluggable notification channels (Email, SMS, WhatsApp, etc.)"""

    @property
    @abstractmethod
    def channel_type(self) -> NotificationChannelType:
        """Returns the channel enum type"""
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Indicates if this channel is currently active/configured"""
        pass

    @abstractmethod
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        Sends a notification to the specified recipient.
        Returns True if successful, False otherwise.
        """
        pass
