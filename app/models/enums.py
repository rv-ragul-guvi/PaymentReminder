import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    DOWN_PAYMENT_PAID = "DOWN_PAYMENT_PAID"
    CONVERTED = "CONVERTED"
    OVERDUE = "OVERDUE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentSource(str, enum.Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class NotificationChannelType(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class ReminderType(str, enum.Enum):
    PENDING_REMINDER = "PENDING_REMINDER"
    OVERDUE_ALERT = "OVERDUE_ALERT"
    DP_NOT_CONVERTED_TEAM_ALERT = "DP_NOT_CONVERTED_TEAM_ALERT"


class ReminderDeliveryStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
