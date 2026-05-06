# 08 — Implementation Order

This document outlines the structured 12-phase execution sequence to implement the Microwave Backup Link Monitor. Each phase is defined with an explicit objective, the targeted source files, and the concrete acceptance criteria required before proceeding to the next step.

---

## Phase 1: Database Models and Initial Seeding
-   **Objective**: Define the SQLAlchemy database schema, establish cascade relationships, and implement the initial seeding logic.
-   **Files Touched**:
    -   `app/models.py` (All declarative models)
    -   `app/extensions.py` (Instantiates the Database singleton)
    -   `app/__init__.py` (Bootstraps database context)
-   **Acceptance Criteria**:
    -   Running Flask db initialization commands successfully creates the SQLite database file inside the `instance` directory.
    -   All tables (`user`, `link`, `ping_result`, etc.) are generated with their defined constraints, indexes, and primary keys.
    -   Database seed checks successfully insert default configurations into `SetupState` and `AppSettings` if they are empty.

---

## Phase 2: Setup Wizard Backend API
-   **Objective**: Implement the backend routing endpoints for the first-boot installation sequence.
-   **Files Touched**:
    -   `app/routes/setup.py` (Setup routes blueprint)
    -   `app/services/crypto_service.py` (Fernet encryption implementation)
    -   `app/__init__.py` (Registers setup blueprint)
-   **Acceptance Criteria**:
    -   `POST /api/setup/test-smtp` successfully establishes an SMTP connection handshake and sends a test email using the provided parameters.
    -   `POST /api/setup/test-jumpserver` successfully establishes an SSH connection handshake using the provided credentials.
    -   `POST /api/setup/complete` creates the administrator account with a hashed password, saves encrypted SMTP/Jump Server credentials to the database, and flags `is_complete` in `SetupState` as `True`.

---

## Phase 3: Authentication and RBAC Logic
-   **Objective**: Implement session-based authentication, password hashing, and user permissions verification logic.
-   **Files Touched**:
    -   `app/permissions.py` (Granular permissions checks and route decorators)
    -   `app/routes/auth.py` (Login, logout, and credential endpoints)
    -   `app/__init__.py` (Registers auth blueprints and session validation hooks)
-   **Acceptance Criteria**:
    -   `POST /api/auth/login` validates credentials against password hashes and initializes the signed session cookie.
    -   Failed logins increment the user's failed attempts counter, locking the account for 15 minutes after 5 consecutive failures.
    -   Granular permission decorators successfully protect API endpoints, returning an HTTP `403 Forbidden` response if the user does not have the required permission.

---

## Phase 4: Link CRUD API Endpoints
-   **Objective**: Implement RESTful CRUD API routes for link configurations.
-   **Files Touched**:
    -   `app/routes/links.py` (CRUD blueprint)
    -   `app/__init__.py` (Registers links blueprint)
-   **Acceptance Criteria**:
    -   `GET /api/links` returns a paginated list of registered links, supporting text search, status filters, and regional groupings.
    -   `POST /api/links` validates inputs (such as IPv4 address syntax) and creates new link configurations, returning an error if the Link ID is already registered.
    -   `PUT /api/links/<id>` updates existing link properties, and `DELETE /api/links/<id>` purges the configuration and cascades to delete all historical logs.

---

## Phase 5: SSH Ping Service and Background Scheduler
-   **Objective**: Integrate the Paramiko SSH client wrapper, implement CLI parsing rules, and set up background scheduler sweeps.
-   **Files Touched**:
    -   `app/services/ssh_service.py` (Pre-existing Paramiko client wrapper)
    -   `app/services/ping_service.py` (Ping orchestrator and CLI parser)
    -   `app/services/scheduler.py` (Background scheduler job definition)
    -   `app/__init__.py` (Launches background scheduler threads)
-   **Acceptance Criteria**:
    -   Background ping cycles successfully parse terminal outputs to extract latency metrics and packet loss percentages.
    -   The background scheduler runs sweeps sequentially at the configured interval, utilizing a concurrency lock to prevent overlapping runs.
    -   `POST /api/links/<id>/ping` executes an immediate manual ping check in a separate thread, returning raw terminal output to the user.

---

