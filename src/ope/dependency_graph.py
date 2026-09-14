"""Executable module dependency graph for OPE.

The graph mirrors ``schemas/dependency-graph-v1.md``.  It is deliberately
kept as the single executable representation of module dependencies so engine
execution, cascade propagation, root-cause traversal, and scoring use the same
relationships.
"""
from __future__ import annotations

MODULE_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "01-entity": (),
    "02-infrastructure": ("01-entity",),
    "03-code": ("02-infrastructure",),
    "04-crawl": ("03-code",),
    "05-index": ("04-crawl",),
    "06-semantics": ("05-index",),
    "07-content": ("06-semantics",),
    "08-media": ("06-semantics",),
    "09-search": ("07-content", "08-media"),
    "10-ai-search": ("07-content", "08-media"),
    "11-authority": ("09-search", "10-ai-search"),
    "12-local": ("09-search", "10-ai-search"),
    "13-ux": ("11-authority", "12-local"),
    "14-accessibility": ("11-authority", "12-local"),
    "15-performance": ("11-authority", "12-local"),
    "16-security": ("11-authority", "12-local"),
    "17-language": ("11-authority", "12-local"),
    "18-analytics": (
        "13-ux",
        "14-accessibility",
        "15-performance",
        "16-security",
        "17-language",
    ),
    "19-conversion": ("18-analytics",),
    "20-continuous-optimization": ("19-conversion",),
}

_MODULE_BY_NUMBER: dict[str, str] = {
    name.split("-", 1)[0]: name for name in MODULE_DEPENDENCIES
}

DEPENDENCIES_BY_NUMBER: dict[str, tuple[str, ...]] = {
    name.split("-", 1)[0]: tuple(dep.split("-", 1)[0] for dep in deps)
    for name, deps in MODULE_DEPENDENCIES.items()
}


def _compute_topological_order(
    graph: dict[str, tuple[str, ...]] = MODULE_DEPENDENCIES,
) -> tuple[str, ...]:
    """Return a deterministic topological order and reject malformed graphs.

    A three-state DFS is used rather than a simple visited set so a back-edge
    is detected as a cycle instead of being silently accepted.  Dependencies
    that are not graph nodes are rejected as dangling edges.
    """
    state: dict[str, int] = {}  # 0/unseen, 1/visiting, 2/complete
    order: list[str] = []

    def visit(module: str) -> None:
        current_state = state.get(module, 0)
        if current_state == 2:
            return
        if current_state == 1:
            raise ValueError(f"dependency graph contains a cycle at {module}")

        if module not in graph:
            raise ValueError(f"dependency graph contains unknown module: {module}")

        state[module] = 1
        for dep in graph[module]:
            if dep not in graph:
                raise ValueError(
                    f"dependency graph contains dangling dependency: {module} -> {dep}"
                )
            visit(dep)
        state[module] = 2
        order.append(module)

    for module in sorted(graph):
        visit(module)
    return tuple(order)


TOPOLOGICAL_ORDER: tuple[str, ...] = _compute_topological_order()
TOPOLOGICAL_ORDER_NUMBERS: tuple[str, ...] = tuple(
    module.split("-", 1)[0] for module in TOPOLOGICAL_ORDER
)


if len(MODULE_DEPENDENCIES) != 20:
    raise ValueError("OPE dependency graph must contain exactly 20 modules")
if len(set(TOPOLOGICAL_ORDER)) != len(MODULE_DEPENDENCIES):
    raise ValueError("OPE dependency graph contains duplicate topological nodes")


def upstream_modules(module: str) -> frozenset[str]:
    """Return all transitive upstream dependencies (full module names)."""
    result: set[str] = set()
    stack = list(MODULE_DEPENDENCIES.get(module, ()))
    while stack:
        current = stack.pop()
        if current not in result:
            result.add(current)
            stack.extend(MODULE_DEPENDENCIES.get(current, ()))
    return frozenset(result)


def downstream_modules(module: str) -> frozenset[str]:
    """Return all transitive downstream dependents (full module names)."""
    result: set[str] = set()
    stack = [
        candidate
        for candidate, deps in MODULE_DEPENDENCIES.items()
        if module in deps
    ]
    while stack:
        current = stack.pop()
        if current not in result:
            result.add(current)
            stack.extend(
                candidate
                for candidate, deps in MODULE_DEPENDENCIES.items()
                if current in deps
            )
    return frozenset(result)


def cascade_blocked(module_statuses: dict[str, str]) -> dict[str, str]:
    """Cascade BLOCKED downstream from upstream FAIL/BLOCKED statuses.

    Existing FAIL status is preserved because it represents direct evidence
    for that module.  Only a module without its own FAIL result is converted
    to BLOCKED when an upstream dependency is FAIL or BLOCKED.  UNKNOWN and
    N/A upstream statuses never cascade.
    """
    result = dict(module_statuses)
    for module_key in TOPOLOGICAL_ORDER_NUMBERS:
        if module_key not in result or result[module_key] == "FAIL":
            continue
        for dep_key in DEPENDENCIES_BY_NUMBER.get(module_key, ()):
            if result.get(dep_key) in ("FAIL", "BLOCKED"):
                result[module_key] = "BLOCKED"
                break
    return result


def find_root_causes(module_statuses: dict[str, str]) -> dict[str, list[str]]:
    """Find upstream FAIL modules for every BLOCKED module.

    BLOCKED modules are traversal intermediaries, never root causes.  Results
    are deterministically sorted by module number.
    """
    root_causes: dict[str, list[str]] = {}
    for module_key in TOPOLOGICAL_ORDER_NUMBERS:
        if module_statuses.get(module_key) != "BLOCKED":
            continue
        full_name = _MODULE_BY_NUMBER.get(module_key)
        if full_name is None:
            continue
        causes = {
            upstream_name.split("-", 1)[0]
            for upstream_name in upstream_modules(full_name)
            if module_statuses.get(upstream_name.split("-", 1)[0]) == "FAIL"
        }
        if causes:
            root_causes[module_key] = sorted(causes)
    return root_causes
