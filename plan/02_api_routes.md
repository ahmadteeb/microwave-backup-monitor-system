# 02 — API Routes

All API endpoints return JSON payloads. Unauthorized access attempts to protected resources return an HTTP `401 Unauthorized` response. Access attempts violating granular permission overrides return an HTTP `403 Forbidden` response.

---

## 1. Authentication Routes (Public)

These routes handle session validation and credential replacement.

### 1.1 `POST /api/auth/login`
- **Method**: `POST`
- **Required Permission**: None (Public)
- **Request Body**:
  ```json
  {
    "username": "operator1",
    "password": "Password123"
  }
  ```
- **Success Response (200 OK)**:
  - Sets signed session cookie (`session` key containing encrypted credentials).
  ```json
  {
    "status": "success",
    "message": "Login successful",
    "data": {
      "user_id": 2,
      "username": "operator1",
      "full_name": "John Doe",
      "role": "operator",
      "force_password_change": false
    }
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Missing inputs.
  - `401 Unauthorized`: `"Invalid username or password"`. Used for both missing credentials and lockout conditions, ensuring usernames are not leaked.
  - `403 Forbidden`: Account is locked. Returns:
    ```json
    {
      "error": "Account is temporarily locked. Please try again later or contact your administrator.",
      "code": "ACCOUNT_LOCKED"
    }
    ```

### 1.2 `POST /api/auth/logout`
- **Method**: `POST`
- **Required Permission**: None (Public, requires an active session)
- **Request Body**: None
- **Success Response (200 OK)**:
  - Clear session cookie.
  ```json
  {
    "status": "success",
    "message": "Logged out successfully"
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: No active session found.

### 1.3 `POST /api/auth/change-password`
- **Method**: `POST`
- **Required Permission**: Authenticated (Forced or voluntary password changes)
- **Request Body**:
  ```json
  {
    "current_password": "OldPassword123",
    "new_password": "NewSecurePassword456",
    "confirm_password": "NewSecurePassword456"
  }
  ```
- **Success Response (200 OK)**:
  - Resets password hash, marks `force_password_change = false`.
  ```json
  {
    "status": "success",
    "message": "Password changed successfully"
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Passwords mismatch or fail complexity checks (must be at least 8 characters, containing uppercase, lowercase, numbers, and symbols).
  - `401 Unauthorized`: Invalid active session or incorrect current password.

---

## 2. Setup Wizard Routes (Public)

These routes are only accessible if `is_complete` in `SetupState` evaluates to `False`. Once setup is marked complete, any access attempts return a `403 Forbidden` error.

### 2.1 `POST /api/setup/complete`
- **Method**: `POST`
- **Required Permission**: None (Only on first boot)
- **Request Body**:
  ```json
  {
    "admin": {
      "full_name": "System Administrator",
      "username": "admin",
      "email": "admin@telecom.net",
      "password": "SecurePassword123!",
      "confirm_password": "SecurePassword123!"
    },
    "smtp": {
      "host": "smtp.telecom.net",
      "port": 587,
      "username": "alerts@telecom.net",
      "password": "SMTPPassword123",
      "from_address": "alerts@telecom.net",
      "use_tls": true,
      "use_ssl": false
    },
    "jumpserver": {
      "host": "10.0.0.10",
      "port": 22,
      "username": "gateway",
      "password": "GatewayPassword123"
    }
  }
  ```
- **Success Response (201 Created)**:
  ```json
  {
    "status": "success",
    "message": "Initial configuration complete. Administrator profile generated.",
    "is_complete": true
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Input validation failed, or passwords mismatched.
  - `403 Forbidden`: Setup has already been completed.

### 2.2 `POST /api/setup/test-smtp`
- **Method**: `POST`
- **Required Permission**: None (Only during initial setup)
- **Request Body**: Same schema as `"smtp"` object inside Section 2.1.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "SMTP server connection test completed successfully. Test alert delivered."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Invalid parameters or direct mail generation failure.
  - `403 Forbidden`: Setup already marked complete.

### 2.3 `POST /api/setup/test-jumpserver`
- **Method**: `POST`
- **Required Permission**: None (Only during initial setup)
- **Request Body**: Same schema as `"jumpserver"` object inside Section 2.1.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Secure SSH tunnel handshake completed successfully."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Connection handshake failed.

---

## 3. Dashboard Routes

These routes feed telemetry data and charts to the main dashboard workspace.

### 3.1 `GET /api/dashboard/summary`
- **Method**: `GET`
- **Required Permission**: `links.view`
- **Request Body**: None
- **Success Response (200 OK)**:
  ```json
  {
    "data": {
      "total_links": 142,
      "mw_reachable": 138,
      "mw_unreachable": 4,
      "high_utilization": 2,
      "system_health": "degraded",
      "next_check_seconds": 45
    }
  }
  ```

### 3.2 `GET /api/dashboard/links`
- **Method**: `GET`
- **Required Permission**: `links.view`
- **Parameters**: `?page=1&per_page=10&search=BK-01&status=down&leg=LEG598`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": 1,
        "link_id": "BK-001",
        "leg_name": "LEG598",
        "site_a": "Alpha Base",
        "site_b": "Delta Repeater",
        "equipment_a": "ATN 910-C",
        "equipment_b": "ATN 910-C",
        "mw_ip": "10.58.14.1",
        "status": "up",
        "latency_ms": 12.4,
        "fiber_util_pct": 45.2,
        "mw_util_pct": 0.0,
        "last_updated": "2026-05-06T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 10
  }
  ```

---

## 4. Link Routes

These endpoints perform CRUD operations on microwave link pairings.

### 4.1 `GET /api/links`
- **Method**: `GET`
- **Required Permission**: `links.view`
- **Parameters**: `?page=1&per_page=20&search=SITE-A`
- **Success Response (200 OK)**: Paginated link inventory payload. Same response format as `GET /api/dashboard/links`.

### 4.2 `POST /api/links`
- **Method**: `POST`
- **Required Permission**: `links.add`
- **Request Body**:
  ```json
  {
    "link_id": "BK-001",
    "leg_name": "LEG598",
    "site_a": "Alpha Base",
    "site_b": "Delta Repeater",
    "equipment_a": "ATN 910-C",
    "equipment_b": "ATN 910-C",
    "mw_ip": "10.58.14.1",
    "link_type": "Microwave Backup",
    "notes": "Backup line for Delta site"
  }
  ```
- **Success Response (201 Created)**:
  ```json
  {
    "status": "success",
    "message": "Link successfully registered in inventory database.",
    "data": {
      "id": 1,
      "link_id": "BK-001"
    }
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Input checks failed. Validation includes IP address structural correctness, and uppercase alphanumeric checks on `link_id` conforming to `BK-XXX`.
  - `409 Conflict`: A link using that exact `link_id` is already registered.

### 4.3 `GET /api/links/<id>`
- **Method**: `GET`
- **Required Permission**: `links.view`
- **Success Response (200 OK)**:
  ```json
  {
    "data": {
      "id": 1,
      "link_id": "BK-001",
      "leg_name": "LEG598",
      "site_a": "Alpha Base",
      "site_b": "Delta Repeater",
      "equipment_a": "ATN 910-C",
      "equipment_b": "ATN 910-C",
      "mw_ip": "10.58.14.1",
      "link_type": "Microwave Backup",
      "notes": "Backup line for Delta site",
      "status": "up",
      "latency_ms": 12.4,
      "fiber_util_pct": 45.2,
      "mw_util_pct": 0.0,
      "consecutive_timeouts": 0
    }
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Target ID does not exist in the database.

### 4.4 `PUT /api/links/<id>`
- **Method**: `PUT`
- **Required Permission**: `links.edit`
- **Request Body**: Same structure as `POST /api/links`.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Link configuration successfully updated."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Input checks failed.
  - `404 Not Found`: Target ID does not exist.

### 4.5 `DELETE /api/links/<id>`
- **Method**: `DELETE`
- **Required Permission**: `links.delete`
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Link successfully purged from inventory database."
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Link matching ID not found.

### 4.6 `POST /api/links/<id>/ping`
- **Method**: `POST`
- **Required Permission**: `links.ping`
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "is_reachable": true,
      "latency_ms": 11.2,
      "raw_output": "PING 10.58.14.1 (10.58.14.1) 56(84) bytes of data.\n64 bytes from 10.58.14.1: icmp_seq=1 ttl=64 time=11.2 ms"
    }
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Link does not exist.
  - `502 Bad Gateway`: Jumpserver SSH gateway is down or connection timed out.

### 4.7 `GET /api/links/<id>/ping-history`
- **Method**: `GET`
- **Required Permission**: `links.view`
- **Parameters**: `?page=1&per_page=24`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "timestamp": "2026-05-06T12:00:00Z",
        "is_reachable": true,
        "latency_ms": 12.4,
        "triggered_by": "scheduler"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 24
  }
  ```

### 4.8 `GET /api/links/<id>/metrics`
- **Method**: `GET`
- **Required Permission**: `links.view`
- **Parameters**: `?page=1&per_page=24`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "timestamp": "2026-05-06T12:00:00Z",
        "fiber_util_pct": 45.2,
        "mw_util_pct": 0.0
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 24
  }
  ```

### 4.9 `GET /api/links/export`
- **Method**: `GET`
- **Required Permission**: `links.export`
- **Success Response (200 OK)**:
  - Generates downloadable CSV stream file directly.
  - Header line: `Link ID, LEG, Site A, Site B, Microwave IP, Status, Latency MS, Last Updated`

---

## 5. User Management Routes

These routes control operational and security user attributes.

### 5.1 `GET /api/users`
- **Method**: `GET`
- **Required Permission**: `users.view`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": 2,
        "username": "operator1",
        "full_name": "John Doe",
        "email": "operator1@telecom.net",
        "role": "operator",
        "is_active": true,
        "is_locked": false,
        "last_login_at": "2026-05-06T10:00:00Z"
      }
    ]
  }
  ```

### 5.2 `POST /api/users`
- **Method**: `POST`
- **Required Permission**: `users.add`
- **Request Body**:
  ```json
  {
    "username": "operator1",
    "full_name": "John Doe",
    "email": "operator1@telecom.net",
    "role": "operator",
    "password": "SecurePassword123!",
    "force_password_change": true
  }
  ```
- **Success Response (201 Created)**:
  ```json
  {
    "status": "success",
    "message": "User account generated.",
    "data": { "id": 2 }
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Input checks or complexity validations failed.
  - `409 Conflict`: Username or email already registered in database.

### 5.3 `PUT /api/users/<user_id>`
- **Method**: `PUT`
- **Required Permission**: `users.edit`
- **Request Body**:
  ```json
  {
    "full_name": "Johnathan Doe",
    "email": "johndoe@telecom.net",
    "role": "operator",
    "is_active": true
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Profile parameters updated."
  }
  ```

### 5.4 `DELETE /api/users/<user_id>`
- **Method**: `DELETE`
- **Required Permission**: `users.delete`
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "User account purged successfully."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: User attempted to delete their own logged-in account.

### 5.5 `POST /api/users/<user_id>/reset-password`
- **Method**: `POST`
- **Required Permission**: `users.reset_password`
- **Request Body**:
  ```json
  {
    "password": "NewSecretPassword1!",
    "confirm_password": "NewSecretPassword1!",
    "force_password_change": true
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "User credential reset. Reset token and flags initialized."
  }
  ```

### 5.6 `GET /api/users/<user_id>/permissions`
- **Method**: `GET`
- **Required Permission**: `users.manage_permissions`
- **Success Response (200 OK)**:
  ```json
  {
    "data": {
      "role": "operator",
      "overrides": [
        { "permission_key": "links.delete", "is_granted": true }
      ],
      "effective_permissions": {
        "links.view": true,
        "links.delete": true
      }
    }
  }
  ```

### 5.7 `PUT /api/users/<user_id>/permissions`
- **Method**: `PUT`
- **Required Permission**: `users.manage_permissions`
- **Request Body**:
  ```json
  {
    "overrides": [
      { "permission_key": "links.delete", "is_granted": true }
    ]
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Permission overrides updated successfully."
  }
  ```

### 5.8 `POST /api/users/<user_id>/unlock`
- **Method**: `POST`
- **Required Permission**: `users.edit`
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "User account unlocked. Failed login count reset."
  }
  ```

---

## 6. Notification Routes

These endpoints govern dashboard notifications and subscription alerts.

### 6.1 `GET /api/notifications`
- **Method**: `GET`
- **Required Permission**: `notifications.view_own`
- **Parameters**: `?page=1&per_page=15`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": 1,
        "event_key": "mw_link_down",
        "severity": "critical",
        "link_id": "BK-001",
        "message": "Standby microwave link BK-001 has entered the down state.",
        "is_read": false,
        "created_at": "2026-05-06T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 15
  }
  ```

### 6.2 `GET /api/notifications/unread-count`
- **Method**: `GET`
- **Required Permission**: `notifications.view_own`
- **Success Response (200 OK)**:
  ```json
  {
    "data": { "unread_count": 1 }
  }
  ```

### 6.3 `POST /api/notifications/<id>/read`
- **Method**: `POST`
- **Required Permission**: `notifications.view_own`
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Alert marked as read."
  }
  ```

