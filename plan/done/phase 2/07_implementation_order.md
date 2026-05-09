# 07 Implementation Order

## Phase 1 — New model additions + migration validation

### Goal
Add the new database models and fields without breaking the existing SQLite data.

### Files touched
- `/app/models.py`
- `/app/extensions.py`
- `/app/__init__.py`
- `/app/config.py`

### Acceptance conditions
- `db.create_all()` creates new tables for `SetupState`, `User`, `UserPermission`, `NotificationSubscription`, `InAppNotification`, `SmtpConfig`, `AppSettings`, `LinkStatus`, `SystemLog`.
- New fields on `Link`, `PingResult`, and `JumpServer` are added as nullable or with safe server defaults.
- Existing data in `Link`, `PingResult`, `MetricSnapshot`, and `JumpServer` remains accessible.
- No runtime errors occur when importing the app.

## Phase 2 — CryptoService + move encrypt/decrypt out of jumpserver.py

### Goal
Centralize encryption and support Fernet key migration.

### Files touched
- `/app/services/crypto_service.py`
- `/app/routes/jumpserver.py`
- `/app/services/ping_service.py` (if it decrypts jump server config)
- `/app/__init__.py` or `/app/config.py`

### Acceptance conditions
- `crypto_service.py` exposes `encrypt()` and `decrypt()`.
- It derives the key from `SECRET_KEY` using PBKDF2.
- It falls back to SHA-256 decryption if PBKDF2 fails.
- `app/routes/jumpserver.py` uses the shared service and no longer defines its own key helpers.
- Existing encrypted passwords can be decrypted when present.

## Phase 3 — log_service + write_log integration into existing routes

### Goal
Add centralized audit logging and wire it into core route operations.

### Files touched
- `/app/services/log_service.py`
- `/app/routes/links.py`
- `/app/routes/jumpserver.py`
- `/app/routes/dashboard.py`
- `/app/services/scheduler.py`
- `/app/services/ping_service.py`

### Acceptance conditions
- `write_log()` works without raising.
- Existing link add/edit/delete/manual ping operations write audit log entries.
- Scheduler cycle start, completion, and error events are logged.
- Jump server updates write `jumpserver_updated` logs.

## Phase 4 — Setup wizard backend

### Goal
Implement first-boot setup with admin creation, SMTP/jump server configuration, and initial settings seed.

### Files touched
- `/app/routes/setup.py`
- `/frontend/setup.html`
- `/frontend/js/auth.js`
- `/app/models.py`
- `/app/services/crypto_service.py`

### Acceptance conditions
- `/setup` loads the wizard page when `SetupState` is incomplete.
- `/api/setup/test-smtp` validates and connects without saving.
- `/api/setup/test-jumpserver` validates and connects without saving.
- `/api/setup/complete` creates the required DB rows and returns `redirect: /login`.

## Phase 5 — Auth + session + login_required on all existing routes

### Goal
Protect the app with authentication and session expiry.

### Files touched
- `/app/routes/auth.py`
- `/app/permissions.py`
- `/app/__init__.py`
- `/frontend/login.html`
- `/frontend/change_password.html`
- `/frontend/js/auth.js`
- `/frontend/js/utils.js`

### Acceptance conditions
- Users can log in and log out.
- Session data is stored in signed cookies.
- Session timeout is enforced from `AppSettings`.
- `@login_required` blocks unauthenticated access to API routes and redirects page routes to `/login`.

## Phase 6 — RBAC + require_permission on all routes + GET /api/auth/me

### Goal
Enforce role-based permissions and expose effective permissions to the frontend.

### Files touched
- `/app/permissions.py`
- `/app/routes/links.py`
- `/app/routes/dashboard.py`
- `/app/routes/jumpserver.py`
- `/app/routes/pinglog.py`
- `/frontend/js/table.js`
- `/frontend/index.html`

### Acceptance conditions
- `has_permission()` returns role defaults and honors `UserPermission` overrides.
- `@require_permission` returns `403` when access is denied.
- `/api/auth/me` returns the full permission map.
- UI elements are hidden or shown based on permission data.

## Phase 7 — User management backend

### Goal
Add admin-only CRUD, reset password, unlock, and permissions override.

### Files touched
- `/app/routes/users.py`
- `/app/models.py`
- `/app/services/log_service.py`
- `/frontend/index.html`
- `/frontend/js/users.js`

### Acceptance conditions
- Admins can list, create, update, delete, reset passwords, and unlock users.
- `users.manage_permissions` controls whether permission overrides are editable.
- User create seeds notification subscriptions.
- User actions generate appropriate audit logs.

## Phase 8 — Notification + SMTP service

### Goal
Add event-driven notifications, email delivery, and in-app bell badge.

### Files touched
- `/app/routes/notifications.py`
- `/app/services/notification_service.py`
- `/app/models.py`
- `/frontend/index.html`
- `/frontend/js/notifications.js`
- `/frontend/css/components.css`

### Acceptance conditions
- `check_ping_event()` and `check_util_event()` trigger the seven configured events.
- `send_notification()` creates `InAppNotification` rows and sends email attempts.
- `ping_service_error` events log and notify correctly.
- The bell badge updates every 60 seconds from `/api/notifications/unread-count`.

## Phase 9 — Settings + profile backend

### Goal
Add SMTP, jump server, and application settings management plus user profile edits.

### Files touched
- `/app/routes/settings.py`
- `/app/routes/profile.py`
- `/frontend/js/settings.js`
- `/frontend/js/profile.js`
- `/frontend/index.html`
- `/app/services/log_service.py`

### Acceptance conditions
- `GET` and `PUT` settings endpoints work with masked password handling.
- Test actions for SMTP and jump server work.
- App settings updates are persisted and used by `scheduler.py` and `ping_service.py`.
- Users can edit their own profile and change passwords.

## Phase 10 — Full frontend integration

### Goal
Clean up `/frontend/index.html`, add SPA sections, and connect the frontend to the new backend.

### Files touched
- `/frontend/index.html`
- `/frontend/js/dashboard.js`
- `/frontend/js/table.js`
- `/frontend/js/modal.js`
- `/frontend/js/pinglog.js`
- `/frontend/js/charts.js`
- `/frontend/js/users.js`
- `/frontend/js/notifications.js`
- `/frontend/js/logs.js`
- `/frontend/js/settings.js`
- `/frontend/js/profile.js`
- `/frontend/js/auth.js`
- `/frontend/js/utils.js`
- `/frontend/css/main.css`
- `/frontend/css/components.css`

### Acceptance conditions
- The sidebar shows only permitted pages.
- The dashboard and link table sections render correctly with updated labels.
- `Add Link` is visible only for `links.add` users.
- The Users, Notifications, Logs, and Settings SPA sections are present and usable when permitted.
- Login, setup, and change password standalone pages work end to end.
