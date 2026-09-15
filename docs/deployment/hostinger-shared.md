# Deploying OPE on Hostinger shared hosting

How to put the OMNI-Presence-Engine Command Center on a Hostinger Premium shared
hosting plan (target hostname: `ope.sumitdhariyal.in`), what works there, what
does not, and how to upgrade to live audits later without redesigning anything.

---

## 1. Architecture

Hostinger is a **presentation/deployment layer**. The brain never moves.

```
                      CANONICAL OPE ENGINE
                    (Python — source of truth)
       audit() → normalize_result() → dependency cascade
              → root causes → scoring → planner
                              │
              ┌───────────────┴───────────────┐
              │                               │
       CLI / local dashboard          Future OPE API
       (ope audit, ope dashboard)     (VPS / container)
              │                               │
              │ writes canonical              │ ope-web-v1
              │ report JSON / HTML            │ envelope
              ↓                               ↓
        ┌─────────────────────────────────────────────┐
        │   HOSTINGER SHARED  (Apache + PHP, static)  │
        │   index.php · api/*.php · assets · reports  │
        │   renders canonical results — never derives │
        └─────────────────────────────────────────────┘
```

The PHP shell contains **no** audit logic, scoring, dependency graph or
root-cause analysis. Those exist only in Python and are never duplicated.

---

## 2. What works on Hostinger / what does not

### ✅ Works

- The full RawBlock **Command Center UI** (`index.php`).
- **Rendering canonical report JSON** — uploaded in the browser, rendered
  client-side by the shared canonical renderer.
- **Published static reports** produced by the canonical Python reporter
  (`ope audit --html`), listed from `reports/index.json`.
- **API shell**: `/api/health`, `/api/status`, `/api/audit` speaking the
  `ope-web-v1` envelope.
- **Health/status/runtime reporting**, module and check counts read from the
  canonical registry at build time.

### ❌ Does not work (and is never faked)

- A **long-running Python OPE server** (`ope dashboard`) — shared hosting has no
  Python runtime, no daemons, no arbitrary ports.
- A **live audit executed on Hostinger**. `/api/audit` returns
  `runtime_unavailable`; it never invents a score, finding or recommendation.
- Browser-based performance auditing and PDF/PNG export (need Playwright).

> The engine is healthy — only this hosting runtime lacks Python execution. The
> UI says exactly that, without alarm language.

---

## 3. Build the package

```bash
git clone https://github.com/digitalhulk/OMNI-Presence-Engine.git
cd OMNI-Presence-Engine
python3 -m pip install -e .
python3 scripts/build_hostinger.py --zip
```

Produces:

- `dist/hostinger/` — the complete package
- `dist/ope-hostinger.zip` — the same, zipped for File Manager upload

The build copies `design/rawblock.css` and `web/assets/ope-render.js` and
generates `api/contract.php` from `src/ope/web_contract.py`, so the deployed
shell can never drift from the engine contract.

---

## 4. Upload (File Manager or FTP — no SSH needed)

Requirements: **PHP 8.0+** (8.1+ recommended), Apache with `mod_rewrite` and
`mod_headers` (both standard on Hostinger). **No database. No environment
variables. No Composer.**

### Which directory is public

For a subdomain `ope.sumitdhariyal.in`, Hostinger serves:

```
/home/uXXXXXXXXX/domains/sumitdhariyal.in/public_html/ope/
```

(For an addon domain it is `.../domains/<domain>/public_html/`.) That directory
is the **public root** — upload the *contents* of `dist/hostinger/` into it, not
the folder itself.

### Steps — File Manager

1. hPanel → **Websites** → your domain → **File Manager**.
2. Navigate to the subdomain's `public_html` directory (above).
3. Upload `dist/ope-hostinger.zip`.
4. Right-click → **Extract** into the current directory.
5. Delete the zip.
6. Confirm `index.php`, `.htaccess`, `api/`, `assets/`, `reports/` sit at the
   root — **not** inside a nested `hostinger/` folder.
7. `.htaccess` starts with a dot; enable **Show hidden files** in File Manager if
   you cannot see it. It must be present or the hardening and HTTPS redirect are
   not applied.

### Steps — FTP

```
Host: ftp://<your-domain>        (credentials: hPanel → Files → FTP Accounts)
Upload dist/hostinger/*  →  /domains/sumitdhariyal.in/public_html/ope/
```

Upload in **binary** mode and make sure hidden files (`.htaccess`) are included.

### Permissions

Defaults are correct: directories `755`, files `644`. Nothing needs to be
writable — the shell never writes to disk.

