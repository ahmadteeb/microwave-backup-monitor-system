import csv
import io
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from app.models import db, Link, PingResult, AppSettings, LinkStatus
from app.services.ping_service import ping_single_link
from app.services.notification_service import send_event_notification
from app.services.external_util_service import refresh_external_utilization_for_single_link, lookup_link_info, lookup_leg_info
from app.permissions import login_required, require_permission

links_bp = Blueprint('links', __name__, url_prefix='/api/links')

def validate_ipv4(ip):
    pattern = re.compile(r'^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$')
    return pattern.match(ip)

def serialize_link(link):
    # Get latest ping result
    latest_ping = link.ping_results.order_by(PingResult.timestamp.desc()).first()
    
    status = 'UNKNOWN'
    if link.status:
        status = link.status.mw_status.upper()

    ping_data = None
    latency = None
    if latest_ping:
        ping_data = {
            "reachable": latest_ping.reachable,
            "latency_ms": latest_ping.latency_ms,
            "packet_loss": latest_ping.packet_loss,
            "timestamp": latest_ping.timestamp.isoformat() + "Z"
        }
        latency = latest_ping.latency_ms
        if status == 'UNKNOWN':
            if latest_ping.reachable:
                status = 'UP'
            else:
                if latest_ping.raw_output and "100% packet loss" in latest_ping.raw_output:
                    status = 'TIMEOUT'
                else:
                    status = 'DOWN'

    metric_data = None
    leg_util_pct = None
    leg_bitrate = None
    leg_capacity_pct = None
    
    if link.status:
        metric_data = {
            "leg_util_pct": link.status.leg_util_pct,
            "leg_capacity_mbps": link.status.leg_capacity_mbps,
            "mw_util_pct": link.status.mw_util_pct,
            "mw_capacity_mbps": link.status.mw_capacity_mbps,
            "timestamp": link.status.last_metric_at.isoformat() + "Z" if link.status.last_metric_at else None
        }
        settings = db.session.get(AppSettings, 1)
        warn_pct = settings.util_warning_threshold_pct if settings else 70.0
        if status == 'UP' and link.status.mw_util_pct is not None and link.status.mw_util_pct >= warn_pct:
            status = 'HIGH'

        leg_util_pct = link.status.leg_util_pct
        if link.status.avg_max_mbitrate:
            leg_bitrate = link.status.avg_max_mbitrate
            if link.status.mw_capacity_mbps:
                try:
                    leg_capacity_pct = round((float(link.status.mw_capacity_mbps) / float(link.status.avg_max_mbitrate)) * 100, 1)
                except (TypeError, ValueError, ZeroDivisionError):
                    pass

    return {
        "id": link.id,
        "link_id": link.link_id,
        "leg_name": link.leg_name,
        "site_a": link.site_a,
        "site_b": link.site_b,
        "mw_ip": link.mw_ip,
        "equipment_a": link.equipment_a,
        "equipment_b": link.equipment_b,
        "link_type": link.link_type,
        "notes": link.notes,
        "status": status,
        "leg_util_pct": leg_util_pct,
        "leg_bitrate": leg_bitrate,
        "leg_capacity_pct": leg_capacity_pct,
        "latency_ms": latency,
        "latest_ping": ping_data,
        "latest_metric": metric_data
    }

@links_bp.route('', methods=['GET'])
@login_required
@require_permission('links.view')
def list_links():
    status_filter = request.args.get('status')
    leg_filter = request.args.get('leg')
    search_query = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Link.query

    if leg_filter and leg_filter != 'ALL_REGIONS':
        query = query.filter(Link.leg_name == leg_filter)
    
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(db.or_(
            Link.link_id.ilike(search_term),
            Link.leg_name.ilike(search_term)
        ))

    if status_filter and status_filter != 'ALL_OPERATIONAL':
        status_lower = status_filter.lower()
        query = query.outerjoin(LinkStatus, Link.id == LinkStatus.link_id)
        query = query.filter(LinkStatus.mw_status == status_lower)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    results = [serialize_link(link) for link in paginated.items]

    return jsonify({
        "links": results,
        "total": paginated.total,
        "page": paginated.page,
        "per_page": paginated.per_page,
        "pages": paginated.pages
    })

