<?php
/**
 * OPE Hostinger shell — operator configuration EXAMPLE.
 *
 * Copy to `config.php` next to index.php and edit. `config.php` is blocked from
 * HTTP access by .htaccess and must NEVER be committed to git.
 *
 * With no config.php the shell runs in HOSTINGER_SHARED mode and honestly
 * reports `runtime_unavailable` for live audits. That is a valid, complete
 * deployment — the static Command Center and published reports all work.
 *
 * Define these only once a Python-capable OPE API exists (VPS, container, or any
 * host that can run `ope`). Pointing at one flips this deployment to live mode
 * with no front-end changes.
 */

declare(strict_types=1);

// Base URL of a Python-capable OPE API. The shell POSTs to <base>/api/audit.
// Must be absolute http(s). HTTPS strongly recommended — the shell verifies TLS
// and does not follow redirects.
// define('OPE_API_BASE', 'https://ope-api.example.com');

// Optional bearer token sent as `Authorization: Bearer <token>` to that API.
// Keep real tokens out of version control.
// define('OPE_API_TOKEN', 'replace-me');
