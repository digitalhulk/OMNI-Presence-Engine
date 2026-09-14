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
