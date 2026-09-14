"""Tests for the CLI module — argument parsing, dispatch, and output formats."""
from __future__ import annotations

import json
from io import StringIO
from unittest import mock

import pytest

from ope.cli import (
    build_parser,
    performance_audit_markdown_report,
    site_audit_markdown_report,
)


class TestBuildParser:
    def test_audit_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com"])
        assert args.command == "audit"
        assert args.url == "https://example.com"

    def test_audit_default_timeout(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com"])
        assert args.timeout == 15

    def test_audit_markdown_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com", "--markdown"])
        assert args.markdown is True

    def test_audit_html_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com", "--html", "out.html"])
        assert args.html == "out.html"

    def test_audit_no_subresources(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com", "--no-subresources"])
        assert args.no_subresources is True

    def test_audit_no_history(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com", "--no-history"])
        assert args.no_history is True

    def test_audit_browser_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "https://example.com", "--browser", "--browser-timeout", "60"])
        assert args.browser is True
        assert args.browser_timeout == 60

    def test_site_audit_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["site-audit", "https://example.com"])
        assert args.command == "site-audit"
        assert args.url == "https://example.com"

    def test_site_audit_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["site-audit", "https://example.com"])
        assert args.max_pages == 200
        assert args.max_depth == 10
        assert args.delay == 0.5

    def test_site_audit_markdown(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["site-audit", "https://example.com", "--markdown"])
        assert args.markdown is True

    def test_site_audit_no_history(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["site-audit", "https://example.com", "--no-history"])
        assert args.no_history is True

    def test_site_audit_no_sitemaps(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["site-audit", "https://example.com", "--no-sitemaps"])
        assert args.no_sitemaps is True

    def test_performance_audit_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["performance-audit", "https://example.com"])
        assert args.command == "performance-audit"

    def test_performance_audit_markdown(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["performance-audit", "https://example.com", "--markdown"])
        assert args.markdown is True

    def test_performance_audit_desktop_only(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["performance-audit", "https://example.com", "--desktop-only"])
        assert args.desktop_only is True

    def test_performance_audit_timeout(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["performance-audit", "https://example.com", "--timeout", "60"])
        assert args.timeout == 60

    def test_setup_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["setup"])
        assert args.command == "setup"


class TestMainDispatch:
    @mock.patch("ope.cli.audit_command", return_value=0)
    def test_implicit_audit_command(self, mock_cmd: mock.Mock) -> None:
        from ope.cli import main
        with mock.patch("sys.argv", ["ope", "https://example.com"]):
            result = main()
        assert result == 0
        mock_cmd.assert_called_once()

    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_no_command_prints_help(self, mock_out: StringIO) -> None:
        from ope.cli import main
        with mock.patch("sys.argv", ["ope"]):
            result = main()
        assert result == 0


class TestAuditCommand:
    @mock.patch("ope.cli.history")
    @mock.patch("ope.cli.normalize_result")
    @mock.patch("ope.cli.audit")
    def test_json_output(self, mock_audit: mock.Mock, mock_norm: mock.Mock, mock_hist: mock.Mock, capsys: pytest.CaptureFixture[str]) -> None:
        mock_audit.return_value = {"target": "https://example.com", "inventory": {}, "findings": []}
        mock_norm.return_value = {"target": "https://example.com", "engine_contract": "evidence-diagnostic-v1", "findings": []}

        import argparse

        from ope.cli import audit_command
        args = argparse.Namespace(
            url="https://example.com", timeout=15, no_subresources=False,
            no_history=False, markdown=False, html=None,
            browser=False, browser_timeout=30,
            browser_desktop_only=False, browser_mobile_only=False,
        )
        result = audit_command(args)
        assert result == 0
        output = json.loads(capsys.readouterr().out)
        assert output["engine_contract"] == "evidence-diagnostic-v1"

    @mock.patch("ope.cli.history")
    @mock.patch("ope.cli.normalize_result")
    @mock.patch("ope.cli.audit")
    def test_no_history_skips_save(self, mock_audit: mock.Mock, mock_norm: mock.Mock, mock_hist: mock.Mock) -> None:
        mock_audit.return_value = {"target": "https://example.com", "inventory": {}, "findings": []}
        mock_norm.return_value = {"target": "https://example.com", "findings": []}

        import argparse

        from ope.cli import audit_command
        args = argparse.Namespace(
            url="https://example.com", timeout=15, no_subresources=False,
            no_history=True, markdown=False, html=None,
            browser=False, browser_timeout=30,
            browser_desktop_only=False, browser_mobile_only=False,
        )
        audit_command(args)
        mock_hist.attach_baseline.assert_not_called()
        mock_hist.save_run.assert_not_called()

    @mock.patch("ope.cli.audit", side_effect=Exception("Network error"))
    def test_audit_exception_returns_2(self, mock_audit: mock.Mock) -> None:
        import argparse

        from ope.cli import audit_command
        args = argparse.Namespace(
            url="https://example.com", timeout=15, no_subresources=False,
            no_history=True, markdown=False, html=None,
            browser=False, browser_timeout=30,
            browser_desktop_only=False, browser_mobile_only=False,
        )
        assert audit_command(args) == 2


class TestSiteAuditMarkdownReport:
    def test_basic_report(self) -> None:
        result = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "crawl_summary": {"pages_crawled": 10},
            "findings": [
                {"id": "site-001", "severity": "high", "priority": 0.7,
                 "module": "04-crawl", "symptom": "orphan pages",
                 "root_cause": "No incoming links"},
            ],
        }
        md = site_audit_markdown_report(result)
        assert "OPE Site Audit" in md
        assert "COMPLETED" in md
        assert "orphan pages" in md
        assert "No incoming links" in md

    def test_no_findings(self) -> None:
        result = {"target": "https://example.com", "status": "COMPLETED", "findings": []}
        md = site_audit_markdown_report(result)
        assert "No site-level findings" in md


class TestPerformanceAuditMarkdownReport:
    def test_basic_report(self) -> None:
        result = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "duration_s": 5.2,
            "performance_report": {
                "vitals_summary": {
                    "DESKTOP": {
                        "lcp": {"value_ms": 2400.0, "rating": "GOOD"},
                        "fcp": {"value_ms": 1200.0, "rating": "GOOD"},
                    }
                }
            },
            "findings": [
                {"id": "perf-001", "severity": "high", "priority": 0.8,
                 "symptom": "Slow LCP", "root_cause": "Large image"},
            ],
        }
        md = performance_audit_markdown_report(result)
        assert "OPE Performance Audit" in md
        assert "COMPLETED" in md
        assert "LCP" in md
        assert "GOOD" in md
        assert "Slow LCP" in md

    def test_no_findings(self) -> None:
        result = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "duration_s": 3.0,
            "findings": [],
        }
        md = performance_audit_markdown_report(result)
        assert "No performance findings" in md

    def test_no_vitals(self) -> None:
        result = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "duration_s": 3.0,
            "findings": [],
        }
        md = performance_audit_markdown_report(result)
        assert "Core Web Vitals" not in md
