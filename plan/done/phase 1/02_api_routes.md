# 02 — API Routes

## Overview

All routes are JSON REST endpoints under the `/api` prefix. Flask Blueprints group routes by domain. Responses use standard HTTP status codes. Error responses return `{"error": "<message>"}`.

---

## Link Routes (`/api/links`) — Blueprint: `links_bp`

### GET /api/links

**Purpose**: List all links with their latest ping result and latest metric snapshot joined.

- **Query parameters**: `status` (optional, filter: `up`, `down`, `timeout`, `high`), `leg` (optional, filter by leg_name), `search` (optional, match against link_id or leg_name), `page` (default 1), `per_page` (default 20)
- **Response** (200):
  ```
  {
    "links": [
      {
        "id": 1, "link_id": "MW-B-402", "leg_name": "North-1",
        "site_a": "...", "site_b": "...", "mw_ip": "10.0.0.1",
        "latest_ping": { "reachable": true, "latency_ms": 14, "timestamp": "..." },
        "latest_metric": { "fiber_util_pct": 80, "mw_util_pct": 12 },
        "status": "UP"
      }
    ],
    "total": 142, "page": 1, "per_page": 20, "pages": 8
  }
  ```
- **Status derivation**: `UP` if latest ping reachable and latency < threshold; `DOWN` if unreachable; `TIMEOUT` if unreachable and raw_output contains timeout pattern; `HIGH` if mw_util_pct > 70.
- **Read-heavy**: Yes. Polled by the frontend table every 30 seconds.

---

### POST /api/links

**Purpose**: Create a new link (config fields only, no metrics).

- **Request body**:
  ```
  {
    "link_id": "MW-TX-9904",       // required, unique
    "leg_name": "NORTH_BACKHAUL_01", // required
    "site_a": "ALPHA_BASE",          // optional
    "site_b": "DELTA_REPEATER",      // optional
    "mw_ip": "10.0.5.22",            // required, valid IPv4
    "equipment_a": "...",            // optional
    "equipment_b": "...",            // optional
    "link_type": "microwave",       // optional
    "notes": "..."                  // optional
  }
  ```
- **Response** (201): The created link object.
- **Errors**: 400 if `link_id` missing/empty, `mw_ip` missing or invalid IPv4 format, `leg_name` missing. 409 if `link_id` already exists.
- **Write-heavy**: No — infrequent operation.

---

### PUT /api/links/\<id\>

**Purpose**: Update a link's configuration fields.

- **URL param**: `id` — integer primary key.
- **Request body**: Same shape as POST, all fields optional (partial update supported).
- **Response** (200): The updated link object.
- **Errors**: 404 if link not found. 400 if `mw_ip` provided but invalid. 409 if `link_id` changed to one that already exists.

---

### DELETE /api/links/\<id\>

**Purpose**: Delete a link and all its ping results and metric snapshots (cascade).

- **Response** (200): `{"message": "Link deleted", "link_id": "MW-B-402"}`
- **Errors**: 404 if link not found.

---

### GET /api/links/\<id\>

**Purpose**: Single link detail with last 24h of ping history and metric snapshots.

- **Response** (200):
  ```
  {
    "link": { ...link fields... },
    "ping_history": [ { "timestamp": "...", "reachable": true, "latency_ms": 14 }, ... ],
    "metric_history": [ { "timestamp": "...", "fiber_util_pct": 80, "mw_util_pct": 12 }, ... ]
  }
  ```
- **Errors**: 404 if link not found.
- **Read-heavy**: Moderate — used when a user clicks on a link row for detail view.

---

### POST /api/links/\<id\>/ping

**Purpose**: Trigger an immediate manual ping for one link, bypassing the scheduler cycle.

- **Request body**: None.
- **Response** (200): The new PingResult object: `{ "reachable": true, "latency_ms": 14, "packet_loss": 0.0, "timestamp": "..." }`
- **Errors**: 404 if link not found. 503 if jump server not configured or unreachable.
- **Behavior**: Runs the ping synchronously (blocks for ~5 seconds max). Uses a separate SSH connection so it does not conflict with any running scheduler cycle. Returns the result immediately.
- **Write-heavy**: Yes — writes a PingResult row.

