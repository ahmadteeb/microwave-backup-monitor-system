# 01 — Database Design

## Overview

SQLAlchemy ORM with SQLite for development. Schema is portable to PostgreSQL by changing one connection string. All tables created via `db.create_all()` on app start.

---

## Model 1 — Link

Represents a single MW backup link in the inventory.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | Surrogate key |
| `link_id` | String(50) | Unique, not null, indexed | Human-readable ID (e.g., `MW-B-402`) |
| `leg_name` | String(100) | Not null | LEG/region name (e.g., `North-1`) |
| `site_a` | String(100) | Nullable | Site A node name |
| `site_b` | String(100) | Nullable | Site B node name |
| `mw_ip` | String(45) | Not null | IPv4 address pinged through jump server |
| `equipment_a` | String(100) | Nullable | Equipment at Site A |
| `equipment_b` | String(100) | Nullable | Equipment at Site B |
| `link_type` | String(50) | Nullable, default `'microwave'` | Link classification |
| `notes` | Text | Nullable | Free-text notes |
| `created_at` | DateTime | Not null, default `utcnow` | Creation timestamp |
| `updated_at` | DateTime | Not null, default `utcnow`, onupdate | Last update timestamp |

- `link_id` is unique/indexed because it is the primary search key.
- `mw_ip` is not null because every link must be pingable.
- `site_a`/`site_b` are nullable for progressive data entry.

---

## Model 2 — PingResult

One row per ping check per link.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | Surrogate key |
| `link_id` | Integer | FK → `link.id`, not null, indexed | Link that was pinged |
| `timestamp` | DateTime | Not null, default `utcnow`, indexed | When the ping ran |
| `reachable` | Boolean | Not null | True if at least one reply received |
| `latency_ms` | Float | Nullable | Average RTT in ms. Null when unreachable |
| `packet_loss` | Float | Nullable | Packet loss percentage (0–100) |
| `raw_output` | Text | Nullable | Full ping stdout for debugging |

- `raw_output` stored for audit; engineers inspect it when investigating intermittent issues.
- `packet_loss` separated from `reachable` because partial loss still counts as reachable but degraded.

---

## Model 3 — MetricSnapshot

Utilization metrics for fiber and MW paths at a point in time.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | Surrogate key |
| `link_id` | Integer | FK → `link.id`, not null, indexed | Owning link |
| `timestamp` | DateTime | Not null, default `utcnow`, indexed | Snapshot time |
| `fiber_util_pct` | Float | Nullable | Fiber utilization % (0–100) |
| `fiber_capacity_mbps` | Float | Nullable | Fiber capacity in Mbps |
| `mw_util_pct` | Float | Nullable | MW utilization % (0–100) |
| `mw_capacity_mbps` | Float | Nullable | MW capacity in Mbps |
| `source` | String(20) | Nullable, default `'manual'` | Data origin: `manual`, `snmp`, `api` |

- All metric fields nullable to allow partial data entry.
- `source` future-proofs for automated SNMP collection.

---

## Model 4 — JumpServer

SSH jump server configuration. Only one active at a time.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | Surrogate key |
| `host` | String(255) | Not null | Jump server hostname/IP |
| `port` | Integer | Not null, default `22` | SSH port |
| `username` | String(100) | Not null | SSH username |
| `password_encrypted` | String(500) | Not null | Fernet-encrypted password |
| `active` | Boolean | Not null, default `True` | Only one row should be active |
| `label` | String(100) | Nullable | Human-readable label |
| `created_at` | DateTime | Not null, default `utcnow` | Creation timestamp |
| `updated_at` | DateTime | Not null, default `utcnow`, onupdate | Last update timestamp |

- Passwords encrypted with Fernet (key from `SECRET_KEY`) — never stored in plaintext.
- Stored in DB (not just `.env`) so credentials can be updated via Settings UI without restart.

---

## Relationships

- **Link → PingResult**: One-to-many, `cascade='all, delete-orphan'`. Deleting a link removes all its ping history.
- **Link → MetricSnapshot**: One-to-many, `cascade='all, delete-orphan'`. Same cascade behavior.
- **JumpServer**: Standalone, no foreign keys to other models.

---

## Database Initialization

1. `db.create_all()` called inside `create_app()` within the app context — creates tables if they don't exist.
2. No Alembic/Flask-Migrate for v1. Schema is additive; SQLite file can be deleted and recreated during development.
3. If no JumpServer row exists, the scheduler logs a warning and skips ping cycles until one is configured via the API.

---

## Index Recommendations

| Table | Column(s) | Type | Justification |
|---|---|---|---|
| `link` | `link_id` | Unique | Fast lookup by display ID; uniqueness enforcement |
| `link` | `leg_name` | Non-unique | LEG_REGION filter queries |
| `ping_result` | `link_id, timestamp` | Composite (desc timestamp) | "Most recent ping for link X" — most frequent query |
| `ping_result` | `timestamp` | Non-unique | 24h stability chart time-range queries |
| `metric_snapshot` | `link_id, timestamp` | Composite (desc timestamp) | "Most recent metric for link X" |

---

## Open Questions

1. **Data retention** — PingResult rows accumulate fast (1 per link per minute). Should v1 include a retention policy (e.g., delete > 30 days)?
2. **MetricSnapshot entry** — Should we add `POST /api/links/<id>/metrics` for manual entry, or seed with demo data for v1?
3. **Password encryption** — Use `cryptography.fernet` (recommended) or simpler base64 with a security warning?
