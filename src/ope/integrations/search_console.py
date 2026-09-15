from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .. import USER_AGENT

MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # bound provider payloads like the audit path

# Search Console reports lag ~2-3 days; query a recent, fully-populated window.
_LOOKBACK_DAYS = 28
_REPORTING_LAG_DAYS = 3
_ROW_LIMIT = 100


@dataclass(frozen=True)
class SearchConsoleConfig:
    api_key: str
    site_url: str = ""
    base_url: str = "https://searchconsole.googleapis.com/webmasters/v3"
    timeout: int = 45

    @classmethod
    def from_env(cls) -> "SearchConsoleConfig | None":
        api_key = os.getenv("OPE_SEARCH_CONSOLE_KEY", "").strip()
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            site_url=os.getenv("OPE_SEARCH_CONSOLE_SITE", "").strip(),
            base_url=os.getenv("OPE_SEARCH_CONSOLE_BASE_URL", cls.base_url).rstrip("/"),
        )


class SearchConsoleError(RuntimeError):
    pass


def _property_for(url: str, configured_site: str) -> str:
    """Resolve the Search Console property to query.

    An explicit ``OPE_SEARCH_CONSOLE_SITE`` (URL-prefix or ``sc-domain:``
    property) wins; otherwise the audited origin is used as a URL-prefix
    property, which is how most sites register in Search Console.
    """
    if configured_site:
        return configured_site
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return url


class SearchConsoleClient:
    """Minimal stdlib-only Google Search Console Search Analytics client.

    ``OPE_SEARCH_CONSOLE_KEY`` is an OAuth2 access token for the Search
    Console API, sent as a bearer credential and never included in reports,
    exceptions, or repository configuration. Any failure raises
    :class:`SearchConsoleError` rather than returning a guessed value, so
    evidence-binding code records an explicit UNKNOWN instead of fabricating
    query visibility.
    """

    def __init__(self, config: SearchConsoleConfig | None = None) -> None:
        resolved = config or SearchConsoleConfig.from_env()
        if resolved is None:
            raise SearchConsoleError("OPE_SEARCH_CONSOLE_KEY is not configured")
        self.config: SearchConsoleConfig = resolved

    def query_analytics(self, url: str) -> dict[str, Any]:
        site = _property_for(url, self.config.site_url)
        end = date.today() - timedelta(days=_REPORTING_LAG_DAYS)
        start = end - timedelta(days=_LOOKBACK_DAYS)
        payload = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query"],
            "rowLimit": _ROW_LIMIT,
        }
        endpoint = f"{self.config.base_url}/sites/{urllib.parse.quote(site, safe='')}/searchAnalytics/query"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, min(self.config.timeout, 60))) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise SearchConsoleError(
                        f"Search Console response exceeds {MAX_RESPONSE_BYTES}-byte safety limit"
                    )
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise SearchConsoleError(f"Search Console HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SearchConsoleError(f"Search Console request failed: {exc.reason}") from exc
        try:
            payload_out = json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise SearchConsoleError("Search Console returned an invalid JSON response") from exc
        if not isinstance(payload_out, dict):
            raise SearchConsoleError("Search Console response JSON must be an object")
        return payload_out


def extract_query_visibility(payload: dict[str, Any]) -> dict[str, Any]:
    """Aggregate a Search Analytics response into deterministic visibility metrics.

    Sums real impressions/clicks across the returned query rows and records
    how many distinct queries the property surfaced for. Missing or malformed
    rows contribute nothing (never a fabricated figure).
    """
    rows = payload.get("rows") if isinstance(payload, dict) else None
    rows = rows if isinstance(rows, list) else []
    total_impressions = 0
    total_clicks = 0
    top_queries: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        impressions = row.get("impressions")
        clicks = row.get("clicks")
        if isinstance(impressions, (int, float)):
            total_impressions += int(impressions)
        if isinstance(clicks, (int, float)):
            total_clicks += int(clicks)
        keys = row.get("keys")
        if isinstance(keys, list) and keys and len(top_queries) < 10:
            top_queries.append({
                "query": str(keys[0]),
                "impressions": int(impressions) if isinstance(impressions, (int, float)) else 0,
                "clicks": int(clicks) if isinstance(clicks, (int, float)) else 0,
            })
    return {
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "distinct_queries": len(rows),
        "top_queries": top_queries,
    }


def fetch_query_visibility(url: str, client: SearchConsoleClient | None = None) -> dict[str, Any] | None:
    """Fetch aggregated query visibility, or None if Search Console is not usable.

    Returns None (never fabricated metrics) when no API key is configured or
    the request/parse fails for any reason.
    """
    active_client = client
    if active_client is None:
        config = SearchConsoleConfig.from_env()
        if config is None:
            return None
        active_client = SearchConsoleClient(config)
    try:
        payload = active_client.query_analytics(url)
    except SearchConsoleError:
        return None
    return extract_query_visibility(payload)
