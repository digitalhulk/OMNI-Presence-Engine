from __future__ import annotations

from copy import deepcopy
from typing import Any

from .audit_pipeline import execute_audit_checks
from .dependency_graph import cascade_blocked, find_root_causes
from .module_runner import ExecutionStatus
from .performance_evidence import inject_performance_evidence
from .planner import build_remediation_plan
from .registry import checks_for_module
from .scoring import health_basis, module_score_basis
from .site_evidence import inject_site_evidence

HYPOTHESIS_ROOT_CAUSE = "Not yet established; additional evidence or dependency analysis is required."


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Normalize one finding without treating malformed evidence as success."""
    item = deepcopy(finding) if isinstance(finding, dict) else {}
    raw_evidence = item.get("evidence")
    evidence = raw_evidence if isinstance(raw_evidence, list) else []
    valid_evidence = [entry for entry in evidence if isinstance(entry, dict)]
    confidence = min(
        (_safe_float(entry.get("confidence", 0.2), 0.2) for entry in valid_evidence),
        default=0.2,
    )
    item["confidence"] = round(max(0.0, min(1.0, confidence)), 3)
    item.setdefault("affected_layer", item.get("module", ""))
    item.setdefault("dependency", "")
    item.setdefault("impact", "")
    item.setdefault("regression_guard", [])
    item.setdefault("execution_status", "FAIL")
    item.setdefault("evidence_status", item.get("status") or "OBSERVED")
    item["status"] = item.get("status") or "OBSERVED"
    if not item.get("root_cause"):
        item["root_cause"] = HYPOTHESIS_ROOT_CAUSE
        item["status"] = "HYPOTHESIS"
        item["evidence_status"] = "HYPOTHESIS"
    # Priority is canonically 0-100 (the scoring.priority() primitive and
    # audit._finding both produce that scale). Clamping to 0-1 here previously
    # collapsed every distinct high priority to 1.0 — a real severity-ordering
    # collision. Clamp to the canonical 0-100 range instead.
    item["priority"] = round(max(0.0, min(100.0, _safe_float(item.get("priority", 0.0), 0.0))), 2)
    return item


def _reconcile_module_status(existing: Any, check_statuses: list[str]) -> str:
    """Derive a module status without mistaking partial coverage for PASS."""
    if existing in {ExecutionStatus.FAIL.value, ExecutionStatus.BLOCKED.value}:
        return str(existing)
    if not check_statuses:
        return ExecutionStatus.UNKNOWN.value
    if ExecutionStatus.FAIL.value in check_statuses:
        return ExecutionStatus.FAIL.value
    if ExecutionStatus.BLOCKED.value in check_statuses:
        return ExecutionStatus.BLOCKED.value
    if all(status == ExecutionStatus.NA.value for status in check_statuses):
        return ExecutionStatus.NA.value
    if all(status == ExecutionStatus.PASS.value for status in check_statuses):
        return ExecutionStatus.PASS.value
    return ExecutionStatus.UNKNOWN.value


_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _max_fail_severity(module: dict[str, Any], severity_by_id: dict[str, str]) -> str | None:
    """Highest severity among the module's own findings (drives the score cap)."""
    worst: str | None = None
    worst_rank = -1
    for fid in module.get("findings", []) or []:
        sev = str(severity_by_id.get(str(fid), "")).lower()
        rank = _SEVERITY_RANK.get(sev, -1)
        if rank > worst_rank:
            worst_rank, worst = rank, sev
    return worst


