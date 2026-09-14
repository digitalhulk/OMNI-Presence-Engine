"""Tests for the performance analysis module."""
from __future__ import annotations

from ope.browser import (
    BrowserResult,
    BrowserStatus,
    ConsoleMessage,
    DeviceProfile,
    DOMMetrics,
    PerformanceTiming,
    ResourceSummary,
    WebVitals,
)
from ope.performance import (
    Finding,
    PerformanceReport,
    _rating,
    analyze_performance,
)


class TestRating:
    def test_good_fcp(self) -> None:
        assert _rating(1500, "fcp") == "GOOD"

    def test_needs_improvement_fcp(self) -> None:
        assert _rating(2000, "fcp") == "NEEDS_IMPROVEMENT"

    def test_poor_fcp(self) -> None:
        assert _rating(4000, "fcp") == "POOR"

    def test_none_value(self) -> None:
        assert _rating(None, "fcp") == "UNKNOWN"

    def test_unknown_metric(self) -> None:
        assert _rating(100, "nonexistent") == "UNKNOWN"

    def test_lcp_thresholds(self) -> None:
        assert _rating(2000, "lcp") == "GOOD"
        assert _rating(3000, "lcp") == "NEEDS_IMPROVEMENT"
        assert _rating(5000, "lcp") == "POOR"

    def test_cls_thresholds(self) -> None:
        assert _rating(0.05, "cls") == "GOOD"
        assert _rating(0.15, "cls") == "NEEDS_IMPROVEMENT"
        assert _rating(0.3, "cls") == "POOR"

    def test_tbt_thresholds(self) -> None:
        assert _rating(100, "tbt") == "GOOD"
        assert _rating(400, "tbt") == "NEEDS_IMPROVEMENT"
        assert _rating(800, "tbt") == "POOR"

    def test_ttfb_thresholds(self) -> None:
        assert _rating(500, "ttfb") == "GOOD"
        assert _rating(1000, "ttfb") == "NEEDS_IMPROVEMENT"
        assert _rating(2000, "ttfb") == "POOR"

    def test_boundary_values(self) -> None:
        assert _rating(1800, "fcp") == "GOOD"
        assert _rating(1800.1, "fcp") == "NEEDS_IMPROVEMENT"
        assert _rating(3000, "fcp") == "NEEDS_IMPROVEMENT"
        assert _rating(3000.1, "fcp") == "POOR"


class TestFinding:
    def test_to_dict_minimal(self) -> None:
        f = Finding(module="test", severity="HIGH", symptom="Bad thing")
        d = f.to_dict()
        assert d["module"] == "test"
        assert d["severity"] == "HIGH"
        assert d["symptom"] == "Bad thing"
        assert "recommendation" not in d

    def test_to_dict_full(self) -> None:
        f = Finding(
            module="performance.vitals", severity="HIGH",
            symptom="LCP is 5000ms", evidence={"lcp_ms": 5000},
            recommendation="Optimize images", metric="lcp", profile="DESKTOP",
        )
        d = f.to_dict()
        assert d["recommendation"] == "Optimize images"
        assert d["metric"] == "lcp"
        assert d["profile"] == "DESKTOP"


class TestPerformanceReport:
    def test_to_dict_minimal(self) -> None:
        r = PerformanceReport(url="http://example.com/")
        d = r.to_dict()
        assert d["url"] == "http://example.com/"
        assert d["status"] == "COMPLETED"
        assert d["findings"] == []

    def test_to_dict_with_error(self) -> None:
        r = PerformanceReport(url="http://example.com/", status="NO_DATA", error="No results")
        d = r.to_dict()
        assert d["error"] == "No results"


class TestAnalyzePerformanceEmpty:
    def test_no_results(self) -> None:
        report = analyze_performance([])
        assert report.status == "NO_DATA"
        assert report.error

    def test_failed_result(self) -> None:
        br = BrowserResult(url="http://example.com/", status=BrowserStatus.TIMEOUT, errors=["timeout"])
        report = analyze_performance([br])
        assert report.url == "http://example.com/"
        assert len(report.findings) == 0


def _make_browser_result(
    vitals: WebVitals | None = None,
    timing: PerformanceTiming | None = None,
    dom: DOMMetrics | None = None,
    resources: ResourceSummary | None = None,
    console: list[ConsoleMessage] | None = None,
    source_len: int = 5000,
    rendered_len: int = 6000,
    profile: DeviceProfile = DeviceProfile.DESKTOP,
) -> BrowserResult:
    return BrowserResult(
        url="http://example.com/",
        final_url="http://example.com/",
        status=BrowserStatus.SUCCESS,
        status_code=200,
        profile=profile,
        source_html_length=source_len,
        rendered_html_length=rendered_len,
        vitals=vitals or WebVitals(),
        timing=timing or PerformanceTiming(),
        dom_metrics=dom or DOMMetrics(),
        resource_summary=resources or ResourceSummary(),
        console_messages=console or [],
    )