### 6.4 `POST /api/notifications/read-all`
- **Method**: `POST`
- **Required Permission**: `notifications.view_own`
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "All alert records flagged as read."
  }
  ```

### 6.5 `GET /api/notifications/subscriptions`
- **Method**: `GET`
- **Required Permission**: `notifications.view_own`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      { "event_key": "mw_link_down", "is_subscribed": true }
    ]
  }
  ```

### 6.6 `PUT /api/notifications/subscriptions`
- **Method**: `PUT`
- **Required Permission**: `notifications.edit_own`
- **Request Body**:
  ```json
  {
    "subscriptions": [
      { "event_key": "mw_link_down", "is_subscribed": false }
    ]
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Alert notification settings saved."
  }
  ```

### 6.7 `GET /api/users/<user_id>/notifications/subscriptions`
- **Method**: `GET`
- **Required Permission**: `notifications.manage_all`
- **Success Response (200 OK)**: Same payload schema as `GET /api/notifications/subscriptions`.

### 6.8 `PUT /api/users/<user_id>/notifications/subscriptions`
- **Method**: `PUT`
- **Required Permission**: `notifications.manage_all`
- **Request Body**: Same schema as `PUT /api/notifications/subscriptions`.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "User alert subscription overrides finalized."
  }
  ```

---

## 7. System Config Routes

These endpoints configure administrative credentials and thresholds.

### 7.1 `GET /api/settings/smtp`
- **Method**: `GET`
- **Required Permission**: `config.view`
- **Success Response (200 OK)**:
  ```json
  {
    "data": {
      "host": "smtp.telecom.net",
      "port": 587,
      "username": "alerts@telecom.net",
      "password": "****************",
      "from_address": "alerts@telecom.net",
      "use_tls": true,
      "use_ssl": false
    }
  }
  ```

### 7.2 `PUT /api/settings/smtp`
- **Method**: `PUT`
- **Required Permission**: `config.edit_smtp`
- **Request Body**: Same schema as `"smtp"` payload inside Section 2.1.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "SMTP mailing system parameters configured."
  }
  ```

