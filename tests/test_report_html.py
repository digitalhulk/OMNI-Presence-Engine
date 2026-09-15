from pathlib import Path

from ope.report_html import html_report, load_rawblock_css, write_html_report


def _result(**overrides):
    base = {
        "engine": "ope",
        "version": "0.1.0",
        "run_id": "ope-1",
        "target": "https://example.com",
        "started_at": 1726190400,
        "engine_contract": "evidence-root-cause-v1",
        "inventory": {"status": 200, "title": "Example", "images": 2, "images_missing_alt": 1},
        "modules": {
            "03": {"status": "FAIL", "findings": ["X-1"]},
            "02": {"status": "PASS", "findings": []},
            "01": {"status": "UNKNOWN", "findings": []},
        },
        "summary": {"finding_count": 1, "critical": 0, "high": 0, "medium": 1, "low": 0, "info": 0},
        "findings": [
            {
                "id": "X-1",
                "module": "03-code",
                "symptom": "<script>alert(1)</script> Document has no title",
                "status": "OBSERVED",
                "severity": "medium",
                "priority": 49.0,
                "confidence": 1.0,
                "root_cause": "Template does not render a title.",
                "remediation": ["Add a title."],
                "validation": ["Re-audit."],
                "evidence": [{"source": "html-parser", "target": "https://example.com", "value": {"title": ""}}],
            }
        ],
    }
    base.update(overrides)
    return base


def test_css_loader_finds_design_stylesheet():
    css = load_rawblock_css()
    assert "--rb-black" in css
    assert "Archivo Black" in css
    assert "rb-btn--primary" in css


def test_html_report_renders_rawblock_branding_and_content():
    out = html_report(_result())
    assert "RAW//BLOCK" in out
    assert "https://example.com" in out
    assert "X-1" in out
    assert "rb-btn--primary" in out  # stylesheet inlined
    assert "MODULE 03" in out
    assert "Template does not render a title." in out
    assert "49.0" in out


def test_html_report_escapes_user_content():
    out = html_report(_result())
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


def test_html_report_handles_empty_findings():
    result = _result(findings=[], summary={"finding_count": 0})
    out = html_report(result)
    assert "NO FINDINGS" in out


def test_write_html_report_persists_file(tmp_path: Path):
    target = tmp_path / "nested" / "audit.report.html"
    returned = write_html_report(_result(), target)
    assert returned == target
    text = target.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")
    assert "OMNI-PRESENCE ENGINE" in text


def _diagnosed_result(**overrides):
    modules = {f"{i:02d}": {"status": "BLOCKED", "findings": [], "score": None} for i in range(3, 21)}
    modules["01"] = {"status": "PASS", "findings": [], "score": 100.0}
    modules["02"] = {"status": "FAIL", "findings": ["X-1"], "score": 0.0}
    base = {
        "target": "https://example.com",
        "started_at": 1726190400,
        "inventory": {"status": 503},
        "summary": {"finding_count": 1, "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
        "modules": modules,
        "health": 9.52,
        "dependency_root_causes": {f"{i:02d}": ["02"] for i in range(3, 21)},
        "findings": [{
            "id": "X-1", "module": "02-infrastructure",
            "symptom": "Origin returns 503 <b>down</b>", "severity": "high", "priority": 72.0,
            "root_cause": "Origin down", "remediation": ["Restore origin"], "validation": ["Re-audit"],
            "evidence": [{"source": "http", "target": "https://example.com", "value": {}}],
        }],
    }
    base.update(overrides)
    return base


def test_html_report_surfaces_health_and_plan():
    out = html_report(_diagnosed_result())
    assert "GLOBAL HEALTH" in out
    assert "9.52" in out
    assert "DIAGNOSIS" in out
    assert "ROOT CAUSES" in out
    assert "MODULE 02" in out
    assert "unblocks" in out
    assert "Restore origin" in out
    assert "WAITING" in out  # blocked modules listed


def test_html_report_module_grid_shows_scores():
    out = html_report(_diagnosed_result())
    assert "score 0.0" in out   # module 02 FAIL
    assert "score 100.0" in out  # module 01 PASS


def test_html_report_escapes_plan_content():
    out = html_report(_diagnosed_result())
    assert "<b>down</b>" not in out
    assert "&lt;b&gt;down&lt;/b&gt;" in out


def test_html_report_escapes_malicious_content_in_every_field():
    payload = '"><script>alert(1)</script><img src=x onerror=alert(2)>'
    result = _diagnosed_result(
        target=payload,
        findings=[{
            "id": payload, "module": payload, "symptom": payload, "severity": "high",
            "priority": 72.0, "status": "OBSERVED", "confidence": payload,
            "root_cause": payload, "remediation": [payload], "validation": [payload],
            "evidence": [{"source": payload, "target": payload, "value": {"x": payload}}],
        }],
    )
    out = html_report(result)
    # No raw tag from the payload may appear unescaped anywhere in the document
    # body (the only "<script" tokens are the report's own inline scripts, not
    # the payload's). The payload's angle brackets must be entity-encoded.
    assert "<script>alert(1)</script>" not in out
    assert "<img src=x" not in out       # would be a real injected tag
    assert '"><script' not in out        # attribute-breakout form neutralised
    assert "&lt;script&gt;" in out       # escaped form present


def test_html_report_no_failures_states_no_remediation():
    healthy = {f"{i:02d}": {"status": "PASS", "findings": [], "score": 100.0} for i in range(1, 21)}
    out = html_report(_diagnosed_result(modules=healthy, dependency_root_causes={},
                                        findings=[], health=100.0,
                                        summary={"finding_count": 0}))
    assert "no remediation is required" in out.lower()


def test_html_report_omits_reasoning_when_absent():
    out = html_report(_result())
    assert "AI REASONING" not in out


def test_html_report_renders_available_reasoning():
    result = _result()
    result["reasoning"] = {
        "provider": "openrouter", "available": True, "advisory": True, "model": "test/model",
        "result": {"root_cause_hypotheses": ["origin down"], "priorities": ["fix origin"],
                   "recommendations": [], "content_opportunities": [], "validation_plan": ["re-audit"]},
    }
    out = html_report(result)
    assert "AI REASONING (ADVISORY)" in out
    assert "Advisory only" in out
    assert "origin down" in out
    assert "Root-cause hypotheses" in out


def test_html_report_renders_unavailable_reasoning():
    result = _result()
    result["reasoning"] = {"provider": "openrouter", "available": False,
                           "reason": "OPENROUTER_API_KEY is not configured", "result": None}
    out = html_report(result)
    assert "AI REASONING (ADVISORY)" in out
    assert "unavailable" in out.lower()
    assert "OPENROUTER_API_KEY is not configured" in out


def test_html_report_escapes_reasoning_content():
    payload = "<script>alert('r')</script>"
    result = _result()
    result["reasoning"] = {"provider": "openrouter", "available": True, "model": payload,
                           "result": {"recommendations": [payload]}}
    out = html_report(result)
    assert "<script>alert('r')</script>" not in out
    assert "&lt;script&gt;" in out
