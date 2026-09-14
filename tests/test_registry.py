"""Tests for registry.py — check definitions, runner building, and invariants."""
from __future__ import annotations

from ope.module_runner import CheckResult, ExecutionStatus
from ope.registry import (
    CHECKS,
    build_runner,
    checks_for_module,
    registered_check_ids,
)


class TestCheckDefinitions:
    def test_136_checks(self) -> None:
        assert len(CHECKS) == 136

    def test_20_modules(self) -> None:
        modules = {c.module for c in CHECKS}
        assert len(modules) == 20

    def test_no_duplicate_check_ids(self) -> None:
        ids = [c.id for c in CHECKS]
        assert len(ids) == len(set(ids))

    def test_check_id_format(self) -> None:
        for c in CHECKS:
            assert c.id == f"{c.module}.{c.check_name}"

    def test_module_numbering(self) -> None:
        modules = sorted({c.module for c in CHECKS})
        for m in modules:
            num = m.split("-")[0]
            assert num.isdigit()
            assert 1 <= int(num) <= 20


class TestRegisteredCheckIds:
    def test_returns_all_ids(self) -> None:
        ids = registered_check_ids()
        assert len(ids) == 136
        assert isinstance(ids, tuple)

    def test_ids_match_checks(self) -> None:
        ids = registered_check_ids()
        for check in CHECKS:
            assert check.id in ids


class TestChecksForModule:
    def test_entity_module(self) -> None:
        ids = checks_for_module("01-entity")
        assert len(ids) == 5
        assert "01-entity.identity" in ids

    def test_performance_module(self) -> None:
        ids = checks_for_module("15-performance")
        assert len(ids) == 11

    def test_unknown_module_returns_empty(self) -> None:
        ids = checks_for_module("99-nonexistent")
        assert len(ids) == 0


class TestBuildRunner:
    def test_unbound_checks_return_unknown(self) -> None:
        runner = build_runner()
        output = runner.run({})
        checks = output["checks"]
        for check_id, result in checks.items():
            assert result["status"] == ExecutionStatus.UNKNOWN.value

    def test_bound_check_executes(self) -> None:
        def my_check(audit: dict) -> CheckResult:
            return CheckResult(
                check_id="01-entity.identity",
                module="01-entity",
                status=ExecutionStatus.PASS,
                evidence=[{"source": "test", "value": True, "confidence": 1.0}],
                reason="Test pass",
            )

        runner = build_runner({"01-entity.identity": my_check})
        output = runner.run({})
        identity_result = output["checks"].get("01-entity.identity")
        assert isinstance(identity_result, dict)
        assert identity_result["status"] == ExecutionStatus.PASS.value

    def test_all_136_specs_created(self) -> None:
        runner = build_runner()
        output = runner.run({})
        assert len(output["checks"]) == 136
