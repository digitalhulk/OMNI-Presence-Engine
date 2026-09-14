"""Tests for performance-audit HTML report rendering."""
from __future__ import annotations

from typing import Any

from ope.report_html_performance import performance_html_report, write_performance_html_report


def test_performance_html_report_renders(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "<!doctype html>" in html
    assert "PERFORMANCE AUDIT" in html
    assert "example.com" in html


def test_performance_html_report_contains_vitals(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "CORE WEB VITALS" in html
    assert "DESKTOP" in html
    assert "LCP" in html


def test_performance_html_report_contains_resources(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "RESOURCE SUMMARY" in html
    assert "Total requests" in html


def test_performance_html_report_contains_modules(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "MODULE" in html


def test_performance_html_report_escapes_xss(minimal_performance_result: dict[str, Any]) -> None:
    minimal_performance_result["target"] = "<img onerror=alert(1)>"
    html = performance_html_report(minimal_performance_result)
    assert "<img onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_performance_html_report_empty_findings(minimal_performance_result: dict[str, Any]) -> None:
    minimal_performance_result["findings"] = []
    html = performance_html_report(minimal_performance_result)
    assert "NO FINDINGS" in html


def test_performance_html_report_no_report_key(minimal_performance_result: dict[str, Any]) -> None:
    del minimal_performance_result["performance_report"]
    html = performance_html_report(minimal_performance_result)
    assert "PERFORMANCE AUDIT" in html


def test_performance_html_report_duration(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "4.2s" in html


def test_write_performance_html_report_persists(minimal_performance_result: dict[str, Any], tmp_path: Any) -> None:
    out = tmp_path / "perf-report.html"
    result = write_performance_html_report(minimal_performance_result, out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "<!doctype html>" in content
    assert "PERFORMANCE AUDIT" in content


def test_performance_html_report_scope_label(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "SCOPE: PERFORMANCE" in html


def test_performance_html_report_bytes_formatting(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "1.4 MB" in html


def test_performance_html_report_contract_footer(minimal_performance_result: dict[str, Any]) -> None:
    html = performance_html_report(minimal_performance_result)
    assert "evidence-diagnostic-v1" in html
