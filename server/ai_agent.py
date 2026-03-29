"""
AI Agent — receives a user prompt about a remote machine, asks the LLM
what commands to run, executes them, feeds results back, and iterates
until the AI produces a final answer.

Supports three action types:
  - commands:    run shell commands on the remote machine
  - fetch_file:  download a file from the remote machine
  - run_local:   run a Python script locally for parsing/computation
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from openai import OpenAI, AuthenticationError, APIStatusError
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """\
You are an AI assistant integrated into a network discovery and management tool.
You are connected to a remote machine and can execute shell commands on it.

Machine context:
- Host: {hostname}
- OS: {os_name}
- Protocol: {protocol}

Your job is to help the user by answering questions or performing actions on this machine.

You have THREE capabilities:

1. **Run remote commands** — execute shell commands on the remote machine:
   {{"commands": ["command1", "command2"]}}

2. **Fetch a file** — download a file from the remote machine to analyze locally:
   {{"fetch_file": "/path/to/file"}}
   The file content (or a summary for binary files) will be returned to you.

3. **Run local Python** — execute a Python script on the management server for
   parsing, computation, or processing fetched files:
   {{"run_local": "import json\\ndata = ...\\nprint(result)"}}
   Use this for heavy parsing (e.g. parsing .evtx, .log, CSV, binary files).
   The script's stdout will be returned to you.
   When you fetch a file, it is saved at the path given in the result — use
   that path in your run_local script.

