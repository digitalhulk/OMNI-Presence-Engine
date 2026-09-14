from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

Provider = Callable[[str], Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Observation:
    source: str
    target: str
    value: Any = None
    confidence: float = 1.0
    provenance: str = "direct"
    observed_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        confidence = max(0.0, min(1.0, float(self.confidence)))
        return {
            "source": self.source,
            "target": self.target,
            "value": self.value,
            "confidence": confidence,
            "provenance": self.provenance,
            "observed_at": self.observed_at,
        }


class EvidenceProviderRegistry:
    """Registry for evidence providers; absence of a provider is explicit."""

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, source: str, provider: Provider) -> None:
        key = source.strip()
        if not key:
            raise ValueError("Evidence source must not be empty")
        if key in self._providers:
            raise ValueError(f"Evidence provider already registered: {key}")
        self._providers[key] = provider

    def available(self, source: str) -> bool:
        return source in self._providers

    def observe(self, source: str, target: str) -> Observation:
        provider = self._providers.get(source)
        if provider is None:
            return Observation(
                source=source,
                target=target,
                value=None,
                confidence=0.0,
                provenance="unavailable",
            )
        value = provider(target)
        return Observation(source=source, target=target, value=value)

    def sources(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
