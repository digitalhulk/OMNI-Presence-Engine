from __future__ import annotations

from copy import deepcopy
from typing import Any


def enrich_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Normalize an existing finding into OPE's root-cause contract.

    Empty root-cause fields remain explicit rather than being promoted to PASS.
    """
    item = deepcopy(finding)
    module = str(item.get("module", ""))
    evidence = item.get("evidence") or []
    confidence = min((float(e.get("confidence", 0.2)) for e in evidence), default=0.2)
    item["confidence"] = round(max(0.0, min(1.0, confidence)), 3)
    item.setdefault("affected_layer", module)
    item.setdefault("dependency", "")
    item.setdefault("impact", "")
    item.setdefault("regression_guard", [])
    item["status"] = item.get("status") or "OBSERVED"
    if not item.get("root_cause"):
        item["root_cause"] = "Not yet established; additional evidence or dependency analysis is required."
        item["status"] = "HYPOTHESIS"
    item["priority"] = round(float(item.get("priority", 0.0)), 2)
    return item


def enrich_result(result: dict[str, Any]) -> dict[str, Any]:
    """Apply the common finding contract without changing deterministic observations."""
    output = deepcopy(result)
    output["engine_contract"] = "evidence-root-cause-v1"
    output["findings"] = [enrich_finding(f) for f in result.get("findings", [])]
    return output
