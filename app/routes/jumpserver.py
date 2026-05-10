import base64
import hashlib

from cryptography.fernet import Fernet
from flask import Blueprint, request, jsonify, current_app
from app.models import db, JumpServer
from app.permissions import login_required, require_permission

jumpserver_bp = Blueprint('jumpserver', __name__, url_prefix='/api/jumpserver')

def get_fernet_key():
    secret = current_app.config['SECRET_KEY']
    # Create a 32-byte url-safe base64 key from the SECRET_KEY
    key_bytes = hashlib.sha256(secret.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(key_bytes)

def encrypt_password(password):
    f = Fernet(get_fernet_key())
    return f.encrypt(password.encode('utf-8')).decode('utf-8')

def decrypt_password(encrypted_password):
    f = Fernet(get_fernet_key())
    return f.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')

@jumpserver_bp.route('', methods=['GET'])
@login_required
@require_permission('config.view')
def get_jumpserver():
    js = JumpServer.query.filter_by(active=True).first()
    if not js:
        return jsonify({"error": "No active jump server configured"}), 404

    return jsonify({
        "id": js.id,
        "host": js.host,
        "port": js.port,
        "username": js.username,
        "password": "••••••••",
        "active": js.active,
        "label": js.label
    }), 200

@jumpserver_bp.route('', methods=['PUT'])
@login_required
@require_permission('config.edit_jumpserver')
def update_jumpserver():
    data = request.get_json() or {}
    active = bool(data.get('active', False))
    password = data.get('password')

    active_js = JumpServer.query.filter_by(active=True).first()

    if not active:
        if active_js:
            active_js.active = False
            if data.get('host'):
                active_js.host = data['host']
            if data.get('port'):
                active_js.port = int(data.get('port', active_js.port))
            if data.get('username'):
                active_js.username = data['username']
            if password and password != '••••••••':
                active_js.password_encrypted = encrypt_password(password)
            if data.get('label') is not None:
                active_js.label = data.get('label')
            db.session.commit()

        return jsonify({
            "active": False
        }), 200

    if not data.get('host') or not data.get('username'):
        return jsonify({"error": "Missing required fields: host and username"}), 400

    if active_js:
        active_js.active = False
        db.session.commit()

    if password and password != '••••••••':
        encrypted_password = encrypt_password(password)
    else:
        encrypted_password = active_js.password_encrypted if active_js else None

    js = JumpServer(
        host=data['host'],
        port=int(data.get('port', 22)),
        username=data['username'],
        password_encrypted=encrypted_password,
        active=True,
        label=data.get('label')
    )
    db.session.add(js)
    db.session.commit()

    return jsonify({
        "id": js.id,
        "host": js.host,
        "port": js.port,
        "username": js.username,
        "password": "••••••••",
        "active": js.active,
        "label": js.label
    }), 200
