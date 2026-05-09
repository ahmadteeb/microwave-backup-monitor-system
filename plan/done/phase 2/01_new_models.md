# 01 New Models

## New models in `app/models.py`

### SetupState
- id: Integer primary key.
- is_complete: Boolean, default False.
- completed_at: DateTime, nullable.

Notes:
- Only one row is expected, with `id=1`.
- Used by `app/__init__.py` before_request hook to route first-boot traffic to `/setup`.

### User
- id: Integer primary key.
- username: String(64), unique, not nullable.
- full_name: String(128), not nullable.
- email: String(256), unique, not nullable.
- password_hash: String(256), not nullable.
- role: Enum('admin','operator','viewer'), not nullable.
- is_active: Boolean, default True.
- is_locked: Boolean, default False.
- locked_until: DateTime, nullable.
- failed_login_count: Integer, default 0.
- force_password_change: Boolean, default False.
- created_at: DateTime, not nullable.
- updated_at: DateTime, not nullable.
- last_login_at: DateTime, nullable.

Relationships:
- user_permissions: one-to-many to `UserPermission`.
- notification_subscriptions: one-to-many to `NotificationSubscription`.
- in_app_notifications: one-to-many to `InAppNotification`.
- updated_smtp_configs: optional one-to-many reverse via `SmtpConfig.updated_by_id`.
- updated_jumpservers: optional one-to-many reverse via `JumpServer.updated_by_id`.
- updated_app_settings: optional one-to-many reverse via `AppSettings.updated_by_id`.

### UserPermission
- id: Integer primary key.
- user_id: Foreign key to `User.id`, not nullable.
- permission_key: String(64), not nullable.
- is_granted: Boolean, not nullable.

Constraints:
- Unique constraint on `(user_id, permission_key)`.

Notes:
- If a row exists, it overrides the role default for that user.
- If no row exists, permission resolves from `ROLE_DEFAULTS` in `app/permissions.py`.

### NotificationSubscription
- id: Integer primary key.
- user_id: Foreign key to `User.id`, not nullable.
- event_key: String(64), not nullable.
- is_subscribed: Boolean, default True.

Constraints:
- Unique constraint on `(user_id, event_key)`.

Notes:
- Seeded for all seven event keys when a new user is created.
- Used by `/app/routes/notifications.py` and `app/services/notification_service.py`.

### InAppNotification
- id: Integer primary key.
- user_id: Foreign key to `User.id`, not nullable.
- event_key: String(64), not nullable.
- severity: Enum('critical','warning','info','error'), not nullable.
- link_id: String(32), nullable.
- message: Text, not nullable.
- is_read: Boolean, default False.
- created_at: DateTime, not nullable.

Indexes:
- Index on `(user_id, is_read, created_at)` is recommended for polling unread count and listing notifications.

### SmtpConfig
- id: Integer primary key.
- host: String(256), not nullable.
- port: Integer, not nullable.
- username: String(256), nullable.
- password_encrypted: String(500), nullable.
- from_address: String(256), not nullable.
- use_tls: Boolean, default True.
- use_ssl: Boolean, default False.
- updated_at: DateTime, not nullable.
- updated_by_id: Foreign key to `User.id`, nullable.

Notes:
- Always created with `id=1` during setup.
- Password is encrypted by `app/services/crypto_service.py`.

### AppSettings
- id: Integer primary key.
- session_timeout_minutes: Integer, default 480.
- ping_interval_seconds: Integer, default 60.
- ping_count: Integer, default 3.
- ping_timeout_seconds: Integer, default 2.
- consecutive_timeout_alert_threshold: Integer, default 5.
- util_warning_threshold_pct: Float, default 70.0.
- util_critical_threshold_pct: Float, default 90.0.
- updated_at: DateTime, not nullable.
- updated_by_id: Foreign key to `User.id`, nullable.

Notes:
- Replaces `.env` values for ping and session settings.
- Seeded during setup with the default values above.

