"""Browser execution engine — provider-neutral abstraction over Playwright."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BrowserStatus(str, Enum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    NAVIGATION_ERROR = "NAVIGATION_ERROR"
    CRASH = "CRASH"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class DeviceProfile(str, Enum):
    DESKTOP = "DESKTOP"
    MOBILE = "MOBILE"


DEVICE_CONFIGS: dict[DeviceProfile, dict[str, Any]] = {
    DeviceProfile.DESKTOP: {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPE-Audit/0.3",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
    DeviceProfile.MOBILE: {
        "viewport": {"width": 412, "height": 915},
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 OPE-Audit/0.3",
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
    },
}


@dataclass
class BrowserConfig:
    timeout_ms: int = 30000
    navigation_timeout_ms: int = 30000
    max_redirects: int = 10
    max_dom_nodes: int = 100000
    max_screenshot_bytes: int = 5 * 1024 * 1024
    max_resources: int = 500
    max_resource_bytes: int = 50 * 1024 * 1024
    profiles: list[DeviceProfile] = field(default_factory=lambda: [DeviceProfile.DESKTOP])
    capture_screenshot: bool = True
    collect_console: bool = True
    collect_coverage: bool = False
    headless: bool = True
    chromium_path: str = ""


@dataclass
class NetworkRequest:
    url: str
    method: str = "GET"
    resource_type: str = ""
    status: int = 0
    mime_type: str = ""
    transfer_size: int = 0
    resource_size: int = 0
    initiator: str = ""
    is_third_party: bool = False
    timing: dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    from_cache: bool = False
    protocol: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"url": self.url, "method": self.method, "resource_type": self.resource_type, "status": self.status}
        if self.mime_type: d["mime_type"] = self.mime_type
        d["transfer_size"] = self.transfer_size; d["resource_size"] = self.resource_size
        if self.initiator: d["initiator"] = self.initiator
        d["is_third_party"] = self.is_third_party
        if self.timing: d["timing"] = self.timing
        d["duration_ms"] = round(self.duration_ms, 1)
        d["from_cache"] = self.from_cache
        if self.protocol: d["protocol"] = self.protocol
        if self.error: d["error"] = self.error
        return d


@dataclass
class ConsoleMessage:
    type: str
    text: str
    url: str = ""
    line: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text[:500], "url": self.url, "line": self.line}


@dataclass
class PerformanceTiming:
    navigation_start: float = 0.0
    dns_start: float = 0.0
    dns_end: float = 0.0
    connect_start: float = 0.0
    connect_end: float = 0.0
    tls_start: float = 0.0
    request_start: float = 0.0
    response_start: float = 0.0
    response_end: float = 0.0
    dom_interactive: float = 0.0
    dom_content_loaded: float = 0.0
    dom_complete: float = 0.0
    load_event_end: float = 0.0

    def ttfb(self) -> float | None:
        if self.response_start > 0 and self.navigation_start > 0:
            return round(self.response_start - self.navigation_start, 1)
        return None

    def dns_ms(self) -> float | None:
        if self.dns_end > 0 and self.dns_start > 0:
            return round(self.dns_end - self.dns_start, 1)
        return None

    def tls_ms(self) -> float | None:
        if self.tls_start > 0 and self.connect_end > 0:
            return round(self.connect_end - self.tls_start, 1)
        return None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        ttfb = self.ttfb()
        if ttfb is not None: d["ttfb_ms"] = ttfb
        dns = self.dns_ms()
        if dns is not None: d["dns_ms"] = dns
        tls = self.tls_ms()
        if tls is not None: d["tls_ms"] = tls
        if self.dom_interactive > 0: d["dom_interactive_ms"] = round(self.dom_interactive - self.navigation_start, 1)
        if self.dom_content_loaded > 0: d["dom_content_loaded_ms"] = round(self.dom_content_loaded - self.navigation_start, 1)
        if self.dom_complete > 0: d["dom_complete_ms"] = round(self.dom_complete - self.navigation_start, 1)
        if self.load_event_end > 0: d["load_event_ms"] = round(self.load_event_end - self.navigation_start, 1)
        return d


@dataclass
class WebVitals:
    fcp_ms: float | None = None
    lcp_ms: float | None = None
    lcp_element: str | None = None
    lcp_url: str | None = None
    lcp_tag: str | None = None
    cls: float | None = None
    cls_shifts: list[dict[str, Any]] = field(default_factory=list)
    tbt_ms: float | None = None
    long_tasks: list[dict[str, Any]] = field(default_factory=list)
    inp_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.fcp_ms is not None: d["fcp_ms"] = round(self.fcp_ms, 1)
        if self.lcp_ms is not None: d["lcp_ms"] = round(self.lcp_ms, 1)
        if self.lcp_element: d["lcp_element"] = self.lcp_element
        if self.lcp_url: d["lcp_url"] = self.lcp_url
        if self.lcp_tag: d["lcp_tag"] = self.lcp_tag
        if self.cls is not None: d["cls"] = round(self.cls, 4)
        if self.cls_shifts: d["cls_shifts"] = self.cls_shifts[:10]
        if self.tbt_ms is not None: d["tbt_ms"] = round(self.tbt_ms, 1)
        if self.long_tasks: d["long_task_count"] = len(self.long_tasks); d["long_tasks"] = self.long_tasks[:10]
        if self.inp_ms is not None: d["inp_ms"] = round(self.inp_ms, 1)
        return d


@dataclass
class DOMMetrics:
    node_count: int = 0
    max_depth: int = 0
    element_count: int = 0
    script_count: int = 0
    style_count: int = 0
    iframe_count: int = 0
    image_count: int = 0
    link_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count, "max_depth": self.max_depth,
            "element_count": self.element_count, "script_count": self.script_count,
            "style_count": self.style_count, "iframe_count": self.iframe_count,
            "image_count": self.image_count, "link_count": self.link_count,
        }


@dataclass
class ResourceSummary:
    total_requests: int = 0
    total_transfer_bytes: int = 0
    total_resource_bytes: int = 0
    first_party_requests: int = 0
    third_party_requests: int = 0
    by_type: dict[str, dict[str, int]] = field(default_factory=dict)
    largest_resources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_transfer_bytes": self.total_transfer_bytes,
            "total_resource_bytes": self.total_resource_bytes,
            "first_party_requests": self.first_party_requests,
            "third_party_requests": self.third_party_requests,
            "by_type": self.by_type,
            "largest_resources": self.largest_resources[:10],
        }


@dataclass
class BrowserResult:
    url: str
    final_url: str = ""
    status: BrowserStatus = BrowserStatus.ERROR
    status_code: int = 0
    profile: DeviceProfile = DeviceProfile.DESKTOP
    source_html: str = ""
    rendered_html: str = ""
    source_html_length: int = 0
    rendered_html_length: int = 0
    dom_metrics: DOMMetrics = field(default_factory=DOMMetrics)
    timing: PerformanceTiming = field(default_factory=PerformanceTiming)
    vitals: WebVitals = field(default_factory=WebVitals)
    resources: list[NetworkRequest] = field(default_factory=list)
    resource_summary: ResourceSummary = field(default_factory=ResourceSummary)
    console_messages: list[ConsoleMessage] = field(default_factory=list)
    screenshot: bytes | None = None
    screenshot_path: str = ""
    errors: list[str] = field(default_factory=list)
    collection_context: dict[str, Any] = field(default_factory=dict)
    observed_at: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "url": self.url, "final_url": self.final_url,
            "status": self.status.value, "status_code": self.status_code,
            "profile": self.profile.value,
            "source_html_length": self.source_html_length,
            "rendered_html_length": self.rendered_html_length,
            "dom_metrics": self.dom_metrics.to_dict(),
            "timing": self.timing.to_dict(),
            "vitals": self.vitals.to_dict(),
            "resource_summary": self.resource_summary.to_dict(),
            "duration_ms": round(self.duration_ms, 1),
            "observed_at": self.observed_at,
        }
        if self.errors: d["errors"] = self.errors[:20]
        if self.console_messages: d["console_errors"] = [m.to_dict() for m in self.console_messages if m.type == "error"][:10]
        if self.screenshot_path: d["screenshot_path"] = self.screenshot_path
        if self.collection_context: d["collection_context"] = self.collection_context
        return d


def _find_chromium() -> str:
    """Locate the pre-installed Chromium binary."""
    import glob
    import os
    patterns = [
        "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
        "/opt/pw-browsers/chromium-*/chrome",
        "/opt/pw-browsers/chromium/chrome",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches and os.path.isfile(matches[0]):
            return matches[0]
    return ""


def _classify_resource_type(pw_type: str) -> str:
    mapping = {
        "document": "html", "stylesheet": "css", "script": "js",
        "image": "image", "font": "font", "media": "media",
        "xhr": "xhr", "fetch": "fetch", "websocket": "websocket",
        "manifest": "manifest", "other": "other",
    }
    return mapping.get(pw_type, pw_type or "other")


def _build_resource_summary(resources: list[NetworkRequest], origin_host: str) -> ResourceSummary:
    summary = ResourceSummary()
    by_type: dict[str, dict[str, int]] = {}
    for r in resources:
        summary.total_requests += 1
        summary.total_transfer_bytes += r.transfer_size
        summary.total_resource_bytes += r.resource_size
        if r.is_third_party:
            summary.third_party_requests += 1
        else:
            summary.first_party_requests += 1
        rt = r.resource_type or "other"
        if rt not in by_type:
            by_type[rt] = {"count": 0, "transfer_bytes": 0, "resource_bytes": 0}
        by_type[rt]["count"] += 1
        by_type[rt]["transfer_bytes"] += r.transfer_size
        by_type[rt]["resource_bytes"] += r.resource_size
    summary.by_type = by_type
    sorted_by_size = sorted(resources, key=lambda r: r.transfer_size, reverse=True)
    summary.largest_resources = [{"url": r.url[:200], "type": r.resource_type, "transfer_bytes": r.transfer_size} for r in sorted_by_size[:10]]
    return summary


def execute_browser_audit(url: str, config: BrowserConfig | None = None) -> list[BrowserResult]:
    """Run browser-based audit for each configured device profile."""
    from .url import TargetStatus, validate_target

    cfg = config or BrowserConfig()
    validation = validate_target(url, resolve_dns=False)
    if validation.status != TargetStatus.VALID:
        return [BrowserResult(url=url, status=BrowserStatus.BLOCKED, errors=[validation.reason or f"Invalid target: {validation.status.value}"])]

    normalized = validation.normalized
    results: list[BrowserResult] = []
    for profile in cfg.profiles:
        result = _run_profile(normalized, profile, cfg)
        results.append(result)
    return results


def _run_profile(url: str, profile: DeviceProfile, config: BrowserConfig) -> BrowserResult:
    """Execute a single browser profile run."""
    import urllib.parse

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    result = BrowserResult(url=url, profile=profile, observed_at=time.time())
    device_cfg = DEVICE_CONFIGS[profile]
    origin_host = (urllib.parse.urlparse(url).hostname or "").lower()
    resources: list[NetworkRequest] = []
    start_time = time.perf_counter()

    chromium_path = config.chromium_path or _find_chromium()

    try:
        with sync_playwright() as pw:
            launch_args: dict[str, Any] = {"headless": config.headless}
            if chromium_path:
                launch_args["executable_path"] = chromium_path
            browser = pw.chromium.launch(**launch_args)
            try:
                context = browser.new_context(
                    viewport=device_cfg["viewport"],
                    user_agent=device_cfg["user_agent"],
                    device_scale_factor=device_cfg["device_scale_factor"],
                    is_mobile=device_cfg["is_mobile"],
                    has_touch=device_cfg["has_touch"],
                    ignore_https_errors=False,
                )
                context.set_default_timeout(config.timeout_ms)
                context.set_default_navigation_timeout(config.navigation_timeout_ms)
                page = context.new_page()

                def on_request(req: Any) -> None:
                    if len(resources) >= config.max_resources:
                        return
                    nr = NetworkRequest(url=req.url, method=req.method, resource_type=_classify_resource_type(req.resource_type))
                    host = (urllib.parse.urlparse(req.url).hostname or "").lower()
                    nr.is_third_party = host != origin_host and not host.endswith("." + origin_host)
                    resources.append(nr)

                def on_response(resp: Any) -> None:
                    for nr in reversed(resources):
                        if nr.url == resp.url and nr.status == 0:
                            nr.status = resp.status
                            headers = resp.headers
                            nr.mime_type = headers.get("content-type", "").split(";")[0].strip()
                            cl = headers.get("content-length", "")
                            if cl.isdigit():
                                nr.transfer_size = int(cl)
                            break

                console_msgs: list[ConsoleMessage] = []

                def on_console(msg: Any) -> None:
                    if len(console_msgs) < 100:
                        console_msgs.append(ConsoleMessage(type=msg.type, text=msg.text[:500]))

                page.on("request", on_request)
                page.on("response", on_response)
                page.on("console", on_console)

                try:
                    resp = page.goto(url, wait_until="networkidle", timeout=config.navigation_timeout_ms)
                except PlaywrightTimeout:
                    try:
                        resp = page.goto(url, wait_until="load", timeout=config.navigation_timeout_ms)
                    except PlaywrightTimeout:
                        result.status = BrowserStatus.TIMEOUT
                        result.errors.append("Navigation timeout")
                        result.duration_ms = (time.perf_counter() - start_time) * 1000
                        return result

                if resp:
                    result.status_code = resp.status
                    result.final_url = resp.url

                result.source_html = page.content()
                result.source_html_length = len(result.source_html)

                page.wait_for_timeout(2000)

                result.rendered_html = page.content()
                result.rendered_html_length = len(result.rendered_html)

                _collect_timing(page, result)
                _collect_vitals(page, result)
                _collect_dom_metrics(page, result)

                result.resources = resources
                result.resource_summary = _build_resource_summary(resources, origin_host)
                result.console_messages = console_msgs

                if config.capture_screenshot:
                    try:
                        screenshot = page.screenshot(full_page=False, type="png")
                        if len(screenshot) <= config.max_screenshot_bytes:
                            result.screenshot = screenshot
                    except Exception:
                        pass

                result.status = BrowserStatus.SUCCESS
                result.collection_context = {
                    "profile": profile.value,
                    "viewport": device_cfg["viewport"],
                    "user_agent": device_cfg["user_agent"],
                    "chromium_path": chromium_path or "default",
                }

            finally:
                browser.close()

    except PlaywrightError as exc:
        result.status = BrowserStatus.CRASH
        result.errors.append(f"Browser error: {exc}")
    except Exception as exc:
        result.status = BrowserStatus.ERROR
        result.errors.append(f"{type(exc).__name__}: {exc}")

    result.duration_ms = (time.perf_counter() - start_time) * 1000
    return result


def _collect_timing(page: Any, result: BrowserResult) -> None:
    try:
        raw = page.evaluate("""() => {
            const e = performance.getEntriesByType('navigation')[0];
            if (!e) return null;
            return {
                navigationStart: e.startTime, dnsStart: e.domainLookupStart,
                dnsEnd: e.domainLookupEnd, connectStart: e.connectStart,
                connectEnd: e.connectEnd, tlsStart: e.secureConnectionStart,
                requestStart: e.requestStart, responseStart: e.responseStart,
                responseEnd: e.responseEnd, domInteractive: e.domInteractive,
                domContentLoaded: e.domContentLoadedEventEnd,
                domComplete: e.domComplete, loadEventEnd: e.loadEventEnd,
            };
        }""")
        if raw:
            result.timing = PerformanceTiming(
                navigation_start=raw.get("navigationStart", 0),
                dns_start=raw.get("dnsStart", 0), dns_end=raw.get("dnsEnd", 0),
                connect_start=raw.get("connectStart", 0), connect_end=raw.get("connectEnd", 0),
                tls_start=raw.get("tlsStart", 0), request_start=raw.get("requestStart", 0),
                response_start=raw.get("responseStart", 0), response_end=raw.get("responseEnd", 0),
                dom_interactive=raw.get("domInteractive", 0),
                dom_content_loaded=raw.get("domContentLoaded", 0),
                dom_complete=raw.get("domComplete", 0),
                load_event_end=raw.get("loadEventEnd", 0),
            )
    except Exception as exc:
        result.errors.append(f"Timing collection failed: {exc}")


def _collect_vitals(page: Any, result: BrowserResult) -> None:
    try:
        vitals_raw = page.evaluate("""() => {
            const result = {};
            const paintEntries = performance.getEntriesByType('paint');
            for (const e of paintEntries) {
                if (e.name === 'first-contentful-paint') result.fcp = e.startTime;
            }
            const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
            if (lcpEntries.length > 0) {
                const lcp = lcpEntries[lcpEntries.length - 1];
                result.lcp = lcp.startTime;
                result.lcpUrl = lcp.url || '';
                const el = lcp.element;
                if (el) {
                    result.lcpTag = el.tagName || '';
                    result.lcpElement = el.outerHTML ? el.outerHTML.substring(0, 300) : '';
                }
            }
            const clsEntries = performance.getEntriesByType('layout-shift');
            let clsTotal = 0;
            const shifts = [];
            for (const e of clsEntries) {
                if (!e.hadRecentInput) {
                    clsTotal += e.value;
                    if (shifts.length < 10) {
                        const sources = [];
                        if (e.sources) {
                            for (const s of e.sources) {
                                sources.push({node: s.node ? s.node.nodeName : '', rect: s.currentRect ? {x: s.currentRect.x, y: s.currentRect.y, w: s.currentRect.width, h: s.currentRect.height} : null});
                            }
                        }
                        shifts.push({value: e.value, startTime: e.startTime, sources});
                    }
                }
            }
            result.cls = clsTotal;
            result.clsShifts = shifts;
            const longTasks = performance.getEntriesByType('longtask');
            let tbt = 0;
            const tasks = [];
            for (const e of longTasks) {
                const blocking = Math.max(0, e.duration - 50);
                tbt += blocking;
                if (tasks.length < 20) tasks.push({start: e.startTime, duration: e.duration, blocking});
            }
            result.tbt = tbt;
            result.longTasks = tasks;
            return result;
        }""")
        if vitals_raw:
            result.vitals = WebVitals(
                fcp_ms=vitals_raw.get("fcp"),
                lcp_ms=vitals_raw.get("lcp"),
                lcp_element=vitals_raw.get("lcpElement"),
                lcp_url=vitals_raw.get("lcpUrl"),
                lcp_tag=vitals_raw.get("lcpTag"),
                cls=vitals_raw.get("cls"),
                cls_shifts=vitals_raw.get("clsShifts", []),
                tbt_ms=vitals_raw.get("tbt"),
                long_tasks=vitals_raw.get("longTasks", []),
            )
    except Exception as exc:
        result.errors.append(f"Vitals collection failed: {exc}")


def _collect_dom_metrics(page: Any, result: BrowserResult) -> None:
    try:
        dom_raw = page.evaluate("""() => {
            const all = document.querySelectorAll('*');
            let maxDepth = 0;
            for (let i = 0; i < Math.min(all.length, 50000); i++) {
                let depth = 0; let el = all[i];
                while (el.parentElement) { depth++; el = el.parentElement; if (depth > 100) break; }
                if (depth > maxDepth) maxDepth = depth;
            }
            return {
                nodeCount: document.querySelectorAll('*').length,
                maxDepth,
                elementCount: document.querySelectorAll('*').length,
                scriptCount: document.querySelectorAll('script').length,
                styleCount: document.querySelectorAll('style, link[rel="stylesheet"]').length,
                iframeCount: document.querySelectorAll('iframe').length,
                imageCount: document.querySelectorAll('img, picture, svg').length,
                linkCount: document.querySelectorAll('a[href]').length,
            };
        }""")
        if dom_raw:
            result.dom_metrics = DOMMetrics(
                node_count=dom_raw.get("nodeCount", 0),
                max_depth=dom_raw.get("maxDepth", 0),
                element_count=dom_raw.get("elementCount", 0),
                script_count=dom_raw.get("scriptCount", 0),
                style_count=dom_raw.get("styleCount", 0),
                iframe_count=dom_raw.get("iframeCount", 0),
                image_count=dom_raw.get("imageCount", 0),
                link_count=dom_raw.get("linkCount", 0),
            )
    except Exception as exc:
        result.errors.append(f"DOM metrics collection failed: {exc}")
