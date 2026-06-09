"""
Health and Readiness endpoints (Tier 3.1).

GET /health — always 200, used by load balancers. No auth required.
GET /ready  — 200 if the app can serve traffic, 503 if not. Checks DB and scheduler.
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify
from sqlalchemy import text

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


def _get_uptime_seconds():
    """Calculate uptime from the module-level APP_START_TIME set in __init__.py."""
    try:
        from app import APP_START_TIME
        return int((datetime.utcnow() - APP_START_TIME).total_seconds())
    except Exception:
        return 0


@health_bp.route('/health', methods=['GET'])
def health():
    """Liveness probe — always returns 200."""
    return jsonify({
        'status': 'ok',
        'uptime_seconds': _get_uptime_seconds()
    }), 200


@health_bp.route('/ready', methods=['GET'])
def ready():
    """
    Readiness probe — returns 200 if the app can serve traffic, 503 if not.
    
    Checks:
    1. Database reachable (SELECT 1)
    2. Scheduler running
    """
    checks = {}
    all_ok = True

    # Check 1: Database
    try:
        from app.extensions import db
        db.session.execute(text('SELECT 1'))
        checks['database'] = 'ok'
    except Exception as exc:
        checks['database'] = f'error: {exc}'
        all_ok = False
        logger.error(f"Readiness check failed — database: {exc}")

    # Check 2: Scheduler
    try:
        from app.services.scheduler import _scheduler_instance
        if _scheduler_instance and _scheduler_instance.running:
            checks['scheduler'] = 'ok'
        else:
            checks['scheduler'] = 'stopped'
            all_ok = False
    except Exception as exc:
        checks['scheduler'] = f'error: {exc}'
        all_ok = False

    status_str = 'ready' if all_ok else 'not_ready'
    status_code = 200 if all_ok else 503

    return jsonify({
        'status': status_str,
        'checks': checks
    }), status_code
