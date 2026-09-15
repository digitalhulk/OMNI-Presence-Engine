"""Tests for the module-level dependency graph — structure, cascade, root-cause traversal."""
from __future__ import annotations

import pytest

from ope.dependency_graph import (
    DEPENDENCIES_BY_NUMBER,
    MODULE_DEPENDENCIES,
    TOPOLOGICAL_ORDER,
    TOPOLOGICAL_ORDER_NUMBERS,
    GraphValidationError,
    _compute_topological_order,
    cascade_blocked,
    downstream_modules,
    find_root_causes,
    upstream_modules,
    validate_graph,
)


class TestGraphStructure:
    def test_20_modules(self) -> None:
        assert len(MODULE_DEPENDENCIES) == 20

    def test_entity_has_no_upstream(self) -> None:
        assert MODULE_DEPENDENCIES["01-entity"] == ()

    def test_continuous_optimization_is_terminal(self) -> None:
        assert not downstream_modules("20-continuous-optimization")

    def test_graph_is_acyclic(self) -> None:
        assert len(TOPOLOGICAL_ORDER) == 20

    def test_topological_order_has_all_modules(self) -> None:
        assert set(TOPOLOGICAL_ORDER) == set(MODULE_DEPENDENCIES)

    def test_topological_order_respects_edges(self) -> None:
        indices = {m: i for i, m in enumerate(TOPOLOGICAL_ORDER)}
        for module, deps in MODULE_DEPENDENCIES.items():
            for dep in deps:
                assert indices[dep] < indices[module], (
                    f"{dep} must appear before {module}"
                )

    def test_number_mapping_covers_all(self) -> None:
        assert len(DEPENDENCIES_BY_NUMBER) == 20
        assert len(TOPOLOGICAL_ORDER_NUMBERS) == 20


class TestParallelBranches:
    def test_content_and_media_share_semantics_upstream(self) -> None:
        assert MODULE_DEPENDENCIES["07-content"] == ("06-semantics",)
        assert MODULE_DEPENDENCIES["08-media"] == ("06-semantics",)

    def test_search_and_ai_search_share_upstream(self) -> None:
        assert "07-content" in MODULE_DEPENDENCIES["09-search"]
        assert "08-media" in MODULE_DEPENDENCIES["09-search"]
        assert "07-content" in MODULE_DEPENDENCIES["10-ai-search"]
        assert "08-media" in MODULE_DEPENDENCIES["10-ai-search"]

    def test_authority_and_local_share_upstream(self) -> None:
        assert "09-search" in MODULE_DEPENDENCIES["11-authority"]
        assert "10-ai-search" in MODULE_DEPENDENCIES["11-authority"]
        assert "09-search" in MODULE_DEPENDENCIES["12-local"]
        assert "10-ai-search" in MODULE_DEPENDENCIES["12-local"]

    def test_ux_tier_shares_upstream(self) -> None:
        for m in ("13-ux", "14-accessibility", "15-performance", "16-security", "17-language"):
            assert "11-authority" in MODULE_DEPENDENCIES[m]
            assert "12-local" in MODULE_DEPENDENCIES[m]

    def test_analytics_depends_on_ux_tier(self) -> None:
        deps = MODULE_DEPENDENCIES["18-analytics"]
        for m in ("13-ux", "14-accessibility", "15-performance", "16-security", "17-language"):
            assert m in deps


class TestUpstreamModules:
    def test_entity_has_no_upstream(self) -> None:
        assert upstream_modules("01-entity") == frozenset()

    def test_infrastructure_has_entity_upstream(self) -> None:
        assert upstream_modules("02-infrastructure") == frozenset({"01-entity"})

    def test_transitive_upstream(self) -> None:
        ups = upstream_modules("04-crawl")
        assert "01-entity" in ups
        assert "02-infrastructure" in ups
        assert "03-code" in ups

    def test_continuous_optimization_has_all_upstream(self) -> None:
        ups = upstream_modules("20-continuous-optimization")
        assert len(ups) == 19


class TestDownstreamModules:
    def test_entity_has_all_downstream(self) -> None:
        down = downstream_modules("01-entity")
        assert len(down) == 19

    def test_continuous_optimization_has_no_downstream(self) -> None:
        assert downstream_modules("20-continuous-optimization") == frozenset()

    def test_semantics_feeds_content_and_media(self) -> None:
        down = downstream_modules("06-semantics")
        assert "07-content" in down
        assert "08-media" in down

    def test_parallel_branches_are_not_mutual_downstream(self) -> None:
        assert "08-media" not in downstream_modules("07-content")
        assert "07-content" not in downstream_modules("08-media")


