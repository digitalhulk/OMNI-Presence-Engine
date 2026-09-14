"""Regression tests for dependency-graph hardening."""
from __future__ import annotations

import pytest

from ope.dependency_graph import (
    MODULE_DEPENDENCIES,
    _compute_topological_order,
    cascade_blocked,
    find_root_causes,
)


class TestGraphValidation:
    def test_cycle_is_rejected(self) -> None:
        graph = {"a": ("b",), "b": ("a",)}
        with pytest.raises(ValueError, match="cycle"):
            _compute_topological_order(graph)

    def test_dangling_dependency_is_rejected(self) -> None:
        graph = {"a": ("missing",), "b": ()}
        with pytest.raises(ValueError, match="dangling dependency"):
            _compute_topological_order(graph)

    def test_valid_branch_graph_is_deterministic(self) -> None:
        graph = {
            "root": (),
            "left": ("root",),
            "right": ("root",),
            "leaf": ("left", "right"),
        }
        first = _compute_topological_order(graph)
        second = _compute_topological_order(graph)
        assert first == second
        assert first.index("root") < first.index("leaf")
        assert first.index("left") < first.index("leaf")
        assert first.index("right") < first.index("leaf")

    def test_declared_graph_edges_are_all_internal(self) -> None:
        assert all(
            dependency in MODULE_DEPENDENCIES
            for dependencies in MODULE_DEPENDENCIES.values()
            for dependency in dependencies
        )


class TestCascadeEvidencePreservation:
    def test_direct_fail_is_not_overwritten_by_upstream_fail(self) -> None:
        statuses = {"01": "FAIL", "02": "FAIL", "03": "PASS"}
        cascaded = cascade_blocked(statuses)
        assert cascaded["01"] == "FAIL"
        assert cascaded["02"] == "FAIL"
        assert cascaded["03"] == "BLOCKED"

    def test_unknown_and_na_never_create_blocked(self) -> None:
        statuses = {
            "01": "UNKNOWN",
            "02": "N/A",
            "03": "PASS",
            "04": "PASS",
        }
        cascaded = cascade_blocked(statuses)
        assert cascaded == statuses

    def test_multiple_fail_roots_are_retained(self) -> None:
        statuses = {f"{number:02d}": "PASS" for number in range(1, 21)}
        statuses["07"] = "FAIL"
        statuses["08"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        roots = find_root_causes(cascaded)
        assert roots["09"] == ["07", "08"]
        assert roots["18"] == ["07", "08"]
        assert roots["20"] == ["07", "08"]

    def test_blocked_without_a_fail_root_has_no_fabricated_cause(self) -> None:
        statuses = {"06": "BLOCKED", "07": "BLOCKED", "08": "PASS"}
        assert find_root_causes(statuses) == {}
