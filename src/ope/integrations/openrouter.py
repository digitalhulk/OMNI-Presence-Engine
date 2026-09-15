from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from typing import Any

try:
    _VERSION = _package_version("omni-presence-engine")
except PackageNotFoundError:  # pragma: no cover - only when running from an uninstalled tree
    _VERSION = "0.0.0"

# Derived from the installed package version — never a hardcoded string that
# drifts out of sync (the same rule the rest of the codebase follows).
USER_AGENT = f"OPE-Reasoning/{_VERSION}"


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "OpenRouterConfig | None":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            model=os.getenv("OPENROUTER_MODEL", cls.model).strip() or cls.model,
            base_url=os.getenv("OPENROUTER_BASE_URL", cls.base_url).rstrip("/"),
        )


class OpenRouterError(RuntimeError):
    pass


MAX_RESPONSE_BYTES = 1_048_576  # 1 MiB — bound the response body to prevent unbounded reads


class OpenRouterClient:
    """Minimal stdlib-only OpenRouter chat client.

    Credentials are read at runtime from environment variables and are never
    included in reports, prompts, exceptions, or repository configuration.
    """

    def __init__(self, config: OpenRouterConfig | None = None) -> None:
        resolved = config or OpenRouterConfig.from_env()
        if resolved is None:
            raise OpenRouterError("OPENROUTER_API_KEY is not configured")
        self.config: OpenRouterConfig = resolved

    def chat_json(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, min(self.config.timeout, 120))) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise OpenRouterError(
                        f"OpenRouter response exceeds {MAX_RESPONSE_BYTES}-byte safety limit"
                    )
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise OpenRouterError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc.reason}") from exc

        try:
            envelope = json.loads(body.decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenRouterError("OpenRouter returned an invalid JSON response") from exc
        if not isinstance(result, dict):
            raise OpenRouterError("OpenRouter response JSON must be an object")
        return result
