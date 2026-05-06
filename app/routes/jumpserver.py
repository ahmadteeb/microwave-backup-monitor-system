from flask import Blueprint, request, jsonify, current_app
from app.models import db, JumpServer
from cryptography.fernet import Fernet
import base64
import hashlib

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
def get_jumpserver():
    js = JumpServer.query.filter_by(active=True).first()
    if not js:
        # Provide fallback from config if none in DB, though usually we want DB config
        fallback_host = current_app.config.get('JUMP_HOST')
        if fallback_host:
            return jsonify({
                "id": 0,
                "host": fallback_host,
                "port": current_app.config.get('JUMP_PORT', 22),
                "username": current_app.config.get('JUMP_USER'),
                "password": "••••••••",
                "active": True,
                "label": "Config Fallback"
            }), 200
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
def update_jumpserver():
    data = request.get_json()
    if not data or not data.get('host') or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Missing required fields: host, username, password"}), 400

    # Deactivate all existing
    JumpServer.query.update({JumpServer.active: False})
    
    js = JumpServer(
        host=data['host'],
        port=data.get('port', 22),
        username=data['username'],
        password_encrypted=encrypt_password(data['password']),
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
