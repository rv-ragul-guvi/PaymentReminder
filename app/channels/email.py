import logging
import os
from pathlib import Path
from email.message import EmailMessage
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape

import aiosmtplib

from app.channels.base import BaseNotificationChannel
from app.core.config import settings
from app.models.enums import NotificationChannelType

logger = logging.getLogger("guvi.notification.email")

# In-memory buffer of sent emails for testing / mock verification
mock_sent_emails: List[Dict[str, Any]] = []


class EmailNotificationChannel(BaseNotificationChannel):
    def __init__(self):
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        if not template_dir.exists():
            template_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    @property
    def channel_type(self) -> NotificationChannelType:
        return NotificationChannelType.EMAIL

    @property
    def is_enabled(self) -> bool:
        return settings.ENABLE_EMAIL_CHANNEL

    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
    ) -> bool:
        if not self.is_enabled:
            logger.warning(f"Email channel is disabled. Skipping message to {recipient}")
            return False

        # Enrich context with defaults if not present
        full_context = {
            "company_name": settings.COMPANY_NAME,
            "support_email": settings.COMPANY_SUPPORT_EMAIL,
            "recipient_email": recipient,
            **context,
        }

        try:
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(full_context)
        except Exception as e:
            logger.error(f"Failed to render email template {template_name}: {e}")
            raise

        if settings.EMAIL_MODE.upper() == "MOCK" or not settings.SMTP_HOST:
            # Mock mode: record message and log
            record = {
                "recipient": recipient,
                "subject": subject,
                "template": template_name,
                "context": full_context,
                "html": html_content,
            }
            mock_sent_emails.append(record)
            logger.info(
                f"[MOCK EMAIL SENT] To: {recipient} | Subject: '{subject}' | Template: {template_name}"
            )
            return True

        # Real SMTP delivery via aiosmtplib
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg["To"] = recipient
            msg.set_content(f"Please view this email in an HTML-compatible client. Subject: {subject}")
            msg.add_alternative(html_content, subtype="html")

            # Configure TLS: port 465 uses direct TLS (use_tls=True), port 587 uses STARTTLS
            use_tls = (settings.SMTP_PORT == 465)
            start_tls = (settings.SMTP_PORT == 587 or (settings.SMTP_TLS and not use_tls))

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=use_tls,
                start_tls=start_tls,
            )
            logger.info(f"[SMTP EMAIL SENT] Successfully sent email to {recipient} with subject '{subject}'")
            return True
        except Exception as e:
            logger.error(f"[SMTP ERROR] Failed to send email to {recipient}: {e}")
            raise
