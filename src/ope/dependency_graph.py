"""Module-level dependency graph derived from schemas/dependency-graph-v1.md.

Entity -> Infrastructure -> Code -> Crawl -> Index -> Semantics ->
Content/Media -> Search/AI -> Authority/Local ->
UX/Accessibility/Performance/Security/Language ->
Analytics -> Conversion -> Continuous Optimization.

Parallel branches (Content/Media, Search/AI, etc.) share the same upstream
and feed the same downstream tier.  The graph is acyclic by construction.
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
    "18-analytics": ("13-ux", "14-accessibility", "15-performance", "16-security", "17-language"),
    "19-conversion": ("18-analytics",),
    "20-continuous-optimization": ("19-conversion",),
}

_MODULE_BY_NUMBER: dict[str, str] = {
    name.split("-")[0]: name for name in MODULE_DEPENDENCIES
}

DEPENDENCIES_BY_NUMBER: dict[str, tuple[str, ...]] = {
    name.split("-")[0]: tuple(dep.split("-")[0] for dep in deps)
    for name, deps in MODULE_DEPENDENCIES.items()
}


def _compute_topological_order() -> tuple[str, ...]:
    visited: set[str] = set()
    order: list[str] = []

    def visit(module: str) -> None:
        if module in visited:
            return
        visited.add(module)
        for dep in MODULE_DEPENDENCIES.get(module, ()):
            visit(dep)
        order.append(module)

    for module in sorted(MODULE_DEPENDENCIES):
        visit(module)
    return tuple(order)


TOPOLOGICAL_ORDER: tuple[str, ...] = _compute_topological_order()

TOPOLOGICAL_ORDER_NUMBERS: tuple[str, ...] = tuple(
    m.split("-")[0] for m in TOPOLOGICAL_ORDER
)


def upstream_modules(module: str) -> frozenset[str]:
    """All transitive upstream dependencies (full module names)."""
    result: set[str] = set()
    stack = list(MODULE_DEPENDENCIES.get(module, ()))
    while stack:
        current = stack.pop()
        if current not in result:
            result.add(current)
            stack.extend(MODULE_DEPENDENCIES.get(current, ()))
    return frozenset(result)


def downstream_modules(module: str) -> frozenset[str]:
    """All transitive downstream dependents (full module names)."""
    result: set[str] = set()
    stack = [m for m, deps in MODULE_DEPENDENCIES.items() if module in deps]
    while stack:
        current = stack.pop()
        if current not in result:
            result.add(current)
            stack.extend(
                m for m, deps in MODULE_DEPENDENCIES.items() if current in deps
            )
    return frozenset(result)


def cascade_blocked(module_statuses: dict[str, str]) -> dict[str, str]:
    """Cascade BLOCKED downstream from FAIL modules.

    Accepts and returns module-number keyed statuses (e.g. ``"02"`` -> ``"FAIL"``).
    Iterates in topological order so BLOCKED propagates transitively:
    if A fails, B is blocked, and C (which depends on B) is also blocked.

    Only FAIL and BLOCKED upstream statuses trigger cascading.  UNKNOWN
    upstream does not block downstream — absent evidence is not a failure.
    """
    result = dict(module_statuses)
    for module_key in TOPOLOGICAL_ORDER_NUMBERS:
        if module_key not in result:
            continue
        for dep_key in DEPENDENCIES_BY_NUMBER.get(module_key, ()):
            if result.get(dep_key) in ("FAIL", "BLOCKED"):
                result[module_key] = "BLOCKED"
                break
    return result


def find_root_causes(module_statuses: dict[str, str]) -> dict[str, list[str]]:
    """For each BLOCKED module, find the upstream FAIL modules that caused it.

    Accepts module-number keyed statuses.  Returns module-number keyed
    root-cause lists.  A root cause is a module with FAIL status — BLOCKED
    modules are intermediaries, not root causes.
    """
    root_causes: dict[str, list[str]] = {}
    for module_key in TOPOLOGICAL_ORDER_NUMBERS:
        if module_statuses.get(module_key) != "BLOCKED":
            continue
        causes: list[str] = []
        full_name = _MODULE_BY_NUMBER.get(module_key, "")
        if not full_name:
            continue
        for upstream_name in upstream_modules(full_name):
            upstream_key = upstream_name.split("-")[0]
            if module_statuses.get(upstream_key) == "FAIL":
                causes.append(upstream_key)
        if causes:
            root_causes[module_key] = sorted(causes)
    return root_causes
