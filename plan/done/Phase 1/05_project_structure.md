# 05 — Project Structure

## Complete File Tree

```
MW Backup Link Monitor System/
│
├── run.py                              ← Entry point: creates Flask app, starts scheduler
├── requirements.txt                    ← Python dependencies
├── .env.example                        ← Environment variable template with defaults
├── README.md                           ← Setup instructions, usage guide, architecture summary
│
├── app/
│   ├── __init__.py                     ← App factory: create_app(), register blueprints, init DB & scheduler
│   ├── config.py                       ← Configuration class reading from .env via python-dotenv
│   ├── models.py                       ← SQLAlchemy models: Link, PingResult, MetricSnapshot, JumpServer
│   │
│   ├── routes/
│   │   ├── __init__.py                 ← Blueprint registration helper (imports and registers all blueprints)
│   │   ├── links.py                    ← CRUD for /api/links + manual ping trigger
│   │   ├── dashboard.py               ← /api/dashboard/kpi and /api/dashboard/stability
│   │   ├── pinglog.py                  ← /api/ping-log (recent ping results)
│   │   └── jumpserver.py              ← /api/jumpserver (get/update jump server config)
│   │
│   └── services/
│       ├── __init__.py                 ← Empty init for package recognition
│       ├── ssh_service.py              ← SSHService class — copied verbatim from requirements, unmodified
│       ├── ping_service.py             ← Ping orchestration: connect, execute, parse, store results
│       └── scheduler.py               ← APScheduler BackgroundScheduler setup and job definitions
│
├── frontend/
│   ├── index.html                      ← Single-page dashboard HTML
│   │
│   ├── css/
│   │   ├── main.css                    ← CSS custom properties, reset, typography, grid layout, dark theme
│   │   └── components.css              ← Component styles: cards, table, sidebar, modal, badges, bars
│   │
│   └── js/
│       ├── dashboard.js                ← KPI card polling, system health badge, uptime, countdown timer
│       ├── table.js                    ← Table rendering, pagination, search integration, filter handling
│       ├── modal.js                    ← Modal open/close, form validation, create/edit/delete API calls
│       ├── pinglog.js                  ← Ping activity log polling, entry rendering, auto-scroll
│       └── charts.js                   ← Chart.js initialization, stability trend data refresh
│
└── plan/
    ├── 00_overview.md                  ← Project summary, architecture diagram, file listing
    ├── 01_database.md                  ← Database models and schema design
    ├── 02_api_routes.md                ← Full REST API specification
    ├── 03_ssh_ping_service.md          ← SSH integration and ping service strategy
    ├── 04_frontend.md                  ← Frontend layout, components, polling, theming
    ├── 05_project_structure.md         ← This file — complete project tree
    ├── 06_implementation_order.md      ← Phased build sequence
    └── 07_config_and_env.md            ← Environment variables and configuration
```

---

## File Purposes

### Root Files

| File | Purpose |
|---|---|
| `run.py` | Creates the Flask application via `create_app()`, starts the dev server. In production, this file is the WSGI entry point. Contains `if __name__ == '__main__': app.run(debug=True, port=5000)`. |
| `requirements.txt` | Lists: `flask`, `flask-sqlalchemy`, `apscheduler`, `paramiko`, `python-dotenv`, `cryptography`. Pinned to specific versions for reproducibility. |
| `.env.example` | Documents every environment variable with type, default, and description. Developers copy to `.env` and fill in real values. |
| `README.md` | Explains what the project does, how to set it up (clone, install, configure `.env`, run), and links to the plan docs for architecture context. |

### `/app` — Backend Package

