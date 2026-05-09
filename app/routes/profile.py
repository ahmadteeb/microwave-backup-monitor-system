from flask import Blueprint, request, jsonify, session
from app.models import db, User
from app.extensions import bcrypt
from app.services.log_service import write_log
from app.permissions import login_required

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')


@profile_bp.route('', methods=['GET'])
@login_required
def get_profile():
    user = User.query.get(session.get('user_id'))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'role': user.role,
        'last_login_at': user.last_login_at.isoformat() + 'Z' if user.last_login_at else None,
        'force_password_change': user.force_password_change
    }), 200


@profile_bp.route('', methods=['PUT'])
@login_required
def update_profile():
    user = User.query.get(session.get('user_id'))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    if data.get('full_name'):
        user.full_name = data['full_name'].strip()
    if data.get('email') and data['email'] != user.email:
        if User.query.filter(User.email == data['email'], User.id != user.id).first():
            return jsonify({'error': 'Email already exists'}), 409
        user.email = data['email'].strip()
    if 'password' in data and data.get('password'):
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        if data.get('password') != data.get('confirm_password'):
            return jsonify({'error': 'Password confirmation does not match'}), 400
        user.password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        user.force_password_change = False
        write_log('auth', 'profile_password_changed', user.username, user.username)

    db.session.commit()
    return jsonify({'result': 'profile updated'}), 200
