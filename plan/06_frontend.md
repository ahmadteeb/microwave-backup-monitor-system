# 06 — Frontend Layout and JavaScript Modules

## 1. Visual Theme (Dark NOC Aesthetics)

The user interface implements a high-density, dark NOC dashboard theme. All visual components are styled using vanilla CSS, with styles defined across dedicated files to maintain a clear separation of concerns.

### 1.1 Color Palette
-   **Core Canvas Background**: `#0F1117`
-   **Dashboard Component Panels**: `#1A1D27`
-   **Floating Overlays and Modals**: `#22263A`
-   **System Accent (Teal)**: `#00C2A8`
-   **Primary Text**: `#E8EAF0`
-   **Secondary Text (Muted)**: `#7A8099`
-   **Border Accents**: `#2A2D3E`
-   **Status Indicators**:
    -   **Up (Operational)**: `#00C48C` (Teal-Green)
    -   **Down (Failed)**: `#FF4D6A` (Rose-Red)
    -   **High Utilization (Warning)**: `#FFB547` (Amber-Yellow)
    -   **Checking (Diagnostic)**: `#7A8099` (Slate-Gray)

### 1.2 Font Configurations
-   **Primary System Typography**: `Inter` (Google Fonts CDN). Used for general layouts, lists, forms, and headings.
-   **Console Monospace Typography**: `JetBrains Mono` (Google Fonts CDN). Applied to terminal ping logs, device IP addresses, Link IDs, and debug output blocks.

---

## 2. Global Chrome and Layout Structure

All application pages share a common, consistent layout structure (Chrome) split into two primary areas: a left-aligned navigation sidebar and a top global status bar.

### 2.1 Navigation Sidebar
-   **Logo Branding**: Displays "MW Link Monitor" in bold uppercase letters using the system accent teal color.
-   **Navigation Menu**: A vertical list of options. Navigation items use spaces instead of underscores:
    -   Dashboard (Renders main link listings and system status metrics)
    -   Links (Provides access to static link configuration tools)
    -   Notifications (Shows the system alert history inbox)
    -   System Logs (Provides administrators with access to system audit logs)
    -   Settings (Provides configuration controls for SMTP, Jump Server, and App variables)
    -   User Management (Access-controlled area for user account management)
-   **Collapsible State**: The sidebar can be collapsed to maximize screen real estate on smaller displays.

### 2.2 Top Global Status Bar
-   **Left Section**: Displays the system health status, alongside the primary system name branding.
-   **Right Section**: Displays current session metadata:
    -   The logged-in user's name (formatted with spaces, e.g., "John Doe").
    -   An interactive Notification Icon (Bell) featuring an unread alert counter badge.
    -   An explicit Logout button that clears the active session.

---

## 3. Page Specifications

### 3.1 Dashboard Workspace (`/`)
The main NOC workspace is divided into four distinct operational sections:

```
+-----------------------------------------------------------------------------------+
|  [TOTAL LINKS]       [MW REACHABLE]       [MW UNREACHABLE]      [HIGH UTILIZATION] |
|       142                 138                    4                      2         |
+-----------------------------------------------------------------------------------+
|  [Search Input]              [LEG Region Select]             [Status Dropdown]    |
+-----------------------------------------------------------------------------------+
|  Link ID | LEG | Site A | Site B | Fiber Util | MW Util | MW Status | Actions     |
|  --------+-----+--------+--------+------------+---------+-----------+---------    |
|  BK-001  | 598 | Alpha  | Delta  | [████░░░░] | [░░░░░] |    UP     | [Edit][Del] |
+-----------------------------------------------------------------------------------+
|  [HH:MM:SS] BK-001 -> 10.58.14.1 - Reply 12ms                                     |
|  [HH:MM:SS] BK-004 -> 10.58.15.2 - Timeout (Consecutive Timeouts: 3)              |
+-----------------------------------------------------------------------------------+
```

-   **Section 1: KPI Dashboard Cards (4)**
    -   *Total Links Card*: Current inventory count.
    -   *MW Reachable Card*: Count of responsive links. Employs a green accent light.
    -   *MW Unreachable Card*: Count of failing links. Employs a red accent light.
    -   *High Utilization Card*: Count of links operating above threshold limits. Employs an amber accent light.
    -   *Scheduler Activity Pulse*: Each card features a small breathing dot indicator that pulses when the scheduler is actively executing background checks.
-   **Section 2: Interactive Filter Toolbar**
    -   Includes a text search input for Link IDs or nodes, a LEG Name dropdown filter, and a Status selector (All, Up, Down, High, Checking).
    -   Features a dynamic results counter reading: "Showing X of Y links".
-   **Section 3: Main Active Link Table**
    -   Displays link parameters and performance metrics: Link ID, LEG, Site A, Site B, Equipment, Fiber Util, Fiber Peak, Fiber Cap, MW Util, MW Peak, MW Cap, MW Status, Ping, Last Updated, and Actions.
    -   *Utilization Bars*: Inline horizontal progress bars color-coded green (optimal), amber (near capacity), or red (critical).
    -   *Telemetry Background*: Dynamic metrics columns use a subtle, teal-tinted background color to clearly distinguish auto-fetched metrics from static configurations.
    -   *Data Freshness Indicator*: Displays the relative age of metrics data. The timestamp turns amber if metrics are more than 2 minutes old, and red if they are more than 5 minutes old (indicating stale telemetry).
