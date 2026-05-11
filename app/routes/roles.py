from flask import Blueprint, request, jsonify
from app.models import db, Role, RolePermission, User
from app.services.log_service import write_log
from app.permissions import login_required, require_permission, ROLE_DEFAULTS

roles_bp = Blueprint('roles', __name__, url_prefix='/api/roles')

# Helper to get all available permission keys
def _get_all_permission_keys():
    # Return keys from the admin defaults since admin has all keys
    return list(ROLE_DEFAULTS.get('admin', {}).keys())


@roles_bp.route('', methods=['GET'])
@login_required
@require_permission('users.manage_permissions')
def list_roles():
    roles = Role.query.order_by(Role.name).all()
    return jsonify({
        'roles': [
            {
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'is_system': r.is_system,
                'created_at': r.created_at.isoformat() + 'Z'
            }
            for r in roles
        ]
    }), 200


@roles_bp.route('', methods=['POST'])
@login_required
@require_permission('users.manage_permissions')
def create_role():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()

    if not name:
        return jsonify({'error': 'Role name is required'}), 400
        
    if not name.isalnum() and not all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        return jsonify({'error': 'Role name can only contain letters, numbers, hyphens, and underscores'}), 400

    if Role.query.filter_by(name=name).first():
        return jsonify({'error': 'Role with this name already exists'}), 409

    role = Role(name=name, description=description, is_system=False)
    db.session.add(role)
    db.session.commit()
    
    # Initialize all permissions to False
    all_keys = _get_all_permission_keys()
    for key in all_keys:
        rp = RolePermission(role_name=name, permission_key=key, is_granted=False)
        db.session.add(rp)
    db.session.commit()

    write_log('auth', 'role_created', 'system', name, {'description': description})
    return jsonify({'result': 'role created', 'id': role.id}), 201


@roles_bp.route('/<string:name>', methods=['PUT'])
@login_required
@require_permission('users.manage_permissions')
def update_role(name):
    role = Role.query.filter_by(name=name).first_or_404()
    data = request.get_json() or {}

    if 'description' in data:
        role.description = data['description'].strip()

    db.session.commit()
    write_log('auth', 'role_updated', 'system', name)
    return jsonify({'result': 'role updated'}), 200


@roles_bp.route('/<string:name>', methods=['DELETE'])
@login_required
@require_permission('users.manage_permissions')
def delete_role(name):
    role = Role.query.filter_by(name=name).first_or_404()
    
    if role.is_system:
        return jsonify({'error': 'Cannot delete a system role'}), 403
        
    # Check if any users are using this role
    if User.query.filter_by(role=name).first():
        return jsonify({'error': 'Cannot delete role because it is assigned to one or more users'}), 409

    db.session.delete(role)
    db.session.commit()
    write_log('auth', 'role_deleted', 'system', name)
    return jsonify({'result': 'role deleted'}), 200


@roles_bp.route('/<string:name>/permissions', methods=['GET'])
@login_required
@require_permission('users.manage_permissions')
def get_role_permissions(name):
    role = Role.query.filter_by(name=name).first_or_404()
    perms = RolePermission.query.filter_by(role_name=name).all()
    
    # Also ensure any missing keys are returned as False
    all_keys = _get_all_permission_keys()
    perm_dict = {p.permission_key: p.is_granted for p in perms}
    
    result = {}
    for key in all_keys:
        result[key] = perm_dict.get(key, False)

    return jsonify({'permissions': result}), 200


@roles_bp.route('/<string:name>/permissions', methods=['PUT'])
@login_required
@require_permission('users.manage_permissions')
def update_role_permissions(name):
    role = Role.query.filter_by(name=name).first_or_404()
    data = request.get_json() or {}
    overrides = data.get('permissions', {})
    
    if not isinstance(overrides, dict):
        return jsonify({'error': 'Invalid payload'}), 400

    all_keys = _get_all_permission_keys()
    
    for key, value in overrides.items():
        if key not in all_keys:
            continue
        is_granted = bool(value)
        rp = RolePermission.query.filter_by(role_name=name, permission_key=key).first()
        if rp:
            rp.is_granted = is_granted
        else:
            db.session.add(RolePermission(role_name=name, permission_key=key, is_granted=is_granted))
            
    db.session.commit()
    write_log('auth', 'role_permissions_updated', 'system', name)
    return jsonify({'result': 'permissions updated'}), 200
