import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage
import logging
from flask import render_template
from app.models import db, User, NotificationSubscription, InAppNotification, SmtpConfig, Link
from app.services.crypto_service import decrypt
from app.services.log_service import write_log

logger = logging.getLogger(__name__)

EVENT_SEVERITY = {
    'mw_link_down': 'critical',
    'mw_link_recovered': 'info',
    'leg_util_high': 'warning',
    'leg_util_near_cap': 'critical',
    'mw_util_high': 'warning',
    'consecutive_timeouts': 'critical',
    'ping_service_error': 'error'
}


def _send_email_notification(user_email, subject, body, smtp_config, html_body=None):
    if not smtp_config:
        return

    password = smtp_config.get('password')
    if not password and smtp_config.get('password_encrypted'):
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
            if smtp_config.get('use_tls') and not smtp_config.get('use_ssl'):
                server.starttls()
                server.ehlo()
        if smtp_config.get('username') and password:
            server.login(smtp_config['username'], password)
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_config['from_address']
        msg['To'] = user_email
        msg.set_content(body)
        if html_body:
            msg.add_alternative(html_body, subtype='html')
        server.send_message(msg)
        server.quit()
    except Exception as exc:
        logger.error(f"Email send failed to {user_email}: {exc}")


def _deliver_emails(payloads_or_emails, subject, body, smtp_config, html_body=None):
    for item in payloads_or_emails:
        if isinstance(item, dict):
            email = item.get('email')
            user_html = item.get('html_body') or html_body
            if email:
                _send_email_notification(email, subject, body, smtp_config, html_body=user_html)
        else:
            if item:
                _send_email_notification(item, subject, body, smtp_config, html_body=html_body)


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
    subscriptions = NotificationSubscription.query.filter_by(event_key=event_key).all()
    sub_dict = {sub.user_id: sub.is_subscribed for sub in subscriptions}
    
    users = User.query.filter(User.is_active.is_(True)).all()
    user_ids = [u.id for u in users if sub_dict.get(u.id, True)]
    
    if not user_ids:
        return 0

    users = [u for u in users if u.id in user_ids]
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
            link = None
            if link_id:
                link = Link.query.filter_by(link_id=link_id).first()

            emoji_map = {
                'critical': '🔴',
                'error': '⚠️',
                'warning': '🟡',
                'info': '🔵'
            }
            if 'recovered' in event_key.lower() or 'up' in event_key.lower():
                emoji_map['info'] = '🟢'

            subject_emoji = emoji_map.get(severity, '🔵')
            sev_str = severity.upper()
            title_str = event_key.replace('_', ' ').title()

            if link:
                leg_name = getattr(link, 'leg_name', None) or link.link_id
                subject = f"{subject_emoji} [{sev_str}] {title_str} — {leg_name}"
            else:
                subject = f"{subject_emoji} [{sev_str}] {title_str}"

            body = message

            email_payloads = []
            from flask import current_app
            app = current_app._get_current_object()
            with app.app_context():
                for user in users:
                    user_name = getattr(user, 'full_name', None) or getattr(user, 'username', None) or user.email
                    html_body = None
                    if link:
                        html_body = render_template(
                            'emails/link_event.html',
                            event_type=event_key.split('_')[-1].upper(),
                            message=message,
                            link=link,
                            timestamp=now.strftime('%Y-%m-%d %H:%M:%S'),
                            user_name=user_name,
                            mw_capacity=getattr(link, 'mw_capacity', None),
                            mw_util_pct=getattr(link, 'mw_util_pct', None),
                            leg_util_pct=getattr(link, 'leg_util_pct', None)
                        )
                    email_payloads.append({
                        'email': user.email,
                        'html_body': html_body
                    })

            # Load SMTP config for email delivery
            smtp_record = SmtpConfig.query.first()
            smtp_config = None
            if smtp_record:
                decrypted_pass = None
                if smtp_record.password_encrypted:
                    try:
                        decrypted_pass = decrypt(smtp_record.password_encrypted)
                    except Exception as e:
                        logger.error(f"Failed to decrypt SMTP password: {e}")
                        
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
            if smtp_config:
                thread = threading.Thread(target=_deliver_emails, args=(email_payloads, subject, body, smtp_config, None), daemon=True)
                thread.start()
        return len(notifications)
    except Exception as exc:
        db.session.rollback()
        logger.exception(f"Failed to create notifications for event {event_key}: {exc}")
        write_log('notifications', 'notification_failed', 'system', event_key, {'error': str(exc)})
        return 0
