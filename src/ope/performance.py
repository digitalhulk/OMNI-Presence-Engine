"""Performance analysis — evidence-backed findings from browser execution data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .browser import BrowserResult, BrowserStatus

CWV_THRESHOLDS: dict[str, dict[str, float]] = {
    "fcp": {"good": 1800, "poor": 3000},
    "lcp": {"good": 2500, "poor": 4000},
    "cls": {"good": 0.1, "poor": 0.25},
    "tbt": {"good": 200, "poor": 600},
    "inp": {"good": 200, "poor": 500},
    "ttfb": {"good": 800, "poor": 1800},
}


def _rating(value: float | None, metric: str) -> str:
    if value is None:
        return "UNKNOWN"
    thresholds = CWV_THRESHOLDS.get(metric)
    if not thresholds:
        return "UNKNOWN"
    if value <= thresholds["good"]:
        return "GOOD"
    if value <= thresholds["poor"]:
        return "NEEDS_IMPROVEMENT"
    return "POOR"


@dataclass
class Finding:
    module: str
    severity: str
    symptom: str
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    metric: str = ""
    profile: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "module": self.module,
            "severity": self.severity,
            "symptom": self.symptom,
            "evidence": self.evidence,
        }
        if self.recommendation:
            d["recommendation"] = self.recommendation
        if self.metric:
            d["metric"] = self.metric
        if self.profile:
            d["profile"] = self.profile
        return d


@dataclass
class PerformanceReport:
    url: str
    profiles: list[dict[str, Any]] = field(default_factory=list)
    vitals_summary: dict[str, dict[str, Any]] = field(default_factory=dict)
    resource_analysis: dict[str, Any] = field(default_factory=dict)
    dom_analysis: dict[str, Any] = field(default_factory=dict)
    render_analysis: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    status: str = "COMPLETED"
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "url": self.url,
            "status": self.status,
            "profiles": self.profiles,
            "vitals_summary": self.vitals_summary,
        }
        if self.resource_analysis:
            d["resource_analysis"] = self.resource_analysis
        if self.dom_analysis:
            d["dom_analysis"] = self.dom_analysis
        if self.render_analysis:
            d["render_analysis"] = self.render_analysis
        d["findings"] = [f.to_dict() for f in self.findings]
        if self.error:
            d["error"] = self.error
        return d


def analyze_performance(results: list[BrowserResult]) -> PerformanceReport:
    if not results:
        return PerformanceReport(url="", status="NO_DATA", error="No browser results")

    url = results[0].url
    report = PerformanceReport(url=url)

    for br in results:
        report.profiles.append({
            "profile": br.profile.value,
            "status": br.status.value,
            "status_code": br.status_code,
            "duration_ms": round(br.duration_ms, 1),
        })
        if br.status != BrowserStatus.SUCCESS:
            continue

        _analyze_vitals(br, report)
        _analyze_resources(br, report)
        _analyze_dom(br, report)
        _analyze_render_diff(br, report)

    return report


def _analyze_vitals(br: BrowserResult, report: PerformanceReport) -> None:
    v = br.vitals
    profile_key = br.profile.value
    summary: dict[str, Any] = {}

    if v.fcp_ms is not None:
        r = _rating(v.fcp_ms, "fcp")
        summary["fcp"] = {"value_ms": round(v.fcp_ms, 1), "rating": r}
        if r == "POOR":
            report.findings.append(Finding(
                module="performance.vitals", severity="HIGH",
                symptom=f"First Contentful Paint is {v.fcp_ms:.0f}ms (threshold: {CWV_THRESHOLDS['fcp']['poor']}ms)",
                evidence={"fcp_ms": round(v.fcp_ms, 1), "threshold_ms": CWV_THRESHOLDS["fcp"]["poor"]},
                recommendation="Reduce render-blocking resources, optimize server response time",
                metric="fcp", profile=profile_key,
            ))
        elif r == "NEEDS_IMPROVEMENT":
            report.findings.append(Finding(
                module="performance.vitals", severity="MEDIUM",
                symptom=f"FCP at {v.fcp_ms:.0f}ms needs improvement",
                evidence={"fcp_ms": round(v.fcp_ms, 1)},
                metric="fcp", profile=profile_key,
            ))

    if v.lcp_ms is not None:
        r = _rating(v.lcp_ms, "lcp")
        summary["lcp"] = {
            "value_ms": round(v.lcp_ms, 1), "rating": r,
        }
        if v.lcp_element:
            summary["lcp"]["element"] = v.lcp_element[:200]
        if v.lcp_url:
            summary["lcp"]["resource_url"] = v.lcp_url[:200]
        if v.lcp_tag:
            summary["lcp"]["tag"] = v.lcp_tag
        if r == "POOR":
            evidence: dict[str, Any] = {
                "lcp_ms": round(v.lcp_ms, 1),
                "threshold_ms": CWV_THRESHOLDS["lcp"]["poor"],
            }
            if v.lcp_tag:
                evidence["lcp_tag"] = v.lcp_tag
            if v.lcp_url:
                evidence["lcp_url"] = v.lcp_url[:200]
            report.findings.append(Finding(
                module="performance.vitals", severity="HIGH",
                symptom=f"Largest Contentful Paint is {v.lcp_ms:.0f}ms (poor)",
                evidence=evidence,
                recommendation="Optimize the LCP resource: preload images, use responsive formats, reduce TTFB",
                metric="lcp", profile=profile_key,
            ))
        elif r == "NEEDS_IMPROVEMENT":
            report.findings.append(Finding(
                module="performance.vitals", severity="MEDIUM",
                symptom=f"LCP at {v.lcp_ms:.0f}ms needs improvement",
                evidence={"lcp_ms": round(v.lcp_ms, 1)},
                metric="lcp", profile=profile_key,
            ))

    if v.cls is not None:
        r = _rating(v.cls, "cls")
        summary["cls"] = {"value": round(v.cls, 4), "rating": r, "shift_count": len(v.cls_shifts)}
        if r == "POOR":
            evidence_cls: dict[str, Any] = {"cls": round(v.cls, 4), "threshold": CWV_THRESHOLDS["cls"]["poor"]}
            if v.cls_shifts:
                evidence_cls["top_shifts"] = v.cls_shifts[:3]
            report.findings.append(Finding(
                module="performance.vitals", severity="HIGH",
                symptom=f"Cumulative Layout Shift is {v.cls:.4f} (poor)",
                evidence=evidence_cls,
                recommendation="Set explicit dimensions on images/embeds, avoid inserting content above fold",
                metric="cls", profile=profile_key,
            ))
        elif r == "NEEDS_IMPROVEMENT":
            report.findings.append(Finding(
                module="performance.vitals", severity="MEDIUM",
                symptom=f"CLS at {v.cls:.4f} needs improvement",
                evidence={"cls": round(v.cls, 4)},
                metric="cls", profile=profile_key,
            ))

    if v.tbt_ms is not None:
        r = _rating(v.tbt_ms, "tbt")
        summary["tbt"] = {"value_ms": round(v.tbt_ms, 1), "rating": r, "long_task_count": len(v.long_tasks)}
        if r == "POOR":
            report.findings.append(Finding(
                module="performance.vitals", severity="HIGH",
                symptom=f"Total Blocking Time is {v.tbt_ms:.0f}ms ({len(v.long_tasks)} long tasks)",
                evidence={"tbt_ms": round(v.tbt_ms, 1), "long_task_count": len(v.long_tasks)},
                recommendation="Break up long tasks, defer non-critical JavaScript, reduce third-party scripts",
                metric="tbt", profile=profile_key,
            ))

    ttfb = br.timing.ttfb()
    if ttfb is not None:
        r = _rating(ttfb, "ttfb")
        summary["ttfb"] = {"value_ms": ttfb, "rating": r}
        if r == "POOR":
            report.findings.append(Finding(
                module="performance.timing", severity="HIGH",
                symptom=f"Time to First Byte is {ttfb:.0f}ms (poor)",
                evidence={"ttfb_ms": ttfb, "threshold_ms": CWV_THRESHOLDS["ttfb"]["poor"]},
                recommendation="Optimize server response time, use CDN, enable caching",
                metric="ttfb", profile=profile_key,
            ))

    report.vitals_summary[profile_key] = summary


def _analyze_resources(br: BrowserResult, report: PerformanceReport) -> None:
    rs = br.resource_summary
    profile_key = br.profile.value
    analysis: dict[str, Any] = {
        "profile": profile_key,
        "total_requests": rs.total_requests,
        "total_transfer_bytes": rs.total_transfer_bytes,
        "total_resource_bytes": rs.total_resource_bytes,
        "first_party_requests": rs.first_party_requests,
        "third_party_requests": rs.third_party_requests,
        "by_type": rs.by_type,
    }

    if rs.total_requests > 100:
        report.findings.append(Finding(
            module="performance.resources", severity="MEDIUM",
            symptom=f"Page makes {rs.total_requests} network requests",
            evidence={"total_requests": rs.total_requests, "by_type": {k: v["count"] for k, v in rs.by_type.items()}},
            recommendation="Reduce HTTP requests: bundle scripts, use sprites, lazy-load below-fold resources",
            profile=profile_key,
        ))

    total_mb = rs.total_transfer_bytes / (1024 * 1024)
    if total_mb > 5:
        report.findings.append(Finding(
            module="performance.resources", severity="HIGH",
            symptom=f"Total page weight is {total_mb:.1f} MB",
            evidence={"total_transfer_mb": round(total_mb, 2)},
            recommendation="Compress resources, use modern image formats (WebP/AVIF), minify CSS/JS",
            profile=profile_key,
        ))
    elif total_mb > 2:
        report.findings.append(Finding(
            module="performance.resources", severity="MEDIUM",
            symptom=f"Page weight is {total_mb:.1f} MB",
            evidence={"total_transfer_mb": round(total_mb, 2)},
            profile=profile_key,
        ))

    if rs.third_party_requests > 20:
        report.findings.append(Finding(
            module="performance.resources", severity="MEDIUM",
            symptom=f"{rs.third_party_requests} third-party requests detected",
            evidence={"third_party_requests": rs.third_party_requests, "first_party_requests": rs.first_party_requests},
            recommendation="Audit third-party scripts, defer non-critical, consider self-hosting critical resources",
            profile=profile_key,
        ))

    js_info = rs.by_type.get("js", {})
    if js_info.get("count", 0) > 15:
        report.findings.append(Finding(
            module="performance.resources", severity="MEDIUM",
            symptom=f"{js_info['count']} JavaScript files loaded",
            evidence={"js_count": js_info["count"], "js_bytes": js_info.get("transfer_bytes", 0)},
            recommendation="Bundle and minify JavaScript, use code splitting, defer non-critical scripts",
            profile=profile_key,
        ))

    css_info = rs.by_type.get("css", {})
    if css_info.get("count", 0) > 10:
        report.findings.append(Finding(
            module="performance.resources", severity="LOW",
            symptom=f"{css_info['count']} CSS files loaded",
            evidence={"css_count": css_info["count"], "css_bytes": css_info.get("transfer_bytes", 0)},
            recommendation="Combine and minify CSS, inline critical CSS, defer non-critical stylesheets",
            profile=profile_key,
        ))

    report.resource_analysis = analysis


def _analyze_dom(br: BrowserResult, report: PerformanceReport) -> None:
    dm = br.dom_metrics
    profile_key = br.profile.value
    analysis: dict[str, Any] = {
        "profile": profile_key,
        "node_count": dm.node_count,
        "max_depth": dm.max_depth,
        "element_count": dm.element_count,
        "script_count": dm.script_count,
        "style_count": dm.style_count,
        "iframe_count": dm.iframe_count,
        "image_count": dm.image_count,
    }

    if dm.node_count > 3000:
        report.findings.append(Finding(
            module="performance.dom", severity="MEDIUM",
            symptom=f"Excessive DOM size: {dm.node_count} nodes",
            evidence={"node_count": dm.node_count},
            recommendation="Reduce DOM size: lazy-render off-screen content, virtualize large lists",
            profile=profile_key,
        ))

    if dm.max_depth > 32:
        report.findings.append(Finding(
            module="performance.dom", severity="LOW",
            symptom=f"Deep DOM nesting: max depth {dm.max_depth}",
            evidence={"max_depth": dm.max_depth},
            recommendation="Flatten DOM hierarchy, avoid deeply nested wrappers",
            profile=profile_key,
        ))

    if dm.iframe_count > 3:
        report.findings.append(Finding(
            module="performance.dom", severity="MEDIUM",
            symptom=f"{dm.iframe_count} iframes detected",
            evidence={"iframe_count": dm.iframe_count},
            recommendation="Lazy-load iframes, use facades for embedded content",
            profile=profile_key,
        ))

    report.dom_analysis = analysis


def _analyze_render_diff(br: BrowserResult, report: PerformanceReport) -> None:
    if not br.source_html_length or not br.rendered_html_length:
        return
    diff = br.rendered_html_length - br.source_html_length
    ratio = br.rendered_html_length / max(br.source_html_length, 1)
    profile_key = br.profile.value

    analysis: dict[str, Any] = {
        "profile": profile_key,
        "source_html_bytes": br.source_html_length,
        "rendered_html_bytes": br.rendered_html_length,
        "diff_bytes": diff,
        "render_ratio": round(ratio, 2),
    }

    if ratio > 3.0:
        report.findings.append(Finding(
            module="performance.render", severity="INFO",
            symptom=f"Client-side rendering adds {ratio:.1f}x content (source: {br.source_html_length}B → rendered: {br.rendered_html_length}B)",
            evidence={"source_bytes": br.source_html_length, "rendered_bytes": br.rendered_html_length, "ratio": round(ratio, 2)},
            recommendation="Consider server-side rendering for SEO-critical content",
            profile=profile_key,
        ))

    console_errors = [m for m in br.console_messages if m.type == "error"]
    if console_errors:
        report.findings.append(Finding(
            module="performance.runtime", severity="MEDIUM",
            symptom=f"{len(console_errors)} JavaScript console error(s)",
            evidence={"error_count": len(console_errors), "errors": [e.text[:200] for e in console_errors[:5]]},
            profile=profile_key,
        ))

    report.render_analysis = analysis
