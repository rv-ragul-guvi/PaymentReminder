from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    PROJECT_NAME: str = "GUVI Payment Reminder Service"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database (defaults to local async SQLite, easily swapped for PostgreSQL)
    DATABASE_URL: str = "sqlite+aiosqlite:///./payment_reminders.db"

    # Company / Service Info
    COMPANY_NAME: str = "GUVI"
    COMPANY_SUPPORT_EMAIL: str = "support@guvi.in"
    COURSES_TEAM_EMAIL: EmailStr = "courses-team@guvi.in"
    BASE_PAYMENT_GATEWAY_URL: str = "https://pay.guvi.in/checkout"

    # Notification Channels
    DEFAULT_NOTIFICATION_CHANNEL: str = "EMAIL"  # EMAIL, SMS, WHATSAPP
    ENABLE_EMAIL_CHANNEL: bool = True
    ENABLE_SMS_CHANNEL: bool = False
    ENABLE_WHATSAPP_CHANNEL: bool = False

    # SMTP / Email Configuration
    EMAIL_MODE: str = "MOCK"  # "MOCK" (logs to stdout/memory for tests/dev) or "SMTP"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: EmailStr = "admissions@guvi.in"
    EMAILS_FROM_NAME: str = "Team GUVI"

    # Reminder Policies & Intervals
    # Time elapsed since payment link shared to trigger first pending reminder (in hours)
    PENDING_REMINDER_INITIAL_DELAY_HOURS: int = 24
    # Minimum interval between consecutive reminders for the same link (in hours)
    REMINDER_COOLDOWN_HOURS: int = 24
    # Max reminders to send to a user for a pending link
    MAX_PENDING_REMINDERS: int = 3
    # DP (Down Payment) Paid but Not Converted escalation threshold (in hours)
    DP_CONVERSION_WINDOW_HOURS: int = 48
    # Scheduler interval to scan and evaluate reminders (in seconds)
    SCHEDULER_INTERVAL_SECONDS: int = 300  # every 5 minutes by default


settings = Settings()
