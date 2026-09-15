# Changelog

All notable changes to OPE are recorded here. The project follows the release
flow documented in `docs/20-continuous-optimization/update-pipeline-v1.md`:
version bump → changelog → validation → release.

## 0.12.0

Live-site finalization: real-response robustness, full diagnostic surfacing
in every report format, and an end-to-end acceptance layer.

### Added

- **Response decompression** (`audit._decode_content_encoding`): bounded
  gzip/deflate handling for servers that compress a response OPE did not
  ask to be compressed. Output is capped (8 MiB) against decompression
  bombs; unknown or malformed encodings raise rather than feeding garbage
  to the HTML parser.
- **HTML report diagnostics**: the canonical `report_html.py` renderer now
  shows global health, per-module scores, dependency root causes, and the
  dependency-ordered remediation plan (root causes by unblock impact,
  independent failures, blocked-and-waiting) — all through the existing
  `_e()` escaping. The module grid shows each module's score. JSON,
  Markdown, and HTML now expose the same diagnostic chain the engine
  computes.
- **`test_acceptance.py`** (19 tests): drives the real `audit()` pipeline
  against controlled fixtures with the network mocked — healthy site,
  broken infrastructure, redirect, malformed HTML, robots restrictions,
  missing metadata/canonical/alt, performance-evidence present vs. absent,
  end-to-end cascade + root-cause invariants (evidence firewall: a module
  with its own FAIL is never masked to BLOCKED), and JSON/Markdown/HTML
  report generation across HTTP status codes without crashes.
- **SSRF regression tests**: cloud-metadata IP, IPv4-mapped IPv6 loopback,
  and mixed public/private resolution are all confirmed blocked.

### Notes

- The one known SSRF limitation remains DNS-rebinding via TOCTOU (the
  resolved address is validated, then reconnected): closing it requires
  pinning the validated IP through the opener/TLS/redirect path and is
  tracked as separate hardening. All static and resolved-address SSRF
  vectors (loopback, private, link-local, metadata, IPv6 forms) are blocked.

## 0.11.0

Executable remediation planning (the `PLAN` stage) and diagnostic surfacing.
The dependency-graph root-cause analysis and explainable scores built in
prior clusters now drive a dependency-ordered remediation plan and are
visible in every human-readable report.

### Added

- **`planner.py` — `build_remediation_plan()`**: a deterministic,
  evidence-based remediation plan derived from the diagnosis. It never
  invents remediation, evidence, or priorities — it *orders* what the
  diagnosis produced, driven by the real dependency graph:
  - **root causes** — `FAIL` modules that block downstream work, ordered by
    how many modules each would unblock (desc), then module number; fixing
    these first frees the most of the graph;
  - **direct failures** — `FAIL` modules that block nothing downstream;
  - **blocked** — modules waiting on their root causes, listed but not
    planned as work items (their evidence is untrustworthy until the
    upstream failure is fixed).
  Findings are ordered by priority then id; a module with no finding record
  is reported with an empty finding list rather than an invented one.
  `IMPLEMENT` stays human-owned — the plan describes what to fix, never
  applies changes.
- **`planner.diagnosis_markdown()`**: a shared markdown renderer for global
  health, failing/blocked modules, and the remediation plan, so the
  diagnostic view is identical across single-page, site, and performance
  reports.
- **Engine wiring**: each normalizer now attaches a top-level
  `remediation_plan` to the output.
- **Report surfacing**: `audit.markdown_report()` and the site/performance
  markdown reports now include a "Diagnosis & Plan" section — previously the
  single-page report surfaced neither health, module status, root causes,
  nor scores.
- **`test_planner.py`** (12 tests) and engine-integration coverage for the
  attached plan.

## 0.10.0

Score explainability and provenance: every module score and the global
health score now carry a deterministic basis explaining how they were
derived. OpenRouter response-body size hardening.

### Added

