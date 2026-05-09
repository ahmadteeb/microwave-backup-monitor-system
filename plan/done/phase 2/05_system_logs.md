# 05 System Logs

## `write_log()` signature and error handling

### Function definition in `app/services/log_service.py`
- Signature:
  - `write_log(category, event, actor, target=None, detail=None, ip_address=None)`
- Behavior:
  1. Create a `SystemLog` row with `timestamp=utcnow()`.
  2. Populate `category`, `event`, `actor`, `target`, `detail`, `ip_address`.
  3. Commit the row to the database.
  4. Wrap the operation in `try/except`.
  5. On exception, log the exception to Python logger and do not propagate.

Notes:
- This function must never raise exceptions to calling code.
- It is the central audit log writer for all route and service events.

## Full event table

| Category | Event | Actor | Target | Detail |
|---|---|---|---|---|
| auth | login_success | username | username | `{ ip: "x.x.x.x" }` |
| auth | login_failed | `anonymous` | attempted username | `{ ip: "x.x.x.x" }` |
| auth | logout | username | username | `null` |
| auth | account_locked | `system` | username | `{ failed_count: n, ip: "x.x.x.x" }` |
| auth | account_unlocked | admin username or `system` | username | `{ reason: "manual" }` |
| auth | password_changed | username | username | `null` |
| auth | password_reset | admin username | target username | `{ force_change: true/false }` |
| users | user_created | admin username | new username | `{ role: "admin" }` |
| users | user_edited | admin username | target username | `{ changed: { field: [old, new], ... } }` |
| users | user_deleted | admin username | target username | `null` |
| users | role_changed | admin username | target username | `{ old_role: "operator", new_role: "viewer" }` |
| users | permission_overridden | admin username | target username | `{ key: "links.add", old_value: true, new_value: false }` |
| links | link_added | username | link_id | `null` |
| links | link_edited | username | link_id | `{ changed: { field: [old, new], ... } }` |
| links | link_deleted | username | link_id | `null` |
| links | manual_ping | username | link_id | `{ reachable: true/false, latency_ms: 123 }` |
| config | smtp_updated | username | `smtp` | `{ changed: [fields] }` |
| config | jumpserver_updated | username | `jumpserver` | `{ changed: [fields] }` |
| config | app_settings_updated | username | `app_settings` | `{ changed: [fields] }` |
| scheduler | ping_cycle_started | `system` | `null` | `{ link_count: n }` |
| scheduler | ping_cycle_completed | `system` | `null` | `{ duration_ms: n, success_count: n, fail_count: n }` |
| scheduler | ping_cycle_error | `system` | `null` | `{ error: "message" }` |
| notifications | email_sent | `system` | recipient email | `{ event_key: "mw_link_down", link_id: "BK-001" }` |
| notifications | email_failed | `system` | recipient email | `{ event_key: "mw_link_down", error: "message" }` |

Notes:
- Never log raw passwords, encryption keys, or tokens.
- Do not store user password hashes in `detail`.
- The `detail` field should be structured JSON when additional data is needed.

## Log routes in `app/routes/logs.py`

### System log endpoint
- `GET /api/logs/system`
- Permission: `logs.view_system`
- Supported query parameters:
  - `page` (integer)
  - `per_page` (integer)
  - `category` (string)
  - `actor` (string)
  - `search` (string)
  - `date_from` (ISO date string)
  - `date_to` (ISO date string)
  - `sort` (any sortable field, e.g. `timestamp`)
  - `order` (`asc` or `desc`)
- Response shape:
  - `page`, `per_page`, `total`, `items`.
  - Each item includes `timestamp`, `category`, `event`, `actor`, `target`, `detail`.

### System log export endpoint
- `GET /api/logs/system/export`
- Permission: `logs.export`
- Uses the same filter parameters as `/api/logs/system`.
- Response is CSV with headers in this order:
  - `timestamp`, `category`, `event`, `actor`, `target`, `detail`, `ip_address`

### Ping log endpoint
- `GET /api/logs/ping`
- Permission: `logs.view_ping`
- Supported query parameters:
  - `page`, `per_page`, `search`, `date_from`, `date_to`, `sort`, `order`
- Response shape is paginated ping log rows.

### Ping log export endpoint
- `GET /api/logs/ping/export`
- Permission: `logs.export`
- Uses the same filter parameters as `/api/logs/ping`.
- CSV headers must be in this order, based on existing ping log fields:
  - `timestamp`, `link_id`, `reachable`, `latency_ms`, `packet_loss`, `raw_output`, `triggered_by`, `triggered_by_user_id`

Notes:
- Both export endpoints should include only rows matching the current filters.
- CSV detail fields should be JSON-encoded if necessary.

## Frontend log browsing requirements
- The System Log tab in `/frontend/index.html` must display filters for category, date range, actor text, and free-text search.
- The table columns are: Timestamp, Category, Event, Actor, Target, Detail.
- Detail values should expand inline as JSON in the UI.
- Pagination is 50 rows per page, newest first.
- The Export CSV button is visible only if `logs.export` is `true`.

## What must never appear in logs
- Passwords in plain text.
- Password hashes.
- Fernet keys or encryption key material.
- SMTP passwords or Jump Server passwords.
- Session cookie contents.
- Any secret token or sensitive authentication header.
