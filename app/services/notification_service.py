from datetime import datetime
import logging
from app.models import db, User, NotificationSubscription, InAppNotification
from app.services.log_service import write_log

logger = logging.getLogger(__name__)

EVENT_SEVERITY = {
    'mw_link_down': 'critical',
    'mw_link_recovered': 'info',
    'fiber_util_high': 'warning',
    'fiber_util_near_cap': 'critical',
    'mw_util_high': 'warning',
    'consecutive_timeouts': 'critical',
    'ping_service_error': 'error'
}


def send_event_notification(event_key, message, link_id=None, severity=None):
    severity = severity or EVENT_SEVERITY.get(event_key, 'info')
    subscriptions = NotificationSubscription.query.filter_by(
        event_key=event_key,
        is_subscribed=True
    ).all()
    if not subscriptions:
        return 0

    user_ids = [sub.user_id for sub in subscriptions]
    users = User.query.filter(User.id.in_(user_ids), User.is_active.is_(True)).all()
    notifications = []

    for user in users:
        notifications.append(InAppNotification(
            user_id=user.id,
            event_key=event_key,
            severity=severity,
            link_id=link_id,
            message=message,
            created_at=datetime.utcnow()
        ))

    try:
        db.session.bulk_save_objects(notifications)
        db.session.commit()
        return len(notifications)
    except Exception as exc:
        db.session.rollback()
        logger.exception(f"Failed to create notifications for event {event_key}: {exc}")
        write_log('notifications', 'notification_failed', 'system', event_key, {'error': str(exc)})
        return 0
