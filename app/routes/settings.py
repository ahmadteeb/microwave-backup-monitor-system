import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Blueprint, request, jsonify, session, current_app
from app.models import db, SmtpConfig, JumpServer, AppSettings, User, ExternalDbConfig, WebhookConfig
from urllib.parse import quote_plus
from app.services.crypto_service import encrypt, decrypt, encrypt_with_key, decrypt_with_key
from app.services.ssh_service import SSHService
from app.services.log_service import write_log
from app.services.external_util_service import invalidate_external_engine, test_external_connection, get_external_db_status
from app.permissions import login_required, require_permission

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


def _current_user():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None


def _mask_password(value):
    return '••••••••' if value else ''


def _build_smtp_response(config):
    if not config:
        return {'enabled': False}
    return {
        'enabled': True,
        'host': config.host,
        'port': config.port,
        'username': config.username,
        'password': _mask_password(config.password_encrypted),
        'from_address': config.from_address,
        'from_email': config.from_address,
        'use_tls': config.use_tls,
        'use_ssl': config.use_ssl
    }


def _build_jump_response(js):
    if not js:
        return None
    return {
        'id': js.id,
        'host': js.host,
        'port': js.port,
        'username': js.username,
        'password': _mask_password(js.password_encrypted),
        'active': js.active,
        'label': js.label
    }


def _get_secrets_path():
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    secrets_path = os.path.join(app_root, 'data', 'secrets', 'secrets.json')
    if os.path.exists(secrets_path):
        return secrets_path
    legacy_path = os.path.join(app_root, 'secrets', 'secrets.json')
    return legacy_path


def _load_encrypted_secrets():
    path = _get_secrets_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _load_secret_payload():
    secrets_data = _load_encrypted_secrets()
    if not secrets_data:
        return {}
    encrypted_data = secrets_data.get('db_config_encrypted')
    if not encrypted_data:
        return {}
    try:
        decrypted_json = decrypt_with_key(encrypted_data, current_app.config['SECRET_KEY'])
        return json.loads(decrypted_json)
    except Exception:
        return {}


def _save_secret_payload(payload):
    path = _get_secrets_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    encrypted_data = encrypt_with_key(json.dumps(payload, indent=2), current_app.config['SECRET_KEY'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'secret_key': current_app.config['SECRET_KEY'],
            'db_config_encrypted': encrypted_data
        }, f, indent=2)


@settings_bp.route('/smtp', methods=['GET'])
@login_required
@require_permission('config.view')
def get_smtp():
    config = db.session.get(SmtpConfig, 1)
    if not config:
        return jsonify({'smtp': None}), 200
    return jsonify({'smtp': _build_smtp_response(config)}), 200


@settings_bp.route('/smtp', methods=['PUT'])
@login_required
@require_permission('config.edit_smtp')
def update_smtp():
    data = request.get_json() or {}
    config = db.session.get(SmtpConfig, 1)
    enabled = bool(data.get('enabled', True))

    if not enabled:
        if config:
            db.session.delete(config)
            db.session.commit()
            write_log('config', 'smtp_disabled', session.get('username', 'system'), 'smtp', {})
        return jsonify({'result': 'smtp disabled'}), 200

    if not config:
        config = SmtpConfig(id=1)
        db.session.add(config)

    changed = {}
    if 'host' in data and data['host'] != config.host:
        changed['host'] = [config.host, data['host']]
        config.host = data['host']
    if 'port' in data and data['port'] != config.port:
        changed['port'] = [config.port, int(data['port'])]
        config.port = int(data['port'])
    if 'username' in data and data['username'] != config.username:
        changed['username'] = [config.username, data['username']]
        config.username = data['username']
    from_address = data.get('from_address') or data.get('from_email')
    if from_address is not None and from_address != config.from_address:
        changed['from_address'] = [config.from_address, from_address]
        config.from_address = from_address
    if 'use_tls' in data and data['use_tls'] != config.use_tls:
        changed['use_tls'] = [config.use_tls, data['use_tls']]
        config.use_tls = bool(data['use_tls'])
    if 'use_ssl' in data and data['use_ssl'] != config.use_ssl:
        changed['use_ssl'] = [config.use_ssl, data['use_ssl']]
        config.use_ssl = bool(data['use_ssl'])

    password = data.get('password')
    if password and password != '••••••••':
        config.password_encrypted = encrypt(password)
    if password == '••••••••' and not config.password_encrypted:
        config.password_encrypted = None

    config.updated_by_id = session.get('user_id')
    config.updated_at = datetime.utcnow()
    db.session.commit()
    write_log('config', 'smtp_updated', session.get('username', 'system'), 'smtp', {'changes': changed})
    return jsonify({'result': 'smtp updated'}), 200