RULES:
1. Respond with ONLY a JSON block when you need to perform an action. No extra text.
2. After receiving results, either request another action or give your final answer.
3. When you have enough information, give a clear, helpful answer in plain text (no JSON).
4. For destructive/install actions, just proceed — the user has already authorized the action.
5. Keep commands concise and non-interactive (avoid editors, pagers, prompts).
6. For Windows hosts, use cmd.exe or PowerShell commands. For Linux, use bash.
7. Prefer fetching + local parsing for binary/large files (e.g. .evtx, large logs).
8. You can chain actions: fetch a file, then run_local to parse it, then answer.
9. For run_local Python scripts, always print() your results to stdout.
"""

MAX_ITERATIONS = 10

# Per-session conversation history: session_id → list of messages
_chat_history: dict[int, list[dict]] = {}


def get_history(session_id: int) -> list[dict]:
    return _chat_history.setdefault(session_id, [])


class AIAgent:
    def __init__(self):
        self.token = self._get_token()
        self.base_url = os.getenv("AI_BASE_URL", "https://models.inference.ai.azure.com")
        self.model = os.getenv("AI_MODEL", "gpt-4o")
        self.client = OpenAI(api_key=self.token, base_url=self.base_url)

    def _get_token(self) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError("No GITHUB_TOKEN and 'gh auth token' failed.") from e

    def _refresh_token(self):
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True, text=True, check=True,
            )
            self.token = result.stdout.strip()
            self.client = OpenAI(api_key=self.token, base_url=self.base_url)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    def _chat(self, messages: list[dict]) -> str:
        def _do():
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.3,
            )
            return resp.choices[0].message.content

        try:
            return _do()
        except (AuthenticationError, APIStatusError) as e:
            status = getattr(e, "status_code", None)
            if isinstance(e, AuthenticationError) or status in (401, 403):
                self._refresh_token()
                return _do()
            raise

    def run(self, user_prompt: str, connector, host_info: dict, session_id: int | None = None) -> list[dict]:
        """
        Run the agent loop. Yields step dicts for SSE streaming.
        """
        system = SYSTEM_PROMPT.format(
            hostname=host_info.get("hostname", "unknown"),
            os_name=host_info.get("os_name", "unknown"),
            protocol=host_info.get("protocol", "unknown"),
        )

        history = get_history(session_id) if session_id else []

        messages = [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": user_prompt},
        ]

        for iteration in range(MAX_ITERATIONS):
            yield {"type": "thinking"}

            try:
                response = self._chat(messages)
            except Exception as exc:
                yield {"type": "error", "text": f"AI API error: {exc}"}
                return

            if not response:
                yield {"type": "error", "text": "AI returned empty response"}
                return

            action = self._extract_action(response)

            if action is None:
                # Plain text — final answer
                if session_id is not None:
                    history.append({"role": "user", "content": user_prompt})
                    history.append({"role": "assistant", "content": response})
                yield {"type": "answer", "text": response}
                return

            messages.append({"role": "assistant", "content": response})
            action_type = action["type"]

            # ── Remote commands ──────────────────────────────────────
            if action_type == "commands":
                results_text = []
                for cmd in action["commands"]:
                    yield {"type": "command", "command": cmd}
                    try:
                        stdout_buf, stderr_buf, exit_code = [], [], 0
                        for chunk_type, chunk_data in connector.run_cmd_stream(cmd):
                            if chunk_type == "stdout":
                                stdout_buf.append(chunk_data)
                                yield {"type": "command_output", "stream": "stdout", "text": chunk_data}
                            elif chunk_type == "stderr":
                                stderr_buf.append(chunk_data)
                                yield {"type": "command_output", "stream": "stderr", "text": chunk_data}
                            elif chunk_type == "exit":
                                exit_code = chunk_data
                        yield {"type": "command_done", "command": cmd, "exit_code": exit_code}
                        results_text.append(
                            f"$ {cmd}\n[exit code: {exit_code}]\n"
                            f"stdout:\n{''.join(stdout_buf)}\nstderr:\n{''.join(stderr_buf)}"
                        )
                    except Exception as exc:
                        yield {"type": "command_output", "stream": "stderr", "text": str(exc)}
                        yield {"type": "command_done", "command": cmd, "exit_code": -1}
                        results_text.append(f"$ {cmd}\n[ERROR] {exc}")

                messages.append({
                    "role": "user",
                    "content": "Command results:\n\n" + "\n\n---\n\n".join(results_text),
                })

            # ── Fetch file ───────────────────────────────────────────
            elif action_type == "fetch_file":
                remote_path = action["path"]
                yield {"type": "command", "command": f"fetch: {remote_path}"}
                try:
                    local_path = self._fetch_file(connector, remote_path)
                    # Read content for text files, summarize for binary
                    content = self._read_fetched(local_path, remote_path)
                    yield {"type": "command_output", "stream": "stdout",
                           "text": f"Fetched {remote_path} → {local_path}\n({len(content)} chars)"}
                    yield {"type": "command_done", "command": f"fetch: {remote_path}", "exit_code": 0}
                    messages.append({
                        "role": "user",
                        "content": (
                            f"File fetched from {remote_path}.\n"
                            f"Saved locally at: {local_path}\n"
                            f"Content (first 50000 chars):\n{content[:50000]}"
                        ),
                    })
                except Exception as exc:
                    yield {"type": "command_output", "stream": "stderr", "text": str(exc)}
                    yield {"type": "command_done", "command": f"fetch: {remote_path}", "exit_code": -1}
                    messages.append({
                        "role": "user",
                        "content": f"Failed to fetch {remote_path}: {exc}",
                    })

            # ── Run local Python ─────────────────────────────────────
            elif action_type == "run_local":
                script = action["script"]
                display_cmd = "python (local)"
                yield {"type": "command", "command": display_cmd}
                try:
                    result = self._run_local_python(script)
                    yield {"type": "command_output", "stream": "stdout", "text": result["stdout"]}
                    if result["stderr"]:
                        yield {"type": "command_output", "stream": "stderr", "text": result["stderr"]}
                    yield {"type": "command_done", "command": display_cmd, "exit_code": result["exit_code"]}
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Local Python script result:\n"
                            f"[exit code: {result['exit_code']}]\n"
                            f"stdout:\n{result['stdout']}\n"
                            f"stderr:\n{result['stderr']}"
                        ),
                    })
                except Exception as exc:
                    yield {"type": "command_output", "stream": "stderr", "text": str(exc)}
                    yield {"type": "command_done", "command": display_cmd, "exit_code": -1}
                    messages.append({
                        "role": "user",
                        "content": f"Local Python execution failed: {exc}",
                    })

        yield {"type": "answer", "text": "(Reached maximum iteration limit)"}

    # ── Helpers ──────────────────────────────────────────────────────────

    def _fetch_file(self, connector, remote_path: str) -> str:
        """Download a file from the remote host to a local temp file. Returns local path."""
        suffix = os.path.splitext(remote_path)[1] or ".bin"
        fd, local_path = tempfile.mkstemp(suffix=suffix, prefix="discovery_")
        os.close(fd)
        connector.fetch_file(remote_path, local_path)
        return local_path

    def _read_fetched(self, local_path: str, remote_path: str) -> str:
        """Read a fetched file. Returns text for text files, hex summary for binary."""
        try:
            with open(local_path, "r", encoding="utf-8", errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, ValueError):
            # Binary file — return size info
            size = os.path.getsize(local_path)
            return (
                f"[Binary file: {size} bytes]\n"
                f"Local path: {local_path}\n"
                f"Use run_local with a Python script to parse this file."
            )

    def _run_local_python(self, script: str) -> dict:
        """Run a Python script locally in a subprocess. Returns stdout/stderr/exit_code."""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=120,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }

    def _extract_action(self, text: str) -> dict | None:
        """Parse AI response into an action dict, or None if it's a plain-text answer."""
        data = self._try_parse_json(text)
        if data is None:
            return None

        if "commands" in data and isinstance(data["commands"], list):
            return {"type": "commands", "commands": data["commands"]}
        if "fetch_file" in data:
            return {"type": "fetch_file", "path": data["fetch_file"]}
        if "run_local" in data:
            return {"type": "run_local", "script": data["run_local"]}

        return None

    def _try_parse_json(self, text: str) -> dict | None:
        """Try to extract a JSON object from text (plain or in code block)."""
        stripped = text.strip()
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        return None
