from __future__ import annotations

from typing import Any


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, float(value))), 2)


def priority(*, impact: float, confidence: float, urgency: float, fixability: float) -> float:
    """Calculate remediation priority from bounded inputs."""
    return clamp(100 * impact * confidence * urgency * fixability)


def _evidence_weight(check_data: dict[str, Any]) -> float:
    """Derive a check's weight from its evidence confidence."""
    evidence = check_data.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        return 1.0
    confidences: list[float] = []
    for entry in evidence:
        if isinstance(entry, dict):
            raw = entry.get("confidence")
            if raw is not None:
                try:
                    confidences.append(float(raw))
                except (TypeError, ValueError):
                    pass
    if not confidences:
        return 1.0
    return max(0.01, min(1.0, sum(confidences) / len(confidences)))


def module_score(module: dict[str, Any], module_checks: dict[str, Any] | None = None) -> float | None:
    """Evidence-weighted pass coverage per scoring-v1 spec.

    When *module_checks* is provided (a dict of check_id → check result dict
    for every check that belongs to this module), the score is the weighted
    fraction of checks that passed, where each check's weight is derived
    from its evidence confidence.  N/A checks are excluded from the
    denominator — they cannot apply to the target.  UNKNOWN checks count in
    the denominator but not the numerator: unknown is never treated as pass.

    Returns None when no evidence-backed checks exist (all N/A, or no
    checks at all), signalling that a numeric score cannot be stated.
    """
    if not module_checks:
        status = module.get("status")
        if status in {None, "UNKNOWN", "BLOCKED", "N/A"}:
            return None
        if status == "FAIL":
            return 0.0
        if status == "PASS":
            return 100.0
        return None

    weighted_pass = 0.0
    weighted_total = 0.0

    for check_data in module_checks.values():
        if not isinstance(check_data, dict):
            continue
        status = check_data.get("status", "UNKNOWN")
        if status == "N/A":
            continue

        weight = _evidence_weight(check_data)
        weighted_total += weight

        if status == "PASS":
            weighted_pass += weight

    if weighted_total == 0:
        return None

    return clamp((weighted_pass / weighted_total) * 100)


def global_health(module_scores: dict[str, float | None]) -> float | None:
    """Dependency-aware global health per scoring-v1 spec.

    Upstream modules (lower-numbered) that score poorly reduce confidence
    in downstream scores, but downstream observations remain visible.
    Returns None when no modules have a numeric score.
    """
    scored = {k: v for k, v in module_scores.items() if v is not None}
    if not scored:
        return None

    weighted_sum = 0.0
    total_weight = 0.0
    upstream_confidence = 1.0

    for module_key in sorted(scored.keys()):
        score = scored[module_key]
        adjusted = score * upstream_confidence
        weighted_sum += adjusted
        total_weight += 1.0
        if score < 50.0:
            upstream_confidence *= 0.9

    return clamp(weighted_sum / total_weight)