@settings_bp.route('/smtp/test', methods=['POST'])
@login_required
@require_permission('config.edit_smtp')
def test_smtp():
    """Test SMTP connection using form data from request body (before save)."""
    data = request.get_json() or {}
    user = _current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    host = data.get('host') or data.get('server')
    port = int(data.get('port', 587))
    username = data.get('username')
    from_address = data.get('from_address') or data.get('from_email')
    use_tls = bool(data.get('use_tls', True))
    use_ssl = bool(data.get('use_ssl', False))

    if not host or not from_address:
        return jsonify({'error': 'SMTP host and from address are required'}), 400

    # Resolve password: use provided value, fall back to saved DB record if masked
    password = data.get('password')
    if not password or password == '••••••••':
        config = db.session.get(SmtpConfig, 1)
        if config and config.password_encrypted:
            try:
                password = decrypt(config.password_encrypted)
            except Exception as exc:
                return jsonify({'error': f'Unable to decrypt saved SMTP password: {exc}'}), 500
        else:
            password = None

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.ehlo()
                server.starttls()
                server.ehlo()
        if username and password:
            server.login(username, password)
        message = EmailMessage()
        message['Subject'] = 'MW Link Monitor Test Email'
        message['From'] = from_address
        message['To'] = user.email
        message.set_content('This is a test email from MW Link Monitor settings.')
        server.send_message(message)
        server.quit()
        return jsonify({'result': f'Test email sent to {user.email}'}), 200
    except Exception as exc:
        write_log('notifications', 'email_failed', 'system', user.email, {'event_key': 'test_smtp', 'error': str(exc)})
        return jsonify({'error': str(exc)}), 500


@settings_bp.route('/jumpserver', methods=['GET'])
@login_required
@require_permission('config.view')
def get_jumpserver():
    """Get the most recent jump server config (active or inactive)."""
    js = JumpServer.query.order_by(JumpServer.id.desc()).first()
    if not js:
        return jsonify({'jumpserver': None}), 200
    return jsonify({'jumpserver': _build_jump_response(js)}), 200


@settings_bp.route('/jumpserver', methods=['PUT'])
@login_required
@require_permission('config.edit_jumpserver')
def update_jumpserver():
    """Update jump server config. Invalidates persistent SSH session on change."""
    data = request.get_json() or {}
    active = bool(data.get('active', True))
    active_js = db.session.query(JumpServer).filter_by(active=True).first()

    if not active:
        if active_js:
            active_js.active = False
            db.session.commit()
            write_log('config', 'jumpserver_disabled', session.get('username', 'system'), 'jumpserver', {})
            # Invalidate the persistent SSH session
            from app.services.ssh_session_manager import get_session_manager
            get_session_manager().invalidate()
        return jsonify({'jumpserver': _build_jump_response(active_js) if active_js else None}), 200

    if not data.get('host') or not data.get('username'):
        return jsonify({'error': 'Missing required fields'}), 400

    changed = {}
    if active_js:
        active_js.active = False
        db.session.commit()

    password = data.get('password')
    if password and password != '••••••••':
        encrypted_password = encrypt(password)
    elif active_js:
        encrypted_password = active_js.password_encrypted
    else:
        encrypted_password = None

    js = JumpServer(
        host=data['host'],
        port=int(data.get('port', 22)),
        username=data['username'],
        password_encrypted=encrypted_password,
        active=True,
        label=data.get('label'),
        updated_by_id=session.get('user_id')
    )
    db.session.add(js)
    db.session.commit()
    write_log('config', 'jumpserver_updated', session.get('username', 'system'), 'jumpserver', {'changed': list(data.keys())})
    
    # Invalidate the persistent SSH session to force reconnect with new config
    from app.services.ssh_session_manager import get_session_manager
    get_session_manager().invalidate()
    
    return jsonify({'jumpserver': _build_jump_response(js)}), 200


