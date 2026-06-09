import smtplib
import threading
from datetime import datetime, timedelta
from email.message import EmailMessage
import logging
from flask import render_template
from app.models import db, User, NotificationSubscription, InAppNotification, SmtpConfig, Link, LinkStatus, WebhookConfig
from app.services.crypto_service import decrypt
from app.services.log_service import write_log

logger = logging.getLogger(__name__)

EVENT_SEVERITY = {
    'mw_link_down': 'critical',
    'mw_link_flapping': 'critical',
    'mw_link_recovered': 'info',
    'leg_util_high': 'warning',
    'leg_util_near_cap': 'critical',
    'mw_util_high': 'warning',
    'consecutive_timeouts': 'critical',
    'ping_service_error': 'error'
}

# Notification cooldown in seconds per event type (Tier 1.2)
NOTIFICATION_COOLDOWN_SECONDS = {
    'mw_link_down': 1800,          # 30 min
    'mw_link_flapping': 1800,      # 30 min
    'consecutive_timeouts': 3600,  # 1 hour
    'leg_util_high': 3600,
    'leg_util_near_cap': 1800,
    'mw_util_high': 3600,
    'mw_link_recovered': 0,        # always fire recoveries
    'ping_service_error': 3600,
}

# Severity-aware email subject templates (Tier 1.2)
# Using uniform subjects for link events to ensure strict email client threading
SUBJECT_TEMPLATES = {
    'mw_link_down':        '[MW Monitor] Link Alert \u2014 {leg_name}',
    'mw_link_flapping':    '[MW Monitor] Link Alert \u2014 {leg_name}',
    'mw_link_recovered':   '[MW Monitor] Link Alert \u2014 {leg_name}',
    'leg_util_high':       '[MW Monitor] Link Alert \u2014 {leg_name}',
    'mw_util_high':        '[MW Monitor] Link Alert \u2014 {leg_name}',
    'leg_util_near_cap':   '[MW Monitor] Link Alert \u2014 {leg_name}',
    'consecutive_timeouts':'[MW Monitor] Link Alert \u2014 {leg_name}',
    'ping_service_error':  '[MW Monitor] System Alert \u2014 Ping Service Error',
}

# Maps event_key to the LinkStatus timestamp column used for cooldown tracking
_COOLDOWN_COLUMN_MAP = {
    'mw_link_down': 'last_mw_down_notified_at',
    'mw_link_flapping': 'last_mw_down_notified_at',
    'consecutive_timeouts': 'last_mw_down_notified_at',
    'leg_util_high': 'last_leg_high_notified_at',
    'mw_util_high': 'last_mw_high_notified_at',
    'leg_util_near_cap': 'last_leg_near_cap_notified_at',
}


def _check_and_update_cooldown(event_key, link_id):
    """
    Check whether enough time has elapsed since the last notification for this
    event on this link. If so, update the timestamp and return True (allow).
    Returns False if the notification should be suppressed (still in cooldown).
    
    Always returns True for link-less events or events without a cooldown column.
    """
    if link_id is None:
        return True

    cooldown = NOTIFICATION_COOLDOWN_SECONDS.get(event_key, 0)
    if cooldown == 0:
        return True

    column_name = _COOLDOWN_COLUMN_MAP.get(event_key)
    if column_name is None:
        return True

    try:
        link = Link.query.filter_by(link_id=link_id).first()
        if not link:
            return True

        status_record = LinkStatus.query.filter_by(link_id=link.id).first()
        if not status_record:
            return True

        last_notified = getattr(status_record, column_name, None)
        now = datetime.utcnow()

        if last_notified is not None:
            elapsed = (now - last_notified).total_seconds()
            if elapsed < cooldown:
                logger.debug(
                    f"Notification suppressed by cooldown: event={event_key}, "
                    f"link={link_id}, elapsed={elapsed:.0f}s, cooldown={cooldown}s"
                )
                return False

        # Update the cooldown timestamp
        setattr(status_record, column_name, now)
        db.session.commit()
        return True
    except Exception as exc:
        logger.error(f"Cooldown check failed for {event_key}/{link_id}: {exc}")
        db.session.rollback()
        return True  # fail-open: allow notification if cooldown check errors


