# MW Backup Link Monitor System

A real-time **Microwave Backup Link Monitoring** platform built for telecom network operations teams. It continuously pings microwave and fiber backup links, tracks reachability and latency, enriches data with external utilization metrics, and delivers instant alerts via email, in-app notifications, webhooks, and WebSocket events.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Deployment (Production)](#docker-deployment-production)
  - [Simulation Mode](#simulation-mode)
- [Initial Setup Wizard](#initial-setup-wizard)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Application Settings](#application-settings)
  - [Secrets Management](#secrets-management)
- [Core Concepts](#core-concepts)
  - [Link Lifecycle](#link-lifecycle)
  - [Ping Cycle](#ping-cycle)
  - [Flapping Detection](#flapping-detection)
  - [Utilization Monitoring](#utilization-monitoring)
  - [Notification System](#notification-system)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [API Reference](#api-reference)
  - [Authentication](#authentication-api)
  - [Dashboard](#dashboard-api)
  - [Links](#links-api)
  - [Users](#users-api)
  - [Roles](#roles-api)
  - [Notifications](#notifications-api)
  - [Settings](#settings-api)
  - [Logs](#logs-api)
  - [Health & Readiness](#health--readiness-api)
- [WebSocket Events](#websocket-events)
- [Scheduled Jobs](#scheduled-jobs)
- [Jump Server (SSH Gateway)](#jump-server-ssh-gateway)
- [External Utilization Database](#external-utilization-database)
- [Email Notifications](#email-notifications)
- [Webhook Integrations](#webhook-integrations)
- [Security](#security)
- [Data Persistence](#data-persistence)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

The MW Backup Link Monitor System is designed for **telecom operations centers** that need to monitor the health and utilization of microwave (MW) and fiber backup links across a network. It provides:

- **Automated ICMP ping monitoring** with configurable intervals and concurrency
- **Real-time dashboards** with live KPI updates via WebSocket
- **Multi-channel alerting** (email with Outlook threading, in-app, webhooks/Slack)
- **External database integration** for utilization metrics from NMS/P&Q systems
- **Role-based access control** with granular permissions
- **Comprehensive audit logging** of all user and system actions
- **SSH jump server support** for pinging devices behind network boundaries

---

## Key Features

| Feature | Description |
|---|---|
| **Real-Time Dashboard** | Live KPIs — total links, reachable/unreachable, high utilization, 24h availability |
| **Concurrent Ping Engine** | Multi-threaded ping cycles with configurable concurrency (default 10 workers) |
| **Flapping Detection** | Automatically detects rapid UP/DOWN oscillation and suppresses noisy alerts |
| **Per-Link Thresholds** | Override global utilization thresholds on a per-link basis |
| **Email Threading** | DOWN → RECOVERED emails are threaded in Outlook using `Thread-Index` headers |
| **Notification Cooldowns** | Prevents alert storms with per-event-type cooldown timers (30 min – 1 hour) |
| **CSV Export** | Export filtered link inventory and status to CSV |
| **External DB Sync** | Daily sync of MW/LEG utilization data from an external MySQL database |
| **SSH Jump Server** | Persistent SSH connection pooling for pinging devices via a bastion host |
| **Guided Setup Wizard** | Step-by-step initial configuration (database, admin user, SMTP, jump server) |
| **Health Probes** | `/health` (liveness) and `/ready` (readiness) endpoints for container orchestration |
| **Webhook/Slack** | Push alert payloads to generic webhooks or Slack-formatted endpoints |
| **Daily Reports** | Scheduled daily summary emails sent to all active users |
| **Session Management** | Configurable session timeout, account lockout, and forced password change |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Application                     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │  Routes   │  │ Templates │  │  Static (CSS/JS)   │    │
│  │ (API +   │  │ (Jinja2) │  │  Dashboard, Auth,  │    │
│  │  Pages)  │  │          │  │  Tables, Modals    │    │
│  └─────┬────┘  └──────────┘  └────────────────────┘    │
│        │                                                │
│  ┌─────▼──────────────────────────────────────────┐     │
│  │               Service Layer                     │     │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────────┐  │     │
│  │  │ Ping     │ │Notification│ │External Util  │  │     │
│  │  │ Service  │ │ Service    │ │ Service       │  │     │
│  │  └──────────┘ └───────────┘ └───────────────┘  │     │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────────┐  │     │
│  │  │SSH Sess. │ │ Crypto    │ │ Log Service   │  │     │
│  │  │ Manager  │ │ Service   │ │               │  │     │
│  │  └──────────┘ └───────────┘ └───────────────┘  │     │
│  └────────────────────────────────────────────────┘     │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐      │
│  │ APScheduler │  │ SocketIO   │  │ Flask-Limiter│      │
│  │ (Background)│  │ (WebSocket)│  │ (Rate Limit) │      │
│  └────────────┘  └────────────┘  └──────────────┘      │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │          SQLAlchemy ORM (Models)             │        │
│  │  Link, PingResult, LinkStatus, User, Role,  │        │
│  │  SmtpConfig, JumpServer, AppSettings, ...   │        │
│  └────────────────┬────────────────────────────┘        │
└───────────────────┼─────────────────────────────────────┘
                    │
          ┌─────────▼──────────┐
          │   SQLite / MySQL   │
          │   (App Database)   │
          └────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Flask 3.0 |
| **ORM** | Flask-SQLAlchemy 3.1 |
| **Real-Time** | Flask-SocketIO 5.x + Eventlet |
| **Task Scheduler** | APScheduler 3.10 |
| **SSH Client** | Paramiko 3.4 |
| **Encryption** | Cryptography (Fernet + PBKDF2) |
| **Password Hashing** | Flask-Bcrypt |
| **Rate Limiting** | Flask-Limiter 3.5+ |
| **Database** | SQLite (default) / MySQL / PostgreSQL |
| **External DB** | PyMySQL (MySQL/MariaDB connector) |
| **WSGI Server** | Gunicorn 21.2 + Eventlet worker |
| **Containerization** | Docker + Docker Compose |
| **Frontend** | Vanilla HTML/CSS/JS, Chart.js |

---

## Project Structure

```
MW Backup Link Monitor System/
├── run.py                          # Application entry point
├── Dockerfile                      # Container image definition
├── docker-compose.yml              # Production deployment
├── docker-compose-simulation.yaml  # Simulation mode with mock devices
├── requirements.txt                # Python dependencies
├── simulation-data.py              # Generates sample links for demo/testing
├── .gitignore
│
└── app/
    ├── __init__.py                 # Flask app factory, route registration, middleware
    ├── config.py                   # Configuration loading (secrets, DB URI)
    ├── extensions.py               # Shared Flask extensions (db, bcrypt, socketio, limiter)
    ├── models.py                   # SQLAlchemy models (14 models)
    ├── permissions.py              # RBAC: role defaults, decorators, permission checks
    │
    ├── routes/                     # API & page routes (Blueprints)
    │   ├── auth.py                 # Login, logout, password change, session info
    │   ├── dashboard.py            # KPI endpoint for dashboard
    │   ├── health.py               # /health and /ready probes
    │   ├── links.py                # CRUD, ping, export, external lookup
    │   ├── logs.py                 # System & ping log queries
    │   ├── notifications.py        # In-app notification management
    │   ├── pinglog.py              # Ping history log viewer
    │   ├── profile.py              # User profile & password self-service
    │   ├── roles.py                # Role & permission management
    │   ├── settings.py             # SMTP, jump server, app settings, external DB, webhooks
    │   ├── setup.py                # First-run setup wizard API
    │   └── users.py                # User CRUD, lock/unlock, reset password
    │
    ├── services/                   # Business logic layer
    │   ├── crypto_service.py       # Fernet encryption/decryption (PBKDF2 key derivation)
    │   ├── external_util_service.py# External MySQL utilization data sync
    │   ├── log_service.py          # System audit log writer
    │   ├── notification_service.py # Email, in-app, WebSocket, webhook delivery
    │   ├── ping_service.py         # Concurrent ping engine with flapping detection
    │   ├── scheduler.py            # APScheduler job management
    │   ├── ssh_service.py          # Low-level SSH command execution (Paramiko)
    │   └── ssh_session_manager.py  # Persistent SSH connection pool (singleton)
    │
    ├── templates/                  # Jinja2 HTML templates
    │   ├── base.html               # Main layout (sidebar, nav, notification bell)
    │   ├── dashboard.html          # Dashboard page
    │   ├── login.html              # Login page
    │   ├── setup.html              # Setup wizard page
    │   ├── users.html              # User management page
    │   ├── roles.html              # Role management page
    │   ├── logs.html               # Log viewer page
    │   └── emails/
    │       ├── link_event.html     # Link alert email template
    │       └── daily_report.html   # Daily summary email template
    │
    └── static/
        ├── css/
        │   ├── main.css            # Root CSS variables & global styles
        │   └── components.css      # Component-level styles
        └── js/
            ├── api.js              # API helper (fetch wrapper)
            ├── auth.js             # Login form logic
            ├── chart.min.js        # Chart.js library
            ├── charts.js           # Chart initialization
            ├── dashboard.js        # Dashboard KPI & WebSocket logic
            ├── dialog.js           # Link detail dialog
            ├── modal.js            # Link add/edit modal
            ├── notifications.js    # Notification bell & panel
            ├── pinglog.js          # Ping log viewer
            ├── roles.js            # Role management UI
            ├── settings.js         # Settings page (SMTP, jump server, app config)
            ├── setup.js            # Setup wizard UI
            ├── table.js            # Main link table (sort, filter, paginate)
            └── user.js             # User management UI
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (for containerized deployment)
- **`iputils-ping`** (Linux) or native `ping` (Windows/macOS) for local development
- (Optional) **MySQL/MariaDB** for external utilization data

### Local Development

```bash
# 1. Clone the repository
git clone <repository-url>
cd "MW Backup Link Monitor System"

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python run.py
```

The application will start on **http://localhost:5000**. On first launch, you will be redirected to the [Setup Wizard](#initial-setup-wizard).

### Docker Deployment (Production)

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f app

# Stop
docker compose down
```

The production `docker-compose.yml` creates:
- A **named volume** `mw_backup_link_monitor_system` for persistent data (`/app/data`)
- A **custom bridge network** with a static IP (`172.20.0.2`) for the app container

> **Note:** The production compose file does not expose ports by default. Configure port mapping or a reverse proxy as needed for your environment.

### Simulation Mode

A simulation environment with 10 mock network devices is provided for demo and testing:

```bash
docker compose -f docker-compose-simulation.yaml up -d --build
```

This creates:
- The monitor app on `http://localhost:5000`
- 10 simulated devices (nginx containers) with IPs `172.20.0.3` – `172.20.0.12`
- Pre-populated test links pointing to the simulated devices

The simulation runs `simulation-data.py` on startup to seed the database with sample links.

---

## Initial Setup Wizard

On first launch, the application redirects all requests to `/setup`. The wizard guides you through:

| Step | Description |
|---|---|
| **1. Database** | Configure the application database connection (SQLite default, or MySQL/PostgreSQL) |
| **2. Admin Account** | Create the initial administrator user |
| **3. SMTP (Optional)** | Configure email relay for alert notifications |
| **4. Jump Server (Optional)** | Configure an SSH bastion host for pinging remote devices |

Setup generates a `secrets.json` file in `data/secrets/` containing:
- A cryptographically random `secret_key`
- Encrypted database configuration

Once setup is complete, the wizard is permanently locked — all subsequent requests to `/setup` redirect to `/login`.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-this-to-a-random-secret-key` | Flask secret key for session signing. **Must be changed in production.** |
| `DATABASE_URL` | `sqlite:///:memory:` | SQLAlchemy database URI (overridden by `secrets.json` if present) |
| `FLASK_ENV` | `production` | Set to `development` for debug mode |
| `LOG_LEVEL` | `INFO` | Python logging level |

### Application Settings

Configurable via the Settings page (`/api/settings/app`):

| Setting | Default | Description |
|---|---|---|
| `ping_interval_seconds` | `60` | Seconds between automated ping cycles |
| `ping_count` | `3` | Number of ICMP echo requests per ping |
| `ping_timeout_seconds` | `2` | Timeout in seconds for each ping |
| `ping_concurrency` | `10` | Maximum concurrent ping threads |
| `consecutive_timeout_alert_threshold` | `5` | Consecutive timeouts before alerting |
| `util_warning_threshold_pct` | `70.0` | Global utilization warning threshold (%) |
| `util_critical_threshold_pct` | `90.0` | Global utilization critical threshold (%) |
| `session_timeout_minutes` | `480` | User session inactivity timeout (8 hours) |
| `daily_report_hour` | `8` | Hour (UTC) for daily summary email |
| `daily_report_minute` | `0` | Minute for daily summary email |

### Secrets Management

Sensitive configuration is stored in `data/secrets/secrets.json` and encrypted at rest using Fernet symmetric encryption with PBKDF2-derived keys:

```json
{
  "secret_key": "<random-base64-key>",
  "db_config_encrypted": "<fernet-encrypted-json>"
}
```

Sensitive fields in the database (SMTP password, jump server password, external DB password) are individually encrypted using the application's `SECRET_KEY`.

---

## Core Concepts

### Link Lifecycle

Each monitored link represents a physical microwave or fiber connection between two sites:

```
┌──────────┐     MW/Fiber Link      ┌──────────┐
│  Site A   │◄─────────────────────►│  Site B   │
│ (Source)  │    MW IP: x.x.x.x     │  (Sink)  │
└──────────┘                        └──────────┘
```

A link has the following attributes:
- **Link ID** — Unique identifier (e.g., `MW_LINK_001`)
- **Leg Name** — Network segment/region (e.g., `NORTH`, `SOUTH`)
- **MW IP** — The IP address to ping for reachability
- **Site A / Site B** — Endpoint identifiers
- **Link Type** — `microwave` or `fiber`

### Ping Cycle

The system runs automated ping cycles at a configurable interval:

```
┌─────────────┐
│  Scheduler   │ ──── triggers every N seconds
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│              Ping Cycle                          │
│                                                  │
│  1. Emit WS event: ping_cycle_start              │
│  2. Fetch all active links                       │
│  3. Spawn ThreadPoolExecutor (10 workers)        │
│  4. Each worker:                                 │
│     a. Try SSH (jump server) → else local ping   │
│     b. Parse output (reachable, latency, loss)   │
│     c. Persist PingResult + update LinkStatus    │
│     d. Emit WS event: link_status_update         │
│  5. Emit WS event: ping_cycle_complete           │
│  6. Emit WS event: kpi_update                   │
└─────────────────────────────────────────────────┘
```

### Flapping Detection

The system detects **flapping** — rapid oscillation between UP and DOWN states — to prevent alert storms:

| Parameter | Value | Description |
|---|---|---|
| `FLAPPING_TRANSITION_COUNT` | `5` | State changes to trigger flapping |
| `FLAPPING_WINDOW_MINUTES` | `10` | Time window for counting transitions |
| `FLAPPING_STABLE_CYCLES` | `2` | Consecutive stable pings to exit flapping |

When a link enters flapping state:
1. A `FLAPPING` event is logged
2. A critical notification is sent
3. Individual UP/DOWN events are suppressed until the link stabilises
4. After `FLAPPING_STABLE_CYCLES` consecutive successful pings, the link exits flapping

### Utilization Monitoring

The system tracks two utilization dimensions:

| Dimension | Source | Description |
|---|---|---|
| **MW Utilization** | External DB | Microwave link utilization percentage |
| **LEG Utilization** | External DB | Aggregate leg/segment utilization |

Thresholds can be set globally or overridden per-link:
- **Warning** (default 70%) → Status becomes `HIGH`
- **Critical** (default 90%) → Alert notification sent

### Notification System

The notification pipeline delivers alerts across four channels:

```
Event Trigger
     │
     ├──► In-App Notification (stored in DB, pushed via WebSocket)
     │
     ├──► Email (SMTP, with Outlook threading support)
     │        └── Uses Thread-Index headers for DOWN→RECOVERED threading
     │
     ├──► Webhook (generic JSON or Slack-formatted payloads)
     │
     └──► WebSocket (real-time push to connected clients)
```

**Cooldown timers** prevent duplicate alerts:

| Event | Cooldown |
|---|---|
| `mw_link_down` | 30 minutes |
| `mw_link_flapping` | 30 minutes |
| `consecutive_timeouts` | 1 hour |
| `leg_util_high` | 1 hour |
| `leg_util_near_cap` | 30 minutes |
| `mw_util_high` | 1 hour |
| `mw_link_recovered` | No cooldown (always fires) |

---

## Role-Based Access Control (RBAC)

Three built-in roles with granular permissions:

| Permission | Admin | Operator | Viewer |
|---|---|---|---|
| `links.view` | ✅ | ✅ | ✅ |
| `links.add` | ✅ | ✅ | ❌ |
| `links.edit` | ✅ | ✅ | ❌ |
| `links.delete` | ✅ | ❌ | ❌ |
| `links.ping` | ✅ | ✅ | ❌ |
| `links.export` | ✅ | ✅ | ✅ |
| `users.view` | ✅ | ✅ | ❌ |
| `users.add` | ✅ | ❌ | ❌ |
| `users.edit` | ✅ | ❌ | ❌ |
| `users.delete` | ✅ | ❌ | ❌ |
| `users.reset_password` | ✅ | ❌ | ❌ |
| `users.manage_permissions` | ✅ | ❌ | ❌ |
| `config.view` | ✅ | ❌ | ❌ |
| `config.edit_smtp` | ✅ | ❌ | ❌ |
| `config.edit_jumpserver` | ✅ | ❌ | ❌ |
| `config.edit_app` | ✅ | ❌ | ❌ |
| `logs.view_system` | ✅ | ✅ | ❌ |
| `logs.view_ping` | ✅ | ✅ | ✅ |
| `logs.export` | ✅ | ✅ | ❌ |
| `notifications.view_own` | ✅ | ✅ | ✅ |
| `notifications.edit_own` | ✅ | ✅ | ✅ |
| `notifications.manage_all` | ✅ | ❌ | ❌ |

Permissions are stored in the `RolePermission` table and can be customized via the Roles management page.

---

## API Reference

All API routes return JSON. Authentication is via session cookies (`mw_session`).

### Authentication API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Authenticate user, returns session cookie |
| `POST` | `/api/auth/logout` | End session |
| `GET` | `/api/auth/me` | Get current user info and permissions |
| `POST` | `/api/auth/change-password` | Change own password |

### Dashboard API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard/kpi` | Get real-time KPIs (total links, reachable, unreachable, availability, uptime) |

### Links API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/links` | List links (paginated, with `status`, `leg`, `search` filters) |
| `POST` | `/api/links` | Create a new link |
| `GET` | `/api/links/<id>` | Get link details with ping history |
| `PUT` | `/api/links/<id>` | Update a link |
| `DELETE` | `/api/links/<id>` | Delete a link |
| `POST` | `/api/links/<id>/ping` | Trigger a manual ping |
| `POST` | `/api/links/<id>/metrics` | Submit utilization metrics |
| `GET` | `/api/links/export` | Export links to CSV |
| `GET` | `/api/links/legs` | List distinct leg names |
| `POST` | `/api/links/lookup` | Look up link data from external DB |
| `POST` | `/api/links/lookup-leg` | Look up LEG data from external DB |

### Users API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users` | List all users |
| `POST` | `/api/users` | Create a new user |
| `PUT` | `/api/users/<id>` | Update a user |
| `DELETE` | `/api/users/<id>` | Delete a user |
| `POST` | `/api/users/<id>/reset-password` | Reset a user's password |
| `POST` | `/api/users/<id>/lock` | Lock a user account |
| `POST` | `/api/users/<id>/unlock` | Unlock a user account |

### Roles API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/roles` | List all roles with permissions |
| `POST` | `/api/roles` | Create a custom role |
| `PUT` | `/api/roles/<id>` | Update role permissions |
| `DELETE` | `/api/roles/<id>` | Delete a custom role |

### Notifications API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/notifications` | Get user's notifications (paginated) |
| `POST` | `/api/notifications/<id>/read` | Mark a notification as read |
| `POST` | `/api/notifications/read-all` | Mark all notifications as read |
| `GET` | `/api/notifications/subscriptions` | Get notification subscriptions |
| `PUT` | `/api/notifications/subscriptions` | Update notification subscriptions |

### Settings API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/settings/smtp` | Get SMTP configuration |
| `PUT` | `/api/settings/smtp` | Update SMTP configuration |
| `POST` | `/api/settings/smtp/test` | Send a test email |
| `GET` | `/api/settings/jumpserver` | Get jump server configuration |
| `PUT` | `/api/settings/jumpserver` | Update jump server configuration |
| `POST` | `/api/settings/jumpserver/test` | Test jump server SSH connection |
| `GET` | `/api/settings/app` | Get application settings |
| `PUT` | `/api/settings/app` | Update application settings |
| `GET` | `/api/settings/external-db` | Get external DB configuration |
| `PUT` | `/api/settings/external-db` | Update external DB configuration |
| `POST` | `/api/settings/external-db/test` | Test external DB connection |
| `GET` | `/api/settings/webhooks` | List webhook configurations |
| `POST` | `/api/settings/webhooks` | Create a webhook |
| `PUT` | `/api/settings/webhooks/<id>` | Update a webhook |
| `DELETE` | `/api/settings/webhooks/<id>` | Delete a webhook |

### Logs API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/logs` | Query system logs (filterable by category, event, date range) |
| `GET` | `/api/logs/export` | Export system logs to CSV |

### Health & Readiness API

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Liveness probe — always returns `200 OK` |
| `GET` | `/ready` | None | Readiness probe — checks DB and scheduler. Returns `503` if not ready |

---

## WebSocket Events

The application uses Socket.IO for real-time updates. All events are broadcast to connected clients:

| Event | Direction | Payload | Description |
|---|---|---|---|
| `ping_cycle_start` | Server → Client | `{ total, started_at }` | Ping cycle has begun |
| `ping_cycle_complete` | Server → Client | `{ total, completed_at }` | Ping cycle finished |
| `link_status_update` | Server → Client | `{ id, link_id, leg_name, status, latency_ms, latest_metric }` | Single link status changed |
| `kpi_update` | Server → Client | `{ total_links, mw_reachable, mw_unreachable, high_utilization, link_availability_24h, next_ping_time }` | Dashboard KPIs refreshed |
| `notification_new` | Server → Client | `{ notification, unread_count }` | New in-app notification |

---

## Scheduled Jobs

The application runs three background jobs via APScheduler:

| Job ID | Trigger | Default | Description |
|---|---|---|---|
| `ping_cycle` | Interval | Every 60s | Pings all active links concurrently |
| `external_util_refresh` | Interval | Every 24h | Syncs utilization data from external MySQL DB |
| `daily_report` | Cron | 08:00 UTC | Sends daily summary email to all active users |

All schedules are **live-reloadable** — changing settings in the UI immediately reschedules the jobs without restarting the application.

---

## Jump Server (SSH Gateway)

For networks where monitored devices are not directly reachable, the system supports pinging via an SSH bastion host:

```
┌───────────┐      SSH       ┌──────────────┐     ICMP      ┌──────────┐
│ MW Monitor │──────────────►│  Jump Server  │──────────────►│ MW Device│
│ Container  │  (Paramiko)   │  (Bastion)    │  (ping cmd)   │ x.x.x.x │
└───────────┘               └──────────────┘               └──────────┘
```

**Key features:**
- **Persistent connection** — A singleton `SSHSessionManager` maintains a single long-lived SSH session
- **Thread-safe** — Uses Paramiko's `exec_command` (separate channel per call) for concurrent pings
- **Auto-reconnect** — Reconnects automatically if the session drops or configuration changes
- **Invalidation** — Jump server config changes trigger immediate session invalidation

Configure the jump server via **Settings → Jump Server** or during initial setup.

---

## External Utilization Database

The system can enrich link data with utilization metrics from an external MySQL/MariaDB database (typically a P&Q or NMS export):

**Expected tables:**

| Table | Key Columns |
|---|---|
| `pandq_mw_link_max_week_utilization` | `Link_Name`, `AVG_MAX_Util_RxTx_perc`, `MW_Link_Capacity`, `XPIC_MW_Link_Capacity`, `Source_NE_Card`, `Sink_NE_Card` |
| `pandq_leg_max_week_utilization` | `LEG_Name`, `AVG_MAX_MBitRate`, `Interface_Speed_Min`, `Interface_Speed_Max`, `Sub_LEG_Count` |

Configure the external database via **Settings → External Database**.

---

## Email Notifications

Email alerts are sent via SMTP and include:

- **Severity-aware subject lines** with emoji indicators:
  - 🔴 `[DOWN]` — Link unreachable
  - 🟠 `[FLAPPING]` — Link oscillating
  - 🟢 `[RESOLVED]` — Link recovered
  - 🟡 `[HIGH UTIL]` — Utilization warning
  - 🔴 `[NEAR CAPACITY]` — Utilization critical
  - ⏱️ `[TIMEOUTS]` — Consecutive ping failures

- **Outlook email threading** — DOWN and RECOVERED emails for the same link are threaded together using `Thread-Index`, `In-Reply-To`, and `References` headers

- **HTML email templates** — Rich HTML emails with link details, timestamps, and status information

- **Daily summary reports** — Automated daily overview of all link statuses and recent events

Configure SMTP via **Settings → SMTP** or during initial setup.

---

## Webhook Integrations

The system can push alert payloads to external endpoints:

**Generic Webhook** payload:
```json
{
  "event": "mw_link_down",
  "severity": "critical",
  "message": "Link MW_LINK_001 is down.",
  "link_id": "MW_LINK_001",
  "leg_name": "NORTH",
  "timestamp": "2024-01-15T12:30:00Z"
}
```

**Slack** payload (auto-formatted with attachments, color coding, and emoji):
```json
{
  "text": "🔴 *Mw Link Down* — NORTH",
  "attachments": [{
    "color": "danger",
    "text": "Link MW_LINK_001 is down.",
    "fields": [
      { "title": "Event", "value": "mw_link_down", "short": true },
      { "title": "Severity", "value": "CRITICAL", "short": true },
      { "title": "Link ID", "value": "MW_LINK_001", "short": true }
    ]
  }]
}
```

Configure webhooks via **Settings → Webhooks**.

---

## Security

| Feature | Implementation |
|---|---|
| **Password Hashing** | Bcrypt via Flask-Bcrypt |
| **Encryption at Rest** | Fernet symmetric encryption with PBKDF2HMAC key derivation (100,000 iterations) |
| **Session Cookies** | `HttpOnly`, `SameSite=Strict`, `Secure` (in production) |
| **Rate Limiting** | 200 requests/minute per IP (Flask-Limiter, in-memory storage) |
| **Account Lockout** | Configurable failed login threshold with automatic lockout |
| **Forced Password Change** | Admin can force users to change password on next login |
| **Session Timeout** | Configurable inactivity timeout (default 8 hours) |
| **Secret Key Validation** | App refuses to start in production with the default secret key (if secrets.json exists) |
| **Setup Lock** | Setup wizard is permanently disabled after initial completion |

---

## Data Persistence

All application data is stored under the `data/` directory:

```
data/
├── instance/          # SQLite database file (when using SQLite)
└── secrets/
    └── secrets.json   # Encrypted application secrets
```

In Docker, this directory is mounted as a **named volume** (`mw_backup_link_monitor_system`) to persist data across container restarts.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|---|---|
| **App redirects to `/setup` loop** | The `secrets.json` file is missing or corrupted. Check `data/secrets/`. |
| **`RuntimeError: SECRET_KEY must be set`** | In production, the `SECRET_KEY` environment variable must be set to a strong random value if secrets.json exists. |
| **Pings show 100% packet loss** | Verify the container has `iputils-ping` installed and the target IPs are reachable from the container network. |
| **SSH jump server connection fails** | Check jump server credentials in Settings. Verify network connectivity to the bastion host. |
| **External DB sync fails** | Verify the external database credentials and ensure the required tables exist. Check **Settings → External Database → Test Connection**. |
| **Email notifications not sending** | Verify SMTP settings. Use **Settings → SMTP → Send Test Email** to diagnose. |
| **WebSocket not connecting** | Ensure the reverse proxy (if any) supports WebSocket upgrades. Flask-SocketIO uses Eventlet. |

### Logs

- **Application logs** are output to stdout/stderr (viewable via `docker compose logs`)
- **System audit logs** are stored in the `SystemLog` database table and viewable via **Logs** in the UI
- **APScheduler logs** are set to `ERROR` level to suppress expected "skipped: maximum instances" warnings

### Health Checks

Use the built-in health endpoints for monitoring:

```bash
# Liveness (always 200)
curl http://localhost:5000/health

# Readiness (checks DB + scheduler)
curl http://localhost:5000/ready
```

---

## License

This project is proprietary software developed for internal telecom network operations use.