---

## Dashboard Routes (`/api/dashboard`) — Blueprint: `dashboard_bp`

### GET /api/dashboard/kpi

**Purpose**: Return aggregated KPI values for the four dashboard cards.

- **Response** (200):
  ```
  {
    "total_links": 142,
    "mw_reachable": 138,
    "mw_unreachable": 4,
    "high_utilization": 12,
    "last_updated": "2026-05-04T14:22:00Z"
  }
  ```
- **Logic**: `total_links` = count of all Link rows. `mw_reachable` = count of links whose latest PingResult has `reachable=True`. `mw_unreachable` = total - reachable. `high_utilization` = count of links whose latest MetricSnapshot has `mw_util_pct > 70`.
- **Read-heavy**: Yes. Polled every 30 seconds.

---

### GET /api/dashboard/stability

**Purpose**: Return 24h ping success rate per hour for the Network Stability Trend chart.

- **Response** (200):
  ```
  {
    "hours": [
      { "hour": "2026-05-04T00:00:00Z", "total_pings": 142, "successful": 138, "failed": 4, "success_rate": 97.2 },
      ...
    ]
  }
  ```
- **Logic**: Group PingResult rows from the last 24 hours by hour. For each hour, count total pings and pings where `reachable=True`. Compute success rate as percentage.
- **Read-heavy**: Yes. Polled every 60 seconds (chart updates less frequently than KPI cards).

---

## Ping Log Routes (`/api/ping-log`) — Blueprint: `pinglog_bp`

### GET /api/ping-log

**Purpose**: Return the last N ping results across all links, newest first. Powers the sidebar ping activity log.

- **Query parameters**: `limit` (default 50, max 200)
- **Response** (200):
  ```
  {
    "results": [
      {
        "link_id": "MW-B-402", "timestamp": "2026-05-04T14:22:18Z",
        "reachable": true, "latency_ms": 14, "status_text": "PING OK"
      },
      ...
    ]
  }
  ```
- **Status text derivation**: `PING OK` if reachable; `TIMEOUT` if unreachable and latency null; `PKT_LOSS` if reachable but packet_loss > 0.
- **Read-heavy**: Yes. Polled every 10 seconds.

---

## Jump Server Routes (`/api/jumpserver`) — Blueprint: `jumpserver_bp`

### GET /api/jumpserver

**Purpose**: Get current active jump server configuration with password masked.

- **Response** (200):
  ```
  {
    "id": 1, "host": "10.0.0.1", "port": 22, "username": "admin",
    "password": "••••••••", "active": true, "label": "Primary NOC Gateway"
  }
  ```
- **Note**: Password is always masked in the response. Never returned in plaintext over HTTP.

---

### PUT /api/jumpserver

**Purpose**: Update or create jump server configuration.

- **Request body**:
  ```
  {
    "host": "10.0.0.1",     // required
    "port": 22,              // optional, default 22
    "username": "admin",     // required
    "password": "secret123", // required (plaintext in request, encrypted on storage)
    "label": "Primary"       // optional
  }
  ```
- **Response** (200): The updated config (password masked).
- **Behavior**: If no active jump server exists, creates one. If one exists, updates it. Marks it active and deactivates any others.
- **Errors**: 400 if host or username missing.

---

## Polling Summary

| Endpoint | Poll interval | Consumer |
|---|---|---|
| `GET /api/dashboard/kpi` | 30 seconds | KPI cards |
| `GET /api/links` | 30 seconds | Link inventory table |
| `GET /api/ping-log` | 10 seconds | Sidebar ping activity log |
| `GET /api/dashboard/stability` | 60 seconds | Network Stability Trend chart |

---

## Open Questions

1. **Pagination for ping-log** — The sidebar shows a short scrolling list. Is a simple `limit` parameter sufficient, or should full cursor-based pagination be supported?
2. **Bulk operations** — Should v1 support bulk delete or bulk ping (e.g., ping all links in a specific LEG)?
3. **WebSocket alternative** — Polling at 10s intervals for the ping log is workable but not real-time. Should v2 consider WebSocket/SSE for push-based updates?
