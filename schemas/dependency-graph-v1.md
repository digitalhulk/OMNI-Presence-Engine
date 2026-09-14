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

The graph is encoded in `src/ope/dependency_graph.py` as `MODULE_DEPENDENCIES` with computed topological ordering. `cascade_blocked()` propagates BLOCKED downstream from FAIL modules (UNKNOWN does not cascade). `find_root_causes()` traces each BLOCKED module back to the upstream FAIL modules, skipping BLOCKED intermediaries. The engine runs both after check execution and module status reconciliation.

## Parallel branches

Content(07)/Media(08), Search(09)/AI-Search(10), Authority(11)/Local(12), and UX(13)/Accessibility(14)/Performance(15)/Security(16)/Language(17) are parallel branches that share the same upstream and feed the same downstream tier. Research, SEO data, first-party data, technical measurements and business data may execute concurrently, then converge at Evidence Normalization.
