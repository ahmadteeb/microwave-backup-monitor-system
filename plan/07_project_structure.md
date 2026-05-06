# 07 — Project Folder Structure

This document details the complete file layout of the application. It lists the exact purpose of each file, its key dependencies/imports, and the primary programming interfaces (classes, functions, or JavaScript modules) it exposes.

---

## 1. Directory Tree Overview

```
/
├── run.py
├── requirements.txt
├── .env.example
├── README.md
├── instance/
│   └── (Auto-created database storage)
├── plan/
│   ├── 00_overview.md
│   ├── 01_database.md
│   ├── 02_api_routes.md
│   ├── 03_ssh_ping_service.md
│   ├── 04_auth_and_rbac.md
│   ├── 05_notifications.md
│   ├── 06_frontend.md
│   ├── 07_project_structure.md
│   └── 08_implementation_order.md
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── extensions.py
│   ├── permissions.py
│   ├── config.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── setup.py
│   │   ├── dashboard.py
│   │   ├── links.py
│   │   ├── users.py
│   │   ├── notifications.py
│   │   ├── logs.py
│   │   ├── settings.py
│   │   └── profile.py
│   └── services/
│       ├── ssh_service.py
│       ├── ping_service.py
│       ├── metric_service.py
│       ├── scheduler.py
│       ├── notification_service.py
│       ├── crypto_service.py
│       └── log_service.py
└── frontend/
    ├── login.html
    ├── setup.html
    ├── change_password.html
    ├── index.html
    ├── links.html
    ├── users.html
    ├── notifications.html
    ├── logs.html
    ├── settings.html
    ├── profile.html
    ├── css/
    │   ├── main.css
    │   ├── components.css
    │   ├── table.css
    │   ├── modal.css
    │   └── forms.css
    └── js/
        ├── auth.js
        ├── dashboard.js
        ├── table.js
        ├── modal.js
        ├── users.js
        ├── notifications.js
        ├── logs.js
        ├── settings.js
        ├── charts.js
        └── utils.js
```

---

## 2. Detailed Backend Module Definitions

### 2.1 Core Application Layer

#### `run.py`
-   **Purpose**: Main entry point file used to run the application server.
-   **Key Imports**: `create_app` from `app` package.
-   **Exposed Interfaces**: Launches the server using `app.run()`.

#### `app/__init__.py`
-   **Purpose**: Implements the Flask Application Factory pattern, initializes extensions, starts the background scheduler, and registers API blueprints.
-   **Key Imports**: `Flask`, `db`, `bcrypt`, `scheduler` from `app.extensions`, `init_scheduler` from `app.services.scheduler`.
-   **Exposed Interfaces**: `create_app(config_class)` returns a configured Flask app instance.

#### `app/extensions.py`
-   **Purpose**: Instantiates application-wide extension singletons, preventing circular import issues.
-   **Key Imports**: `SQLAlchemy`, `Bcrypt`, `APScheduler`.
-   **Exposed Interfaces**: Singletons: `db`, `bcrypt`, `scheduler`.

#### `app/permissions.py`
-   **Purpose**: Implements the RBAC permission check algorithm and route-protection decorators.
-   **Key Imports**: `wraps` from `functools`, `current_user` or `session` from `flask`.
-   **Exposed Interfaces**:
    -   `has_permission(user_id, permission_key) -> bool`
    -   `require_permission(permission_key)` (Decorator function checking granular permissions).

#### `app/config.py`
-   **Purpose**: Configures environment variables, loads parameters from `.env`, and sets database locations.
-   **Key Imports**: `os`, `dotenv`.
-   **Exposed Interfaces**: `Config` class containing static parameters like `SECRET_KEY` and `SQLALCHEMY_DATABASE_URI`.

---

### 2.2 API Blueprints (`app/routes/`)

#### `app/routes/auth.py`
-   **Purpose**: Handles authentication routes: login, logout, password resets, and session management.
-   **Key Imports**: `Blueprint`, `session`, `request`, `User`, `db`.
-   **Exposed Interfaces**: `auth_bp` blueprint containing routes `/api/auth/login`, `/api/auth/logout`, and `/api/auth/change-password`.

#### `app/routes/setup.py`
-   **Purpose**: Handles the initial setup wizard, creating the admin user and validating initial SMTP and Jump Server configurations.
-   **Key Imports**: `Blueprint`, `SetupState`, `User`, `db`, `SmtpConfig`, `JumpServer`.
-   **Exposed Interfaces**: `setup_bp` blueprint containing `/api/setup/complete`, `/api/setup/test-smtp`, and `/api/setup/test-jumpserver`.

#### `app/routes/dashboard.py`
-   **Purpose**: Serves aggregated system statistics and paginated link tables to the dashboard workspace.
-   **Key Imports**: `Blueprint`, `Link`, `LinkStatus`.
-   **Exposed Interfaces**: `dashboard_bp` blueprint containing `/api/dashboard/summary` and `/api/dashboard/links`.

#### `app/routes/links.py`
-   **Purpose**: Handles CRUD operations for microwave links and generates CSV inventory exports.
-   **Key Imports**: `Blueprint`, `Link`, `LinkStatus`, `db`.
-   **Exposed Interfaces**: `links_bp` blueprint containing `/api/links` (CRUD and custom diagnostic endpoints).

#### `app/routes/users.py`
-   **Purpose**: Handles user account administration, password resets, and granular permission overrides.
-   **Key Imports**: `Blueprint`, `User`, `UserPermission`, `db`.
-   **Exposed Interfaces**: `users_bp` blueprint containing endpoints `/api/users` (CRUD, permission controls, and overrides).

