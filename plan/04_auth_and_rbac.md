# 04 — Authentication and Role-Based Access Control (RBAC)

## 1. Authentication Framework

The application implements standard, session-based authentication using Flask's secure signed cookie sessions.

### 1.1 Secure Password Hashing
- All database-stored passwords must be hashed using the `bcrypt` algorithm.
- Set a minimum work factor (rounds) of `12` to guard against brute-force attacks.
- Raw password strings are never stored in the database or transmitted in plain-text API responses.

### 1.2 Session Lifecycles
- Sessions are stored as cryptographically signed cookies on the client browser.
- **Inactivity Timeout**: The session lifetime defaults to `480` minutes (8 hours) of user inactivity. This timeout is a system-wide parameter configured in `AppSettings.session_timeout_minutes`.
- **Sliding Sessions**: Every successful HTTP request intercepts the session cookie and updates its expiration timestamp, implementing a sliding expiration window.
- **Remember Me**: This system explicitly **does not** implement persistent "Remember Me" cookies to reduce session hijacking vectors on shared NOC terminals.

### 1.3 Account Lockout Controls
To mitigate dictionary and brute-force attacks on user accounts, the system enforces the following lockout rules:
- **Lockout Threshold**: If a user account accumulates `5` consecutive failed login attempts, the account is locked.
- **Lockout Duration**: Once locked, the `is_locked` attribute in the `User` table is set to `True`, and `locked_until` is set to `15` minutes in the future.
- **Handling Login Attempts During Lockout**: Any login attempts made during the active lockout period are rejected instantly, returning a generic error message.
- **Auto-Unlock**: If a login attempt occurs after the `locked_until` timestamp has expired, the lockout is cleared, the failed login counter is reset to `0`, and the login attempt is processed normally.
- **Manual Unlock**: An administrator with `users.edit` permissions can manually unlock any locked account via the User Management interface, resetting `failed_login_count` and toggling `is_locked` to `False`.

### 1.4 Forced Password Change Flow
Administrators can require any user to change their password on their next login by toggling the `force_password_change` flag inside their profile settings.
- **Redirection Filter**: A global `@app.before_request` hook intercepts all incoming requests from authenticated users. If `force_password_change` evaluates to `True`, the user is redirected to the `/change-password` page.
- **Bypassed Endpoints**: To prevent complete lockouts, the redirection hook must bypass static assets (CSS/JS files), the logout route (`/api/auth/logout`), and the change password submit endpoint (`/api/auth/change-password`).
- All other pages and API endpoints are blocked and redirect back to the password update page until the change password flow successfully completes.

---

## 2. Granular Permissions and Role Packages

This application supports three distinct user roles: **Admin**, **Operator**, and **Viewer**. These roles define standard permission baselines. Admins can then override individual permissions per user to create granular custom permission sets.

### 2.1 Baseline Role Mapping

The matrix below illustrates the default permissions assigned to each role:

#### Link Permissions

| Code Key | Admin Baseline | Operator Baseline | Viewer Baseline | Human-Facing Label | Description |
|---|---|---|---|---|---|
| `links.view` | ✓ | ✓ | ✓ | View Link List | Allows viewing of link lists, detail panels, and metrics. |
| `links.add` | ✓ | ✓ | ✗ | Add New Link | Allows creating new link configuration entries. |
| `links.edit` | ✓ | ✓ | ✗ | Edit Link Config | Allows modifying static configurations of existing links. |
| `links.delete` | ✓ | ✓ | ✗ | Delete Link | Purges link configurations and historical data. |
| `links.ping` | ✓ | ✓ | ✗ | Trigger Manual Ping | Allows executing manual on-demand reachability tests. |
| `links.export` | ✓ | ✓ | ✓ | Export Links CSV | Allows downloading link data in CSV format. |

#### User Management Permissions

| Code Key | Admin Baseline | Operator Baseline | Viewer Baseline | Human-Facing Label | Description |
|---|---|---|---|---|---|
| `users.view` | ✓ | ✗ | ✗ | View Users | View registered accounts inside the system logs and user directory. |
| `users.add` | ✓ | ✗ | ✗ | Add User | Create new user accounts and initialize baseline credentials. |
| `users.edit` | ✓ | ✗ | ✗ | Edit User Profile | Modify another user's name, email, and role assignments. |
| `users.delete` | ✓ | ✗ | ✗ | Delete User | Purges user accounts from the active directory. |
| `users.reset_password` | ✓ | ✗ | ✗ | Reset Password | Allows resetting another user's password. |
| `users.manage_permissions` | ✓ | ✗ | ✗ | Override User Permissions | Manage granular permission overrides on top of role baselines. |

