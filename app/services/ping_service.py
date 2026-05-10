import re
import time
import logging
import platform
import subprocess
from datetime import datetime
from flask import current_app
from app.models import db, Link, PingResult, JumpServer, AppSettings, LinkStatus, MetricSnapshot
from app.services.ssh_service import SSHService
from app.services.notification_service import send_event_notification
from app.routes.jumpserver import decrypt_password

logger = logging.getLogger(__name__)

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

def _get_active_jumpserver_config():
    js = JumpServer.query.filter_by(active=True).first()
    if js:
        return js.host, js.port, js.username, decrypt_password(js.password_encrypted)

    host = current_app.config.get('JUMP_HOST')
    username = current_app.config.get('JUMP_USER')
    password = current_app.config.get('JUMP_PASSWORD')
    port = current_app.config.get('JUMP_PORT', 22)

    if host and username and password:
        return host, port, username, password

    return None


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
        raw_output = e.output or str(e)

    return raw_output


def _get_ping_settings():
    settings = AppSettings.query.get(1)
    return {
        'count': settings.ping_count if settings else current_app.config.get('PING_COUNT', 3),
        'timeout': settings.ping_timeout_seconds if settings else current_app.config.get('PING_TIMEOUT', 2),
        'consecutive_timeout_threshold': settings.consecutive_timeout_alert_threshold if settings else 5,
        'util_warning_threshold_pct': settings.util_warning_threshold_pct if settings else 70.0,
        'util_critical_threshold_pct': settings.util_critical_threshold_pct if settings else 90.0
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
    previous_timeouts = status_record.consecutive_timeouts

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
                link_id=link.id,
                severity='critical'
            )
        elif previous_status == 'down' and new_status == 'up':
            send_event_notification(
                'mw_link_recovered',
                f'Link {link.link_id} has recovered.',
                link_id=link.id,
                severity='info'
            )

    if status_record.consecutive_timeouts >= settings['consecutive_timeout_threshold'] and previous_timeouts < settings['consecutive_timeout_threshold']:
        send_event_notification(
            'consecutive_timeouts',
            f'Link {link.link_id} has {status_record.consecutive_timeouts} consecutive timeouts.',
            link_id=link.id,
            severity='critical'
        )

    return status_record


def _persist_ping_result(link, reachable, latency_ms, packet_loss, raw_output, triggered_by='scheduler', triggered_by_user_id=None):
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
    return result


def ping_single_link(link):
    """Pings a single link using an active jump server or local ping fallback."""
    config = _get_active_jumpserver_config()
    raw_output = ""

    if config:
        host, port, username, password = config
        ssh = SSHService(host, username, password, port)
        try:
            ssh.connect()
        except Exception as e:
            logger.error(f"Failed to connect to jump server: {e}")
            raise Exception("Jump server connection failed")

        settings = _get_ping_settings()
        cmd = f"ping -c {settings['count']} -W {settings['timeout']} {link.mw_ip}"

        try:
            raw_output = ssh.execCommand(cmd)
            reachable, latency_ms, packet_loss = parse_ping_output(raw_output)
        except Exception as e:
            logger.error(f"Ping command failed for {link.mw_ip}: {e}")
            raw_output = str(e)
            send_event_notification(
                'ping_service_error',
                f'Ping command failed for {link.link_id}: {e}',
                link_id=link.id,
                severity='error'
            )
            reachable, latency_ms, packet_loss = False, None, None
        finally:
            ssh.disconnect()
    else:
        raw_output = _run_local_ping(link.mw_ip)
        reachable, latency_ms, packet_loss = parse_ping_output(raw_output)

    result = _persist_ping_result(link, reachable, latency_ms, packet_loss, raw_output, triggered_by='manual')
    db.session.commit()
    return result

def run_ping_cycle():
    """Runs a full ping cycle across all links using a jump server or local ping fallback."""
    config = _get_active_jumpserver_config()
    using_jump_server = bool(config)
    ssh = None

    if using_jump_server:
        host, port, username, password = config
        ssh = SSHService(host, username, password, port)
        try:
            ssh.connect()
        except Exception as e:
            logger.error(f"Ping cycle aborted: Failed to connect to jump server {host}: {e}")
            return

    links = Link.query.all()
    settings = _get_ping_settings()
    cmd_template = "ping -c {count} -W {timeout} {ip}"

    for link in links:
        raw_output = ""
        try:
            if using_jump_server:
                cmd = cmd_template.format(count=settings['count'], timeout=settings['timeout'], ip=link.mw_ip)
                raw_output = ssh.execCommand(cmd)
            else:
                raw_output = _run_local_ping(link.mw_ip)

            reachable, latency_ms, packet_loss = parse_ping_output(raw_output)
            _persist_ping_result(link, reachable, latency_ms, packet_loss, raw_output)
        except Exception as e:
            logger.error(f"Failed to ping link {link.mw_ip}: {e}")
            send_event_notification(
                'ping_service_error',
                f'Ping execution failed for {link.link_id}: {e}',
                link_id=link.id,
                severity='error'
            )
            _persist_ping_result(link, False, None, None, str(e))

    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to commit ping cycle results: {e}")
        db.session.rollback()
    finally:
        if ssh:
            ssh.disconnect()