#### `app/routes/notifications.py`
-   **Purpose**: Renders user alert inboxes and manages subscription preferences.
-   **Key Imports**: `Blueprint`, `InAppNotification`, `NotificationSubscription`.
-   **Exposed Interfaces**: `notifications_bp` blueprint containing `/api/notifications` (CRUD and unread alert count endpoints).

#### `app/routes/logs.py`
-   **Purpose**: Serves system audit and ping diagnostic logs.
-   **Key Imports**: `Blueprint`, `SystemLog`, `PingResult`.
-   **Exposed Interfaces**: `logs_bp` blueprint containing `/api/logs/system` and `/api/logs/ping`.

#### `app/routes/settings.py`
-   **Purpose**: Handles system settings panel: updates configurations for SMTP, Jump Server, and App thresholds.
-   **Key Imports**: `Blueprint`, `SmtpConfig`, `JumpServer`, `AppSettings`, `db`.
-   **Exposed Interfaces**: `settings_bp` blueprint containing endpoints `/api/settings/smtp`, `/api/settings/jumpserver`, and `/api/settings/app`.

#### `app/routes/profile.py`
-   **Purpose**: Serves self-service profile and password modification.
-   **Key Imports**: `Blueprint`, `User`, `db`.
-   **Exposed Interfaces**: `profile_bp` blueprint containing `/api/profile` endpoints.

---

### 2.3 System Services (`app/services/`)

#### `app/services/ssh_service.py`
-   **Purpose**: Establishes secure terminal connections to remote devices, tunnelled through an intermediate Jump Server using Paramiko.
-   **Key Imports**: `paramiko`.
-   **Exposed Interfaces**: `SSHService` class exposing `connect()`, `disconnect()`, and `execCommand(cmd)`.

#### `app/services/ping_service.py`
-   **Purpose**: Orchestrates background reachability sweeps, parsing ping command outputs and updating link statuses.
-   **Key Imports**: `SSHService`, `PingResult`, `LinkStatus`, `db`.
-   **Exposed Interfaces**:
    -   `run_ping_cycle()` (Sweep of all active microwave links)
    -   `ping_target(ip)` (Performs an on-demand manual ping)

#### `app/services/metric_service.py`
-   **Purpose**: Connects to remote routers to poll traffic utilization metrics, parsing CLI command outputs.
-   **Key Imports**: `SSHService`, `MetricSnapshot`, `LinkStatus`.
-   **Exposed Interfaces**: `harvest_metrics()` (Queries routers and logs metrics snapshot records).

#### `app/services/scheduler.py`
-   **Purpose**: Runs the background APScheduler instance and manages background job timings.
-   **Key Imports**: `BackgroundScheduler` from `apscheduler`.
-   **Exposed Interfaces**: `init_scheduler(app)` (Configures background jobs and timing parameters).

#### `app/services/notification_service.py`
-   **Purpose**: Handles alert routing, creating in-app alerts and sending SMTP emails to subscribed users.
-   **Key Imports**: `SmtpConfig`, `InAppNotification`, `NotificationSubscription`, `smtplib`.
-   **Exposed Interfaces**: `dispatch_alert(event_key, link_id, message_text)` (Handles alert routing and delivery).

#### `app/services/crypto_service.py`
-   **Purpose**: Provides symmetric cryptography to secure database secrets at rest.
-   **Key Imports**: `Fernet` from `cryptography.fernet`.
-   **Exposed Interfaces**: `CryptoService` class exposing `encrypt(plain)` and `decrypt(cipher)` methods.

#### `app/services/log_service.py`
-   **Purpose**: Provides unified system audit logging across all application components.
-   **Key Imports**: `SystemLog`, `db`, `request`.
-   **Exposed Interfaces**: `write_log(category, event, actor, target, detail_dict)` (Writes audit trails to the database).

---

## 3. Client Frontend Definitions

### 3.1 Static Pages (`frontend/`)
-   `login.html`: Dedicated login page with authentication forms and error blocks.
-   `setup.html`: First-boot setup wizard form.
-   `change_password.html`: Redirection target for forced password changes.
-   `index.html`: NOC Dashboard. Renders KPI cards, active link lists, and terminal logs.
-   `links.html`: Provides administrative tools for link configurations and settings.
-   `users.html`: User account and permissions override settings console.
-   `notifications.html`: User alerts listing inbox.
-   `logs.html`: Audit records and ping logs listing panel.
-   `settings.html`: System-wide SMTP, Jump Server, and application settings panels.
-   `profile.html`: Personal configuration screen.

### 3.2 Pure CSS Styling (`frontend/css/`)
-   `main.css`: Sets base margins, imports standard fonts, and defines system-wide CSS variables.
-   `components.css`: Contains shared styles for buttons, badges, status indicators, and tabs.
-   `table.css`: Responsive, high-density table layouts optimized for large inventories.
-   `modal.css`: Full-screen overlay panels and confirmation dialog boxes.
-   `forms.css`: Standard styles for form fields, layout groups, and field validation indicators.

### 3.3 Vanilla JS Modules (`frontend/js/`)
-   `auth.js`: Manages login attempts and redirection.
-   `dashboard.js`: Orchestrates KPI loading, ping logs, and countdown updates.
-   `table.js`: Controls paginated tables, row toggles, and detail templates.
-   `modal.js`: Opens form views and executes validation routines.
-   `users.js`: Connects user configurations and override selectors.
-   `notifications.js`: Fetches personal notifications and toggles subscriptions.
-   `logs.js`: Integrates log tables, multi-column search, and csv downloader.
-   `settings.js`: Controls connection testing triggers and form validation.
-   `charts.js`: Renders radial utilization gauges and history sparklines.
-   `utils.js`: Stores common formats, badges, progress bars, and debouncers.