@links_bp.route('/export', methods=['GET'])
@login_required
@require_permission('links.export')
def export_links():
    status_filter = request.args.get('status')
    leg_filter = request.args.get('leg')
    search_query = request.args.get('search')

    query = Link.query
    if leg_filter and leg_filter != 'ALL_REGIONS':
        query = query.filter(Link.leg_name == leg_filter)
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(db.or_(
            Link.link_id.ilike(search_term),
            Link.leg_name.ilike(search_term)
        ))
    if status_filter and status_filter != 'ALL_OPERATIONAL':
        status_lower = status_filter.lower()
        query = query.outerjoin(LinkStatus, Link.id == LinkStatus.link_id)
        query = query.filter(LinkStatus.mw_status == status_lower)

    links = query.all()
    exported = [serialize_link(link) for link in links]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Link ID", "Leg", "Site A", "Site B", "LEG Util %", "LEG Bitrate Mbps", "MW IP", "Equipment A", "Equipment B", "Link Type", "Status", "Latency ms", "Direct LEG Util %", "MW Util %", "MW/LEG %", "Link Cap Mbps", "Last Ping"])

    for link in exported:
        writer.writerow([
            link["link_id"],
            link["leg_name"],
            link["site_a"],
            link["site_b"],
            link["leg_util_pct"] if link["leg_util_pct"] is not None else '',
            link["leg_bitrate"] if link["leg_bitrate"] is not None else '',
            link["mw_ip"],
            link["equipment_a"],
            link["equipment_b"],
            link["link_type"],
            link["status"],
            link["latency_ms"] if link["latency_ms"] is not None else '',
            link["latest_metric"]["leg_util_pct"] if link["latest_metric"] else '',
            link["latest_metric"]["mw_util_pct"] if link["latest_metric"] else '',
            link["leg_capacity_pct"] if link["leg_capacity_pct"] is not None else '',
            link["latest_metric"]["mw_capacity_mbps"] if link["latest_metric"] else '',
            link["latest_ping"]["timestamp"] if link["latest_ping"] else ''
        ])

    return Response(output.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename="active_link_inventory.csv"'
    })

@links_bp.route('', methods=['POST'])
@login_required
@require_permission('links.add')
def create_link():
    data = request.get_json()
    if not data or not data.get('link_id') or not data.get('leg_name') or not data.get('mw_ip'):
        return jsonify({"error": "Missing required fields: link_id, leg_name, mw_ip"}), 400
    
    if not validate_ipv4(data['mw_ip']):
        return jsonify({"error": "Invalid IPv4 address format"}), 400

    existing = Link.query.filter_by(link_id=data['link_id']).first()
    if existing:
        return jsonify({"error": f"Link ID {data['link_id']} already exists"}), 409

    link = Link(
        link_id=data['link_id'],
        leg_name=data['leg_name'],
        site_a=data.get('site_a'),
        site_b=data.get('site_b'),
        mw_ip=data['mw_ip'],
        equipment_a=data.get('equipment_a'),
        equipment_b=data.get('equipment_b'),
        link_type=data.get('link_type', 'microwave'),
        notes=data.get('notes'),
        is_active=True
    )
    db.session.add(link)
    db.session.commit()
    
    # Fetch initial data from external DB
    try:
        refresh_external_utilization_for_single_link(link)
        db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to fetch initial external status for {link.link_id}: {e}")

    return jsonify(serialize_link(link)), 201

def _resolve_external_capacity(row):
    capacity = row.get('XPIC_MW_Link_Capacity')
    if capacity is None:
        capacity = row.get('MW_Link_Capacity')
    return capacity


