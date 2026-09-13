from __future__ import annotations

from typing import Any


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, float(value))), 2)


def priority(*, impact: float, confidence: float, urgency: float, fixability: float) -> float:
    """Calculate remediation priority from bounded inputs."""
    return clamp(100 * impact * confidence * urgency * fixability)


def module_score(module: dict[str, Any]) -> float | None:
    """Return a score only when the module has executed evidence-backed checks."""
    status = module.get("status")
    if status in {None, "UNKNOWN", "BLOCKED", "N/A"}:
        return None
    if status == "FAIL":
        return 0.0
    if status != "PASS":
        return None
    return 100.0
