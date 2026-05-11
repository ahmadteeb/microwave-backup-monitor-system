"""
SSH Session Manager: Persistent SSH connection pooling.

FEATURE:
- Maintains a single persistent SSH connection to the active jump server.
- Automatically reconnects when the connection drops or config changes.
- Thread-safe for concurrent exec_command calls via paramiko's Transport.
- Singleton pattern with lazy initialization.

USAGE:
  from app.services.ssh_session_manager import get_session_manager
  
  # Execute a command (auto-connects if needed)
  output = get_session_manager().execute("ping -c 3 1.2.3.4")
  
  # Force invalidate (e.g., after config change)
  get_session_manager().invalidate()
"""

import paramiko
import threading
import logging
from typing import Optional
from flask import current_app

logger = logging.getLogger(__name__)


class SSHSessionManager:
    """
    Singleton manager for persistent SSH connections to the active jump server.
    Thread-safe. Auto-reconnects on config change or connection loss.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'SSHSessionManager':
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = SSHSessionManager()
        return cls._instance
    
    def __init__(self):
        self._client: Optional[paramiko.SSHClient] = None
        self._client_lock = threading.Lock()
        self._current_config: Optional[tuple] = None  # (host, port, user, pass)
        self._logger = logging.getLogger(__name__)
    
    def _get_db_config(self) -> Optional[tuple]:
        """
        Read active jump server config from DB.
        Returns (host, port, username, password) or None if not configured.
        
        Must be called within a Flask app context.
        """
        try:
            from app.models import JumpServer
            from app.services.crypto_service import decrypt
            
            js = JumpServer.query.filter_by(active=True).first()
            if js:
                password = decrypt(js.password_encrypted) if js.password_encrypted else None
                return (js.host, js.port, js.username, password)
        except Exception as e:
            self._logger.debug(f"Error reading jump server config from DB: {e}")
        
        return None
    
    def _is_connected(self) -> bool:
        """Check if the current client has an active transport."""
        try:
            if self._client is None:
                return False
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False
    
    def _connect(self, config: tuple) -> None:
        """
        Open a fresh SSH connection using the given config tuple.
        
        Args:
            config: (host, port, username, password) tuple
            
        Raises:
            paramiko.AuthenticationException: If credentials are invalid
            paramiko.SSHException: If connection fails
        """
        host, port, username, password = config
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            port=port,
            username=username,
            password=password,
            timeout=15,
            banner_timeout=15
        )
        self._client = client
        self._current_config = config
        self._logger.info(f"SSH session established to {host}:{port}")
    
    def invalidate(self) -> None:
        """
        Force-close the current session.
        Called when jump server config changes or is disabled.
        """
        with self._client_lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = None
            self._current_config = None
            self._logger.info("SSH session invalidated")
    
    def execute(self, command: str, timeout: int = 10) -> str:
        """
        Execute a command on the jump server (thread-safe).
        
        Opens a new exec channel per call (paramiko Transport is thread-safe).
        Automatically reconnects if the session is not alive or config changed.
        
        Args:
            command: The command to execute
            timeout: Timeout in seconds for command execution
            
        Returns:
            stdout as a string (includes stderr if present)
            
        Raises:
            RuntimeError: If no active jump server is configured
            paramiko.SSHException: If connection fails
        """
        with self._client_lock:
            config = self._get_db_config()
            if config is None:
                raise RuntimeError("No active jump server configured")
            
            # Reconnect if config changed or connection dropped
            if not self._is_connected() or config != self._current_config:
                if self._client:
                    try:
                        self._client.close()
                    except Exception:
                        pass
                self._connect(config)
        
        # Execute OUTSIDE the lock (paramiko Transport.exec_command is thread-safe
        # once connected; no need to hold lock during command execution)
        try:
            stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
            output = stdout.read().decode(errors='ignore')
            stderr_out = stderr.read().decode(errors='ignore')
            if stderr_out:
                self._logger.debug(f"SSH stderr: {stderr_out}")
            return output
        except Exception as e:
            # Log and re-raise; caller handles error
            self._logger.error(f"SSH command execution failed: {e}")
            raise


def get_session_manager() -> SSHSessionManager:
    """Convenience function to get the singleton SSHSessionManager instance."""
    return SSHSessionManager.get_instance()