| File | Purpose |
|---|---|
| `__init__.py` | The `create_app()` factory function. Creates Flask instance, loads config, initializes SQLAlchemy, registers all route blueprints, sets up static file serving for `/frontend`, initializes the scheduler, and calls `db.create_all()`. |
| `config.py` | A `Config` class with attributes mapped to environment variables. Uses `python-dotenv` to load `.env`. Exposes `SQLALCHEMY_DATABASE_URI`, `SECRET_KEY`, `JUMP_HOST`, `PING_INTERVAL_SECONDS`, etc. |
| `models.py` | Defines all four SQLAlchemy models (Link, PingResult, MetricSnapshot, JumpServer) with relationships, indices, and column constraints. |

### `/app/routes` — API Blueprints

| File | Purpose |
|---|---|
| `__init__.py` | Imports all blueprints and provides a `register_blueprints(app)` function called by the app factory. |
| `links.py` | Handles `GET/POST/PUT/DELETE /api/links` and `POST /api/links/<id>/ping`. Includes pagination, filtering, search, and status derivation logic. |
| `dashboard.py` | Handles `GET /api/dashboard/kpi` (aggregate counts) and `GET /api/dashboard/stability` (hourly ping success rates for 24h chart). |
| `pinglog.py` | Handles `GET /api/ping-log` (last N ping results across all links). Joins with Link to include `link_id` in each result. |
| `jumpserver.py` | Handles `GET /api/jumpserver` (read config, mask password) and `PUT /api/jumpserver` (create/update config, encrypt password). |

### `/app/services` — Business Logic

| File | Purpose |
|---|---|
| `ssh_service.py` | Contains the `SSHService` class exactly as provided. Not modified. Handles SSH connection, shell invocation, and command execution via Paramiko. |
| `ping_service.py` | Orchestrates a ping cycle: retrieves active jump server config, connects via SSHService, iterates over all links, executes ping commands, parses stdout, stores PingResult rows. Also exposes a `ping_single_link()` function for manual pings. |
| `scheduler.py` | Configures APScheduler `BackgroundScheduler`, defines the `ping_cycle` interval job, handles start/shutdown lifecycle, and provides cycle overlap protection via threading lock. |

### `/frontend` — Static Frontend

| File | Purpose |
|---|---|
| `index.html` | The single HTML page. Contains the full dashboard structure: top bar, sidebar, KPI cards, table, chart container, topology panel, modal. Links to CSS and JS files. |
| `css/main.css` | Global styles: CSS custom properties (color tokens, font stacks, spacing), CSS reset, typography rules, grid layout definitions, dark theme base colors. |
| `css/components.css` | Component-scoped styles: `.kpi-card`, `.link-table`, `.sidebar`, `.modal`, `.status-badge`, `.util-bar`, `.ping-log-entry`, `.nav-item`, `.btn-primary`, `.btn-ghost`, etc. |
| `js/dashboard.js` | Initializes KPI card polling (30s interval). Updates card values. Manages system health badge state. Runs the next-check countdown timer. Contains the shared `fetchAPI()` helper used by other modules. |
| `js/table.js` | Renders the link inventory table from API data. Handles pagination (page state, prev/next buttons). Listens to search input and filter dropdowns to trigger re-fetch. Builds utilization bars and status badges as DOM elements. |
| `js/modal.js` | Controls the CONFIGURE_MICROWAVE_LINK modal. Opens in create or edit mode. Validates fields (required checks, IPv4 regex). Calls POST or PUT on save. Shows inline errors. Closes on success. |
| `js/pinglog.js` | Polls `/api/ping-log` every 10 seconds. Renders timestamped, color-coded log entries in the sidebar panel. Auto-scrolls to the newest entry. |
| `js/charts.js` | Initializes a Chart.js bar chart in the Network Stability Trend container. Polls `/api/dashboard/stability` every 60 seconds and updates the chart data. Configures dark theme chart options. |

---

## Open Questions

1. **Separate `utils.js`?** — The shared `fetchAPI()` helper is currently planned inside `dashboard.js`. If it grows (error handling, retry logic), should it be extracted to a standalone `js/utils.js`?
2. **Favicon and assets** — Should we include a `frontend/assets/` folder for a favicon, logo, or placeholder images? The current plan has no image assets.
