"""Tests for the OSV.dev dependency-vulnerability adapter (real local transport)."""
from __future__ import annotations

import http.server
import json
import threading

import pytest

from ope.integrations.osv import (
    OSVClient,
    OSVConfig,
    detect_dependencies,
    scan_dependencies,
    scan_from_env,
)


class _Handler(http.server.BaseHTTPRequestHandler):
    vulns_for: dict = {}          # version -> list of vuln dicts
    status = 200

    def log_message(self, *_a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length)) if length else {}
        version = str(payload.get("version"))
        body = json.dumps({"vulns": self.vulns_for.get(version, [])}).encode()
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass


@pytest.fixture()
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield httpd, port
    httpd.shutdown()
    _Handler.vulns_for = {}
    _Handler.status = 200


# --- detection (local, no network) --------------------------------------------

def test_detects_versioned_cdn_libraries():
    deps = detect_dependencies([
        "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js",
        "https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js",
        "https://unpkg.com/react@17.0.2/umd/react.production.min.js",
    ])
    names = {(d["name"], d["version"]) for d in deps}
    assert ("jquery", "3.6.0") in names
    assert ("vue", "2.6.14") in names
    assert ("react", "17.0.2") in names
    assert all(d["ecosystem"] == "npm" for d in deps)


def test_ignores_unversioned_scripts():
    assert detect_dependencies([
        "https://example.com/app.js",
        "https://cdn.jsdelivr.net/npm/lodash/lodash.js",  # no @version
        "/static/bundle.js",
    ]) == []


# --- OSV scan (real local transport) ------------------------------------------

def test_scan_reports_no_vulnerabilities(server):
    _, port = server
    client = OSVClient(OSVConfig(base_url=f"http://127.0.0.1:{port}"))
    deps = detect_dependencies(["https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"])
    result = scan_dependencies(deps, client=client)
    assert result["checked"] == 1
    assert result["vulnerable"] == []


def test_scan_reports_vulnerabilities(server):
    _, port = server
    _Handler.vulns_for = {"1.7.2": [{"id": "CVE-2020-0001"}, {"id": "GHSA-abcd"}]}
    client = OSVClient(OSVConfig(base_url=f"http://127.0.0.1:{port}"))
    deps = detect_dependencies(["https://cdnjs.cloudflare.com/ajax/libs/jquery/1.7.2/jquery.min.js"])
    result = scan_dependencies(deps, client=client)
    assert result["vulnerable"][0]["name"] == "jquery"
    assert result["vulnerable"][0]["vulnerability_ids"] == ["CVE-2020-0001", "GHSA-abcd"]


def test_scan_none_without_dependencies():
    assert scan_dependencies([]) is None


def test_scan_none_on_provider_error(server):
    _, port = server
    _Handler.status = 500
    client = OSVClient(OSVConfig(base_url=f"http://127.0.0.1:{port}"))
    deps = detect_dependencies(["https://cdnjs.cloudflare.com/ajax/libs/jquery/1.7.2/jquery.min.js"])
    assert scan_dependencies(deps, client=client) is None   # honest UNKNOWN, never a fake clean result


def test_scan_from_env_gated(monkeypatch):
    monkeypatch.delenv("OPE_DEPENDENCY_SCAN", raising=False)
    assert scan_from_env(["https://cdnjs.cloudflare.com/ajax/libs/jquery/1.7.2/jquery.min.js"]) is None
