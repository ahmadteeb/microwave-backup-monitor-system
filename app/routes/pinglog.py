from flask import Blueprint, request, jsonify
from app.models import PingResult

pinglog_bp = Blueprint('pinglog', __name__, url_prefix='/api/ping-log')

@pinglog_bp.route('', methods=['GET'])
def get_ping_log():
    limit = request.args.get('limit', 50, type=int)
    if limit > 200:
        limit = 200

    results = PingResult.query.order_by(PingResult.timestamp.desc()).limit(limit).all()
    
    log_entries = []
    for r in results:
        status_text = "PING OK"
        if not r.reachable:
            if r.latency_ms is None:
                status_text = "TIMEOUT"
            else:
                status_text = "ERR" # Unreachable but has latency? Edge case.
        elif r.packet_loss is not None and r.packet_loss > 0:
            status_text = "PKT_LOSS"

        log_entries.append({
            "link_id": r.link.link_id if r.link else "UNKNOWN",
            "timestamp": r.timestamp.isoformat() + "Z",
            "reachable": r.reachable,
            "latency_ms": r.latency_ms,
            "status_text": status_text
        })

    return jsonify({"results": log_entries}), 200
