"""Standalone HTML audit reports rendered with the RawBlock design system.

The report is a single self-contained HTML document: the RawBlock stylesheet
(design/rawblock.css) is inlined at render time so reports can be shared,
attached to tickets, or opened offline.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .planner import build_remediation_plan

_SEVERITY_CHIP = {
    "critical": "rb-chip--error",
    "high": "rb-chip--error",
    "medium": "rb-chip--warning",
    "low": "",
    "info": "rb-chip--info",
}

_STATUS_CHIP = {
    "PASS": "rb-chip--success",
    "FAIL": "rb-chip--error",
    "OBSERVED": "rb-chip--error",
    "HYPOTHESIS": "rb-chip--warning",
    "UNKNOWN": "",
}

# Emergency fallback so a report can never fail to render in an odd install.
_FALLBACK_CSS = """
body{margin:0;background:#fff;color:#000;font-family:monospace}
*{border-radius:0!important;box-shadow:none!important}
a{color:#0000ff}.rb-card{border:3px solid #000;padding:24px;margin:16px 0}
table{border-collapse:collapse;width:100%}th,td{border:3px solid #000;padding:8px;text-align:left}
"""


def load_rawblock_css() -> str:
    """Locate design/rawblock.css across dev checkouts and installed wheels."""
    env_path = os.environ.get("OPE_RAWBLOCK_CSS")
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path(__file__).resolve().parents[2] / "design" / "rawblock.css")
    candidates.append(Path(sys.prefix) / "share" / "ope" / "rawblock.css")
    candidates.append(Path(sys.exec_prefix) / "share" / "ope" / "rawblock.css")
    for candidate in candidates:
        try:
            return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return _FALLBACK_CSS


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _chip(label: str, variant: str = "") -> str:
    cls = f"rb-chip rb-chip--status {variant}".strip()
    return f'<span class="{cls}">{_e(label)}</span>'


def _severity_chip(severity: str) -> str:
    return _chip(severity.upper(), _SEVERITY_CHIP.get(severity.lower(), ""))


def _status_chip(status: str) -> str:
    return _chip(status.upper(), _STATUS_CHIP.get(status.upper(), ""))


def _iso(epoch: float) -> str:
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return _e(epoch)


def _summary_cards(summary: dict[str, Any]) -> str:
    order = [("finding_count", "TOTAL"), ("critical", "CRITICAL"), ("high", "HIGH"),
             ("medium", "MEDIUM"), ("low", "LOW"), ("info", "INFO")]
    cells = []
    for key, label in order:
        value = summary.get(key, 0)
        elevated = " rb-card--elevated" if key in {"critical", "high"} and value else ""
        color = ""
        if key in {"critical", "high"} and value:
            color = " rb-txt-error"
        elif key == "medium" and value:
            color = " rb-txt-warning"
        cells.append(
            f'<div class="rb-card{elevated}" style="text-align:center;padding:var(--rb-sp-3);">'
            f'<div class="rb-mono rb-tiny rb-uppercase">{label}</div>'
            f'<div style="font-family:var(--rb-font-headline);font-size:48px;line-height:1.1;"{color}>'
            f'{value or 0}</div></div>'
        )
    return '<div class="rb-grid rb-grid-3" style="margin-bottom:var(--rb-sp-5);">' + "".join(cells) + "</div>"


def _inventory_table(inventory: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><th>{_e(k).replace('_', ' ')}</th><td>{_e(v)}</td></tr>"
        for k, v in inventory.items()
    )
    return f'<table class="rb-table">{rows}</table>'


def _module_grid(modules: dict[str, Any]) -> str:
    cells = []
    for key in sorted(modules):
        entry = modules[key]
        status = str(entry.get("status", "UNKNOWN"))
        count = len(entry.get("findings", []))
        score = entry.get("score")
        score_text = "—" if score is None else _e(score)
        cells.append(
            '<div style="border:var(--rb-border-thick);padding:8px;">'
            f'<div class="rb-mono rb-tiny rb-uppercase" style="margin-bottom:6px;">MODULE {_e(key)}</div>'
            f'{_status_chip(status)} '
            f'<span class="rb-mono rb-tiny">score {score_text} · {count} FINDING{"S" if count != 1 else ""}</span>'
            "</div>"
        )
    return '<div class="rb-grid rb-grid-4 rb-grid-6" style="margin-bottom:var(--rb-sp-5);">' + "".join(cells) + "</div>"


def _plan_step_html(step: dict[str, Any]) -> str:
    unblocks = step.get("unblocks", [])
    impact = (
        f' — unblocks {len(unblocks)} module(s): {_e(", ".join(str(u) for u in unblocks))}'
        if unblocks else ""
    )
    findings = step.get("findings", [])
    if findings:
        items = []
        for finding in findings:
            sev = _e(str(finding.get("severity", "")).upper())
            remediation = "".join(
                f"<li>{_e(step_text)}</li>" for step_text in finding.get("remediation", [])
            )
            rem_html = f"<ul class='rb-small'>{remediation}</ul>" if remediation else ""
            items.append(
                f'<li><span class="rb-mono rb-tiny">{_e(finding.get("id", ""))} [{sev}]</span> '
                f'{_e(finding.get("symptom", ""))} '
                f'<span class="rb-tiny">(priority {_e(finding.get("priority", 0))})</span>{rem_html}</li>'
            )
        body = f"<ul>{''.join(items)}</ul>"
    else:
        body = '<p class="rb-small">No finding record attached; module status derived from failing checks.</p>'
    return (
        f'<div class="rb-card" style="margin-bottom:var(--rb-sp-3);">'
        f'<h3 class="rb-card__title">MODULE {_e(step.get("module", ""))} '
        f'{_status_chip(str(step.get("status", "UNKNOWN")))}{impact}</h3>{body}</div>'
    )


def _diagnosis_section(result: dict[str, Any]) -> str:
    health = result.get("health")
    health_text = "N/A (insufficient evidence)" if health is None else _e(health)
    plan = result.get("remediation_plan")
    if not isinstance(plan, dict):
        plan = build_remediation_plan(result)

    blocks = [f'<p class="rb-mono"><strong>GLOBAL HEALTH:</strong> {health_text}</p>']

    root_causes = plan.get("root_causes", [])
    direct_failures = plan.get("direct_failures", [])
    blocked = plan.get("blocked", [])

    if not root_causes and not direct_failures:
        blocks.append('<p>No failing modules were diagnosed; no remediation is required.</p>')
        return "".join(blocks)

    if root_causes:
        blocks.append('<h3 class="rb-uppercase">FIX FIRST — ROOT CAUSES (BY DOWNSTREAM IMPACT)</h3>')
        blocks += [_plan_step_html(step) for step in root_causes]
    if direct_failures:
        blocks.append('<h3 class="rb-uppercase">THEN — INDEPENDENT FAILURES</h3>')
        blocks += [_plan_step_html(step) for step in direct_failures]
    if blocked:
        waiting = "".join(
            f'<li>MODULE {_e(entry.get("module", ""))} — waiting on '
            f'{_e(", ".join(str(w) for w in entry.get("waiting_on", [])) or "upstream failure")}</li>'
            for entry in blocked
        )
        blocks.append(
            f'<h3 class="rb-uppercase">WAITING (BLOCKED, NOT YET ACTIONABLE)</h3><ul>{waiting}</ul>'
        )
    return "".join(blocks)


_REASONING_SECTIONS = (
    ("root_cause_hypotheses", "Root-cause hypotheses"),
    ("priorities", "Priorities"),
    ("recommendations", "Recommendations"),
    ("content_opportunities", "Content opportunities"),
    ("validation_plan", "Validation plan"),
)


def _reasoning_list(items: Any) -> str:
    entries: list[str] = []
    if isinstance(items, list):
        for item in items:
            entries.append(_e(item) if isinstance(item, str) else _e(json.dumps(item, ensure_ascii=False, sort_keys=True)))
    elif isinstance(items, str) and items.strip():
        entries.append(_e(items))
    elif items not in (None, {}, []):
        entries.append(_e(json.dumps(items, ensure_ascii=False, sort_keys=True)))
    if not entries:
        return ""
    return "<ul>" + "".join(f"<li>{entry}</li>" for entry in entries) + "</ul>"


def _reasoning_section(reasoning: dict[str, Any]) -> str:
    """Render the optional advisory-reasoning block. All content is escaped and
    clearly labelled advisory; it is never presented as evidence or PASS/FAIL."""
    if not reasoning.get("available"):
        reason = _e(reasoning.get("reason", "not configured"))
        return (
            '<p class="rb-small"><em>Advisory AI reasoning unavailable — '
            f'{reason}.</em> The deterministic findings are unaffected.</p>'
        )
    model = _e(reasoning.get("model", "unknown"))
    blocks = [
        '<p class="rb-small"><em>Advisory only (model: '
        f'{model}), grounded in the deterministic audit evidence — not a measurement, '
        "not a PASS/FAIL, not evidence.</em></p>"
    ]
    body = reasoning.get("result")
    if not isinstance(body, dict):
        blocks.append('<p class="rb-small">The provider returned no structured reasoning.</p>')
        return "".join(blocks)
    rendered_any = False
    for key, title in _REASONING_SECTIONS:
        listing = _reasoning_list(body.get(key))
        if listing:
            rendered_any = True
            blocks.append(f'<h3 class="rb-uppercase">{_e(title)}</h3>{listing}')
    if not rendered_any:
        blocks.append('<p class="rb-small">The provider returned no reasoning items.</p>')
    return "".join(blocks)


def _finding_card(finding: dict[str, Any]) -> str:
    severity = str(finding.get("severity", "info"))
    evidence = finding.get("evidence", [])
    remediation = finding.get("remediation", []) or []
    validation = finding.get("validation", []) or []

    rem = "<p class='rb-tiny'>No remediation recorded.</p>"
    if remediation:
        rem = "<ul>" + "".join(f"<li>{_e(x)}</li>" for x in remediation) + "</ul>"
    val = "<p class='rb-tiny'>No validation recorded.</p>"
    if validation:
        val = "<ul>" + "".join(f"<li>{_e(x)}</li>" for x in validation) + "</ul>"

    evidence_block = ""
    if evidence:
        payload = _e(json.dumps(evidence, indent=2, ensure_ascii=False, default=str))
        evidence_block = (
            "<details style='margin-top:var(--rb-sp-3);'>"
            "<summary class='rb-btn rb-btn--sm rb-btn--secondary' style='display:inline-flex;'>"
            "EVIDENCE (DIRECT)</summary>"
            f"<pre style='margin-top:var(--rb-sp-2);'>{payload}</pre></details>"
        )

    confidence = finding.get("confidence", "")
    meta = (
        f'<span class="rb-mono rb-tiny">MODULE {_e(finding.get("module", ""))}</span>'
        f' {_status_chip(str(finding.get("status", "OBSERVED")))}'
    )
    if confidence != "":
        meta += f' <span class="rb-mono rb-tiny">CONFIDENCE {_e(confidence)}</span>'
    root_cause = finding.get("root_cause", "")
    root_block = (
        f'<p class="rb-small"><strong class="rb-uppercase">Root cause — </strong>{_e(root_cause)}</p>'
        if root_cause
        else ""
    )

    return (
        '<article class="rb-card rb-card--elevated rb-finding" '
        f'data-severity="{_e(severity.lower())}" style="margin-bottom:var(--rb-sp-3);">'
        '<div style="display:flex;flex-wrap:wrap;gap:var(--rb-sp-2);align-items:center;'
        'border-bottom:var(--rb-border-thick);padding-bottom:var(--rb-sp-2);margin-bottom:var(--rb-sp-2);">'
        f'<span class="rb-mono rb-small">{_e(finding.get("id", ""))}</span>'
        f"{_severity_chip(severity)}"
        f'<span class="rb-chip rb-chip--status">PRIORITY {_e(finding.get("priority", 0))}</span>'
        '<span style="flex:1 1 auto;"></span>'
        f"{meta}"
        "</div>"
        f'<h3 style="font-size:22px;font-family:var(--rb-font-body);font-weight:600;">'
        f'{_e(finding.get("symptom", ""))}</h3>'
        f"{root_block}"
        '<div class="rb-grid rb-grid-2">'
        f'<div><p class="rb-label">Remediation</p>{rem}</div>'
        f'<div><p class="rb-label">Validation</p>{val}</div>'
        "</div>"
        f"{evidence_block}"
        "</article>"
    )


def html_report(result: dict[str, Any]) -> str:
    """Render an OPE audit result dict as a standalone RawBlock HTML document."""
    css = load_rawblock_css()
    inventory = result.get("inventory", {})
    summary = result.get("summary", {})
    modules = result.get("modules", {})
    findings = sorted(result.get("findings", []),
                      key=lambda f: float(f.get("priority", 0.0)), reverse=True)

    status = inventory.get("status", "")
    status_chip = _chip(f"HTTP {status}", "rb-chip--success" if str(status).startswith("2") else "rb-chip--error")

    reasoning = result.get("reasoning")
    reasoning_html = ""
    if isinstance(reasoning, dict):
        reasoning_html = (
            '<h2>AI REASONING (ADVISORY)</h2>'
            f'<div style="margin-bottom:var(--rb-sp-5);">{_reasoning_section(reasoning)}</div>'
        )

    finding_cards = "".join(_finding_card(f) for f in findings) or (
        '<div class="rb-card rb-card--elevated"><h3 class="rb-card__title">NO FINDINGS</h3>'
        "<p>No findings were generated by the deterministic checks.</p></div>"
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
<title>OPE // RAW AUDIT — {_e(result.get('target', ''))}</title>
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
      OMNI-PRESENCE ENGINE · EVIDENCE-FIRST AUDIT · RAW//BLOCK REPORT
    </p>
    <h1 style="font-size:clamp(32px,6vw,64px);margin:0;">{_e(result.get('target', ''))}</h1>
    <div class="meta-bar" style="margin-top:var(--rb-sp-3);">
      {status_chip}
      <span class="rb-chip rb-chip--status">RUN {_e(result.get('run_id', ''))}</span>
      <span class="rb-mono rb-tiny">{_iso(result.get('started_at', 0))}</span>
    </div>
  </div>
</header>

<main class="rb-shell" style="padding-top:var(--rb-sp-5);padding-bottom:var(--rb-sp-7);">

  <h2>SUMMARY</h2>
  {_summary_cards(summary)}

  <h2>DIAGNOSIS &amp; PLAN</h2>
  <div style="margin-bottom:var(--rb-sp-5);">{_diagnosis_section(result)}</div>

  {reasoning_html}

  <h2>MODULES (20-LAYER DEPENDENCY GRAPH)</h2>
  {_module_grid(modules)}

  <h2>INVENTORY</h2>
  <div style="margin-bottom:var(--rb-sp-5);">{_inventory_table(inventory)}</div>

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
      GENERATED BY OPE {_e(result.get('version', ''))} · CONTRACT {_e(result.get('engine_contract', 'evidence-root-cause-v1'))} ·
      EVIDENCE IS DIRECT · SHARP EDGES ONLY · RAW//BLOCK DESIGN SYSTEM
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


def write_html_report(result: dict[str, Any], path: str | os.PathLike[str]) -> Path:
    """Render and persist the report; returns the written path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_report(result), encoding="utf-8")
    return out
