from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_VERSION = "run-history-v1"
MAX_RUNS_PER_TARGET = 50

# Metrics compared between runs as (inventory key, better direction, relative
# tolerance, minimum absolute delta). The absolute floor keeps normal run-to-run
# jitter from being reported as a regression.
_TRACKED_METRICS = (
    ("ttfb_ms", "lower", 0.5, 50.0),
    ("page_weight_bytes", "lower", 0.25, 50_000),
    ("word_count", "higher", 0.25, 100),
)


def history_dir(directory: str | Path | None = None) -> Path:
    if directory:
        return Path(directory)
    return Path(os.getenv("OPE_HOME") or (Path.home() / ".ope")) / "runs"


def _target_key(target: str, scope: str = "page") -> str:
    """Stable, filesystem-safe directory name for an audited target.

    Keyed by (scope, target) so different audit scopes of the same URL never
    share a history keyspace: a page audit, a site audit, and a performance
    audit of the same target carry different findings and metrics, and mixing
    them would produce misleading regression comparisons.
    """
    return hashlib.sha256(f"{scope}:{target}".encode("utf-8")).hexdigest()[:16]


def _metrics(inventory: dict[str, Any]) -> dict[str, float]:
    values = {}
    for key, _, _, _ in _TRACKED_METRICS:
        value = inventory.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values[key] = float(value)
    return values


def snapshot(result: dict[str, Any]) -> dict[str, Any]:
    """Reduce one audit result to the durable record a later run compares against."""
    inventory = result.get("inventory") or {}
    checks = result.get("checks") or {}
    return {
        "version": HISTORY_VERSION,
        "run_id": result.get("run_id"),
        "target": result.get("target"),
        "final_url": result.get("final_url"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "metrics": _metrics(inventory if isinstance(inventory, dict) else {}),
        "finding_ids": sorted({str(item.get("id")) for item in result.get("findings") or [] if isinstance(item, dict) and item.get("id")}),
        "check_statuses": {check_id: str(check.get("status")) for check_id, check in checks.items() if isinstance(check, dict)},
    }


def save_run(result: dict[str, Any], directory: str | Path | None = None) -> Path | None:
    """Persist one run, returning None when the store is not writable."""
    try:
        scope = str(result.get("engine_scope") or "page")
        target_dir = history_dir(directory) / _target_key(str(result.get("target") or ""), scope)
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = target_dir / f"{stamp}.json"
        path.write_text(json.dumps(snapshot(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for stale in sorted(target_dir.glob("*.json"), reverse=True)[MAX_RUNS_PER_TARGET:]:
            stale.unlink(missing_ok=True)
        return path
    except OSError:
        return None


def load_runs(target: str, directory: str | Path | None = None, limit: int = MAX_RUNS_PER_TARGET, scope: str = "page") -> list[dict[str, Any]]:
    """Load stored runs for one target and scope, newest first."""
    target_dir = history_dir(directory) / _target_key(str(target or ""), scope)
    if not target_dir.is_dir():
        return []
    runs = []
    for path in sorted(target_dir.glob("*.json"), reverse=True)[:limit]:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(record, dict):
            runs.append(record)
    return runs


def compare(inventory: dict[str, Any], findings: list[Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Diff the current observations against the most recent stored run.

    Tolerates a parseable-but-malformed baseline record: fields with the
    wrong type are treated as absent rather than raising, so a corrupt
    history entry degrades to "no comparison" instead of crashing the audit.
    """
    raw_baseline_metrics = baseline.get("metrics")
    baseline_metrics = raw_baseline_metrics if isinstance(raw_baseline_metrics, dict) else {}
    current_metrics = _metrics(inventory)
    regressions = []
    for key, direction, tolerance, floor in _TRACKED_METRICS:
        before, after = baseline_metrics.get(key), current_metrics.get(key)
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            continue
        delta = after - before
        if direction == "lower" and delta > max(before * tolerance, floor):
            regressions.append({"metric": key, "before": before, "after": after, "direction": direction})
        elif direction == "higher" and -delta > max(before * tolerance, floor):
            regressions.append({"metric": key, "before": before, "after": after, "direction": direction})

    baseline_findings = set(baseline.get("finding_ids") or [])
    current_findings = {str(item.get("id")) for item in findings if isinstance(item, dict) and item.get("id")}
    return {
        "metric_regressions": regressions,
        "new_findings": sorted(current_findings - baseline_findings),
        "resolved_findings": sorted(baseline_findings - current_findings),
    }


def attach_baseline(result: dict[str, Any], directory: str | Path | None = None) -> dict[str, Any]:
    """Attach run-history evidence to an audit result, in place.

    The engine stays honest about a first run: with no stored baseline
    there is nothing to compare, and the history block says so rather
    than implying a clean comparison.
    """
    inventory = result.get("inventory")
    if not isinstance(inventory, dict):
        return result
    target = str(result.get("target") or "")
    scope = str(result.get("engine_scope") or "page")
    runs = load_runs(target, directory, scope=scope)
    store = history_dir(directory)
    try:
        store.mkdir(parents=True, exist_ok=True)
        writable = os.access(store, os.W_OK)
    except OSError:
        writable = False

    history: dict[str, Any] = {"store_writable": writable, "runs_recorded": len(runs), "baseline_run_id": None, "baseline_recorded_at": None, "metric_regressions": None, "new_findings": None, "resolved_findings": None}
    if runs:
        baseline = runs[0]
        history["baseline_run_id"] = baseline.get("run_id")
        history["baseline_recorded_at"] = baseline.get("recorded_at")
        history.update(compare(inventory, result.get("findings") or [], baseline))
    inventory["history"] = history
    return result
