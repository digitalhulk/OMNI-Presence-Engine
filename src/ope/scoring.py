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


def module_score_basis(module: dict[str, Any], module_checks: dict[str, Any] | None = None) -> dict[str, Any]:
    """Deterministic explanation of how a module's score was derived.

    Returns a structured basis dict so a score is never an opaque number:
    the ``method`` names the derivation path, and the check tallies and
    evidence-weighted totals show exactly what produced the ``score``.  This
    is provenance, not a second scoring path — ``module_score()`` returns
    this dict's ``score`` field, so the number and its explanation can never
    disagree.
    """
    status = module.get("status")

    if status == "BLOCKED":
        basis: dict[str, Any] = {
            "score": None,
            "status": "BLOCKED",
            "method": "blocked",
            "reason": "Upstream dependency failure; check results are not reliable.",
        }
        blocked_by = module.get("blocked_by")
        if isinstance(blocked_by, list) and blocked_by:
            basis["blocked_by"] = list(blocked_by)
        return basis

    if not module_checks:
        if status in {None, "UNKNOWN", "N/A"}:
            return {
                "score": None,
                "status": status if status is not None else "UNKNOWN",
                "method": "no-evidence",
                "reason": "No evidence-backed checks; a numeric score cannot be stated.",
            }
        if status == "FAIL":
            return {"score": 0.0, "status": "FAIL", "method": "status-derived"}
        if status == "PASS":
            return {"score": 100.0, "status": "PASS", "method": "status-derived"}
        return {
            "score": None,
            "status": str(status),
            "method": "no-evidence",
            "reason": f"Unrecognized status {status!r}; no numeric score.",
        }

    checks_total = 0
    passed = 0
    failed = 0
    unknown = 0
    na = 0
    weighted_pass = 0.0
    weighted_total = 0.0

    for check_data in module_checks.values():
        if not isinstance(check_data, dict):
            continue
        checks_total += 1
        check_status = check_data.get("status", "UNKNOWN")
        if check_status == "N/A":
            na += 1
            continue

        weight = _evidence_weight(check_data)
        weighted_total += weight

        if check_status == "PASS":
            passed += 1
            weighted_pass += weight
        elif check_status == "FAIL":
            failed += 1
        else:
            unknown += 1

    if weighted_total == 0:
        return {
            "score": None,
            "status": str(status) if status is not None else "UNKNOWN",
            "method": "no-evidence",
            "reason": "Every applicable check is N/A; the module cannot be scored.",
            "checks_total": checks_total,
            "checks_na": na,
        }

    score = clamp((weighted_pass / weighted_total) * 100)
    return {
        "score": score,
        "status": str(status) if status is not None else "UNKNOWN",
        "method": "evidence-weighted-coverage",
        "checks_total": checks_total,
        "checks_passed": passed,
        "checks_failed": failed,
        "checks_unknown": unknown,
        "checks_na": na,
        "weighted_pass": round(weighted_pass, 4),
        "weighted_total": round(weighted_total, 4),
    }


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
    BLOCKED modules always return None — their results may be unreliable
    due to upstream failure.  The full derivation is available via
    ``module_score_basis()``; this function returns that basis's ``score``.
    """
    score: float | None = module_score_basis(module, module_checks)["score"]
    return score


def health_basis(module_scores: dict[str, float | None]) -> dict[str, Any]:
    """Deterministic explanation of the dependency-aware global health score.

    Traverses the real dependency graph in topological order and records,
    per scored module, the upstream confidence applied and the resulting
    adjusted contribution.  ``global_health()`` returns this dict's
    ``health`` field, so the rolled-up number is always traceable to the
    per-module contributions that produced it.
    """
    from .dependency_graph import DEPENDENCIES_BY_NUMBER, TOPOLOGICAL_ORDER_NUMBERS

    scored = {k: v for k, v in module_scores.items() if v is not None}
    if not scored:
        return {
            "health": None,
            "method": "graph-topological-weighted",
            "modules_scored": 0,
            "contributions": [],
        }

    confidence: dict[str, float] = {}
    contributions: list[dict[str, Any]] = []
    weighted_sum = 0.0
    total_weight = 0.0

    for module_key in TOPOLOGICAL_ORDER_NUMBERS:
        if module_key not in scored:
            continue

        upstream_conf = 1.0
        limiting: str | None = None
        for dep_key in DEPENDENCIES_BY_NUMBER.get(module_key, ()):
            if dep_key in confidence and confidence[dep_key] < upstream_conf:
                upstream_conf = confidence[dep_key]
                limiting = dep_key

        score = scored[module_key]
        adjusted = score * upstream_conf
        weighted_sum += adjusted
        total_weight += 1.0

        module_conf = upstream_conf
        if score < 50.0:
            module_conf *= 0.9
        confidence[module_key] = module_conf

        contributions.append({
            "module": module_key,
            "score": score,
            "upstream_confidence": round(upstream_conf, 4),
            "adjusted": round(adjusted, 4),
            "module_confidence": round(module_conf, 4),
            "limiting_upstream": limiting,
        })

    return {
        "health": clamp(weighted_sum / total_weight),
        "method": "graph-topological-weighted",
        "modules_scored": len(contributions),
        "contributions": contributions,
    }


def global_health(module_scores: dict[str, float | None]) -> float | None:
    """Dependency-aware global health per scoring-v1 spec.

    Upstream modules that score poorly reduce confidence in downstream
    scores.  The traversal follows the real dependency graph (not module
    numbers), so parallel branches do not penalise each other.
    Returns None when no modules have a numeric score.  The full derivation
    is available via ``health_basis()``; this function returns its ``health``.
    """
    health: float | None = health_basis(module_scores)["health"]
    return health