class TestVitalsAnalysis:
    def test_poor_fcp_finding(self) -> None:
        br = _make_browser_result(vitals=WebVitals(fcp_ms=4000))
        report = analyze_performance([br])
        fcp_findings = [f for f in report.findings if f.metric == "fcp"]
        assert len(fcp_findings) == 1
        assert fcp_findings[0].severity == "HIGH"

    def test_needs_improvement_fcp(self) -> None:
        br = _make_browser_result(vitals=WebVitals(fcp_ms=2000))
        report = analyze_performance([br])
        fcp_findings = [f for f in report.findings if f.metric == "fcp"]
        assert len(fcp_findings) == 1
        assert fcp_findings[0].severity == "MEDIUM"

    def test_good_fcp_no_finding(self) -> None:
        br = _make_browser_result(vitals=WebVitals(fcp_ms=1000))
        report = analyze_performance([br])
        fcp_findings = [f for f in report.findings if f.metric == "fcp"]
        assert len(fcp_findings) == 0

    def test_poor_lcp_finding(self) -> None:
        br = _make_browser_result(vitals=WebVitals(lcp_ms=5000, lcp_tag="IMG", lcp_url="http://example.com/hero.jpg"))
        report = analyze_performance([br])
        lcp_findings = [f for f in report.findings if f.metric == "lcp"]
        assert len(lcp_findings) == 1
        assert lcp_findings[0].severity == "HIGH"
        assert "lcp_tag" in lcp_findings[0].evidence

    def test_poor_cls_finding(self) -> None:
        br = _make_browser_result(vitals=WebVitals(cls=0.3, cls_shifts=[{"value": 0.15}]))
        report = analyze_performance([br])
        cls_findings = [f for f in report.findings if f.metric == "cls"]
        assert len(cls_findings) == 1
        assert cls_findings[0].severity == "HIGH"
        assert "top_shifts" in cls_findings[0].evidence

    def test_poor_tbt_finding(self) -> None:
        br = _make_browser_result(vitals=WebVitals(
            tbt_ms=800,
            long_tasks=[{"start": 100, "duration": 200, "blocking": 150}],
        ))
        report = analyze_performance([br])
        tbt_findings = [f for f in report.findings if f.metric == "tbt"]
        assert len(tbt_findings) == 1
        assert tbt_findings[0].severity == "HIGH"

    def test_poor_ttfb_finding(self) -> None:
        br = _make_browser_result(timing=PerformanceTiming(navigation_start=1, response_start=2001))
        report = analyze_performance([br])
        ttfb_findings = [f for f in report.findings if f.metric == "ttfb"]
        assert len(ttfb_findings) == 1
        assert ttfb_findings[0].severity == "HIGH"

    def test_vitals_summary_populated(self) -> None:
        br = _make_browser_result(vitals=WebVitals(fcp_ms=1000, lcp_ms=2000, cls=0.05, tbt_ms=100))
        report = analyze_performance([br])
        summary = report.vitals_summary.get("DESKTOP", {})
        assert "fcp" in summary
        assert summary["fcp"]["rating"] == "GOOD"
        assert "lcp" in summary
        assert "cls" in summary
        assert "tbt" in summary


