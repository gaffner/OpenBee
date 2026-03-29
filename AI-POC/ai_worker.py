"""
AI Worker - Uses GitHub Copilot token to access AI models via GitHub Models API.

Usage:
    from ai_worker import AIWorker

    worker = AIWorker()
    response = worker.chat("What is the capital of France?")
    print(response)
"""

import os
import subprocess
from openai import OpenAI, AuthenticationError, APIStatusError
from dotenv import load_dotenv

load_dotenv()


class AIWorker:
    """AI Worker that sends prompts via GitHub Models API using your GitHub token."""

    def __init__(self, model: str | None = None):
        self.token = self._get_token()
        self.base_url = os.getenv("AI_BASE_URL", "https://api.githubcopilot.com")
        self.model = model or os.getenv("AI_MODEL", "claude-opus-4.6")
        self.client = OpenAI(
            api_key=self.token,
            base_url=self.base_url,
        )

    def _get_token(self) -> str:
        """Get GitHub token from .env or refresh it via gh CLI."""
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
        return self._refresh_token()

    def _refresh_token(self) -> str:
        """Re-fetch a fresh token from gh CLI and rebuild the client."""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True, text=True, check=True,
            )
            token = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "'gh auth token' failed. Run 'gh auth login' first."
            ) from e
        self.token = token
        self.client = OpenAI(api_key=self.token, base_url=self.base_url)
        print(f"[AIWorker] Token refreshed: {self.token[:10]}...")
        return token

    def _call_with_retry(self, fn):
        """Execute fn(); on auth failure, refresh token and retry once."""
        try:
            return fn()
        except (AuthenticationError, APIStatusError) as e:
            status = getattr(e, 'status_code', None)
            if isinstance(e, AuthenticationError) or status in (401, 403):
                print(f"[AIWorker] Auth error ({e}), refreshing token...")
                self._refresh_token()
                return fn()
            raise

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        """Send a single prompt and return the response text."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        def _do():
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature,
            )
            return resp.choices[0].message.content

        return self._call_with_retry(_do)

    def chat_stream(self, prompt: str, system: str | None = None, temperature: float = 0.7):
        """Send a prompt and yield response chunks as they arrive."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        def _do():
            return self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=temperature, stream=True,
            )

        stream = self._call_with_retry(_do)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_multi(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Send a full conversation (list of {role, content} dicts)."""
        def _do():
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature,
            )
            return resp.choices[0].message.content

        return self._call_with_retry(_do)


# --- Quick test ---
if __name__ == "__main__":
    worker = AIWorker()
    print(f"Model: {worker.model}")
    print(f"Base URL: {worker.base_url}")
    print(f"Token: {worker.token[:10]}...")
    print()

    # Simple chat
    print("=== Simple Chat ===")
    answer = worker.chat("What is 2+2? Reply in one short sentence.")
    print(f"Response: {answer}")
    print()

    # Streaming
    print("=== Streaming ===")
    for chunk in worker.chat_stream("Count from 1 to 5, one number per line."):
        print(chunk, end="", flush=True)
    print()
    print()

    # With system prompt
    print("=== System Prompt ===")
    answer = worker.chat(
        prompt="What can you help me with?",
        system="You are a network device discovery assistant. Reply in 2 sentences max.",
    )
    print(f"Response: {answer}")
    print()

    print("AI Worker POC complete!")
