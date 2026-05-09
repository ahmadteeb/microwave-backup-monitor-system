# 06 Frontend

## New standalone HTML pages

### `frontend/login.html`
Sections:
- Page title: `Sign In`.
- Login form with:
  - `Username` input.
  - `Password` input.
  - Submit button `Sign In`.
- Error banner area below the form for `Invalid username or password.` or lockout messages.
- Small footer link to `/setup` should not be shown after setup completion.

### `frontend/setup.html`
Sections:
1. **Page header**: `Setup MW Link Monitor`.
2. **Admin Account card**:
   - Full Name
   - Username
   - Email
   - Password
   - Confirm Password
   - Validation messages inline.
3. **SMTP Configuration card**:
   - Host
   - Port (default 587)
   - Username (optional)
   - Password (optional)
   - From Address
   - Use TLS toggle (default on)
   - Use SSL toggle (default off)
   - `Test SMTP` button.
   - Inline test result message.
4. **Jump Server card**:
   - Host
   - Port (default 22)
   - Username
   - Password
   - `Test Connection` button.
   - Inline test result message.
5. **Complete Setup** footer button `Complete Setup`.

### `frontend/change_password.html`
Sections:
- Page title: `Change Password`.
- If forced password change flow: visible fields are `New Password` and `Confirm New Password`.
- Otherwise: include `Current Password` plus `New Password`, `Confirm New Password`.
- `Save Password` button and validation feedback.
- Success redirect behavior to `/`.

## Changes to `frontend/index.html`

### Remove these exact elements
- The sidebar `<li class="nav-item">` entries for Link Clusters, Topology, and Traffic Analysis.
- The entire `.bottom-panels` container containing `NETWORK STABILITY TREND (24H)` and `TOPOLOGY MONITOR`.
- The floating add button `<div class="fab" id="fab-add-link">` and its child elements.
- The sidebar `button` with `#btn-add-sidebar`.
- Any `<h1>` or title text containing `LINK_MONITOR_NOC`.
- The hardcoded modal footer text `SYSTEM_AUTH: VALIDATED_USER_04`.
- Anything labelled with underscores such as `STATUS_FILTER`, `LEG_REGION`, `PING_ACTIVITY_LOG`, `LINK_ID`, `LEG_NAME`, `SITE_A_NODE`, `SITE_B_NODE`, `MW_IP_ADDRESS`, `CONFIGURE_MICROWAVE_LINK`, `SAVE_LINK`, `CANCEL`, `ADD_LINK`, `NEXT_CHECK`, `PAGE X OF Y`, `TOTAL LINKS`, `MW REACHABLE`, `MW UNREACHABLE`, `HIGH UTILIZATION`, `SYSTEM HEALTHY`, `UPTIME`.

### Additions and replacements
- App title text: `MW Link Monitor`.
- A toolbar row between the KPI cards and link table with:
  - left text: `Showing X of Y links`.
  - right button: `Add Link` with a plus icon.
  - the button is hidden by default and only shown when `links.add` is `true` in `/api/auth/me`.
- Replace the sidebar add button with the toolbar `Add Link` button.
- Replace the modal footer text with `Logged in as: {user full name}`.
- Rename all visible labels to human-readable text with spaces.

### Sidebar navigation list with permission gates
The sidebar items must be:
- Dashboard (always visible when authenticated).
- Links (visible when `links.view` permission is true).
- Users (visible when `users.view` permission is true).
- Notifications (visible when `notifications.view_own` permission is true).
- Logs (visible when `logs.view_system` permission is true).
- Settings (visible when `config.view` permission is true).
- Profile (always visible in user menu).

Notes:
- Navigation items may be hidden or disabled based on permissions from `GET /api/auth/me`.
- `Users`, `Logs`, and `Settings` should not appear unless the authenticated user has the respective permission.

### SPA section model
- `index.html` must contain hidden section containers for each SPA page:
  - `#dashboard-section`
  - `#links-section`
  - `#users-section`
  - `#notifications-section`
  - `#logs-section`
  - `#settings-section`
  - `#profile-section`
- Clicking sidebar nav items toggles visibility and updates active state.
- Only one section is visible at a time.
- `dashboard.js` and `table.js` should initialize the dashboard and link table when their sections are shown.
- `auth.js` or `utils.js` must handle SPA startup by calling `/api/auth/me` and caching the result.

## New JS files

### `frontend/js/auth.js`
Functions:
- `login(username, password)` submits `POST /api/auth/login`.
- `logout()` submits `POST /api/auth/logout` and redirects to `/login`.
- `initializeAuth()` fetches `/api/auth/me` on SPA load and returns the authenticated user object.
- Handles 401 redirect to `/login`.

Inputs and outputs:
- Input: form values.
- Output: redirect path or error message.

### `frontend/js/settings.js`
Functions:
- `loadSmtpSettings()` calls `GET /api/settings/smtp`.
- `saveSmtpSettings(payload)` calls `PUT /api/settings/smtp`.
- `testSmtpSettings()` calls `POST /api/settings/smtp/test`.
- `loadJumpServerSettings()` calls `GET /api/settings/jumpserver`.
- `saveJumpServerSettings(payload)` calls `PUT /api/settings/jumpserver`.
- `testJumpServerSettings()` calls `POST /api/settings/jumpserver/test`.
- `loadAppSettings()` calls `GET /api/settings/app`.
- `saveAppSettings(payload)` calls `PUT /api/settings/app`.