- **`scoring.module_score_basis()`**: returns a structured explanation of a
  module's score — the derivation `method` (`evidence-weighted-coverage`,
  `status-derived`, `blocked`, or `no-evidence`), check tallies
  (passed/failed/unknown/na), and the evidence-weighted pass/total. For
  BLOCKED modules it names the `blocked_by` root causes. `module_score()`
  now returns this basis's `score`, so the number and its explanation can
  never disagree.
- **`scoring.health_basis()`**: returns the topological rollup behind the
  global health score — per scored module, the upstream confidence applied,
  the limiting upstream module, and the adjusted contribution.
  `global_health()` returns this basis's `health`.
- **Engine wiring**: each module dict now carries a `score_basis` key and
  the output carries a top-level `health_basis` key, attached by the three
  normalizers via `engine._compute_scores()` / `_reconcile_and_score()`.
- **Score-basis and health-basis tests**: `TestModuleScoreBasis` (7 tests)
  and `TestHealthBasis` (5 tests) verifying basis/score agreement, check
  tallies, BLOCKED root-cause naming, topological ordering, and determinism.
- **OpenRouter body-bounding tests**: oversized responses are rejected and
  bounded responses are parsed.

### Changed

- **`scoring.module_score()` / `global_health()`**: refactored to delegate
  to the new basis functions — a single source of computation, so the
  score and its provenance are always consistent. External behavior and
  golden values are unchanged.

### Fixed

- **OpenRouter unbounded read**: `OpenRouterClient.chat_json()` now bounds
  the success response body to 1 MiB (`MAX_RESPONSE_BYTES`), matching the
  bound already enforced on the audit HTTP path. Previously the success
  path called `response.read()` with no size limit while only the error
  path was bounded.

## 0.9.0

Executable, validated dependency graph with evidence-safe BLOCKED cascade,
graph-based root-cause traversal, and dependency-aware scoring.

### Added

- **`dependency_graph.py`**: the 20-module dependency graph from
  `schemas/dependency-graph-v1.md` encoded as `MODULE_DEPENDENCIES` — the
  single executable source of module dependencies — with deterministic
  topological ordering (`TOPOLOGICAL_ORDER`, `TOPOLOGICAL_ORDER_NUMBERS`),
  number-keyed dependency mapping (`DEPENDENCIES_BY_NUMBER`), and query
  functions `upstream_modules()`, `downstream_modules()`,
  `cascade_blocked()`, `find_root_causes()`.
- **Graph validation** (`validate_graph()`, `GraphValidationError`): a
  reusable validator that rejects **dangling edges** (a dependency that is
  not a declared module) and **cycles**. Cycles are detected with an
  iterative three-state DFS (UNSEEN → VISITING → COMPLETE) — a single
  "visited" set cannot distinguish a back-edge from an already-explored
  node — and the traversal is iterative so a deep/adversarial graph cannot
  exhaust the recursion stack. Topological order uses Kahn's algorithm and
  is deterministic.
- **Evidence-safe BLOCKED cascade**: `cascade_blocked()` marks a module
  `BLOCKED` when any transitive upstream dependency is `FAIL`/`BLOCKED`,
  but `BLOCKED` is a *derived* state that never replaces direct evidence —
  a module's own `FAIL` stays `FAIL` and its own `N/A` stays `N/A`; only
  `PASS`/`UNKNOWN` modules are converted. `UNKNOWN`/`N/A` upstream states
  never cause a block. Cascade derives module status only and never mutates
  check-level evidence.
- **Graph-based root-cause traversal**: `find_root_causes()` traces each
  BLOCKED module's transitive upstream to the FAIL modules that caused it,
  never fabricating a BLOCKED intermediary as a cause and never inventing a
  cause where no upstream FAIL exists. Root causes are reported per module
  in `dependency_root_causes` and per blocked module in `blocked_by`.
- **`test_dependency_graph.py`**: 66 tests across 11 classes covering graph
  structure, parallel branches, upstream/downstream queries, graph
  validation (cycles, self-cycle, dangling edges, deep-chain determinism),
  evidence-safe cascade (direct FAIL/N/A preservation), root-cause
  traversal, nine end-to-end golden scenarios, the definitive acceptance
  test, and execution-order independence.
