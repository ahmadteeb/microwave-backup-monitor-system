# 01 — Database Models

## 1. Declarative Models

This document details every table, field, constraint, relationship, and index inside the database. It serves as the single source of truth for the database schema in both development (SQLite) and production (PostgreSQL) environments.

---

### 1.1 SetupState (Code Table: `setup_state`)

This table stores whether the initial setup wizard has been completed. It must only contain a single row with ID equal to one.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique identifier. Enforced to be exactly `1`. |
| `is_complete` | Boolean | Not Null, Default `False` | Is Complete | Toggle representing whether the wizard was submitted successfully. |
| `completed_at` | DateTime | Nullable | Completed At | The exact timestamp when the wizard was finished. |

---

### 1.2 User (Code Table: `user`)

Stores core user details, credential hashes, account locking parameters, and operational states.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `username` | String(64) | Unique, Not Null, Index | Username | Lowercase login identifier containing only alphanumeric characters and hyphens. |
| `full_name` | String(128) | Not Null | Full Name | The user's complete name (without any underscores). |
| `email` | String(256) | Unique, Not Null | Email Address | Primary contact address for email alerts. |
| `password_hash` | String(256) | Not Null | Password Hash | Secure password representation hashed using `bcrypt` (minimum cost factor 12). |
| `role` | Enum | Not Null | User Role | Administrative grouping. Values: `admin`, `operator`, `viewer`. |
| `is_active` | Boolean | Not Null, Default `True` | Is Active | Indicates whether the user can log in. |
| `is_locked` | Boolean | Not Null, Default `False` | Is Locked | Lock state triggered on consecutive login failures. |
| `locked_until` | DateTime | Nullable | Locked Until | Expiration timestamp of the account lockout period. |
| `failed_login_count` | Integer | Not Null, Default `0` | Failed Login Count | Running count of unsuccessful login attempts since the last success. |
| `force_password_change` | Boolean | Not Null, Default `False` | Force Password Change | Flag requiring the user to change their password on their next login session. |
| `created_at` | DateTime | Not Null, Default `utcnow` | Created At | Timestamp of account creation. |
| `updated_at` | DateTime | Not Null, Default `utcnow`, onupdate | Updated At | Timestamp of the last configuration change. |
| `last_login_at` | DateTime | Nullable | Last Login At | Timestamp of the most recent successful login event. |

---

### 1.3 UserPermission (Code Table: `user_permission`)

Stores granular override permissions for specific users. An override takes precedence over the role default.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `user_id` | Integer | Foreign Key (`user.id`), Not Null, Index | User ID | Relates the override to a specific user. |
| `permission_key` | String(64) | Not Null | Permission Key | Code representation of the discrete permission (e.g., `links.delete`). |
| `is_granted` | Boolean | Not Null | Is Granted | True indicates explicit grant; False indicates explicit denial. |

- **Unique Constraint**: Combined unique check on `(user_id, permission_key)`.
- **Relationship**: Direct foreign key relation linking multiple overrides to a single `User` record.

---

### 1.4 NotificationSubscription (Code Table: `notification_subscription`)

Maintains subscription states for each user against distinct alert types.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `user_id` | Integer | Foreign Key (`user.id`), Not Null, Index | User ID | Relates the subscription preference to a user. |
| `event_key` | String(64) | Not Null | Event Key | Code identifier of the trigger event (e.g., `mw_link_down`). |
| `is_subscribed` | Boolean | Not Null, Default `True` | Is Subscribed | Toggle representing whether the user wants to receive alerts for this event. |

- **Unique Constraint**: Combined unique check on `(user_id, event_key)`.
- **Relationship**: Direct link back to the `User` table.

---

### 1.5 InAppNotification (Code Table: `in_app_notification`)

Maintains delivery records of in-app alerts sent to specific user dashboards.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `user_id` | Integer | Foreign Key (`user.id`), Not Null, Index | User ID | Targeted recipient user. |
| `event_key` | String(64) | Not Null | Event Key | Alert event type that triggered the notification. |
| `severity` | Enum | Not Null | Severity | Severity badge categorization: `critical`, `warning`, `info`, `error`. |
| `link_id` | String(32) | Nullable, Index | Link ID | Optional reference pointing to the affected link. |
| `message` | Text | Not Null | Message Text | Detailed alert text shown on the notification listing page. |
| `is_read` | Boolean | Not Null, Default `False` | Is Read | Status tracking whether the user has dismissed or read the alert. |
| `created_at` | DateTime | Not Null, Default `utcnow`, Index | Created At | Exact timestamp of alert generation. |

