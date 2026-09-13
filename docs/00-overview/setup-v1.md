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
