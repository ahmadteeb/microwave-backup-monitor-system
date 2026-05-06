# 04 — Frontend Plan

## Overview

The frontend is a single-page dashboard served as static files by Flask. No JavaScript frameworks — all interactivity is built with vanilla JS using `fetch()` for API calls and direct DOM manipulation for updates. Chart.js (CDN) is the only external JS library.

---

## File Structure

```
/frontend
  index.html              ← Main dashboard page (single HTML file)
  css/
    main.css              ← CSS custom properties, reset, typography, dark theme
    components.css        ← Cards, table, sidebar, modal, badges, bars, chart containers
  js/
    dashboard.js          ← KPI cards, system health badge, uptime, next-check countdown
    table.js              ← Link inventory table: render, paginate, search, filter
    modal.js              ← CONFIGURE_MICROWAVE_LINK modal: open/close, validation, CRUD
    pinglog.js            ← Sidebar ping activity log: polling, auto-scroll, color coding
    charts.js             ← Chart.js bar chart: Network Stability Trend initialization + refresh
```

---

## Page Layout — `index.html`

The page is a CSS Grid layout with three major regions: sidebar (left), main content (center-right), and a top bar (full width).

### Top Bar

- **Left**: System name `LINK_MONITOR_NOC` in bold monospace. Next to it, a `SYSTEM HEALTHY` badge — a small pill-shaped element with a green dot and text. This badge reads its state from the KPI endpoint. If the system cannot reach the jump server or the last ping cycle failed, it switches to `SYSTEM DEGRADED` (amber) or `SYSTEM DOWN` (red).
- **Right**: `UPTIME: 99.99%` — calculated from ping success rate over the last 24 hours (from the stability endpoint). `NEXT_CHECK: 00:42` — a countdown timer in JS that ticks down from the ping interval to 00:00, then resets on each cycle. This is purely cosmetic; the backend scheduler controls actual timing.
- **Far right icons**: Notification bell (placeholder — no functionality in v1), message icon (placeholder), settings gear (opens jump server config in future), user avatar (placeholder).
- **Styling**: Dark background (`#0d1117`), teal accent text for system name, monospace font for uptime/timer values.

### Left Sidebar (200px width)

From top to bottom:

1. **Search input**: Text field with magnifying glass icon and placeholder `SITE/ID SEARCH...`. On keyup, filters the link inventory table in real-time by matching against `link_id` and `leg_name`. Debounced at 300ms.

2. **STATUS_FILTER dropdown**: A styled `<select>` with options: `ALL_OPERATIONAL`, `UP`, `DOWN`, `TIMEOUT`, `HIGH`. Changing the selection triggers a re-fetch of `/api/links` with the `status` query parameter.

3. **LEG_REGION dropdown**: A styled `<select>` dynamically populated from the distinct `leg_name` values returned by the API. First option is `ALL_REGIONS`. Changing triggers re-fetch with `leg` query parameter.

4. **NAVIGATION section**: A vertical list of nav links with icons:
   - Dashboard (highlighted/active — teal text and left border accent)
   - Link Clusters (placeholder)
   - Topology (placeholder)
   - Traffic Analysis (placeholder)
   - System Logs (placeholder)
   
   Only "Dashboard" is functional in v1. Others are styled but non-functional.

5. **PING_ACTIVITY_LOG section**: A small scrollable panel at the bottom of the sidebar (about 150px tall). Shows the last ~10 ping results with format: `[HH:MM:SS] MW-B-402 PING OK    14ms`. Color-coded: green for PING OK, amber for PKT_LOSS, red for TIMEOUT. Auto-scrolls to newest. Polled via `/api/ping-log` every 10 seconds.

6. **ADD_LINK button**: Full-width teal button at the very bottom of the sidebar. Text: `+ ADD_LINK`. On click, opens the CONFIGURE_MICROWAVE_LINK modal with all fields empty (create mode).

### KPI Cards Row (4 cards)

Four equal-width cards spanning the top of the main content area.

