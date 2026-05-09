import smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Blueprint, request, jsonify, session
from app.models import db, SmtpConfig, JumpServer, AppSettings, User
from app.services.crypto_service import encrypt, decrypt
from app.services.ssh_service import SSHService
from app.services.log_service import write_log
from app.permissions import login_required, require_permission

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


def _current_user():
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def _mask_password(value):
    return '••••••••' if value else ''


def _build_smtp_response(config):
    if not config:
        return None
    return {
        'host': config.host,
        'port': config.port,
        'username': config.username,
        'password': _mask_password(config.password_encrypted),
        'from_address': config.from_address,
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


@settings_bp.route('/smtp', methods=['GET'])
@login_required
@require_permission('config.view')
def get_smtp():
    config = SmtpConfig.query.get(1)
    if not config:
        return jsonify({'smtp': None}), 200
    return jsonify({'smtp': _build_smtp_response(config)}), 200


@settings_bp.route('/smtp', methods=['PUT'])
@login_required
@require_permission('config.edit_smtp')
def update_smtp():
    data = request.get_json() or {}
    config = SmtpConfig.query.get(1)
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
    if 'from_address' in data and data['from_address'] != config.from_address:
        changed['from_address'] = [config.from_address, data['from_address']]
        config.from_address = data['from_address']
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
    write_log('config', 'smtp_updated', session.get('username', 'system'), 'smtp', {'changed': list(changed.keys())})
    return jsonify({'result': 'smtp updated'}), 200


@settings_bp.route('/smtp/test', methods=['POST'])
@login_required
@require_permission('config.edit_smtp')
def test_smtp():
    config = SmtpConfig.query.get(1)
    if not config:
        return jsonify({'error': 'SMTP not configured'}), 400
    user = _current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    password = None
    if config.password_encrypted:
        try:
            password = decrypt(config.password_encrypted)
        except Exception as exc:
            return jsonify({'error': f'Unable to decrypt SMTP password: {exc}'}), 500

    try:
        if config.use_ssl:
            server = smtplib.SMTP_SSL(config.host, config.port, timeout=10)
        else:
            server = smtplib.SMTP(config.host, config.port, timeout=10)
            if config.use_tls:
                server.ehlo()
                server.starttls()
                server.ehlo()
        if config.username and password:
            server.login(config.username, password)
        message = EmailMessage()
        message['Subject'] = 'MW Link Monitor Test Email'
        message['From'] = config.from_address
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
    js = JumpServer.query.filter_by(active=True).first()
    if not js:
        return jsonify({'jumpserver': None}), 200
    return jsonify({'jumpserver': _build_jump_response(js)}), 200


@settings_bp.route('/jumpserver', methods=['PUT'])
@login_required
@require_permission('config.edit_jumpserver')
def update_jumpserver():
    data = request.get_json() or {}
    if not data.get('host') or not data.get('username'):
        return jsonify({'error': 'Missing required fields'}), 400

    active_js = JumpServer.query.filter_by(active=True).first()
    changed = {}
    if active_js:
        active_js.active = False
        db.session.commit()

    js = JumpServer(
        host=data['host'],
        port=int(data.get('port', 22)),
        username=data['username'],
        password_encrypted=encrypt(data.get('password', '')) if data.get('password') and data.get('password') != '••••••••' else (active_js.password_encrypted if active_js else None),
        active=True,
        label=data.get('label'),
        updated_by_id=session.get('user_id')
    )
    db.session.add(js)
    db.session.commit()
    write_log('config', 'jumpserver_updated', session.get('username', 'system'), 'jumpserver', {'changed': list(data.keys())})
    return jsonify({'jumpserver': _build_jump_response(js)}), 200


@settings_bp.route('/jumpserver/test', methods=['POST'])
@login_required
@require_permission('config.edit_jumpserver')
def test_jumpserver():
    data = request.get_json() or {}
    js = JumpServer.query.filter_by(active=True).first()
    if not js:
        return jsonify({'error': 'Jump server not configured'}), 400

    password = None
    if js.password_encrypted:
        try:
            password = decrypt(js.password_encrypted)
        except Exception as exc:
            return jsonify({'error': f'Unable to decrypt jump server password: {exc}'}), 500

    try:
        ssh = SSHService(js.host, js.username, password, js.port)
        ssh.connect()
        ssh.disconnect()
        return jsonify({'result': 'connection successful'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@settings_bp.route('/app', methods=['GET'])
@login_required
@require_permission('config.view')
def get_app_settings():
    settings = AppSettings.query.get(1)
    if not settings:
        return jsonify({'app': None}), 200
    return jsonify({'app': {
        'session_timeout_minutes': settings.session_timeout_minutes,
        'ping_interval_seconds': settings.ping_interval_seconds,
        'ping_count': settings.ping_count,
        'ping_timeout_seconds': settings.ping_timeout_seconds,
        'consecutive_timeout_alert_threshold': settings.consecutive_timeout_alert_threshold,
        'util_warning_threshold_pct': settings.util_warning_threshold_pct,
        'util_critical_threshold_pct': settings.util_critical_threshold_pct
    }}), 200


@settings_bp.route('/app', methods=['PUT'])
@login_required
@require_permission('config.edit_app')
def update_app_settings():
    data = request.get_json() or {}
    settings = AppSettings.query.get(1)
    if not settings:
        settings = AppSettings(id=1)
        db.session.add(settings)

    changed = {}
    for field in ['session_timeout_minutes', 'ping_interval_seconds', 'ping_count', 'ping_timeout_seconds', 'consecutive_timeout_alert_threshold', 'util_warning_threshold_pct', 'util_critical_threshold_pct']:
        if field in data:
            value = data[field]
            if getattr(settings, field) != value:
                changed[field] = [getattr(settings, field), value]
                setattr(settings, field, value)

    settings.updated_by_id = session.get('user_id')
    settings.updated_at = datetime.utcnow()
    db.session.commit()
    write_log('config', 'app_settings_updated', session.get('username', 'system'), 'app_settings', {'changed': list(changed.keys())})
    return jsonify({'result': 'app settings updated'}), 200
