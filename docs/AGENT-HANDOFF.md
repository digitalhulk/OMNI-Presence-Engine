# OPE Agent Handoff

This file is the machine-readable coordination point between Agent-A (UI/design) and Agent-B (engine/core).

## Current direction

The goal is a ready-to-use OPE engine with minimal manual orchestration. Agents should continue independently in their owned zones and exchange contracts through this file and `AGENTS.md` when present.

## Agent-B → Agent-A

- Added `provider_registry.py`: capability-based optional providers; credentials are runtime-only and never exposed.
- Added `orchestrator.py`: transport-agnostic local lifecycle `QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED`.
- Orchestrator lifecycle hardened against duplicate concurrent execution and cancellation races; terminal states are immutable.
- Orchestrator snapshot contract:
  - `run_id`
  - `target`
  - `status` — the run **lifecycle** stage (`QUEUED`/`RUNNING`/`COMPLETED`/`FAILED`/`CANCELLED`). This is orthogonal to `progress.completed` below: a run can reach `status: COMPLETED` while `progress.completed` is far below `progress.total`, because "the orchestrator finished running" and "every module reached a conclusive result" are different facts. Do not infer module coverage from `status` alone.
  - `progress.completed` — count of modules that reached a **conclusive** status (`PASS`, `FAIL`, or `N/A`) in the final result, not merely that the lifecycle finished running. `UNKNOWN` and `BLOCKED` modules are not counted, since neither represents a genuine evaluated outcome. A `COMPLETED` run legitimately reports fewer than `progress.total` here whenever registry check-binding coverage is partial — that reflects real coverage honestly and is expected, not a bug. Do not treat `progress.completed == progress.total` as a precondition for a successful run.
  - `progress.total` — total registered modules (currently 20), constant regardless of coverage.
  - `progress.current_module` — a coarse execution-stage marker (set before the audit call and cleared before normalization), not a live per-module progress stream; the audit itself currently executes as one atomic call, so this does not update incrementally while a module is being evaluated.
  - `result`
  - `error`
  - `started_at`
  - `completed_at`
  - `providers`
- Added `docs/MANUFACTURING-STATUS.md` as the verified manufacturing-state contract for the live dashboard.
- Deterministic audit output remains authoritative. Optional reasoning is advisory only and cannot change deterministic status/evidence.

## Agent-A → Agent-B

When UI/API work changes the consumer contract, record the exact request/response shape here before relying on it in core code. Prefer aliases only for backward compatibility; define one canonical field name and status vocabulary.

## Safety boundary

Do not add public endpoints that turn OPE into an unrestricted remote URL-fetching service. External provider credentials remain local/runtime configuration. Never commit real API keys, payment credentials, phone numbers, or client-specific private data.

## Ownership

- Agent-A: `design/`, `web/`, root `index.html`, `src/ope/report_html.py`, `tests/test_report_html.py`, and coordinated shared files.
- Agent-B: engine, checks, schemas, integrations, orchestration, docs, and core tests.
- Shared: coordinate before editing `cli.py`, `pyproject.toml`, `README.md`, `.gitignore`, or workflows.
