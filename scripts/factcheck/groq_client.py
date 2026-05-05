"""Lightweight Groq API client for factcheck pipeline.

We avoid the official `groq` Python SDK to keep this script dependency-free
(factcheck-v2.py runs from `/usr/bin/env python3` without virtualenv on dev/CI).

API key resolution order:
    1. env GROQ_API_KEY
    2. tokens.json -> "groq" -> "api_key"
    3. tokens.json -> "groq" -> "api_keys"[0]

If no key resolves, calls raise GroqUnavailableError so callers can degrade
gracefully (the pipeline catches this and returns an explicit error rather
than crashing the entire factcheck run).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_TIMEOUT = 60
DEFAULT_TOKENS_PATH = "/Users/antonk/artvision-data/tokens.json"

# Cloudflare in front of api.groq.com blocks default urllib User-Agent
# (returns CF error 1010). A vanilla browser UA passes the WAF check.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class GroqUnavailableError(RuntimeError):
    """Raised when no Groq API key is configured or all keys exhausted."""


class GroqError(RuntimeError):
    """Raised on non-recoverable Groq API errors."""


def resolve_api_keys(tokens_path: str = DEFAULT_TOKENS_PATH) -> list[str]:
    """Return ordered list of Groq API keys (env first, then tokens.json)."""
    keys: list[str] = []
    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        keys.append(env_key)

    tp = Path(tokens_path)
    if tp.is_file():
        try:
            data = json.loads(tp.read_text(encoding="utf-8"))
            groq = data.get("groq", {})
            if isinstance(groq, dict):
                primary = groq.get("api_key", "").strip()
                if primary and primary not in keys:
                    keys.append(primary)
                for k in groq.get("api_keys", []) or []:
                    k = (k or "").strip()
                    if k and k not in keys:
                        keys.append(k)
        except (OSError, ValueError):
            pass

    return keys


class GroqClient:
    """Minimal Groq Chat Completions client (OpenAI-compatible) using stdlib only."""

    def __init__(
        self,
        api_keys: Optional[list[str]] = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        tokens_path: str = DEFAULT_TOKENS_PATH,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_keys = api_keys if api_keys is not None else resolve_api_keys(tokens_path)
        self._key_index = 0

    @property
    def available(self) -> bool:
        return bool(self.api_keys)

    def _next_key(self) -> str:
        if not self.api_keys:
            raise GroqUnavailableError(
                "No Groq API key found (env GROQ_API_KEY or tokens.json -> groq.api_key)."
            )
        key = self.api_keys[self._key_index % len(self.api_keys)]
        return key

    def _rotate_key(self) -> None:
        self._key_index += 1

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format_json: bool = True,
        max_retries: int = 3,
    ) -> str:
        """Send a chat completion. Returns assistant message content (string)."""
        if not self.available:
            raise GroqUnavailableError("Groq API not configured.")

        url = f"{self.base_url}/chat/completions"
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format_json:
            body["response_format"] = {"type": "json_object"}
        payload = json.dumps(body).encode("utf-8")

        last_err: Exception | None = None
        for attempt in range(max_retries):
            api_key = self._next_key()
            req = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                choices = data.get("choices") or []
                if not choices:
                    raise GroqError(f"Empty choices in response: {raw[:200]}")
                content = choices[0].get("message", {}).get("content", "")
                if not isinstance(content, str):
                    raise GroqError(f"Non-string content: {type(content).__name__}")
                return content
            except urllib.error.HTTPError as exc:
                # Rate-limit or auth → rotate key and retry with backoff
                last_err = exc
                if exc.code in (401, 403, 429):
                    self._rotate_key()
                    time.sleep(0.5 * (attempt + 1))
                    continue
                if 500 <= exc.code < 600:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise GroqError(f"HTTP {exc.code}: {exc.reason}") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_err = exc
                time.sleep(0.5 * (attempt + 1))
                continue

        raise GroqError(f"Groq call failed after {max_retries} retries: {last_err}")


def get_default_client() -> GroqClient:
    """Convenience constructor honouring env var GROQ_MODEL."""
    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    return GroqClient(model=model)
