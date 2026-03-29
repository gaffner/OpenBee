import paramiko


class SSHConnector:
    """Connect to a remote host via SSH and execute commands."""

    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )

    def run_cmd(self, command: str) -> dict:
        """Run a shell command. Returns dict with stdout, stderr, exit_code."""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
        exit_code = stdout.channel.recv_exit_status()
        return {
            "stdout": stdout.read().decode("utf-8", errors="replace"),
            "stderr": stderr.read().decode("utf-8", errors="replace"),
            "exit_code": exit_code,
        }

    def run_cmd_stream(self, command: str):
        """Run a command and yield (type, chunk) as output arrives.
        Yields: ('stdout', text), ('stderr', text)
        Final yield: ('exit', exit_code)
        """
        stdin, stdout, stderr = self.client.exec_command(command, timeout=120)
        channel = stdout.channel
        channel.setblocking(0)

        import select
        while not channel.exit_status_ready() or channel.recv_ready() or channel.recv_stderr_ready():
            readable, _, _ = select.select([channel], [], [], 0.1)
            if channel.recv_ready():
                chunk = channel.recv(4096).decode("utf-8", errors="replace")
                if chunk:
                    yield ("stdout", chunk)
            if channel.recv_stderr_ready():
                chunk = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                if chunk:
                    yield ("stderr", chunk)

        # Drain remaining data
        while channel.recv_ready():
            chunk = channel.recv(4096).decode("utf-8", errors="replace")
            if chunk:
                yield ("stdout", chunk)
        while channel.recv_stderr_ready():
            chunk = channel.recv_stderr(4096).decode("utf-8", errors="replace")
            if chunk:
                yield ("stderr", chunk)

        yield ("exit", channel.recv_exit_status())

    def fetch_file(self, remote_path: str, local_path: str):
        """Download a file from the remote host via SFTP."""
        sftp = self.client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()

    def close(self):
        self.client.close()