class TestCascadeBlocked:
    def test_no_fail_no_cascade(self) -> None:
        statuses = {f"{i:02d}": "UNKNOWN" for i in range(1, 21)}
        assert cascade_blocked(statuses) == statuses

    def test_entity_fail_cascades_all(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["01"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        assert cascaded["01"] == "FAIL"
        for i in range(2, 21):
            assert cascaded[f"{i:02d}"] == "BLOCKED", f"module {i:02d} not blocked"

    def test_unknown_upstream_does_not_cascade(self) -> None:
        statuses = {"01": "UNKNOWN", "02": "PASS"}
        cascaded = cascade_blocked(statuses)
        assert cascaded["02"] == "PASS"

    def test_fail_in_middle_cascades_downstream_only(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["06"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        for i in range(1, 6):
            assert cascaded[f"{i:02d}"] == "PASS", f"module {i:02d} should stay PASS"
        assert cascaded["06"] == "FAIL"
        for i in range(7, 21):
            assert cascaded[f"{i:02d}"] == "BLOCKED", f"module {i:02d} not blocked"

    def test_parallel_branch_fail_blocks_downstream(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["07"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        assert cascaded["08"] == "PASS"
        assert cascaded["09"] == "BLOCKED"
        assert cascaded["10"] == "BLOCKED"

    def test_both_parallel_branches_fail(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["07"] = "FAIL"
        statuses["08"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        assert cascaded["09"] == "BLOCKED"
        assert cascaded["10"] == "BLOCKED"

    def test_cascade_only_existing_keys(self) -> None:
        statuses = {"01": "FAIL", "02": "PASS"}
        cascaded = cascade_blocked(statuses)
        assert cascaded == {"01": "FAIL", "02": "BLOCKED"}
        assert "03" not in cascaded

    def test_downstream_direct_fail_is_preserved(self) -> None:
        # A module carrying its own FAIL evidence keeps FAIL — BLOCKED is a
        # derived state and never overwrites direct evidence.
        statuses = {"01": "FAIL", "02": "FAIL"}
        cascaded = cascade_blocked(statuses)
        assert cascaded["01"] == "FAIL"
        assert cascaded["02"] == "FAIL"

    def test_na_upstream_does_not_cascade(self) -> None:
        statuses = {"01": "N/A", "02": "PASS"}
        cascaded = cascade_blocked(statuses)
        assert cascaded["02"] == "PASS"


class TestFindRootCauses:
    def test_no_blocked_no_root_causes(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        assert find_root_causes(statuses) == {}

    def test_single_root_cause(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["02"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        root_causes = find_root_causes(cascaded)
        for i in range(3, 21):
            assert root_causes[f"{i:02d}"] == ["02"], f"module {i:02d}"

    def test_multiple_root_causes(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["07"] = "FAIL"
        statuses["08"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        root_causes = find_root_causes(cascaded)
        assert sorted(root_causes["09"]) == ["07", "08"]
        assert sorted(root_causes["10"]) == ["07", "08"]

    def test_transitive_root_cause_skips_blocked(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["01"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        root_causes = find_root_causes(cascaded)
        assert root_causes["02"] == ["01"]
        assert root_causes["03"] == ["01"]
        assert root_causes["20"] == ["01"]

    def test_intermediate_fail_and_root_fail(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["01"] = "FAIL"
        statuses["03"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        root_causes = find_root_causes(cascaded)
        # 02 is blocked purely by 01.
        assert root_causes["02"] == ["01"]
        # 03 has its own FAIL evidence — preserved, never derived-BLOCKED.
        assert cascaded["03"] == "FAIL"
        assert "03" not in root_causes
        # 04 sits above both failures; both are visible as root causes.
        assert root_causes["04"] == ["01", "03"]


class TestAcceptanceTest:
    """The definitive acceptance test from the task card:
    If Infrastructure fails, can OPE deterministically trace the resulting
    downstream BLOCKED states back through the real declared dependency
    graph to Infrastructure as the root cause — without using module numbers,
    LLM inference, or fabricated evidence?
    """

    def test_infrastructure_fail_traces_to_root_cause(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["02"] = "FAIL"

        cascaded = cascade_blocked(statuses)
        root_causes = find_root_causes(cascaded)

        assert cascaded["01"] == "PASS"
        assert cascaded["02"] == "FAIL"

        for i in range(3, 21):
            key = f"{i:02d}"
            assert cascaded[key] == "BLOCKED", f"{key} should be BLOCKED"
            assert root_causes[key] == ["02"], f"{key} root cause should be ['02']"

    def test_entity_and_infrastructure_both_fail(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["01"] = "FAIL"
        statuses["02"] = "FAIL"

        cascaded = cascade_blocked(statuses)
        root_causes = find_root_causes(cascaded)

        # Both modules hold direct FAIL evidence — neither is masked to BLOCKED.
        assert cascaded["01"] == "FAIL"
        assert cascaded["02"] == "FAIL"
        assert "02" not in root_causes  # has its own evidence, not derived
        for i in range(3, 21):
            key = f"{i:02d}"
            assert cascaded[key] == "BLOCKED"
            # Both upstream failures are transitively visible as root causes.
            assert root_causes[key] == ["01", "02"]


class TestExecutionOrderIndependence:
    def test_cascade_is_deterministic(self) -> None:
        statuses_a = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses_a["05"] = "FAIL"
        statuses_b = dict(statuses_a)

        assert cascade_blocked(statuses_a) == cascade_blocked(statuses_b)

    def test_root_causes_are_deterministic(self) -> None:
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["07"] = "FAIL"
        statuses["08"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        rc1 = find_root_causes(cascaded)
        rc2 = find_root_causes(cascaded)
        assert rc1 == rc2

    def test_topological_order_is_deterministic(self) -> None:
        assert _compute_topological_order() == _compute_topological_order()


class TestGraphValidation:
    """The validator is a reusable mechanism, tested on synthetic graphs — not
    only on the static 20-module graph (which validate_graph guards at import)."""

    def test_valid_dag_passes(self) -> None:
        validate_graph({"a": (), "b": ("a",), "c": ("a", "b")})  # no raise

    def test_the_declared_module_graph_is_valid(self) -> None:
        validate_graph(MODULE_DEPENDENCIES)  # no raise

    def test_two_node_cycle_is_rejected(self) -> None:
        with pytest.raises(GraphValidationError, match="cycle"):
            validate_graph({"a": ("b",), "b": ("a",)})

    def test_three_node_cycle_is_rejected(self) -> None:
        with pytest.raises(GraphValidationError, match="cycle"):
            validate_graph({"a": ("b",), "b": ("c",), "c": ("a",)})

    def test_self_cycle_is_rejected(self) -> None:
        with pytest.raises(GraphValidationError, match="cycle"):
            validate_graph({"a": ("a",)})

    def test_dangling_dependency_is_rejected(self) -> None:
        with pytest.raises(GraphValidationError, match="dangling"):
            validate_graph({"a": ("missing",), "b": ()})

    def test_graph_validation_error_is_a_value_error(self) -> None:
        assert issubclass(GraphValidationError, ValueError)

    def test_cycle_is_rejected_by_topological_order(self) -> None:
        with pytest.raises(GraphValidationError, match="cycle"):
            _compute_topological_order({"a": ("b",), "b": ("a",)})

    def test_dangling_is_rejected_by_topological_order(self) -> None:
        with pytest.raises(GraphValidationError, match="dangling"):
            _compute_topological_order({"a": ("ghost",)})

    def test_diamond_graph_orders_deterministically(self) -> None:
        graph = {"root": (), "left": ("root",), "right": ("root",), "leaf": ("left", "right")}
        order = _compute_topological_order(graph)
        assert order == _compute_topological_order(graph)
        assert order.index("root") < order.index("left") < order.index("leaf")
        assert order.index("root") < order.index("right") < order.index("leaf")

    def test_long_chain_does_not_overflow(self) -> None:
        # A deep chain would blow a recursive validator's stack; the iterative
        # validator handles it. 5000 >> Python's default recursion limit.
        graph = {"n0": ()}
        graph.update({f"n{i}": (f"n{i - 1}",) for i in range(1, 5000)})
        validate_graph(graph)  # no raise, no RecursionError

    def test_deep_cycle_is_still_detected(self) -> None:
        graph = {"n0": ("n4999",)}
        graph.update({f"n{i}": (f"n{i - 1}",) for i in range(1, 5000)})
        with pytest.raises(GraphValidationError, match="cycle"):
            validate_graph(graph)

    def test_disconnected_graph_is_valid_and_fully_ordered(self) -> None:
        # Two independent components with no edge between them.
        graph = {"a": (), "b": ("a",), "x": (), "y": ("x",)}
        validate_graph(graph)  # no raise
        order = _compute_topological_order(graph)
        assert set(order) == set(graph)
        assert order.index("a") < order.index("b")
        assert order.index("x") < order.index("y")
        assert _compute_topological_order(graph) == order  # deterministic


class TestEvidenceSafeCascade:
    """BLOCKED is a derived dependency state and never replaces direct evidence."""

    def test_direct_fail_survives_upstream_fail(self) -> None:
        statuses = {"01": "FAIL", "02": "FAIL", "03": "PASS"}
        cascaded = cascade_blocked(statuses)
        assert cascaded["02"] == "FAIL"   # own evidence preserved
        assert cascaded["03"] == "BLOCKED"  # derived from upstream FAIL

    def test_direct_na_survives_upstream_fail(self) -> None:
        # 03 depends on 02; 02 fails but 03 is N/A (does not apply) → stays N/A.
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["02"] = "FAIL"
        statuses["03"] = "N/A"
        cascaded = cascade_blocked(statuses)
        assert cascaded["03"] == "N/A"

    def test_na_does_not_conduct_the_block(self) -> None:
        # An N/A module neither becomes BLOCKED nor propagates one downstream
        # through the single path it shields; parallel paths still conduct.
        statuses = {"01": "N/A", "02": "PASS"}
        assert cascade_blocked(statuses) == {"01": "N/A", "02": "PASS"}

    def test_pass_and_unknown_are_overwritable(self) -> None:
        statuses = {"01": "FAIL", "02": "PASS", "03": "UNKNOWN"}
        cascaded = cascade_blocked(statuses)
        assert cascaded["02"] == "BLOCKED"
        assert cascaded["03"] == "BLOCKED"

    def test_cascade_does_not_fabricate_root_cause_without_fail(self) -> None:
        statuses = {"06": "BLOCKED", "07": "BLOCKED", "08": "PASS"}
        assert find_root_causes(statuses) == {}

    def test_intermediate_fail_and_root_both_reported(self) -> None:
        # 02 FAIL, 03 FAIL (own evidence, preserved), 04 BLOCKED → both roots.
        statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
        statuses["02"] = "FAIL"
        statuses["03"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        assert cascaded["03"] == "FAIL"
        roots = find_root_causes(cascaded)
        assert "03" not in roots
        assert roots["04"] == ["02", "03"]


class TestScoringGoldenScenarios:
    """The nine required end-to-end cascade/root-cause golden scenarios."""

    def _all(self, status: str) -> dict[str, str]:
        return {f"{i:02d}": status for i in range(1, 21)}

    def test_1_all_pass(self) -> None:
        statuses = self._all("PASS")
        assert cascade_blocked(statuses) == statuses
        assert find_root_causes(cascade_blocked(statuses)) == {}

    def test_2_all_unknown(self) -> None:
        statuses = self._all("UNKNOWN")
        assert cascade_blocked(statuses) == statuses
        assert find_root_causes(cascade_blocked(statuses)) == {}

    def test_3_all_na(self) -> None:
        statuses = self._all("N/A")
        assert cascade_blocked(statuses) == statuses
        assert find_root_causes(cascade_blocked(statuses)) == {}

    def test_4_one_fail(self) -> None:
        statuses = self._all("PASS")
        statuses["02"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        assert cascaded["02"] == "FAIL"
        assert all(cascaded[f"{i:02d}"] == "BLOCKED" for i in range(3, 21))
        assert cascaded["01"] == "PASS"

    def test_5_upstream_fail_downstream_blocked(self) -> None:
        statuses = self._all("PASS")
        statuses["02"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        roots = find_root_causes(cascaded)
        assert roots["10"] == ["02"]

    def test_6_upstream_fail_downstream_direct_fail(self) -> None:
        statuses = self._all("PASS")
        statuses["02"] = "FAIL"
        statuses["10"] = "FAIL"  # own evidence
        cascaded = cascade_blocked(statuses)
        assert cascaded["10"] == "FAIL"
        assert "10" not in find_root_causes(cascaded)

    def test_7_parallel_branch_failure(self) -> None:
        statuses = self._all("PASS")
        statuses["07"] = "FAIL"
        cascaded = cascade_blocked(statuses)
        assert cascaded["08"] == "PASS"   # sibling branch unaffected
        assert cascaded["09"] == "BLOCKED"
        assert cascaded["10"] == "BLOCKED"

    def test_8_multiple_root_failures(self) -> None:
        statuses = self._all("PASS")
        statuses["07"] = "FAIL"
        statuses["08"] = "FAIL"
        roots = find_root_causes(cascade_blocked(statuses))
        assert roots["09"] == ["07", "08"]
        assert roots["20"] == ["07", "08"]

    def test_9_mixed_states(self) -> None:
        statuses = self._all("PASS")
        statuses["02"] = "FAIL"     # root failure
        statuses["05"] = "N/A"      # inapplicable, must survive
        statuses["06"] = "UNKNOWN"  # overwritable
        cascaded = cascade_blocked(statuses)
        assert cascaded["01"] == "PASS"
        assert cascaded["02"] == "FAIL"
        assert cascaded["05"] == "N/A"
        assert cascaded["06"] == "BLOCKED"
        assert find_root_causes(cascaded)["06"] == ["02"]
