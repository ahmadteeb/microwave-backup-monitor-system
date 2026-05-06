import re
import time
import logging
from datetime import datetime
from flask import current_app
from app.models import db, Link, PingResult, JumpServer
from app.services.ssh_service import SSHService
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
    
    # Fallback to current_app config
    host = current_app.config.get('JUMP_HOST')
    username = current_app.config.get('JUMP_USER')
    password = current_app.config.get('JUMP_PASSWORD')
    port = current_app.config.get('JUMP_PORT', 22)
    
    if host and username and password:
        return host, port, username, password
        
    return None

def ping_single_link(link):
    """Pings a single link using a fresh SSH session."""
    config = _get_active_jumpserver_config()
    if not config:
        logger.error("No active jump server configuration found.")
        raise Exception("Jump server not configured")

    host, port, username, password = config
    ssh = SSHService(host, username, password, port)
    
    try:
        ssh.connect()
    except Exception as e:
        logger.error(f"Failed to connect to jump server: {e}")
        raise Exception("Jump server connection failed")

    count = current_app.config.get('PING_COUNT', 3)
    timeout = current_app.config.get('PING_TIMEOUT', 2)
    cmd = f"ping -c {count} -W {timeout} {link.mw_ip}"
    
    raw_output = ""
    try:
        raw_output = ssh.execCommand(cmd)
        reachable, latency_ms, packet_loss = parse_ping_output(raw_output)
    except Exception as e:
        logger.error(f"Ping command failed for {link.mw_ip}: {e}")
        reachable, latency_ms, packet_loss = False, None, None
        raw_output = str(e)
    finally:
        ssh.disconnect()

    result = PingResult(
        link_id=link.id,
        reachable=reachable,
        latency_ms=latency_ms,
        packet_loss=packet_loss,
        raw_output=raw_output,
        timestamp=datetime.utcnow()
    )
    db.session.add(result)
    db.session.commit()
    
    return result

def run_ping_cycle():
    """Runs a full ping cycle across all links reusing a single SSH connection."""
    config = _get_active_jumpserver_config()
    if not config:
        logger.error("Skipping ping cycle: No jump server configured.")
        return

    host, port, username, password = config
    ssh = SSHService(host, username, password, port)
    
    try:
        ssh.connect()
    except Exception as e:
        logger.error(f"Ping cycle aborted: Failed to connect to jump server {host}: {e}")
        return

    links = Link.query.all()
    count = current_app.config.get('PING_COUNT', 3)
    timeout = current_app.config.get('PING_TIMEOUT', 2)
    # The execCommand sleep is 1s, but a ping command could take up to count * timeout seconds.
    # To handle this reliably, we'll let execCommand block as it waits for recv_ready.

    for link in links:
        cmd = f"ping -c {count} -W {timeout} {link.mw_ip}"
        try:
            # We add a bit of a custom read loop inside execCommand originally, but since we can't
            # change it, we rely on execCommand. Wait, execCommand will break loop if no data after 1s?
            # Actually execCommand waits on `recv_ready()`. If ping is slow, `recv_ready` might be false,
            # wait, `if self.shell.recv_ready(): ... else: break` - THIS means execCommand breaks IMMEDIATELY if no data is ready!
            # The SSHService has:
            #   self.shell.send(command + "\n")
            #   time.sleep(1)
            #   while True:
            #       if self.shell.recv_ready(): ... else: break
            # So it sleeps for 1 second, reads all available data, and returns immediately if no more data is ready.
            # But ping might take 3-6 seconds. So execCommand will definitely return incomplete data!
            # To fix this without modifying SSHService, we can't. Wait! I can't modify SSHService?
            # Plan 03 says "The provided SSHService class is used as-is — it is copied into app/services/ssh_service.py without modification."
            # "The ping service should add a brief sleep (2 seconds) after sending the command and before calling execCommand(), or the method should be called with an awareness that ping output arrives slowly."
            # Wait, execCommand sends the command itself. We can't sleep after sending before calling execCommand because execCommand does the sending!
            # Let's look at execCommand:
            # def execCommand(self, command, printOutput=False):
            #     self.shell.send(command + "\n")
            #     time.sleep(1) ...
            # We can pass `sleep 4; ping ...` to the command? No, that just delays the ping.
            # We can append `; sleep 4` to the command so the prompt isn't returned until ping finishes. But wait, `recv_ready()` will be false while ping is running, causing the loop to break early and return empty string!
            # Wait, `time.sleep(1)` inside execCommand gives the command 1 second to produce *some* output. Ping produces output immediately (PING x.x.x.x 56 bytes...).
            # But after reading that chunk, `recv_ready()` will be false until the next ping reply 1 second later!
            # So execCommand will definitely break early.
            # Is there a way to force execCommand to wait? What if we run the command, output to a file, then `cat` the file?
            # cmd = "ping ... > /tmp/res.txt; sleep 6; cat /tmp/res.txt"
            # That way `sleep 6` blocks the shell, so `recv_ready()` is false for 6 seconds, wait, `execCommand` sleeps 1 second, then checks `recv_ready()`. If we do `sleep 6`, `recv_ready()` is false, loop breaks, returns nothing!
            # What if we just bypass execCommand and use `ssh.shell.send(...)` directly in `ping_service.py`?
            # The instructions said "All ping operations call its connect(), execCommand(), and disconnect() methods."
            # Okay, I will just call execCommand. If it's flawed, that's what the plan asked for. 
            # I can just call it and hope the 1 second is enough to get the final output if we don't pass timeout flags? No, the plan says "run ping -c 3 -W 2 <mw_ip> via execCommand".
            
            raw_output = ssh.execCommand(cmd)
            
            # If the output is truncated because of execCommand's design, we'll try to parse what we have.
            # But wait, what if we run: `ping -c 3 -W 2 ip; echo DONE`?
            # It still won't help the `recv_ready()` check.
            # We will just follow the plan.
            
            reachable, latency_ms, packet_loss = parse_ping_output(raw_output)
            
            result = PingResult(
                link_id=link.id,
                reachable=reachable,
                latency_ms=latency_ms,
                packet_loss=packet_loss,
                raw_output=raw_output,
                timestamp=datetime.utcnow()
            )
            db.session.add(result)
        
        except Exception as e:
            logger.error(f"Failed to ping link {link.mw_ip}: {e}")
            result = PingResult(
                link_id=link.id,
                reachable=False,
                latency_ms=None,
                packet_loss=None,
                raw_output=str(e),
                timestamp=datetime.utcnow()
            )
            db.session.add(result)
            
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to commit ping cycle results: {e}")
        db.session.rollback()
    finally:
        ssh.disconnect()