| Card | Label | Value | Icon | Accent |
|---|---|---|---|---|
| 1 | `TOTAL LINKS` | e.g., `142` | Diamond/layers icon | Default teal border-top |
| 2 | `MW REACHABLE` | e.g., `138` | Link chain icon | Green (#00e676) border-top |
| 3 | `MW UNREACHABLE` | e.g., `4` | Broken chain icon | Red (#ff5252) border-top |
| 4 | `HIGH UTILIZATION` | e.g., `12` | Warning triangle icon | Amber (#ffab40) border-top |

- Each card has: dark background (`#161b22`), subtle border, top accent color bar (3px), large number in white, label in muted gray above, icon in top-right corner.
- All four cards update from a single `GET /api/dashboard/kpi` call every 30 seconds.
- Numbers animate on change (simple CSS transition on opacity — old value fades out, new fades in).

### Active Link Inventory Table

Located below the KPI cards. Full-width with a header row: `ACTIVE LINK INVENTORY` with a count badge (`142 TOTAL`), and filter/download icons in the top-right.

**Table columns:**

| Column | Content | Rendering |
|---|---|---|
| LINK ID | `link_id` string | Monospace text, teal colored |
| LEG | `leg_name` string | Regular text |
| FIBER UTIL | Percentage value + bar | Horizontal bar drawn with CSS (`<div>` with percentage width). Background track is dark gray; fill color is: green (< 70%), amber (70–90%), red (> 90%). Percentage label to the left. |
| MW UTIL | Percentage value + bar | Same bar rendering as FIBER UTIL |
| STATUS | Status badge | Pill-shaped badge. Colors: `UP` = green bg, `HIGH` = amber bg, `DOWN` = red bg, `TIMEOUT` = dark red bg with text. |
| LATENCY | Latency in ms | Teal text. Shows `—` when status is DOWN/TIMEOUT. |
| ACTIONS | Edit + Delete buttons | Pencil icon (opens modal in edit mode) and trash icon (confirms then deletes). |

**Below the table:**
- Legend: colored dots with labels `OPTIMAL < 70%`, `WARNING 70-90%`, `CRITICAL > 90%`.
- Pagination: `PAGE 1 OF 12` with `<` and `>` arrow buttons.

**Data source:** `GET /api/links` with current page, filter, and search params. Refreshed every 30 seconds, but also re-fetched on filter change, search input, or pagination click.

### Network Stability Trend Chart

Below the table, left side (approximately 70% width). A bar chart using Chart.js.

- **Title**: `NETWORK STABILITY TREND (24H)` — static text above the chart.
- **X-axis**: 24 bars, one per hour, labeled with hour values.
- **Y-axis**: Ping success rate or count (two stacked segments per bar: successful pings in teal, failed pings in coral/red).
- **Data source**: `GET /api/dashboard/stability` polled every 60 seconds.
- **Chart.js config**: Dark theme — canvas background transparent (inherits page dark bg), gridlines in subtle gray (`#30363d`), axis labels in light gray, bar colors teal (`#00d4aa`) for success and coral (`#ff6b6b`) for failure.
- **Tooltip**: On hover, shows "Hour: 14:00 — Success: 138, Failed: 4, Rate: 97.2%".

### Topology Monitor Panel

Below the table, right side (approximately 30% width).

- **Title**: `TOPOLOGY MONITOR` — static text.
- **Content for v1**: A placeholder panel with a dark background and a stylized network illustration. This can be a static SVG or Canvas drawing showing abstract nodes and links with a subtle glow effect. No interactive functionality in v1.
- **Future**: This would render an interactive network topology map based on link data.

### Bottom Floating Action Button

A teal circular button (`+` icon) fixed to the bottom-right corner of the viewport. On click, opens the CONFIGURE_MICROWAVE_LINK modal. This duplicates the sidebar ADD_LINK button for quick access.

---

## Modal — CONFIGURE_MICROWAVE_LINK

A centered modal overlay that appears on top of the dashboard with a dark semi-transparent backdrop.

**Header**: Icon (grid/settings icon) + title `CONFIGURE_MICROWAVE_LINK` + close button (✕) in top-right corner.

**Form fields (2-column grid layout):**

| Field | Position | Type | Placeholder | Validation |
|---|---|---|---|---|
| LINK_ID | Left column | Text input | (no placeholder, filled when editing) | Required, alphanumeric + hyphens |
| LEG_NAME | Right column | Text input | (no placeholder) | Required |
| SITE_A_NODE | Left column | Text input | `e.g. ALPHA_BASE` | Optional |
| SITE_B_NODE | Right column | Text input | `e.g. DELTA_REPEATER` | Optional |
| MW_IP_ADDRESS | Full width | Text input | `000.000.000.000` | Required, validated as IPv4 format |

- The MW_IP_ADDRESS field has a special label: `MW_IP_ADDRESS (required)` with teal accent on the label.
- Below the IP field: helper text in teal/green: `Required field: Provide a valid IPv4 address for link telemetry.`
- If validation fails, the helper text turns red and shows the specific error (e.g., "Invalid IPv4 format").
- An info icon (ℹ) appears at the right end of the IP input field.

**Footer:**
- Left side: `SYSTEM_AUTH: VALIDATED_USER_04` — static text in muted gray. Placeholder for future auth integration.
- Right side: `CANCEL` button (outlined/ghost style) and `SAVE_LINK` button (solid teal with save icon).

**Behavior:**
- **Create mode**: Opened from ADD_LINK button. All fields empty. SAVE_LINK calls `POST /api/links`.
- **Edit mode**: Opened from the pencil icon in a table row. Fields pre-filled with existing link data. SAVE_LINK calls `PUT /api/links/<id>`.
- On successful save, the modal closes, a brief success toast appears, and the table re-fetches.
- On API error (e.g., 409 duplicate link_id), the modal stays open with an inline error message below the offending field.

---

## JS Polling Strategy

All polling is done with `setInterval()` + `fetch()`. Each poller is a self-contained function that:
1. Calls the API endpoint.
2. On success, updates the relevant DOM section.
3. On failure (network error, 5xx), logs a warning and retries on the next interval — does not crash or stop polling.

| Poller | Endpoint | Interval | DOM target | Update method |
|---|---|---|---|---|
| KPI poller | `GET /api/dashboard/kpi` | 30s | KPI card values | Update `textContent` of number elements |
| Table poller | `GET /api/links` | 30s | Table `<tbody>` | Clear and rebuild all `<tr>` elements |
| Ping log poller | `GET /api/ping-log` | 10s | Sidebar log container | Rebuild log entries, scroll to bottom |
| Stability poller | `GET /api/dashboard/stability` | 60s | Chart.js instance | Call `chart.data.datasets[0].data = newData; chart.update()` |

**Next-check countdown**: A `setInterval(1000)` (every second) decrements a counter from `PING_INTERVAL_SECONDS` to 0, then resets. This runs independently of API polling — it's purely cosmetic.

**DOM update without full reload**: Each poller only touches its own DOM subtree. No `innerHTML` rewriting of the entire page. Table rows are rebuilt on each poll because the dataset is small (max 20 rows per page). For KPI cards, only the number text nodes are updated.

---

## CSS Theming Plan

### CSS Custom Properties (defined in `main.css` `:root`)

| Variable | Value | Usage |
|---|---|---|
| `--bg-primary` | `#0d1117` | Page background, top bar |
| `--bg-secondary` | `#161b22` | Cards, sidebar, table rows |
| `--bg-tertiary` | `#1c2333` | Input fields, modal background |
| `--bg-overlay` | `rgba(0,0,0,0.7)` | Modal backdrop |
| `--text-primary` | `#e6edf3` | Main text, headings |
| `--text-secondary` | `#8b949e` | Labels, muted text |
| `--text-muted` | `#484f58` | Placeholders, disabled states |
| `--accent-teal` | `#00d4aa` | System name, active nav, buttons, highlights |
| `--accent-teal-hover` | `#00e8bb` | Button hover states |
| `--status-up` | `#00e676` | UP badge, reachable indicators |
| `--status-down` | `#ff5252` | DOWN badge, unreachable indicators |
| `--status-warning` | `#ffab40` | HIGH badge, warning states |
| `--status-timeout` | `#d32f2f` | TIMEOUT badge, dark red |
| `--border-color` | `#30363d` | Table borders, card borders, dividers |
| `--bar-optimal` | `#00d4aa` | Utilization bar < 70% |
| `--bar-warning` | `#ffab40` | Utilization bar 70–90% |
| `--bar-critical` | `#ff5252` | Utilization bar > 90% |
| `--font-body` | `'Inter', sans-serif` | Body text |
| `--font-mono` | `'JetBrains Mono', monospace` | Link IDs, latency values, ping log |
| `--radius-sm` | `4px` | Badges, small elements |
| `--radius-md` | `8px` | Cards, inputs, modal |
| `--shadow-card` | `0 2px 8px rgba(0,0,0,0.3)` | Card elevation |

### Font Loading

Google Fonts loaded in `<head>`:
- Inter (400, 500, 600) — body text
- JetBrains Mono (400, 500) — monospace elements

### Responsive Considerations

The primary target is a NOC desktop monitor (1920×1080 or larger). The layout should work at 1280px minimum width. Below 1024px, the sidebar collapses to an icon-only rail. The application is not designed for mobile.

---

## Vanilla JS Architecture (No Frameworks)

Each JS file is a self-contained module loaded via `<script>` tags in `index.html` (all at bottom of `<body>` with `defer` attribute, in dependency order).

**Shared patterns across all modules:**
- **API calls**: A shared `fetchAPI(url, options)` helper function (defined in `dashboard.js` or a `utils.js` if needed) that wraps `fetch()`, handles JSON parsing, and catches errors.
- **DOM references**: Each module caches its DOM elements in variables at load time (e.g., `const kpiTotal = document.getElementById('kpi-total')`).
- **State**: Minimal state kept in module-scoped variables (current page number, current filters). No global state management — each module owns its own state.
- **Events**: Event listeners attached via `addEventListener()`. Modal open/close uses CSS class toggling (`modal.classList.add('active')`).

This replaces what React/Vue would do: instead of a virtual DOM diffing engine, each poller directly updates the specific text nodes and elements that changed. This is efficient for this dashboard because the DOM structure is static — only the data values change.

---

## Open Questions

1. **Chart.js version** — Should we pin to Chart.js v4 (latest) or v3? V4 is tree-shakable but since we load from CDN, it doesn't matter. Recommend v4 for latest features.
2. **Topology Monitor scope** — Should the placeholder be a static image, a CSS-drawn abstract network, or a simple Canvas animation with floating nodes? Recommend a CSS/SVG static illustration for v1.
3. **Table row click** — Should clicking a table row (not the action buttons) open a detail view or do nothing? The current plan has no detail page — all info is in the table.
4. **Toast notifications** — Should success/error toasts be a custom implementation or should we use a simple CSS-animated notification that auto-dismisses after 3 seconds?
