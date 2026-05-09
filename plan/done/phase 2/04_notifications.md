# 04 Notifications

## Event keys and trigger logic

### `mw_link_down`
- Trigger when a newly saved `PingResult.reachable` is `False` and the previous reachable state was `True`.
- Severity: `critical`.
- Anti-spam: fire once per down transition; do not fire again while the link remains down.

### `mw_link_recovered`
- Trigger when a newly saved `PingResult.reachable` is `True` and the previous reachable state was `False`.
- Severity: `info`.
- Anti-spam: always fire on each up transition.

### `fiber_util_high`
- Trigger when a `MetricSnapshot.fiber_util_pct` crosses `AppSettings.util_critical_threshold_pct` upward.
- Severity: `warning`.
- Anti-spam: fire once when threshold is first crossed upward; do not re-fire while value remains above `util_warning_threshold_pct`.

### `fiber_util_near_cap`
- Trigger when `MetricSnapshot.fiber_util_pct` enters the range `[util_warning_threshold_pct, util_critical_threshold_pct)`.
- Severity: `warning`.
- Anti-spam: do not re-fire while still in near-cap range; eligible again only after value drops below `util_warning_threshold_pct` and then re-enters the range.

### `mw_util_high`
- Trigger when `MetricSnapshot.mw_util_pct` crosses `AppSettings.util_critical_threshold_pct` upward.
- Severity: `warning`.
- Anti-spam: fire once when threshold is first crossed upward; do not re-fire while value remains above `util_warning_threshold_pct`.

### `consecutive_timeouts`
- Trigger when `LinkStatus.consecutive_timeouts` reaches `AppSettings.consecutive_timeout_alert_threshold`.
- After the initial alert, fire again every 10 additional consecutive timeouts while the link remains down.
- Severity: `critical`.

### `ping_service_error`
- Trigger on every exception in `run_ping_cycle()` that aborts the full cycle.
- Severity: `error`.
- Anti-spam: none; every occurrence is sent.

## Anti-spam rules
- `mw_link_down`: do not repeat while the link remains down; next eligibility only after `mw_link_recovered` is sent.
- `mw_link_recovered`: always fire on up transition.
- `fiber_util_high` and `mw_util_high`: once fired, do not fire again while the value stays above `util_warning_threshold_pct`; eligible again after dropping below warn threshold and crossing the critical threshold again.
- `fiber_util_near_cap`: once fired, do not fire again while the value stays in the near-cap range; eligible again after dropping below `util_warning_threshold_pct` and re-entering the range.
- `consecutive_timeouts`: fire at threshold and then at every +10 count while still down.
- `ping_service_error`: fire on every exception.

## `app/services/notification_service.py` functions

### `check_ping_event(link, result, link_status, app_settings)`
Inputs:
- `link`: `Link` model instance.
- `result`: newly saved `PingResult` instance.
- `link_status`: current `LinkStatus` row for the link.
- `app_settings`: `AppSettings.query.get(1)`.

Behavior:
1. Determine the previous reachability from `link_status` or the previous `PingResult`.
2. Evaluate `mw_link_down` and `mw_link_recovered` transitions using current and previous reachable state.
3. Evaluate `consecutive_timeouts` when `link_status.consecutive_timeouts` equals threshold or every 10 additional timeouts.
4. If an event is triggered:
   - call `send_notification(event_key, link.link_id, severity, message)`.
   - update `link_status.last_mw_down_notified_at` when `mw_link_down` fires.
   - reset or update other anti-spam fields only as required for hysteresis.
5. Update `link_status` values such as `mw_status`, `last_ping_at`, `last_ping_latency_ms`, and `consecutive_timeouts`.
6. Commit `link_status` changes.

### `check_util_event(link, metric, link_status, app_settings)`
Inputs:
- `link`: `Link` model instance.
- `metric`: newly saved `MetricSnapshot` instance.
- `link_status`: current `LinkStatus` row.
- `app_settings`: `AppSettings.query.get(1)`.

