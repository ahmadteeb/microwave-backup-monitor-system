# 00 — Project Overview

## Project Summary

The **MW Backup Link Monitor** is a NOC-style web dashboard that provides real-time visibility into microwave (MW) backup link health across a telecommunications network. Network operations center (NOC) engineers use it to:

- **Inventory** all MW backup links with their site-pair endpoints and IP addresses.
- **Monitor reachability** by periodically pinging each MW link's IP through a jump server over SSH.
- **Track utilization** of both fiber (primary) and MW (backup) paths so operators can spot links approaching capacity.
- **Detect degradation** via latency measurements, packet-loss indicators, and 24-hour stability trend charts.
- **Act quickly** through a single-pane-of-glass dashboard with KPI cards, color-coded status badges, and a live ping activity log.

### Who Uses It

- **NOC Engineers** — primary users; monitor link health on shift, respond to DOWN/TIMEOUT alerts.
- **Network Planners** — review utilization trends to decide when to upgrade capacity.
- **System Administrators** — configure jump server credentials and ping parameters.

### Key Constraints

| Constraint | Detail |
|---|---|
| Backend stack | Python 3.10+, Flask, SQLAlchemy ORM, SQLite (dev) |
| Frontend stack | Plain HTML + CSS + vanilla JavaScript — no React, Vue, Angular, or any UI framework |
| SSH connectivity | All pings route through a jump server using the provided `SSHService` class (Paramiko). Direct pinging from the Flask host is **not** permitted. |
| Scheduler | APScheduler runs inside the Flask process for periodic ping cycles |
| Charting | Chart.js (loaded from CDN) for the Network Stability Trend bar chart |
| Database | SQLite file for development; schema must be portable to PostgreSQL by changing one connection string |
| Authentication | Out of scope for v1. The `SYSTEM_AUTH: VALIDATED_USER_04` line in the modal is a static placeholder. |
| Deployment | Single-machine deployment; no containerization required for v1 |

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Browser (Frontend)                          │
│  index.html + main.css + components.css + JS modules (dashboard,    │
│  table, modal, pinglog, charts)                                      │
│  ── polls REST API every 10-30s ──                                   │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  HTTP (JSON)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Flask Application                             │
│                                                                      │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  REST API     │  │  APScheduler     │  │  Static File Server   │  │
│  │  /api/links   │  │  (BackgroundSch) │  │  /frontend/*          │  │
│  │  /api/dashboard│  │  ping_cycle job  │  │                       │  │
│  │  /api/ping-log│  │  runs every 60s  │  │                       │  │
│  │  /api/jumpsvr │  │                  │  │                       │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────────────────────┘  │
│         │                   │                                        │
│         ▼                   ▼                                        │
│  ┌─────────────────────────────────────┐                             │
│  │        ping_service.py              │                             │
│  │  connect_jump() → ping_link()       │                             │
│  │  parse_output() → store_result()    │                             │
│  └──────────────┬──────────────────────┘                             │
│                 │                                                    │
│         ┌───────┴───────┐                                            │
│         ▼               ▼                                            │
│  ┌────────────┐  ┌─────────────┐                                     │
│  │  SQLite DB  │  │ SSHService  │                                     │
│  │  models:    │  │ (Paramiko)  │                                     │
│  │  Link       │  └──────┬──────┘                                     │
│  │  PingResult │         │ SSH                                        │
│  │  Metric...  │         ▼                                            │
│  │  JumpServer │  ┌─────────────┐                                     │
│  └────────────┘  │ Jump Server  │                                     │
│                  │ (gateway)    │                                     │
│                  └──────┬──────┘                                      │
│                         │ SSH hop                                     │
│                         ▼                                            │
│                  ┌──────────────┐                                     │
│                  │ MW Link IPs  │                                     │
│                  │ (ping target)│                                     │
│                  └──────────────┘                                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Planned Files and Folders

| Path | Description |
|---|---|
| `run.py` | Flask application entry point; creates app, starts scheduler, serves frontend |
| `requirements.txt` | Python dependencies: Flask, SQLAlchemy, APScheduler, Paramiko, python-dotenv |
| `.env.example` | Template for all environment variables with defaults and descriptions |
| `README.md` | Setup instructions, usage guide, and architecture summary |
| **`/app`** | |
| `app/__init__.py` | Flask app factory; registers blueprints, initializes DB and scheduler |
| `app/config.py` | Configuration class that reads from `.env` and exposes settings |
| `app/models.py` | SQLAlchemy models: Link, PingResult, MetricSnapshot, JumpServer |
| **`/app/routes`** | |
| `app/routes/__init__.py` | Blueprint registration helper |
| `app/routes/links.py` | CRUD routes for `/api/links` and manual ping trigger |
| `app/routes/dashboard.py` | KPI and stability trend routes for `/api/dashboard/*` |
| `app/routes/pinglog.py` | Route for `/api/ping-log` (recent ping results) |
| `app/routes/jumpserver.py` | Routes for `/api/jumpserver` (get/update jump server config) |
| **`/app/services`** | |
| `app/services/ssh_service.py` | The provided `SSHService` class — copied verbatim, not modified |
| `app/services/ping_service.py` | Ping execution logic: connect to jump server, run ping commands, parse output, store results |
| `app/services/scheduler.py` | APScheduler configuration: job definitions, interval triggers, lifecycle hooks |
| **`/frontend`** | |
| `frontend/index.html` | Main dashboard page — single-page layout matching the NOC-style UI |
| `frontend/css/main.css` | Global styles: CSS custom properties, reset, typography, dark theme base |
| `frontend/css/components.css` | Component-level styles: cards, table, sidebar, modal, badges, bars, chart containers |
| `frontend/js/dashboard.js` | KPI card polling, system health badge, uptime/next-check display |
| `frontend/js/table.js` | Link inventory table rendering, pagination, search, filter integration |
| `frontend/js/modal.js` | CONFIGURE_MICROWAVE_LINK modal: open/close, form validation, save/edit/delete |
| `frontend/js/pinglog.js` | Ping activity log: polling, auto-scroll, color-coded entries |
| `frontend/js/charts.js` | Chart.js Network Stability Trend bar chart initialization and data refresh |
| **`/plan`** | |
| `plan/00_overview.md` | This file — project summary, architecture, file listing |
| `plan/01_database.md` | Database models and schema design |
| `plan/02_api_routes.md` | Full REST API specification |
| `plan/03_ssh_ping_service.md` | SSH integration and ping execution strategy |
| `plan/04_frontend.md` | Frontend layout, components, polling, and theming plan |
| `plan/05_project_structure.md` | Complete file tree with per-file descriptions |
| `plan/06_implementation_order.md` | Phased build sequence with acceptance criteria |
| `plan/07_config_and_env.md` | Environment variables and Flask configuration plan |

---

## Environment Variables Needed

| Variable | Purpose |
|---|---|
| `JUMP_HOST` | Hostname or IP of the SSH jump server |
| `JUMP_PORT` | SSH port of the jump server (default 22) |
| `JUMP_USER` | SSH username for jump server authentication |
| `JUMP_PASSWORD` | SSH password for jump server authentication |
| `PING_INTERVAL_SECONDS` | How often the scheduler runs a full ping cycle (default 60) |
| `PING_COUNT` | Number of ICMP packets per ping (default 3) |
| `PING_TIMEOUT` | Timeout in seconds per ping attempt (default 2) |
| `DATABASE_URL` | SQLAlchemy connection string (default `sqlite:///mw_monitor.db`) |
| `SECRET_KEY` | Flask secret key for session signing |
| `LOG_LEVEL` | Python logging level (default `INFO`) |

---

## Open Questions

1. **Authentication scope** — The UI shows `SYSTEM_AUTH: VALIDATED_USER_04` in the modal footer. Is this purely cosmetic for v1, or should we stub a simple auth mechanism (e.g., API key header)?
2. **Metric data source** — The MetricSnapshot model stores utilization data, but the screenshots show Fiber Util and MW Util columns. Should v1 support manual metric entry only, or should we stub an SNMP/API collector interface for future use?
3. **Topology Monitor panel** — The screenshot shows a network topology visualization with nodes and links. Should v1 render a static placeholder image, or should we implement a basic interactive topology (e.g., using Canvas/SVG)?
4. **Export functionality** — The table header shows filter and download icons. Should v1 support CSV export of the link inventory?
5. **Notification bell** — The top bar shows a notification bell icon. Should v1 implement any notification system, or is this a placeholder for future work?
