# 03 API Routes

## New routes

### Setup routes (`app/routes/setup.py`)

| Method | URL | Permission | Request body | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/setup` | none | none | HTML page served | none |
| POST | `/api/setup/test-smtp` | none | `{ host, port, username?, password?, from_address, use_tls, use_ssl }` | `200 { "result": "SMTP connection successful" }` | `400` validation errors, `500` SMTP failure |
| POST | `/api/setup/test-jumpserver` | none | `{ host, port, username, password }` | `200 { "result": "Jump server connection successful" }` | `400` validation errors, `500` SSH failure |
| POST | `/api/setup/complete` | none | `{ full_name, username, email, password, confirm_password, smtp: {host, port, username?, password?, from_address, use_tls, use_ssl}, jumpserver: {host, port, username, password} }` | `200 { "redirect": "/login" }` | `400` validation / `409` username/email duplicate / `500` setup failure |

Notes:
- `test-smtp` and `test-jumpserver` must not persist data.
- `complete` writes `User`, `SmtpConfig`, `JumpServer`, `AppSettings`, `SetupState`, and `NotificationSubscription` rows.

### Auth routes (`app/routes/auth.py`)

| Method | URL | Permission | Request body | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/api/auth/me` | authenticated | none | user object with `permissions` map | `401` if not authenticated |
| POST | `/api/auth/login` | none | `{ username, password }` | `200 { "redirect": "/" }` or `{ "redirect": "/change-password" }` | `401` invalid credentials, `423` account locked |
| POST | `/api/auth/logout` | authenticated | none | `200 { "result": "logged out" }` | `401` if not authenticated |
| POST | `/api/auth/change-password` | authenticated | `{ current_password? , new_password, confirm_password }` | `200 { "redirect": "/" }` | `400` validation errors, `401` invalid current password |

Notes:
- The login route writes `system` log events for success and lockout.
- `auth/me` must return every known permission key with effective booleans.

### User routes (`app/routes/users.py`)

| Method | URL | Permission | Request body | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/api/users` | `users.view` | none | list of users with status metadata | `401`, `403` |
| POST | `/api/users` | `users.add` | `{ full_name, username, email, role, is_active, force_password_change }` | `201 { "id": ... }` | `400`, `409` |
| GET | `/api/users/<id>` | `users.view` | none | user object | `401`, `403`, `404` |
| PUT | `/api/users/<id>` | `users.edit` | `{ full_name, email, role, is_active, force_password_change }` | `200 { "result": "updated" }` | `400`, `403`, `404` |
| DELETE | `/api/users/<id>` | `users.delete` | none | `200 { "result": "deleted" }` | `401`, `403`, `404`, `400` cannot delete self |
| POST | `/api/users/<id>/reset-password` | `users.reset_password` | `{ new_password, confirm_password, force_password_change }` | `200 { "result": "password reset" }` | `400`, `403`, `404` |
| POST | `/api/users/<id>/unlock` | `users.edit` | none | `200 { "result": "unlocked" }` | `401`, `403`, `404` |
| GET | `/api/users/<id>/permissions` | `users.manage_permissions` | none | `{ permissions: { ... }, overrides: { ... } }` | `401`, `403`, `404` |
| PUT | `/api/users/<id>/permissions` | `users.manage_permissions` | `{ overrides: { "links.add": true, ... } }` | `200 { "result": "permissions updated" }` | `400`, `401`, `403`, `404` |
| GET | `/api/users/<id>/notifications/subscriptions` | `notifications.manage_all` | none | list of subscription records | `401`, `403`, `404` |
| PUT | `/api/users/<id>/notifications/subscriptions` | `notifications.manage_all` | `{ subscriptions: [{ event_key, is_subscribed }, ...] }` | `200 { "result": "subscriptions updated" }` | `400`, `401`, `403`, `404` |

Notes:
- User create and update actions write `users` SystemLog events.
- Creating a user seeds `NotificationSubscription` for all seven event keys set to `true`.
- Permission override PUT should compare old and new values and write `permission_overridden` logs per changed key.

### Notification routes (`app/routes/notifications.py`)

| Method | URL | Permission | Request body | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/api/notifications` | `notifications.view_own` | none | paginated notifications list | `401`, `403` |
| GET | `/api/notifications/unread-count` | `notifications.view_own` | none | `{ unread_count: n }` | `401`, `403` |
| POST | `/api/notifications/<id>/read` | `notifications.view_own` | none | `200 { "result": "read" }` | `401`, `403`, `404` |
| POST | `/api/notifications/read-all` | `notifications.view_own` | none | `200 { "result": "all read" }` | `401`, `403` |
| GET | `/api/notifications/subscriptions` | `notifications.edit_own` | none | list of own subscriptions | `401`, `403` |
| PUT | `/api/notifications/subscriptions` | `notifications.edit_own` | `{ subscriptions: [{ event_key, is_subscribed }, ...] }` | `200 { "result": "updated" }` | `400`, `401`, `403` |

Notes:
- Only the authenticated user can manage their own subscriptions unless `manage_all` is used on admin routes.
- The bell badge poll endpoint uses `/api/notifications/unread-count`.

### Log routes (`app/routes/logs.py`)

