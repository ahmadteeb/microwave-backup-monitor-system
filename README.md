# Microwave Backup Link Monitor System

A robust, real-time monitoring and alerting system designed for Network Operations Centers (NOC). This application tracks the health, availability, and bandwidth utilization of Microwave (MW) backup links, providing real-time UI updates, threaded email alerts, and Slack/Webhook integrations.

---

## 🌟 Key Features

### 📡 Real-Time Monitoring & Metrics
* **ICMP Ping Polling:** Actively polls configured MW IP addresses at customizable intervals to determine Up/Down status.
* **Jump Server Support:** Optionally routes pings through an SSH Jump Server to access restricted or isolated network segments.
* **Utilization Tracking:** Integrates with external MySQL databases to pull in external bandwidth utilization metrics (`AVG_MAX_Util_RxTx_perc`, `AVG_MAX_MBitRate`).
* **Warning & Critical Thresholds:** Supports global and per-link customized utilization thresholds (Warning & Critical), emitting alerts when limits are breached.

### 🔔 Intelligent Alerting & Notifications
* **Smart Email Threading:** Link failure and recovery emails are grouped into single threads via `Message-ID` and `In-Reply-To` headers, reducing inbox clutter for NOC engineers.
* **Slack & Custom Webhooks:** Supports dynamically configurable webhook endpoints for real-time notifications to Slack channels or custom APIs.
* **Daily Digest Reports:** Automatically sends a scheduled email report summarizing link availability (24h uptime), current statuses, and high utilization events.
* **Granular Subscriptions:** Users can subscribe/unsubscribe from specific events (Link Up, Link Down, High Utilization, System Errors).

### 🛡️ Security & Role-Based Access (RBAC)
* **Encrypted Secrets:** Database credentials, SMTP passwords, and external integrations are securely encrypted via symmetric cryptography and stored in `data/secrets/secrets.json`.
* **Role-Based Access Control:** Highly granular permissions system (e.g., `view_dashboard`, `manage_users`, `manage_links`, `edit_app_settings`).
* **First-Run Setup Wizard:** A secure bootstrap UI that forces the creation of an admin account and initial configurations before the app can be accessed.

### 💻 Modern User Interface
* **Real-time Dashboard:** Built with vanilla JS and Socket.IO, the dashboard updates dynamically without page reloads.
* **Responsive Modals & Settings:** A central system settings modal allows live configuration of Webhooks, SMTP, Ping Intervals, and Jump Servers without restarting the application.

---

## 🛠️ Technology Stack

* **Backend:** Python 3.10+, Flask, Flask-SQLAlchemy, Flask-SocketIO (Eventlet)
* **Task Scheduling:** APScheduler (Background polling, daily reports, external DB syncs)
* **Frontend:** Vanilla JavaScript, HTML5, CSS3, FontAwesome
* **Database:** SQLite (default for internal storage), PyMySQL (for external metrics lookups)
* **Security:** bcrypt (password hashing), cryptography (Fernet symmetric encryption)

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10 or higher
* Docker & Docker Compose (optional, for simulation)

### Local Installation

1. **Clone the repository and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   # Development Mode
   python run.py

   # Production Mode (Required for stable WebSockets)
   gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 run:app
   ```

3. **Complete the Setup Wizard:**
   Open `http://localhost:5000` in your browser. You will be redirected to the `/setup` wizard to configure your initial Admin user, database string, and encryption keys.

---

## 🐋 Docker Simulation Environment

This repository includes a full Docker Compose simulation environment. It spins up the monitor application alongside several lightweight alpine containers to act as "simulated MW links."

**To start the simulation:**
```bash
docker compose -f docker-compose-simulation.yaml up -d --build
```

**What it does:**
1. Builds the `mwbackuplinkmonitorsystem-app` image.
2. Creates an isolated Docker network (`172.20.0.x`).
3. Starts the main app container on `172.20.0.2`.
4. Starts 10 Alpine "device" containers (`172.20.0.3` through `172.20.0.12`).
5. The app container automatically runs `simulation-data.py` to seed the database with links pointing to these Alpine containers before starting the Gunicorn server.

You can now log into `http://localhost:5000`, see the 10 simulated links online, and optionally bring down a simulated device to watch the system catch the failure:
```bash
# Simulate a link failure
docker stop simulation_device4
```

---

## ⚙️ System Settings & Configuration

The application allows for hot-reloading of settings via the UI (`Settings Modal`).

* **General:** Modify ping interval (e.g., 60 seconds), session timeout length, and the daily report schedule (Hour/Minute).
* **SMTP:** Configure the outgoing mail server for email alerts. Includes a "Test Connection" tool.
* **Jump Server:** Configure an intermediate SSH server. If enabled, the system connects to the jump server via SSH and executes the ping commands from there.
* **External DB:** Configure credentials for an external MySQL database to fetch bandwidth metrics.
* **Webhooks:** Add custom endpoints (Slack or Generic POST) to receive JSON payloads for system events.

### Expected External MySQL Schema
If using the External DB feature, the system expects the following tables:

**1. `pandq_mw_link_max_week_utilization`**
- `Link_Name`, `Link_Name_Unif`, `Link_Categ`, `SiteID`, `Source_NE_Card`, `SiteID_Opp`, `Sink_NE_Card`, `AVG_MAX_Util_RxTx_perc`, `AVG_MAX_Rx_Kbps`, `AVG_MAX_Tx_Kbps`

**2. `pandq_leg_max_week_utilization`**
- `LEG_Name`, `AVG_MAX_MBitRate`, `Interface_Speed_Min`, `Interface_Speed_Max`, `Sub_LEG_Count`

---

## 🔐 Secrets Management

For maximum security, the application avoids storing raw passwords in the SQLite database. During the setup wizard, a symmetric encryption key is generated. 

All sensitive data (SMTP passwords, Jump Server passwords, External DB passwords, Webhook URLs) are:
1. Encrypted using the `cryptography` library.
2. Written to `data/secrets/secrets.json`.

**⚠️ Important:** 
- The application requires `SECRET_KEY` to be set in the environment or present in `secrets.json` to boot in production.
- Do NOT commit `data/secrets/secrets.json` to source control.

---

## 📡 Webhook Payload Format

When a Webhook is configured, the system sends a JSON `POST` request with the following structure:

```json
{
  "event_key": "mw_link_down",
  "message": "Link TEST_LINK_01 (192.168.100.5) is DOWN",
  "severity": "CRITICAL",
  "context": {
    "link_id": "TEST_LINK_01",
    "leg_name": "EAST_LEG",
    "ip": "192.168.100.5"
  },
  "timestamp": "2026-06-09T12:00:00Z"
}
```
If the webhook is configured as a `Slack` type, the payload is automatically translated into Slack's expected `{"text": "..."}` format.
