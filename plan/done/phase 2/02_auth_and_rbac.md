# 02 Auth and RBAC

## Setup wizard flow

### Trigger condition in `app/__init__.py`
- Add a `before_request` hook.
- If `SetupState.query.get(1)` does not exist or `is_complete` is `False`, then:
  - allow requests to `/setup`, `/api/setup/*`, `/static/*`, and login assets.
  - redirect all other requests to `/setup`.
- After setup completes, requests to `/setup` redirect to `/login`.

### Setup completion sequence in `/app/routes/setup.py`
- `POST /api/setup/complete` validates all required fields.
- If validation passes, the route must:
  1. Confirm `SetupState` is still incomplete to prevent race conditions.
  2. Hash the admin password with bcrypt cost factor 12.
  3. Create a `User` row with `role='admin'`, `force_password_change=False`, and seeded timestamps.
  4. Create `SmtpConfig` row with encrypted password via `app/services/crypto_service.py`.
  5. Deactivate any existing `JumpServer` rows; create a new active `JumpServer` row with encrypted password.
  6. Create `AppSettings` row with default values.
  7. Create `SetupState` row with `is_complete=True` and `completed_at=utcnow`.
  8. Seed `NotificationSubscription` rows for the admin user for all seven event keys.
  9. Return `200` with `{"redirect": "/login"}`.

## Login flow

### Login page
- `GET /login` serves `/frontend/login.html`.
- Fields: Username, Password.
- Submit button: `Sign In`.
- On 401: show `Invalid username or password.`
- On 423: show `Account locked. Please try again in X minutes or contact an administrator.`
- On success: redirect to `/` or `/change-password` if required.

### `POST /api/auth/login` in `/app/routes/auth.py`
1. Find `User` by `username`.
2. If not found, return `401` with generic error.
3. If `is_active` is `False`, return `401` generic error.
4. If `is_locked` is `True` and `locked_until > utcnow`:
   - return `423` with remaining minutes.
5. If `locked_until <= utcnow`:
   - clear `is_locked`, set `locked_until=None`, reset `failed_login_count=0`, commit, continue.
6. Verify password with bcrypt.
7. If password is incorrect:
   - increment `failed_login_count` and commit.
   - if `failed_login_count >= 5`, set `is_locked=True`, `locked_until=utcnow+15min`, commit.
   - write `SystemLog` with category `auth`, event `account_locked` when lock occurs.
   - return `401` generic error.
8. If password is correct:
   - reset `failed_login_count=0`, `is_locked=False`, `last_login_at=utcnow`, commit.
   - set Flask session values: `user_id`, `username`, `full_name`, `role`, `logged_in_at`.
   - write `SystemLog` event `login_success` with `ip_address` from request.
9. If `force_password_change=True`, return `200` `{"redirect": "/change-password"}`.
10. Else return `200` `{"redirect": "/"}`.

### `POST /api/auth/logout`
- Clear the session.
- Write `SystemLog` event `logout`.
- Return `200`.

## Session management

### Session contents
The Flask session must store:
- `user_id`
- `username`
- `full_name`
- `role`
- `logged_in_at` as ISO string

### Session timeout hook in `app/__init__.py`
- The `before_request` hook reads `AppSettings.query.get(1).session_timeout_minutes`.
- If the user is authenticated and `datetime.utcnow() - logged_in_at` exceeds the timeout:
  - clear the session.
  - for `/api/*` requests return `401` JSON `{"error": "Authentication required"}`.
  - for page routes redirect to `/login`.

### `login_required` decorator in `app/permissions.py`
- If `user_id` missing or session expired:
  - on API routes, return `401` JSON `{"error": "Authentication required"}`.
  - on non-API routes, redirect to `/login`.
- Otherwise allow the wrapped route.

## Force password change flow

### `GET /change-password`
- Serves `/frontend/change_password.html`.
- If the current session has `force_password_change=True`, the form omits current password.
- Otherwise the form includes Current Password, New Password, Confirm New Password.

### `POST /api/auth/change-password`
- Validate passwords and current password if required.
- If invalid, return `400` with per-field errors.
- Hash new password with bcrypt.
- Set `force_password_change=False`.
- Write `SystemLog` event `password_changed`.
- Return `200` `{"redirect": "/"}`.

