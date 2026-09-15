# OPE — Hostinger shared-hosting deployment (template)

This directory is the **source template** for the Hostinger deployment package.
Do not upload it directly — build the package first, so the canonical design
system, renderer and API contract are pulled in from their single homes:

```bash
python scripts/build_hostinger.py --zip
# -> dist/hostinger/           (upload the CONTENTS of this directory)
# -> dist/ope-hostinger.zip    (upload + extract via File Manager)
```

## What this is

A **deployment adapter**, not an engine. The canonical Python OPE engine
(`audit()` → `normalize_result()` → dependency cascade → scoring → planner)
remains the only source of truth. This shell:

- serves the RawBlock Command Center UI,
- renders canonical OPE result JSON **client-side**,
- lists static reports produced by the canonical Python reporter,
- answers `/api/health`, `/api/status`, `/api/audit` with the `ope-web-v1`
  envelope,
- and reports `runtime_unavailable` — honestly — when no Python runtime is
  reachable.

There is **no PHP or JavaScript reimplementation** of any audit, score,
dependency graph or root-cause logic anywhere in this package.

## Files

| Path | Role |
| --- | --- |
| `index.php` | Command Center shell (URL input, runtime banner, report loader) |
| `.htaccess` | HTTPS redirect, clean API routes, hardening, CSP, caching |
| `api/_bootstrap.php` | Shared helpers: config, security headers, JSON, URL validation, upstream forwarding |
| `api/contract.php` | **Generated** from `src/ope/web_contract.py` — never edit by hand |
| `api/health.php` | Shell liveness + runtime identity |
| `api/status.php` | Capabilities, module/check counts, published report index |
| `api/audit.php` | Live-audit request → forwards to a configured API, else `runtime_unavailable` |
| `config.example.php` | Copy to `config.php` to point at a Python-capable OPE API |
| `assets/` | Copied at build time from `design/rawblock.css` and `web/assets/ope-render.js` |
| `reports/` | Static reports + `index.json` descriptor list |

## Two runtimes, one interface

| | `hostinger_shared` (default) | `python` (API configured) |
| --- | --- | --- |
| Command Center UI | ✅ | ✅ |
| Render uploaded report JSON | ✅ | ✅ |
| Published static reports | ✅ | ✅ |
| **Live audit** | ❌ `runtime_unavailable` | ✅ canonical result |

Creating `config.php` with `OPE_API_BASE` flips the deployment to live mode.
**The front-end does not change** — that is the point of the contract.

## Security notes

- PHP **never fetches a user-supplied URL**. The only outbound request possible
  is to the operator-configured `OPE_API_BASE`, so no SSRF is introduced here.
  Target URLs are validated locally as defence in depth (scheme, credentials,
  control characters, private/loopback/link-local/CGNAT literals) and validated
  again by the canonical Python validator upstream.
- Request bodies are capped (8 KB), JSON depth-limited, and a JSON content type
  is required — which is what CSRF protection means for a stateless, cookie-free,
  non-mutating API (there is no session to ride).
- No `eval`, no shell execution, no dynamic includes, no user-controlled file
  writes. Output is escaped with `htmlspecialchars` server-side and the shared
  renderer escapes every interpolated value client-side.
- `config.php`, `config.example.php`, `_`-prefixed includes, and any
  `.py/.toml/.md/.log/...` file are denied over HTTP by `.htaccess`.

## Publishing a report

Reports are rendered by the **canonical Python reporter**, then uploaded:

```bash
ope audit https://example.com --html example.report.html
```

Upload to `reports/`, then add a descriptor to `reports/index.json`:

```json
{ "reports": [
  { "file": "example.report.html", "target": "https://example.com",
    "generated_at": "2026-09-15T12:00:00Z", "engine_version": "1.5.0" }
] }
```

Full instructions: [`docs/deployment/hostinger-shared.md`](../../docs/deployment/hostinger-shared.md).
