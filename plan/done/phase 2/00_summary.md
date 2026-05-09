# 00 Summary

## What is changing and why

The enhancement plan upgrades the existing MW Backup Link Monitor from a single-user, environment-configured app into a secured, multi-user operations console with first-boot setup, authentication, RBAC, user management, notifications, audit logging, and editable system settings.

Why these changes are needed:
- Remove stale UI clutter and fix label readability in `/frontend/index.html` and JS/CSS assets.
- Replace environment-only configuration for jump server, SMTP, and ping settings with a database-backed setup wizard and settings UI.
- Add authentication and session management to protect all API routes and pages.
- Add role-based access control so admin/operator/viewer permissions are enforced in backend routes and frontend visibility.
- Provide admin user management, per-user notification preferences, and audit trails for security and operations.
- Add notification delivery via in-app alerts and SMTP email for critical link events.
- Add system audit logging for auth, users, links, config, scheduler, and notification events.

## Enhancement map

### E1 — Remove UI clutter and fix labels
- Files: `/frontend/index.html`, `/frontend/js/dashboard.js`, `/frontend/js/table.js`, `/frontend/js/modal.js`, `/frontend/js/pinglog.js`, `/frontend/js/charts.js`, `/frontend/css/main.css`, `/frontend/css/components.css`
- Purpose: remove unused nav items, bottom panels, floating add button, and replace underscore labels with human-readable text.

### E2 — Setup wizard
- Files: `/app/__init__.py`, `/app/routes/setup.py`, `/frontend/setup.html`, `/frontend/js/auth.js` (or shared setup helper), `/app/models.py`, `/app/services/crypto_service.py`, `/app/extensions.py`, `/app/config.py`
- Purpose: add first-boot configuration, seed admin user, SMTP config, jump server config, AppSettings, and SetupState.

### E3 — Authentication and session management
- Files: `/app/routes/auth.py`, `/app/__init__.py`, `/app/permissions.py`, `/frontend/login.html`, `/frontend/change_password.html`, `/frontend/js/auth.js`, `/frontend/js/utils.js`, `/app/models.py`
- Purpose: add login/logout, session cookie, password lockout, force password change, and session timeout enforcement.

### E4 — RBAC
- Files: `/app/permissions.py`, `/app/routes/links.py`, `/app/routes/dashboard.py`, `/app/routes/jumpserver.py`, `/app/routes/pinglog.py`, `/frontend/js/table.js`, `/frontend/js/dashboard.js`, `/frontend/index.html`
- Purpose: enforce role defaults and per-user overrides on route access and frontend controls.

### E5 — User management
- Files: `/app/routes/users.py`, `/frontend/index.html`, `/frontend/js/users.js`, `/app/models.py`, `/app/services/log_service.py`, `/app/services/crypto_service.py`
- Purpose: add admin-only user CRUD, reset password, unlock, and permission override management.

### E6 — Notification system with SMTP
- Files: `/app/routes/notifications.py`, `/app/services/notification_service.py`, `/app/models.py`, `/frontend/index.html`, `/frontend/js/notifications.js`, `/frontend/css/components.css`, `/app/services/log_service.py`
- Purpose: add event-driven in-app notifications, email delivery, subscriptions, and a bell badge.

### E7 — System audit logs
- Files: `/app/services/log_service.py`, `/app/routes/logs.py`, `/frontend/index.html`, `/frontend/js/logs.js`, `/frontend/css/components.css`, `/app/models.py`
- Purpose: add centralized audit logging, read-only log browsing, filtering, and export support.

### E8 — Settings page
- Files: `/app/routes/settings.py`, `/app/routes/profile.py`, `/frontend/index.html`, `/frontend/js/settings.js`, `/frontend/js/profile.js`, `/frontend/css/components.css`, `/app/models.py`, `/app/services/crypto_service.py`, `/app/services/log_service.py`
- Purpose: add editable SMTP/jump server/app settings and user profile management.

## Files that must NOT be changed
- `/app/services/ssh_service.py` — SSHService is explicitly protected.
- Core ping parsing logic in `/app/services/ping_service.py` — specifically `parse_ping_output()` and the packet parsing algorithm must remain unchanged.

## Migration risks and preservation guarantees

### Migration risks
- Existing SQLite data must not be destroyed. New models and fields must be added with nullable or server-default values.
- Existing encrypted `JumpServer.password_encrypted` values use SHA-256-derived Fernet keys. The new `app/services/crypto_service.py` must support PBKDF2 decryption with SHA-256 fallback and re-encrypt on save.
- Existing `ping_service.py` and `scheduler.py` use `.env` values for ping config; new code must preserve current behavior until `AppSettings` exists, then switch cleanly.
- A missing active `JumpServer` row should not crash pings; the scheduler must skip cycles gracefully and log the error.

### Preserved functionality
- Existing `Link`, `PingResult`, `MetricSnapshot`, and `JumpServer` data remain accessible.
- Existing link CRUD routes and manual ping operations remain operational after adding auth and RBAC.
- Existing scheduled ping cycle behavior remains intact, with configuration moving from `.env` to database-backed settings.
- Existing frontend dashboards and link table flows remain usable after UI cleanup.
- The setup wizard only appears on first boot or when `SetupState.is_complete` is false.

## Cross-file notes
- New backend shared services are centralized in `/app/services/crypto_service.py` and `/app/services/log_service.py`; route modules must import from these instead of duplicating logic.
- The frontend must call `/api/auth/me` at startup to cache permissions and gate UI controls in `/frontend/js/table.js`, `/frontend/js/dashboard.js`, and `/frontend/js/notifications.js`.
- The notification bell and unread count polling are defined in `/frontend/js/notifications.js` and depend on `/app/routes/notifications.py`.
- The setup wizard page and login page are standalone HTML pages, while `/frontend/index.html` becomes the authenticated SPA shell.
