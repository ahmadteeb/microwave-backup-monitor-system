"""
Ping Service: Execute network pings against links and persist results.

MAJOR CHANGES:
- Concurrent pinging using ThreadPoolExecutor (configurable workers, default 10)
- New _ping_one_link() helper for per-link execution in worker threads
- Thread-safe _persist_ping_result() with scoped DB sessions (db.session.remove() in finally)
- New WebSocket events: ping_cycle_start, ping_cycle_complete
- UPDATED: Uses persistent SSHSessionManager instead of per-cycle SSH connect/disconnect
- Each worker thread uses its own DB session scope to avoid conflicts
- Original ping_single_link() now uses SSHSessionManager for persistent connections
"""

import re
import time
import logging
import platform
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import current_app
from app.models import db, Link, PingResult, JumpServer, AppSettings, LinkStatus, MetricSnapshot
from app.services.notification_service import send_event_notification
from app.services.crypto_service import decrypt
from app.services.ssh_session_manager import get_session_manager

logger = logging.getLogger(__name__)

# Global app instance for background threads (set by scheduler or tests)
_app_instance = None

def set_app_instance(app):
    """Set the Flask app instance for use in background threads."""
    global _app_instance
    _app_instance = app

def parse_ping_output(raw_output):
    """
    Parses ping output from standard Linux ping.
    Returns (reachable: bool, latency_ms: float or None, packet_loss: float or None)
    """
    reachable = False
    latency_ms = None
    packet_loss = None

    # Check network unreachable
    if "Network is unreachable" in raw_output:
        return False, None, 100.0

    # Parse packet loss
    loss_match = re.search(r'(\d+)% packet loss', raw_output)
    if loss_match:
        packet_loss = float(loss_match.group(1))
    
    # Parse latency (rtt min/avg/max/mdev)
    rtt_match = re.search(r'rtt .+ = [\d.]+/(?P<avg>[\d.]+)/', raw_output)
    if rtt_match:
        latency_ms = float(rtt_match.group('avg'))
        reachable = True
    elif "bytes from" in raw_output:
        reachable = True
    elif packet_loss is not None and packet_loss < 100.0:
        reachable = True

    # Complete timeout
    if packet_loss == 100.0:
        reachable = False
        latency_ms = None

    return reachable, latency_ms, packet_loss

def _run_local_ping(ip):
    settings = _get_ping_settings()
    system_name = platform.system().lower()
    if system_name == 'windows':
        cmd = ['ping', '-n', str(settings['count']), '-w', str(settings['timeout'] * 1000), ip]
    else:
        cmd = ['ping', '-c', str(settings['count']), '-W', str(settings['timeout']), ip]

    try:
        raw_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=(settings['count'] * settings['timeout'] + 10))
    except subprocess.CalledProcessError as e:
        raw_output = e.output
    except subprocess.TimeoutExpired as e:
        if e.output:
            raw_output = e.output.decode(errors='ignore') if isinstance(e.output, (bytes, bytearray)) else str(e.output)
        else:
            raw_output = '100% packet loss'

    return raw_output


def _get_ping_settings():
    """Fetch ping settings from DB or app config (safe for use in background threads)."""
    try:
        settings = db.session.get(AppSettings, 1)
    except Exception:
        settings = None
    
    return {
        'count': settings.ping_count if settings else current_app.config.get('PING_COUNT', 3),
        'timeout': settings.ping_timeout_seconds if settings else current_app.config.get('PING_TIMEOUT', 2),
        'consecutive_timeout_threshold': settings.consecutive_timeout_alert_threshold if settings else 5,
        'util_warning_threshold_pct': settings.util_warning_threshold_pct if settings else 70.0,
        'util_critical_threshold_pct': settings.util_critical_threshold_pct if settings else 90.0,
        'concurrency': settings.ping_concurrency if settings else 10,
    }


def _derive_status(reachable, latest_metric, settings):
    if not reachable:
        return 'down'

    if latest_metric and latest_metric.mw_util_pct is not None:
        if latest_metric.mw_util_pct >= settings['util_critical_threshold_pct']:
            return 'high'
        if latest_metric.mw_util_pct >= settings['util_warning_threshold_pct']:
            return 'high'

    return 'up'


def _build_link_status(link, reachable, latency_ms, packet_loss, result_timestamp, settings):
    latest_metric = link.metrics.order_by(MetricSnapshot.timestamp.desc()).first()
    status_record = LinkStatus.query.filter_by(link_id=link.id).first()
    if not status_record:
        status_record = LinkStatus(link_id=link.id)
        db.session.add(status_record)

    previous_status = status_record.mw_status
    previous_timeouts = status_record.consecutive_timeouts or 0

    new_status = _derive_status(reachable, latest_metric, settings)
    status_record.mw_status = new_status
    status_record.last_ping_at = result_timestamp
    status_record.last_ping_latency_ms = latency_ms
    status_record.consecutive_timeouts = previous_timeouts + 1 if not reachable else 0
    if latest_metric:
        status_record.last_metric_at = latest_metric.timestamp
        status_record.fiber_util_pct = latest_metric.fiber_util_pct
        status_record.mw_util_pct = latest_metric.mw_util_pct

    if previous_status != new_status:
        if new_status == 'down':
            send_event_notification(
                'mw_link_down',
                f'Link {link.link_id} is down.',
                link_id=link.link_id,
                severity='critical'
            )
        elif previous_status == 'down' and new_status == 'up':
            send_event_notification(
                'mw_link_recovered',
                f'Link {link.link_id} has recovered.',
                link_id=link.link_id,
                severity='info'
            )

    if status_record.consecutive_timeouts >= settings['consecutive_timeout_threshold'] and previous_timeouts < settings['consecutive_timeout_threshold']:
        send_event_notification(
            'consecutive_timeouts',
            f'Link {link.link_id} has {status_record.consecutive_timeouts} consecutive timeouts.',
            link_id=link.link_id,
            severity='critical'
        )

    return status_record