-   **Section 4: Terminal Activity Log (Ping Log)**
    -   A scrollable terminal output area displaying recent ping execution logs.
    -   Successful checks are displayed in green text; timeouts and errors are highlighted in red text; and background scheduler statuses are displayed in gray text.
    -   Displays a countdown timer showing the remaining seconds before the next automated sweep begins.

### 3.2 Row Expand Detail Panel
Clicking on any row inside the active link table slides open a detailed diagnostics panel directly beneath it:

-   **Primary Fiber Stats (Left)**: Renders a radial gauge illustrating active capacity consumption, alongside a 24-period historical traffic sparkline chart.
-   **Microwave Standby Stats (Right)**: Displays microwave utilization, active latency metrics, consecutive failure tallies, and an interface sparkline chart.
-   **Dynamic System Warning Banners**: Warning banners appear inside the panel when link performance degrades:
    -   *Fiber Critical Alert*: A bright red warning banner if fiber utilization crosses 90%.
    -   *Fiber Near Cap Alert*: An amber warning banner if fiber utilization falls within the 80% to 90% range.
    -   *Microwave Offline Alert*: A bright red warning banner if a microwave link goes down, displaying the number of consecutive timeouts.

### 3.3 Add and Edit Link Configuration Modal
A modal dialog used to manage link configurations. It contains the following form controls:
-   **Link ID**: Capitalized alphanumeric string matching pattern `BK-XXX`.
-   **LEG Name**: Regional logical routing group.
-   **Site A & Site B Nodes**: Target terminal site names.
-   **Microwave Target IP**: Target device IP address (supporting both IPv4 and IPv6).
-   **Equipment Hardware Models (Site A & Site B)**: Optional description fields.
-   **Notes**: Text area for operator notes.
-   **System Telemetry Info Banner**: A status banner informs the user: *"Fiber and MW metrics are fetched automatically every 60 seconds and cannot be entered manually."*

### 3.4 User Management Workspace (`/users`)
Renders an account administration table showing: Full Name, Username, Email, Role, Account Status, Last Login, and Actions (Edit, Reset Password, Delete, Unlock).

-   **User Configuration Modal**: Controls account creation and profile updates.
-   **Permissions Override Control Panel**: Renders a list of granular system permissions organized by category (Links, Users, Config, Logs, Notifications).
    -   Each permission has an on/off toggle.
    -   Displays a status badge indicating whether the permission is inheriting its value from the "Role Default" or using a "Custom Override".
    -   Includes a "Reset to Role Defaults" button that clears all custom permission overrides, reverting the user's permissions back to the role defaults.

### 3.5 System Settings Console (`/settings`)
An administration workspace split into three collapsible sections:
1.  **SMTP Mail Client Setup**: Configures connection parameters (Host, Port, Username, Password, From Address, and Security Toggles). Includes an interactive "Test Connection" button that transmits a test message to verify settings.
2.  **Jump Server Handshake Setup**: Configures SSH login details (Host, Port, Username, and Password/Cryptographic Key). Includes an interactive "Test Connection" diagnostic button to verify login handshakes.
3.  **Application Monitoring Thresholds**: Configures application-level parameters: inactivity session limits, background polling frequencies, warning thresholds, and consecutive timeout limits.

---

## 4. Frontend Javascript Modules

### 4.1 UI Controller (`js/dashboard.js`)
-   **`pollSummary()`**: Fetches high-level system statistics (`GET /api/dashboard/summary`) and updates the KPI cards and system health indicators. Runs every 30 seconds.
-   **`tickSchedulerTimer()`**: Manages the countdown timer displayed on the terminal ping log panel. Resets the countdown when the background scheduling cycle runs.

### 4.2 Paginated Data Engine (`js/table.js`)
-   **`fetchPage(page_number)`**: Fetches paginated link records from the API, incorporating active search parameters, regional filters, and status selections.
-   **`renderLinksTable(data_array)`**: Generates the table row elements, inserting color-coded status badges, utilization progress bars, and custom actions.
-   **`toggleRowDetails(row_id)`**: Manages the row expansion details panel, fetching historical telemetry and initializing the diagnostic charts.

### 4.3 Form Handlers (`js/modal.js`)
-   **`validateLinkInput()`**: Performs client-side input validation on link configuration forms: verifies required fields, checks that Link IDs conform to the `BK-XXX` pattern, and validates IP address syntax.
-   **`submitLinkForm(target_url, method_verb)`**: Handles link creation and update form submissions, showing validation errors on the form fields if the request fails.

### 4.4 Diagnostic Charts Engine (`js/charts.js`)
Uses `Chart.js` via CDN to render performance visualizations in the expanded details panel:
-   **`initRadialGauge(element_id, percentage)`**: Configures and renders radial doughnut charts illustrating bandwidth utilization.
-   **`renderSparkline(element_id, data_points)`**: Renders lightweight, line charts showing 24-period traffic and ping latency histories.

### 4.5 Shared Helpers (`js/utils.js`)
-   **`formatRelativeTimestamp(timestamp)`**: Formats raw datetime strings into relative, human-readable labels (e.g., "30 seconds ago", "2 minutes ago").
-   **`generateBadge(status_value)`**: Returns HTML status badges with appropriate CSS color classes.
-   **`debounce(callback_fn, delay_ms)`**: Debounces high-frequency input events, such as keyboard inputs on search fields, to prevent overloading backend APIs.
