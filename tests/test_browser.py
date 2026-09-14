"""Tests for the browser execution engine."""
from __future__ import annotations

from unittest import mock

from ope.browser import (
    BrowserConfig,
    BrowserResult,
    BrowserStatus,
    ConsoleMessage,
    DeviceProfile,
    DOMMetrics,
    NetworkRequest,
    PerformanceTiming,
    ResourceSummary,
    WebVitals,
    _build_resource_summary,
    _classify_resource_type,
    _find_chromium,
    execute_browser_audit,
)


class TestBrowserStatus:
    def test_values(self) -> None:
        assert BrowserStatus.SUCCESS.value == "SUCCESS"
        assert BrowserStatus.TIMEOUT.value == "TIMEOUT"
        assert BrowserStatus.BLOCKED.value == "BLOCKED"
        assert BrowserStatus.ERROR.value == "ERROR"
        assert BrowserStatus.CRASH.value == "CRASH"
        assert BrowserStatus.NAVIGATION_ERROR.value == "NAVIGATION_ERROR"


class TestDeviceProfile:
    def test_values(self) -> None:
        assert DeviceProfile.DESKTOP.value == "DESKTOP"
        assert DeviceProfile.MOBILE.value == "MOBILE"

    def test_device_configs_exist(self) -> None:
        from ope.browser import DEVICE_CONFIGS
        assert DeviceProfile.DESKTOP in DEVICE_CONFIGS
        assert DeviceProfile.MOBILE in DEVICE_CONFIGS
        assert DEVICE_CONFIGS[DeviceProfile.DESKTOP]["viewport"]["width"] == 1920
        assert DEVICE_CONFIGS[DeviceProfile.MOBILE]["viewport"]["width"] == 412
        assert DEVICE_CONFIGS[DeviceProfile.MOBILE]["is_mobile"] is True
        assert DEVICE_CONFIGS[DeviceProfile.DESKTOP]["is_mobile"] is False


class TestBrowserConfig:
    def test_defaults(self) -> None:
        cfg = BrowserConfig()
        assert cfg.timeout_ms == 30000
        assert cfg.navigation_timeout_ms == 30000
        assert cfg.max_redirects == 10
        assert cfg.max_dom_nodes == 100000
        assert cfg.max_screenshot_bytes == 5 * 1024 * 1024
        assert cfg.max_resources == 500
        assert cfg.max_resource_bytes == 50 * 1024 * 1024
        assert cfg.profiles == [DeviceProfile.DESKTOP]
        assert cfg.capture_screenshot is True
        assert cfg.collect_console is True
        assert cfg.headless is True

    def test_custom(self) -> None:
        cfg = BrowserConfig(
            timeout_ms=5000,
            profiles=[DeviceProfile.DESKTOP, DeviceProfile.MOBILE],
            capture_screenshot=False,
        )
        assert cfg.timeout_ms == 5000
        assert len(cfg.profiles) == 2
        assert cfg.capture_screenshot is False


class TestNetworkRequest:
    def test_to_dict_minimal(self) -> None:
        nr = NetworkRequest(url="http://example.com/style.css")
        d = nr.to_dict()
        assert d["url"] == "http://example.com/style.css"
        assert d["method"] == "GET"
        assert d["status"] == 0
        assert d["duration_ms"] == 0.0
        assert d["from_cache"] is False

    def test_to_dict_populated(self) -> None:
        nr = NetworkRequest(
            url="http://example.com/app.js",
            method="GET",
            resource_type="js",
            status=200,
            mime_type="application/javascript",
            transfer_size=45000,
            resource_size=120000,
            is_third_party=False,
            duration_ms=150.3,
            protocol="h2",
        )
        d = nr.to_dict()
        assert d["mime_type"] == "application/javascript"
        assert d["transfer_size"] == 45000
        assert d["protocol"] == "h2"
        assert d["duration_ms"] == 150.3

    def test_error_included(self) -> None:
        nr = NetworkRequest(url="http://fail.com/x", error="net::ERR_FAILED")
        d = nr.to_dict()
        assert d["error"] == "net::ERR_FAILED"


class TestConsoleMessage:
    def test_to_dict(self) -> None:
        cm = ConsoleMessage(type="error", text="Uncaught TypeError", url="http://example.com/app.js", line=42)
        d = cm.to_dict()
        assert d["type"] == "error"
        assert d["text"] == "Uncaught TypeError"
        assert d["url"] == "http://example.com/app.js"
        assert d["line"] == 42

    def test_text_truncation(self) -> None:
        cm = ConsoleMessage(type="log", text="x" * 1000)
        d = cm.to_dict()
        assert len(d["text"]) == 500


