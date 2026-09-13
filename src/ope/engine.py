from __future__ import annotations

from copy import deepcopy
from typing import Any

from .audit_pipeline import execute_audit_checks

HYPOTHESIS_ROOT_CAUSE = "Not yet established; additional evidence or dependency analysis is required."


def normalize_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Normalize one finding without treating missing evidence as success."""
    item = deepcopy(finding)
    evidence = item.get("evidence") or []
    confidence = min((float(e.get("confidence", 0.2)) for e in evidence), default=0.2)
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
    item["priority"] = round(float(item.get("priority", 0.0)), 2)
    return item


def normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Attach the stable evidence/diagnostic contract to an audit result."""
    output = deepcopy(result)
    output["engine_contract"] = "evidence-diagnostic-v1"
    output["findings"] = [normalize_finding(f) for f in output.get("findings", [])]

    # Execute the deterministic registry against the evidence already collected
    # by audit.py. No new evidence is invented here.
    execution = execute_audit_checks(output)
    for module in output.get("modules", {}).values():
        if not module.get("findings") and module.get("status") == "PASS":
            module["status"] = "UNKNOWN"

    for check in execution.get("checks", {}).values():
        if check.get("status") == "FAIL":
            module = str(check.get("module", ""))
            module_number = module.split("-", 1)[0]
            if module_number in output.get("modules", {}):
                output["modules"][module_number]["status"] = "FAIL"

    return output