---

### 1.6 Link (Code Table: `link`)

Stores the physical network topology configuration of monitored microwave link pairs.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `link_id` | String(32) | Unique, Not Null, Index | Link ID | Alphanumeric unique identifier matching pattern (e.g., `BK-001`). Uppercase enforced. |
| `leg_name` | String(64) | Not Null, Index | LEG Name | Human-readable region/logical division grouping (e.g., `LEG598`). |
| `site_a` | String(128) | Not Null | Site A | Node site name on the starting end of the path. |
| `site_b` | String(128) | Not Null | Site B | Node site name on the terminating end of the path. |
| `equipment_a` | String(128) | Nullable | Equipment Model A | Hardware vendor/model deployed at Site A. |
| `equipment_b` | String(128) | Nullable | Equipment Model B | Hardware vendor/model deployed at Site B. |
| `mw_ip` | String(45) | Not Null | Microwave IP Address | Destination IPv4 or IPv6 target monitored during pings. |
| `link_type` | String(64) | Nullable, Default `"Microwave Backup"` | Link Type | Informational grouping representing physical media. |
| `notes` | Text | Nullable | Notes | Field for operator comments and system documentation. |
| `is_active` | Boolean | Not Null, Default `True` | Is Active | Toggle determining whether background pings are active on this link. |
| `created_at` | DateTime | Not Null, Default `utcnow` | Created At | Creation timestamp. |
| `updated_at` | DateTime | Not Null, Default `utcnow`, onupdate | Updated At | Configuration change timestamp. |
| `created_by` | Integer | Foreign Key (`user.id`), Nullable | Created By | Tracking identifier of the user who added the link. |

---

### 1.7 PingResult (Code Table: `ping_result`)

Maintains history entries generated by periodic reachability checks.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `link_id` | Integer | Foreign Key (`link.id`), Not Null, Index | Link ID | Affected network link record. |
| `timestamp` | DateTime | Not Null, Index | Timestamp | The exact moment when the ping execution commenced. |
| `is_reachable` | Boolean | Not Null | Is Reachable | Reachability result of the ICMP check. |
| `latency_ms` | Float | Nullable | Latency MS | Calculated average round-trip time. Null if the host is unreachable. |
| `raw_output` | Text | Nullable | Raw Output | Full stdout response captured from the remote terminal execution. |
| `triggered_by` | Enum | Not Null | Triggered By | Origin of check. Values: `scheduler` or `manual`. |
| `triggered_by_user_id` | Integer | Foreign Key (`user.id`), Nullable | Triggered By User ID | Captures the user ID if the check was executed manually. |

- **Composite Index**: An index named `idx_ping_result_link_timestamp` on `(link_id, timestamp DESC)` to speed up loading of recent ping details.

---

### 1.8 MetricSnapshot (Code Table: `metric_snapshot`)

Stores telemetry metrics representing traffic levels and bandwidth throughput across paths.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `link_id` | Integer | Foreign Key (`link.id`), Not Null, Index | Link ID | Relates the telemetry capture to a specific hardware link. |
| `timestamp` | DateTime | Not Null, Index | Timestamp | The exact moment the metric harvest was finalized. |
| `fiber_util_mbps` | Float | Nullable | Fiber Util Mbps | Calculated current primary route bandwidth in Megabits per second. |
| `fiber_util_pct` | Float | Nullable | Fiber Util Pct | Percentage of physical fiber capacity currently consumed. |
| `fiber_peak_mbps` | Float | Nullable | Fiber Peak Mbps | Peak utilization registered across the tracking interval. |
| `fiber_peak_at` | DateTime | Nullable | Fiber Peak At | The exact moment peak fiber utilization was registered. |
| `fiber_capacity_mbps` | Float | Nullable | Fiber Capacity Mbps | Hardwired max operational speed threshold of primary link. |
| `mw_util_mbps` | Float | Nullable | Microwave Util Mbps | Current standby microwave path bandwidth usage in Megabits per second. |
| `mw_util_pct` | Float | Nullable | Microwave Util Pct | Percentage of backup microwave capacity currently utilized. |
| `mw_peak_mbps` | Float | Nullable | Microwave Peak Mbps | Historical peak utilization captured across the backup route. |
| `mw_peak_at` | DateTime | Nullable | Microwave Peak At | The exact moment the backup microwave peaked. |
| `mw_capacity_mbps` | Float | Nullable | Microwave Capacity Mbps | Hardwired max standby route interface speed. |