#### System Config Permissions

| Code Key | Admin Baseline | Operator Baseline | Viewer Baseline | Human-Facing Label | Description |
|---|---|---|---|---|---|
| `config.view` | ✓ | ✗ | ✗ | View System Config | View system constants, mail parameters, and SSH gateway info. |
| `config.edit_smtp` | ✓ | ✗ | ✗ | Edit SMTP Config | Modify SMTP server connection parameters. |
| `config.edit_jumpserver` | ✓ | ✗ | ✗ | Edit Jump Server | Edit connection details for the SSH Jump Server gateway. |
| `config.edit_app` | ✓ | ✗ | ✗ | Edit App Settings | Update timeout thresholds, warning levels, and polling frequencies. |

#### Logs Permissions

| Code Key | Admin Baseline | Operator Baseline | Viewer Baseline | Human-Facing Label | Description |
|---|---|---|---|---|---|
| `logs.view_system` | ✓ | ✗ | ✗ | View System Log | Access system-wide security, audit, and operational logs. |
| `logs.view_ping` | ✓ | ✓ | ✓ | View Ping Log | View historical ICMP test results and trace files. |
| `logs.export` | ✓ | ✓ | ✗ | Export Logs CSV | Export system audit records and ping logs to CSV format. |

#### Notifications Permissions

| Code Key | Admin Baseline | Operator Baseline | Viewer Baseline | Human-Facing Label | Description |
|---|---|---|---|---|---|
| `notifications.view_own` | ✓ | ✓ | ✓ | View My Alerts | Access the personal in-app alert inbox. |
| `notifications.edit_own` | ✓ | ✓ | ✓ | Edit My Alerts | Mark personal alerts as read or change subscription preferences. |
| `notifications.manage_all` | ✓ | ✗ | ✗ | Manage User Subscriptions | View and override alert preferences for any system user. |

---

## 3. Effective Permission Resolution Algorithm

Granular permissions are evaluated using a hierarchical resolution algorithm. This allows administrators to grant or deny specific privileges to individual users, overriding their standard role-based baselines.

```
+-------------------------------------------------------------+
|               Call: has_permission(user, key)               |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|        Query: user_permission Table for Matching row        |
|               (user_id = user AND key = key)                |
+------------------------------+------------------------------+
                               |
                               | Row Exists?
                               +-----------------------+
                               | Yes                   | No
                               v                       v
+------------------------------------+   +------------------------------------+
|  Return evaluated `is_granted` DB  |   | Load User `Role` Column            |
|  Value (Explicit Custom Override)  |   | (admin, operator, viewer)          |
+------------------------------------+   +-----------------+------------------+
                                                           |
                                                           v
                                         +------------------------------------+
                                         | Resolve matching Baseline Role     |
                                         | Default value from the static Matrix|
                                         +-----------------+------------------+
                                                           |
                                                           v
                                         +------------------------------------+
                                         | Return resolved Boolean state      |
                                         +------------------------------------+
```

### 3.1 Resolving Effective Permissions

-   **Step 1**: Query the `user_permission` table for a record matching the target `user_id` and `permission_key`.
-   **Step 2**: If an override record exists, return the value of `is_granted` (either `True` or `False`). This override takes immediate precedence.
-   **Step 3**: If no override record is found, load the user's assigned role from the `User` table (`admin`, `operator`, or `viewer`).
-   **Step 4**: Resolve and return the baseline permission value from the static mapping matrix.

---

## 4. Permission Enforcement Decorators

To secure backend operations, API endpoints and page rendering routes are protected using custom decorators.

### 4.1 Login Required Decorator (`@login_required`)
-   Checks if `user_id` is present in the active Flask session.
-   If absent, redirects page requests to `/login`.
-   For API routes, returns an HTTP `401 Unauthorized` response.

### 4.2 Require Permission Decorator (`@require_permission`)
-   Checks if the logged-in user has the required permission using the effective permission resolution algorithm.
-   If the user has the permission, execution continues.
-   If the permission check fails, API requests return an HTTP `403 Forbidden` response:
    ```json
    {
      "error": "You do not have the required permissions to perform this action.",
      "code": "INSUFFICIENT_PERMISSIONS"
    }
    ```
-   For page requests, renders a standard access-denied page.
