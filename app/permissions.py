from functools import wraps
from flask import session, request, redirect, jsonify
from app.models import db, User

ROLE_DEFAULTS = {
    'admin': {
        'links.view': True,
        'links.add': True,
        'links.edit': True,
        'links.delete': True,
        'links.ping': True,
        'links.export': True,
        'users.view': True,
        'users.add': True,
        'users.edit': True,
        'users.delete': True,
        'users.reset_password': True,
        'users.manage_permissions': True,
        'config.view': True,
        'config.edit_smtp': True,
        'config.edit_jumpserver': True,
        'config.edit_app': True,
        'logs.view_system': True,
        'logs.view_ping': True,
        'logs.export': True,
        'notifications.view_own': True,
        'notifications.edit_own': True,
        'notifications.manage_all': True,
    },
    'operator': {
        'links.view': True,
        'links.add': True,
        'links.edit': True,
        'links.delete': False,
        'links.ping': True,
        'links.export': True,
        'users.view': True,
        'users.add': False,
        'users.edit': False,
        'users.delete': False,
        'users.reset_password': False,
        'users.manage_permissions': False,
        'config.view': False,
        'config.edit_smtp': False,
        'config.edit_jumpserver': False,
        'config.edit_app': False,
        'logs.view_system': True,
        'logs.view_ping': True,
        'logs.export': True,
        'notifications.view_own': True,
        'notifications.edit_own': True,
        'notifications.manage_all': False,
    },
    'viewer': {
        'links.view': True,
        'links.add': False,
        'links.edit': False,
        'links.delete': False,
        'links.ping': False,
        'links.export': True,
        'users.view': False,
        'users.add': False,
        'users.edit': False,
        'users.delete': False,
        'users.reset_password': False,
        'users.manage_permissions': False,
        'config.view': False,
        'config.edit_smtp': False,
        'config.edit_jumpserver': False,
        'config.edit_app': False,
        'logs.view_system': False,
        'logs.view_ping': True,
        'logs.export': False,
        'notifications.view_own': True,
        'notifications.edit_own': True,
        'notifications.manage_all': False,
    }
}


def has_permission(user_id, permission_key):
    if not user_id:
        return False
        
    user = db.session.get(User, user_id)
    if not user:
        return False
        
    # Check role permissions in DB
    from app.models import RolePermission
    role_perm = RolePermission.query.filter_by(role_name=user.role, permission_key=permission_key).first()
    if role_perm is not None:
        return role_perm.is_granted
        
    # Fallback to hardcoded defaults (in case DB isn't seeded yet)
    return ROLE_DEFAULTS.get(user.role, {}).get(permission_key, False)


def _is_api_request():
    return request.path.startswith('/api/')


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if _is_api_request():
                return jsonify({'error': 'Authentication required'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


def require_permission(permission_key):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id or not has_permission(user_id, permission_key):
                return jsonify({'error': 'Permission denied', 'code': 'FORBIDDEN'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
