"""Standalone HTML performance-audit reports using the RawBlock design system.

Reuses shared helpers from report_html.py. The report extends the
single-page template with performance-specific sections (Core Web Vitals
table, resource analysis, findings sorted by priority).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .report_html import (
    _e,
    _finding_card,
    _iso,
    _module_grid,
    _status_chip,
    _summary_cards,
    load_rawblock_css,
)


def _vitals_table(result: dict[str, Any]) -> str:
    report = result.get("performance_report")
    if not isinstance(report, dict):
        return ""
    vitals = report.get("vitals_summary")
    if not isinstance(vitals, dict) or not vitals:
        return ""

    sections: list[str] = []
    for profile, metrics in sorted(vitals.items()):
        if not isinstance(metrics, dict):
            continue
        rows = []
        for metric, data in sorted(metrics.items()):
            if not isinstance(data, dict):
                continue
            val = data.get("value_ms") or data.get("value", "?")
            unit = "ms" if "value_ms" in data else ""
            rating = str(data.get("rating", "?")).upper()
            chip_cls = {
                "GOOD": "rb-chip--success",
                "NEEDS IMPROVEMENT": "rb-chip--warning",
                "NEEDS_IMPROVEMENT": "rb-chip--warning",
                "POOR": "rb-chip--error",
            }.get(rating.replace("_", " "), "")
            rows.append(
                f"<tr><td class='rb-mono'>{_e(metric.upper())}</td>"
                f"<td>{_e(val)}{_e(unit)}</td>"
                f'<td><span class="rb-chip {chip_cls}">{_e(rating)}</span></td></tr>'
            )
        if rows:
            sections.append(
                f'<h3 class="rb-uppercase rb-mono" style="margin-top:var(--rb-sp-3);">{_e(profile)}</h3>'
                '<table class="rb-table"><thead><tr><th>Metric</th><th>Value</th>'
                "<th>Rating</th></tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table>"
            )

    if not sections:
        return ""
    return '<div style="margin-bottom:var(--rb-sp-5);">' + "".join(sections) + "</div>"


def _resource_summary(result: dict[str, Any]) -> str:
    report = result.get("performance_report")
    if not isinstance(report, dict):
        return ""
    resources = report.get("resource_summary")
    if not isinstance(resources, dict) or not resources:
        return ""

    items = [
        ("Total requests", resources.get("total_requests", "?")),
        ("Total size", _format_bytes(resources.get("total_bytes"))),
        ("JS requests", resources.get("js_requests", "?")),
        ("CSS requests", resources.get("css_requests", "?")),
        ("Image requests", resources.get("image_requests", "?")),
        ("Font requests", resources.get("font_requests", "?")),
    ]
    cells = []
    for label, value in items:
        cells.append(
            f'<div class="rb-card" style="text-align:center;padding:var(--rb-sp-3);">'
            f'<div class="rb-mono rb-tiny rb-uppercase">{_e(label)}</div>'
            f'<div style="font-family:var(--rb-font-headline);font-size:32px;line-height:1.2;">'
            f"{_e(value)}</div></div>"
        )
    return '<div class="rb-grid rb-grid-3" style="margin-bottom:var(--rb-sp-5);">' + "".join(cells) + "</div>"


def _format_bytes(value: Any) -> str:
    if value is None:
        return "?"
    try:
        b = int(value)
    except (TypeError, ValueError):
        return str(value)
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


def performance_html_report(result: dict[str, Any]) -> str:
    """Render a normalized performance audit result as a standalone RawBlock HTML document."""
    css = load_rawblock_css()
    summary = result.get("summary", {})
    modules = result.get("modules", {})
    findings = sorted(
        result.get("findings", []),
        key=lambda f: float(f.get("priority", 0.0)),
        reverse=True,
    )

    status = result.get("status", "UNKNOWN")
    status_chip = _status_chip(status)

    duration = result.get("duration_s", 0)
    try:
        duration_str = f"{float(duration):.1f}s"
    except (TypeError, ValueError):
        duration_str = "?"

    finding_cards = "".join(_finding_card(f) for f in findings) or (
        '<div class="rb-card rb-card--elevated"><h3 class="rb-card__title">NO FINDINGS</h3>'
        "<p>No performance findings were generated.</p></div>"
    )

    filters = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    filter_buttons = "".join(
        f'<button class="rb-chip rb-filter{" is-active" if f == "ALL" else ""}" type="button" '
        f'data-filter="{f.lower()}" aria-pressed="{str(f == "ALL").lower()}">{f}</button>'
        for f in filters
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OPE // PERFORMANCE AUDIT — {_e(result.get('target', ''))}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Mono:wght@400;700&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{css}
.report-header {{ border-bottom: var(--rb-border-heavy); }}
.meta-bar {{ display:flex; flex-wrap:wrap; gap:var(--rb-sp-3); align-items:center; }}
</style>
</head>
<body>

<header class="report-header rb-inverted">
  <div class="rb-shell" style="padding-top:var(--rb-sp-4);padding-bottom:var(--rb-sp-4);">
    <p class="rb-mono rb-tiny rb-uppercase" style="margin-bottom:var(--rb-sp-2);">
      OMNI-PRESENCE ENGINE · PERFORMANCE AUDIT · RAW//BLOCK REPORT
    </p>
    <h1 style="font-size:clamp(32px,6vw,64px);margin:0;">{_e(result.get('target', ''))}</h1>
    <div class="meta-bar" style="margin-top:var(--rb-sp-3);">
      {status_chip}
      <span class="rb-chip rb-chip--status">SCOPE: PERFORMANCE</span>
      <span class="rb-chip rb-chip--status">DURATION: {_e(duration_str)}</span>
      <span class="rb-mono rb-tiny">{_iso(result.get('started_at', 0))}</span>
    </div>
  </div>
</header>

<main class="rb-shell" style="padding-top:var(--rb-sp-5);padding-bottom:var(--rb-sp-7);">

  <h2>CORE WEB VITALS</h2>
  {_vitals_table(result)}

  <h2>RESOURCE SUMMARY</h2>
  {_resource_summary(result)}

  <h2>FINDING SUMMARY</h2>
  {_summary_cards(summary)}

  <h2>MODULES (20-LAYER DEPENDENCY GRAPH)</h2>
  {_module_grid(modules)}

  <div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:var(--rb-sp-3);">
    <h2 style="margin:0;">FINDINGS</h2>
    <span style="flex:1 1 auto;"></span>
    <span class="row rb-stack" style="display:flex;gap:8px;flex-wrap:wrap;">{filter_buttons}</span>
  </div>
  <hr class="rb-rule">
  <div id="findings">{finding_cards}</div>

</main>

<footer style="border-top:var(--rb-border-heavy);">
  <div class="rb-shell rb-inverted" style="border:0;padding-top:var(--rb-sp-4);padding-bottom:var(--rb-sp-4);">
    <p class="rb-mono rb-tiny" style="margin:0;">
      GENERATED BY OPE {_e(result.get('version', ''))} · CONTRACT {_e(result.get('engine_contract', 'evidence-diagnostic-v1'))} ·
      SCOPE {_e(result.get('engine_scope', 'performance'))} · EVIDENCE IS DIRECT · RAW//BLOCK DESIGN SYSTEM
    </p>
  </div>
</footer>

<script>
  document.querySelectorAll('.rb-filter').forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      document.querySelectorAll('.rb-filter').forEach(function (b) {{
        b.classList.remove('is-active');
        b.setAttribute('aria-pressed', 'false');
      }});
      btn.classList.add('is-active');
      btn.setAttribute('aria-pressed', 'true');
      var want = btn.getAttribute('data-filter');
      document.querySelectorAll('.rb-finding').forEach(function (card) {{
        card.style.display = (want === 'all' || card.getAttribute('data-severity') === want) ? '' : 'none';
      }});
    }});
  }});
</script>
</body>
</html>
"""


def write_performance_html_report(result: dict[str, Any], path: str | os.PathLike[str]) -> Path:
    """Render and persist the performance audit report; returns the written path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(performance_html_report(result), encoding="utf-8")
    return out
