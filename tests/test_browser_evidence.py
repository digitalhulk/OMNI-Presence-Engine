"""Tests for the browser evidence injection module."""
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
from ope.browser_evidence import inject_browser_evidence


def _make_result(
    profile: DeviceProfile = DeviceProfile.DESKTOP,
    status: BrowserStatus = BrowserStatus.SUCCESS,
    vitals: WebVitals | None = None,
    timing: PerformanceTiming | None = None,
    dom: DOMMetrics | None = None,
    resources: ResourceSummary | None = None,
    console: list[ConsoleMessage] | None = None,
    source_len: int = 5000,
    rendered_len: int = 6000,
) -> BrowserResult:
    return BrowserResult(
        url="http://example.com/",
        final_url="http://example.com/",
        status=status,
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


class TestInjectBrowserEvidence:
    def test_successful_desktop_result(self) -> None:
        inv: dict = {}
        br = _make_result(
            vitals=WebVitals(fcp_ms=1200.0, lcp_ms=2400.0, cls=0.05, tbt_ms=150.0),
            timing=PerformanceTiming(navigation_start=1.0, response_start=301.0),
            dom=DOMMetrics(node_count=800, max_depth=12, script_count=5, image_count=10),
            resources=ResourceSummary(total_requests=40, total_transfer_bytes=500000, total_resource_bytes=1200000, first_party_requests=30, third_party_requests=10, by_type={"js": {"count": 8}}),
            console=[ConsoleMessage(type="error", text="TypeError"), ConsoleMessage(type="log", text="ok")],
            source_len=5000,
            rendered_len=10000,
        )
        inject_browser_evidence(inv, [br])

        assert inv["browser_vitals"]["fcp_ms"] == 1200.0
        assert inv["browser_vitals"]["lcp_ms"] == 2400.0
        assert inv["browser_vitals"]["cls"] == 0.05
        assert inv["browser_vitals"]["tbt_ms"] == 150.0
        assert inv["browser_vitals"]["ttfb_ms"] == 300.0
        assert inv["browser_dom"]["node_count"] == 800
        assert inv["browser_dom"]["max_depth"] == 12
        assert inv["browser_dom"]["script_count"] == 5
        assert inv["browser_dom"]["image_count"] == 10
        assert inv["browser_resources"]["total_requests"] == 40
        assert inv["browser_resources"]["third_party_requests"] == 10
        assert inv["browser_render"]["render_ratio"] == 2.0
        assert inv["browser_render"]["source_html_length"] == 5000
        assert inv["browser_render"]["rendered_html_length"] == 10000
        assert inv["browser_console_errors"] == 1
        assert inv["browser_profile"] == "DESKTOP"

    def test_mobile_fallback(self) -> None:
        inv: dict = {}
        br = _make_result(
            profile=DeviceProfile.MOBILE,
            vitals=WebVitals(fcp_ms=2000.0),
        )
        inject_browser_evidence(inv, [br])
        assert inv["browser_vitals"]["fcp_ms"] == 2000.0
        assert inv["browser_profile"] == "MOBILE"

    def test_desktop_preferred_over_mobile(self) -> None:
        inv: dict = {}
        mobile = _make_result(profile=DeviceProfile.MOBILE, vitals=WebVitals(fcp_ms=3000.0))
        desktop = _make_result(profile=DeviceProfile.DESKTOP, vitals=WebVitals(fcp_ms=1000.0))
        inject_browser_evidence(inv, [mobile, desktop])
        assert inv["browser_vitals"]["fcp_ms"] == 1000.0
        assert inv["browser_profile"] == "DESKTOP"

    def test_failed_result_no_injection(self) -> None:
        inv: dict = {}
        br = _make_result(status=BrowserStatus.ERROR)
        inject_browser_evidence(inv, [br])
        assert "browser_vitals" not in inv
        assert "browser_dom" not in inv
        assert "browser_render" not in inv

    def test_empty_results_no_injection(self) -> None:
        inv: dict = {}
        inject_browser_evidence(inv, [])
        assert "browser_vitals" not in inv

    def test_mixed_success_failure(self) -> None:
        inv: dict = {}
        failed = _make_result(status=BrowserStatus.TIMEOUT, profile=DeviceProfile.DESKTOP)
        ok = _make_result(status=BrowserStatus.SUCCESS, profile=DeviceProfile.MOBILE, vitals=WebVitals(fcp_ms=1500.0))
        inject_browser_evidence(inv, [failed, ok])
        assert inv["browser_vitals"]["fcp_ms"] == 1500.0
        assert inv["browser_profile"] == "MOBILE"

    def test_no_overwrite_existing_keys(self) -> None:
        inv: dict = {"browser_vitals": {"fcp_ms": 9999.0}}
        br = _make_result(vitals=WebVitals(fcp_ms=1000.0))
        inject_browser_evidence(inv, [br])
        assert inv["browser_vitals"]["fcp_ms"] == 9999.0

    def test_partial_vitals(self) -> None:
        inv: dict = {}
        br = _make_result(vitals=WebVitals(fcp_ms=1200.0))
        inject_browser_evidence(inv, [br])
        assert inv["browser_vitals"] == {"fcp_ms": 1200.0}

    def test_zero_source_html(self) -> None:
        inv: dict = {}
        br = _make_result(source_len=0, rendered_len=5000)
        inject_browser_evidence(inv, [br])
        assert inv["browser_render"]["render_ratio"] == 0.0

    def test_console_errors_count(self) -> None:
        inv: dict = {}
        br = _make_result(console=[
            ConsoleMessage(type="error", text="err1"),
            ConsoleMessage(type="error", text="err2"),
            ConsoleMessage(type="warning", text="warn"),
            ConsoleMessage(type="log", text="info"),
        ])
        inject_browser_evidence(inv, [br])
        assert inv["browser_console_errors"] == 2

    def test_timing_included(self) -> None:
        inv: dict = {}
        br = _make_result(timing=PerformanceTiming(
            navigation_start=1.0, response_start=201.0,
            dom_interactive=501.0, dom_content_loaded=601.0,
        ))
        inject_browser_evidence(inv, [br])
        assert "browser_timing" in inv
        assert inv["browser_timing"]["ttfb_ms"] == 200.0

    def test_empty_timing_not_included(self) -> None:
        inv: dict = {}
        br = _make_result(timing=PerformanceTiming())
        inject_browser_evidence(inv, [br])
        assert "browser_timing" not in inv