def _send_email_notification(user_email, subject, body, smtp_config, html_body=None, thread_id=None):
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
        
        import uuid
        import hashlib
        import base64
        
        # Every email gets exactly one Message-ID header
        if thread_id and isinstance(thread_id, dict) and thread_id.get('msg_id'):
            msg['Message-ID'] = thread_id['msg_id']
        else:
            msg['Message-ID'] = f"<{uuid.uuid4().hex}@mwmonitor.local>"
            
        if thread_id and isinstance(thread_id, dict):
            if thread_id.get('in_reply_to'):
                msg['References'] = thread_id['in_reply_to']
                msg['In-Reply-To'] = thread_id['in_reply_to']
                
            thread_base = thread_id.get('thread_index_base')
            if thread_base:
                # Outlook strict threading headers
                msg['Thread-Topic'] = subject
                
                # Generate a consistent 22-byte Thread-Index based on the thread base (link_id)
                h = hashlib.md5(thread_base.encode('utf-8')).digest()
                # 1 byte header (0x01) + 5 bytes fake timestamp + 16 bytes hash = 22 bytes
                thread_index_bytes = b'\x01\x00\x00\x00\x00\x00' + h[:16]
                msg['Thread-Index'] = base64.b64encode(thread_index_bytes).decode('ascii')

        msg.set_content(body)
        if html_body:
            msg.add_alternative(html_body, subtype='html')
            
        logger.info(f"Sending Email -> To: {user_email} | Message-ID: {msg.get('Message-ID')} | In-Reply-To: {msg.get('In-Reply-To')} | Thread-Index: {msg.get('Thread-Index')} | Subject: {subject}")
            
        server.send_message(msg)
        server.quit()
    except Exception as exc:
        logger.error(f"Email send failed to {user_email}: {exc}")


def _deliver_emails(payloads_or_emails, subject, body, smtp_config, html_body=None, thread_id=None):
    for item in payloads_or_emails:
        if isinstance(item, dict):
            email = item.get('email')
            user_html = item.get('html_body') or html_body
            if email:
                _send_email_notification(email, subject, body, smtp_config, html_body=user_html, thread_id=thread_id)
        else:
            if item:
                _send_email_notification(item, subject, body, smtp_config, html_body=html_body, thread_id=thread_id)


