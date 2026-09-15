# Engine Integration Plan

## Purpose

Connect the deterministic `ModuleRunner` and the 20-module registry to observations already produced by the audit pipeline without inventing evidence or changing the public report contract.

## Current contract

- `PASS` requires evidence.
- `FAIL` requires an observed failing condition.
- `UNKNOWN` means the engine does not have sufficient evidence.
- `BLOCKED` is reserved for dependency blocking.
- Unbound registry checks remain `UNKNOWN`.
- Existing report keys and module identifiers remain stable.

## Evidence-backed bindings

`AUDIT_BINDINGS` in `src/ope/audit_pipeline.py` is the authoritative list; it is validated against the registry, so a binding naming a check that does not exist cannot silently disappear. The observation sources it draws on:

| Evidence source | Example bound checks |
| --- | --- |
| HTTP response (status, headers, timing, cookies) | `02-infrastructure.hosting.availability`, `02-infrastructure.server_reachability`, `15-performance.ttfb`, `16-security.security_headers`, `16-security.cookies` |
| TLS handshake | `16-security.tls` |
| Parsed HTML (head, structure, landmarks, media, forms) | `03-code.head_metadata`, `03-code.html.validity`, `05-index.canonicalization`, `13-ux.mobile_usability`, `14-accessibility.alt_text`, `17-language.language_declaration` |
| JSON-LD entity graph | `01-entity.identity`, `06-semantics.entity_markup`, `11-authority.reviews`, `12-local.nap_consistency` |
| robots.txt / AI crawler access | `04-crawl.robots_access`, `04-crawl.bot_access`, `10-ai-search.agent_accessibility` |
| Linked CSS/JS measurement | `03-code.css_cost`, `03-code.js_cost`, `14-accessibility.reduced_motion` |
| Content citability analysis | `10-ai-search.answer_eligibility`, `10-ai-search.citation_presence` |
| Local run history | `20-continuous-optimization.monitoring`, `20-continuous-optimization.regression_guards` |
| PageSpeed Insights (optional, key-gated) | `15-performance.lcp`, `15-performance.cls`, `15-performance.inp` |

Note that `structured_data` is a check of module `03-code` in the registry, not of `06-semantics`; `06-semantics` owns `entity_markup`. Bindings must use the registry's own check ids.

Each binding is deliberately limited to an observation the audit actually makes.

## Reconciliation rule

A module can become `FAIL` when an evidence-backed bound check fails.

A module can become `PASS` only when every registered check in that module has an evidence provider and every covered check passes.

Partial coverage must remain `UNKNOWN`. This prevents a small set of passing checks from being presented as proof that an entire module has passed.

`N/A` is reserved for a check that cannot apply to the target as observed: markup detailing an entity or local business the page never declares, a defect count over a population the page does not contain (form inputs, buttons, video), or a history comparison with no stored baseline. `N/A` is a deliberate statement that the check does not apply — it is never a substitute for `UNKNOWN` (no evidence) or `FAIL` (evidence of a problem).

## Integration sequence

1. Keep `ModuleRunner` evidence semantics strict.
2. Adapt existing audit observations into `CheckResult` objects.
3. Execute the registered checks against the audit context.
4. Reconcile module status using the partial-coverage rule above.
5. Preserve existing findings, inventory, summary, and report JSON keys.
6. Add regression tests for pass, fail, partial coverage, and unbound checks.
7. Wire the normalized engine into the CLI only after the core integration is stable and the shared CLI contract has been coordinated with Agent-A.

## Current state (v0.10.0)

All 136 registry checks across 20 modules are bound: 115 deterministic checks execute against observations, 3 finding-record checks return `N/A` when no findings exist, and 18 external-evidence checks return `UNKNOWN` with a specific reason naming the missing API or service.

Three normalizers share the same `evidence-diagnostic-v1` contract:
- `normalize_result()` — single-page audit
- `normalize_site_result()` — site-wide crawl audit (`engine_scope: "site"`)
- `normalize_performance_result()` — browser performance audit (`engine_scope: "performance"`)

The performance normalizer converts browser-level findings into the engine finding schema, injects five performance evidence groups into the inventory via `performance_evidence.py`, runs all 136 registry checks, and reconciles module statuses. The single-page and site audit types record run history for regression detection; performance audit does not yet record run history.

The 20-module dependency graph from `schemas/dependency-graph-v1.md` is executable in `dependency_graph.py`. The graph is validated at construction — `validate_graph()` rejects dangling edges and cycles (iterative three-state DFS), and topological order is deterministic (Kahn's algorithm). After check execution and module status reconciliation, the engine runs `cascade_blocked()` then `find_root_causes()`. Cascade is evidence-safe: a module is derived `BLOCKED` when any transitive upstream dependency is `FAIL`/`BLOCKED`, but a module's own direct evidence is preserved — `FAIL` stays `FAIL`, `N/A` stays `N/A`, and only `PASS`/`UNKNOWN` modules are converted. `UNKNOWN`/`N/A` upstream states never cause a block. Root causes are reported in the output's `dependency_root_causes` map and per blocked module in `blocked_by`. The cascade derives module status only; it never mutates check-level evidence (no check becomes `FAIL`/`BLOCKED` because an upstream module failed).

Scoring is integrated: `scoring.module_score()` computes evidence-weighted pass coverage per module (N/A excluded, UNKNOWN never treated as pass, BLOCKED returns None), and `scoring.global_health()` traverses the dependency graph in topological order so parallel branches do not penalize each other. Each normalizer attaches per-module `score` and a top-level `health` key.

Scores are explainable: `scoring.module_score_basis()` and `scoring.health_basis()` return the deterministic derivation behind each number — the module basis names the derivation method, check tallies, evidence-weighted pass/total, and (for BLOCKED modules) the `blocked_by` root causes; the health basis lists each scored module's upstream confidence and adjusted contribution in topological order. `module_score()` and `global_health()` return the `score`/`health` field of these bases, so the number and its provenance share a single computation and cannot disagree. Each normalizer attaches per-module `score_basis` and a top-level `health_basis` key.

Remediation is planned: `planner.build_remediation_plan()` turns the diagnosis into a dependency-ordered plan attached to the output as `remediation_plan`. Root-cause modules are ordered by how many downstream modules each would unblock (from the dependency graph), then module number; each carries its evidence-backed findings ordered by priority. Direct failures (blocking nothing) and blocked modules (waiting on their root causes) are listed separately. The planner orders existing evidence only — it invents no remediation — and `IMPLEMENT` stays human-owned. `planner.diagnosis_markdown()` renders the health, module status, and plan into the markdown reports so the diagnostic chain is visible, not just computed.

## Explicit non-goals

- No synthetic evidence.
- No new execution status values.
- No UI/report redesign.
- No client-specific data.
- No changes to Agent-A owned files.
