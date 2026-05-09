import re
import smtplib
from email.message import EmailMessage
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models import db, User, SetupState, SmtpConfig, AppSettings, JumpServer, NotificationSubscription
from app.services.crypto_service import encrypt
from app.services.ssh_service import SSHService
from app.extensions import bcrypt

setup_bp = Blueprint('setup', __name__, url_prefix='/api/setup')

USERNAME_PATTERN = re.compile(r'^[a-z0-9-]+$')
EVENT_KEYS = [
    'mw_link_down',
    'mw_link_recovered',
    'fiber_util_high',
    'fiber_util_near_cap',
    'mw_util_high',
    'consecutive_timeouts',
    'ping_service_error'
]


def _validate_email(email):
    return bool(email and re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def _validate_setup_payload(data):
    errors = {}
    if not data.get('full_name'):
        errors['full_name'] = 'Full Name is required.'
    username = data.get('username')
    if not username or not USERNAME_PATTERN.match(username):
        errors['username'] = 'Username must be lowercase, alphanumeric, or hyphens.'
    if not _validate_email(data.get('email')):
        errors['email'] = 'Valid email is required.'
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    if len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    if password != confirm_password:
        errors['confirm_password'] = 'Passwords must match.'

    smtp = data.get('smtp', {})
    if not smtp.get('host'):
        errors['smtp.host'] = 'SMTP host is required.'
    if not smtp.get('port'):
        errors['smtp.port'] = 'SMTP port is required.'
    if not smtp.get('from_address') or not _validate_email(smtp.get('from_address')):
        errors['smtp.from_address'] = 'Valid from address is required.'

    jumpserver = data.get('jumpserver', {})
    if not jumpserver.get('host'):
        errors['jumpserver.host'] = 'Jump server host is required.'
    if not jumpserver.get('port'):
        errors['jumpserver.port'] = 'Jump server port is required.'
    if not jumpserver.get('username'):
        errors['jumpserver.username'] = 'Jump server username is required.'
    if not jumpserver.get('password'):
        errors['jumpserver.password'] = 'Jump server password is required.'

    return errors


@setup_bp.route('/test-smtp', methods=['POST'])
def test_smtp():
    data = request.get_json() or {}
    if not data.get('host') or not data.get('port') or not data.get('from_address'):
        return jsonify({'error': 'Missing SMTP host, port, or from_address.'}), 400

    host = data.get('host')
    port = int(data.get('port'))
    username = data.get('username')
    password = data.get('password')
    use_tls = bool(data.get('use_tls', True))
    use_ssl = bool(data.get('use_ssl', False))
    from_address = data.get('from_address')

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
        server.ehlo()
        if use_tls and not use_ssl:
            server.starttls()
            server.ehlo()
        if username and password:
            server.login(username, password)
        server.quit()
        return jsonify({'result': 'SMTP connection successful'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@setup_bp.route('/test-jumpserver', methods=['POST'])
def test_jumpserver():
    data = request.get_json() or {}
    if not data.get('host') or not data.get('port') or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing jump server host, port, username, or password.'}), 400

    try:
        ssh = SSHService(data['host'], data['username'], data['password'], int(data['port']))
        ssh.connect()
        ssh.disconnect()
        return jsonify({'result': 'Jump server connection successful'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@setup_bp.route('/complete', methods=['POST'])
def complete_setup():
    data = request.get_json() or {}
    errors = _validate_setup_payload(data)
    if errors:
        return jsonify({'errors': errors}), 400

    setup_state = SetupState.query.get(1)
    if setup_state and setup_state.is_complete:
        return jsonify({'error': 'Setup already completed'}), 400

    username = data['username'].strip().lower()
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        username=username,
        full_name=data['full_name'].strip(),
        email=data['email'].strip(),
        password_hash=password_hash,
        role='admin',
        is_active=True,
        force_password_change=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(user)
    db.session.flush()

    smtp = data['smtp']
    smtp_config = SmtpConfig(
        id=1,
        host=smtp['host'],
        port=int(smtp['port']),
        username=smtp.get('username'),
        password_encrypted=encrypt(smtp.get('password', '')) if smtp.get('password') else None,
        from_address=smtp['from_address'],
        use_tls=bool(smtp.get('use_tls', True)),
        use_ssl=bool(smtp.get('use_ssl', False)),
        updated_at=datetime.utcnow(),
        updated_by_id=user.id
    )
    db.session.add(smtp_config)

    JumpServer.query.update({JumpServer.active: False})
    jumpserver = JumpServer(
        host=data['jumpserver']['host'],
        port=int(data['jumpserver']['port']),
        username=data['jumpserver']['username'],
        password_encrypted=encrypt(data['jumpserver']['password']),
        active=True,
        updated_at=datetime.utcnow(),
        updated_by_id=user.id
    )
    db.session.add(jumpserver)

    if not AppSettings.query.get(1):
        app_settings = AppSettings(id=1)
        db.session.add(app_settings)

    if not setup_state:
        setup_state = SetupState(id=1)
        db.session.add(setup_state)

    setup_state.is_complete = True
    setup_state.completed_at = datetime.utcnow()

    for event_key in EVENT_KEYS:
        subscription = NotificationSubscription(
            user_id=user.id,
            event_key=event_key,
            is_subscribed=True
        )
        db.session.add(subscription)

    db.session.commit()
    return jsonify({'redirect': '/login'}), 200
