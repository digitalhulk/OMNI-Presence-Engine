from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .. import USER_AGENT

MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # bound provider payloads like the audit path


@dataclass(frozen=True)
class BacklinkConfig:
    api_key: str
    # Defaults target the Ahrefs v3 backlinks-stats endpoint; override the base
    # URL to point at a Moz/other compatible index that returns the same shape.
    base_url: str = "https://api.ahrefs.com/v3/site-explorer/backlinks-stats"
    target: str = ""
    timeout: int = 45

    @classmethod
    def from_env(cls) -> "BacklinkConfig | None":
        api_key = os.getenv("OPE_BACKLINK_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPE_BACKLINK_BASE_URL", cls.base_url).rstrip("/"),
            target=os.getenv("OPE_BACKLINK_TARGET", "").strip(),
        )


class BacklinkError(RuntimeError):
    pass


def _target_for(url: str, configured_target: str) -> str:
    """Resolve the target to query the backlink index for.

    An explicit ``OPE_BACKLINK_TARGET`` wins; otherwise the audited host is
    used (off-site authority is a domain-level property, not a page-level one).
    """
    if configured_target:
        return configured_target
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc or url


class BacklinkClient:
    """Minimal stdlib-only backlink-index client (Ahrefs v3 by default).

    ``OPE_BACKLINK_API_KEY`` is sent as a bearer credential and never included
    in reports, exceptions, or repository configuration. Any failure raises
    :class:`BacklinkError` rather than returning a guessed value, so
    evidence-binding code records an explicit UNKNOWN instead of fabricating
    an authority figure.
    """

    def __init__(self, config: BacklinkConfig | None = None) -> None:
        resolved = config or BacklinkConfig.from_env()
        if resolved is None:
            raise BacklinkError("OPE_BACKLINK_API_KEY is not configured")
        self.config: BacklinkConfig = resolved

    def backlinks_stats(self, url: str) -> dict[str, Any]:
        target = _target_for(url, self.config.target)
        params = {"target": target, "mode": "domain"}
        request = urllib.request.Request(
            f"{self.config.base_url}?{urllib.parse.urlencode(params)}",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, min(self.config.timeout, 60))) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise BacklinkError(
                        f"Backlink index response exceeds {MAX_RESPONSE_BYTES}-byte safety limit"
                    )
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise BacklinkError(f"Backlink index HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise BacklinkError(f"Backlink index request failed: {exc.reason}") from exc
        try:
            payload = json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise BacklinkError("Backlink index returned an invalid JSON response") from exc
        if not isinstance(payload, dict):
            raise BacklinkError("Backlink index response JSON must be an object")
        return payload


def _first_number(source: dict[str, Any], *names: str) -> int | None:
    for name in names:
        value = source.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return None


def extract_backlink_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull deterministic off-site authority counts from a backlinks-stats response.

    Reads referring-domain and backlink counts from the provider's ``metrics``
    object (Ahrefs v3 shape), falling back to top-level keys for compatible
    indexes. A metric the provider does not report stays ``None`` — never a
    fabricated figure.
    """
    metrics = payload.get("metrics") if isinstance(payload, dict) else None
    source = metrics if isinstance(metrics, dict) else (payload if isinstance(payload, dict) else {})
    referring_domains = _first_number(source, "live_refdomains", "refdomains", "referring_domains")
    backlinks = _first_number(source, "live", "backlinks", "all_time")
    return {
        "referring_domains": referring_domains,
        "backlinks": backlinks,
    }


def fetch_backlinks(url: str, client: BacklinkClient | None = None) -> dict[str, Any] | None:
    """Fetch off-site authority metrics, or None if the index is not usable.

    Returns None (never fabricated metrics) when no API key is configured or
    the request/parse fails for any reason.
    """
    active_client = client
    if active_client is None:
        config = BacklinkConfig.from_env()
        if config is None:
            return None
        active_client = BacklinkClient(config)
    try:
        payload = active_client.backlinks_stats(url)
    except BacklinkError:
        return None
    return extract_backlink_metrics(payload)
