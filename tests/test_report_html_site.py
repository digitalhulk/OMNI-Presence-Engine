"""Tests for site-audit HTML report rendering."""
from __future__ import annotations

from typing import Any

from ope.report_html_site import site_html_report, write_site_html_report


def test_site_html_report_renders(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "<!doctype html>" in html
    assert "SITE AUDIT" in html
    assert "example.com" in html


def test_site_html_report_contains_crawl_summary(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "CRAWL SUMMARY" in html
    assert "Pages crawled" in html


def test_site_html_report_contains_modules(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "MODULE" in html
    assert "20-LAYER" in html


def test_site_html_report_contains_findings(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "Missing HSTS header" in html
    assert "FINDINGS" in html


def test_site_html_report_escapes_xss(minimal_site_result: dict[str, Any]) -> None:
    minimal_site_result["target"] = "<script>alert(1)</script>"
    html = site_html_report(minimal_site_result)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_site_html_report_empty_findings(minimal_site_result: dict[str, Any]) -> None:
    minimal_site_result["findings"] = []
    html = site_html_report(minimal_site_result)
    assert "NO FINDINGS" in html


def test_site_html_report_no_crawl_summary(minimal_site_result: dict[str, Any]) -> None:
    del minimal_site_result["crawl_summary"]
    html = site_html_report(minimal_site_result)
    assert "CRAWL SUMMARY" in html


def test_site_html_report_page_table(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "PAGES" in html
    assert "example.com/about" in html


def test_write_site_html_report_persists(minimal_site_result: dict[str, Any], tmp_path: Any) -> None:
    out = tmp_path / "site-report.html"
    result = write_site_html_report(minimal_site_result, out)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "<!doctype html>" in content
    assert "SITE AUDIT" in content


def test_site_html_report_scope_label(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "SCOPE: SITE" in html


def test_site_html_report_contract_footer(minimal_site_result: dict[str, Any]) -> None:
    html = site_html_report(minimal_site_result)
    assert "evidence-diagnostic-v1" in html
