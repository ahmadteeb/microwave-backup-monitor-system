import paramiko
import time

class SSHService:
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

    def execCommand(self, command, printOutput=False):
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
