# OPE Execution Specification v1

OPE converts online-presence problems into evidence-backed actions.

Flow: DISCOVER -> INVENTORY -> AUDIT -> EVIDENCE -> DIAGNOSE -> SCORE -> PLAN -> IMPLEMENT -> VALIDATE -> MONITOR.

The orchestrator combines live web intelligence, SEO datasets, first-party search data, analytics, technical measurements and business outcomes.

Each module owns its checks. Findings are normalized before scoring. Symptoms never become root causes without evidence.

Executable today: DISCOVER through DIAGNOSE, SCORE and VALIDATE run in-process for a single target (`ope audit`), and MONITOR is served by the local run history, which compares each run against the previous one for the same target. IMPLEMENT stays human-owned, and scheduled multi-target monitoring is not implemented. See `automation/audit-runner-v1.md` for the step-by-step status and the README for per-module check coverage.

OPE uses generic, sanitized reference implementations only. External providers such as Parallel and OpenSEO supply optional research or workflow data; first-party sources remain authoritative for their own measurements.

Performance optimization follows the visual-preservation rule: improve implementation efficiency without silently degrading the approved experience.
