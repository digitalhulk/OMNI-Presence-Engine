"""Tests for the performance evidence injection module."""
from __future__ import annotations

from ope.performance_evidence import inject_performance_evidence


def _make_perf_result(
    status: str = "COMPLETED",
    performance_report: dict | None = None,
) -> dict:
    d: dict = {
        "target": "https://example.com",
        "normalized_target": "https://example.com/",
        "status": status,
    }
    if performance_report is not None:
        d["performance_report"] = performance_report
    return d


def _make_report(
    vitals_summary: dict | None = None,
    resource_analysis: dict | None = None,
    dom_analysis: dict | None = None,
    render_analysis: dict | None = None,
    findings: list | None = None,
) -> dict:
    d: dict = {"url": "https://example.com/", "status": "COMPLETED"}
    if vitals_summary is not None:
        d["vitals_summary"] = vitals_summary
    if resource_analysis is not None:
        d["resource_analysis"] = resource_analysis
    if dom_analysis is not None:
        d["dom_analysis"] = dom_analysis
    if render_analysis is not None:
        d["render_analysis"] = render_analysis
    if findings is not None:
        d["findings"] = findings
    return d


class TestInjectPerformanceEvidence:
    def test_non_completed_status_no_injection(self) -> None:
        inv: dict = {}
        inject_performance_evidence(inv, _make_perf_result(status="ERROR"))
        assert not inv

    def test_non_dict_result_no_injection(self) -> None:
        inv: dict = {}
        inject_performance_evidence(inv, "not a dict")  # type: ignore[arg-type]
        assert not inv

    def test_missing_performance_report_no_injection(self) -> None:
        inv: dict = {}
        inject_performance_evidence(inv, _make_perf_result())
        assert not inv

    def test_vitals_summary_injected(self) -> None:
        inv: dict = {}
        report = _make_report(vitals_summary={
            "DESKTOP": {
                "fcp": {"value_ms": 1200.0, "rating": "GOOD"},
                "lcp": {"value_ms": 2400.0, "rating": "GOOD"},
                "cls": {"value": 0.05, "rating": "GOOD"},
            }
        })
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_vitals_summary" in inv
        assert "fcp" in inv["perf_vitals_summary"]
        assert inv["perf_vitals_summary"]["fcp"]["rating"] == "GOOD"

    def test_vitals_summary_first_profile_wins(self) -> None:
        inv: dict = {}
        report = _make_report(vitals_summary={
            "DESKTOP": {"fcp": {"value_ms": 1200.0, "rating": "GOOD"}},
            "MOBILE": {"fcp": {"value_ms": 2800.0, "rating": "NEEDS_IMPROVEMENT"}},
        })
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert inv["perf_vitals_summary"]["fcp"]["rating"] == "GOOD"

    def test_empty_vitals_not_injected(self) -> None:
        inv: dict = {}
        report = _make_report(vitals_summary={})
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_vitals_summary" not in inv

    def test_resource_analysis_injected(self) -> None:
        inv: dict = {}
        report = _make_report(resource_analysis={
            "total_requests": 45,
            "total_transfer_bytes": 1200000,
            "total_resource_bytes": 2400000,
            "first_party_requests": 30,
            "third_party_requests": 15,
            "by_type": {"js": {"count": 8, "transfer_bytes": 500000}},
        })
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        res = inv["perf_resource_analysis"]
        assert res["total_requests"] == 45
        assert res["third_party_requests"] == 15
        assert "by_type" in res

    def test_empty_resource_analysis_not_injected(self) -> None:
        inv: dict = {}
        report = _make_report(resource_analysis={})
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_resource_analysis" not in inv

    def test_dom_analysis_injected(self) -> None:
        inv: dict = {}
        report = _make_report(dom_analysis={
            "node_count": 2500, "max_depth": 20,
            "element_count": 1200, "script_count": 12,
            "style_count": 5, "iframe_count": 2, "image_count": 30,
        })
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        dom = inv["perf_dom_analysis"]
        assert dom["node_count"] == 2500
        assert dom["max_depth"] == 20
        assert dom["image_count"] == 30

    def test_empty_dom_not_injected(self) -> None:
        inv: dict = {}
        report = _make_report(dom_analysis={})
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_dom_analysis" not in inv

    def test_render_analysis_injected(self) -> None:
        inv: dict = {}
        report = _make_report(render_analysis={
            "source_html_bytes": 50000,
            "rendered_html_bytes": 120000,
            "diff_bytes": 70000,
            "render_ratio": 2.4,
        })
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        rnd = inv["perf_render_analysis"]
        assert rnd["source_html_bytes"] == 50000
        assert rnd["render_ratio"] == 2.4

    def test_empty_render_not_injected(self) -> None:
        inv: dict = {}
        report = _make_report(render_analysis={})
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_render_analysis" not in inv

    def test_findings_summary_injected(self) -> None:
        inv: dict = {}
        report = _make_report(findings=[
            {"severity": "HIGH", "symptom": "Slow LCP"},
            {"severity": "HIGH", "symptom": "High TBT"},
            {"severity": "MEDIUM", "symptom": "Many requests"},
        ])
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        fs = inv["perf_findings_summary"]
        assert fs["total"] == 3
        assert fs["by_severity"]["HIGH"] == 2
        assert fs["by_severity"]["MEDIUM"] == 1

    def test_empty_findings_not_injected(self) -> None:
        inv: dict = {}
        report = _make_report(findings=[])
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_findings_summary" not in inv

    def test_no_overwrite_existing_keys(self) -> None:
        inv: dict = {"perf_vitals_summary": {"fcp": {"value_ms": 999}}}
        report = _make_report(vitals_summary={
            "DESKTOP": {"fcp": {"value_ms": 1200.0, "rating": "GOOD"}}
        })
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert inv["perf_vitals_summary"]["fcp"]["value_ms"] == 999

    def test_full_injection(self) -> None:
        inv: dict = {}
        report = _make_report(
            vitals_summary={"DESKTOP": {"lcp": {"value_ms": 2400.0, "rating": "GOOD"}}},
            resource_analysis={"total_requests": 50, "total_transfer_bytes": 1000000, "total_resource_bytes": 2000000, "first_party_requests": 40, "third_party_requests": 10},
            dom_analysis={"node_count": 1500, "max_depth": 15},
            render_analysis={"source_html_bytes": 30000, "rendered_html_bytes": 60000, "render_ratio": 2.0},
            findings=[{"severity": "LOW", "symptom": "Minor issue"}],
        )
        inject_performance_evidence(inv, _make_perf_result(performance_report=report))
        assert "perf_vitals_summary" in inv
        assert "perf_resource_analysis" in inv
        assert "perf_dom_analysis" in inv
        assert "perf_render_analysis" in inv
        assert "perf_findings_summary" in inv