- **Composite Index**: An index named `idx_metric_snapshot_link_timestamp` on `(link_id, timestamp DESC)` for fast dashboard lookups.

---

### 1.9 LinkStatus (Code Table: `link_status`)

Stores materialized summaries containing latest statuses and recent check details for each link. This optimized cache avoids querying millions of records during dashboard lists.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `link_id` | Integer | Foreign Key (`link.id`), Unique, Not Null, Index | Link ID | Relates the cache back to exactly one link. |
| `mw_status` | Enum | Not Null | Microwave Status | Current evaluated status: `up`, `down`, `high`, `checking`, `unknown`. |
| `last_ping_at` | DateTime | Nullable | Last Ping At | Timestamp of the most recent reachability check. |
| `last_ping_latency_ms` | Float | Nullable | Last Ping Latency | Latency of the last success check. |
| `consecutive_timeouts` | Integer | Not Null, Default `0` | Consecutive Timeouts | Current running tally of failed reachability cycles since the last success. |
| `last_metric_at` | DateTime | Nullable | Last Metric At | Timestamp of the most recent metric collection. |
| `fiber_util_pct` | Float | Nullable | Fiber Util Pct | Latest calculated primary link utilization percentage. |
| `mw_util_pct` | Float | Nullable | Microwave Util Pct | Latest calculated backup link utilization percentage. |
| `data_fresh` | Boolean | Not Null, Default `False` | Data Fresh | Evaluated state indicating whether metrics were updated within 5 minutes. |

---

### 1.10 JumpServer (Code Table: `jump_server`)

Maintains SSH credentials needed to navigate beyond the server gateway to reach link devices. This table only holds a single active configuration row with ID equal to one.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. Enforced to be exactly `1`. |
| `host` | String(256) | Not Null | Host | Destination IP or Hostname of the terminal gateway server. |
| `port` | Integer | Not Null, Default `22` | Port | Gateway port listening for secure shell queries. |
| `username` | String(128) | Not Null | Username | Terminal logon credential username. |
| `password` | String(256) | Nullable | Password | Optional credential string. Encrypted at rest via Fernet keys. |
| `private_key` | Text | Nullable | Private Key | Optional private cryptographic key. Encrypted at rest via Fernet keys. |
| `updated_at` | DateTime | Not Null, Default `utcnow` | Updated At | Timestamp of last setup change. |
| `updated_by` | Integer | Foreign Key (`user.id`), Nullable | Updated By | Tracks the user account that modified credentials. |

---

### 1.11 SmtpConfig (Code Table: `smtp_config`)

Manages secure parameters used to transmit automated system alerts. Holds a single active row with ID equal to one.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. Enforced to be exactly `1`. |
| `host` | String(256) | Not Null | Host | Mail server address utilized for outgoing transmissions. |
| `port` | Integer | Not Null | Port | SMTP port. |
| `username` | String(256) | Nullable | Username | Optional login credential username. |
| `password` | String(256) | Nullable | Password | Optional login credential password. Encrypted at rest via Fernet keys. |
| `from_address` | String(256) | Not Null | From Address | Email address displayed on outgoing messages. |
| `use_tls` | Boolean | Not Null, Default `True` | Use TLS | Flag establishing secure sessions using STARTTLS logic. |
| `use_ssl` | Boolean | Not Null, Default `False` | Use SSL | Flag establishing secure connections directly via SMTPS. |
| `updated_at` | DateTime | Not Null, Default `utcnow` | Updated At | Timestamp of last configuration change. |
| `updated_by` | Integer | Foreign Key (`user.id`), Nullable | Updated By | Logged tracking user who modified settings. |

---

### 1.12 AppSettings (Code Table: `app_settings`)

