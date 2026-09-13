from __future__ import annotations

from typing import Any

from .engine import normalize_finding, normalize_result


def enrich_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible alias for the canonical engine normalizer."""
    return normalize_finding(finding)


def enrich_result(result: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible alias for the canonical engine normalizer."""
    return normalize_result(result)
