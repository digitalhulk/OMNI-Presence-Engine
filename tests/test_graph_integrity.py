"""Machine-checkable dependency-graph integrity contract.

schemas/dependency-graph-v1.md declares MODULE_DEPENDENCIES the single
executable source of module dependencies. This test freezes the full edge set
and the spec's stated structure (linear spine + parallel branches), so any edge
that silently disappears or changes in the future fails here, and it verifies
the graph is consumed by the runtime (validation, cascade, root-cause).
"""
from __future__ import annotations

from pathlib import Path

from ope.dependency_graph import (
    MODULE_DEPENDENCIES,
    cascade_blocked,
    find_root_causes,
    validate_graph,
)

# Frozen contract — mirrors schemas/dependency-graph-v1.md exactly.
# Entity -> Infrastructure -> Code -> Crawl -> Index -> Semantics -> then the
# parallel branches (Content/Media, Search/AI, Authority/Local, UX tier) ->
# Analytics -> Conversion -> Continuous Optimization.
EXPECTED_EDGES = {
    "01-entity": [],
    "02-infrastructure": ["01-entity"],
    "03-code": ["02-infrastructure"],
    "04-crawl": ["03-code"],
    "05-index": ["04-crawl"],
    "06-semantics": ["05-index"],
    "07-content": ["06-semantics"],
    "08-media": ["06-semantics"],
    "09-search": ["07-content", "08-media"],
    "10-ai-search": ["07-content", "08-media"],
    "11-authority": ["09-search", "10-ai-search"],
    "12-local": ["09-search", "10-ai-search"],
    "13-ux": ["11-authority", "12-local"],
    "14-accessibility": ["11-authority", "12-local"],
    "15-performance": ["11-authority", "12-local"],
    "16-security": ["11-authority", "12-local"],
    "17-language": ["11-authority", "12-local"],
    "18-analytics": ["13-ux", "14-accessibility", "15-performance", "16-security", "17-language"],
    "19-conversion": ["18-analytics"],
    "20-continuous-optimization": ["19-conversion"],
}


def test_edge_set_is_frozen_to_the_spec():
    # Compare as sets per node so declaration order never matters, but no edge
    # may appear or disappear without updating this contract deliberately.
    assert set(MODULE_DEPENDENCIES) == set(EXPECTED_EDGES)
    for node, deps in EXPECTED_EDGES.items():
        assert set(MODULE_DEPENDENCIES[node]) == set(deps), f"edges changed for {node}"


def test_all_twenty_modules_present():
    assert len(MODULE_DEPENDENCIES) == 20


def test_graph_validates_and_is_acyclic():
    # validate_graph raises on a dangling edge or a cycle; it must accept the
    # real graph.
    validate_graph(MODULE_DEPENDENCIES)


def test_every_edge_targets_a_declared_module():
    for node, deps in MODULE_DEPENDENCIES.items():
        for dep in deps:
            assert dep in MODULE_DEPENDENCIES, f"{node} depends on undeclared {dep}"


def test_parallel_branches_share_upstream_and_downstream():
    # The spec's parallel branches: each pair/tier shares the same upstream.
    assert MODULE_DEPENDENCIES["07-content"] == MODULE_DEPENDENCIES["08-media"]
    assert MODULE_DEPENDENCIES["09-search"] == MODULE_DEPENDENCIES["10-ai-search"]
    assert MODULE_DEPENDENCIES["11-authority"] == MODULE_DEPENDENCIES["12-local"]
    for m in ("13-ux", "14-accessibility", "15-performance", "16-security", "17-language"):
        assert set(MODULE_DEPENDENCIES[m]) == {"11-authority", "12-local"}
    # ...and the UX tier converges into analytics.
    assert set(MODULE_DEPENDENCIES["18-analytics"]) == {"13-ux", "14-accessibility", "15-performance", "16-security", "17-language"}


def test_runtime_consumes_the_graph_for_cascade_and_root_cause():
    # A FAIL at the foundation must block a transitive downstream module through
    # the real edges, and root-cause must trace back to that FAIL. cascade_blocked
    # and find_root_causes are module-number keyed ("02" -> "FAIL").
    statuses = {f"{i:02d}": "PASS" for i in range(1, 21)}
    statuses["02"] = "FAIL"
    cascaded = cascade_blocked(statuses)
    assert cascaded["02"] == "FAIL"        # own evidence preserved
    assert cascaded["03"] == "BLOCKED"     # transitive downstream blocked via the real edges
    assert cascaded["20"] == "BLOCKED"
    roots = find_root_causes(cascaded)
    assert "02" in roots["03"]


def test_spec_file_names_the_executable_source():
    spec = (Path(__file__).resolve().parents[1] / "schemas" / "dependency-graph-v1.md").read_text(encoding="utf-8")
    assert "MODULE_DEPENDENCIES" in spec
    assert "parallel branches" in spec.lower()


def test_canonical_dependency_model_is_module_level_only():
    """The canonical dependency model is MODULE-level (MODULE_DEPENDENCIES).

    ModuleRunner supports a generic check-level `depends_on`, but the registry
    intentionally declares none — schemas/dependency-graph-v1.md states cascade
    derives *module* status only. This contract test prevents a second,
    check-level dependency graph from being introduced by accident: if a future
    check declares check-level deps, this fails and forces an explicit decision.
    """
    from ope.registry import CHECKS
    with_check_deps = [c.id for c in CHECKS if getattr(c, "depends_on", ())]
    assert with_check_deps == [], (
        "check-level depends_on is declared on "
        f"{with_check_deps}; the canonical dependency model is module-level "
        "(MODULE_DEPENDENCIES). Introducing check-level edges needs a deliberate "
        "spec + engine decision, not an accidental second graph."
    )
