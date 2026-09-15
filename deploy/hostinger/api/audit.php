<?php
/**
 * POST /api/audit — request a live audit.
 *
 * This endpoint NEVER performs an audit itself. There is no PHP reimplementation
 * of the engine anywhere in this shell. It has exactly two honest outcomes:
 *
 *   1. No Python runtime configured  -> 503 runtime_unavailable.
 *      A truthful "this hosting runtime cannot execute the engine", carrying no
 *      result, no score and no findings, so it can never be mistaken for a real
 *      audit of the target.
 *   2. An OPE API is configured      -> forward, and pass the canonical envelope
 *      straight through unmodified.
 *
 * Request:  {"url": "https://example.com"}
 * Response: the canonical ope-web-v1 envelope (see src/ope/web_contract.py).
 */

declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

ope_require_method('POST');

$runtime = ope_runtime();
$body = ope_read_json_body();
if ($body === null) {
    ope_json(ope_invalid_request_payload(
        'Send a JSON body of the form {"url": "https://example.com"} (max '
        . OPE_MAX_BODY_BYTES . ' bytes) with Content-Type: application/json.',
        $runtime
    ), 400);
    exit;
}

$reason = null;
$url = ope_validate_target_url($body['url'] ?? null, $reason);
if ($url === null) {
    ope_json(ope_invalid_request_payload((string) $reason, $runtime), 400);
    exit;
}

// No Python-capable runtime: say so, plainly, and stop. 503 (not 500) because
// nothing is broken — the capability is simply absent on this runtime.
if (!ope_has_live_runtime()) {
    ope_json(ope_runtime_unavailable_payload(OPE_RUNTIME_HOSTINGER_SHARED, $url), 503);
    exit;
}

$error = null;
$upstream = ope_forward_audit($url, $error);
if ($upstream === null) {
    // The upstream engine is configured but unreachable/unusable. That is an
    // upstream transport problem, and it is reported as such — it is neither a
    // finding about the target site nor a fabricated result.
    ope_json([
        'status' => OPE_STATUS_ERROR,
        'web_contract' => OPE_WEB_CONTRACT_VERSION,
        'engine' => OPE_ENGINE,
        'runtime' => $runtime,
        'live_execution' => false,
        'target' => $url,
        'message' => (string) $error,
    ], 502);
    exit;
}

// Pass the canonical envelope through untouched: the engine owns the result
// format and this shell must not reshape, enrich, or summarise it.
$status = (($upstream['status'] ?? '') === OPE_STATUS_SUCCESS) ? 200 : 502;
ope_json($upstream, $status);