def _deliver_webhooks(event_key, message, link, severity):
    """
    Deliver webhook notifications to all active WebhookConfig endpoints (Tier 3.4).
    Runs in a daemon thread. Never raises.
    """
    try:
        webhooks = WebhookConfig.query.filter_by(active=True).all()
    except Exception as exc:
        logger.error(f"Failed to query webhooks: {exc}")
        return

    if not webhooks:
        return

    leg_name = link.leg_name if link else event_key
    link_id_str = link.link_id if link else None
    timestamp_str = datetime.utcnow().isoformat() + 'Z'

    for webhook in webhooks:
        try:
            if webhook.channel_type == 'slack':
                # Slack-compatible payload
                color_map = {'critical': 'danger', 'error': 'danger', 'warning': 'warning', 'info': 'good'}
                color = color_map.get(severity, '#439FE0')
                fields = [
                    {'title': 'Event', 'value': event_key, 'short': True},
                    {'title': 'Severity', 'value': severity.upper(), 'short': True},
                ]
                if link:
                    fields.extend([
                        {'title': 'Link ID', 'value': link.link_id, 'short': True},
                        {'title': 'Leg', 'value': link.leg_name, 'short': True},
                        {'title': 'MW IP', 'value': link.mw_ip, 'short': True},
                    ])
                emoji_map = {'critical': '\U0001f534', 'error': '\u26a0\ufe0f', 'warning': '\U0001f7e1', 'info': '\U0001f7e2'}
                emoji = emoji_map.get(severity, '\U0001f535')
                title = event_key.replace('_', ' ').title()
                payload = {
                    'text': f"{emoji} *{title}* \u2014 {leg_name}",
                    'attachments': [{
                        'color': color,
                        'text': message,
                        'fields': fields,
                        'ts': timestamp_str
                    }]
                }
            else:
                # Generic webhook payload
                payload = {
                    'event': event_key,
                    'severity': severity,
                    'message': message,
                    'link_id': link_id_str,
                    'leg_name': leg_name,
                    'timestamp': timestamp_str
                }

            def _post_webhook(url, data):
                try:
                    import requests
                    requests.post(url, json=data, timeout=5)
                except Exception as post_exc:
                    logger.error(f"Webhook delivery failed to {url}: {post_exc}")

            thread = threading.Thread(target=_post_webhook, args=(webhook.url, payload), daemon=True)
            thread.start()
        except Exception as exc:
            logger.error(f"Failed to prepare webhook {webhook.label}: {exc}")


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

    # Always emit WebSocket notifications (not gated by cooldown)
    now = datetime.utcnow()
    for user in users:
        _emit_notification_ws(user.id, {
            'event_key': event_key,
            'severity': severity,
            'link_id': link_id,
            'message': message,
            'is_read': False,
            'created_at': now.isoformat() + 'Z'
        })

    # Check cooldown — if suppressed, skip email and DB notifications
    if not _check_and_update_cooldown(event_key, link_id):
        return 0

    notifications = []
    user_emails = []

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

        if user_emails:
            link = None
            if link_id:
                link = Link.query.filter_by(link_id=link_id).first()

            # Build severity-aware subject line from templates
            leg_name = link.leg_name if link else event_key
            subject = SUBJECT_TEMPLATES.get(
                event_key,
                '[MW Monitor] {leg_name}'
            ).format(leg_name=leg_name, event_key=event_key)

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
                import uuid
                
                thread_id_payload = {
                    'msg_id': f"<{uuid.uuid4().hex}@mwmonitor.local>",
                    'in_reply_to': None,
                    'thread_index_base': f"link-{link.link_id}" if link else None
                }
                
                if link:
                    try:
                        from app.models import LinkEventLog
                        events = LinkEventLog.query.filter_by(link_id=link.id).order_by(LinkEventLog.timestamp.desc()).limit(2).all()
                        if events:
                            # If the latest event was created within the last 15 seconds, it was just flushed
                            # by the current transaction, so this email represents that exact event.
                            now = datetime.utcnow()
                            # Use offset-naive comparison since events[0].timestamp is naive
                            if (now - events[0].timestamp).total_seconds() < 15:
                                thread_id_payload['msg_id'] = f"<event-{events[0].id}@mwmonitor.local>"
                                if len(events) > 1:
                                    thread_id_payload['in_reply_to'] = f"<event-{events[1].id}@mwmonitor.local>"
                            else:
                                # This is a secondary alert (like high util), it replies to the current active event
                                thread_id_payload['in_reply_to'] = f"<event-{events[0].id}@mwmonitor.local>"
                    except Exception as e:
                        logger.error(f"Failed to generate thread IDs: {e}")
                
                thread = threading.Thread(target=_deliver_emails, args=(email_payloads, subject, body, smtp_config, None, thread_id_payload), daemon=True)
                thread.start()

            # Deliver webhooks (Tier 3.4)
            _deliver_webhooks(event_key, message, link, severity)

        return len(notifications)
    except Exception as exc:
        db.session.rollback()
        logger.exception(f"Failed to create notifications for event {event_key}: {exc}")
        write_log('notifications', 'notification_failed', 'system', event_key, {'error': str(exc)})
        return 0