def _persist_external_link_metrics(link, row):
    if row.get('Source_NE_Card'):
        link.site_a = row.get('Source_NE_Card')
    if row.get('Sink_NE_Card'):
        link.site_b = row.get('Sink_NE_Card')

    status = LinkStatus.query.filter_by(link_id=link.id).first()
    if not status:
        status = LinkStatus(link_id=link.id)
        db.session.add(status)
        
    status.mw_util_pct = row.get('AVG_MAX_Util_RxTx_perc')
    status.mw_capacity_mbps = _resolve_external_capacity(row)
    status.metric_source = 'external'
    status.last_metric_at = datetime.utcnow()

    link.updated_at = datetime.utcnow()
    db.session.commit()

@links_bp.route('/lookup', methods=['POST'])
@login_required
@require_permission('links.view')
def lookup_external_link():
    data = request.get_json() or {}
    link_id = data.get('link_id', '').strip()
    if not link_id:
        return jsonify({'error': 'Missing required field: link_id'}), 400

    try:
        row = lookup_link_info(link_id)
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        return jsonify({'error': f'External lookup failed: {exc}'}), 500

    if not row:
        return jsonify({'error': 'Link not found in external utilization database'}), 404

    link = Link.query.filter_by(link_id=link_id).first()
    if link:
        try:
            _persist_external_link_metrics(link, row)
        except Exception:
            db.session.rollback()

    return jsonify({'external': row}), 200

@links_bp.route('/lookup-leg', methods=['POST'])
@login_required
@require_permission('links.view')
def lookup_external_leg():
    data = request.get_json() or {}
    leg_name = data.get('leg_name', '').strip()
    if not leg_name:
        return jsonify({'error': 'Missing required field: leg_name'}), 400

    try:
        row = lookup_leg_info(leg_name)
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        return jsonify({'error': f'External lookup failed: {exc}'}), 500

    if not row:
        return jsonify({'error': 'LEG not found in external utilization database'}), 404

    try:
        links = Link.query.filter_by(leg_name=row.get('LEG_Name')).all()
        for link in links:
            status = LinkStatus.query.filter_by(link_id=link.id).first()
            if not status:
                status = LinkStatus(link_id=link.id)
                db.session.add(status)
            status.avg_max_mbitrate = row.get('AVG_MAX_MBitRate')
            status.interface_speed_min = row.get('Interface_Speed_Min')
            status.interface_speed_max = row.get('Interface_Speed_Max')
            status.sub_leg_count = row.get('Sub_LEG_Count')
            status.leg_source = 'external'
            
            if status.interface_speed_max:
                try:
                    status.leg_capacity_mbps = float(status.interface_speed_max)
                    status.leg_util_pct = round((float(status.avg_max_mbitrate or 0) / float(status.interface_speed_max)) * 100, 1)
                except (TypeError, ValueError, ZeroDivisionError):
                    pass
            
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'external': row}), 200

@links_bp.route('/<int:id>', methods=['GET'])
@login_required
@require_permission('links.view')
def get_link(id):
    link = db.session.get(Link, id)
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    serialized = serialize_link(link)
    
    ping_history = PingResult.query.filter_by(link_id=id).order_by(PingResult.timestamp.desc()).limit(1440).all()
    
    return jsonify({
        "link": serialized,
        "ping_history": [{
            "timestamp": p.timestamp.isoformat() + "Z",
            "reachable": p.reachable,
            "latency_ms": p.latency_ms,
            "packet_loss": p.packet_loss
        } for p in ping_history],
        "metric_history": []
    }), 200