- **Evidence-firewall tests** (`test_engine.py::TestEvidenceFirewall`):
  cascade never mutates check evidence, direct-FAIL modules keep FAIL
  end-to-end, and BLOCKED is module-level only (never a check status).

### Changed

- **`engine.py` reconciliation**: after check execution and module status
  reconciliation, the engine now runs `cascade_blocked()` and
  `find_root_causes()` against the 20-module status map. Modules whose
  status changes to BLOCKED get a `blocked_by` key listing root causes.
  The output gains a `dependency_root_causes` map when any module is blocked.
- **`scoring.module_score()`**: BLOCKED modules now return `None` instead
  of computing scores from unreliable check results.
- **`scoring.global_health()`**: replaced alphabetical module-key ordering
  with topological-order traversal from the dependency graph. Upstream
  confidence uses `min()` across direct graph dependencies, so parallel
  branches (Content/Media, Search/AI, Authority/Local, UX tier) do not
  penalize each other.

## 0.8.0

SSRF final consolidation, User-Agent unification, version sync, and test
coverage expansion.

### Changed

- **SSRF validation fully consolidated**: `crawler.py` now imports
  `validate_url_strict()` from `url.py` instead of maintaining its own
  `_safe_url()` duplicate. All robots-related URL validation goes through
  the single canonical implementation in `url.py`.
- **User-Agent string unified**: all six remaining hardcoded
  `"OPE-Audit/0.1"` strings across `audit.py`, `crawler.py`,
  `sitemap.py`, `site_crawler.py`, `site_audit.py`, and
  `integrations/pagespeed.py` now derive from the centralized
  `ope.USER_AGENT` constant (or `ENGINE_VERSION` in `audit.py`), which
  tracks the installed package version dynamically.
- **`ope.USER_AGENT`**: new package-level constant in `__init__.py`
  providing a single source of truth for the HTTP User-Agent string
  (`OPE-Audit/{version}`).

### Fixed

- **Version sync**: README.md (0.6.0 → 0.8.0), engine-integration-plan.md
  (v0.6.0 → v0.8.0), conftest.py fixture (0.6.0 → 0.8.0).
- **README check-count accuracy**: corrected "116 deterministic / 20
  UNKNOWN" to "115 deterministic + 3 finding-record / 18 UNKNOWN"
  throughout README.md to match the canonical breakdown in
  `audit-runner-v1.md` and `engine-integration-plan.md`.
- **Documentation accuracy**: `engine-integration-plan.md` now correctly
  states that performance audit does not yet record run history (previously
  claimed all three audit types do).

### Added

- **`crawler.robots_url()` tests**: URL construction, port preservation,
  SSRF rejection via the canonical `validate_url_strict` path.
- **`crawler.fetch_robots()` tests**: successful fetch with structured
  result, network error handling, robots.txt size-limit enforcement, and
  dynamic User-Agent verification.
- **`audit.markdown_report()` tests**: section presence, finding rendering,
  and empty-findings path.

### Removed

- **Dead SSRF duplicate**: `crawler._safe_url()` removed — was the last
  remaining duplicate of `url.validate_url_strict()`. `import ipaddress`
  and `import socket` removed from `crawler.py` as they were only used by
  `_safe_url()`.

## 0.7.0

DRY consolidation, version sync, and spec accuracy.

### Changed

- **SSRF validation consolidated**: `audit.py` now imports
  `validate_url_strict()` and `ALLOWED_SCHEMES` from the canonical
  `url.py` module instead of maintaining a duplicate `_validate_url()`
  implementation. `_SafeRedirect` uses the same shared function.
  Security-critical code path — one source of truth.
- **Priority formula DRY**: `audit.py:_finding()` now calls
  `scoring.priority()` instead of inlining the same formula.
  `scoring.priority()` was previously orphaned (implemented but never
  called from production code).
- **Engine normalizer DRY**: extracted `_reconcile_and_score()` and
  `_init_modules_from_findings()` in `engine.py`, eliminating ~80 lines
  of duplicated reconciliation/scoring logic across the three normalizers.
