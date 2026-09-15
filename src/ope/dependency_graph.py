"""Executable module dependency graph for OPE.

The graph mirrors ``schemas/dependency-graph-v1.md`` and is the single
executable representation of module dependencies: engine execution, cascade
propagation, root-cause traversal, and scoring all derive their ordering and
relationships from ``MODULE_DEPENDENCIES`` here — never from a second
hardcoded assumption such as "module N always depends on module N-1".

Contract:

- Graph construction rejects malformed topology (dangling edges, cycles)
  rather than silently accepting it (``validate_graph``).
- ``cascade_blocked`` derives a ``BLOCKED`` module status downstream of an
  upstream ``FAIL``/``BLOCKED``, but never overwrites a module's own direct
  evidence: a module that is itself ``FAIL`` stays ``FAIL``, and a module
  that is ``N/A`` (the check does not apply) stays ``N/A``.  ``BLOCKED`` is a
  *derived* dependency state, never a replacement for direct evidence.
- ``find_root_causes`` reports only upstream modules that actually hold
  ``FAIL`` evidence; ``BLOCKED`` intermediaries are never fabricated as root
  causes, and no cause is invented where no ``FAIL`` exists.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

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

# Direct evidence-backed module states are never overwritten by a derived
# BLOCKED: FAIL is an observed failure, N/A is an observed non-applicability.
_DIRECT_EVIDENCE_STATES = frozenset({"FAIL", "N/A"})
# States that propagate a block to dependents.  Absent (UNKNOWN) or
# inapplicable (N/A) upstream evidence is not a failure and does not cascade.
_CASCADING_STATES = frozenset({"FAIL", "BLOCKED"})

_MODULE_BY_NUMBER: dict[str, str] = {
    name.split("-", 1)[0]: name for name in MODULE_DEPENDENCIES
}

DEPENDENCIES_BY_NUMBER: dict[str, tuple[str, ...]] = {
    name.split("-", 1)[0]: tuple(dep.split("-", 1)[0] for dep in deps)
    for name, deps in MODULE_DEPENDENCIES.items()
}


class GraphValidationError(ValueError):
    """Raised when a dependency graph is malformed (dangling edge or cycle)."""


def validate_graph(graph: Mapping[str, Sequence[str]]) -> None:
    """Validate an arbitrary dependency graph, raising on malformed topology.

    Two failure modes are rejected explicitly rather than silently accepted:

    - **Dangling edge**: a dependency that is not itself a declared node.
    - **Cycle**: detected by an explicit-stack three-state DFS
      (UNSEEN → VISITING → COMPLETE).  A single "visited" set is insufficient
      because it cannot distinguish a node still on the current DFS path
      (a back-edge / cycle) from one already fully explored on another path.

    The traversal is iterative so validating a large or adversarial graph
    cannot exhaust the interpreter's recursion stack.  Reusable for any
    dependency graph, not only the module graph.
    """
    declared = set(graph)
    for node, deps in graph.items():
        for dep in deps:
            if dep not in declared:
                raise GraphValidationError(
                    f"dangling dependency: {node!r} depends on undeclared module {dep!r}"
                )

    unseen, visiting, complete = 0, 1, 2
    state: dict[str, int] = dict.fromkeys(graph, unseen)
    for start in graph:
        if state[start] != unseen:
            continue
        # Each stack frame carries the node and a forward iterator over its
        # dependencies, so exploration resumes where it paused.
        stack: list[tuple[str, Iterator[str]]] = [(start, iter(graph[start]))]
        state[start] = visiting
        while stack:
            node, deps_iter = stack[-1]
            advanced = False
            for dep in deps_iter:
                dep_state = state[dep]
                if dep_state == visiting:
                    raise GraphValidationError(
                        f"cycle detected: edge {node!r} -> {dep!r} closes a dependency loop"
                    )
                if dep_state == unseen:
                    state[dep] = visiting
                    stack.append((dep, iter(graph[dep])))
                    advanced = True
                    break
            if not advanced:
                state[node] = complete
                stack.pop()


def _compute_topological_order(
    graph: Mapping[str, Sequence[str]] = MODULE_DEPENDENCIES,
) -> tuple[str, ...]:
    """Deterministic topological order over a validated graph (Kahn's algorithm).

    Dependencies name prerequisites, so a module is emitted only once every
    module it depends on has been emitted.  Ready modules are emitted in
    sorted order for a stable, reproducible layering.  Malformed graphs are
    rejected up front by :func:`validate_graph`.
    """
    validate_graph(graph)
    pending: dict[str, set[str]] = {node: set(deps) for node, deps in graph.items()}
    order: list[str] = []
    while pending:
        ready = sorted(node for node, deps in pending.items() if not deps)
        if not ready:  # pragma: no cover - validate_graph already rejects cycles
            raise GraphValidationError("cycle detected: no dependency-free module remains")
        for node in ready:
            order.append(node)
            del pending[node]
        for deps in pending.values():
            deps.difference_update(ready)
    return tuple(order)


TOPOLOGICAL_ORDER: tuple[str, ...] = _compute_topological_order()
TOPOLOGICAL_ORDER_NUMBERS: tuple[str, ...] = tuple(
    module.split("-", 1)[0] for module in TOPOLOGICAL_ORDER
)

if len(MODULE_DEPENDENCIES) != 20:
    raise GraphValidationError("OPE dependency graph must contain exactly 20 modules")
if len(set(TOPOLOGICAL_ORDER)) != len(MODULE_DEPENDENCIES):
    raise GraphValidationError("OPE dependency graph produced a non-bijective topological order")


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
    """Derive downstream ``BLOCKED`` status from upstream failure — evidence-safe.

    Accepts and returns module-number keyed statuses (e.g. ``"02" -> "FAIL"``).

    A module is marked ``BLOCKED`` when any of its **transitive** upstream
    dependencies is ``FAIL`` or ``BLOCKED`` — unless it holds its own direct
    evidence.  The transitive rule is deliberate: an inapplicable (``N/A``)
    intermediate layer does not repair a broken foundation, and a module that
    still transitively depends on a failed module cannot be trusted, so the
    upstream failure remains visible rather than being silently shielded.

    ``BLOCKED`` is a *derived* dependency state and never replaces direct
    evidence:

    - A module whose own status is ``FAIL`` or ``N/A`` is left untouched — a
      real failure stays a failure, and an inapplicable module stays ``N/A``.
    - Only ``PASS``/``UNKNOWN`` (non-evidence) modules are converted to
      ``BLOCKED``.
    - ``UNKNOWN`` and ``N/A`` upstream states never cause a block: absent or
      inapplicable evidence is not a failure.

    Iterating in topological order means every upstream result is finalized
    before a module is evaluated.  Only module statuses are derived here;
    check-level evidence is never touched, so a check never becomes ``FAIL``
    because an upstream module did.
    """
    result = dict(module_statuses)
    for module_key in TOPOLOGICAL_ORDER_NUMBERS:
        if module_key not in result:
            continue
        if result[module_key] in _DIRECT_EVIDENCE_STATES:
            continue
        full_name = _MODULE_BY_NUMBER.get(module_key)
        if full_name is None:
            continue
        if any(
            result.get(upstream_name.split("-", 1)[0]) in _CASCADING_STATES
            for upstream_name in upstream_modules(full_name)
        ):
            result[module_key] = "BLOCKED"
    return result


def find_root_causes(module_statuses: dict[str, str]) -> dict[str, list[str]]:
    """Trace every ``BLOCKED`` module to the upstream ``FAIL`` modules that caused it.

    Accepts module-number keyed statuses and returns module-number keyed,
    deterministically sorted root-cause lists.  A root cause is a module with
    ``FAIL`` evidence; ``BLOCKED`` intermediaries are traversal steps, never
    root causes, and no cause is invented where the transitive upstream holds
    no ``FAIL``.  A module carrying its own ``FAIL`` is not ``BLOCKED`` and so
    is never assigned a derived root cause — its failure is its own evidence.
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
