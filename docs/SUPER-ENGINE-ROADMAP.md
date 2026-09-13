# OPE Super-Engine Roadmap

## Objective

OPE should behave as a ready-to-use presence engineering engine: one trusted entry point should orchestrate deterministic auditing, evidence validation, diagnosis, optional external providers, advisory reasoning, validation planning, and report generation.

## Operating rules

1. Deterministic observations remain authoritative.
2. External providers are optional evidence sources, never truth by themselves.
3. Missing credentials produce an explicit unavailable capability, not fabricated evidence.
4. AI reasoning is advisory and cannot change deterministic status or convert UNKNOWN into PASS.
5. Credentials are runtime-only and never committed.
6. No public endpoint may become an unrestricted remote URL-fetching proxy.
7. Agent-A owns presentation/UI; Agent-B owns engine/core. Shared files require coordination.

## Provider routing

The provider registry maps capabilities to optional providers. The next integrations should be implemented as small adapters behind capability contracts rather than scattering provider-specific logic throughout checks.

Priority order:

- reasoning/evidence synthesis: OpenRouter
- research/web discovery: Parallel
- SEO/site audit/AI visibility: OpenSEO where its supported API contract is available
- keyword/SERP/backlink/competitor evidence: DataForSEO
- search performance/indexing evidence: Google Search Console and Bing Webmaster

A provider may be selected only when its capability is requested, its runtime configuration is present, and its response can be mapped into OPE evidence with source and observation timestamp.

## Autonomous lifecycle

`CREATE → QUEUED → RUNNING → OBSERVE → VALIDATE EVIDENCE → RECONCILE → DIAGNOSE → OPTIONAL REASON → REPORT → COMPLETE`

Cancellation and provider failure must remain explicit lifecycle states. A failed optional provider must not invalidate deterministic results.

## Definition of ready-to-use

- One local entry point starts a complete audit.
- Progress is observable without manual orchestration.
- Every PASS has valid evidence.
- Partial module coverage cannot silently become PASS.
- Findings distinguish observed facts from hypotheses.
- Provider availability is visible without leaking credentials.
- AI output is grounded in collected evidence.
- Results are consumable by the UI without UI-side audit logic.
- Core tests cover lifecycle, provider routing, malformed input, failure isolation, and cancellation.
