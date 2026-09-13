from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def normalize_evidence(items: list[EvidenceRecord | dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        record = item if isinstance(item, EvidenceRecord) else EvidenceRecord(**item)
        confidence = max(0.0, min(1.0, float(record.confidence)))
        normalized.append({**record.to_dict(), "confidence": confidence})
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
        priority=round(float(priority), 2),
        evidence=normalize_evidence(evidence),
        affected_layer=affected_layer,
        dependency=dependency,
        root_cause=root_cause,
        impact=impact,
        remediation=remediation or [],
        validation=validation or [],
        regression_guard=regression_guard or [],
    )