### 7.3 `POST /api/settings/smtp/test`
- **Method**: `POST`
- **Required Permission**: `config.edit_smtp`
- **Success Response (200 OK)**: Sends standard test connection email to current user.
  ```json
  {
    "status": "success",
    "message": "SMTP connection diagnostic cleared. Delivered test alert."
  }
  ```

### 7.4 `GET /api/settings/jumpserver`
- **Method**: `GET`
- **Required Permission**: `config.view`
- **Success Response (200 OK)**:
  ```json
  {
    "data": {
      "host": "10.0.0.10",
      "port": 22,
      "username": "gateway",
      "password_configured": true,
      "private_key_configured": false
    }
  }
  ```

### 7.5 `PUT /api/settings/jumpserver`
- **Method**: `PUT`
- **Required Permission**: `config.edit_jumpserver`
- **Request Body**:
  ```json
  {
    "host": "10.0.0.10",
    "port": 22,
    "username": "gateway",
    "password": "NewSecretGatewayPassword12",
    "private_key": null
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Jump Server routing credentials updated."
  }
  ```

### 7.6 `POST /api/settings/jumpserver/test`
- **Method**: `POST`
- **Required Permission**: `config.edit_jumpserver`
- **Success Response (200 OK)**: Performs immediate diagnostic SSH connection to verify login credentials.
  ```json
  {
    "status": "success",
    "message": "Jump Server handshakes validated."
  }
  ```

