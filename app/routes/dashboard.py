from flask import Blueprint, jsonify
from app import APP_START_TIME
from app.models import db, Link, PingResult, MetricSnapshot, LinkStatus
from app.permissions import login_required, require_permission
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/kpi', methods=['GET'])
@login_required
@require_permission('links.view')
def get_kpis():
    total_links = Link.query.count()
    
    mw_reachable = LinkStatus.query.filter(LinkStatus.mw_status.in_(['up', 'high'])).count()
    high_utilization = LinkStatus.query.filter(LinkStatus.mw_status == 'high').count()
    mw_unreachable = total_links - mw_reachable
    
    uptime_seconds = int((datetime.utcnow() - APP_START_TIME).total_seconds())
    uptime_parts = []
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    if days:
        uptime_parts.append(f"{days}d");
    if hours:
        uptime_parts.append(f"{hours}h");
    uptime_parts.append(f"{minutes}m")
    uptime_display = ' '.join(uptime_parts)

    since = datetime.utcnow() - timedelta(hours=24)
    total_pings = PingResult.query.filter(PingResult.timestamp >= since).count()
    ok_pings = PingResult.query.filter(PingResult.timestamp >= since, PingResult.reachable.is_(True)).count()
    availability_pct = round((ok_pings / total_pings * 100), 1) if total_pings > 0 else None

    return jsonify({
        "total_links": total_links,
        "mw_reachable": mw_reachable,
        "mw_unreachable": mw_unreachable,
        "high_utilization": high_utilization,
        "uptime_display": uptime_display,
        "link_availability_24h": availability_pct,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }), 200
