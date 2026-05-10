import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage
import logging
from app.models import db, User, NotificationSubscription, InAppNotification, SmtpConfig
from app.services.crypto_service import decrypt
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


def _send_email_notification(user_email, subject, body, smtp_config):
    if not smtp_config:
        return

    password = None
    if smtp_config.get('password_encrypted'):
        try:
            password = decrypt(smtp_config['password_encrypted'])
        except Exception as exc:
            logger.error(f"Unable to decrypt SMTP password: {exc}")
            return

    try:
        if smtp_config.get('use_ssl'):
            server = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'], timeout=10)
        else:
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'], timeout=10)
            server.ehlo()
            if smtp_config.get('use_tls'):
                server.starttls()
                server.ehlo()
        if smtp_config.get('username') and password:
            server.login(smtp_config['username'], password)
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_config['from_address']
        msg['To'] = user_email
        msg.set_content(body)
        server.send_message(msg)
        server.quit()
    except Exception as exc:
        logger.error(f"Email send failed to {user_email}: {exc}")


def _deliver_emails(user_emails, subject, body, smtp_config):
    for email in user_emails:
        if email:
            _send_email_notification(email, subject, body, smtp_config)


def _emit_notification_ws(user_id, notification_data):
    """Emit a real-time WebSocket event for a new notification."""
    try:
        from app.extensions import socketio
        # Emit unread count + notification payload to all connected clients
        # (Frontend will filter by its own user context)
        unread_count = InAppNotification.query.filter_by(user_id=user_id, is_read=False).count()
        socketio.emit('notification_new', {
            'notification': notification_data,
            'unread_count': unread_count
        })
    except Exception as e:
        logger.warning(f"Failed to emit notification_new: {e}")


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
    user_emails = []

    now = datetime.utcnow()
    for user in users:
        notifications.append(InAppNotification(
            user_id=user.id,
            event_key=event_key,
            severity=severity,
            link_id=link_id,
            message=message,
            created_at=now
        ))
        user_emails.append(user.email)

    try:
        db.session.bulk_save_objects(notifications)
        db.session.commit()

        # Emit WebSocket events for each user
        for user in users:
            _emit_notification_ws(user.id, {
                'event_key': event_key,
                'severity': severity,
                'link_id': link_id,
                'message': message,
                'is_read': False,
                'created_at': now.isoformat() + 'Z'
            })

        if user_emails:
            subject = f"[MW Monitor] {event_key.replace('_', ' ').title()}"
            body = message
            # Load SMTP config for email delivery
            smtp_record = SmtpConfig.query.first()
            smtp_config = None
            if smtp_record and smtp_record.enabled:
                smtp_config = {
                    'host': smtp_record.host,
                    'port': smtp_record.port,
                    'username': smtp_record.username,
                    'password_encrypted': smtp_record.password_encrypted,
                    'from_address': smtp_record.from_email,
                    'use_tls': smtp_record.use_tls,
                    'use_ssl': getattr(smtp_record, 'use_ssl', False),
                }
            if smtp_config:
                thread = threading.Thread(target=_deliver_emails, args=(user_emails, subject, body, smtp_config), daemon=True)
                thread.start()
        return len(notifications)
    except Exception as exc:
        db.session.rollback()
        logger.exception(f"Failed to create notifications for event {event_key}: {exc}")
        write_log('notifications', 'notification_failed', 'system', event_key, {'error': str(exc)})
        return 0
