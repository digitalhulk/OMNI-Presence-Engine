"""Real-transport tests for the Search Console and backlink-index adapters.

These exercise the adapters against an actual local HTTP server (not mocks),
so the true urllib request/parse/bounded-read behaviour is verified. Both
adapters are credential-gated and must degrade to ``None`` (never a fabricated
metric) when unconfigured or when the provider errors.
"""
from __future__ import annotations

import http.server
import json
import threading

import pytest

from ope.integrations.backlink_index import (
    MAX_RESPONSE_BYTES,
    BacklinkClient,
    BacklinkConfig,
    extract_backlink_metrics,
    fetch_backlinks,
)
from ope.integrations.search_console import (
    SearchConsoleClient,
    SearchConsoleConfig,
    extract_query_visibility,
    fetch_query_visibility,
)


class _Handler(http.server.BaseHTTPRequestHandler):
    payload: dict = {}
    status: int = 200
    oversize: bool = False

    def log_message(self, *_a):
        pass

    def _respond(self):
        if self.oversize:
            body = b"{\"metrics\":{}}" + b" " * (MAX_RESPONSE_BYTES + 16)
        else:
            body = json.dumps(self.payload).encode("utf-8")
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        self._respond()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        self._respond()


@pytest.fixture()
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield httpd, port
    httpd.shutdown()
    _Handler.status = 200
    _Handler.oversize = False


# --- Search Console adapter ---------------------------------------------------


def test_search_console_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("OPE_SEARCH_CONSOLE_KEY", raising=False)
    assert SearchConsoleConfig.from_env() is None
    assert fetch_query_visibility("https://example.com") is None


def test_search_console_extract_aggregates_rows():
    payload = {"rows": [
        {"keys": ["shoes"], "impressions": 100, "clicks": 12},
        {"keys": ["red shoes"], "impressions": 40, "clicks": 3},
    ]}
    metrics = extract_query_visibility(payload)
    assert metrics["total_impressions"] == 140
    assert metrics["total_clicks"] == 15
    assert metrics["distinct_queries"] == 2
    assert metrics["top_queries"][0]["query"] == "shoes"


def test_search_console_extract_handles_no_rows():
    metrics = extract_query_visibility({})
    assert metrics == {"total_impressions": 0, "total_clicks": 0, "distinct_queries": 0, "top_queries": []}


def test_search_console_real_transport_fetches_metrics(server):
    _, port = server
    _Handler.payload = {"rows": [{"keys": ["q"], "impressions": 55, "clicks": 4}]}
    client = SearchConsoleClient(SearchConsoleConfig(api_key="tok", base_url=f"http://127.0.0.1:{port}"))
    metrics = fetch_query_visibility("https://example.com", client=client)
    assert metrics is not None
    assert metrics["total_impressions"] == 55
    assert metrics["total_clicks"] == 4


def test_search_console_http_error_degrades_to_none(server):
    _, port = server
    _Handler.payload = {"error": "forbidden"}
    _Handler.status = 403
    client = SearchConsoleClient(SearchConsoleConfig(api_key="tok", base_url=f"http://127.0.0.1:{port}"))
    assert fetch_query_visibility("https://example.com", client=client) is None


def test_search_console_oversize_response_degrades_to_none(server):
    _, port = server
    _Handler.oversize = True
    client = SearchConsoleClient(SearchConsoleConfig(api_key="tok", base_url=f"http://127.0.0.1:{port}"))
    assert fetch_query_visibility("https://example.com", client=client) is None


def test_search_console_never_leaks_key_in_property(monkeypatch):
    from ope.integrations import search_console
    prop = search_console._property_for("https://sub.example.com/page?x=1", "")
    assert prop == "https://sub.example.com/"


# --- Backlink-index adapter ---------------------------------------------------


def test_backlink_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("OPE_BACKLINK_API_KEY", raising=False)
    assert BacklinkConfig.from_env() is None
    assert fetch_backlinks("https://example.com") is None


def test_backlink_extract_reads_ahrefs_shape():
    payload = {"metrics": {"live_refdomains": 320, "live": 5400}}
    metrics = extract_backlink_metrics(payload)
    assert metrics["referring_domains"] == 320
    assert metrics["backlinks"] == 5400


def test_backlink_extract_missing_metric_is_none():
    metrics = extract_backlink_metrics({"metrics": {}})
    assert metrics["referring_domains"] is None
    assert metrics["backlinks"] is None


def test_backlink_real_transport_fetches_metrics(server):
    _, port = server
    _Handler.payload = {"metrics": {"live_refdomains": 7, "live": 42}}
    client = BacklinkClient(BacklinkConfig(api_key="tok", base_url=f"http://127.0.0.1:{port}"))
    metrics = fetch_backlinks("https://example.com", client=client)
    assert metrics == {"referring_domains": 7, "backlinks": 42}


def test_backlink_http_error_degrades_to_none(server):
    _, port = server
    _Handler.payload = {"error": "unauthorized"}
    _Handler.status = 401
    client = BacklinkClient(BacklinkConfig(api_key="tok", base_url=f"http://127.0.0.1:{port}"))
    assert fetch_backlinks("https://example.com", client=client) is None


def test_backlink_oversize_response_degrades_to_none(server):
    _, port = server
    _Handler.oversize = True
    client = BacklinkClient(BacklinkConfig(api_key="tok", base_url=f"http://127.0.0.1:{port}"))
    assert fetch_backlinks("https://example.com", client=client) is None


def test_backlink_target_defaults_to_host():
    from ope.integrations import backlink_index
    assert backlink_index._target_for("https://sub.example.com/page", "") == "sub.example.com"
    assert backlink_index._target_for("https://example.com", "custom.com") == "custom.com"
