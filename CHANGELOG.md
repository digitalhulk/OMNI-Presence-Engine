# Changelog

All notable changes to OPE are recorded here. The project follows the release
flow documented in `docs/20-continuous-optimization/update-pipeline-v1.md`:
version bump → changelog → validation → release.

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