---

## 5. Configure the subdomain

In hPanel → **Domains → Subdomains**, create `ope` under `sumitdhariyal.in`, then
point the document root at the directory you uploaded into. Enable **SSL**
(hPanel → Security → SSL) so the `.htaccess` HTTPS redirect and HSTS header are
meaningful.

DNS is managed in hPanel; this repository makes no DNS changes.

---

## 6. Test the deployment

```bash
# 1. Shell is alive and declares its runtime
curl -s https://ope.sumitdhariyal.in/api/health | python3 -m json.tool

# 2. Capabilities + canonical module/check counts
curl -s https://ope.sumitdhariyal.in/api/status | python3 -m json.tool

# 3. Live audit request → honest runtime state (HTTP 503), never a fake result
curl -s -X POST https://ope.sumitdhariyal.in/api/audit \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://example.com"}' | python3 -m json.tool

# 4. Hardening: these must NOT be readable
curl -sI https://ope.sumitdhariyal.in/config.php        # expect 403
curl -sI https://ope.sumitdhariyal.in/api/_bootstrap.php # expect 403
```

Expected `/api/audit` body on shared hosting:

```json
{
  "status": "runtime_unavailable",
  "runtime": "hostinger_shared",
  "engine": "python",
  "live_execution": false,
  "message": "Live OPE execution requires a Python-capable runtime.",
  "web_contract": "ope-web-v1",
  "target": "https://example.com"
}
```

In the browser, open `https://ope.sumitdhariyal.in/` and confirm: the runtime
banner reads **LIVE ENGINE — UNAVAILABLE ON THIS RUNTIME**, the URL form submits
to a runtime panel (not a score), and uploading a canonical report JSON renders a
full report.

---

## 7. Publishing real reports

Reports are always produced by the canonical engine, then uploaded:

```bash
ope audit https://example.com --html  example.report.html
ope audit https://example.com --json  > example.report.json
```

1. Upload `example.report.html` into `reports/`.
2. Add a descriptor to `reports/index.json`:

```json
{ "reports": [
  { "file": "example.report.html",
    "target": "https://example.com",
    "generated_at": "2026-09-15T12:00:00Z",
    "engine_version": "1.5.0" }
] }
```

It then appears under **Published reports** and at
`/report/example.report` (clean permalink).

> `web/sample-report.js` is **development fixture data** (a real result shape
> audited against a fixed example page). It is deliberately **not** included in
> the deployment package, so production can never present it as a real audit.

---

## 8. Upgrade path → live audits

```
Hostinger (this package)
        │  config.php: OPE_API_BASE
        ↓
Future OPE API  (VPS / container / any Python host)
        ↓
CANONICAL PYTHON OPE ENGINE
```

When a Python-capable API exists, create `config.php` next to `index.php`:

```php
<?php
declare(strict_types=1);
define('OPE_API_BASE', 'https://ope-api.example.com');
define('OPE_API_TOKEN', 'optional-bearer-token');
```

The shell then reports `runtime: python`, `live_execution: true`, forwards
`POST /api/audit` to `<base>/api/audit`, and passes the canonical envelope
through untouched. **No front-end change is required** — same HTML, same
renderer, same contract.

The API must answer with the `ope-web-v1` envelope from
`src/ope/web_contract.py`:

```json
{ "status": "success", "runtime": "python", "engine": "python",
  "engine_version": "1.5.0", "live_execution": true,
  "target": "https://example.com", "web_contract": "ope-web-v1",
  "result": { "…canonical normalized result…" } }
```

`result` is the canonical `normalize_result()` output, verbatim — there is no
second result format.

---

## 9. Security summary

| Control | Where |
| --- | --- |
| HTTPS redirect + HSTS | `.htaccess` |
| CSP, nosniff, frame/referrer/permissions policy | `.htaccess` + API headers |
| No SSRF via PHP (never fetches a user URL) | `api/_bootstrap.php` |
| URL validation (scheme, creds, control chars, private/loopback/CGNAT) | `ope_validate_target_url()` |
| Canonical SSRF + DNS-pinning validation | Python engine, unchanged |
| Body size cap (8 KB), JSON depth cap, JSON content type required | `ope_read_json_body()` |
| Source/config/internals not web-readable | `.htaccess` deny rules |
| XSS-safe output | `htmlspecialchars` (PHP) + `esc()` (renderer) |
| No eval / shell / dynamic include / user file writes | by construction |

Secrets live only in `config.php`, which is never committed and never served.