@links_bp.route('/<int:id>', methods=['PUT'])
@login_required
@require_permission('links.edit')
def update_link(id):
    link = db.session.get(Link, id)
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    data = request.get_json()
    
    if 'link_id' in data:
        if data['link_id'] != link.link_id and Link.query.filter_by(link_id=data['link_id']).first():
            return jsonify({"error": f"Link ID {data['link_id']} already exists"}), 409
        link.link_id = data['link_id']

    if 'mw_ip' in data:
        if not validate_ipv4(data['mw_ip']):
            return jsonify({"error": "Invalid IPv4 address format"}), 400
        link.mw_ip = data['mw_ip']

    if 'leg_name' in data: link.leg_name = data['leg_name']
    if 'site_a' in data: link.site_a = data['site_a']
    if 'site_b' in data: link.site_b = data['site_b']
    if 'equipment_a' in data: link.equipment_a = data['equipment_a']
    if 'equipment_b' in data: link.equipment_b = data['equipment_b']
    if 'link_type' in data: link.link_type = data['link_type']
    if 'notes' in data: link.notes = data['notes']

    db.session.commit()

    # Refresh data from external DB in case link_id or leg_name changed
    try:
        refresh_external_utilization_for_single_link(link)
        db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to refresh external status for {link.link_id}: {e}")

    return jsonify(serialize_link(link)), 200

@links_bp.route('/<int:id>', methods=['DELETE'])
@login_required
@require_permission('links.delete')
def delete_link(id):
    link = db.session.get(Link, id)
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    link_id = link.link_id
    db.session.delete(link)
    db.session.commit()
    return jsonify({"message": "Link deleted", "link_id": link_id}), 200

@links_bp.route('/<int:id>/ping', methods=['POST'])
@login_required
@require_permission('links.ping')
def manual_ping(id):
    link = db.session.get(Link, id)
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    try:
        result = ping_single_link(link)
        return jsonify({
            "reachable": result.reachable,
            "latency_ms": result.latency_ms,
            "packet_loss": result.packet_loss,
            "timestamp": result.timestamp.isoformat() + "Z"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@links_bp.route('/legs', methods=['GET'])
@login_required
@require_permission('links.view')
def list_legs():
    legs = db.session.query(Link.leg_name).distinct().order_by(Link.leg_name).all()
    return jsonify({'legs': [row[0] for row in legs]}), 200


@links_bp.route('/<int:id>/metrics', methods=['POST'])
@login_required
@require_permission('links.edit')
def submit_metric(id):
    link = db.session.get(Link, id)
    if not link:
        return jsonify({'error': 'Link not found'}), 404

    data = request.get_json() or {}

    status = LinkStatus.query.filter_by(link_id=link.id).first()
    if not status:
        status = LinkStatus(link_id=link.id)
        db.session.add(status)
        
    status.leg_util_pct = data.get('leg_util_pct', data.get('fiber_util_pct', status.leg_util_pct))
    status.leg_capacity_mbps = data.get('leg_capacity_mbps', data.get('fiber_capacity_mbps', status.leg_capacity_mbps))
    status.mw_util_pct = data.get('mw_util_pct', status.mw_util_pct)
    status.mw_capacity_mbps = data.get('mw_capacity_mbps', status.mw_capacity_mbps)
    status.metric_source = data.get('source', 'manual')
    status.last_metric_at = datetime.utcnow()

    settings = db.session.get(AppSettings, 1)
    warn_pct = settings.util_warning_threshold_pct if settings else 70.0
    crit_pct = settings.util_critical_threshold_pct if settings else 90.0

    mw_util = data.get('mw_util_pct')
    if mw_util is not None:
        if mw_util >= crit_pct:
            send_event_notification('mw_util_high', f'Link {link.link_id} MW utilization at {mw_util:.1f}% (critical)', link_id=link.link_id, severity='critical')
        elif mw_util >= warn_pct:
            send_event_notification('mw_util_high', f'Link {link.link_id} MW utilization at {mw_util:.1f}% (warning)', link_id=link.link_id, severity='warning')

    leg_util = data.get('leg_util_pct', data.get('fiber_util_pct'))
    if leg_util is not None:
        if leg_util >= crit_pct:
            send_event_notification('leg_util_near_cap', f'Link {link.link_id} leg utilization at {leg_util:.1f}% (near capacity)', link_id=link.link_id, severity='critical')
        elif leg_util >= warn_pct:
            send_event_notification('leg_util_high', f'Link {link.link_id} leg utilization at {leg_util:.1f}% (warning)', link_id=link.link_id, severity='warning')

    db.session.commit()
    return jsonify({'result': 'metric recorded'}), 201
