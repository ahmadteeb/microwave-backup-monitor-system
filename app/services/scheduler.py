from apscheduler.schedulers.background import BackgroundScheduler
import threading
import logging
from app.services.ping_service import run_ping_cycle, set_app_instance
from app.services.external_util_service import refresh_external_utilization
from app.extensions import db
from app.models import AppSettings, Link, LinkEventLog, User, SmtpConfig, NotificationSubscription
from app.services.notification_service import _deliver_emails
from flask import render_template
from datetime import datetime, timedelta

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

def external_util_job():
    global _app_instance
    if not _app_instance:
        logger.error('No app instance available for external utilization job')
        return

    with _app_instance.app_context():
        try:
            refresh_external_utilization()
        except Exception as exc:
            logger.error(f'Error refreshing external utilization: {exc}')

def daily_report_job():
    global _app_instance
    if not _app_instance:
        logger.error('No app instance available for daily report job')
        return

    with _app_instance.app_context():
        try:
            logger.info("Starting daily report job")
            links = Link.query.filter_by(is_active=True).all()
            
            # Fetch events from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            events = LinkEventLog.query.filter(LinkEventLog.timestamp >= yesterday).order_by(LinkEventLog.timestamp.desc()).all()
            
            # Format link data
            formatted_links = []
            for link in links:
                status = 'UNKNOWN'
                if link.status:
                    status = link.status.mw_status.upper()
                
                formatted_links.append({
                    'link_id': link.link_id,
                    'leg_name': link.leg_name,
                    'status': status,
                    'mw_util_pct': link.status.mw_util_pct if link.status else None,
                    'leg_util_pct': link.status.leg_util_pct if link.status else None,
                    'latency_ms': link.status.last_ping_latency_ms if link.status else None
                })
            
            html_body = render_template(
                'emails/daily_report.html',
                date=datetime.utcnow().strftime('%Y-%m-%d'),
                links=formatted_links,
                events=events
            )
            
            # Get users subscribed to report or just all active users
            users = User.query.filter(User.is_active.is_(True)).all()
            user_emails = [u.email for u in users if u.email]
            
            if user_emails:
                smtp_record = SmtpConfig.query.first()
                if smtp_record:
                    from app.services.crypto_service import decrypt
                    decrypted_pass = None
                    if smtp_record.password_encrypted:
                        try:
                            decrypted_pass = decrypt(smtp_record.password_encrypted)
                        except Exception as e:
                            pass
                    
                    smtp_config = {
                        'host': smtp_record.host,
                        'port': smtp_record.port,
                        'username': smtp_record.username,
                        'password': decrypted_pass,
                        'password_encrypted': smtp_record.password_encrypted,
                        'from_address': smtp_record.from_address,
                        'use_tls': smtp_record.use_tls,
                        'use_ssl': getattr(smtp_record, 'use_ssl', False),
                    }
                    _deliver_emails(user_emails, "[MW Monitor] Daily Report", "Please view this email in an HTML client.", smtp_config, html_body=html_body)
                    logger.info("Daily report sent successfully")
                else:
                    logger.warning("SMTP not configured, skipping daily report")
        except Exception as exc:
            logger.error(f'Error sending daily report: {exc}')


def reload_scheduler_interval():
    """
    Live-reload the ping cycle interval from AppSettings (Tier 2.2).
    
    Reschedules the APScheduler job without restarting the scheduler.
    Called from the settings route after saving AppSettings.
    """
    global _scheduler_instance, _app_instance
    if not _scheduler_instance or not _scheduler_instance.running:
        logger.warning("Cannot reload scheduler interval: scheduler not running")
        return

    try:
        if _app_instance:
            with _app_instance.app_context():
                settings = db.session.get(AppSettings, 1)
                new_interval = settings.ping_interval_seconds if settings else 60
        else:
            new_interval = 60

        _scheduler_instance.reschedule_job(
            'ping_cycle',
            trigger='interval',
            seconds=new_interval
        )
        logger.info(f"Ping cycle interval rescheduled to {new_interval}s")
    except Exception as exc:
        logger.error(f"Failed to reschedule ping cycle: {exc}")


def reload_daily_report_time():
    """
    Live-reload the daily report schedule from AppSettings (Tier 2.2).
    
    Reschedules the daily_report cron job without restarting the scheduler.
    Called from the settings route after saving AppSettings.
    """
    global _scheduler_instance, _app_instance
    if not _scheduler_instance or not _scheduler_instance.running:
        logger.warning("Cannot reload daily report time: scheduler not running")
        return

    try:
        if _app_instance:
            with _app_instance.app_context():
                settings = db.session.get(AppSettings, 1)
                hour = settings.daily_report_hour if settings else 8
                minute = settings.daily_report_minute if settings else 0
        else:
            hour, minute = 8, 0

        _scheduler_instance.reschedule_job(
            'daily_report',
            trigger='cron',
            hour=hour,
            minute=minute
        )
        logger.info(f"Daily report rescheduled to {hour:02d}:{minute:02d}")
    except Exception as exc:
        logger.error(f"Failed to reschedule daily report: {exc}")


def init_scheduler(app):
    global _scheduler_instance, _app_instance
    
    # Store the app instance globally
    _app_instance = app
    set_app_instance(app)
    
    # Return existing scheduler if already initialized
    if _scheduler_instance and _scheduler_instance.running:
        logger.info("Scheduler already running, returning existing instance")
        return _scheduler_instance
    
    scheduler = BackgroundScheduler()
    with app.app_context():
        settings = db.session.get(AppSettings, 1)
        interval = settings.ping_interval_seconds if settings else app.config.get('PING_INTERVAL_SECONDS', 60)
        report_hour = settings.daily_report_hour if settings else 8
        report_minute = settings.daily_report_minute if settings else 0
    
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
    
    scheduler.add_job(
        func=external_util_job,
        trigger='interval',
        days=1,
        id='external_util_refresh',
        max_instances=1,
        misfire_grace_time=3600,
        coalesce=True,
        replace_existing=True
    )
    
    scheduler.add_job(
        func=daily_report_job,
        trigger='cron',
        hour=report_hour,
        minute=report_minute,
        id='daily_report',
        max_instances=1,
        misfire_grace_time=3600,
        coalesce=True,
        replace_existing=True
    )

    scheduler.start()
    _scheduler_instance = scheduler
    logger.info(f"Scheduler started with {interval}s ping interval, daily report at {report_hour:02d}:{report_minute:02d}")
    return scheduler
