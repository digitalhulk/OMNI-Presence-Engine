from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter
from typing import Any, Callable, Iterable


class ExecutionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    NA = "N/A"


CheckRunner = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class CheckSpec:
    id: str
    module: str
    runner: CheckRunner
    depends_on: tuple[str, ...] = ()


@dataclass
class CheckResult:
    check_id: str
    module: str
    status: ExecutionStatus
    evidence: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"check_id": self.check_id, "module": self.module, "status": self.status.value, "evidence": self.evidence, "findings": self.findings, "reason": self.reason, "duration_ms": self.duration_ms}


class DependencyError(ValueError):
    pass


class ModuleRunner:
    """Deterministic dependency-aware executor for OPE checks."""

    DEFAULT_BLOCK_ON = frozenset({ExecutionStatus.FAIL, ExecutionStatus.BLOCKED, ExecutionStatus.UNKNOWN})

    def __init__(self, checks: Iterable[CheckSpec], *, block_on: frozenset[ExecutionStatus] | None = None) -> None:
        self.checks = tuple(sorted(checks, key=lambda c: c.id))
        self.block_on = self.DEFAULT_BLOCK_ON if block_on is None else frozenset(block_on)
        self._validate()

    def _validate(self) -> None:
        ids = [c.id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise DependencyError("Duplicate check id detected")
        known = set(ids)
        for check in self.checks:
            missing = sorted(set(check.depends_on) - known)
            if missing:
                raise DependencyError(f"Check {check.id} has missing dependencies: {', '.join(missing)}")
        self._topological_order()

    def _topological_order(self) -> list[CheckSpec]:
        by_id = {c.id: c for c in self.checks}
        state: dict[str, int] = {}
        ordered: list[CheckSpec] = []
        def visit(check_id: str) -> None:
            mark = state.get(check_id, 0)
            if mark == 1:
                raise DependencyError(f"Dependency cycle detected at {check_id}")
            if mark == 2:
                return
            state[check_id] = 1
            for dep in sorted(by_id[check_id].depends_on):
                visit(dep)
            state[check_id] = 2
            ordered.append(by_id[check_id])
        for check in self.checks:
            visit(check.id)
        return ordered

    def run(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        results: dict[str, CheckResult] = {}
        for check in self._topological_order():
            dependency_results = [results[d] for d in check.depends_on]
            blockers = [r for r in dependency_results if r.status in self.block_on]
            if blockers:
                reason = "Blocked by: " + ", ".join(f"{r.check_id}={r.status.value}" for r in sorted(blockers, key=lambda x: x.check_id))
                results[check.id] = CheckResult(check.id, check.module, ExecutionStatus.BLOCKED, reason=reason)
                continue
            started = perf_counter()
            try:
                raw = check.runner(ctx)
                result = self._coerce(check, raw)
            except Exception as exc:
                result = CheckResult(check.id, check.module, ExecutionStatus.FAIL, reason=f"check execution failed: {type(exc).__name__}: {exc}")
            result.duration_ms = round((perf_counter() - started) * 1000, 3)
            results[check.id] = result
        return self._build_output(results)

    @staticmethod
    def _valid_evidence(evidence: Any) -> bool:
        if not isinstance(evidence, list) or not evidence:
            return False
        for record in evidence:
            if not isinstance(record, dict):
                return False
            if not isinstance(record.get("source"), str) or not record["source"].strip():
                return False
            if not isinstance(record.get("observed_at"), str) or not record["observed_at"].strip():
                return False
            confidence = record.get("confidence")
            if confidence is not None:
                try:
                    if not 0 <= float(confidence) <= 1:
                        return False
                except (TypeError, ValueError):
                    return False
        return True

    @classmethod
    def _coerce(cls, check: CheckSpec, raw: Any) -> CheckResult:
        if isinstance(raw, CheckResult):
            if raw.check_id != check.id or raw.module != check.module:
                raise ValueError("CheckResult identity does not match CheckSpec")
            if raw.status == ExecutionStatus.PASS and not cls._valid_evidence(raw.evidence):
                reason = raw.reason or "PASS result has invalid or missing evidence"
                return CheckResult(check.id, check.module, ExecutionStatus.UNKNOWN, list(raw.evidence), list(raw.findings), reason)
            return raw
        if raw is True:
            return CheckResult(check.id, check.module, ExecutionStatus.UNKNOWN, reason="check returned PASS without evidence")
        if raw is False:
            return CheckResult(check.id, check.module, ExecutionStatus.FAIL, reason="check returned a negative result")
        if raw is None:
            return CheckResult(check.id, check.module, ExecutionStatus.UNKNOWN, reason="check returned no result")
        if isinstance(raw, dict):
            status = ExecutionStatus(str(raw.get("status", ExecutionStatus.UNKNOWN.value)))
            evidence = list(raw.get("evidence", []))
            findings = list(raw.get("findings", []))
            reason = str(raw.get("reason", ""))
            if status == ExecutionStatus.PASS and not cls._valid_evidence(evidence):
                reason = reason or "PASS result has invalid or missing evidence"
                status = ExecutionStatus.UNKNOWN
            return CheckResult(check.id, check.module, status, evidence, findings, reason)
        raise TypeError(f"Unsupported check result type: {type(raw).__name__}")

    def _build_output(self, results: dict[str, CheckResult]) -> dict[str, Any]:
        by_module: dict[str, list[CheckResult]] = {}
        for result in results.values():
            by_module.setdefault(result.module, []).append(result)
        modules = {module: {"status": aggregate_status(items).value, "checks": [r.check_id for r in sorted(items, key=lambda x: x.check_id)]} for module, items in sorted(by_module.items())}
        return {"checks": {key: value.to_dict() for key, value in sorted(results.items())}, "modules": modules}


def aggregate_status(results: Iterable[CheckResult]) -> ExecutionStatus:
    items = list(results)
    if not items:
        return ExecutionStatus.UNKNOWN
    statuses = {r.status for r in items}
    if ExecutionStatus.FAIL in statuses:
        return ExecutionStatus.FAIL
    if ExecutionStatus.BLOCKED in statuses:
        return ExecutionStatus.BLOCKED
    if statuses == {ExecutionStatus.NA}:
        return ExecutionStatus.NA
    if statuses == {ExecutionStatus.PASS}:
        return ExecutionStatus.PASS
    if ExecutionStatus.UNKNOWN in statuses:
        return ExecutionStatus.UNKNOWN
    if ExecutionStatus.NA in statuses:
        return ExecutionStatus.UNKNOWN
    return ExecutionStatus.UNKNOWN
