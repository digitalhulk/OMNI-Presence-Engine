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
class PageSpeedConfig:
    api_key: str = ""
    base_url: str = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    timeout: int = 45

    @classmethod
    def from_env(cls) -> "PageSpeedConfig":
        return cls(api_key=os.getenv("OPE_PAGESPEED_API_KEY", "").strip())


class PageSpeedError(RuntimeError):
    pass


class PageSpeedClient:
    """Minimal stdlib-only Google PageSpeed Insights (Lighthouse) client.

    Anonymous requests share Google's low default quota; set
    OPE_PAGESPEED_API_KEY (a free key from Google Cloud Console) for
    reliable use. Any failure raises PageSpeedError rather than
    returning a guessed value, so evidence-binding code can record an
    explicit UNKNOWN instead of fabricating a metric.
    """

    def __init__(self, config: PageSpeedConfig | None = None) -> None:
        self.config = config or PageSpeedConfig.from_env()

    def fetch(self, url: str, *, strategy: str = "mobile") -> dict[str, Any]:
        params = {"url": url, "strategy": strategy, "category": "PERFORMANCE"}
        if self.config.api_key:
            params["key"] = self.config.api_key
        request = urllib.request.Request(
            f"{self.config.base_url}?{urllib.parse.urlencode(params)}",
            headers={"User-Agent": USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, min(self.config.timeout, 60))) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise PageSpeedError(
                        f"PageSpeed response exceeds {MAX_RESPONSE_BYTES}-byte safety limit"
                    )
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise PageSpeedError(f"PageSpeed HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise PageSpeedError(f"PageSpeed request failed: {exc.reason}") from exc
        try:
            payload = json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise PageSpeedError("PageSpeed returned an invalid JSON response") from exc
        if not isinstance(payload, dict):
            raise PageSpeedError("PageSpeed response JSON must be an object")
        return payload


def _numeric(audits: Any, audit_id: str) -> float | None:
    audit = audits.get(audit_id) if isinstance(audits, dict) else None
    value = audit.get("numericValue") if isinstance(audit, dict) else None
    return float(value) if isinstance(value, (int, float)) else None


def extract_vitals(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract deterministic Core Web Vitals from a raw PSI response.

    fcp/lcp/cls/tbt are lab metrics from lighthouseResult.audits. inp is
    real-user field data from loadingExperience and is absent for
    low-traffic origins; absence is reported as None, never guessed.
    """
    lighthouse = payload.get("lighthouseResult") if isinstance(payload, dict) else None
    audits = lighthouse.get("audits") if isinstance(lighthouse, dict) else None
    loading_experience = payload.get("loadingExperience") if isinstance(payload, dict) else None
    metrics = loading_experience.get("metrics") if isinstance(loading_experience, dict) else None
    inp_metric = metrics.get("INTERACTION_TO_NEXT_PAINT") if isinstance(metrics, dict) else None
    percentile = inp_metric.get("percentile") if isinstance(inp_metric, dict) else None
    return {
        "fcp_ms": _numeric(audits, "first-contentful-paint"),
        "lcp_ms": _numeric(audits, "largest-contentful-paint"),
        "cls": _numeric(audits, "cumulative-layout-shift"),
        "tbt_ms": _numeric(audits, "total-blocking-time"),
        "inp_ms": float(percentile) if isinstance(percentile, (int, float)) else None,
    }


def fetch_vitals(url: str, client: PageSpeedClient | None = None) -> dict[str, Any] | None:
    """Fetch and extract Core Web Vitals, or None if PSI is not usable.

    Returns None (never fabricated numbers) when no API key is
    configured or the request/parse fails for any reason.
    """
    active_client = client or PageSpeedClient()
    if not active_client.config.api_key:
        return None
    try:
        payload = active_client.fetch(url)
    except PageSpeedError:
        return None
    return extract_vitals(payload)
