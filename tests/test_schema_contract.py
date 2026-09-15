"""Contract tests: the engine's emitted output must conform to the reconciled
schemas in schemas/audit/. These bind the stable evidence-diagnostic-v1 contract
to the YAML docs so the two cannot silently diverge again.

The schemas are declarative YAML with no runtime YAML dependency (the package is
stdlib-only), so the required keys / enums are asserted here as Python constants
AND cross-checked against the schema file text, catching drift in either
direction.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import ope.audit as audit_module
from ope.audit import Response
from ope.engine import normalize_result

_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas" / "audit"
_HTML = b"<html><head><title>t</title></head><body><h1>hi</h1><img src=a.jpg></body></html>"

# The stable contract, mirrored from schemas/audit/*.yaml.
RUN_REQUIRED = ["run_id", "target", "started_at", "engine_contract", "modules", "findings", "summary"]
FINDING_REQUIRED = ["id", "module", "symptom", "severity", "status", "execution_status",
                    "evidence_status", "priority", "confidence", "root_cause", "evidence",
                    "remediation", "validation"]
MODULE_STATUSES = {"PASS", "FAIL", "UNKNOWN", "BLOCKED", "N/A"}
CHECK_STATUSES = {"PASS", "FAIL", "UNKNOWN", "N/A"}
EVIDENCE_STATUS_ENUM = {"OBSERVED", "HYPOTHESIS", "FACT", "ESTIMATE"}
EXECUTION_STATUS_ENUM = {"PASS", "FAIL", "UNKNOWN", "BLOCKED", "N/A"}
SEVERITY_ENUM = {"critical", "high", "medium", "low", "info"}


@pytest.fixture()
def real_result(monkeypatch):
    resp = Response(final_url="http://acme.example/", status=503, headers={"content-type": "text/html"},
                    set_cookies=[], body=_HTML, charset="utf-8", dns_ms=1.0, ttfb_ms=1.0)
    monkeypatch.setattr(audit_module, "_request", lambda url, timeout=15: resp)
    monkeypatch.setattr(audit_module.crawler, "fetch_robots", lambda url, timeout=10: {
        "url": url, "status": 200, "bytes": 0, "ai_crawlers": {}, "blocked_ai_crawlers": [],
        "allowed_ai_crawlers": [], "rule_count": 0, "sitemaps": [], "rules": []})
    monkeypatch.setattr(audit_module, "_tls_profile", lambda url, timeout=10: {})
    monkeypatch.setattr(audit_module, "fetch_vitals", lambda url: None)
    monkeypatch.setattr(audit_module, "fetch_query_visibility", lambda url: None)
    monkeypatch.setattr(audit_module, "fetch_backlinks", lambda url: None)
    return normalize_result(audit_module.audit("http://acme.example/"))


def test_run_has_all_required_fields(real_result):
    for key in RUN_REQUIRED:
        assert key in real_result, f"run contract missing {key}"
    assert real_result["engine_contract"] == "evidence-diagnostic-v1"
    assert isinstance(real_result["target"], str)          # target is a string, not an object
    assert isinstance(real_result["started_at"], (int, float))
    assert isinstance(real_result["modules"], dict)        # modules is a map, not an array


def test_module_results_conform(real_result):
    for num, module in real_result["modules"].items():
        assert module["status"] in MODULE_STATUSES, f"module {num} status {module['status']}"
        assert "findings" in module
        if module["status"] == "BLOCKED":
            assert module.get("score") is None


def test_check_results_conform(real_result):
    for cid, check in real_result["checks"].items():
        assert check["check_id"] == cid
        assert check["status"] in CHECK_STATUSES, f"check {cid} status {check['status']}"


def test_findings_conform(real_result):
    for f in real_result["findings"]:
        for key in FINDING_REQUIRED:
            assert key in f, f"finding {f.get('id')} missing {key}"
        assert f["evidence_status"] in EVIDENCE_STATUS_ENUM
        assert f["execution_status"] in EXECUTION_STATUS_ENUM
        assert f["severity"] in SEVERITY_ENUM
        assert 0.0 <= f["priority"] <= 100.0
        assert 0.0 <= f["confidence"] <= 1.0
        for ev in f["evidence"]:
            assert "source" in ev and "observed_at" in ev


def test_schema_files_document_the_same_contract():
    # Loose binding without a YAML dependency: the schema text must mention every
    # required key, so a schema edit that drops one is caught here too.
    run_text = (_SCHEMA_DIR / "run-v1.yaml").read_text(encoding="utf-8")
    assert "evidence-diagnostic-v1" in run_text
    for key in RUN_REQUIRED:
        assert key in run_text, f"run-v1.yaml no longer documents {key}"
    finding_text = (_SCHEMA_DIR / "finding-v1.yaml").read_text(encoding="utf-8")
    for key in FINDING_REQUIRED:
        assert key in finding_text, f"finding-v1.yaml no longer documents {key}"
    # The dropped-from-contract enum values must not reappear as emitted labels.
    assert "NOT_APPLICABLE" not in run_text  # code uses N/A
