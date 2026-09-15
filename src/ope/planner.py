"""Deterministic, evidence-based remediation planning.

This is the executable ``PLAN`` stage of the OPE pipeline
(``DIAGNOSE -> PRIORITIZE -> PLAN -> IMPLEMENT``).  It never invents
remediation, evidence, or priorities: it *orders* what the diagnosis already
produced.  The ordering is driven by the real dependency graph — fix the
root-cause module that unblocks the most downstream modules first — so the
plan is a direct, traceable consequence of the executable dependency graph
and the evidence-backed findings.

``IMPLEMENT`` stays human-owned: the plan describes what to fix and in what
order, and never applies changes.
"""
from __future__ import annotations

from typing import Any


def _module_number(value: Any) -> str:
    """First segment of a module identifier (e.g. ``02-infrastructure`` -> ``02``)."""
    return str(value).split("-", 1)[0]


def _findings_for_module(findings: list[dict[str, Any]], module_number: str) -> list[dict[str, Any]]:
    """Return this module's findings, ordered by priority (desc) then id (asc).

    Ordering is total and deterministic — priority breaks ties by id, so a
    plan is byte-for-byte reproducible across runs.
    """
    owned = [f for f in findings if isinstance(f, dict) and _module_number(f.get("module", "")) == module_number]
    return sorted(
        owned,
        key=lambda f: (-float(f.get("priority", 0.0) or 0.0), str(f.get("id", ""))),
    )


def _step(module_number: str, module: dict[str, Any], findings: list[dict[str, Any]], unblocks: list[str]) -> dict[str, Any]:
    """Build one plan step: a module to fix, its findings, and its unblock impact."""
    module_findings = [
        {
            "id": f.get("id", ""),
            "symptom": f.get("symptom", ""),
            "severity": f.get("severity", ""),
            "priority": f.get("priority", 0.0),
            "root_cause": f.get("root_cause", ""),
            "remediation": list(f.get("remediation", []) or []),
            "validation": list(f.get("validation", []) or []),
        }
        for f in findings
    ]
    return {
        "module": module_number,
        "status": module.get("status", "UNKNOWN"),
        "score": module.get("score"),
        "unblocks": unblocks,
        "unblock_count": len(unblocks),
        "finding_count": len(module_findings),
        "findings": module_findings,
    }


def build_remediation_plan(result: dict[str, Any]) -> dict[str, Any]:
    """Produce a dependency-ordered remediation plan from a normalized result.

    The plan has three ordered groups, all derived — never invented:

    - ``root_causes``: modules whose own ``FAIL`` evidence blocks downstream
      modules, ordered by how many modules each unblocks (desc), then module
      number.  Fixing these first frees the most of the graph.
    - ``direct_failures``: modules that are ``FAIL`` but block nothing
      downstream — real problems to fix that no other module is waiting on.
    - ``blocked``: modules currently ``BLOCKED``, listed with the root causes
      they are waiting on.  They are not planned as work items because their
      own evidence is not trustworthy until the upstream failure is fixed.

    Nothing is fabricated: findings, remediation text, priorities and
    statuses all come straight from the diagnosis, and a module with no
    finding record is reported with an empty finding list rather than an
    invented one.
    """
    modules = result.get("modules")
    if not isinstance(modules, dict):
        modules = {}
    raw_findings = result.get("findings")
    findings = raw_findings if isinstance(raw_findings, list) else []
    root_cause_map = result.get("dependency_root_causes")
    if not isinstance(root_cause_map, dict):
        root_cause_map = {}

    # Invert the root-cause map: for each root module, the blocked modules it
    # is (partly) responsible for. This is the graph-derived unblock impact.
    unblocks_by_root: dict[str, list[str]] = {}
    for blocked_number, causes in root_cause_map.items():
        if not isinstance(causes, list):
            continue
        for cause in causes:
            unblocks_by_root.setdefault(str(cause), []).append(str(blocked_number))
    for cause in unblocks_by_root:
        unblocks_by_root[cause] = sorted(set(unblocks_by_root[cause]))

    fail_numbers = {
        _module_number(number)
        for number, module in modules.items()
        if isinstance(module, dict) and module.get("status") == "FAIL"
    }
    root_cause_numbers = set(unblocks_by_root)

    # Root causes: FAIL modules that block something, most-unblocking first.
    root_causes = [
        _step(number, modules.get(number, {}), _findings_for_module(findings, number), unblocks_by_root[number])
        for number in sorted(
            root_cause_numbers,
            key=lambda n: (-len(unblocks_by_root[n]), n),
        )
        if isinstance(modules.get(number), dict)
    ]

    # Direct failures: FAIL modules that block nothing downstream.
    direct_failures = [
        _step(number, modules.get(number, {}), _findings_for_module(findings, number), [])
        for number in sorted(fail_numbers - root_cause_numbers)
        if isinstance(modules.get(number), dict)
    ]

    # Blocked modules: waiting on their root causes, not planned as work.
    blocked = [
        {
            "module": _module_number(number),
            "waiting_on": sorted(str(c) for c in (root_cause_map.get(_module_number(number)) or [])),
        }
        for number, module in sorted(modules.items())
        if isinstance(module, dict) and module.get("status") == "BLOCKED"
    ]

    planned_findings = sum(step["finding_count"] for step in root_causes) + sum(
        step["finding_count"] for step in direct_failures
    )

    return {
        "method": "dependency-ordered",
        "root_causes": root_causes,
        "direct_failures": direct_failures,
        "blocked": blocked,
        "summary": {
            "root_cause_count": len(root_causes),
            "direct_failure_count": len(direct_failures),
            "blocked_count": len(blocked),
            "planned_findings": planned_findings,
        },
    }