- **User-Agent version derived dynamically**: `audit.py:_request()` and
  `browser.py` device configs now derive the OPE version from
  `importlib.metadata` instead of hardcoding stale version strings.

### Fixed

- **Version sync**: README.md (0.5.0 → 0.6.0), engine-integration-plan.md
  (v0.5.0 → v0.6.0), conftest.py fixture (0.5.0 → 0.6.0), browser.py
  User-Agent (0.3 → dynamic), audit.py User-Agent (0.1 → dynamic).
- **Documentation accuracy**: `setup-v1.md` now documents all CLI flags
  including `--browser*`, `--no-robots`, `--allow-subdomains`,
  `--mobile-only`, and `--no-screenshot`. Engine integration plan updated
  with scoring integration status.
- **Type hints**: `cli.py` markdown report functions use `dict[str, Any]`
  instead of bare `dict`. `registry.py:_unknown_runner()` has an explicit
  `CheckRunner` return type. `audit.py:_SafeRedirect.redirect_request()`
  has parameter type annotations.

### Removed

- **Dead constants**: `_MODERN_TLS`, `_CERT_EXPIRY_WARNING_DAYS`,
  `_LOCALE_PATTERN`, and `_CONTENT_WORD_BUDGET` removed from `audit.py`
  — they were duplicates of the canonical definitions in
  `audit_pipeline.py` and were never referenced in `audit.py`.
- **Dead import**: `import ipaddress` removed from `audit.py` (was only
  used by the now-removed `_validate_url()`).

## 0.6.0

Scoring integration, CLI test coverage, documentation accuracy, and dead code
removal.

### Added

- **Scoring integration in `engine.py`**: all three normalizers
  (`normalize_result`, `normalize_site_result`,
  `normalize_performance_result`) now compute per-module
  `module_score()` and `global_health()` from `scoring.py`. Each
  module dict carries a `"score"` key (float or None) and the output
  dict carries a `"health"` key.
- **CLI command tests**: `TestSiteAuditCommand` (JSON output, HTML
  dispatch, exception handling) and `TestPerformanceAuditCommand`
  (JSON output, HTML dispatch, exception handling) — 6 new tests
  covering the two previously untested command functions.
- **Engine scoring tests**: `TestScoringIntegration` — 7 new tests
  verifying that all three normalizers produce `health` and per-module
  `score` keys, with full-pass, mixed, and empty-check scenarios.

### Fixed

- **Documentation accuracy**: `audit-runner-v1.md` and
  `engine-integration-plan.md` now state the correct check breakdown
  (115 deterministic + 3 finding-record + 18 external-evidence = 136).
  The `ope.priority` reference in `audit-runner-v1.md` is corrected to
  `ope.scoring`. The engine integration plan version is updated to
  v0.5.0.

### Removed

- **Dead code**: `evidence.py`, `evidence_provider.py`, `root_cause.py`
  and their test files (`test_evidence.py`, `test_evidence_provider.py`,
  `test_root_cause.py`). These modules were never imported by any
  production code — `evidence.py` and `evidence_provider.py` were
  superseded by `engine.py`'s inline normalization, and `root_cause.py`
  was a thin alias wrapper. All functionality they provided is covered
  by the canonical `engine.normalize_finding()` and
  `engine.normalize_result()`.

## 0.5.0

Contract integrity, unified HTML reporting, and scoring engine.

### Added

- **Evidence-weighted `module_score()`** in `scoring.py`: replaces the
  binary 0/100/None stub with evidence-weighted pass coverage per the
  `scoring-v1` spec. Each check's contribution is weighted by its
  evidence confidence. N/A checks are excluded from the denominator.
  UNKNOWN is never treated as pass.
- **`global_health()`** in `scoring.py`: dependency-aware global health
  score per the spec. Upstream failures reduce confidence in downstream
  module scores.
- **`report_html_site.py`**: standalone RawBlock HTML report for site
  audits, with crawl summary cards, page table, module grid and
  severity-filtered findings. Reuses shared helpers from `report_html.py`.
