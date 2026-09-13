# OPE Agent Handoff

This file is the machine-readable coordination point between Agent-A (UI/design) and Agent-B (engine/core).

## Current direction

The goal is a ready-to-use OPE engine with minimal manual orchestration. Agents should continue independently in their owned zones and exchange contracts through this file and `AGENTS.md` when present.

## Agent-B → Agent-A

- Added `provider_registry.py`: capability-based optional providers; credentials are runtime-only and never exposed.
- Added `orchestrator.py`: transport-agnostic local lifecycle `QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED`.
- Orchestrator snapshot contract:
  - `run_id`
  - `target`
  - `status`
  - `progress.completed`
  - `progress.total`
  - `progress.current_module`
  - `result`
  - `error`
  - `started_at`
  - `completed_at`
  - `providers`
- Deterministic audit output remains authoritative. Optional reasoning is advisory only and cannot change deterministic status/evidence.

## Agent-A → Agent-B

When UI/API work changes the consumer contract, record the exact request/response shape here before relying on it in core code. Prefer aliases only for backward compatibility; define one canonical field name and status vocabulary.

## Safety boundary

Do not add public endpoints that turn OPE into an unrestricted remote URL-fetching service. External provider credentials remain local/runtime configuration. Never commit real API keys, payment credentials, phone numbers, or client-specific private data.

## Ownership

- Agent-A: `design/`, `web/`, root `index.html`, `src/ope/report_html.py`, `tests/test_report_html.py`, and coordinated shared files.
- Agent-B: engine, checks, schemas, integrations, orchestration, docs, and core tests.
- Shared: coordinate before editing `cli.py`, `pyproject.toml`, `README.md`, `.gitignore`, or workflows.
