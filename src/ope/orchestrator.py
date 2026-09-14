from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from .audit import audit
from .engine import normalize_result
from .provider_registry import integration_inventory
from .reasoning import reason_about_result


TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


@dataclass
class AuditRun:
    """State for one locally orchestrated audit."""

    run_id: str
    target: str
    status: str = "QUEUED"
    completed_modules: int = 0
    total_modules: int = 20
    current_module: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    provider_inventory: dict[str, Any] = field(default_factory=dict)


class AuditOrchestrator:
    """Run OPE end-to-end without requiring callers to chain layers manually."""

    def __init__(
        self,
        audit_fn: Callable[[str], dict[str, Any]] = audit,
        normalize_fn: Callable[[dict[str, Any]], dict[str, Any]] = normalize_result,
        reasoning_fn: Callable[[dict[str, Any]], dict[str, Any]] = reason_about_result,
    ) -> None:
        self._audit = audit_fn
        self._normalize = normalize_fn
        self._reason = reasoning_fn
        self._runs: dict[str, AuditRun] = {}
        self._executing: set[str] = set()
        self._lock = Lock()

    def create_run(self, target: str) -> AuditRun:
        target = target.strip()
        if not target:
            raise ValueError("Audit target must not be empty")
        run = AuditRun(
            run_id=f"ope-{uuid4().hex[:12]}",
            target=target,
            provider_inventory=integration_inventory(),
        )
        with self._lock:
            self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> AuditRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.status in TERMINAL_STATES:
                return False
            run.status = "CANCELLED"
            run.current_module = None
            run.completed_at = _now()
            return True

    def execute(self, run_id: str, *, enable_reasoning: bool = True) -> AuditRun:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(run_id)

        with self._lock:
            if run.status in TERMINAL_STATES:
                return run
            if run_id in self._executing:
                return run
            self._executing.add(run_id)
            run.status = "RUNNING"
            run.started_at = run.started_at or _now()
            run.current_module = "01-entity"

        try:
            raw = self._audit(run.target)
            with self._lock:
                if run.status == "CANCELLED":
                    return run
                run.current_module = "20-continuous-optimization"

            normalized = self._normalize(raw)
            if enable_reasoning:
                try:
                    advisory = self._reason(normalized)
                    normalized["reasoning"] = advisory
                except Exception as exc:  # advisory failures must not break deterministic truth
                    normalized["reasoning"] = {
                        "provider": "unavailable",
                        "advisory": False,
                        "error": type(exc).__name__,
                        "error_detail": str(exc),
                    }

            with self._lock:
                if run.status == "CANCELLED":
                    return run
                run.result = normalized
                # completed_modules must mean what its name says: the count
                # of modules that reached a conclusive status, not merely
                # that the orchestration lifecycle finished running. Most
                # real audits will legitimately report far fewer than
                # total_modules here (see registry check-binding coverage)
                # -- that is honest, not a bug. Conflating "audit finished"
                # with "all modules completed" would let a mostly-UNKNOWN
                # result claim 20/20 progress, misleading any consumer
                # (including a UI) into reading full coverage that never
                # happened.
                run.completed_modules = _count_conclusive_modules(normalized)
                run.current_module = None
                run.status = "COMPLETED"
                run.completed_at = _now()
            return run
        except Exception as exc:
            with self._lock:
                if run.status == "CANCELLED":
                    return run
                run.status = "FAILED"
                run.error = f"{type(exc).__name__}: {exc}"
                run.current_module = None
                run.completed_at = _now()
            return run
        finally:
            with self._lock:
                self._executing.discard(run_id)

    def snapshot(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        with self._lock:
            return {
                "run_id": run.run_id,
                "target": run.target,
                "status": run.status,
                "progress": {
                    "completed": run.completed_modules,
                    "total": run.total_modules,
                    "current_module": run.current_module,
                },
                "result": run.result,
                "error": run.error,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "providers": run.provider_inventory,
            }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_CONCLUSIVE_MODULE_STATUSES = {"PASS", "FAIL", "N/A"}


def _count_conclusive_modules(normalized_result: dict[str, Any]) -> int:
    """Count modules that reached a conclusive status.

    PASS, FAIL, and N/A are conclusive outcomes -- the module was actually
    evaluated to a genuine result. UNKNOWN and BLOCKED mean evaluation did
    not reach a conclusion (missing evidence or a blocked dependency,
    respectively) and must not be counted as "completed" merely because
    the orchestration lifecycle itself finished running.
    """
    modules = normalized_result.get("modules")
    if not isinstance(modules, dict):
        return 0
    return sum(
        1
        for module in modules.values()
        if isinstance(module, dict) and module.get("status") in _CONCLUSIVE_MODULE_STATUSES
    )