class TestPerformanceTiming:
    def test_ttfb(self) -> None:
        pt = PerformanceTiming(navigation_start=1, response_start=251.5)
        assert pt.ttfb() == 250.5

    def test_ttfb_none(self) -> None:
        pt = PerformanceTiming()
        assert pt.ttfb() is None

    def test_dns_ms(self) -> None:
        pt = PerformanceTiming(dns_start=10, dns_end=25.3)
        assert pt.dns_ms() == 15.3

    def test_tls_ms(self) -> None:
        pt = PerformanceTiming(tls_start=30, connect_end=55.7)
        assert pt.tls_ms() == 25.7

    def test_to_dict(self) -> None:
        pt = PerformanceTiming(
            navigation_start=1,
            response_start=201,
            dom_interactive=501,
            dom_content_loaded=601,
            dom_complete=1001,
            load_event_end=1051,
        )
        d = pt.to_dict()
        assert d["ttfb_ms"] == 200.0
        assert d["dom_interactive_ms"] == 500.0
        assert d["dom_content_loaded_ms"] == 600.0
        assert d["load_event_ms"] == 1050.0

    def test_to_dict_empty(self) -> None:
        pt = PerformanceTiming()
        d = pt.to_dict()
        assert d == {}


class TestWebVitals:
    def test_to_dict_empty(self) -> None:
        wv = WebVitals()
        d = wv.to_dict()
        assert d == {}

    def test_to_dict_populated(self) -> None:
        wv = WebVitals(
            fcp_ms=1200.5,
            lcp_ms=2500.3,
            lcp_element="<img src='hero.jpg'>",
            lcp_tag="IMG",
            cls=0.15,
            cls_shifts=[{"value": 0.1, "startTime": 100}],
            tbt_ms=350.0,
            long_tasks=[{"start": 100, "duration": 120, "blocking": 70}],
        )
        d = wv.to_dict()
        assert d["fcp_ms"] == 1200.5
        assert d["lcp_ms"] == 2500.3
        assert d["lcp_element"] == "<img src='hero.jpg'>"
        assert d["lcp_tag"] == "IMG"
        assert d["cls"] == 0.15
        assert d["cls_shifts"] == [{"value": 0.1, "startTime": 100}]
        assert d["tbt_ms"] == 350.0
        assert d["long_task_count"] == 1


class TestDOMMetrics:
    def test_to_dict(self) -> None:
        dm = DOMMetrics(
            node_count=1500,
            max_depth=15,
            element_count=1200,
            script_count=10,
            style_count=3,
            iframe_count=1,
            image_count=20,
            link_count=50,
        )
        d = dm.to_dict()
        assert d["node_count"] == 1500
        assert d["max_depth"] == 15
        assert d["script_count"] == 10
        assert d["iframe_count"] == 1


class TestResourceSummary:
    def test_to_dict(self) -> None:
        rs = ResourceSummary(
            total_requests=50,
            total_transfer_bytes=500000,
            total_resource_bytes=1200000,
            first_party_requests=30,
            third_party_requests=20,
            by_type={"js": {"count": 10, "transfer_bytes": 200000, "resource_bytes": 500000}},
        )
        d = rs.to_dict()
        assert d["total_requests"] == 50
        assert d["first_party_requests"] == 30
        assert d["by_type"]["js"]["count"] == 10


class TestBrowserResult:
    def test_to_dict_minimal(self) -> None:
        br = BrowserResult(url="http://example.com/")
        d = br.to_dict()
        assert d["url"] == "http://example.com/"
        assert d["status"] == "ERROR"
        assert d["profile"] == "DESKTOP"
        assert "errors" not in d

    def test_to_dict_with_errors(self) -> None:
        br = BrowserResult(url="http://example.com/", errors=["Timeout"])
        d = br.to_dict()
        assert d["errors"] == ["Timeout"]

    def test_to_dict_with_console_errors(self) -> None:
        br = BrowserResult(
            url="http://example.com/",
            console_messages=[
                ConsoleMessage(type="error", text="TypeError"),
                ConsoleMessage(type="log", text="Info msg"),
            ],
        )
        d = br.to_dict()
        assert len(d["console_errors"]) == 1
        assert d["console_errors"][0]["text"] == "TypeError"