class TestResourceAnalysis:
    def test_high_request_count(self) -> None:
        rs = ResourceSummary(total_requests=150, by_type={"js": {"count": 50, "transfer_bytes": 0, "resource_bytes": 0}})
        br = _make_browser_result(resources=rs)
        report = analyze_performance([br])
        resource_findings = [f for f in report.findings if f.module == "performance.resources"]
        assert any("150 network requests" in f.symptom for f in resource_findings)

    def test_large_page_weight(self) -> None:
        rs = ResourceSummary(total_transfer_bytes=6 * 1024 * 1024)
        br = _make_browser_result(resources=rs)
        report = analyze_performance([br])
        weight_findings = [f for f in report.findings if "weight" in f.symptom.lower() or "MB" in f.symptom]
        assert len(weight_findings) >= 1
        assert weight_findings[0].severity == "HIGH"

    def test_medium_page_weight(self) -> None:
        rs = ResourceSummary(total_transfer_bytes=3 * 1024 * 1024)
        br = _make_browser_result(resources=rs)
        report = analyze_performance([br])
        weight_findings = [f for f in report.findings if "weight" in f.symptom.lower() or "MB" in f.symptom]
        assert len(weight_findings) >= 1
        assert weight_findings[0].severity == "MEDIUM"

    def test_many_third_party_requests(self) -> None:
        rs = ResourceSummary(third_party_requests=25, first_party_requests=10)
        br = _make_browser_result(resources=rs)
        report = analyze_performance([br])
        tp_findings = [f for f in report.findings if "third-party" in f.symptom]
        assert len(tp_findings) == 1

    def test_many_js_files(self) -> None:
        rs = ResourceSummary(by_type={"js": {"count": 20, "transfer_bytes": 500000, "resource_bytes": 1000000}})
        br = _make_browser_result(resources=rs)
        report = analyze_performance([br])
        js_findings = [f for f in report.findings if "JavaScript files" in f.symptom]
        assert len(js_findings) == 1

    def test_many_css_files(self) -> None:
        rs = ResourceSummary(by_type={"css": {"count": 15, "transfer_bytes": 100000, "resource_bytes": 200000}})
        br = _make_browser_result(resources=rs)
        report = analyze_performance([br])
        css_findings = [f for f in report.findings if "CSS files" in f.symptom]
        assert len(css_findings) == 1


class TestDOMAnalysis:
    def test_excessive_dom_size(self) -> None:
        dm = DOMMetrics(node_count=5000)
        br = _make_browser_result(dom=dm)
        report = analyze_performance([br])
        dom_findings = [f for f in report.findings if f.module == "performance.dom"]
        assert any("5000 nodes" in f.symptom for f in dom_findings)

    def test_deep_nesting(self) -> None:
        dm = DOMMetrics(max_depth=50)
        br = _make_browser_result(dom=dm)
        report = analyze_performance([br])
        depth_findings = [f for f in report.findings if "depth" in f.symptom.lower()]
        assert len(depth_findings) == 1

    def test_many_iframes(self) -> None:
        dm = DOMMetrics(iframe_count=5)
        br = _make_browser_result(dom=dm)
        report = analyze_performance([br])
        iframe_findings = [f for f in report.findings if "iframe" in f.symptom.lower()]
        assert len(iframe_findings) == 1

    def test_normal_dom_no_finding(self) -> None:
        dm = DOMMetrics(node_count=500, max_depth=10, iframe_count=1)
        br = _make_browser_result(dom=dm)
        report = analyze_performance([br])
        dom_findings = [f for f in report.findings if f.module == "performance.dom"]
        assert len(dom_findings) == 0


class TestRenderDiffAnalysis:
    def test_heavy_client_rendering(self) -> None:
        br = _make_browser_result(source_len=5000, rendered_len=20000)
        report = analyze_performance([br])
        render_findings = [f for f in report.findings if f.module == "performance.render"]
        assert len(render_findings) == 1
        assert "4.0x" in render_findings[0].symptom

    def test_normal_ratio_no_finding(self) -> None:
        br = _make_browser_result(source_len=5000, rendered_len=6000)
        report = analyze_performance([br])
        render_findings = [f for f in report.findings if f.module == "performance.render"]
        assert len(render_findings) == 0

    def test_console_errors_finding(self) -> None:
        console = [
            ConsoleMessage(type="error", text="TypeError: x is not defined"),
            ConsoleMessage(type="error", text="ReferenceError: y"),
            ConsoleMessage(type="log", text="Info message"),
        ]
        br = _make_browser_result(console=console)
        report = analyze_performance([br])
        console_findings = [f for f in report.findings if f.module == "performance.runtime"]
        assert len(console_findings) == 1
        assert "2 JavaScript console error" in console_findings[0].symptom


class TestMultiProfile:
    def test_desktop_and_mobile(self) -> None:
        desktop = _make_browser_result(
            vitals=WebVitals(fcp_ms=1000, lcp_ms=2000),
            profile=DeviceProfile.DESKTOP,
        )
        mobile = _make_browser_result(
            vitals=WebVitals(fcp_ms=3500, lcp_ms=5000),
            profile=DeviceProfile.MOBILE,
        )
        report = analyze_performance([desktop, mobile])
        assert "DESKTOP" in report.vitals_summary
        assert "MOBILE" in report.vitals_summary
        mobile_findings = [f for f in report.findings if f.profile == "MOBILE"]
        assert len(mobile_findings) > 0
