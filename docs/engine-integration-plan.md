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

## Explicit non-goals

- No synthetic evidence.
- No global OPE score.
- No new execution status values.
- No UI/report redesign.
- No client-specific data.
- No changes to Agent-A owned files.