### 7.7 `GET /api/settings/app`
- **Method**: `GET`
- **Required Permission**: `config.view`
- **Success Response (200 OK)**:
  ```json
  {
    "data": {
      "session_timeout_minutes": 480,
      "ping_interval_seconds": 60,
      "metric_poll_interval_seconds": 60,
      "consecutive_timeout_alert_threshold": 5,
      "util_warning_threshold_pct": 70.0,
      "util_critical_threshold_pct": 90.0
    }
  }
  ```

### 7.8 `PUT /api/settings/app`
- **Method**: `PUT`
- **Required Permission**: `config.edit_app`
- **Request Body**: Same parameters as returned payload inside Section 7.7.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Application threshold limits modified."
  }
  ```

---

## 8. Logs Routes

These endpoints serve security audit records and connectivity logs.

### 8.1 `GET /api/logs/system`
- **Method**: `GET`
- **Required Permission**: `logs.view_system`
- **Parameters**: `?page=1&per_page=50&category=auth&actor=admin`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": 1,
        "timestamp": "2026-05-06T12:00:00Z",
        "category": "auth",
        "event": "login_success",
        "actor": "admin",
        "target": "admin",
        "detail": { "ip": "192.168.1.50" },
        "ip_address": "192.168.1.50"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 50
  }
  ```

