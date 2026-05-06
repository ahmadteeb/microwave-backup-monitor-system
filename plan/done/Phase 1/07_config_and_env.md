# 07 — Configuration and Environment Variables

## `.env.example` Contents

Below is the full `.env.example` file listing every variable with its type, default value, and description.

```
# ============================================================
# MW Backup Link Monitor — Environment Configuration
# ============================================================
# Copy this file to .env and fill in your values.
# Lines starting with # are comments.
# ============================================================

# --- Jump Server (SSH Gateway) ---

# Hostname or IP address of the SSH jump server used to reach MW link IPs.
# Type: string. Required.
JUMP_HOST=10.0.0.1

# SSH port on the jump server.
# Type: integer. Default: 22.
JUMP_PORT=22

# SSH username for authenticating to the jump server.
# Type: string. Required.
JUMP_USER=admin

# SSH password for the jump server.
# Type: string. Required.
# Note: This is used as the initial/fallback config. Once configured via the
# Settings API, the database-stored (Fernet-encrypted) value takes precedence.
JUMP_PASSWORD=changeme

# --- Ping Configuration ---

# Interval in seconds between automated ping cycles.
# Type: integer. Default: 60. Minimum: 10.
PING_INTERVAL_SECONDS=60

# Number of ICMP echo requests per ping command (-c flag).
# Type: integer. Default: 3.
PING_COUNT=3

# Timeout in seconds for each ping attempt (-W flag).
# Type: integer. Default: 2.
PING_TIMEOUT=2

# --- Database ---

# SQLAlchemy database connection URI.
# Default uses SQLite (file-based, no server needed).
# To switch to PostgreSQL, change to: postgresql://user:pass@host:5432/dbname
# Type: string. Default: sqlite:///mw_monitor.db
DATABASE_URL=sqlite:///mw_monitor.db

# --- Flask Application ---

# Secret key used for session signing and Fernet password encryption.
# Generate a strong random value for production. At least 32 characters.
# Type: string. Required.
SECRET_KEY=change-this-to-a-random-secret-key

# --- Logging ---

# Python logging level. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL.
# Type: string. Default: INFO.
LOG_LEVEL=INFO
```

---

## How `app/config.py` Reads from `.env`

The `Config` class uses `python-dotenv` to load environment variables from the `.env` file at the project root. The `load_dotenv()` function is called at module import time, before the Config class attributes are resolved.

Each config attribute reads from `os.environ.get()` with a fallback default value. Integer values are cast with `int()`. The `Config` class is passed to `app.config.from_object()` inside `create_app()`.

**Key design decisions:**

- **`python-dotenv` over `os.environ` alone** — `python-dotenv` loads the `.env` file automatically, so developers do not need to export variables manually in their shell. This reduces setup friction.
- **Defaults for every variable** — Every variable has a sensible default so the app can start with just `python run.py` during development (using SQLite, default ping settings). Only `JUMP_HOST`, `JUMP_USER`, and `JUMP_PASSWORD` truly require user input, and the app gracefully handles missing jump server config by skipping ping cycles.
- **No environment-specific config subclasses** — For v1, a single `Config` class is sufficient. `DevelopmentConfig` and `ProductionConfig` subclasses can be added later if needed.

---

## How Flask Accesses Config Values

Throughout the application, config values are accessed via `current_app.config['KEY']` inside request handlers, or via `app.config['KEY']` in the app factory and services.

Examples:
- `current_app.config['PING_INTERVAL_SECONDS']` — used by the scheduler to set the job interval.
- `current_app.config['SECRET_KEY']` — used by the jump server service to derive the Fernet encryption key.
- `current_app.config['SQLALCHEMY_DATABASE_URI']` — used by Flask-SQLAlchemy to connect to the database.

---

## Switching from SQLite to PostgreSQL

To switch to PostgreSQL in production:

1. Install the `psycopg2-binary` package (add to `requirements.txt`).
2. Change one line in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@db-host:5432/mw_monitor
   ```
3. Restart the application. `db.create_all()` will create tables in the PostgreSQL database.

No code changes are required. SQLAlchemy abstracts the database engine. The same models, queries, and relationships work identically on both SQLite and PostgreSQL.

**Caveat:** SQLite-specific behaviors (e.g., lack of native `BOOLEAN` type, no concurrent write support) are not relied upon in the codebase. All queries use standard SQL constructs that are portable.

---

## Environment Variable Validation

On application start, `create_app()` performs basic validation:

- If `SECRET_KEY` is still the default placeholder value (`change-this-to-a-random-secret-key`), log a warning: "Using default SECRET_KEY — change this for production."
- If `DATABASE_URL` is not set, default to `sqlite:///mw_monitor.db` silently.
- If `PING_INTERVAL_SECONDS` is less than 10, clamp to 10 and log a warning — to prevent overloading the jump server.
- If `JUMP_HOST` is not set, log a warning: "No jump server configured in .env. Ping cycles will be skipped until configured via the Settings API."

---

## Open Questions

1. **Fernet key derivation** — The plan uses Flask `SECRET_KEY` as the base for Fernet encryption. Should we use the raw `SECRET_KEY` padded/hashed to 32 bytes (as Fernet requires a URL-safe base64-encoded 32-byte key), or should we add a separate `ENCRYPTION_KEY` env var? Recommendation: derive via `hashlib.sha256(SECRET_KEY.encode()).digest()` then base64-encode.
2. **`.env` in version control** — `.env.example` is committed; `.env` is added to `.gitignore`. Should this be documented in the README? Yes.
3. **Docker env** — If containerized later, should we support reading from Docker secrets or environment variables directly (without `.env` file)? `python-dotenv` gracefully falls back to real environment variables if no `.env` file exists, so no code change is needed.
