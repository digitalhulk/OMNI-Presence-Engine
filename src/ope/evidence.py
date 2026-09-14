from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InvalidEvidenceError(ValueError):
    """Raised when an evidence item is missing a required identity field.

    source and target identify what was observed and where the observation
    came from; there is no safe default for either; fabricating one would
    violate the evidence-first contract, so this is a hard failure rather
    than a silent coercion.
    """


@dataclass(frozen=True)
class EvidenceRecord:
    source: str
    target: str
    value: Any
    observed_at: str = field(default_factory=utc_now)
    confidence: float = 1.0
    provenance: str = "direct"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_confidence(value: Any) -> float:
    """Coerce a confidence value, treating anything untrustworthy as 0.0.

    An unparsable or missing confidence is not evidence that the observation
    is reliable; it is the opposite. This must never raise, since a caller
    passing a malformed confidence should get the lowest-confidence, honest
    outcome rather than an unhandled crash that could interrupt an audit.
    """
    return max(0.0, min(1.0, _safe_float(value, 0.0)))


def normalize_evidence(items: list[EvidenceRecord | dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, EvidenceRecord):
            if not item.source.strip() or not item.target.strip():
                raise InvalidEvidenceError(
                    "Evidence item is missing a required 'source' or 'target' identifier"
                )
            record = item
        elif isinstance(item, dict):
            source = item.get("source")
            target = item.get("target")
            if not isinstance(source, str) or not source.strip() or not isinstance(target, str) or not target.strip():
                raise InvalidEvidenceError(
                    "Evidence item is missing a required 'source' or 'target' identifier"
                )
            # confidence is re-derived safely below regardless of what is
            # supplied here, so any raw value is an acceptable placeholder.
            record = EvidenceRecord(**{**item, "confidence": 1.0})
        else:
            raise InvalidEvidenceError(
                f"Evidence item must be an EvidenceRecord or dict, got {type(item).__name__}"
            )
        raw_confidence = item.confidence if isinstance(item, EvidenceRecord) else item.get("confidence", 1.0)
        normalized.append({**record.to_dict(), "confidence": _safe_confidence(raw_confidence)})
    return normalized


@dataclass
class RootCauseFinding:
    id: str
    module: str
    symptom: str
    status: str
    severity: str
    priority: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    affected_layer: str = ""
    dependency: str = ""
    root_cause: str = ""
    impact: str = ""
    remediation: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    regression_guard: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_finding(
    *,
    finding_id: str,
    module: str,
    symptom: str,
    severity: str,
    evidence: list[EvidenceRecord | dict[str, Any]],
    affected_layer: str = "",
    dependency: str = "",
    root_cause: str = "",
    impact: str = "",
    remediation: list[str] | None = None,
    validation: list[str] | None = None,
    regression_guard: list[str] | None = None,
    status: str = "OBSERVED",
    priority: float = 0.0,
) -> RootCauseFinding:
    return RootCauseFinding(
        id=finding_id,
        module=module,
        symptom=symptom,
        status=status,
        severity=severity,
        priority=round(max(0.0, min(100.0, _safe_float(priority, 0.0))), 2),
        evidence=normalize_evidence(evidence),
        affected_layer=affected_layer,
        dependency=dependency,
        root_cause=root_cause,
        impact=impact,
        remediation=remediation or [],
        validation=validation or [],
        regression_guard=regression_guard or [],
    )
