# OPE Dependency Graph v1

Entity -> Infrastructure -> Code -> Crawl -> Index -> Semantics -> Content/Media -> Search/AI -> Authority/Local -> UX/Accessibility/Performance/Security/Language -> Analytics -> Conversion -> Continuous Optimization.

This is a dependency model, not a rigid workflow. Any observed failure can enter the graph at the symptom and trace backward to the owning dependency.

## Root-cause traversal

1. Record the symptom.
2. Identify affected module.
3. Inspect upstream dependencies.
4. Collect evidence.
5. Separate correlation from cause.
6. Select the lowest validated owner of the failure.
7. Generate remediation.
8. Define measurable validation.
9. Add a regression guard.

## Executable implementation

The graph is encoded in `src/ope/dependency_graph.py` as `MODULE_DEPENDENCIES`, the single executable source of module dependencies — engine execution, cascade propagation, root-cause traversal, and scoring all derive from it, never from a second hardcoded assumption such as "module N depends on module N-1".

**Dependency model level.** The canonical dependency model is deliberately **module-level**. `ModuleRunner` exposes a generic per-check `depends_on` capability, but the registry declares none (all 136 checks have empty `depends_on`), so there is exactly one dependency graph — the module graph above. Introducing check-level dependencies would be a deliberate spec + engine decision, never an accidental second graph; the contract is locked by `tests/test_graph_integrity.py::test_canonical_dependency_model_is_module_level_only`.

**Graph validation.** `validate_graph()` rejects malformed topology explicitly rather than silently accepting it:

- **Dangling edge** — a dependency that is not itself a declared module raises an error.
- **Cycle** — detected by an iterative three-state DFS (UNSEEN → VISITING → COMPLETE); any edge back to a node still on the current path is a cycle. A single "visited" set is insufficient because it cannot tell a back-edge from an already-explored node. The traversal is iterative so a deep or adversarial graph cannot exhaust the recursion stack.

Topological ordering (Kahn's algorithm over the validated graph) is deterministic and reproducible.

**Evidence-safe cascade.** `cascade_blocked()` marks a module `BLOCKED` when any of its **transitive** upstream dependencies is `FAIL` or `BLOCKED` — but `BLOCKED` is a *derived* dependency state and never replaces direct evidence:

- A module with its own `FAIL` evidence keeps `FAIL`. A real failure is never masked by a derived state.
- A module that is `N/A` (the check does not apply) keeps `N/A`.
- Only `PASS`/`UNKNOWN` (non-evidence) modules are converted to `BLOCKED`.
- `UNKNOWN` and `N/A` upstream states never cause a block — absent or inapplicable evidence is not a failure.

The transitive rule is deliberate: an inapplicable intermediate layer does not repair a broken foundation, so a module that still transitively depends on a failed module is `BLOCKED` and the upstream failure remains visible rather than being silently shielded.

**Root-cause traversal.** `find_root_causes()` traces each `BLOCKED` module through its transitive upstream and reports only modules that actually hold `FAIL` evidence, deterministically sorted. `BLOCKED` intermediaries are never fabricated as root causes, and no cause is invented where the transitive upstream holds no `FAIL`. A module carrying its own `FAIL` is not `BLOCKED` and so is never assigned a derived root cause — its failure is its own evidence.

**Evidence firewall.** Cascade derives *module* status only. It never touches check-level results: no check becomes `FAIL` or `BLOCKED` because an upstream module failed, and no evidence is synthesized for a `BLOCKED` module. The engine runs cascade and root-cause after check execution and module reconciliation, then scores.

## Parallel branches

Content(07)/Media(08), Search(09)/AI-Search(10), Authority(11)/Local(12), and UX(13)/Accessibility(14)/Performance(15)/Security(16)/Language(17) are parallel branches that share the same upstream and feed the same downstream tier. Research, SEO data, first-party data, technical measurements and business data may execute concurrently, then converge at Evidence Normalization.
