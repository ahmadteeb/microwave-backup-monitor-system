from apscheduler.schedulers.background import BackgroundScheduler
import threading
import logging
from app.services.ping_service import run_ping_cycle
from app.extensions import db
from app.models import AppSettings

logger = logging.getLogger(__name__)

_ping_lock = threading.Lock()
_scheduler_instance = None
_app_instance = None

def ping_job():
    global _app_instance
    # Use a more robust locking mechanism
    if not _ping_lock.acquire(blocking=False):
        return
    
    try:
        logger.info("Starting scheduled ping cycle")
        if not _app_instance:
            logger.error("No app instance available for ping job")
            return

        with _app_instance.app_context():
            run_ping_cycle()
            logger.info("Completed scheduled ping cycle")
    except Exception as e:
        logger.error(f"Error in scheduled ping cycle: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        _ping_lock.release()

def init_scheduler(app):
    global _scheduler_instance, _app_instance
    
    # Store the app instance globally
    _app_instance = app
    
    # Return existing scheduler if already initialized
    if _scheduler_instance and _scheduler_instance.running:
        logger.info("Scheduler already running, returning existing instance")
        return _scheduler_instance
    
    scheduler = BackgroundScheduler()
    with app.app_context():
        settings = db.session.get(AppSettings, 1)
        interval = settings.ping_interval_seconds if settings else app.config.get('PING_INTERVAL_SECONDS', 60)
    
    scheduler.add_job(
        func=ping_job,
        trigger='interval',
        seconds=interval,
        id='ping_cycle',
        max_instances=1,
        misfire_grace_time=interval * 2,
        coalesce=True,
        replace_existing=True
    )
    
    scheduler.start()
    _scheduler_instance = scheduler
    logger.info(f"Scheduler started with {interval}s interval")
    return scheduler
