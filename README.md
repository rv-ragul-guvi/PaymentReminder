# GUVI Payment Reminder Service

A production-grade, asynchronous backend service built with **FastAPI**, **SQLAlchemy**, and **APScheduler** for **GUVI Geek Networks** to automate course payment follow-ups, overdue payment alerts, and internal sales/counselor escalations for down payments paid but not converted.

---

## 🎯 Key Requirements & Features

1. **Pending Payment Follow-ups**: Automatically sends reminder notifications when a course payment link is shared with a student but payment is still pending.
2. **Overdue Payment Alerts**: Detects when a payment deadline has passed and sends an urgent overdue alert to the student while updating the status to `OVERDUE`.
3. **Down Payment (DP) Paid but Not Converted Escalation**:
   - When a student pays the down payment but has not converted (completed full payment) within the conversion window (e.g. 48 hours), the system automatically triggers an escalation alert directly to the **GUVI Courses Team** (`courses-team@guvi.in`).
   - The alert provides the student's name, phone, email, course details, down payment paid, remaining balance, and payment link so counselors can intervene.
4. **Dual Link Sources**:
   - **Internal Generation**: Generate and store branded payment links directly from the GUVI service (`POST /api/v1/payment-links`), automatically emailing the initial link to the user.
   - **External Ingestion**: Record payment links generated or sent by external portals/CRMs/gateways (`POST /api/v1/payment-links/external-event`).
5. **Pluggable Notification System**:
   - Built on an extensible `BaseNotificationChannel` interface.
   - Fully implemented **Email** channel with rich HTML Jinja2 templates (supports both `MOCK` for local development/testing and `SMTP` for production).
   - Pre-configured pluggable adapters for **SMS** and **WhatsApp** ready for provider SDK integration (Twilio, Gupshup, Kaleyra, Meta Cloud API).
6. **Anti-Spam & Cooldown Protection**:
   - Configurable cooldown windows between reminders.
   - Max reminder limits to prevent user fatigue.
   - Full audit trail stored in `reminder_logs` and `payment_events`.
7. **Docker & Compose**: Containerized with multi-stage Dockerfile and Docker Compose.

---

## 🏗️ Architecture Overview

```
app/
├── api/
│   └── v1/
│       ├── courses.py          # Course catalog endpoints
│       ├── payment_links.py    # Payment link generation & external ingestion
│       ├── payments.py         # Payment status webhook & updates
│       └── reminders.py        # Reminder trigger & audit logs
├── channels/                   # Pluggable Notification System
│   ├── base.py                 # BaseNotificationChannel abstract contract
│   ├── email.py                # Email channel (HTML templates + SMTP/Mock)
│   ├── sms.py                  # SMS channel adapter stub
│   ├── whatsapp.py             # WhatsApp channel adapter stub
│   └── factory.py              # NotificationService dispatcher
├── core/
│   ├── config.py               # Pydantic Settings & environment config
│   └── database.py             # Async SQLAlchemy engine & session factory
├── models/                     # SQLAlchemy models
│   ├── course.py               # Course definitions
│   ├── enums.py                # PaymentStatus, PaymentSource, Channels, etc.
│   ├── payment_event.py        # Event history log
│   ├── payment_link.py         # Payment link state & timestamps
│   └── reminder_log.py         # Audit trail of every notification dispatched
├── schemas/                    # Pydantic input/output schemas
├── services/
│   ├── payment_service.py      # Core payment operations & lifecycle
│   └── reminder_engine.py      # Automated reminder & escalation evaluator
├── templates/
│   └── email/                  # Responsive HTML email templates
│       ├── payment_link_initial.html
│       ├── pending_reminder.html
│       ├── overdue_alert.html
│       └── dp_not_converted_team_alert.html
├── worker.py                   # Background scheduler job (APScheduler)
└── main.py                     # FastAPI application factory & lifespan
```

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+ (or Docker)
- pip / virtualenv

### 1. Local Setup
```bash
# Clone and enter directory
cd /Users/r-ragul/GUVI/PaymentReminder

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment settings
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Visit the interactive Swagger API documentation at:
**http://localhost:8000/docs**

---

### 2. Running with Docker Compose
```bash
docker-compose up --build
```
The service will start on port `8000` with persistent SQLite storage mounted at `/data/payment_reminders.db`.

---

## 📡 API Endpoints Reference

### 1. Payment Links
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/payment-links` | Generate internal payment link, store in DB, and email student |
| `POST` | `/api/v1/payment-links/external-event` | Record payment link sent event from external portal/CRM |
| `GET` | `/api/v1/payment-links` | List payment links (filter by `status`, `user_email`, `course_id`, `source`) |
| `GET` | `/api/v1/payment-links/{id}` | Get full payment link details with lifecycle events and reminder logs |

### 2. Payment Status & Webhooks
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/payments/status-update` | Update payment status (`DOWN_PAYMENT_PAID`, `CONVERTED`, `CANCELLED`, `EXPIRED`) |

### 3. Reminders & Monitoring
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/reminders/trigger` | Manually run reminder evaluation (`?force=true` bypasses cooldown for testing/cron) |
| `GET` | `/api/v1/reminders/logs` | Query reminder delivery logs across Email, SMS, WhatsApp |
| `GET` | `/health` | Service health check |

### 4. Courses
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/courses` | List all available courses |
| `POST` | `/api/v1/courses` | Create a new course entry |

---

## 🧪 Testing

Run the automated test suite covering all APIs, reminder workflows, escalation alerts, and notification channels:
```bash
source .venv/bin/activate
python -m pytest -v
```

---

## ⚙️ Configuration (.env)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./payment_reminders.db` | Async database connection URL (SQLite or PostgreSQL) |
| `EMAIL_MODE` | `MOCK` | `MOCK` (logs emails without sending) or `SMTP` (real email dispatch) |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP host |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | `""` | SMTP username/email |
| `SMTP_PASSWORD` | `""` | SMTP password / App password |
| `COURSES_TEAM_EMAIL` | `courses-team@guvi.in` | Target email for Down Payment non-conversion escalations |
| `PENDING_REMINDER_INITIAL_DELAY_HOURS` | `24` | Hours to wait after link is sent before sending first pending reminder |
| `REMINDER_COOLDOWN_HOURS` | `24` | Minimum hours between consecutive reminders |
| `MAX_PENDING_REMINDERS` | `3` | Maximum pending reminders sent to a user |
| `DP_CONVERSION_WINDOW_HOURS` | `48` | Threshold hours before DP is marked unconverted and team is alerted |
| `SCHEDULER_INTERVAL_SECONDS` | `300` | Frequency in seconds for the background reminder scanner |

---

## 🔌 Pluggable Notification Channels

To plug in a new SMS or WhatsApp provider:
1. Open `app/channels/sms.py` or `app/channels/whatsapp.py` (or create a new channel subclassing `BaseNotificationChannel`).
2. Implement `send_notification(...)` with your provider's SDK (e.g. Twilio, Gupshup, Meta Cloud API).
3. Set `ENABLE_SMS_CHANNEL=true` or `ENABLE_WHATSAPP_CHANNEL=true` in `.env`.
4. Register the channel with `notification_service.register_channel(...)`.
