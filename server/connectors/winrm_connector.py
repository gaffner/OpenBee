import winrm


class WinRMConnector:
    """Connect to a remote Windows host via WinRM and execute commands."""

    def __init__(self, host: str, username: str, password: str, use_ssl: bool = False):
        port = 5986 if use_ssl else 5985
        scheme = "https" if use_ssl else "http"
        self.endpoint = f"{scheme}://{host}:{port}/wsman"
        self.session = winrm.Session(
            self.endpoint,
            auth=(username, password),
            transport="ntlm",
            server_cert_validation="ignore" if use_ssl else "validate",
        )

    def run_cmd(self, command: str) -> dict:
        """Run a cmd.exe command. Returns dict with stdout, stderr, exit_code."""
        result = self.session.run_cmd(command)
        return {
            "stdout": result.std_out.decode("utf-8", errors="replace"),
            "stderr": result.std_err.decode("utf-8", errors="replace"),
            "exit_code": result.status_code,
        }

    def run_cmd_stream(self, command: str):
        """WinRM cannot stream — run and yield all at once."""
        result = self.run_cmd(command)
        if result["stdout"]:
            yield ("stdout", result["stdout"])
        if result["stderr"]:
            yield ("stderr", result["stderr"])
        yield ("exit", result["exit_code"])

    def fetch_file(self, remote_path: str, local_path: str):
        """Download a file from remote Windows host via PowerShell base64 encoding."""
        # Read file as base64 via PowerShell
        script = f'[Convert]::ToBase64String([IO.File]::ReadAllBytes("{remote_path}"))'
        result = self.run_ps(script)
        if result["exit_code"] != 0:
            raise RuntimeError(result["stderr"] or f"Failed to read {remote_path}")
        import base64
        data = base64.b64decode(result["stdout"].strip())
        with open(local_path, "wb") as f:
            f.write(data)

    def run_ps(self, script: str) -> dict:
        """Run a PowerShell script. Returns dict with stdout, stderr, exit_code."""
        result = self.session.run_ps(script)
        return {
            "stdout": result.std_out.decode("utf-8", errors="replace"),
            "stderr": result.std_err.decode("utf-8", errors="replace"),
            "exit_code": result.status_code,
        }
