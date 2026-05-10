from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from app.models import db, User, UserPermission
from app.services.log_service import write_log
from app.extensions import bcrypt
from app.permissions import has_permission, ROLE_DEFAULTS

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _build_permissions(user_id):
    permissions = {}
    role = User.query.get(user_id).role if user_id else 'viewer'
    defaults = ROLE_DEFAULTS.get(role, {})
    for key in defaults:
        permissions[key] = has_permission(user_id, key)
    return permissions


def _normalize_username(value):
    return value.strip().lower() if value else None


def _session_payload(user):
    return {
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'role': user.role,
        'logged_in_at': datetime.utcnow().isoformat()
    }


@auth_bp.route('/me', methods=['GET'])
def get_me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'Authentication required'}), 401

    return jsonify({
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'role': user.role,
        'permissions': _build_permissions(user.id)
    }), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = _normalize_username(data.get('username'))
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Invalid username or password'}), 401

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active:
        write_log('auth', 'login_failed', 'anonymous', username, {'ip': request.remote_addr})
        return jsonify({'error': 'Invalid username or password'}), 401

    if user.is_locked:
        if user.locked_until and user.locked_until > datetime.utcnow():
            minutes = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            return jsonify({'error': 'Account locked. Please try again later.', 'minutes': minutes}), 423
        user.is_locked = False
        user.locked_until = None
        user.failed_login_count = 0
        db.session.commit()

    if not bcrypt.check_password_hash(user.password_hash, password):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.is_locked = True
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            write_log('auth', 'account_locked', 'system', user.username, {
                'failed_count': user.failed_login_count,
                'ip': request.remote_addr
            })
        db.session.commit()
        return jsonify({'error': 'Invalid username or password'}), 401

    user.failed_login_count = 0
    user.is_locked = False
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    session.clear()
    session.update(_session_payload(user))
    write_log('auth', 'login_success', user.username, user.username, {'ip': request.remote_addr})

    return jsonify({'redirect': '/'}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    user_id = session.get('user_id')
    username = session.get('username')
    session.clear()
    if username:
        write_log('auth', 'logout', username, username)
    return jsonify({'result': 'logged out'}), 200


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json() or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not new_password or new_password != confirm_password or len(new_password) < 8:
        return jsonify({'error': 'Password validation failed'}), 400

    if not user.force_password_change:
        if not current_password or not bcrypt.check_password_hash(user.password_hash, current_password):
            return jsonify({'error': 'Invalid current password'}), 401

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.force_password_change = False
    db.session.commit()
    write_log('auth', 'password_changed', user.username, user.username)
    return jsonify({'redirect': '/'}), 200