def _step_markdown(step: dict[str, Any]) -> list[str]:
    """Render one remediation step (a module and its findings) as markdown."""
    header = f"- **Module {step['module']}** ({step['status']})"
    if step["unblock_count"]:
        header += f" — unblocks {step['unblock_count']} module(s): {', '.join(step['unblocks'])}"
    lines = [header]
    if not step["findings"]:
        lines.append("  - _No finding record attached; module status is derived from failing checks._")
        return lines
    for finding in step["findings"]:
        sev = str(finding.get("severity", "")).upper()
        lines.append(f"  - `{finding['id']}` [{sev}] {finding['symptom']} (priority {finding['priority']})")
        for remediation in finding.get("remediation", []):
            lines.append(f"    - fix: {remediation}")
    return lines


def diagnosis_markdown(result: dict[str, Any]) -> list[str]:
    """Render health, module status, and the remediation plan as markdown lines.

    Shared by every report surface so the diagnostic view is presented
    identically for single-page, site, and performance audits.  Purely a
    view over already-computed, evidence-backed data.
    """
    lines: list[str] = ["## Diagnosis & Plan", ""]

    health = result.get("health")
    lines.append(f"**Global health:** {health if health is not None else 'N/A (insufficient evidence)'}")
    lines.append("")

    modules = result.get("modules")
    if not isinstance(modules, dict):
        modules = {}
    graded = [
        (num, mod)
        for num, mod in sorted(modules.items())
        if isinstance(mod, dict) and mod.get("status") in {"FAIL", "BLOCKED"}
    ]
    if graded:
        lines.append("### Failing & blocked modules")
        lines.append("")
        for num, mod in graded:
            score = mod.get("score")
            score_text = "—" if score is None else str(score)
            lines.append(f"- **{num}** — {mod.get('status')} (score {score_text})")
        lines.append("")

    plan = result.get("remediation_plan")
    if not isinstance(plan, dict):
        plan = build_remediation_plan(result)

    summary = plan.get("summary", {})
    if not plan.get("root_causes") and not plan.get("direct_failures"):
        lines.append("### Remediation plan")
        lines.append("")
        lines.append("No failing modules were diagnosed; no remediation is required.")
        lines.append("")
        return lines

    lines.append("### Remediation plan (dependency-ordered)")
    lines.append("")
    lines.append(
        f"{summary.get('root_cause_count', 0)} root cause(s), "
        f"{summary.get('direct_failure_count', 0)} independent failure(s), "
        f"{summary.get('blocked_count', 0)} blocked module(s) waiting."
    )
    lines.append("")

    if plan.get("root_causes"):
        lines.append("**Fix first — root causes (ordered by downstream impact):**")
        for step in plan["root_causes"]:
            lines += _step_markdown(step)
        lines.append("")

    if plan.get("direct_failures"):
        lines.append("**Then — independent failures (block nothing downstream):**")
        for step in plan["direct_failures"]:
            lines += _step_markdown(step)
        lines.append("")

    if plan.get("blocked"):
        lines.append("**Waiting on the above (blocked, not yet actionable):**")
        for entry in plan["blocked"]:
            waiting = ", ".join(entry["waiting_on"]) if entry["waiting_on"] else "upstream failure"
            lines.append(f"- **Module {entry['module']}** — waiting on {waiting}")
        lines.append("")

    return lines
