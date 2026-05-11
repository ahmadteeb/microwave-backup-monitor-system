import paramiko
import time
import logging

logger = logging.getLogger(__name__)

class SSHService:
    """
    SSH Service for executing commands on remote hosts.
    
    CHANGES:
    - Added execute_command_channel() method for concurrent execution
      Uses exec_command (separate channel per call, thread-safe) instead of shell
      Allows parallel pings without blocking each other
    - Original execCommand() (shell-based) retained for backward compatibility
    """
    
    def __init__(self, host, username, password, port=22, jumpClient=None):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.channel = None
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.shell = None
        if jumpClient is not None:
            transport = jumpClient.get_transport()
            dest_address = (self.host, self.port)
            local_address = ('127.0.0.1', 0)
            self.channel = transport.open_channel('direct-tcpip', dest_address, local_address)

    def connect(self):
        self.client.connect(self.host, username=self.username, password=self.password, port=self.port, sock=self.channel)
        self.shell = self.client.invoke_shell()
        time.sleep(1)
        self.shell.recv(9999)

    def disconnect(self):
        self.client.close()

    def execute_command_channel(self, command, timeout=10):
        """
        Execute a command using exec_channel (not the interactive shell).
        
        Thread-safe: each call opens its own channel, suitable for concurrent execution.
        Paramiko's Transport.exec_channel is thread-safe; invoke_shell is NOT.
        
        Args:
            command: The command to execute
            timeout: Timeout in seconds to wait for command output (default 10)
            
        Returns:
            output: Raw stdout + stderr as string
        """
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            # Read stdout
            output = ""
            try:
                output = stdout.read(1024 * 1024).decode(errors='ignore')  # Max 1MB per command
            except Exception as e:
                logger.warning(f"Failed to read stdout: {e}")
            
            # Read stderr
            try:
                err = stderr.read(1024 * 1024).decode(errors='ignore')
                if err:
                    output += err
            except Exception as e:
                logger.warning(f"Failed to read stderr: {e}")
            
            # Ensure channel is closed
            stdin.close()
            stdout.close()
            stderr.close()
            
            return output
        except Exception as e:
            logger.error(f"execute_command_channel failed: {e}")
            raise

    def execCommand(self, command, printOutput=False):
        """
        Legacy shell-based command execution (backward compatible).
        NOT thread-safe; do not use from concurrent threads.
        
        Args:
            command: The command to execute
            printOutput: If True, print output to stdout as it arrives
            
        Returns:
            output: Raw command output as string
        """
        output = ""
        self.shell.send(command + "\n")
        time.sleep(1)
        while True:
            if self.shell.recv_ready():
                data = self.shell.recv(4096).decode(errors='ignore')
                output += data
                if printOutput:
                    print(data, end='')
                if "---- More ----" in data:
                    self.shell.send(" ")
                    time.sleep(0.2)
                else:
                    break
        return output