def _compute_scores(modules: dict[str, Any], checks: dict[str, Any], findings: list[dict[str, Any]] | None = None) -> dict[str, float | None]:
    """Compute per-module scores and attach score + score_basis to each module."""
    severity_by_id = {
        str(f.get("id")): str(f.get("severity", ""))
        for f in (findings or [])
        if isinstance(f, dict) and f.get("id") is not None
    }
    scores: dict[str, float | None] = {}
    for module_number, module in modules.items():
        if not isinstance(module, dict):
            continue
        module_code = str(module_number)
        module_checks: dict[str, Any] = {}
        for check_id, check_data in checks.items():
            if isinstance(check_data, dict) and str(check_data.get("module", "")).startswith(module_code + "-"):
                module_checks[check_id] = check_data
        basis = module_score_basis(
            module,
            module_checks=module_checks or None,
            max_fail_severity=_max_fail_severity(module, severity_by_id),
        )
        module["score"] = basis["score"]
        module["score_basis"] = basis
        scores[module_number] = basis["score"]
    return scores


def _reconcile_and_score(output: dict[str, Any], modules: dict[str, Any]) -> None:
    """Execute registry checks, reconcile module statuses, and compute scores."""
    execution = execute_audit_checks(output)
    checks = execution.get("checks", {}) if isinstance(execution, dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    output["checks"] = checks

    for module_number, module in modules.items():
        if not isinstance(module, dict):
            module = {}
            modules[module_number] = module
        module_code = str(module_number)
        module_id = next(
            (
                str(value.get("module"))
                for value in checks.values()
                if isinstance(value, dict)
                and str(value.get("module", "")).startswith(module_code + "-")
            ),
            module_code,
        )
        check_ids = checks_for_module(module_id)
        statuses = [
            str(checks[check_id].get("status", ExecutionStatus.UNKNOWN.value))
            if isinstance(checks.get(check_id), dict)
            else ExecutionStatus.UNKNOWN.value
            for check_id in check_ids
        ]
        module["status"] = _reconcile_module_status(module.get("status"), statuses)

    pre_cascade = {
        num: mod.get("status", "UNKNOWN")
        for num, mod in modules.items()
        if isinstance(mod, dict)
    }
    cascaded = cascade_blocked(pre_cascade)
    root_cause_map = find_root_causes(cascaded)
    for num, mod in modules.items():
        if isinstance(mod, dict) and cascaded.get(num) != pre_cascade.get(num):
            mod["status"] = cascaded[num]
            if num in root_cause_map:
                mod["blocked_by"] = root_cause_map[num]

    if root_cause_map:
        output["dependency_root_causes"] = root_cause_map

    scores = _compute_scores(modules, checks, output.get("findings"))
    basis = health_basis(scores)
    output["health"] = basis["health"]
    output["health_basis"] = basis

    output["remediation_plan"] = build_remediation_plan(output)


def _init_modules_from_findings(findings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Create a fresh 20-module dict and populate findings into matching modules."""
    modules: dict[str, dict[str, Any]] = {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)}
    for f in findings:
        module_key = str(f.get("module", "")).split("-")[0]
        if module_key in modules:
            modules[module_key]["findings"].append(f.get("id", ""))
            modules[module_key]["status"] = "FAIL"
    return modules


def _attach_entity(output: dict[str, Any]) -> None:
    """Materialize a structured entity record from the JSON-LD signals already
    extracted into inventory. This is a summary of observed signals (the same
    ones the 01-entity module evaluates), never a fabricated identity graph:
    every field is read from inventory, and absent signals stay None/empty.
    """
    inv = output.get("inventory")
    inv = inv if isinstance(inv, dict) else {}
    types = inv.get("entity_types")
    output["entity"] = {
        "types": list(types) if isinstance(types, list) else [],
        "has_entity_type": bool(inv.get("has_entity_type")),
        "canonical_url": inv.get("canonical") or output.get("final_url") or output.get("target"),
        "identifiers_present": inv.get("has_identifiers"),
        "relationships_present": inv.get("has_relationships"),
        "name_matches_title": inv.get("name_matches_title"),
        "is_local_business": bool(inv.get("is_local_business")),
        "has_nap": inv.get("has_nap"),
        "ownership_verification": list(inv.get("verification_tags") or []),
        "evidence_status": "OBSERVED" if inv.get("has_entity_type") else "UNKNOWN",
        "source": "json-ld",
    }


def normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Attach the stable evidence/diagnostic contract to an audit result."""
    output = deepcopy(result) if isinstance(result, dict) else {}
    output["engine_contract"] = "evidence-diagnostic-v1"

    raw_findings = output.get("findings")
    findings = raw_findings if isinstance(raw_findings, list) else []
    output["findings"] = [normalize_finding(finding) for finding in findings]

    modules = output.get("modules")
    if not isinstance(modules, dict):
        modules = {}
        output["modules"] = modules

    _reconcile_and_score(output, modules)
    _attach_entity(output)
    return output


def normalize_site_result(site_result: dict[str, Any]) -> dict[str, Any]:
    """Attach the evidence-diagnostic-v1 contract to a site audit result.

    Normalizes site-level findings, injects site evidence into a synthetic
    inventory, and runs the check registry against it.  The seed page's
    inventory is minimal (site-level signals only), so most single-page
    checks will return UNKNOWN — that is correct rather than fabricating
    PASS from absent evidence.
    """
    output = deepcopy(site_result) if isinstance(site_result, dict) else {}
    output["engine_contract"] = "evidence-diagnostic-v1"
    output["engine_scope"] = "site"

    raw_findings = output.get("findings")
    findings = raw_findings if isinstance(raw_findings, list) else []
    output["findings"] = [normalize_finding(finding) for finding in findings]

    inventory: dict[str, Any] = output.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    inject_site_evidence(inventory, output)
    output["inventory"] = inventory

    modules = _init_modules_from_findings(output["findings"])
    output["modules"] = modules

    _reconcile_and_score(output, modules)
    _attach_entity(output)
    return output


def normalize_performance_result(perf_result: dict[str, Any]) -> dict[str, Any]:
    """Attach the evidence-diagnostic-v1 contract to a performance audit result.

    Converts performance findings into the engine finding schema, injects
    performance evidence into inventory, and runs the check registry.
    Performance-only inventory is sparse, so most non-performance checks
    will correctly return UNKNOWN.
    """
    output = deepcopy(perf_result) if isinstance(perf_result, dict) else {}
    output["engine_contract"] = "evidence-diagnostic-v1"
    output["engine_scope"] = "performance"

    raw_findings = _extract_performance_findings(output)
    output["findings"] = [normalize_finding(f) for f in raw_findings]

    inventory: dict[str, Any] = output.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    inject_performance_evidence(inventory, output)
    output["inventory"] = inventory

    modules = _init_modules_from_findings(output["findings"])
    output["modules"] = modules

    _reconcile_and_score(output, modules)
    _attach_entity(output)
    return output


# Canonical 0-100 priority scale (matches scoring.priority() and _finding()).
_PERF_SEVERITY_PRIORITY: dict[str, float] = {
    "HIGH": 80.0, "MEDIUM": 50.0, "LOW": 30.0, "INFO": 10.0,
}


def _extract_performance_findings(output: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert performance-report findings into the engine finding schema."""
    report = output.get("performance_report")
    if not isinstance(report, dict):
        return []
    raw = report.get("findings")
    if not isinstance(raw, list):
        return []

    findings: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "MEDIUM")).lower()
        module_raw = str(item.get("module", "15-performance"))
        if not any(c == "-" for c in module_raw):
            module_raw = "15-performance"
        evidence_entry: dict[str, Any] = {"source": "performance-audit", "confidence": 0.9}
        raw_evidence = item.get("evidence")
        if isinstance(raw_evidence, dict):
            evidence_entry["value"] = raw_evidence
        findings.append({
            "id": f"perf-{idx + 1:03d}",
            "module": module_raw,
            "symptom": item.get("symptom", ""),
            "severity": severity,
            "status": "OBSERVED",
            "priority": _PERF_SEVERITY_PRIORITY.get(
                str(item.get("severity", "MEDIUM")).upper(), 0.5
            ),
            "root_cause": item.get("recommendation") or "Performance issue detected by browser audit",
            "evidence": [evidence_entry],
        })
    return findings
