"""Bridge performance-audit signals into the engine inventory.

Follows the same pattern as browser_evidence.py and site_evidence.py:
convert domain-specific PerformanceAuditResult data into inventory keys
the check registry already understands.  Uses setdefault() to never
overwrite existing keys.
"""
from __future__ import annotations

from typing import Any


def inject_performance_evidence(
    inventory: dict[str, Any],
    perf_result: dict[str, Any],
) -> None:
    """Enrich an audit inventory with performance-audit measurements.

    Only injects when the result status is COMPLETED.
    """
    if not isinstance(perf_result, dict):
        return
    if perf_result.get("status") != "COMPLETED":
        return

    report = perf_result.get("performance_report")
    if not isinstance(report, dict):
        return

    _inject_vitals_summary(inventory, report)
    _inject_resource_analysis(inventory, report)
    _inject_dom_analysis(inventory, report)
    _inject_render_analysis(inventory, report)
    _inject_findings_summary(inventory, report)


def _inject_vitals_summary(
    inventory: dict[str, Any], report: dict[str, Any]
) -> None:
    vitals = report.get("vitals_summary")
    if not isinstance(vitals, dict) or not vitals:
        return

    summary: dict[str, Any] = {}
    for _profile, profile_data in vitals.items():
        if not isinstance(profile_data, dict):
            continue
        for metric in ("fcp", "lcp", "cls", "tbt", "ttfb"):
            metric_data = profile_data.get(metric)
            if not isinstance(metric_data, dict):
                continue
            if metric not in summary:
                summary[metric] = metric_data

    if summary:
        inventory.setdefault("perf_vitals_summary", summary)


def _inject_resource_analysis(
    inventory: dict[str, Any], report: dict[str, Any]
) -> None:
    resources = report.get("resource_analysis")
    if not isinstance(resources, dict) or not resources:
        return

    data: dict[str, Any] = {}
    for key in (
        "total_requests",
        "total_transfer_bytes",
        "total_resource_bytes",
        "first_party_requests",
        "third_party_requests",
    ):
        val = resources.get(key)
        if isinstance(val, (int, float)):
            data[key] = val

    by_type = resources.get("by_type")
    if isinstance(by_type, dict):
        data["by_type"] = by_type

    if data:
        inventory.setdefault("perf_resource_analysis", data)


def _inject_dom_analysis(
    inventory: dict[str, Any], report: dict[str, Any]
) -> None:
    dom = report.get("dom_analysis")
    if not isinstance(dom, dict) or not dom:
        return

    data: dict[str, Any] = {}
    for key in (
        "node_count",
        "max_depth",
        "element_count",
        "script_count",
        "style_count",
        "iframe_count",
        "image_count",
    ):
        val = dom.get(key)
        if isinstance(val, (int, float)):
            data[key] = val

    if data:
        inventory.setdefault("perf_dom_analysis", data)


def _inject_render_analysis(
    inventory: dict[str, Any], report: dict[str, Any]
) -> None:
    render = report.get("render_analysis")
    if not isinstance(render, dict) or not render:
        return

    data: dict[str, Any] = {}
    for key in (
        "source_html_bytes",
        "rendered_html_bytes",
        "diff_bytes",
        "render_ratio",
    ):
        val = render.get(key)
        if isinstance(val, (int, float)):
            data[key] = val

    if data:
        inventory.setdefault("perf_render_analysis", data)


def _inject_findings_summary(
    inventory: dict[str, Any], report: dict[str, Any]
) -> None:
    findings = report.get("findings")
    if not isinstance(findings, list) or not findings:
        return

    by_severity: dict[str, int] = {}
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity", "UNKNOWN")).upper()
        by_severity[sev] = by_severity.get(sev, 0) + 1

    inventory.setdefault(
        "perf_findings_summary",
        {"total": len(findings), "by_severity": by_severity},
    )