Behavior:
1. Compare `metric.fiber_util_pct` to `util_warning_threshold_pct` and `util_critical_threshold_pct`.
2. Compare `metric.mw_util_pct` to `util_critical_threshold_pct`.
3. Trigger `fiber_util_high` when fiber util crosses the critical threshold upward.
4. Trigger `fiber_util_near_cap` when fiber util enters the warning-to-critical range.
5. Trigger `mw_util_high` when microwave util crosses the critical threshold upward.
6. For each triggered event:
   - call `send_notification(event_key, link.link_id, severity, message)`.
   - update the corresponding `LinkStatus` anti-spam timestamp field.
7. Update `link_status.fiber_util_pct`, `link_status.mw_util_pct`, and `link_status.last_metric_at`.
8. Commit `link_status` changes.

### `send_notification(event_key, link_id_str, severity, message)`
Inputs:
- `event_key`: one of the seven event keys.
- `link_id_str`: the link identifier string, e.g. `BK-001`.
- `severity`: one of `critical`, `warning`, `info`, `error`.
- `message`: short human-readable description.

Behavior:
1. Query all `User` rows where `is_active=True`.
2. For each user:
   - query `NotificationSubscription` for `event_key`.
   - if no subscription row exists, treat as subscribed only if the user is new and all defaults are seeded; otherwise default to `True` if the row is absent.
   - if `is_subscribed=True`, create `InAppNotification` with `user_id`, `event_key`, `severity`, `link_id=link_id_str`, `message`, `is_read=False`, and `created_at=utcnow`.
   - call `send_email(user, event_key, link_id_str, severity, message)`.
3. Do not return an error if one user's email fails; continue processing remaining users.

### `send_email(user, event_key, link_id_str, severity, message)`
Inputs:
- `user`: `User` model instance.
- `event_key`: notification key.
- `link_id_str`: active link identifier.
- `severity`: `critical`, `warning`, `info`, or `error`.
- `message`: short description.

Behavior:
1. Load `SmtpConfig.query.get(1)`.
2. If no SMTP config exists or `host` is blank, do not send email and write a `SystemLog` event `email_failed` with the reason.
3. Construct the subject using the template:
   - `[MW Link Monitor] {SEVERITY}: {Event Title} — {link_id_str}`
   - where `{SEVERITY}` is uppercase severity and `{Event Title}` is the event key with underscores replaced by spaces and title cased.
4. Construct plain-text and HTML bodies.
5. Send multipart email via SMTP using TLS/SSL settings.
6. If SMTP raises an exception, write `SystemLog` event `email_failed` with `detail` containing `event_key`, `link_id`, and the error message.
7. On success, write `SystemLog` event `email_sent` with `detail` containing `event_key` and `link_id`.

## Email format

Subject template:
- `[MW Link Monitor] {SEVERITY}: {event_key replaced underscores with spaces, title case} — {link_id_str}`

Plain text body must include:
- timestamp in UTC.
- event description.
- link ID.
- `Site A → Site B`.
- current microwave IP.
- the short message.

HTML body requirements:
- Use a simple single-column table.
- Use inline styles only.
- Do not reference external CSS.
- Contain the same content as the plain text body.

## Subscription seeding on user create
- When any new `User` is created, insert one `NotificationSubscription` row per event key.
- Keys: `mw_link_down`, `mw_link_recovered`, `fiber_util_high`, `fiber_util_near_cap`, `mw_util_high`, `consecutive_timeouts`, `ping_service_error`.
- All seeded rows have `is_subscribed=True`.

## In-app notification lifecycle

### Creation
- `send_notification()` generates `InAppNotification` records for subscribed active users.

### Read
- `POST /api/notifications/<id>/read` marks a single notification as read by the authenticated user.
- `POST /api/notifications/read-all` marks all notifications for the authenticated user as read.

### Bell badge polling
- `GET /api/notifications/unread-count` returns `{ "unread_count": n }`.
- `/frontend/js/notifications.js` polls this endpoint every 60 seconds.
- The bell badge is hidden when `unread_count == 0`.

## Frontend behavior
- The notification bell in `/frontend/index.html` is visible to all authenticated users.
- The bell badge is built from the unread count returned by `/api/notifications/unread-count`.
- The Notifications SPA section displays paginated 25-per-page notifications and subscription preferences.
- The Preferences tab saves toggles immediately through `PUT /api/notifications/subscriptions`.
