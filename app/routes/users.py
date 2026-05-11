from flask import Blueprint, request, jsonify, session
from app.models import db, User, NotificationSubscription
from app.services.log_service import write_log
from app.extensions import bcrypt
from app.permissions import login_required, require_permission, ROLE_DEFAULTS

users_bp = Blueprint('users', __name__, url_prefix='/api/users')
EVENT_KEYS = [
    'mw_link_down',
    'mw_link_recovered',
    'fiber_util_high',
    'fiber_util_near_cap',
    'mw_util_high',
    'consecutive_timeouts',
    'ping_service_error'
]


def _seed_subscriptions(user_id):
    for event_key in EVENT_KEYS:
        subscription = NotificationSubscription(user_id=user_id, event_key=event_key, is_subscribed=True)
        db.session.add(subscription)


def _serialize_user(user):
    status = 'Active' if user.is_active else 'Inactive'
    if user.is_locked:
        status = 'Locked'
    return {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'role': user.role,
        'status': status,
        'last_login_at': user.last_login_at.isoformat() + 'Z' if user.last_login_at else None,
        'is_active': user.is_active,
        'is_locked': user.is_locked,
        'force_password_change': user.force_password_change
    }


@users_bp.route('', methods=['GET'])
@login_required
@require_permission('users.view')
def list_users():
    users = User.query.order_by(User.full_name).all()
    return jsonify({'users': [_serialize_user(u) for u in users]}), 200


@users_bp.route('', methods=['POST'])
@login_required
@require_permission('users.add')
def create_user():
    data = request.get_json() or {}
    required = ['full_name', 'username', 'email', 'role']
    if not all(data.get(field) for field in required):
        return jsonify({'error': 'Missing required fields'}), 400

    username = data['username'].strip().lower()
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    from app.models import Role
    if not Role.query.filter_by(name=data['role']).first():
        return jsonify({'error': 'Invalid role provided'}), 400

    password = data.get('password') or 'ChangeMe123!'
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user = User(
        username=username,
        full_name=data['full_name'].strip(),
        email=data['email'].strip(),
        role=data['role'],
        password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
        is_active=bool(data.get('is_active', True)),
        force_password_change=bool(data.get('force_password_change', True))
    )
    db.session.add(user)
    db.session.flush()
    _seed_subscriptions(user.id)
    db.session.commit()
    write_log('users', 'user_created', session.get('username', 'system'), user.username, {'role': user.role})
    return jsonify({'id': user.id}), 201


@users_bp.route('/<int:id>', methods=['GET'])
@login_required
@require_permission('users.view')
def get_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': _serialize_user(user)}), 200


@users_bp.route('/<int:id>', methods=['PUT'])
@login_required
@require_permission('users.edit')
def update_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json() or {}
    updates = {}

    if data.get('full_name') and data['full_name'] != user.full_name:
        updates['full_name'] = [user.full_name, data['full_name'].strip()]
        user.full_name = data['full_name'].strip()
    if data.get('email') and data['email'] != user.email:
        if User.query.filter(User.email == data['email'], User.id != id).first():
            return jsonify({'error': 'Email already exists'}), 409
        updates['email'] = [user.email, data['email'].strip()]
        user.email = data['email'].strip()
    if data.get('role') and data['role'] != user.role:
        from app.models import Role
        if not Role.query.filter_by(name=data['role']).first():
            return jsonify({'error': 'Invalid role provided'}), 400
        updates['role'] = [user.role, data['role']]
        user.role = data['role']
    if 'is_active' in data and data['is_active'] != user.is_active:
        updates['is_active'] = [user.is_active, data['is_active']]
        user.is_active = bool(data['is_active'])
    if 'force_password_change' in data and data['force_password_change'] != user.force_password_change:
        updates['force_password_change'] = [user.force_password_change, data['force_password_change']]
        user.force_password_change = bool(data['force_password_change'])

    db.session.commit()
    if updates:
        write_log('users', 'user_edited', session.get('username', 'system'), user.username, {'changed': updates})
    return jsonify({'result': 'updated'}), 200


@users_bp.route('/<int:id>', methods=['DELETE'])
@login_required
@require_permission('users.delete')
def delete_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if session.get('user_id') == user.id:
        return jsonify({'error': 'Cannot delete own account'}), 400
    db.session.delete(user)
    db.session.commit()
    write_log('users', 'user_deleted', session.get('username', 'system'), user.username)
    return jsonify({'result': 'deleted'}), 200


@users_bp.route('/<int:id>/reset-password', methods=['POST'])
@login_required
@require_permission('users.reset_password')
def reset_password(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json() or {}
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    force_password_change = bool(data.get('force_password_change', True))

    if len(new_password) < 8 or new_password != confirm_password:
        return jsonify({'error': 'Password validation failed'}), 400

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.force_password_change = force_password_change
    db.session.commit()
    write_log('auth', 'password_reset', session.get('username', 'system'), user.username, {'force_change': force_password_change})
    return jsonify({'result': 'password reset'}), 200


@users_bp.route('/<int:id>/unlock', methods=['POST'])
@login_required
@require_permission('users.edit')
def unlock_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.is_locked = False
    user.locked_until = None
    user.failed_login_count = 0
    db.session.commit()
    write_log('auth', 'account_unlocked', session.get('username', 'system'), user.username, {'reason': 'manual'})
    return jsonify({'result': 'unlocked'}), 200



@users_bp.route('/<int:id>/notifications/subscriptions', methods=['GET'])
@login_required
@require_permission('notifications.manage_all')
def get_user_subscriptions(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    records = NotificationSubscription.query.filter_by(user_id=user.id).all()
    return jsonify({'subscriptions': [
        {'event_key': r.event_key, 'is_subscribed': r.is_subscribed}
        for r in records
    ]}), 200


@users_bp.route('/<int:id>/notifications/subscriptions', methods=['PUT'])
@login_required
@require_permission('notifications.manage_all')
def update_user_subscriptions(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json() or {}
    subs = data.get('subscriptions', [])
    if not isinstance(subs, list):
        return jsonify({'error': 'Invalid subscriptions payload'}), 400

    changed = []
    for entry in subs:
        event_key = entry.get('event_key')
        is_subscribed = bool(entry.get('is_subscribed', False))
        record = NotificationSubscription.query.filter_by(user_id=user.id, event_key=event_key).first()
        if record:
            if record.is_subscribed != is_subscribed:
                changed.append({'event_key': event_key, 'old': record.is_subscribed, 'new': is_subscribed})
                record.is_subscribed = is_subscribed
        else:
            new_record = NotificationSubscription(user_id=user.id, event_key=event_key, is_subscribed=is_subscribed)
            db.session.add(new_record)
            changed.append({'event_key': event_key, 'old': None, 'new': is_subscribed})

    db.session.commit()
    return jsonify({'result': 'subscriptions updated'}), 200
