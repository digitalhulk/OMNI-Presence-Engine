from __future__ import annotations

from typing import Any

from .browser import BrowserResult, BrowserStatus, DeviceProfile


def inject_browser_evidence(
    inventory: dict[str, Any],
    browser_results: list[BrowserResult],
) -> None:
    """Enrich an audit inventory with first-party browser measurements.

    Picks the best successful result (desktop preferred, then mobile).
    Writes new keys only — never overwrites existing inventory entries.
    If no successful result exists, nothing is written.
    """
    result = _pick_best(browser_results)
    if result is None:
        return

    vitals = result.vitals
    browser_vitals: dict[str, Any] = {}
    if vitals.fcp_ms is not None:
        browser_vitals["fcp_ms"] = vitals.fcp_ms
    if vitals.lcp_ms is not None:
        browser_vitals["lcp_ms"] = vitals.lcp_ms
    if vitals.cls is not None:
        browser_vitals["cls"] = vitals.cls
    if vitals.tbt_ms is not None:
        browser_vitals["tbt_ms"] = vitals.tbt_ms
    ttfb = result.timing.ttfb()
    if ttfb is not None:
        browser_vitals["ttfb_ms"] = ttfb
    if browser_vitals:
        inventory.setdefault("browser_vitals", browser_vitals)

    dom = result.dom_metrics
    browser_dom: dict[str, Any] = {
        "node_count": dom.node_count,
        "max_depth": dom.max_depth,
        "script_count": dom.script_count,
        "image_count": dom.image_count,
    }
    inventory.setdefault("browser_dom", browser_dom)

    rs = result.resource_summary
    browser_resources: dict[str, Any] = {
        "total_requests": rs.total_requests,
        "total_transfer_bytes": rs.total_transfer_bytes,
        "total_resource_bytes": rs.total_resource_bytes,
        "first_party_requests": rs.first_party_requests,
        "third_party_requests": rs.third_party_requests,
        "by_type": rs.by_type,
    }
    inventory.setdefault("browser_resources", browser_resources)

    timing_dict = result.timing.to_dict()
    if timing_dict:
        inventory.setdefault("browser_timing", timing_dict)

    render_ratio = 0.0
    if result.source_html_length > 0:
        render_ratio = result.rendered_html_length / result.source_html_length
    browser_render: dict[str, Any] = {
        "source_html_length": result.source_html_length,
        "rendered_html_length": result.rendered_html_length,
        "render_ratio": round(render_ratio, 2),
    }
    inventory.setdefault("browser_render", browser_render)

    error_count = sum(
        1 for cm in result.console_messages if cm.type == "error"
    )
    inventory.setdefault("browser_console_errors", error_count)

    inventory.setdefault("browser_profile", result.profile.value)


def _pick_best(results: list[BrowserResult]) -> BrowserResult | None:
    successes = [r for r in results if r.status == BrowserStatus.SUCCESS]
    if not successes:
        return None
    for r in successes:
        if r.profile == DeviceProfile.DESKTOP:
            return r
    return successes[0]