Manages session, scheduling, and alerting thresholds. Holds a single configuration row with ID equal to one.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. Enforced to be exactly `1`. |
| `session_timeout_minutes` | Integer | Not Null, Default `480` | Session Timeout Minutes | Session lifetime in minutes. Default value equals 8 hours of inactivity. |
| `ping_interval_seconds` | Integer | Not Null, Default `60` | Ping Interval Seconds | Background delay between automated ICMP check sweeps. |
| `metric_poll_interval_seconds` | Integer | Not Null, Default `60` | Metric Poll Interval Seconds | Delay between router telemetry sweeps. |
| `consecutive_timeout_alert_threshold` | Integer | Not Null, Default `5` | Consecutive Timeout Alert Threshold | Timeout threshold required before raising critical alerts. |
| `util_warning_threshold_pct` | Float | Not Null, Default `70.0` | Util Warning Threshold Pct | Lower utilization limit triggering amber warnings. |
| `util_critical_threshold_pct` | Float | Not Null, Default `90.0` | Util Critical Threshold Pct | Upper utilization limit triggering red critical alerts. |
| `updated_at` | DateTime | Not Null, Default `utcnow` | Updated At | Timestamp of last parameter adjustment. |
| `updated_by` | Integer | Foreign Key (`user.id`), Nullable | Updated By | Logged tracking user who modified system constants. |

---

### 1.13 SystemLog (Code Table: `system_log`)

Stores the secure application audit trail. This table is strictly write-only.

| Code Field | Type | Constraints | Human-Facing Label | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | ID | Unique sequence identifier. |
| `timestamp` | DateTime | Not Null, Index | Timestamp | The exact moment the logged transaction was recorded. |
| `category` | String(32) | Not Null, Index | Category | Security category: `auth`, `users`, `links`, `config`, `scheduler`, `notifications`. |
| `event` | String(64) | Not Null, Index | Event Name | The operation key identifying the specific transaction. |
| `actor` | String(128) | Not Null, Index | Actor | The user name responsible for the execution, or `"system"`. |
| `target` | String(256) | Nullable, Index | Target | Relates the action to a target resource. |
| `detail` | JSON | Nullable | Detail | Structured JSON payload containing detailed metadata. |
| `ip_address` | String(45) | Nullable | IP Address | Network IP of the machine making the request. |

---

## 2. Relationships

The database enforces the following relations and cascade behaviors:

- **`User` (1) ── (Many) `UserPermission`**: Deleting a user removes their custom permissions overrides (`cascade="all, delete-orphan"`).
- **`User` (1) ── (Many) `NotificationSubscription`**: Deleting a user cleans up their subscriptions (`cascade="all, delete-orphan"`).
- **`User` (1) ── (Many) `InAppNotification`**: Deleting a user removes their messages (`cascade="all, delete-orphan"`).
- **`Link` (1) ── (Many) `PingResult`**: Deleting a link cleans up its historical check entries (`cascade="all, delete-orphan"`).
- **`Link` (1) ── (Many) `MetricSnapshot`**: Deleting a link cascades to remove all bandwidth measurements (`cascade="all, delete-orphan"`).
- **`Link` (1) ── (1) `LinkStatus`**: Deleting a link deletes its materialized status cache (`cascade="all, delete-orphan"`).

---

## 3. Index Recommendations

To support fast load times on high-density displays, the following indexes are applied:

1.  `idx_user_username`: Enforces unique logins and speeds up session lookup.
2.  `idx_link_link_id`: Unique index enforcing uppercase key constraints on inventory records.
3.  `idx_link_leg_name`: Speeds up query groupings when operators filter lists by region divisions.
4.  `idx_ping_result_link_timestamp`: Index on `(link_id, timestamp DESC)` for fast lookups of recent latency statistics.
5.  `idx_metric_snapshot_link_timestamp`: Index on `(link_id, timestamp DESC)` for rendering trend metrics.
6.  `idx_system_log_category_timestamp`: Compound index on `(category, timestamp DESC)` to speed up audit log filtering.

---

## 4. Seeding Logic

On application start, the initialization routine must populate default parameters inside the configuration tables if they are empty:

- **SetupState**: Insert a single row with `id = 1` and `is_complete = False` to prevent unauthorized entry bypasses.
- **AppSettings**: Seed a configuration row with default settings (`session_timeout_minutes = 480`, `ping_interval_seconds = 60`, etc.) under `id = 1` so that default timings exist prior to completing the setup wizard.