## RBAC model

### `ROLE_DEFAULTS` in `app/permissions.py`

#### links.* defaults
| Key | admin | operator | viewer |
|---|---|---|---|
| links.view | True | True | True |
| links.add | True | True | False |
| links.edit | True | True | False |
| links.delete | True | True | False |
| links.ping | True | True | False |
| links.export | True | True | True |

#### users.* defaults
| Key | admin | operator | viewer |
|---|---|---|---|
| users.view | True | False | False |
| users.add | True | False | False |
| users.edit | True | False | False |
| users.delete | True | False | False |
| users.reset_password | True | False | False |
| users.manage_permissions | True | False | False |

#### config.* defaults
| Key | admin | operator | viewer |
|---|---|---|---|
| config.view | True | False | False |
| config.edit_smtp | True | False | False |
| config.edit_jumpserver | True | False | False |
| config.edit_app | True | False | False |

#### logs.* defaults
| Key | admin | operator | viewer |
|---|---|---|---|
| logs.view_system | True | False | False |
| logs.view_ping | True | True | True |
| logs.export | True | True | False |

#### notifications.* defaults
| Key | admin | operator | viewer |
|---|---|---|---|
| notifications.view_own | True | True | True |
| notifications.edit_own | True | True | True |
| notifications.manage_all | True | False | False |

### `has_permission(user_id, permission_key) -> bool`
1. Query `UserPermission` for `(user_id, permission_key)`.
2. If a row exists, return `is_granted`.
3. Otherwise query `User.role` and return `ROLE_DEFAULTS[role][permission_key]`.

### `require_permission(key)` decorator
- Wraps a route function.
- Uses `session['user_id']` and `has_permission()`.
- If permission is denied, return `403` JSON `{"error": "Permission denied", "code": "FORBIDDEN"}`.

## Decorator application to existing routes
The following existing routes must receive both `@login_required` and the listed `@require_permission` decorator.

| Route | Blueprint | Decorator |
|---|---|---|
| GET `/api/links` | `app/routes/links.py` | `links.view` |
| POST `/api/links` | `app/routes/links.py` | `links.add` |
| GET `/api/links/<id>` | `app/routes/links.py` | `links.view` |
| PUT `/api/links/<id>` | `app/routes/links.py` | `links.edit` |
| DELETE `/api/links/<id>` | `app/routes/links.py` | `links.delete` |
| POST `/api/links/<id>/ping` | `app/routes/links.py` | `links.ping` |
| GET `/api/dashboard/kpi` | `app/routes/dashboard.py` | `links.view` |
| GET `/api/jumpserver` | `app/routes/jumpserver.py` | `config.view` |
| PUT `/api/jumpserver` | `app/routes/jumpserver.py` | `config.edit_jumpserver` |
| GET `/api/ping-log` | `app/routes/pinglog.py` | `logs.view_ping` |

Notes:
- All new routes in `app/routes/users.py`, `app/routes/notifications.py`, `app/routes/logs.py`, `app/routes/settings.py`, and `app/routes/profile.py` must also use `@login_required` and the permission rules described in `03_api_routes.md`.
- Frontend access control is enforced by permission data returned from `GET /api/auth/me`.

## `GET /api/auth/me` response shape

The response must contain the logged-in user profile plus an effective permission map:
```json
{
  "id": 1,
  "username": "admin",
  "full_name": "Admin User",
  "role": "admin",
  "permissions": {
    "links.view": true,
    "links.add": true,
    "links.edit": true,
    "links.delete": true,
    "links.ping": true,
    "links.export": true,
    "users.view": true,
    "users.add": true,
    "users.edit": true,
    "users.delete": true,
    "users.reset_password": true,
    "users.manage_permissions": true,
    "config.view": true,
    "config.edit_smtp": true,
    "config.edit_jumpserver": true,
    "config.edit_app": true,
    "logs.view_system": true,
    "logs.view_ping": true,
    "logs.export": true,
    "notifications.view_own": true,
    "notifications.edit_own": true,
    "notifications.manage_all": true
  }
}
```

Notes:
- The map must include every known permission key.
- Role defaults are used when the user has no overrides.
- `UserPermission` overrides are applied per key.
