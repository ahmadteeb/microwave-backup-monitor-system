from apscheduler.schedulers.background import BackgroundScheduler
import threading
import logging
from app.services.ping_service import run_ping_cycle
from app.models import AppSettings

logger = logging.getLogger(__name__)

_ping_lock = threading.Lock()

def ping_job(app):
    with app.app_context():
        if not _ping_lock.acquire(blocking=False):
            logger.warning("Previous ping cycle still running. Skipping this trigger.")
            return
        
        try:
            run_ping_cycle()
        finally:
            _ping_lock.release()

def init_scheduler(app):
    scheduler = BackgroundScheduler()
    with app.app_context():
        settings = AppSettings.query.get(1)
        interval = settings.ping_interval_seconds if settings else app.config.get('PING_INTERVAL_SECONDS', 60)
    
    scheduler.add_job(
        func=ping_job,
        trigger='interval',
        args=[app],
        seconds=interval,
        id='ping_cycle',
        max_instances=1,
        misfire_grace_time=30,
        coalesce=True
    )
    
    scheduler.start()
    return scheduler
