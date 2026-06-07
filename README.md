# MW Backup Monitor System

A Flask + Vanilla JS single-page-style application for monitoring microwave backup links, gathering link status, utilization metrics, and integration with external MySQL utilization data.

## Features

- Link CRUD and real-time status monitoring
- External MySQL lookup for Link ID and LEG utilization data
- Daily refresh of external utilization metrics via scheduler
- Encrypted persistent configuration in `data/secrets/secrets.json`
- SMTP and SSH jump server setup and live testing
- System settings configurable from the UI

## Requirements

- Python 3.11+
- Flask
- Flask-SQLAlchemy
- APScheduler
- SQLAlchemy
- PyMySQL
- cryptography

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Running locally

```bash
python run.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Production

Start with Gunicorn:

```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

## Setup

1. Open the application in your browser.
2. Complete the initial setup wizard.
3. Configure:
   - Primary application database
   - Admin user account
   - SMTP settings (optional)
   - Jump server settings (optional)
   - External MySQL lookup database (optional)

### External MySQL lookup configuration

The setup wizard now includes an optional External DB section for configuring a MySQL database used to resolve:

- `Link ID` lookup via `pandq_mw_link_max_week_utilization`
- `LEG` lookup via `pandq_leg_max_week_utilization`

If enabled, the application stores this configuration encrypted in `data/secrets/secrets.json` and exposes it through the system settings UI so it can be changed after initial setup.

## Settings

The system settings modal includes:

- General ping and session timeout values
- SMTP configuration and test button
- Jump server configuration and test button
- External MySQL lookup configuration and test button
- Notification subscription preferences

## External MySQL table expectations

The external database must contain these tables with the expected fields:

- `pandq_mw_link_max_week_utilization`
  - `Link_Name`
  - `Link_Name_Unif`
  - `Link_Categ`
  - `SiteID`
  - `Source_NE_Card`
  - `SiteID_Opp`
  - `Sink_NE_Card`
  - `AVG_MAX_Util_RxTx_perc`
  - `AVG_MAX_Rx_Kbps`
  - `AVG_MAX_Tx_Kbps`

- `pandq_leg_max_week_utilization`
  - `LEG_Name`
  - `AVG_MAX_MBitRate`
  - `Interface_Speed_Min`
  - `Interface_Speed_Max`
  - `Sub_LEG_Count`

## External DB lookup usage

- In the Add/Edit Link modal, use the **Get Link** button to populate external utilization fields using the configured external database.
- Use the **Get LEG** button to look up LEG metadata for matching `LEG_Name`.
- Utilization data refreshes daily via the scheduler service.

## Configuration sources

The application loads configuration in this order:

1. `data/secrets/secrets.json` (encrypted values)
2. Environment variables:
  - `SECRET_KEY`
  - `DATABASE_URL`
  - `EXTERNAL_UTIL_DATABASE_URL`

## Notes

- `data/secrets/secrets.json` is recommended for production and is created during initial setup.
- Keep the `SECRET_KEY` secret and never commit it into source control.
