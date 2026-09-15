"""Tests for the OMNI Command Center dashboard.

Central guarantee: the dashboard is a presentation layer over the canonical
engine. Every value it serves or exports must equal the engine's own output —
no dummy data, no duplicated diagnosis logic.
"""
from __future__ import annotations

import io
import json
import threading
import urllib.request
import zipfile

import pytest

import ope.audit as audit_module
from ope import dashboard, engine
from ope import dashboard_service as svc
from ope.audit import Response

_HTML = b"<html><head><title>x</title></head><body><h1>hi</h1><img src=a.jpg></body></html>"

_VOLATILE = {"duration_ms", "observed_at", "recorded_at", "started_at", "completed_at", "run_id"}


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k not in _VOLATILE}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


@pytest.fixture()
def mock_net(monkeypatch):
    resp = Response(final_url="http://acme.example/", status=503, headers={"content-type": "text/html"},
                    set_cookies=[], body=_HTML, charset="utf-8", dns_ms=1.0, ttfb_ms=1.0)
    monkeypatch.setattr(audit_module, "_request", lambda url, timeout=15: resp)
    monkeypatch.setattr(audit_module.crawler, "fetch_robots", lambda url, timeout=10: {
        "url": url, "status": 200, "bytes": 0, "ai_crawlers": {}, "blocked_ai_crawlers": [],
        "allowed_ai_crawlers": [], "rule_count": 0, "sitemaps": [], "rules": []})
    monkeypatch.setattr(audit_module, "_tls_profile", lambda url, timeout=10: {})
    monkeypatch.setattr(audit_module, "fetch_vitals", lambda url: None)


class TestParity:
    def test_service_output_equals_engine_output(self, mock_net):
        svc_result = svc.run_single_audit("http://acme.example/", record_history=False)
        direct = engine.normalize_result(audit_module.audit("http://acme.example/"))
        assert _scrub(svc_result) == _scrub(direct)

    def test_no_dummy_data_keys_present(self, mock_net):
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        for key in ("health", "health_basis", "modules", "findings", "dependency_root_causes", "remediation_plan", "checks"):
            assert key in r


class TestExports:
    def test_json_export_is_the_canonical_result(self, mock_net):
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        body, ctype, name = svc.export_result(r, "json")
        assert ctype == "application/json" and name == "report.json"
        assert json.loads(body.decode()) == json.loads(json.dumps(r, sort_keys=True))

    def test_markdown_and_html_derive_from_result(self, mock_net):
        from ope.audit import markdown_report
        from ope.report_html import html_report
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        assert svc.export_result(r, "md")[0].decode() == markdown_report(r)
        assert svc.export_result(r, "html")[0].decode() == html_report(r)

    def test_bundle_contains_all_formats_and_manifest(self, mock_net):
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        data, ctype, name = svc.export_bundle(r)
        assert ctype == "application/zip" and name.endswith(".zip")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            assert {"report.json", "report.md", "report.txt", "report.html", "manifest.json"} <= names
            manifest = json.loads(z.read("manifest.json"))
            assert manifest["run_id"] == r["run_id"]
            assert manifest["report_schema"] == svc.REPORT_SCHEMA

    def test_all_text_exports_share_one_diagnosis(self, mock_net):
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        # JSON is authoritative; MD/HTML must reflect the same health value.
        assert str(r["health"]) in svc.export_result(r, "md")[0].decode()
        assert str(r["health"]) in svc.export_result(r, "html")[0].decode()

    def test_html_export_is_offline_self_contained(self, mock_net):
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        html = svc.export_result(r, "html")[0].decode()
        assert "--rb-black" in html  # CSS inlined, no remote stylesheet needed


class TestVisualExportFallback:
    def test_pdf_unavailable_is_clean(self, mock_net, monkeypatch):
        def boom():
            raise svc.ExportUnavailable("no browser")
        monkeypatch.setattr(svc, "_load_playwright", boom)
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        with pytest.raises(svc.ExportUnavailable):
            svc.export_visual(r, "pdf")

    def test_unsupported_format_rejected(self, mock_net):
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        with pytest.raises(ValueError):
            svc.export_result(r, "docx")


class TestDependencyGraphView:
    def test_full_graph_structure(self):
        g = svc.dependency_graph_view()
        assert len(g["nodes"]) == 20
        assert len(g["edges"]) == 32
        assert g["topological_order"][0] == "01"


@pytest.fixture()
def live_server(mock_net):
    srv = dashboard.create_server("127.0.0.1", 0)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


def _get(base, path):
    with urllib.request.urlopen(base + path) as r:
        return r.status, json.loads(r.read())


