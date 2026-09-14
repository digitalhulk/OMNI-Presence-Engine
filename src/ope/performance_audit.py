"""Performance audit orchestrator — browser execution + analysis pipeline."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .browser import (
    BrowserConfig,
    BrowserResult,
    BrowserStatus,
    DeviceProfile,
    execute_browser_audit,
)
from .performance import PerformanceReport, analyze_performance
from .url import TargetStatus, validate_target


@dataclass
class PerformanceAuditConfig:
    profiles: list[DeviceProfile] = field(
        default_factory=lambda: [DeviceProfile.DESKTOP, DeviceProfile.MOBILE]
    )
    timeout_ms: int = 30000
    navigation_timeout_ms: int = 30000
    capture_screenshot: bool = True
    collect_console: bool = True
    max_resources: int = 500
    chromium_path: str = ""
    headless: bool = True


@dataclass
class PerformanceAuditResult:
    target: str
    normalized_target: str = ""
    status: str = "ERROR"
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_s: float = 0.0
    error: str = ""
    browser_results: list[BrowserResult] = field(default_factory=list)
    performance_report: PerformanceReport | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "target": self.target,
            "normalized_target": self.normalized_target,
            "status": self.status,
            "started_at": self.started_at,
            "duration_s": round(self.duration_s, 2),
        }
        if self.error:
            d["error"] = self.error
        if self.browser_results:
            d["browser_results"] = [br.to_dict() for br in self.browser_results]
        if self.performance_report:
            d["performance_report"] = self.performance_report.to_dict()
        return d


def performance_audit(
    url: str,
    config: PerformanceAuditConfig | None = None,
) -> PerformanceAuditResult:
    cfg = config or PerformanceAuditConfig()
    start = time.time()
    result = PerformanceAuditResult(target=url, started_at=start)

    validation = validate_target(url)
    if validation.status not in (TargetStatus.VALID,):
        result.status = "INVALID_TARGET"
        result.error = validation.reason or f"Invalid target: {validation.status.value}"
        result.completed_at = time.time()
        result.duration_s = result.completed_at - start
        return result

    result.normalized_target = validation.normalized

    browser_cfg = BrowserConfig(
        timeout_ms=cfg.timeout_ms,
        navigation_timeout_ms=cfg.navigation_timeout_ms,
        profiles=cfg.profiles,
        capture_screenshot=cfg.capture_screenshot,
        collect_console=cfg.collect_console,
        max_resources=cfg.max_resources,
        chromium_path=cfg.chromium_path,
        headless=cfg.headless,
    )

    try:
        browser_results = execute_browser_audit(result.normalized_target, browser_cfg)
    except Exception as exc:
        result.status = "BROWSER_ERROR"
        result.error = f"Browser execution failed: {exc}"
        result.completed_at = time.time()
        result.duration_s = result.completed_at - start
        return result

    result.browser_results = browser_results

    all_failed = all(br.status != BrowserStatus.SUCCESS for br in browser_results)
    if all_failed:
        errors = []
        for br in browser_results:
            errors.extend(br.errors)
        result.status = "BROWSER_ERROR"
        result.error = "; ".join(errors[:5]) or "All browser profiles failed"
        result.completed_at = time.time()
        result.duration_s = result.completed_at - start
        return result

    try:
        report = analyze_performance(browser_results)
        result.performance_report = report
    except Exception as exc:
        result.status = "ANALYSIS_ERROR"
        result.error = f"Performance analysis failed: {exc}"
        result.completed_at = time.time()
        result.duration_s = result.completed_at - start
        return result

    result.status = "COMPLETED"
    result.completed_at = time.time()
    result.duration_s = result.completed_at - start
    return result
