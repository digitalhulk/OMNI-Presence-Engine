"""Tests for the performance audit orchestrator."""
from __future__ import annotations

import socket
from unittest import mock

from ope.browser import (
    BrowserResult,
    BrowserStatus,
    DeviceProfile,
    WebVitals,
)
from ope.performance_audit import (
    PerformanceAuditConfig,
    PerformanceAuditResult,
    performance_audit,
)


class TestPerformanceAuditConfig:
    def test_defaults(self) -> None:
        cfg = PerformanceAuditConfig()
        assert cfg.profiles == [DeviceProfile.DESKTOP, DeviceProfile.MOBILE]
        assert cfg.timeout_ms == 30000
        assert cfg.capture_screenshot is True
        assert cfg.headless is True
        assert cfg.max_resources == 500

    def test_custom(self) -> None:
        cfg = PerformanceAuditConfig(
            profiles=[DeviceProfile.MOBILE],
            timeout_ms=10000,
            capture_screenshot=False,
        )
        assert len(cfg.profiles) == 1
        assert cfg.timeout_ms == 10000
        assert cfg.capture_screenshot is False


class TestPerformanceAuditResult:
    def test_to_dict_minimal(self) -> None:
        r = PerformanceAuditResult(target="http://example.com/", status="COMPLETED")
        d = r.to_dict()
        assert d["target"] == "http://example.com/"
        assert d["status"] == "COMPLETED"
        assert "error" not in d

    def test_to_dict_with_error(self) -> None:
        r = PerformanceAuditResult(target="http://example.com/", status="INVALID_TARGET", error="bad url")
        d = r.to_dict()
        assert d["error"] == "bad url"


class TestPerformanceAuditInvalidTarget:
    def test_empty_url(self) -> None:
        result = performance_audit("")
        assert result.status == "INVALID_TARGET"
        assert result.error

    def test_ftp_url(self) -> None:
        result = performance_audit("ftp://example.com")
        assert result.status == "INVALID_TARGET"

    def test_localhost_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]
            result = performance_audit("http://localhost")
            assert result.status == "INVALID_TARGET"

    def test_private_ip_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))]
            result = performance_audit("http://router.local")
            assert result.status == "INVALID_TARGET"


class TestPerformanceAuditOrchestration:
    @mock.patch("ope.performance_audit.execute_browser_audit")
    @mock.patch("ope.performance_audit.validate_target")
    def test_successful_audit(self, mock_vt: mock.Mock, mock_exec: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_exec.return_value = [
            BrowserResult(
                url="http://example.com/",
                status=BrowserStatus.SUCCESS,
                status_code=200,
                profile=DeviceProfile.DESKTOP,
                vitals=WebVitals(fcp_ms=1200, lcp_ms=2400),
            ),
        ]
        result = performance_audit("http://example.com")
        assert result.status == "COMPLETED"
        assert result.normalized_target == "http://example.com/"
        assert result.performance_report is not None
        assert len(result.browser_results) == 1

    @mock.patch("ope.performance_audit.execute_browser_audit")
    @mock.patch("ope.performance_audit.validate_target")
    def test_all_profiles_fail(self, mock_vt: mock.Mock, mock_exec: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_exec.return_value = [
            BrowserResult(url="http://example.com/", status=BrowserStatus.TIMEOUT, errors=["Timeout"]),
        ]
        result = performance_audit("http://example.com")
        assert result.status == "BROWSER_ERROR"
        assert "Timeout" in result.error

    @mock.patch("ope.performance_audit.execute_browser_audit")
    @mock.patch("ope.performance_audit.validate_target")
    def test_browser_exception(self, mock_vt: mock.Mock, mock_exec: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_exec.side_effect = RuntimeError("Playwright not installed")
        result = performance_audit("http://example.com")
        assert result.status == "BROWSER_ERROR"
        assert "Playwright" in result.error

    @mock.patch("ope.performance_audit.execute_browser_audit")
    @mock.patch("ope.performance_audit.validate_target")
    def test_multi_profile_partial_failure(self, mock_vt: mock.Mock, mock_exec: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_exec.return_value = [
            BrowserResult(
                url="http://example.com/", status=BrowserStatus.SUCCESS,
                status_code=200, profile=DeviceProfile.DESKTOP,
            ),
            BrowserResult(
                url="http://example.com/", status=BrowserStatus.TIMEOUT,
                profile=DeviceProfile.MOBILE, errors=["Mobile timeout"],
            ),
        ]
        result = performance_audit("http://example.com")
        assert result.status == "COMPLETED"
        assert len(result.browser_results) == 2

    @mock.patch("ope.performance_audit.execute_browser_audit")
    @mock.patch("ope.performance_audit.validate_target")
    def test_result_has_duration(self, mock_vt: mock.Mock, mock_exec: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_exec.return_value = [
            BrowserResult(url="http://example.com/", status=BrowserStatus.SUCCESS, status_code=200),
        ]
        result = performance_audit("http://example.com")
        assert result.duration_s >= 0
        assert result.started_at > 0
        assert result.completed_at >= result.started_at