class TestClassifyResourceType:
    def test_known_types(self) -> None:
        assert _classify_resource_type("document") == "html"
        assert _classify_resource_type("stylesheet") == "css"
        assert _classify_resource_type("script") == "js"
        assert _classify_resource_type("image") == "image"
        assert _classify_resource_type("font") == "font"
        assert _classify_resource_type("xhr") == "xhr"
        assert _classify_resource_type("fetch") == "fetch"

    def test_unknown_type(self) -> None:
        assert _classify_resource_type("something") == "something"

    def test_empty_type(self) -> None:
        assert _classify_resource_type("") == "other"


class TestBuildResourceSummary:
    def test_empty(self) -> None:
        summary = _build_resource_summary([], "example.com")
        assert summary.total_requests == 0
        assert summary.by_type == {}

    def test_mixed_resources(self) -> None:
        resources = [
            NetworkRequest(url="http://example.com/page", resource_type="html", transfer_size=5000, is_third_party=False),
            NetworkRequest(url="http://example.com/style.css", resource_type="css", transfer_size=2000, is_third_party=False),
            NetworkRequest(url="http://cdn.other.com/lib.js", resource_type="js", transfer_size=30000, is_third_party=True),
        ]
        summary = _build_resource_summary(resources, "example.com")
        assert summary.total_requests == 3
        assert summary.total_transfer_bytes == 37000
        assert summary.first_party_requests == 2
        assert summary.third_party_requests == 1
        assert summary.by_type["html"]["count"] == 1
        assert summary.by_type["js"]["transfer_bytes"] == 30000
        assert len(summary.largest_resources) == 3
        assert summary.largest_resources[0]["transfer_bytes"] == 30000


class TestFindChromium:
    @mock.patch("glob.glob", return_value=[])
    def test_not_found(self, _mock_glob: mock.Mock) -> None:
        assert _find_chromium() == ""

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch("glob.glob", return_value=["/opt/pw-browsers/chromium-1194/chrome-linux/chrome"])
    def test_found(self, _mock_glob: mock.Mock, _mock_isfile: mock.Mock) -> None:
        path = _find_chromium()
        assert path == "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


class TestExecuteBrowserAuditSSRF:
    def test_empty_url_blocked(self) -> None:
        results = execute_browser_audit("")
        assert len(results) == 1
        assert results[0].status == BrowserStatus.BLOCKED

    def test_ftp_blocked(self) -> None:
        results = execute_browser_audit("ftp://example.com")
        assert len(results) == 1
        assert results[0].status == BrowserStatus.BLOCKED

    @mock.patch("ope.url.validate_target")
    def test_localhost_blocked(self, mock_vt: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://localhost", status=TargetStatus.BLOCKED,
            normalized="", reason="Restricted address",
        )
        results = execute_browser_audit("http://localhost")
        assert len(results) == 1
        assert results[0].status == BrowserStatus.BLOCKED

    @mock.patch("ope.url.validate_target")
    def test_private_ip_blocked(self, mock_vt: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://internal.example.com", status=TargetStatus.BLOCKED,
            normalized="", reason="Restricted address",
        )
        results = execute_browser_audit("http://internal.example.com")
        assert len(results) == 1
        assert results[0].status == BrowserStatus.BLOCKED


class TestExecuteBrowserAuditProfiles:
    @mock.patch("ope.browser._run_profile")
    @mock.patch("ope.url.validate_target")
    def test_runs_configured_profiles(self, mock_vt: mock.Mock, mock_run: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_run.return_value = BrowserResult(url="http://example.com/", status=BrowserStatus.SUCCESS)

        cfg = BrowserConfig(profiles=[DeviceProfile.DESKTOP, DeviceProfile.MOBILE])
        results = execute_browser_audit("http://example.com", config=cfg)
        assert len(results) == 2
        assert mock_run.call_count == 2

    @mock.patch("ope.browser._run_profile")
    @mock.patch("ope.url.validate_target")
    def test_single_profile(self, mock_vt: mock.Mock, mock_run: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_run.return_value = BrowserResult(url="http://example.com/", status=BrowserStatus.SUCCESS)

        cfg = BrowserConfig(profiles=[DeviceProfile.MOBILE])
        results = execute_browser_audit("http://example.com", config=cfg)
        assert len(results) == 1
        call_args = mock_run.call_args
        assert call_args[0][1] == DeviceProfile.MOBILE
