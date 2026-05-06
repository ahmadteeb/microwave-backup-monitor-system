# 06 — Implementation Order

## Phased Build Sequence

Each phase builds on the previous one. Do not skip phases. Complete the acceptance condition before proceeding.

---

## Phase 1 — Project Scaffold, Config, Models, DB Init

**What to build:**
- Create the project folder structure (`app/`, `app/routes/`, `app/services/`, `frontend/`, `frontend/css/`, `frontend/js/`).
- Write `requirements.txt` with all dependencies.
- Write `.env.example` with all environment variables documented.
- Write `app/config.py` with the `Config` class that reads from `.env`.
- Write `app/models.py` with all four SQLAlchemy models (Link, PingResult, MetricSnapshot, JumpServer) including relationships, indexes, and constraints.
- Write `app/__init__.py` with `create_app()` that initializes Flask, loads config, initializes SQLAlchemy, and calls `db.create_all()`.
- Write `run.py` as the entry point.

**What to test:**
- Run `pip install -r requirements.txt` — no errors.
- Run `python run.py` — Flask starts, `mw_monitor.db` file is created.
- Open the SQLite file with a DB browser and verify all four tables exist with correct columns.

**Acceptance condition:** Flask starts cleanly, database file is created with the correct schema, no import errors.

---

## Phase 2 — JumpServer Settings API + SSHService Integration + Ping Service

**What to build:**
- Copy `SSHService` class into `app/services/ssh_service.py` (verbatim, unmodified).
- Write `app/routes/jumpserver.py` with `GET /api/jumpserver` and `PUT /api/jumpserver` routes. Include Fernet password encryption/decryption.
- Write `app/services/ping_service.py` with:
  - `run_ping_cycle()` — connects to jump server, pings all links, stores results.
  - `ping_single_link(link_id)` — pings one link independently.
  - `parse_ping_output(raw_output)` — extracts reachable, latency_ms, packet_loss from ping stdout.
- Register the jumpserver blueprint in `app/__init__.py`.

**What to test:**
- `PUT /api/jumpserver` with test credentials — verify row is created in DB with encrypted password.
- `GET /api/jumpserver` — verify password is masked in response.
- Unit test `parse_ping_output()` with hardcoded success, timeout, partial-loss, and network-unreachable stdout strings.

**Acceptance condition:** Jump server config can be saved and retrieved. Ping output parser correctly handles all four patterns (success, timeout, partial loss, unreachable).

---

## Phase 3 — Link CRUD API Routes

**What to build:**
- Write `app/routes/links.py` with all CRUD routes:
  - `GET /api/links` (with pagination, filtering, search, join with latest ping + metric)
  - `POST /api/links` (create with validation)
  - `PUT /api/links/<id>` (update with validation)
  - `DELETE /api/links/<id>` (cascade delete)
  - `GET /api/links/<id>` (detail with 24h history)
  - `POST /api/links/<id>/ping` (manual ping trigger)
- Register the links blueprint.

**What to test:**
- Create 5 links via POST — verify they appear in the DB and are returned by GET.
- Update a link — verify changes persist.
- Delete a link — verify it and any associated ping results are removed.
- Test validation: missing `link_id`, invalid `mw_ip`, duplicate `link_id` — verify correct 400/409 errors.
- Test pagination: create 25 links, request page 1 with per_page=10, verify 10 results returned and `pages=3`.

**Acceptance condition:** All CRUD operations work. Validation rejects bad input with descriptive error messages. Pagination works correctly.

---

## Phase 4 — APScheduler Ping Job + Ping Result Storage

**What to build:**
- Write `app/services/scheduler.py` with BackgroundScheduler setup, `ping_cycle` job definition, and cycle overlap protection (threading lock).
- Integrate the scheduler into `create_app()` — start on app launch, stop on shutdown.
- The `ping_cycle` job calls `ping_service.run_ping_cycle()`.
- Ensure `POST /api/links/<id>/ping` (manual ping) uses a separate SSH connection and does not conflict with the scheduler.

**What to test:**
- Start the app with a configured jump server and 3 links. Wait for one scheduler cycle (60s). Verify PingResult rows appear in the DB.
- Trigger a manual ping via `POST /api/links/1/ping` while a cycle is not running — verify result is returned and stored.
- Verify that if a cycle is already running, the next scheduled trigger is skipped (check logs for the warning message).

**Acceptance condition:** The scheduler runs ping cycles at the configured interval. Results are stored in the database. Manual pings work independently. No concurrent cycle conflicts.

**Note:** This phase requires a real or simulated jump server for integration testing. If no jump server is available, mock the SSHService to return hardcoded ping outputs.

---

## Phase 5 — Dashboard KPI and Stability API Routes

**What to build:**
- Write `app/routes/dashboard.py` with:
  - `GET /api/dashboard/kpi` — aggregate query for total links, reachable, unreachable, high utilization.
  - `GET /api/dashboard/stability` — hourly ping success rates for the last 24 hours.
- Write `app/routes/pinglog.py` with:
  - `GET /api/ping-log` — last N ping results across all links with status text derivation.
- Register both blueprints.

**What to test:**
- Seed the database with 10 links and 100 ping results (mix of reachable and unreachable). Query `/api/dashboard/kpi` — verify counts match.
- Seed ping results spanning 24 hours. Query `/api/dashboard/stability` — verify 24 hourly buckets are returned with correct success rates.
- Query `/api/ping-log?limit=10` — verify 10 newest results are returned in descending timestamp order.

**Acceptance condition:** KPI numbers are accurate. Stability data covers 24 hours. Ping log returns correctly ordered, enriched results.

---

## Phase 6 — Frontend HTML/CSS Shell

