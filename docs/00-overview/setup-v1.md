# OPE Setup v1

## Initialize

```bash
ope setup
```

The wizard collects project/entity name, canonical website URL, country, market, primary language, business type, goals, and optional data-source paths or URLs.

Configuration is written locally under `~/.ope/config.json`.

## Run

```bash
ope audit https://example.com --markdown
```

The legacy command remains supported:

```bash
ope-audit https://example.com --markdown
```

## Audit options

| Flag | Effect |
| --- | --- |
| `--json` / `--markdown` / `--html PATH` | Output format |
| `--timeout SECONDS` | Per-request timeout (default 15) |
| `--no-subresources` | Skip fetching linked CSS/JS. Faster, but the CSS cost, third-party, motion and focus checks report `UNKNOWN` |
| `--no-history` | Do not read or write the local run history, so regression comparison is skipped |

## Site audit

```bash
ope site-audit https://example.com --markdown
```

Crawls the site, builds a link graph, detects orphan pages, and produces
cross-page findings under the `evidence-diagnostic-v1` contract.

| Flag | Effect |
| --- | --- |
| `--max-pages N` | Maximum pages to crawl (default 200) |
| `--max-depth N` | Maximum crawl depth (default 10) |
| `--delay SECONDS` | Delay between requests (default 0.5) |
| `--markdown` | Markdown output |
| `--html PATH` | Write a standalone RawBlock HTML report |
| `--no-history` | Skip local run history |
| `--no-sitemaps` | Skip sitemap discovery |

## Performance audit

```bash
ope performance-audit https://example.com --markdown
```

Runs browser-based performance analysis (Core Web Vitals, resource
analysis, DOM analysis, render analysis) and produces findings under the
`evidence-diagnostic-v1` contract.

| Flag | Effect |
| --- | --- |
| `--timeout SECONDS` | Per-request timeout (default 30) |
| `--markdown` | Markdown output with CWV table and prioritized findings |
| `--html PATH` | Write a standalone RawBlock HTML report |
| `--desktop-only` | Skip mobile profile |

## Run history

Each audit records a compact snapshot — tracked metrics, finding ids and check
statuses — under `~/.ope/runs`, keeping the newest 50 runs per target. Set
`OPE_HOME` to move the base directory. The next run for the same target
compares against the most recent snapshot to detect metric regressions and
newly appeared findings; a first run says it has no baseline rather than
implying a clean comparison.

## Optional external evidence

Both are read from the environment at runtime and are never written to the
repository or into reports. When a credential is absent, the affected checks
report `UNKNOWN` — nothing is estimated in its place.

| Variable | Unlocks |
| --- | --- |
| `OPE_PAGESPEED_API_KEY` | Core Web Vitals from Google PageSpeed Insights (`15-performance.lcp/fcp/cls/tbt/inp`) |
| `OPENROUTER_API_KEY` | Advisory reasoning layer over deterministic evidence |

## Flow

```text
CLI
 ↓
SETUP / AUDIT
 ↓
LOCAL PROJECT CONTEXT
 ↓
EVIDENCE COLLECTION
 ↓
AUDIT ANALYSIS
 ↓
FINDINGS / REPORT
```
