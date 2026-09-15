<?php
/**
 * GET /api/health — is this deployment serving, and what runtime is it?
 *
 * Reports the shell's own liveness only. It deliberately makes no claim about
 * the canonical engine's health: a healthy shell on a Python-less runtime is
 * the normal, expected state for shared hosting.
 */

declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

ope_require_method('GET', 'HEAD');

$runtime = ope_runtime();
ope_json([
    'status' => 'ok',
    'web_contract' => OPE_WEB_CONTRACT_VERSION,
    'engine' => OPE_ENGINE,
    'engine_version' => OPE_ENGINE_VERSION,
    'runtime' => $runtime,
    'live_execution' => ope_has_live_runtime(),
    'shell' => 'hostinger-php',
    'php_version' => PHP_MAJOR_VERSION . '.' . PHP_MINOR_VERSION,
]);
