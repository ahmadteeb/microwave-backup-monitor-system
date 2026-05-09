import json
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import quote_plus
from flask import Blueprint, request, jsonify, current_app
from app.models import db, User, SetupState, SmtpConfig, AppSettings, JumpServer, NotificationSubscription
from app.services.crypto_service import encrypt
from app.services.ssh_service import SSHService
from app.extensions import bcrypt

DB_ENGINES = {
    'sqlite': 'sqlite',
    'postgres': 'postgresql',
    'mysql': 'mysql+pymysql'
}


def _get_db_config_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'secrets', 'secrets.json'))


def _validate_db_payload(db_config):
    errors = {}
    engine = db_config.get('engine')
    if engine not in DB_ENGINES:
        errors['db_config.engine'] = 'Database engine must be sqlite, postgres, or mysql.'
        return errors

    if engine == 'sqlite':
        if not db_config.get('path'):
            errors['db_config.path'] = 'SQLite database path is required.'
    else:
        if not db_config.get('host'):
            errors['db_config.host'] = 'Database host is required.'
        if not db_config.get('port'):
            errors['db_config.port'] = 'Database port is required.'
        if not db_config.get('username'):
            errors['db_config.username'] = 'Database username is required.'
        if not db_config.get('database'):
            errors['db_config.database'] = 'Database name is required.'

    return errors


def _build_db_uri(db_config):
    engine = db_config.get('engine')
    if engine == 'sqlite':
        path = db_config.get('path', 'mw_monitor.db').strip() or 'mw_monitor.db'
        return f'sqlite:///{path}'

    driver = DB_ENGINES[engine]
    username = quote_plus(str(db_config.get('username', '')).strip())
    password = quote_plus(str(db_config.get('password', '') or ''))
    host = db_config.get('host').strip()
    port = int(db_config.get('port'))
    database = db_config.get('database').strip()
    return f'{driver}://{username}:{password}@{host}:{port}/{database}'


def _save_secrets(db_config, database_url, secret_key):
    config_path = _get_db_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    config_json = json.dumps({'database_url': database_url, 'db_config': db_config}, indent=2)
    from app.services.crypto_service import encrypt_with_key
    encrypted_data = encrypt_with_key(config_json, secret_key)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump({
            'secret_key': secret_key,
            'db_config_encrypted': encrypted_data
        }, f, indent=2)




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
    secret_key = data.get('secret_key')
    if not secret_key or len(secret_key) < 16:
        errors['secret_key'] = 'Secret key is required and must be at least 16 characters.'
    
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

    smtp_enabled = data.get('smtp_enabled', False)
    smtp = data.get('smtp', {})
    if smtp_enabled:
        if not smtp.get('host'):
            errors['smtp.host'] = 'SMTP host is required.'
        if not smtp.get('port'):
            errors['smtp.port'] = 'SMTP port is required.'
        if not smtp.get('from_address') or not _validate_email(smtp.get('from_address')):
            errors['smtp.from_address'] = 'Valid from address is required.'

    jumpserver_enabled = data.get('jumpserver_enabled', False)
    jumpserver = data.get('jumpserver', {})
    if jumpserver_enabled:
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
    db_errors = _validate_db_payload(data.get('db_config', {}))
    errors.update(db_errors)
    if errors:
        return jsonify({'errors': errors}), 400

    db_config = data.get('db_config', {})
    database_url = _build_db_uri(db_config)
    secret_key = data.get('secret_key')
    
    # Update current app secret key so crypto_service uses it
    current_app.config['SECRET_KEY'] = secret_key

    # Resolve sqlite path to instance folder just like Flask-SQLAlchemy does
    resolved_url = database_url
    if resolved_url.startswith('sqlite:///') and not resolved_url.startswith('sqlite:////') and resolved_url != 'sqlite:///:memory:':
        db_path = resolved_url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            os.makedirs(current_app.instance_path, exist_ok=True)
            db_path = os.path.join(current_app.instance_path, db_path)
            resolved_url = f'sqlite:///{db_path}'

    import sqlalchemy
    from sqlalchemy.orm import sessionmaker

    try:
        new_engine = sqlalchemy.create_engine(resolved_url)
        db.metadata.create_all(new_engine)
        Session = sessionmaker(bind=new_engine)
        new_session = Session()
    except Exception as exc:
        return jsonify({'error': f'Database connection failed: {exc}'}), 500

    try:
        setup_state = new_session.query(SetupState).get(1)
        if setup_state and setup_state.is_complete:
            return jsonify({'error': 'Setup already completed'}), 400

        username = data['username'].strip().lower()
        if new_session.query(User).filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409
        if new_session.query(User).filter_by(email=data['email']).first():
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
        new_session.add(user)
        new_session.flush()

        smtp = data.get('smtp', {})
        if data.get('smtp_enabled', False):
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
            new_session.add(smtp_config)

        if data.get('jumpserver_enabled', False):
            jumpserver = JumpServer(
                host=data['jumpserver']['host'],
                port=int(data['jumpserver']['port']),
                username=data['jumpserver']['username'],
                password_encrypted=encrypt(data['jumpserver']['password']),
                active=True,
                updated_at=datetime.utcnow(),
                updated_by_id=user.id
            )
            new_session.add(jumpserver)

        app_settings = new_session.query(AppSettings).get(1)
        if not app_settings:
            app_settings = AppSettings(id=1)
            new_session.add(app_settings)

        if not setup_state:
            setup_state = SetupState(id=1)
            new_session.add(setup_state)

        setup_state.is_complete = True
        setup_state.completed_at = datetime.utcnow()

        for event_key in EVENT_KEYS:
            subscription = NotificationSubscription(
                user_id=user.id,
                event_key=event_key,
                is_subscribed=True
            )
            new_session.add(subscription)

        new_session.commit()
    except Exception as exc:
        new_session.rollback()
        return jsonify({'error': f'Failed to populate database: {exc}'}), 500
    finally:
        new_session.close()

    _save_secrets(db_config, database_url, secret_key)
    return jsonify({'redirect': '/login'}), 200