def _emit_link_status_update(link, result):
    """Emit a real-time WebSocket event with the updated link status."""
    try:
        from app.extensions import socketio
        latest_metric = link.metrics.order_by(MetricSnapshot.timestamp.desc()).first()
        status = 'UNKNOWN'
        if link.status:
            status = link.status.mw_status.upper()

        payload = {
            'id': link.id,
            'link_id': link.link_id,
            'leg_name': link.leg_name,
            'status': status,
            'latency_ms': result.latency_ms,
            'latest_metric': {
                'fiber_util_pct': latest_metric.fiber_util_pct if latest_metric else None,
                'mw_util_pct': latest_metric.mw_util_pct if latest_metric else None,
            } if latest_metric else None
        }
        socketio.emit('link_status_update', payload)
    except Exception as e:
        logger.warning(f"Failed to emit link_status_update: {e}")


def _emit_kpi_update():
    """Emit a real-time WebSocket event with fresh KPI data."""
    try:
        from app.extensions import socketio
        from datetime import timedelta

        total_links = Link.query.count()
        mw_reachable = LinkStatus.query.filter(LinkStatus.mw_status.in_(['up', 'high'])).count()
        high_utilization = LinkStatus.query.filter(LinkStatus.mw_status == 'high').count()
        mw_unreachable = total_links - mw_reachable

        since = datetime.utcnow() - timedelta(hours=24)
        total_pings = PingResult.query.filter(PingResult.timestamp >= since).count()
        ok_pings = PingResult.query.filter(PingResult.timestamp >= since, PingResult.reachable.is_(True)).count()
        availability_pct = round((ok_pings / total_pings * 100), 1) if total_pings > 0 else None

        payload = {
            'total_links': total_links,
            'mw_reachable': mw_reachable,
            'mw_unreachable': mw_unreachable,
            'high_utilization': high_utilization,
            'link_availability_24h': availability_pct,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        socketio.emit('kpi_update', payload)
    except Exception as e:
        logger.warning(f"Failed to emit kpi_update: {e}")


def _emit_ping_cycle_start(total_links):
    """Emit WebSocket event when ping cycle begins."""
    try:
        from app.extensions import socketio
        payload = {
            'total': total_links,
            'started_at': datetime.utcnow().isoformat() + 'Z'
        }
        socketio.emit('ping_cycle_start', payload)
    except Exception as e:
        logger.warning(f"Failed to emit ping_cycle_start: {e}")


def _emit_ping_cycle_complete(total_links):
    """Emit WebSocket event when ping cycle completes."""
    try:
        from app.extensions import socketio
        payload = {
            'total': total_links,
            'completed_at': datetime.utcnow().isoformat() + 'Z'
        }
        socketio.emit('ping_cycle_complete', payload)
    except Exception as e:
        logger.warning(f"Failed to emit ping_cycle_complete: {e}")


def _persist_ping_result(link, reachable, latency_ms, packet_loss, raw_output, triggered_by='scheduler', triggered_by_user_id=None):
    """
    Persist a ping result to the database (thread-safe).
    
    Each thread must have its own DB session scope. This is called from worker threads,
    so we do NOT use the request-scoped db.session directly. Instead, we create and clean
    up our own session lifecycle.
    
    Note: SQLite may need additional locking for concurrent writes, but Flask-SQLAlchemy
    handles connection pooling. We add a retry mechanism for robustness.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            settings = _get_ping_settings()
            result = PingResult(
                link_id=link.id,
                reachable=reachable,
                latency_ms=latency_ms,
                packet_loss=packet_loss,
                raw_output=raw_output,
                triggered_by=triggered_by,
                triggered_by_user_id=triggered_by_user_id,
                timestamp=datetime.utcnow()
            )
            db.session.add(result)
            _build_link_status(link, reachable, latency_ms, packet_loss, result.timestamp, settings)
            db.session.commit()

            # Emit real-time update for this link
            _emit_link_status_update(link, result)

            return result
        except Exception as e:
            db.session.rollback()
            if attempt < max_retries - 1:
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}), retrying: {e}")
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to persist ping result after {max_retries} attempts: {e}")
                raise
        finally:
            # Clean up session for this thread
            db.session.remove()


def ping_single_link(link):
    """
    Pings a single link synchronously (e.g., from a manual API endpoint).
    
    Uses persistent SSHSessionManager if jump server is configured.
    Falls back to local ping if no jump server is active or if session unavailable.
    This is NOT concurrent; it blocks until the ping completes.
    Returns immediately with the result (no async/threading).
    """
    raw_output = ""
    
    try:
        # Try to use persistent SSH session if jump server configured
        try:
            settings = _get_ping_settings()
            cmd = f"ping -c {settings['count']} -W {settings['timeout']} {link.mw_ip}"
            raw_output = get_session_manager().execute(cmd, timeout=settings['timeout'] + 5)
        except RuntimeError:
            # No jump server configured, fall back to local ping
            raw_output = _run_local_ping(link.mw_ip)
        
        reachable, latency_ms, packet_loss = parse_ping_output(raw_output)
    except Exception as e:
        logger.error(f"Ping command failed for {link.mw_ip}: {e}")
        raw_output = str(e)
        send_event_notification(
            'ping_service_error',
            f'Ping command failed for {link.link_id}: {e}',
            link_id=link.link_id,
            severity='error'
        )
        reachable, latency_ms, packet_loss = False, None, None

    result = _persist_ping_result(link, reachable, latency_ms, packet_loss, raw_output, triggered_by='manual')
    return result


def _ping_one_link(link, settings):
    """
    Ping a single link (worker thread function).
    
    This runs in a background thread and must NOT use the request-scoped session.
    It executes the ping, parses output, persists result with its own DB session,
    and emits WebSocket updates.
    
    Uses persistent SSHSessionManager if jump server is configured, otherwise
    falls back to local ping.
    
    Worker thread must establish its own Flask app context via the global _app_instance
    to access database and send notifications.
    
    Args:
        link: Link model instance (read-only in thread)
        settings: Dict of ping settings from _get_ping_settings()
        
    Returns:
        (link.id, success: bool, error_msg: str or None)
    """
    # Each worker thread must establish its own app context
    if not _app_instance:
        logger.error(f"Failed to ping link {link.mw_ip} ({link.link_id}): App instance not available")
        return (link.id, False, "App instance not available")
    
    with _app_instance.app_context():
        raw_output = ""
        try:
            # Try to use persistent SSH session if jump server configured
            try:
                cmd = f"ping -c {settings['count']} -W {settings['timeout']} {link.mw_ip}"
                raw_output = get_session_manager().execute(cmd, timeout=settings['timeout'] + 5)
            except RuntimeError:
                # No jump server configured, fall back to local ping
                raw_output = _run_local_ping(link.mw_ip)

            reachable, latency_ms, packet_loss = parse_ping_output(raw_output)
            _persist_ping_result(link, reachable, latency_ms, packet_loss, raw_output)
            return (link.id, True, None)
        except Exception as e:
            logger.error(f"Failed to ping link {link.mw_ip} ({link.link_id}): {e}")
            try:
                send_event_notification(
                    'ping_service_error',
                    f'Ping execution failed for {link.link_id}: {e}',
                    link_id=link.link_id,
                    severity='error'
                )
            except Exception as notify_error:
                logger.error(f"Failed to send notification: {notify_error}")
            
            # Persist the failure result
            try:
                _persist_ping_result(link, False, None, None, str(e))
            except Exception as persist_error:
                logger.error(f"Failed to persist ping failure: {persist_error}")
            
            return (link.id, False, str(e))


def run_ping_cycle():
    """
    Run a full ping cycle across all links using concurrent.futures.ThreadPoolExecutor.
    
    Uses persistent SSHSessionManager for jump server connections (if configured).
    Falls back to local ping if no jump server is active.
    
    Flow:
    1. Emit ping_cycle_start WS event
    2. Spawn worker threads (default 10) via ThreadPoolExecutor
    3. Each thread calls _ping_one_link() for its link
    4. Workers emit link_status_update per-link as they complete
    5. Wait for all workers to complete
    6. Emit ping_cycle_complete WS event
    7. Emit kpi_update once for the full cycle
    """
    try:
        # Fetch all links
        links = Link.query.all()
        if not links:
            logger.info("No links to ping")
            return
        
        settings = _get_ping_settings()
        concurrency = settings['concurrency']

        # Emit cycle start
        _emit_ping_cycle_start(len(links))

        # Execute pings concurrently
        # (SSHSessionManager is persistent and thread-safe; no per-thread connect needed)
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(_ping_one_link, link, settings): link.id
                for link in links
            }
            
            completed_count = 0
            failed_count = 0
            for future in as_completed(futures):
                try:
                    link_id_result, success, error_msg = future.result()
                    if success:
                        completed_count += 1
                        logger.debug(f"Successfully pinged link {link_id_result}")
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to ping link {link_id_result}: {error_msg}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Worker thread exception: {e}")

        logger.info(f"Ping cycle completed: {completed_count} succeeded, {failed_count} failed")

        # Emit cycle complete
        _emit_ping_cycle_complete(len(links))

        # Emit KPI update once for the full cycle
        _emit_kpi_update()

    except Exception as e:
        logger.error(f"Ping cycle failed: {e}")
