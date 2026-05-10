from flask import Blueprint, request, jsonify, session
from app.models import db, InAppNotification, NotificationSubscription, User
from app.services.log_service import write_log
from app.permissions import login_required, require_permission

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


def _current_user():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None


@notifications_bp.route('', methods=['GET'])
@login_required
@require_permission('notifications.view_own')
def list_notifications():
    user = _current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    paginated = InAppNotification.query.filter_by(user_id=user.id).order_by(InAppNotification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'notifications': [
            {
                'id': n.id,
                'event_key': n.event_key,
                'severity': n.severity,
                'link_id': n.link_id,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat() + 'Z'
            }
            for n in paginated.items
        ],
        'page': paginated.page,
        'per_page': paginated.per_page,
        'total': paginated.total,
        'pages': paginated.pages
    }), 200


@notifications_bp.route('/unread-count', methods=['GET'])
@login_required
@require_permission('notifications.view_own')
def unread_count():
    user = _current_user()
    count = InAppNotification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({'unread_count': count}), 200


@notifications_bp.route('/<int:id>/read', methods=['POST'])
@login_required
@require_permission('notifications.view_own')
def mark_as_read(id):
    user = _current_user()
    notification = InAppNotification.query.filter_by(id=id, user_id=user.id).first_or_404()
    notification.is_read = True
    db.session.commit()
    return jsonify({'result': 'read'}), 200


@notifications_bp.route('/read-all', methods=['POST'])
@login_required
@require_permission('notifications.view_own')
def mark_all_read():
    user = _current_user()
    InAppNotification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'result': 'all read'}), 200


@notifications_bp.route('/clear', methods=['POST'])
@login_required
@require_permission('notifications.edit_own')
def clear_notifications():
    user = _current_user()
    InAppNotification.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({'result': 'notifications cleared'}), 200


@notifications_bp.route('/subscriptions', methods=['GET'])
@login_required
@require_permission('notifications.edit_own')
def get_subscriptions():
    user = _current_user()
    records = NotificationSubscription.query.filter_by(user_id=user.id).all()
    return jsonify({'subscriptions': [
        {'event_key': r.event_key, 'is_subscribed': r.is_subscribed}
        for r in records
    ]}), 200


@notifications_bp.route('/subscriptions', methods=['PUT'])
@login_required
@require_permission('notifications.edit_own')
def update_subscriptions():
    user = _current_user()
    data = request.get_json() or {}
    subs = data.get('subscriptions', [])
    if not isinstance(subs, list):
        return jsonify({'error': 'Invalid payload'}), 400

    for entry in subs:
        event_key = entry.get('event_key')
        is_subscribed = bool(entry.get('is_subscribed', False))
        record = NotificationSubscription.query.filter_by(user_id=user.id, event_key=event_key).first()
        if record:
            record.is_subscribed = is_subscribed
        else:
            db.session.add(NotificationSubscription(user_id=user.id, event_key=event_key, is_subscribed=is_subscribed))

    db.session.commit()
    return jsonify({'result': 'updated'}), 200