- **`report_html_performance.py`**: standalone RawBlock HTML report for
  performance audits, with Core Web Vitals table, resource summary,
  module grid and findings. Reuses shared helpers from `report_html.py`.
- **`--html PATH` flag** for `ope site-audit` and `ope performance-audit`.
- **`conftest.py`**: shared pytest fixtures (`minimal_audit_result`,
  `minimal_site_result`, `minimal_performance_result`).
- **`[tool.pytest.ini_options]`** in `pyproject.toml` with `testpaths`
  and `addopts`.
- **Test coverage expansion**: new test files for site HTML reports
  (`test_report_html_site.py`, 12 tests) and performance HTML reports
  (`test_report_html_performance.py`, 12 tests); scoring tests expanded
  from 3 to 19 covering evidence weighting, N/A exclusion, global
  health, and upstream penalties.

### Fixed

- **Version single source of truth**: `__init__.py` now derives
  `__version__` from `importlib.metadata` at runtime instead of a
  hardcoded string, so it always matches `pyproject.toml`.
- **Scoring engine**: `module_score()` was a binary stub returning
  0.0 (FAIL), 100.0 (PASS), or None, which contradicted the
  `scoring-v1` spec requiring evidence-weighted pass coverage.
- **README version**: was `0.3.0`, now derives from `pyproject.toml`.
- **`audit-runner-v1.md`**: claimed "93 of 136" bound checks, corrected
  to "all 136" with the actual breakdown.

## 0.4.0

Performance-audit engine contract and unified history integration. The
performance subsystem now produces the same `evidence-diagnostic-v1`
contract as single-page and site audits.

### Added

- **`normalize_performance_result()`** in `engine.py`: stamps
  `engine_contract: "evidence-diagnostic-v1"` and
  `engine_scope: "performance"`, converts performance findings into the
  engine finding schema, runs all 136 registry checks against the
  performance inventory, and reconciles 20-module statuses.
- **`performance_evidence.py`**: bridge module injecting five performance
  signal groups (`perf_vitals_summary`, `perf_resource_analysis`,
  `perf_dom_analysis`, `perf_render_analysis`, `perf_findings_summary`)
  into the inventory using `setdefault()` to never overwrite existing
  keys. Only injects when the performance result status is `COMPLETED`.
- **`--markdown` flag** for `ope performance-audit`: generates a
  formatted report with Core Web Vitals table and findings sorted by
  priority.
- **Site-audit history**: `ope site-audit` now records run history via
  `history.attach_baseline()` and `history.save_run()`, gated on the
  `--no-history` flag.
- **`--no-history` flag** for `ope site-audit`.
- **Test coverage expansion**: 75 new tests across five new test files
  (`test_cli.py`, `test_evidence.py`, `test_registry.py`,
  `test_performance_evidence.py`) and additions to `test_engine.py`.

## 0.3.0

Full check-binding coverage: all 136 registry checks across 20 modules are now
bound to evidence providers. The 43 previously unbound checks are split into
23 deterministic checks (evaluated from the HTTP response, HTML, and page
signals) and 20 external-evidence checks that return `UNKNOWN` with a specific
reason naming the missing API or service, instead of a generic message.

### Added

- **PageParser signals**: verification meta tags (Google, Bing, Yandex,
  Pinterest, Facebook), lazy-image counting, noscript content detection,
  password-input detection, list/table counting.
- **Computed audit signals**: CAPTCHA presence (reCAPTCHA, hCaptcha,
  Turnstile), event-tracking detection (GTM, gtag, fbq, Plausible, Umami),
  UTM attribution code, soft-404 detection, rate-limit header detection,
  title/H1 intent alignment.
- **23 new deterministic check handlers** covering ownership verification,
  crawl errors, crawl budget risk, rendering indexability, entity
  relationships, intent match, helpfulness, conversion context, media
  performance, SERP eligibility, sitelinks readiness, image visibility,
  AI retrievability, source grounding, citations, booking friction,
  authentication security, abuse controls, regional intent, event quality,
  attribution, booking completion, and trust-to-action.