### 8.2 `GET /api/logs/ping`
- **Method**: `GET`
- **Required Permission**: `logs.view_ping`
- **Parameters**: `?page=1&per_page=50&since=1714999200`
- **Success Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": 1,
        "link_id": "BK-001",
        "timestamp": "2026-05-06T12:00:00Z",
        "is_reachable": true,
        "latency_ms": 12.4
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 50
  }
  ```

### 8.3 `GET /api/logs/system/export`
- **Method**: `GET`
- **Required Permission**: `logs.export`
- **Success Response (200 OK)**:
  - Generates downloadable CSV stream file directly.
  - Header line: `Timestamp, Category, Event, Actor, Target, Details, IP Address`

### 8.4 `GET /api/logs/ping/export`
- **Method**: `GET`
- **Required Permission**: `logs.export`
- **Success Response (200 OK)**:
  - Generates downloadable CSV stream file directly.
  - Header line: `Timestamp, Link ID, Reachable, Latency MS`

---

## 9. Profile Routes

These endpoints serve self-service profile and password modification.

### 9.1 `PUT /api/profile`
- **Method**: `PUT`
- **Required Permission**: Authenticated
- **Request Body**:
  ```json
  {
    "full_name": "New Name",
    "email": "newemail@telecom.net"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Profile details updated successfully."
  }
  ```

### 9.2 `POST /api/profile/change-password`
- **Method**: `POST`
- **Required Permission**: Authenticated
- **Request Body**:
  ```json
  {
    "current_password": "OldPassword1!",
    "new_password": "NewSecurePassword1!",
    "confirm_password": "NewSecurePassword1!"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Password updated."
  }
  ```