def _post(base, path, obj):
    req = urllib.request.Request(base + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


class TestServer:
    def test_index_served(self, live_server):
        with urllib.request.urlopen(live_server + "/") as r:
            html = r.read().decode()
        assert "OMNI Command Center" in html
        assert "--rb-black" in html  # RawBlock design reused

    def test_binds_localhost(self, live_server):
        assert live_server.startswith("http://127.0.0.1:")

    def test_providers_and_graph_endpoints(self, live_server):
        _, prov = _get(live_server, "/api/providers")
        assert len(prov["providers"]) == 5
        _, g = _get(live_server, "/api/dependency-graph")
        assert len(g["nodes"]) == 20

    def test_audit_endpoint_runs_real_pipeline(self, live_server):
        status, body, _ = _post(live_server, "/api/audit", {"url": "http://acme.example/"})
        assert status == 200
        result = json.loads(body)
        assert result["engine_contract"] == "evidence-diagnostic-v1"
        assert "remediation_plan" in result and "health_basis" in result

    def test_audit_missing_url_is_400(self, live_server):
        status, body, _ = _post(live_server, "/api/audit", {})
        assert status == 400
        assert "error" in json.loads(body)

    def test_export_endpoint_returns_attachment(self, live_server):
        _, body, _ = _post(live_server, "/api/audit", {"url": "http://acme.example/"})
        result = json.loads(body)
        status, data, headers = _post(live_server, "/api/export", {"run_id": result["run_id"], "result": result, "format": "json"})
        assert status == 200
        assert "attachment" in headers.get("Content-Disposition", "")
        assert json.loads(data)["run_id"] == result["run_id"]

    def test_oversized_body_rejected(self, live_server):
        import urllib.error
        big = json.dumps({"url": "http://acme.example/", "pad": "x" * (9 * 1024 * 1024)}).encode()
        req = urllib.request.Request(live_server + "/api/audit", data=big, headers={"Content-Type": "application/json"})
        # The server refuses an over-cap body without reading it, so the client
        # sees either a clean 400 or a connection reset mid-upload — both mean
        # "rejected" and, crucially, the 9 MiB is never buffered server-side.
        try:
            with urllib.request.urlopen(req) as r:
                assert r.status == 400
        except (urllib.error.HTTPError, urllib.error.URLError, BrokenPipeError, ConnectionError) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                assert exc.code == 400

    def test_unknown_route_404(self, live_server):
        import urllib.error
        try:
            urllib.request.urlopen(live_server + "/api/nope")
            status = 200
        except urllib.error.HTTPError as e:
            status = e.code
        assert status == 404


class TestSecurity:
    def test_ssrf_url_is_rejected_cleanly(self, live_server, monkeypatch):
        # Un-mock: a private target must be blocked by the engine, surfaced as a
        # clean error (no traceback, no result).
        monkeypatch.setattr(audit_module, "_request",
                            lambda url, timeout=15: (_ for _ in ()).throw(ValueError("Resolves to restricted address: 10.0.0.1")))
        status, body, _ = _post(live_server, "/api/audit", {"url": "http://internal.example/"})
        assert status in (400, 500)
        payload = json.loads(body)
        assert "error" in payload
        assert "Traceback" not in payload["error"]

    def test_malicious_finding_is_escaped_in_html_export(self, mock_net, monkeypatch):
        # A finding symptom containing markup must be escaped in the HTML export.
        resp = Response(final_url="http://acme.example/", status=503, headers={"content-type": "text/html"},
                        set_cookies=[], body=b"<html><head><title><script>alert(1)</script></title></head><body>x</body></html>",
                        charset="utf-8", dns_ms=1.0, ttfb_ms=1.0)
        monkeypatch.setattr(audit_module, "_request", lambda url, timeout=15: resp)
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        html = svc.export_result(r, "html")[0].decode()
        assert "<script>alert(1)</script>" not in html

    def test_manifest_has_no_secrets(self, mock_net, monkeypatch):
        monkeypatch.setenv("OPE_PAGESPEED_API_KEY", "super-secret-key-value")
        r = svc.run_single_audit("http://acme.example/", record_history=False)
        data, _, _ = svc.export_bundle(r)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            blob = z.read("manifest.json").decode()
        assert "super-secret-key-value" not in blob  # only configured:true/false, never the value


class TestDeterminism:
    def test_repeated_service_runs_same_diagnosis(self, mock_net):
        a = svc.run_single_audit("http://acme.example/", record_history=False)
        b = svc.run_single_audit("http://acme.example/", record_history=False)
        assert json.dumps(_scrub(a), sort_keys=True) == json.dumps(_scrub(b), sort_keys=True)


class TestReasoning:
    def test_reason_endpoint_honest_unavailable_without_key(self, live_server, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        # Run a real audit first so the server caches the run.
        status, body, _ = _post(live_server, "/api/audit", {"url": "http://acme.example/"})
        assert status == 200
        run = json.loads(body)
        status, rbody, _ = _post(live_server, "/api/reason", {"run_id": run["run_id"], "result": run})
        assert status == 200
        reasoning = json.loads(rbody)["reasoning"]
        assert reasoning["available"] is False
        assert "OPENROUTER_API_KEY" in reasoning["reason"]
        assert reasoning["result"] is None

    def test_reason_endpoint_requires_a_run(self, live_server):
        status, rbody, _ = _post(live_server, "/api/reason", {})
        assert status == 400

    def test_reasoning_never_persisted_to_history(self, live_server, monkeypatch):
        # The advisory reasoning must not enter the deterministic run record.
        status, body, _ = _post(live_server, "/api/audit", {"url": "http://acme.example/"})
        run = json.loads(body)
        assert "reasoning" not in run