- **`_EXTERNAL_EVIDENCE_CHECKS` dict** (20 entries) for checks that need
  external APIs (backlink index, Search Console, browser rendering, CVE
  database, CRM, review aggregation, etc.). Each returns `UNKNOWN` with a
  human-readable reason naming the missing integration instead of the old
  generic "No evidence provider is bound" message.
- **`N/A` semantics** for context-dependent checks: booking friction is N/A
  when no forms exist, auth is N/A when no login form, regional intent is
  N/A for non-local businesses, image visibility is N/A when no images, and
  media performance is N/A when no images are present.

## 0.2.0

Evidence-backed registry coverage went from 10 to 93 of 136 checks, and every
one of the 20 modules now has at least one bound check. An unbound check still
executes and reports `UNKNOWN` with a reason — absence of evidence is never
reported as a pass.

### Fixed

- `structured_data` was bound to `06-semantics`, a check id the registry does
  not define (the registry owns it under `03-code`). The binding was silently
  dropped, so the check never ran.
- Module reconciliation counted only the checks present in the execution
  result, so partial registry coverage could report a false `PASS`. Missing
  checks now count as `UNKNOWN`.
- `crawler.fetch_robots()` was never called by `audit()`, so the three checks
  bound to robots evidence were dead in the real CLI path and only passed in
  unit tests that hand-built the inventory.
- `citability.py` was fully implemented and tested but never wired into an
  audit.
- Response headers were collapsed into a plain dict, reducing multiple
  `Set-Cookie` headers to the last one and hiding insecure cookies.
- `normalize_result()` executed the registry and then discarded the results,
  keeping only reconciled module statuses. The report now publishes
  `result["checks"]`, which the optional reasoning layer already expected.
- The engine version was hardcoded in `audit.py` and had drifted from
  `pyproject.toml`; it is now read from the installed package.
- The bundled sample report declared `evidence-root-cause-v1` rather than the
  actual `evidence-diagnostic-v1` contract, and predated most inventory keys.

### Added

- **Observation surface**: real TLS handshake inspection (protocol, cipher,
  certificate expiry), cookie flag hygiene, CSP directive analysis, credential
  pattern scanning, CDN/WAF detection, DNS and TTFB timing, full JSON-LD graph
  parsing (including `@graph`), document structure and accessibility signals,
  and measurement of linked CSS/JS under strict fetch caps.
- **Run history** (`ope.history`): each run records tracked metrics, finding
  ids and check statuses under `~/.ope/runs` (`OPE_HOME`-aware, newest 50 per
  target). The next run compares against it to detect metric regressions and
  newly appeared findings, which is what makes module 20 executable.
- **PageSpeed Insights integration** (`ope.integrations.pagespeed`): Core Web
  Vitals evidence, gated on `OPE_PAGESPEED_API_KEY`. Without a key it makes no
  network call and the affected checks stay `UNKNOWN`.
- **`N/A` execution status in practice**: used where a check cannot apply to
  the target as observed — local-business detail on a page that declares no
  local business, defect counts over elements the page does not contain, or a
  history comparison with no stored baseline.
- **CLI flags**: `--no-subresources` and `--no-history`.
- **Report viewer**: the RawBlock console renders the new check-level results
  (status totals and failing checks), shows per-module failing-check counts,
  and formats nested inventory values instead of printing `[object Object]`.

### Changed

- `15-performance.page_weight` reports document plus measured CSS/JS against a
  1MB budget, falling back to the HTML-only measurement when subresources were
  not fetched. Both paths state their scope in the check's reason.
- README and `docs/engine-integration-plan.md` now describe the shipped engine,
  including a per-module coverage table and an explicit list of what remains
  unbound and what evidence it would need.

### Not included

The remaining 43 unbound checks need evidence this engine does not collect:
backlink and brand-mention data, Search Console and analytics APIs,
rendered-browser metrics, and dependency or auth scanning.
