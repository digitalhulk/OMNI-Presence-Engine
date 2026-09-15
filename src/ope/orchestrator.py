"""Multi-target audit orchestration.

Runs the single-target audit pipeline across many targets with bounded
concurrency and strict per-target isolation: one target failing (network
error, SSRF block, timeout) never destroys the results for the others. The
aggregate is deterministic — results are returned in input order regardless
of completion order, and the summary is computed from them deterministically.

This is the reusable execution primitive an external scheduler builds on:
a scheduler decides *when* to run and supplies the target list; the engine
owns *how* each target is audited and how results aggregate.
"""
from __future__ import annotations

import concurrent.futures
from typing import Any, Callable

from . import history as history_module
from .audit import ENGINE_VERSION, audit
from .engine import normalize_result

MAX_WORKERS_CAP = 16


def _audit_one(url: str, *, timeout: int, fetch_subresources: bool, record_history: bool) -> dict[str, Any]:
    """Audit a single target, capturing failure as data rather than raising."""
    try:
        raw = audit(url, timeout=timeout, fetch_subresources=fetch_subresources)
        if record_history:
            history_module.attach_baseline(raw)
        result = normalize_result(raw)
        if record_history:
            history_module.save_run(result)
        return {"target": url, "ok": True, "result": result, "error": None}
    except Exception as exc:  # isolation boundary: never let one target abort the batch
        return {"target": url, "ok": False, "result": None, "error": f"{type(exc).__name__}: {exc}"}


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    succeeded = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    healths = [
        r["result"]["health"]
        for r in succeeded
        if isinstance(r.get("result"), dict) and isinstance(r["result"].get("health"), (int, float))
    ]
    total_findings = sum(
        len(r["result"].get("findings", []))
        for r in succeeded
        if isinstance(r.get("result"), dict)
    )
    return {
        "target_count": len(results),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "failed_targets": [r["target"] for r in failed],
        "mean_health": round(sum(healths) / len(healths), 2) if healths else None,
        "total_findings": total_findings,
    }


def audit_targets(
    urls: list[str],
    *,
    timeout: int = 15,
    fetch_subresources: bool = True,
    max_workers: int = 4,
    record_history: bool = False,
    auditor: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audit many targets with bounded concurrency and per-target isolation.

    Results are returned in the same order as *urls* (deterministic), each as
    ``{"target", "ok", "result", "error"}``. A failing target is recorded with
    ``ok=False`` and an ``error`` string; it never affects the others.
    ``max_workers`` is clamped to a safe cap and to the number of targets, so
    no unbounded worker pool is created.

    ``auditor`` is an injection seam for testing; production uses the real
    single-target pipeline.
    """
    run = auditor or (
        lambda url: _audit_one(url, timeout=timeout, fetch_subresources=fetch_subresources, record_history=record_history)
    )
    if not urls:
        return {"engine": "ope", "version": ENGINE_VERSION, "results": [], "summary": _aggregate([])}

    workers = max(1, min(max_workers, len(urls), MAX_WORKERS_CAP))
    indexed: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run, url): i for i, url in enumerate(urls)}
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            try:
                indexed[index] = future.result()
            except Exception as exc:  # defensive: auditor promised not to raise, but isolate anyway
                indexed[index] = {"target": urls[index], "ok": False, "result": None, "error": f"{type(exc).__name__}: {exc}"}

    results = [indexed[i] for i in range(len(urls))]  # restore input order
    return {"engine": "ope", "version": ENGINE_VERSION, "results": results, "summary": _aggregate(results)}


def multi_audit_markdown(report: dict[str, Any]) -> str:
    """Render a concise, deterministic aggregate summary of a multi-target run."""
    summary = report.get("summary", {})
    lines = [
        "# OPE Multi-Target Audit",
        "",
        f"**Targets:** {summary.get('target_count', 0)}  ",
        f"**Succeeded:** {summary.get('succeeded', 0)}  ",
        f"**Failed:** {summary.get('failed', 0)}  ",
        f"**Mean health:** {summary.get('mean_health')}  ",
        f"**Total findings:** {summary.get('total_findings', 0)}",
        "",
        "| Target | Status | Health | Findings |",
        "| --- | --- | --- | --- |",
    ]
    for entry in report.get("results", []):
        if entry["ok"] and isinstance(entry.get("result"), dict):
            r = entry["result"]
            health = r.get("health")
            lines.append(f"| {entry['target']} | OK | {health if health is not None else '—'} | {len(r.get('findings', []))} |")
        else:
            lines.append(f"| {entry['target']} | FAILED | — | {entry.get('error', 'error')} |")
    return "\n".join(lines)
