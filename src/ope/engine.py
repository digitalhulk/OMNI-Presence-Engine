from __future__ import annotations

from copy import deepcopy
from typing import Any


def normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Attach the common evidence/diagnostic contract to an audit result."""
    output = deepcopy(result)
    output["engine_contract"] = "evidence-diagnostic-v1"
    normalized = []
    for finding in output.get("findings", []):
        item = deepcopy(finding)
        evidence = item.get("evidence") or []
        confidence = min((float(e.get("confidence", 0.2)) for e in evidence), default=0.2)
        item["confidence"] = round(max(0.0, min(1.0, confidence)), 3)
        item.setdefault("affected_layer", item.get("module", ""))
        item.setdefault("dependency", "")
        item.setdefault("impact", "")
        item.setdefault("regression_guard", [])
        item["status"] = item.get("status") or "OBSERVED"
        if not item.get("root_cause"):
            item["root_cause"] = "Not yet established; additional evidence or dependency analysis is required."
            item["status"] = "HYPOTHESIS"
        item["priority"] = round(float(item.get("priority", 0.0)), 2)
        normalized.append(item)
    output["findings"] = normalized
    return output
