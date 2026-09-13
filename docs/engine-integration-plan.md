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

## First evidence-backed bindings

The current audit already observes these signals:

| Module | Check | Evidence source |
| --- | --- | --- |
| 02 Infrastructure | hosting availability | HTTP status |
| 03 Code | head metadata | parsed title |
| 05 Index | canonicalization | parsed canonical link |
| 06 Semantics | structured data | JSON-LD block count |
| 13 UX | mobile usability | viewport metadata |
| 14 Accessibility | alt text | image/alt counts |
| 16 Security | HTTPS | final URL |
| 16 Security | security headers | response headers |
| 17 Language | language declaration | HTML `lang` |

These are deliberately limited to observations the existing audit already makes.

## Reconciliation rule

A module can become `FAIL` when an evidence-backed bound check fails.

A module can become `PASS` only when every registered check in that module has an evidence provider and every covered check passes.

Partial coverage must remain `UNKNOWN`. This prevents a small set of passing checks from being presented as proof that an entire module has passed.

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