## Phase 6: Notification Routing and SMTP Integration
-   **Objective**: Implement the system alert routing engine, handling in-app alerts and outgoing SMTP emails.
-   **Files Touched**:
    -   `app/services/notification_service.py` (Alert routing and email delivery)
    -   `app/routes/notifications.py` (User notifications blueprint)
-   **Acceptance Criteria**:
    -   System alerts successfully create in-app notifications in the database and send HTML emails to subscribed, active users.
    -   The system enforces anti-spam rules: throttling down notifications, applying hysteresis limits to traffic utilization thresholds, and implementing reminder limits on consecutive failures.
    -   `GET /api/notifications` serves paginated list views of alerts, and `POST /api/notifications/<id>/read` marks alerts as read.

---

## Phase 7: System Logging and Security Audits
-   **Objective**: Implement a write-only audit logging engine to record security, authentication, and configuration changes.
-   **Files Touched**:
    -   `app/services/log_service.py` (Logs generator)
    -   `app/routes/logs.py` (System logs blueprint)
-   **Acceptance Criteria**:
    -   Calling `write_log()` writes log entries containing actor, target, type, and JSON metadata directly to the database.
    -   Authentication, creation, update, and deletion actions successfully trigger security audit logs.
    -   `GET /api/logs/system` serves paginated lists of audit logs, while `GET /api/logs/system/export` generates downloadable CSV files.

---

## Phase 8: Dashboard Shell and Visual Theme
-   **Objective**: Build the core HTML structures, layout grids, and CSS style rules.
-   **Files Touched**:
    -   `frontend/index.html` (NOC Dashboard shell)
    -   `frontend/css/main.css` (Base layout grids and visual variables)
    -   `frontend/css/components.css` (Button and visual component styles)
-   **Acceptance Criteria**:
    -   Opening the dashboard page renders a high-density, dark NOC interface layout.
    -   The left navigation sidebar and top global status bar are styled correctly using the defined color palette.
    -   All typography uses the Inter and JetBrains Mono system font files.

---

## Phase 9: Link Listings and Interactive Forms Frontend
-   **Objective**: Implement active link listings tables, collapsible details panels, and configuration modals.
-   **Files Touched**:
    -   `frontend/js/table.js` (Paginated tables and detail panels controller)
    -   `frontend/js/modal.js` (Link configuration forms and client-side validation)
    -   `frontend/js/charts.js` (Renders gauges and traffic trend charts)
-   **Acceptance Criteria**:
    -   The main link listing table displays links with status badges and traffic utilization bars.
    -   Clicking on a row slides open the collapsible detail panel, rendering utilization gauges and historical trend sparklines.
    -   The Add and Edit link modal validates inputs on submission and refreshes the table upon successful API responses.

---

## Phase 10: User Accounts Administration Frontend
-   **Objective**: Build the user administration table, accounts wizard, and permissions override controls.
-   **Files Touched**:
    -   `frontend/users.html` (User accounts page)
    -   `frontend/js/users.js` (User listing and permissions controller)
-   **Acceptance Criteria**:
    -   The user accounts table displays registered accounts and current account locks.
    -   The Add and Edit user modal enables profile updates and password resets.
    -   The permissions override panel renders granular access controls with toggles and default inheritance badges.

---

## Phase 11: System Console, Profiles, and Alert Inbox Frontend
-   **Objective**: Implement settings panels, personal profiles, and notification lists.
-   **Files Touched**:
    -   `frontend/settings.html` & `frontend/js/settings.js` (Settings panels)
    -   `frontend/profile.html` & `frontend/js/utils.js` (User profiles)
    -   `frontend/notifications.html` & `frontend/js/notifications.js` (Alert listing inbox)
-   **Acceptance Criteria**:
    -   The settings console enables updates and test Handshakes for SMTP and Jump Server settings.
    -   The user profile page enables personal contact updates and password changes.
    -   The notifications inbox displays unread alert counts and allows dismissing alert records.

---

## Phase 12: End-to-End Diagnostics Test
-   **Objective**: Perform comprehensive diagnostic testing of the system using a real Jump Server connection.
-   **Files Touched**: All system modules.
-   **Acceptance Criteria**:
    -   The setup wizard configures the system on first boot, successfully establishing gateway SSH tunnels.
    -   Background cycles periodically execute reachability sweeps and gather metrics from remote routers.
    -   Simulated network outages successfully trigger in-app alerts and send notification emails to subscribed operators.
