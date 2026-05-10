import csv
import io
from flask import Blueprint, request, jsonify, Response
from app.extensions import db
from app.models import SystemLog, PingResult
from app.permissions import login_required, require_permission

logs_bp = Blueprint('logs', __name__, url_prefix='/api/logs')


def _apply_filters(query, model):
    if model is SystemLog:
        category = request.args.get('category')
        actor = request.args.get('actor')
        search = request.args.get('search')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if category:
            query = query.filter(SystemLog.category == category)
        if actor:
            query = query.filter(SystemLog.actor.ilike(f'%{actor}%'))
        if search:
            query = query.filter(SystemLog.detail.ilike(f'%{search}%'))
        if date_from:
            query = query.filter(SystemLog.timestamp >= date_from)
        if date_to:
            query = query.filter(SystemLog.timestamp <= date_to)
    else:
        search = request.args.get('search')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if search:
            query = query.filter(PingResult.link.has(link_id=search) | PingResult.raw_output.ilike(f'%{search}%'))
        if date_from:
            query = query.filter(PingResult.timestamp >= date_from)
        if date_to:
            query = query.filter(PingResult.timestamp <= date_to)
    return query


@logs_bp.route('/system', methods=['GET'])
@login_required
@require_permission('logs.view_system')
def get_system_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    query = SystemLog.query.order_by(SystemLog.timestamp.desc())
    query = _apply_filters(query, SystemLog)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'logs': [
            {
                'timestamp': log.timestamp.isoformat() + 'Z',
                'category': log.category,
                'event': log.event,
                'actor': log.actor,
                'target': log.target,
                'detail': log.detail,
                'ip_address': log.ip_address
            }
            for log in paginated.items
        ],
        'page': paginated.page,
        'per_page': paginated.per_page,
        'total': paginated.total,
        'pages': paginated.pages
    }), 200


@logs_bp.route('/system/export', methods=['GET'])
@login_required
@require_permission('logs.export')
def export_system_logs():
    query = SystemLog.query.order_by(SystemLog.timestamp.desc())
    query = _apply_filters(query, SystemLog)
    rows = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'category', 'event', 'actor', 'target', 'detail', 'ip_address'])
    for log in rows:
        writer.writerow([
            log.timestamp.isoformat() + 'Z',
            log.category,
            log.event,
            log.actor,
            log.target,
            log.detail if log.detail is not None else '',
            log.ip_address or ''
        ])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="system_logs.csv"'})


@logs_bp.route('/ping', methods=['GET'])
@login_required
@require_permission('logs.view_ping')
def get_ping_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    query = PingResult.query.order_by(PingResult.timestamp.desc())
    query = _apply_filters(query, PingResult)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'logs': [
            {
                'timestamp': row.timestamp.isoformat() + 'Z',
                'link_id': row.link.link_id if row.link else None,
                'reachable': row.reachable,
                'latency_ms': row.latency_ms,
                'packet_loss': row.packet_loss,
                'raw_output': row.raw_output,
                'triggered_by': row.triggered_by,
                'triggered_by_user_id': row.triggered_by_user_id
            }
            for row in paginated.items
        ],
        'page': paginated.page,
        'per_page': paginated.per_page,
        'total': paginated.total,
        'pages': paginated.pages
    }), 200


@logs_bp.route('/ping/export', methods=['GET'])
@login_required
@require_permission('logs.export')
def export_ping_logs():
    query = PingResult.query.order_by(PingResult.timestamp.desc())
    query = _apply_filters(query, PingResult)
    rows = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'link_id', 'reachable', 'latency_ms', 'packet_loss', 'raw_output', 'triggered_by', 'triggered_by_user_id'])
    for row in rows:
        writer.writerow([
            row.timestamp.isoformat() + 'Z',
            row.link.link_id if row.link else '',
            row.reachable,
            row.latency_ms if row.latency_ms is not None else '',
            row.packet_loss if row.packet_loss is not None else '',
            row.raw_output or '',
            row.triggered_by,
            row.triggered_by_user_id or ''
        ])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="ping_logs.csv"'})
