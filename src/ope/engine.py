from __future__ import annotations

from copy import deepcopy
from typing import Any

from .audit_pipeline import execute_audit_checks
from .module_runner import ExecutionStatus
from .registry import checks_for_module

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
    item["priority"] = round(max(0.0, min(1.0, _safe_float(item.get("priority", 0.0), 0.0))), 2)
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


def normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Attach the stable evidence/diagnostic contract to an audit result."""
    output = deepcopy(result) if isinstance(result, dict) else {}
    output["engine_contract"] = "evidence-diagnostic-v1"

    raw_findings = output.get("findings")
    findings = raw_findings if isinstance(raw_findings, list) else []
    output["findings"] = [normalize_finding(finding) for finding in findings]

    # Execute the deterministic registry against the evidence already collected
    # by audit.py. No new evidence is invented here.
    execution = execute_audit_checks(output)
    checks = execution.get("checks", {}) if isinstance(execution, dict) else {}
    if not isinstance(checks, dict):
        checks = {}

    # Reconcile only the existing module status field. Inventory, findings and
    # other report keys are preserved exactly; partial registry coverage is
    # explicitly UNKNOWN rather than a false PASS.
    modules = output.get("modules")
    if not isinstance(modules, dict):
        modules = {}
        output["modules"] = modules

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
        # Checks missing from execution output are treated as UNKNOWN.
        # This prevents partial registry coverage from silently becoming PASS.
        statuses = [
            str(checks[check_id].get("status", ExecutionStatus.UNKNOWN.value))
            if isinstance(checks.get(check_id), dict)
            else ExecutionStatus.UNKNOWN.value
            for check_id in check_ids
        ]
        module["status"] = _reconcile_module_status(module.get("status"), statuses)

    return output
