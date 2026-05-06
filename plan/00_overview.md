# 00 — Project Overview

## 1. Project Summary

The **Microwave Backup Link Monitor** is an internal Network Operations Centre (NOC) web application designed for telecom engineering teams managing a core fiber backbone network. In this network architecture, each router is typically provisioned with one or two high-capacity fiber uplinks. To guarantee high availability and geographical redundancy, a microwave (MW) link is deployed as a hot-standby backup. 

This system acts as a single pane of glass to:
- **Track Link Configurations**: Store static inventory data for primary fiber and backup microwave link pairs.
- **Collect Telemetry**: Periodically poll real-time utilization metrics from routers via secure shell connections.
- **Monitor Reachability**: Orchestrate periodic reachability (ping) cycles to the microwave link interfaces.
- **Send Proactive Alerts**: Instantly notify operators and administrators via email and in-app alerts when link states degrade or fail, incorporating anti-spam rules (hysteresis and throttling).
- **Control Security**: Enforce strict session-based authentication and granular permission overrides on top of role-based defaults.

All configuration and control parameters are manageable directly via the user interface, eliminating operational reliance on command-line configurations or raw environment file edits.

---

## 2. Architecture Diagram

The diagram below illustrates the end-to-end communication flow, demonstrating how the web interface interacts with the backend services, database storage, and remote network infrastructure.

