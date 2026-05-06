# 05 — Notification System

## 1. Trigger Events and Severity Matrix

The application generates system alerts on a variety of network events. Each event is classified by severity, determining how it is rendered in the UI:

| Event Key | Trigger Condition | Severity | Message Format |
|---|---|---|---|
| `mw_link_down` | Microwave link status changes from Up or High to Down. | Critical | Standby microwave link {link_id} has gone down. Reachability checks failed. |
| `mw_link_recovered` | Microwave link status recovers and returns to Up. | Info | Standby microwave link {link_id} has recovered. Reachability checks successful. |
| `fiber_util_high` | Primary fiber utilization crosses the critical threshold (default 90%). | Warning | High fiber utilization detected on link {link_id}: {util_pct}% (Capacity: {cap} Mbps). |
| `fiber_util_near_cap` | Primary fiber utilization enters the warning range (70% - 90%). | Warning | Fiber utilization approaching capacity on link {link_id}: {util_pct}% (Capacity: {cap} Mbps). |
| `mw_util_high` | Standby microwave utilization crosses the warning threshold (default 70%). | Warning | High backup microwave utilization detected on link {link_id}: {util_pct}%. |
| `consecutive_timeouts` | Reachability checks fail consecutively on a microwave link, crossing the timeout threshold (default 5). | Critical | Link {link_id} reached {timeouts} consecutive ping timeouts. Terminal remains unreachable. |
| `ping_service_error` | The ping scheduler encounters an unrecoverable SSH gateway connection error. | Error | Network monitor scheduler error: {error_msg}. Background checks suspended. |

---

## 2. Notification Delivery Architecture

The application implements a dual-channel notification delivery system: **In-App Notifications** and **SMTP Email Alerts**.

### 2.1 In-App Notification Lifecycle
- **Record Creation**: When a trigger event occurs, the system creates a new record in the `InAppNotification` table for each user subscribed to that event type.
- **Unread Count**: The navigation header displays a real-time unread count badge on the notification bell icon. The frontend polls this count via `GET /api/notifications/unread-count` every 60 seconds.
- **Notification Page (`/notifications`)**: Users can view their notifications, sorted chronologically with the newest alerts first. Each alert displays a severity badge and the affected Link ID.
- **Marking as Read**: Users can mark individual notifications as read or dismiss all alerts at once. This updates `is_read = True` inside the database, clearing them from the unread badge count.

### 2.2 SMTP Email Delivery
- **Background Worker**: Email notifications are processed asynchronously by a background worker thread, ensuring alert transmissions do not block the active scheduling loops or user sessions.
- **Connection Handshake**: Loads configuration parameters from the `SmtpConfig` table, decrypting passwords using the symmetric Fernet keys. Establishes a connection to the mail server using either STARTTLS or SMTPS, as configured.
- **Audit Logging**: On success, logs an audit entry to the `SystemLog` table under the `notifications` category. On delivery failure, logs the error details to the `SystemLog` to help diagnose SMTP issues.

---

## 3. Email Layout Templates

SMTP emails are transmitted in multipart format containing both plain text and structured HTML.

### 3.1 Plain Text Template

```
[MW LINK MONITOR ALERTS] - {severity_label} - EVENT: {event_type}
------------------------------------------------------------
Affected Link: {link_id}
Region/LEG: {leg_name}
Site Path: {site_a} <===> {site_b}
Microwave IP: {mw_ip}

Detail Message:
{message_text}

Log Timestamp: {timestamp_iso}
------------------------------------------------------------
Do not reply to this automated diagnostic notification message.
```

### 3.2 HTML Email Template

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: sans-serif; background-color: #0f1117; color: #e8eaf0; padding: 20px; }
    .card { background-color: #1a1d27; border-top: 4px solid #ff4d6a; border-radius: 4px; padding: 24px; max-width: 600px; margin: 0 auto; }
    .card.warning { border-top-color: #ffb547; }
    .card.info { border-top-color: #00c2a8; }
    .header { font-size: 18px; font-weight: bold; color: #ff4d6a; margin-bottom: 16px; }
    .header.warning { color: #ffb547; }
    .header.info { color: #00c2a8; }
    .detail-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    .detail-table td { padding: 10px; border-bottom: 1px solid #2a2d3e; font-size: 13px; }
    .footer { font-size: 11px; color: #7a8099; text-align: center; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="card {severity_class}">
    <div class="header {severity_class}">NETWORK MONITOR NOTIFICATION</div>
    <p>An automated diagnostic system trigger has logged a network status change.</p>
    <table class="detail-table">
      <tr><td><strong>Link ID</strong></td><td style="font-family: monospace; color:#00c2a8;">{link_id}</td></tr>
      <tr><td><strong>Event</strong></td><td>{event_label}</td></tr>
      <tr><td><strong>Path</strong></td><td>{site_a} to {site_b}</td></tr>
      <tr><td><strong>Microwave IP</strong></td><td>{mw_ip}</td></tr>
      <tr><td><strong>Detail</strong></td><td>{message_text}</td></tr>
      <tr><td><strong>Timestamp</strong></td><td>{timestamp_iso}</td></tr>
    </table>
    <p class="footer">This is an automated system diagnostic notification. Do not reply directly to this mail box.</p>
  </div>
</body>
</html>
```

---

## 4. User Alert Subscriptions

Users can manage their notification subscriptions from their profile interface.

- **Initialization**: When a new user account is created, the system automatically inserts subscription records for each event key in the `NotificationSubscription` table, defaulting to `is_subscribed = True`.
- **Target Routing Criteria**: When an alert fires, the system queries the active directory to identify recipients who meet all of the following criteria:
  1. The user account is active (`is_active = True`).
  2. The user account is not locked (`is_locked = False`).
  3. The user has an email address registered in the database.
  4. The user has an active subscription record (`is_subscribed = True`) matching the target event key.

---

## 5. Anti-Spam Rules and Throttle Controls

To prevent alert fatigue on NOC terminals during network outages or utilization spikes, the notification engine enforces strict anti-spam rules.

### 5.1 Outage State Lock (`mw_link_down`)
- **Control Strategy**: The `mw_link_down` alert fires exactly once when a link transitions from Up to Down.
- **Throttling**: While the link remains down, subsequent ping failures do not trigger additional `mw_link_down` notifications.

### 5.2 Hysteresis Constraints for Utilization Thresholds
To prevent repeating alerts when traffic utilization fluctuates around threshold values (e.g., repeatedly crossing the 90% mark), the system enforces a 10% hysteresis buffer.
- **High Trigger**: An alert is generated the first time utilization crosses the warning (70%) or critical (90%) threshold.
- **Reset Buffer**: The alert state is not cleared until utilization drops back below the threshold by at least 10% (i.e., below 60% for warning, or 80% for critical). Traffic must drop below this reset threshold before a new alert can be triggered.

### 5.3 Exponential Reminders (`consecutive_timeouts`)
- **Control Strategy**: A timeout alert is triggered when a microwave link reaches 5 consecutive timeouts.
- **Reminder Intervals**: If the link remains down, subsequent notifications are throttled, firing only at 10-cycle intervals thereafter (e.g., at 15, 25, 35 consecutive timeouts).

### 5.4 Recovery Confirmation (`mw_link_recovered`)
- **Control Strategy**: An alert is generated when a microwave link status transitions back to Up.
- **Outage Clear**: This recovery notification immediately clears the down state tracking flags, priming the link to trigger new down alerts if subsequent ping checks fail.