@settings_bp.route('/jumpserver/test', methods=['POST'])
@login_required
@require_permission('config.edit_jumpserver')
def test_jumpserver():
    """Test jump server SSH connection using form data from request body (before save)."""
    data = request.get_json() or {}

    host = data.get('host')
    port = int(data.get('port', 22))
    username = data.get('username')

    if not host or not username:
        return jsonify({'error': 'Host and username are required'}), 400

    # Resolve password: use provided value, fall back to saved DB record if masked
    password = data.get('password')
    if not password or password == '••••••••':
        js = JumpServer.query.filter_by(active=True).first()
        if js and js.password_encrypted:
            try:
                password = decrypt(js.password_encrypted)
            except Exception as exc:
                return jsonify({'error': f'Unable to decrypt saved jump server password: {exc}'}), 500
        else:
            return jsonify({'error': 'Password is required'}), 400

    try:
        ssh = SSHService(host, username, password, port)
        ssh.connect()
        ssh.disconnect()
        return jsonify({'result': 'connection successful'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@settings_bp.route('/external-db', methods=['GET'])
@login_required
@require_permission('config.view')
def get_external_db_settings():
    ext_config = ExternalDbConfig.query.filter_by(active=True).first()
    enabled = ext_config is not None
    return jsonify({'external_db': {
        'enabled': enabled,
        'host': ext_config.host if ext_config else '',
        'port': ext_config.port if ext_config else 3306,
        'username': ext_config.username if ext_config else '',
        'password': _mask_password(ext_config.password_encrypted) if ext_config else '',
        'database': ext_config.database if ext_config else ''
    }}), 200


@settings_bp.route('/external-db', methods=['PUT'])
@login_required
@require_permission('config.edit_app')
def update_external_db_settings():
    data = request.get_json() or {}
    enabled = bool(data.get('enabled', False))
    ext_config = ExternalDbConfig.query.filter_by(active=True).first()

    if not enabled:
        if ext_config:
            ext_config.active = False
            db.session.commit()
            invalidate_external_engine()
        write_log('config', 'external_db_settings_updated', session.get('username', 'system'), 'external_db_settings', {'enabled': False})
        return jsonify({'result': 'external db disabled'}), 200

    if not data.get('host') or not data.get('port') or not data.get('username') or not data.get('database'):
        return jsonify({'error': 'host, port, username, and database are required'}), 400

    if ext_config:
        ext_config.active = False
        db.session.commit()

    password = data.get('password')
    if password and password != '••••••••':
        encrypted_password = encrypt(password)
    elif ext_config:
        encrypted_password = ext_config.password_encrypted
    else:
        encrypted_password = None

    new_config = ExternalDbConfig(
        host=data['host'],
        port=int(data['port']),
        username=data['username'],
        password_encrypted=encrypted_password,
        database=data['database'],
        active=True,
        updated_by_id=session.get('user_id')
    )
    db.session.add(new_config)
    db.session.commit()
    
    invalidate_external_engine()
    
    write_log('config', 'external_db_settings_updated', session.get('username', 'system'), 'external_db_settings', {'enabled': True})
    return jsonify({'result': 'external db settings updated'}), 200


@settings_bp.route('/external-db/test', methods=['POST'])
@login_required
@require_permission('config.edit_app')
def test_external_db_settings():
    data = request.get_json() or {}
    if not data.get('host') or not data.get('port') or not data.get('username') or not data.get('database'):
        return jsonify({'error': 'Missing external DB host, port, username, or database.'}), 400
        
    password = data.get('password')
    if not password or password == '••••••••':
        ext_config = ExternalDbConfig.query.filter_by(active=True).first()
        if ext_config and ext_config.password_encrypted:
            try:
                password = decrypt(ext_config.password_encrypted)
            except Exception as exc:
                return jsonify({'error': f'Unable to decrypt saved external DB password: {exc}'}), 500
        else:
            password = None
            
    try:
        import sqlalchemy
        from sqlalchemy.engine import URL
        driver = 'mysql+pymysql'
        username = data['username'].strip() or None
        password = password.strip() if password else None
        host = data['host'].strip()
        port = int(data['port'])
        database = data['database'].strip()
        external_db_url = URL.create(
            drivername=driver,
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
            query={'charset': 'utf8mb4'}
        )
        engine = sqlalchemy.create_engine(external_db_url, pool_pre_ping=True, connect_args={'charset': 'utf8mb4', 'use_unicode': True})
        conn = engine.connect()
        conn.close()
        return jsonify({'result': 'External DB connection successful'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@settings_bp.route('/external-db/status', methods=['GET'])
@login_required
@require_permission('config.view')
def external_db_status():
    """Return external DB connection status and last sync info (Tier 2.3)."""
    return jsonify(get_external_db_status()), 200


@settings_bp.route('/external-db/test-connection', methods=['POST'])
@login_required
@require_permission('config.view')
def test_external_db_connection():
    """Test connectivity to the active external DB config (Tier 2.3)."""
    result = test_external_connection()
    status_code = 200 if result['success'] else 503
    return jsonify(result), status_code


@settings_bp.route('/app', methods=['GET'])
@login_required
@require_permission('config.view')
def get_app_settings():
    settings = db.session.get(AppSettings, 1)
    if not settings:
        return jsonify({'app': None}), 200
    return jsonify({'app': {
        'session_timeout_minutes': settings.session_timeout_minutes,
        'ping_interval_seconds': settings.ping_interval_seconds,
        'ping_count': settings.ping_count,
        'ping_timeout_seconds': settings.ping_timeout_seconds,
        'ping_concurrency': settings.ping_concurrency,
        'consecutive_timeout_alert_threshold': settings.consecutive_timeout_alert_threshold,
        'util_warning_threshold_pct': settings.util_warning_threshold_pct,
        'util_critical_threshold_pct': settings.util_critical_threshold_pct,
        'daily_report_hour': settings.daily_report_hour,
        'daily_report_minute': settings.daily_report_minute,
    }}), 200


@settings_bp.route('/app', methods=['PUT'])
@login_required
@require_permission('config.edit_app')
def update_app_settings():
    data = request.get_json() or {}
    settings = db.session.get(AppSettings, 1)
    if not settings:
        settings = AppSettings(id=1)
        db.session.add(settings)

    changed = {}
    for field in [
        'session_timeout_minutes', 'ping_interval_seconds', 'ping_count',
        'ping_timeout_seconds', 'ping_concurrency', 'consecutive_timeout_alert_threshold',
        'util_warning_threshold_pct', 'util_critical_threshold_pct',
        'daily_report_hour', 'daily_report_minute',
    ]:
        if field in data:
            value = data[field]
            old_value = getattr(settings, field)
            if old_value != value:
                changed[field] = [old_value, value]
                setattr(settings, field, value)

    settings.updated_by_id = session.get('user_id')
    settings.updated_at = datetime.utcnow()
    db.session.commit()

    # Audit log with before/after values (Tier 2.4)
    write_log('config', 'settings_updated', session.get('username', 'system'), 'app_settings',
              {'changes': changed}, ip_address=request.remote_addr)

    # Live-reload scheduler jobs if relevant settings changed (Tier 2.2)
    if 'ping_interval_seconds' in changed:
        try:
            from app.services.scheduler import reload_scheduler_interval
            reload_scheduler_interval()
        except Exception:
            write_log('config', 'scheduler_reschedule_failed', session.get('username', 'system'),
                      'app_settings', {'field': 'ping_interval_seconds'})

    if 'daily_report_hour' in changed or 'daily_report_minute' in changed:
        try:
            from app.services.scheduler import reload_daily_report_time
            reload_daily_report_time()
        except Exception:
            write_log('config', 'scheduler_reschedule_failed', session.get('username', 'system'),
                      'app_settings', {'field': 'daily_report_time'})

    return jsonify({'result': 'app settings updated'}), 200


# ─── Webhook / Slack notification channel endpoints (Tier 3.4) ───────────────

@settings_bp.route('/webhooks', methods=['GET'])
@login_required
@require_permission('config.edit_smtp')
def list_webhooks():
    """List all webhook configurations."""
    webhooks = WebhookConfig.query.order_by(WebhookConfig.id).all()
    return jsonify({'webhooks': [
        {
            'id': w.id,
            'label': w.label,
            'url': w.url,
            'channel_type': w.channel_type,
            'active': w.active,
            'created_at': w.created_at.isoformat() + 'Z'
        }
        for w in webhooks
    ]}), 200


@settings_bp.route('/webhooks', methods=['POST'])
@login_required
@require_permission('config.edit_smtp')
def create_webhook():
    """Create a new webhook configuration."""
    data = request.get_json() or {}
    label = (data.get('label') or '').strip()
    url = (data.get('url') or '').strip()
    channel_type = data.get('channel_type', 'generic')

    if not label or not url:
        return jsonify({'error': 'label and url are required'}), 400

    if channel_type not in ('generic', 'slack'):
        return jsonify({'error': 'channel_type must be "generic" or "slack"'}), 400

    webhook = WebhookConfig(
        label=label,
        url=url,
        channel_type=channel_type,
        active=bool(data.get('active', True)),
    )
    db.session.add(webhook)
    db.session.commit()

    write_log('config', 'webhook_created', session.get('username', 'system'), label,
              {'url': url, 'channel_type': channel_type}, ip_address=request.remote_addr)

    return jsonify({
        'id': webhook.id,
        'label': webhook.label,
        'url': webhook.url,
        'channel_type': webhook.channel_type,
        'active': webhook.active,
        'created_at': webhook.created_at.isoformat() + 'Z'
    }), 201


@settings_bp.route('/webhooks/<int:id>', methods=['DELETE'])
@login_required
@require_permission('config.edit_smtp')
def delete_webhook(id):
    """Delete a webhook configuration."""
    webhook = db.session.get(WebhookConfig, id)
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    label = webhook.label
    db.session.delete(webhook)
    db.session.commit()

    write_log('config', 'webhook_deleted', session.get('username', 'system'), label,
              {}, ip_address=request.remote_addr)

    return jsonify({'result': 'webhook deleted'}), 200
