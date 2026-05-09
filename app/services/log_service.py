from datetime import datetime
from app.extensions import db
from app.models import SystemLog
import logging

logger = logging.getLogger(__name__)


import json

def write_log(category, event, actor, target=None, detail=None, ip_address=None):
    try:
        if isinstance(detail, (dict, list)):
            detail = json.dumps(detail)

        log_entry = SystemLog(
            timestamp=datetime.utcnow(),
            category=category,
            event=event,
            actor=actor,
            target=target,
            detail=detail,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception(f"Failed to write system log: {exc}")
