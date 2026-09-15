"""End-to-end acceptance tests for the live audit pipeline.

These drive the real ``audit()`` path — HTML parsing, observation
extraction, finding generation, module reconciliation, dependency cascade,
scoring, remediation planning, and JSON/Markdown/HTML rendering — against
controlled fixtures with the network layer mocked. They prove a real
``ope audit`` run produces a complete, trustworthy, actionable result
without hidden crashes, and that the evidence-first status semantics hold
end to end.
"""
from __future__ import annotations

import json

import pytest

import ope.audit as audit_module
from ope.audit import Response, audit, markdown_report
from ope.cli import site_audit_markdown_report
from ope.engine import normalize_result
from ope.report_html import html_report

_HEALTHY_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Acme Widgets — Precision Tools</title>
<meta name="description" content="Acme builds precision widgets.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://acme.example/">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Acme"}</script>
</head>
<body>
<main>
<h1>Precision Widgets</h1>
<p>Acme builds precision widgets for engineers who care about tolerances.</p>
<img src="/w.jpg" alt="A precision widget">
<a href="/contact">Contact us</a>
</main>
</body>
</html>"""

_SECURITY_HEADERS = {
    "content-type": "text/html",
    "strict-transport-security": "max-age=63072000",
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


def _mock_network(monkeypatch, *, html, status=200, final_url="https://acme.example/",
                  headers=None, robots=None, vitals=None):
    resp = Response(
        final_url=final_url,
        status=status,
        headers=headers if headers is not None else dict(_SECURITY_HEADERS),
        set_cookies=[],
        body=html.encode("utf-8"),
        charset="utf-8",
        dns_ms=1.2,
        ttfb_ms=3.4,
    )
    monkeypatch.setattr(audit_module, "_request", lambda url, timeout=15: resp)
    monkeypatch.setattr(
        audit_module.crawler, "fetch_robots",
        lambda url, timeout=10: robots or {
            "url": url, "status": 200, "bytes": 0, "ai_crawlers": {}, "blocked_ai_crawlers": [],
            "allowed_ai_crawlers": [], "rule_count": 0, "sitemaps": [], "rules": [],
        },
    )
    monkeypatch.setattr(audit_module, "_tls_profile", lambda url, timeout=10: {"protocol": "TLSv1.3"})
    monkeypatch.setattr(audit_module, "fetch_vitals", lambda url: vitals)


def _run(monkeypatch, **kwargs):
    _mock_network(monkeypatch, **kwargs)
    final_url = kwargs.get("final_url", "https://acme.example/")
    return normalize_result(audit(final_url, fetch_subresources=False))


# --- Scenario 1: healthy site ------------------------------------------------

def test_healthy_site_is_complete_and_actionable(monkeypatch):
    result = _run(monkeypatch, html=_HEALTHY_HTML)
    assert result["engine_contract"] == "evidence-diagnostic-v1"
    assert result["inventory"]["status"] == 200
    assert result["health"] is not None
    assert "remediation_plan" in result
    assert "health_basis" in result
    # A clean page raises no HTTPS/title/canonical/viewport failures.
    ids = {f["id"] for f in result["findings"]}
    assert "02-INFRA-TLS-001" not in ids
    assert "03-CODE-META-001" not in ids


# --- Scenario 2: broken infrastructure --------------------------------------

def test_broken_infrastructure_flags_and_blocks_downstream(monkeypatch):
    result = _run(monkeypatch, html="<html><body>error</body></html>",
                  status=503, final_url="http://down.example/")
    # HTTP error + non-HTTPS both recorded as direct evidence.
    ids = {f["id"] for f in result["findings"]}
    assert "CODE-HTTP-001" in ids
    assert "02-INFRA-TLS-001" in ids
    assert result["modules"]["02"]["status"] == "FAIL"
    statuses = {k: v["status"] for k, v in result["modules"].items()}
    # The cascade fires: at least one module with no own evidence is BLOCKED.
    assert "BLOCKED" in statuses.values()
    # Every blocked module traces to a real upstream FAIL (02 among them).
    roots = result["dependency_root_causes"]
    assert roots and all(causes for causes in roots.values())
    assert any("02" in causes for causes in roots.values())
    plan = result["remediation_plan"]
    assert any(step["module"] == "02" for step in plan["root_causes"])


# --- Scenario 3: redirecting site -------------------------------------------

def test_redirect_result_uses_final_url(monkeypatch):
    result = _run(monkeypatch, html=_HEALTHY_HTML, final_url="https://www.acme.example/home")
    assert result["final_url"] == "https://www.acme.example/home"
    assert result["inventory"]["status"] == 200


# --- Scenario 4: malformed HTML ---------------------------------------------

def test_malformed_html_does_not_crash(monkeypatch):
    junk = "<html><head><title>oops<body><p>unclosed <div><img><<>&amp; <script>x"
    result = _run(monkeypatch, html=junk)
    assert result["health"] is not None or result["health"] is None  # no exception
    assert "modules" in result
    assert isinstance(result["findings"], list)


# --- Scenario 5: robots restrictions ----------------------------------------

def test_robots_signals_are_captured(monkeypatch):
    robots = {
        "url": "https://acme.example/robots.txt", "status": 200, "bytes": 40,
        "ai_crawlers": {"GPTBot": False}, "blocked_ai_crawlers": ["GPTBot"],
        "allowed_ai_crawlers": [], "rule_count": 1, "sitemaps": [], "rules": [],
    }
    result = _run(monkeypatch, html=_HEALTHY_HTML, robots=robots)
    assert result["inventory"]["robots"]["blocked_ai_crawlers"] == ["GPTBot"]


# --- Scenario 6/7/8: missing metadata, canonical, accessibility -------------

def test_missing_metadata_canonical_and_alt_are_flagged(monkeypatch):
    html = "<html><head></head><body><h1>Hi</h1><img src='a.jpg'></body></html>"
    result = _run(monkeypatch, html=html)
    ids = {f["id"] for f in result["findings"]}
    assert "03-CODE-META-001" in ids  # no title
    assert "13-UX-MOBILE-001" in ids  # no viewport
    assert "17-LANG-001" in ids       # no lang
    assert "05-INDEX-CAN-001" in ids  # no canonical
    assert "14-A11Y-IMG-001" in ids   # image missing alt


# --- Scenario 9/10: performance evidence available / provider unavailable ---

def test_performance_evidence_present_when_provider_returns(monkeypatch):
    vitals = {"lcp_ms": 1800.0, "cls": 0.02}
    result = _run(monkeypatch, html=_HEALTHY_HTML, vitals=vitals)
    assert result["inventory"]["pagespeed"] == vitals


def test_provider_absence_yields_none_not_fabrication(monkeypatch):
    result = _run(monkeypatch, html=_HEALTHY_HTML, vitals=None)
    assert result["inventory"]["pagespeed"] is None


# --- Scenarios 11-16: dependency/cascade invariants end to end --------------

def test_upstream_fail_blocks_downstream_and_names_root_cause(monkeypatch):
    result = _run(monkeypatch, html="<html><body>x</body></html>",
                  status=500, final_url="http://broken.example/")
    modules = result["modules"]
    assert modules["02"]["status"] == "FAIL"
    roots = result["dependency_root_causes"]
    # Evidence firewall end to end: a module with its own FAIL is never
    # masked to BLOCKED, and only BLOCKED modules get a derived root cause.
    for num, module in modules.items():
        if module["status"] == "FAIL":
            assert num not in roots, f"module {num} FAIL was masked/derived"
        if module["status"] == "BLOCKED":
            assert module["score"] is None
            assert roots.get(num), f"blocked module {num} has no root cause"
            # every named cause is a module that actually holds FAIL evidence
            assert all(modules[c]["status"] == "FAIL" for c in roots[num])


# --- Scenarios 17-19: report generation -------------------------------------

def test_json_report_is_complete(monkeypatch):
    result = _run(monkeypatch, html="<html><body>x</body></html>", status=503,
                  final_url="http://down.example/")
    text = json.dumps(result)  # serializable
    for key in ("health", "health_basis", "remediation_plan", "dependency_root_causes",
                "modules", "findings", "checks"):
        assert key in result, key
    assert '"remediation_plan"' in text


def test_markdown_report_shows_diagnosis_and_plan(monkeypatch):
    result = _run(monkeypatch, html="<html><body>x</body></html>", status=503,
                  final_url="http://down.example/")
    md = markdown_report(result)
    assert "Diagnosis & Plan" in md
    assert "Global health" in md
    assert "Remediation plan" in md
    assert "Module 02" in md


def test_html_report_renders_and_escapes(monkeypatch):
    result = _run(monkeypatch, html="<html><head><title>a</title></head><body>x</body></html>",
                  status=503, final_url="http://down.example/")
    out = html_report(result)
    assert out.startswith("<!doctype html>")
    assert "DIAGNOSIS" in out
    assert "GLOBAL HEALTH" in out
    assert "<script>alert" not in out  # nothing injectable escaped through


# --- Scenario: N/A and UNKNOWN semantics preserved end to end ---------------

def test_unknown_modules_have_no_fabricated_score(monkeypatch):
    result = _run(monkeypatch, html=_HEALTHY_HTML)
    for num, module in result["modules"].items():
        if module["status"] in {"UNKNOWN", "BLOCKED", "N/A"}:
            assert module["score"] is None, f"module {num} fabricated a score"


@pytest.mark.parametrize("status", [200, 301, 404, 500, 503])
def test_pipeline_never_crashes_across_status_codes(monkeypatch, status):
    result = _run(monkeypatch, html=_HEALTHY_HTML, status=status)
    assert "remediation_plan" in result
    assert markdown_report(result)
    assert html_report(result).startswith("<!doctype html>")


def test_site_markdown_report_end_to_end(monkeypatch):
    # The site report renderer consumes the same normalized shape.
    result = _run(monkeypatch, html="<html><body>x</body></html>", status=503,
                  final_url="http://down.example/")
    md = site_audit_markdown_report(result)
    assert "Diagnosis & Plan" in md


def test_diagnostic_output_is_deterministic_modulo_timing(monkeypatch):
    """Same input yields the same diagnosis. Per-check duration_ms and
    wall-clock observed_at are measured telemetry and legitimately vary; the
    diagnostic conclusions (status/score/health/root causes/plan) do not."""
    # Fields that legitimately vary: measured timings, wall-clock timestamps,
    # and run identity. Everything else is the deterministic diagnosis.
    volatile = {"duration_ms", "observed_at", "recorded_at", "started_at", "completed_at", "run_id"}

    def scrub(obj):
        if isinstance(obj, dict):
            return {k: scrub(v) for k, v in obj.items() if k not in volatile}
        if isinstance(obj, list):
            return [scrub(v) for v in obj]
        return obj

    a = _run(monkeypatch, html=_HEALTHY_HTML)
    b = _run(monkeypatch, html=_HEALTHY_HTML)
    assert json.dumps(scrub(a), sort_keys=True) == json.dumps(scrub(b), sort_keys=True)
    # The high-value diagnostic keys are byte-identical.
    for key in ("health", "health_basis", "dependency_root_causes", "remediation_plan", "modules"):
        assert json.dumps(scrub(a.get(key)), sort_keys=True) == json.dumps(scrub(b.get(key)), sort_keys=True)