**What to build:**
- Write `frontend/css/main.css` with all CSS custom properties, reset, typography, and grid layout.
- Write `frontend/css/components.css` with all component styles (cards, table, sidebar, modal, badges, bars, etc.).
- Write `frontend/index.html` with the full dashboard structure — all sections from the screenshot:
  - Top bar with system name, health badge, uptime, countdown, icons.
  - Left sidebar with search, filters, navigation, ping log area, ADD_LINK button.
  - KPI card row (4 cards with placeholder values).
  - Table structure with header and empty tbody.
  - Chart container and topology panel.
  - Modal (hidden by default).
  - Floating action button.
- Configure Flask to serve `frontend/` as static files.

**What to test:**
- Open `http://localhost:5000` in a browser — the dashboard renders with the correct dark theme layout.
- Visually compare with the provided screenshots. The layout, colors, typography, and spacing should match closely.
- Resize the browser to 1280px width — layout remains usable.
- Click ADD_LINK button — modal appears with correct fields and styling.

**Acceptance condition:** The static HTML/CSS dashboard visually matches the screenshot. All UI sections are present and correctly positioned. Modal opens and closes. No JavaScript functionality required yet.

---

## Phase 7 — JS Polling, Table Rendering, Ping Log, KPI Cards

**What to build:**
- Write `frontend/js/dashboard.js` with:
  - Shared `fetchAPI()` helper function.
  - KPI card polling (30s) — update card number values.
  - System health badge logic.
  - Next-check countdown timer (1s tick).
- Write `frontend/js/table.js` with:
  - Table rendering from `/api/links` response data.
  - Utilization bar rendering (CSS width percentage, color based on value).
  - Status badge rendering.
  - Pagination controls (page state, prev/next).
  - Search input handler (debounced, triggers re-fetch).
  - Filter dropdown handlers (trigger re-fetch with query params).
- Write `frontend/js/pinglog.js` with:
  - Ping log polling (10s).
  - Color-coded entry rendering.
  - Auto-scroll to newest.

**What to test:**
- Load the dashboard with seed data in the database. Verify KPI cards show correct numbers.
- Verify the table renders all links with correct utilization bars, status badges, and latency values.
- Change the status filter — table updates.
- Type in the search box — table filters in near real-time.
- Wait 30 seconds — KPI cards and table refresh without a page reload.
- Check the ping log — entries appear with correct color coding.

**Acceptance condition:** All dynamic data displays correctly. Polling works without page reload. Filters and search work. Ping log auto-scrolls.

---

## Phase 8 — Modal Form, Validation, Save/Edit/Delete Flows

**What to build:**
- Write `frontend/js/modal.js` with:
  - Open modal in create mode (from ADD_LINK button and FAB).
  - Open modal in edit mode (from table row pencil icon, pre-fill fields).
  - IPv4 validation regex.
  - Required field validation.
  - POST (create) and PUT (update) API calls on SAVE_LINK click.
  - Inline error display for validation failures and API errors.
  - Success handling: close modal, show toast, refresh table.
  - Delete confirmation flow (from table trash icon): confirm dialog → DELETE API call → refresh table.

**What to test:**
- Create a new link via the modal — verify it appears in the table.
- Edit an existing link — verify changes are reflected.
- Delete a link — verify it's removed from the table and database.
- Try to save with an invalid IP (e.g., `999.999.999.999`) — verify inline error appears.
- Try to create a link with a duplicate link_id — verify 409 error is shown inline.

**Acceptance condition:** Full create/edit/delete lifecycle works through the UI. Validation prevents bad data. Errors are shown inline without crashing.

---

## Phase 9 — Chart.js Stability Trend Chart

**What to build:**
- Write `frontend/js/charts.js` with:
  - Chart.js CDN script inclusion in `index.html`.
  - Bar chart initialization in the Network Stability Trend container.
  - Dark theme configuration (transparent background, gray gridlines, custom colors).
  - Data fetch from `/api/dashboard/stability` on page load and every 60 seconds.
  - Stacked bars: teal for successful pings, red/coral for failed pings.
  - Tooltip customization showing hour, success count, failure count, and rate.

**What to test:**
- Load the dashboard with 24 hours of ping data — the chart renders with 24 bars.
- Hover over a bar — tooltip shows correct data.
- Wait 60 seconds — chart data refreshes without redrawing the entire chart.
- Verify chart matches the screenshot aesthetic: dark background, teal/coral bars, subtle gridlines.

**Acceptance condition:** The chart renders correctly, updates periodically, and matches the screenshot styling.

---

## Phase 10 — End-to-End Test with Real Jump Server

**What to build:**
- No new code. This phase is pure integration testing.
- Configure `.env` with real jump server credentials and real MW link IPs.
- Seed 5–10 links with actual MW IP addresses.

**What to test:**
- Start the application. Wait for one full ping cycle.
- Verify PingResult rows are created with real reachable/latency data.
- Verify the dashboard shows accurate KPI numbers.
- Verify the table shows correct status badges and latency values.
- Trigger a manual ping from the UI — verify it works.
- Verify the stability chart accumulates data over time.
- Verify the ping log shows real ping results with correct timestamps.
- Test error scenarios: incorrect jump server password (verify graceful handling), unreachable MW IP (verify DOWN status).

**Acceptance condition:** The full system works end-to-end with real network infrastructure. Dashboard accurately reflects the state of MW backup links. All error scenarios are handled gracefully.

---

## Open Questions

1. **Seed data for demo** — Should Phase 6/7 include a seed script that populates the database with realistic demo data for visual testing before a real jump server is available?
2. **Automated tests** — Should we write pytest unit tests for the API routes and ping parser, or rely on manual curl/browser testing for v1?
3. **CI/CD** — Is any CI pipeline needed, or is this deployed manually for v1?