```
+-----------------------------------------------------------------------------------+
|                                 Client Browser                                    |
|   HTML5 Layouts, Vanilla JavaScript Modules, Chart.js Visuals, Custom CSS         |
+----------------------------------------+------------------------------------------+
                                         |
                                         | HTTP / HTTPS (JSON REST API)
                                         v
+-----------------------------------------------------------------------------------+
|                               Flask Web Application                               |
|                                                                                   |
|  +---------------------------+  +----------------------+  +--------------------+  |
|  |  Session Authentication   |  |   REST API Engines   |  |   Crypto Service   |  |
|  |     (Signed Cookies)      |  |  (Flask Blueprints)  |  |  (Fernet Database) |  |
|  +-------------+-------------+  +----------+-----------+  +---------+----------+  |
|                |                           |                        |             |
|                v                           v                        v             |
|  +-----------------------------------------------------------------------------+  |
|  |                            SQLAlchemy ORM Layer                             |  |
|  +-------------------------------------+---------------------------------------+  |
|                                        |                                          |
|                                        v                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                     Database Storage Engine (SQLite/Postgres)               |  |
|  +-----------------------------------------------------------------------------+  |
|                                        ^                                          |
|                                        | Reads Settings / Records Results         |
|  +-------------------------------------+---------------------------------------+  |
|  |                     APScheduler Embedded Background Threads                 |  |
|  |                                                                             |  |
|  |  +----------------------------------+  +---------------------------------+  |
|  |  |      Ping Check Scheduler        |  |     Metric Harvesting Engine    |  |
|  |  +----------------+-----------------+  +----------------+----------------+  |
|  +-------------------|-------------------------------------|------------------+  |
|                      |                                     |                      |
|                      | Uses SSHService (Paramiko)          |                      |
|                      v                                     v                      |
|  +-----------------------------------------------------------------------------+  |
|  |                             SSH Gateway Layer                               |  |
|  |             Establishes secure channel via Jump Server to Target IPs        |  |
|  +-------------------------------------+---------------------------------------+  |
|                                        |                                          |
|                                        | Tunnelled SSH / ICMP echo
                                         v
+-----------------------------------------------------------------------------------+
|                             Active Network Infrastructure                         |
|                                                                                   |
|  +---------------------------+  +----------------------+  +--------------------+  |
|  |    Primary Router Nodes   |  |  Microwave Standby   |  |  SMTP Mail Server  |  |
|  |     (ATN / X8 Series)     |  |     IP Addresses     |  |  (Operator Email)  |  |
|  +---------------------------+  +----------------------+  +--------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Planned Files and Folders

The system is organized into a clean split between backend python code, static frontend templates, and planning files:

- `/app`: Base application directory
  - `__init__.py`: App factory bootstrap, APScheduler startup logic.
  - `models.py`: Declarative SQLAlchemy models representing all system resources.
  - `extensions.py`: Centralized extension singletons (Database, Password Hashing, Scheduler).
  - `permissions.py`: Custom security decorators and permission validation algorithms.
  - `routes/`: Flask blueprint routes
    - `auth.py`: Controls login, logout, and credential management.
    - `setup.py`: Manages the application first-boot installation sequence.
    - `dashboard.py`: Renders main interface and aggregates dashboard KPIs.
    - `links.py`: Performs inventory link CRUD, triggers manual ping, and generates CSV exports.
    - `users.py`: Handles administrators, operators, viewers, and user override settings.
    - `notifications.py`: Serves in-app alert lists, marking read, and preference updates.
    - `logs.py`: Exposes system audit trail and ping logging files.
    - `settings.py`: Admin panel settings for SMTP, Jump Server, and App thresholds.
    - `profile.py`: User self-service profile and password modification.
  - `services/`: Business logic scripts
    - `ssh_service.py`: Establishes tunnelled and direct interactive shell sessions via Paramiko.
    - `ping_service.py`: Handles background and user-triggered ping tracking routines.
    - `metric_service.py`: Parses utilization command outputs and inserts telemetry records.
    - `scheduler.py`: Houses APScheduler jobs, timing parameters, and concurrency controls.
    - `notification_service.py`: Resolves alert conditions, builds alerts, and sends emails.
    - `crypto_service.py`: Manages symmetric cryptography for secrets at rest.
    - `log_service.py`: Provides unified system audit logging across all components.
  - `config.py`: Environment loader validating `.env` definitions.
- `/frontend`: Client-side interface
  - `login.html`: Dedicated login window containing lockout warnings.
  - `setup.html`: Single-page setup installation checklist.
  - `change_password.html`: Force redirection password replacement screen.
  - `index.html`: NOC Dashboard featuring high-density data visualizations.
  - `links.html`: Static link configuration dashboard.
  - `users.html`: User creation and granular permissions control table.
  - `notifications.html`: List view of alert notifications.
  - `logs.html`: Unified search and audit logs table.
  - `settings.html`: Application settings control console.
  - `profile.html`: Personal configuration screen.
  - `css/`: Pure CSS stylesheets (no preprocessors)
    - `main.css`: Core colors, grids, resets, and layout guidelines.
    - `components.css`: Cards, buttons, alerts, tabs, and dynamic components.
    - `table.css`: Responsive, dense layout styles for network inventory lists.
    - `modal.css`: Full screen overlays with animation patterns.
    - `forms.css`: Standardized form control groups and field validation indicator visuals.
  - `js/`: Vanilla JS architecture (zero frameworks)
    - `auth.js`: Manages login attempts and redirection.
    - `dashboard.js`: Orchestrates KPI loading, ping logs, and countdown updates.
    - `table.js`: Controls paginated tables, row toggles, and detail templates.
    - `modal.js`: Opens form views and executes validation routines.
    - `users.js`: Connects user configurations and override selectors.
    - `notifications.js`: Fetches personal notifications and toggles subscriptions.
    - `logs.js`: Integrates log tables, multi-column search, and csv downloader.
    - `settings.js`: Controls connection testing triggers and form validation.
    - `charts.js`: Renders radial utilization gauges and history sparklines.
    - `utils.js`: Stores common formats, badges, progress bars, and debouncers.
- `/plan`: This directory containing system design documentation.
- `run.py`: Entrypoint file launching the Flask server.
- `requirements.txt`: Python package requirements.
- `.env.example`: Configuration template for environment setups.
- `README.md`: Quick start guide and workspace assembly guide.

---

## 4. Environment Variables

The application intentionally restricts its environment configuration variables to three critical parameters. This design minimizes operational configuration leakage and ensures that all sensitive network credentials, SMTP parameters, and thresholds are stored securely inside the database under key-based encryption.

| Variable Name | Required | Type | Default Value | Purpose |
|---|---|---|---|---|
| `FLASK_SECRET_KEY` | Yes | String | None | Cryptographic key utilized to sign Flask session cookies. Must be a cryptographically secure 32-byte string. Also used to derive the database encryption key. |
| `DATABASE_URL` | Yes | String | `sqlite:///instance/mw_monitor.db` | Connection string for Flask-SQLAlchemy. Supports SQLite for development and standard PostgreSQL URIs for production environments. |
| `FLASK_ENV` | No | String | `production` | Operational environment setting. Dictates debug logging, template reloading, and stack trace verbosity. Valid values are `development` or `production`. |
