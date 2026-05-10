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

@dashboard_bp.route('/stability', methods=['GET'])
@login_required
@require_permission('links.view')
def get_stability():
    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # We want success rate per hour.
    # Grouping by hour in SQLite is string manipulation.
    # Since we need a portable solution, we can fetch the last 24h of pings and bucket in python.
    pings = PingResult.query.filter(PingResult.timestamp >= twenty_four_hours_ago).all()
    
    # Initialize 24 buckets
    buckets = {}
    for i in range(24):
        # hour start
        bucket_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23-i)
        buckets[bucket_time] = {"total_pings": 0, "successful": 0}
        
    for p in pings:
        # Round timestamp down to the nearest hour
        b_time = p.timestamp.replace(minute=0, second=0, microsecond=0)
        if b_time in buckets:
            buckets[b_time]["total_pings"] += 1
            if p.reachable:
                buckets[b_time]["successful"] += 1

    hours = []
    # Ensure they are sorted
    for b_time in sorted(buckets.keys()):
        stats = buckets[b_time]
        total = stats["total_pings"]
        successful = stats["successful"]
        failed = total - successful
        rate = (successful / total * 100.0) if total > 0 else 0.0
        
        hours.append({
            "hour": b_time.isoformat() + "Z",
            "total_pings": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(rate, 1)
        })

    return jsonify({"hours": hours}), 200
