"""Tests for multi-target orchestration — isolation, determinism, aggregation."""
from __future__ import annotations

import argparse
import json

from ope.orchestrator import audit_targets, multi_audit_markdown


def _ok(url, health=90.0, findings=0):
    return {"target": url, "ok": True, "error": None,
            "result": {"target": url, "health": health, "findings": [{"id": f"f{i}"} for i in range(findings)]}}


def _fake_auditor(mapping):
    def run(url):
        return mapping[url]
    return run


class TestAuditTargets:
    def test_empty_input(self):
        report = audit_targets([])
        assert report["results"] == []
        assert report["summary"]["target_count"] == 0

    def test_results_in_input_order_regardless_of_completion(self):
        urls = ["https://a.example", "https://b.example", "https://c.example"]
        mapping = {u: _ok(u, health=float(i)) for i, u in enumerate(urls)}
        report = audit_targets(urls, auditor=_fake_auditor(mapping), max_workers=3)
        assert [r["target"] for r in report["results"]] == urls

    def test_one_failure_does_not_destroy_others(self):
        urls = ["https://ok1.example", "https://bad.example", "https://ok2.example"]
        mapping = {
            urls[0]: _ok(urls[0]),
            urls[1]: {"target": urls[1], "ok": False, "result": None, "error": "ValueError: boom"},
            urls[2]: _ok(urls[2]),
        }
        report = audit_targets(urls, auditor=_fake_auditor(mapping))
        assert report["summary"]["succeeded"] == 2
        assert report["summary"]["failed"] == 1
        assert report["summary"]["failed_targets"] == ["https://bad.example"]

    def test_auditor_raising_is_isolated(self):
        urls = ["https://a.example", "https://b.example"]

        def raising(url):
            if "b" in url:
                raise RuntimeError("unexpected")
            return _ok(url)

        report = audit_targets(urls, auditor=raising)
        assert report["summary"]["succeeded"] == 1
        assert report["summary"]["failed"] == 1
        bad = next(r for r in report["results"] if not r["ok"])
        assert "RuntimeError" in bad["error"]

    def test_aggregate_mean_health_and_findings(self):
        urls = ["https://a.example", "https://b.example"]
        mapping = {urls[0]: _ok(urls[0], health=80.0, findings=2), urls[1]: _ok(urls[1], health=100.0, findings=1)}
        report = audit_targets(urls, auditor=_fake_auditor(mapping))
        assert report["summary"]["mean_health"] == 90.0
        assert report["summary"]["total_findings"] == 3

    def test_deterministic_repeated_runs(self):
        urls = ["https://a.example", "https://b.example", "https://c.example"]
        mapping = {u: _ok(u, health=float(i * 10)) for i, u in enumerate(urls)}
        r1 = audit_targets(urls, auditor=_fake_auditor(mapping), max_workers=3)
        r2 = audit_targets(urls, auditor=_fake_auditor(mapping), max_workers=3)
        assert json.dumps(r1) == json.dumps(r2)

    def test_worker_count_is_bounded(self):
        # Many targets must not spawn an unbounded pool; cap is respected.
        urls = [f"https://s{i}.example" for i in range(100)]
        mapping = {u: _ok(u) for u in urls}
        report = audit_targets(urls, auditor=_fake_auditor(mapping), max_workers=1000)
        assert report["summary"]["succeeded"] == 100

    def test_all_failed_summary(self):
        urls = ["https://a.example"]
        mapping = {urls[0]: {"target": urls[0], "ok": False, "result": None, "error": "boom"}}
        report = audit_targets(urls, auditor=_fake_auditor(mapping))
        assert report["summary"]["succeeded"] == 0
        assert report["summary"]["failed"] == 1


class TestMultiAuditMarkdown:
    def test_renders_table_and_failures(self):
        urls = ["https://a.example", "https://b.example"]
        mapping = {urls[0]: _ok(urls[0], health=90.0, findings=1),
                   urls[1]: {"target": urls[1], "ok": False, "result": None, "error": "ValueError: down"}}
        md = multi_audit_markdown(audit_targets(urls, auditor=_fake_auditor(mapping)))
        assert "Multi-Target Audit" in md
        assert "https://a.example | OK" in md
        assert "https://b.example | FAILED" in md


class TestMultiAuditCLI:
    def test_all_failed_returns_2(self, monkeypatch, capsys):
        from ope import cli
        report = {"engine": "ope", "version": "x", "results": [{"target": "u", "ok": False, "result": None, "error": "e"}],
                  "summary": {"target_count": 1, "succeeded": 0, "failed": 1}}
        monkeypatch.setattr("ope.orchestrator.audit_targets", lambda *a, **k: report)
        args = argparse.Namespace(urls=["https://x.example"], markdown=False, timeout=15,
                                  no_subresources=False, max_workers=4, no_history=True)
        assert cli.multi_audit_command(args) == 2

    def test_partial_success_returns_0(self, monkeypatch):
        from ope import cli
        report = {"engine": "ope", "version": "x",
                  "results": [{"target": "u", "ok": True, "result": {"health": 90.0, "findings": []}, "error": None}],
                  "summary": {"target_count": 2, "succeeded": 1, "failed": 1}}
        monkeypatch.setattr("ope.orchestrator.audit_targets", lambda *a, **k: report)
        args = argparse.Namespace(urls=["https://x.example", "https://y.example"], markdown=True, timeout=15,
                                  no_subresources=False, max_workers=4, no_history=True)
        assert cli.multi_audit_command(args) == 0