### `frontend/js/profile.js`
Functions:
- `loadProfile()` uses `GET /api/auth/me`.
- `saveProfile(payload)` uses `PUT /api/profile`.
- `changePassword(payload)` uses `POST /api/profile/change-password`.
- `loadNotificationPreferences()` uses `GET /api/notifications/subscriptions`.
- `saveNotificationPreference(event_key, is_subscribed)` uses `PUT /api/notifications/subscriptions`.

### `frontend/js/users.js`
Functions:
- `loadUsers()` uses `GET /api/users`.
- `createUser(payload)` uses `POST /api/users`.
- `updateUser(id, payload)` uses `PUT /api/users/<id>`.
- `deleteUser(id)` uses `DELETE /api/users/<id>`.
- `resetPassword(id, payload)` uses `POST /api/users/<id>/reset-password`.
- `unlockUser(id)` uses `POST /api/users/<id>/unlock`.
- `loadUserPermissions(id)` uses `GET /api/users/<id>/permissions`.
- `saveUserPermissions(id, overrides)` uses `PUT /api/users/<id>/permissions`.
- `loadUserNotificationSubscriptions(id)` uses `GET /api/users/<id>/notifications/subscriptions`.
- `saveUserNotificationSubscriptions(id, subscriptions)` uses `PUT /api/users/<id>/notifications/subscriptions`.

### `frontend/js/notifications.js`
Functions:
- `loadNotifications(page)` uses `GET /api/notifications`.
- `getUnreadCount()` uses `GET /api/notifications/unread-count`.
- `markNotificationRead(id)` uses `POST /api/notifications/<id>/read`.
- `markAllNotificationsRead()` uses `POST /api/notifications/read-all`.
- `loadNotificationSubscriptions()` uses `GET /api/notifications/subscriptions`.
- `updateNotificationSubscription(event_key, is_subscribed)` uses `PUT /api/notifications/subscriptions`.
- `pollUnreadCount()` every 60 seconds updates the bell badge.

### `frontend/js/logs.js`
Functions:
- `loadSystemLogs(filters)` uses `GET /api/logs/system`.
- `exportSystemLogs(filters)` uses `GET /api/logs/system/export`.
- `loadPingLogs(filters)` uses `GET /api/logs/ping`.
- `exportPingLogs(filters)` uses `GET /api/logs/ping/export`.
- `renderLogDetail(detail)` expands JSON inline.

### `frontend/js/utils.js`
Functions:
- `apiFetch(url, options)` wraps `fetch` and redirects to `/login` on `401`.
- `formatDate(timestamp)` formats ISO strings for display.
- `statusBadge(status)` returns UI classes and labels.
- `utilBar(value, thresholds)` returns util bar markup.
- `debounce(fn, wait)` helper.

## Modified JS files

### `frontend/js/dashboard.js`
Changes:
- Add `401` redirect to `/login` on API response.
- Remove stability chart call and topology placeholder logic.
- Update label strings to human readable text.
- Use permissions from `GET /api/auth/me` to hide sections if necessary.

### `frontend/js/table.js`
Changes:
- Use permissions from `GET /api/auth/me` to show/hide `Add Link` toolbar button.
- Remove underscore labels and replace with `Status Filter`, `LEG / Region`, and other human-readable labels.
- Adjust pagination display text to `Page X of Y`.
- Render column headers as `Link ID`, `Fiber Util`, `MW Util`, `Status`, `Latency`, `Actions`.

### `frontend/js/modal.js`
Changes:
- Remove hardcoded `SYSTEM_AUTH: VALIDATED_USER_04` and replace with logged-in user full name.
- Replace underscore labels in form fields, modal title, and buttons.

### `frontend/js/pinglog.js`
Changes:
- Replace any underscore labels with human-readable text.
- Ensure ping log tab is integrated under `/frontend/index.html` if logs section is shown.

### `frontend/js/charts.js`
Changes:
- Remove initialization of the stability chart and topology monitor.
- Keep only any supported charting needed for the dashboard if still applicable.

## CSS additions and removals

### `frontend/css/main.css`
- Add styles for new page sections and active sidebar nav state.
- Add dropdown / user menu styling.
- Add notification bell badge styling.

### `frontend/css/components.css`
- Remove `.fab` and all floating action button styles.
- Add styles for settings accordion sections.
- Add styles for log table row expansion and JSON detail display.
- Add styles for permission toggle pills and subscription toggles.
- Add styles for the top toolbar row containing `Showing X of Y links` and `Add Link` button.

## `/api/auth/me` usage for gating UI elements
- The app shell must call `/api/auth/me` after page load and before rendering protected sections.
- Store `permissions` from that response in a global frontend state object.
- Use the permissions object to:
  - show/hide `Add Link` button (`links.add`).
  - show/hide `Users` nav item (`users.view`).
  - show/hide `Logs` nav item (`logs.view_system`).
  - show/hide `Settings` nav item (`config.view`).
  - show/hide `Notifications` nav item (`notifications.view_own`).
  - disable action buttons in tables based on individual action permissions.
- Refresh the permission state on page load and after login.