| Method | URL | Permission | Request params | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/api/logs/system` | `logs.view_system` | `page`, `per_page`, `category`, `actor`, `search`, `date_from`, `date_to`, `sort`, `order` | paginated system logs | `401`, `403` |
| GET | `/api/logs/system/export` | `logs.export` | same filters | CSV download | `401`, `403` |
| GET | `/api/logs/ping` | `logs.view_ping` | `page`, `per_page`, `search`, `date_from`, `date_to`, `sort`, `order` | paginated ping logs | `401`, `403` |
| GET | `/api/logs/ping/export` | `logs.export` | same filters | CSV download | `401`, `403` |

Notes:
- Both ping and system log routes must support the same query filters.
- Export endpoints must use the same filter set and CSV column ordering defined in `05_system_logs.md`.

### Settings routes (`app/routes/settings.py`)

| Method | URL | Permission | Request body | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/api/settings/smtp` | `config.view` | none | SMTP config object with `password: "••••••••"` | `401`, `403` |
| PUT | `/api/settings/smtp` | `config.edit_smtp` | `{ host, port, username?, password, from_address, use_tls, use_ssl }` | `200 { "result": "smtp updated" }` | `400`, `401`, `403` |
| POST | `/api/settings/smtp/test` | `config.edit_smtp` | none or use saved values | `200 { "result": "test email sent" }` | `401`, `403`, `500` |
| GET | `/api/settings/jumpserver` | `config.view` | none | jumpserver config with `password: "••••••••"` | `401`, `403` |
| PUT | `/api/settings/jumpserver` | `config.edit_jumpserver` | `{ host, port, username, password }` | `200 { "result": "jumpserver updated" }` | `400`, `401`, `403` |
| POST | `/api/settings/jumpserver/test` | `config.edit_jumpserver` | none or use saved values | `200 { "result": "connection successful" }` | `401`, `403`, `500` |
| GET | `/api/settings/app` | `config.view` | none | app settings object | `401`, `403` |
| PUT | `/api/settings/app` | `config.edit_app` | `{ session_timeout_minutes, ping_interval_seconds, ping_count, ping_timeout_seconds, consecutive_timeout_alert_threshold, util_warning_threshold_pct, util_critical_threshold_pct }` | `200 { "result": "app settings updated" }` | `400`, `401`, `403` |

Notes:
- GET responses must mask password fields as `"••••••••"`.
- PUT must preserve existing encrypted password if the submitted string is `"••••••••"`.
- All successful setting changes write `SystemLog` events.

### Profile routes (`app/routes/profile.py`)

| Method | URL | Permission | Request body | Success response | Error cases |
|---|---|---|---|---|---|
| GET | `/api/auth/me` | authenticated | none | user profile and permissions | `401` |
| PUT | `/api/profile` | authenticated | `{ full_name, email }` | `200 { "result": "profile updated" }` | `400`, `401` |
| POST | `/api/profile/change-password` | authenticated | `{ current_password, new_password, confirm_password }` | `200 { "result": "password changed" }` | `400`, `401` |

Notes:
- Profile edit only updates the authenticated user's full name and email.
- Password change uses bcrypt hashing and resets `force_password_change`.

## Modifications to existing routes

### `app/routes/links.py`
- Add `@login_required` to all routes.
- Add `@require_permission(...)` on each route according to RBAC.
- Read ping settings from `AppSettings.query.get(1)` instead of `current_app.config`.
- For manual ping route, set `PingResult.triggered_by='manual'` and `triggered_by_user_id=session['user_id']`.
- After saving each `PingResult`, call `notification_service.check_ping_event(link, result, link_status, app_settings)`.
- Write `SystemLog` events on add/edit/delete/manual-ping.

### `app/routes/dashboard.py`
- Add `@login_required` and `@require_permission('links.view')`.
- Remove the legacy `/api/dashboard/stability` route entirely.

### `app/routes/jumpserver.py`
- Add `@login_required` and `@require_permission('config.view')` to GET.
- Add `@login_required` and `@require_permission('config.edit_jumpserver')` to PUT.
- Import encryption from `app/services/crypto_service.py` instead of defining `get_fernet_key()`, `encrypt_password()`, and `decrypt_password()` locally.
- Remove `.env` fallback logic from GET and `app/services/ping_service.py`.
- Write `SystemLog` event `jumpserver_updated` on successful PUT.

### `app/routes/pinglog.py`
- Add `@login_required` and `@require_permission('logs.view_ping')`.

### `app/services/ping_service.py`
- Remove `_get_active_jumpserver_config()` fallback to `.env`.
- Read `ping_count` and `ping_timeout_seconds` from `AppSettings`.
- After each `PingResult` is saved, call `notification_service.check_ping_event()`.
- Update `LinkStatus` row after each ping.
- Log cycle events via `log_service` (start/complete/error in scheduler, per link updates in ping_service as needed).

### `app/services/scheduler.py`
- Read `ping_interval_seconds` from `AppSettings` on each job trigger.
- Log cycle start, completion, and error events via `log_service`.

### `app/routes/dashboard.py` and other GET routes
- Ensure front-end record count and links are available for `links.view` only.

### `/app/routes/jumpserver.py` and settings flow
- Existing JumpServer read route should return masked password from database only if active row exists.
- No `.env` fallback if DB row is missing; instead return a clean error or empty data for setup.

## Request and response schema conventions
- Use explicit JSON objects for all API request bodies.
- For list endpoints, return paginated objects with `page`, `per_page`, `total`, and `items` arrays.
- On validation errors, return `400` with an object keyed by field names.
- On unauthorized access, return `401` or `403` as described.