### LinkStatus
- id: Integer primary key.
- link_id: Foreign key to `Link.id`, unique.
- mw_status: Enum('up','down','high','checking','unknown'), default 'unknown'.
- last_ping_at: DateTime, nullable.
- last_ping_latency_ms: Float, nullable.
- consecutive_timeouts: Integer, default 0.
- last_metric_at: DateTime, nullable.
- fiber_util_pct: Float, nullable.
- mw_util_pct: Float, nullable.
- last_mw_down_notified_at: DateTime, nullable.
- last_fiber_high_notified_at: DateTime, nullable.
- last_mw_high_notified_at: DateTime, nullable.
- last_fiber_near_cap_notified_at: DateTime, nullable.

Notes:
- One `LinkStatus` row must exist per `Link`.
- It is updated after every ping cycle and used by `app/services/notification_service.py`.

### SystemLog
- id: Integer primary key.
- timestamp: DateTime, not nullable.
- category: String(32), not nullable.
- event: String(64), not nullable.
- actor: String(128), not nullable.
- target: String(256), nullable.
- detail: JSON, nullable.
- ip_address: String(45), nullable.

Indexes:
- Indexes on `(category, timestamp)` and `(actor, timestamp)` are recommended for filtering.

Notes:
- Read-only storage. No update or delete routes.
- Used by `/app/routes/logs.py` and `app/services/log_service.py`.

## Changed existing models in `app/models.py`

### Link
Add the following fields:
- created_by_id: Foreign key to `User.id`, nullable.
- is_active: Boolean, default True, server default `'1'` for migration compatibility.

Notes:
- Existing rows remain unaffected because `created_by_id` is nullable.
- New links should record the creator when created.

### PingResult
Add the following fields:
- triggered_by: Enum('scheduler','manual'), default 'scheduler', server default `'scheduler'`.
- triggered_by_user_id: Foreign key to `User.id`, nullable.

Notes:
- Existing ping rows remain unchanged because new columns are nullable or defaulted.

### JumpServer
Add the following field:
- updated_by_id: Foreign key to `User.id`, nullable.

Notes:
- Existing rows remain unchanged.

## Seeding logic

### SetupState and AppSettings
- `app/__init__.py` must call `db.create_all()`.
- After `create_all()`, if `SetupState.query.get(1)` does not exist, create it with `is_complete=False` and `completed_at=None`.
- If `AppSettings.query.get(1)` does not exist, create `AppSettings` with the default values listed above.
- If `SmtpConfig.query.get(1)` does not exist, it may remain unset until setup completes.

### NotificationSubscription seeding
- When a new `User` is created in setup or via `/api/users`, create one `NotificationSubscription` row per event key for the user.
- The seven event keys are: `mw_link_down`, `mw_link_recovered`, `fiber_util_high`, `fiber_util_near_cap`, `mw_util_high`, `consecutive_timeouts`, `ping_service_error`.
- Each seeded subscription must default `is_subscribed=True`.

### LinkStatus creation/update strategy
- When a `Link` is created, create a matching `LinkStatus` row with `link_id` foreign key and `mw_status='unknown'`.
- During each ping cycle in `app/services/ping_service.py`, fetch or create the current `LinkStatus` row for the link.
- Update `LinkStatus` fields after each `PingResult` and after each metric snapshot update.
- Anti-spam fields are updated by notification logic rather than by repeated email dispatch.

## Fernet key migration path

### New service
- Add `app/services/crypto_service.py` with public methods:
  - `encrypt(plaintext: str) -> str`
  - `decrypt(ciphertext: str) -> str`

### Key derivation
- Primary key derivation must use PBKDF2 from `app/config.py` `SECRET_KEY`.
- Secondary fallback must reproduce the existing SHA-256-derived Fernet key used by `app/routes/jumpserver.py` today.

### Migration behavior
- On decryption of existing `password_encrypted` fields, attempt PBKDF2 first.
- If PBKDF2 decryption raises an exception, attempt SHA-256 fallback decryption.
- If fallback succeeds, return the decrypted value and mark the row for re-encryption with PBKDF2 on the next save.
- All save/update flows that write encrypted passwords must use the PBKDF2-derived key going forward.

Notes:
- This path avoids breaking existing `JumpServer.password_encrypted` values when migrating the live database.
- The plan should mention that `crypto_service.py` is imported by both `app/routes/jumpserver.py` and by future SMTP/jump server settings flows.
