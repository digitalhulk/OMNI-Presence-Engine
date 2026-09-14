# Changelog

All notable changes to OPE are recorded here. The project follows the release
flow documented in `docs/20-continuous-optimization/update-pipeline-v1.md`:
version bump → changelog → validation → release.

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
