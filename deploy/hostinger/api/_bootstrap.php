<?php
/**
 * Shared bootstrap for the OPE Hostinger API shell.
 *
 * This shell is a TRANSPORT ADAPTER, not an engine. It contains no audit logic,
 * no scoring, no dependency graph and no root-cause analysis — those live only
 * in the canonical Python engine. Its entire job is to answer honestly about
 * which runtime it is on, and (when a Python-capable OPE API is configured) to
 * forward a request to it and pass the canonical result straight through.
 *
 * SSRF: this file never fetches a user-supplied URL. The only outbound request
 * the shell can make is to OPE_API_BASE, an operator-configured constant. The
 * audited URL travels as JSON *data* to that trusted endpoint, which performs
 * its own canonical validation (ope.url.validate_url_strict) before fetching.
 * A user therefore cannot steer a request from this server to a target of their
 * choosing. The local validation below is defence in depth, not the boundary.
 *
 * Requires PHP >= 8.0.
 */

declare(strict_types=1);

require_once __DIR__ . '/contract.php';

/** Hard cap on an accepted request body. Keeps a hostile payload cheap. */
const OPE_MAX_BODY_BYTES = 8192;
/** Hard cap on an accepted target URL (mirrors the engine's own limit). */
const OPE_MAX_URL_LENGTH = 8192;
/** Max nesting accepted when decoding a request body. */
const OPE_JSON_MAX_DEPTH = 16;

/**
 * Load operator configuration if present.
 *
 * config.php is NEVER committed (see .htaccess + README) and may define:
 *   OPE_API_BASE  — base URL of a Python-capable OPE API, e.g. https://api.example.com
 *   OPE_API_TOKEN — optional bearer token for that API
 * With no config, the shell reports runtime_unavailable, which is the correct
 * and honest state for plain shared hosting.
 */
function ope_load_config(): void
{
    $config = dirname(__DIR__) . '/config.php';
    if (is_file($config)) {
        require_once $config;
    }
}

/** Configured upstream Python API base, or '' when none is configured. */
function ope_api_base(): string
{
    ope_load_config();
    if (!defined('OPE_API_BASE')) {
        return '';
    }
    $base = trim((string) constant('OPE_API_BASE'));
    // Only an absolute http(s) endpoint is usable; anything else is ignored
    // rather than guessed at.
    if ($base === '' || !preg_match('#^https?://#i', $base)) {
        return '';
    }
    return rtrim($base, '/');
}

/** True when an upstream Python engine is configured for this deployment. */
function ope_has_live_runtime(): bool
{
    return ope_api_base() !== '';
}

/** The runtime identifier this deployment is currently operating as. */
function ope_runtime(): string
{
    return ope_has_live_runtime() ? OPE_RUNTIME_PYTHON : OPE_RUNTIME_HOSTINGER_SHARED;
}

/** Send hardening headers common to every endpoint. */
function ope_send_security_headers(): void
{
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    header('Cache-Control: no-store, max-age=0');
    // API responses are data, never a document: forbid any active content.
    header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");
}

/**
 * Emit a JSON payload and stop.
 *
 * Encoding is strict: invalid UTF-8 or a non-encodable value produces a 500
 * with a fixed body rather than a truncated/partial document.
 */
function ope_json(array $payload, int $status = 200): void
{
    ope_send_security_headers();
    header('Content-Type: application/json; charset=utf-8');
    $body = json_encode(
        $payload,
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE
    );
    if ($body === false) {
        http_response_code(500);
        echo '{"status":"error","engine":"python","live_execution":false,'
            . '"message":"Response could not be serialised."}';
        return;
    }
    http_response_code($status);
    echo $body;
}

/** Reject any method other than those allowed, with a correct Allow header. */
function ope_require_method(string ...$allowed): void
{
    $method = strtoupper((string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'));
    if (in_array($method, $allowed, true)) {
        return;
    }
    header('Allow: ' . implode(', ', $allowed));
    ope_json(ope_invalid_request_payload('Method not allowed.', ope_runtime()), 405);
    exit;
}

/**
 * Read and decode a JSON request body, enforcing the size cap.
 *
 * Returns null when the body is missing, oversized, or not a JSON object.
 * Requiring a JSON content type also means a plain HTML form cannot drive this
 * endpoint cross-site, which is what CSRF protection means for a stateless,
 * cookie-free, non-mutating API like this one (there is no session to ride).
 */
function ope_read_json_body(): ?array
{
    $type = strtolower((string) ($_SERVER['CONTENT_TYPE'] ?? ''));
    if ($type !== '' && !str_contains($type, 'application/json')) {
        return null;
    }
    $length = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
    if ($length > OPE_MAX_BODY_BYTES) {
        return null;
    }
    $raw = file_get_contents('php://input', false, null, 0, OPE_MAX_BODY_BYTES + 1);
    if ($raw === false || $raw === '' || strlen($raw) > OPE_MAX_BODY_BYTES) {
        return null;
    }
    try {
        $decoded = json_decode($raw, true, OPE_JSON_MAX_DEPTH, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        return null;
    }
    return is_array($decoded) ? $decoded : null;
}

/**
 * Validate a target URL for shape and obvious SSRF markers.
 *
 * Defence in depth only — the canonical Python validator remains the authority
 * and runs again upstream. Returns the trimmed URL, or null with $reason set.
 *
 * Deliberately conservative: http/https only, no embedded credentials, no
 * fragment-smuggling, and any host that is already a private/loopback/
 * link-local IP literal is refused outright. Hostnames are NOT resolved here
 * (shared hosting DNS is not a trustworthy SSRF boundary and resolution belongs
 * to the engine, which pins what it validates).
 */
function ope_validate_target_url(mixed $value, ?string &$reason = null): ?string
{
    $reason = null;
    if (!is_string($value)) {
        $reason = 'Target URL must be a string.';
        return null;
    }
    $url = trim($value);
    if ($url === '') {
        $reason = 'Target URL is required.';
        return null;
    }
    if (strlen($url) > OPE_MAX_URL_LENGTH) {
        $reason = 'Target URL exceeds ' . OPE_MAX_URL_LENGTH . ' characters.';
        return null;
    }
    // Control characters (incl. CR/LF) would enable header/request smuggling.
    if (preg_match('/[\x00-\x1F\x7F]/', $url) === 1) {
        $reason = 'Target URL contains control characters.';
        return null;
    }
    $parts = parse_url($url);
    if ($parts === false || !isset($parts['scheme'], $parts['host'])) {
        $reason = 'Target URL must be an absolute http(s) URL.';
        return null;
    }
    $scheme = strtolower((string) $parts['scheme']);
    if ($scheme !== 'http' && $scheme !== 'https') {
        $reason = 'Unsupported scheme: ' . $scheme;
        return null;
    }
    if (isset($parts['user']) || isset($parts['pass'])) {
        $reason = 'Credentials in the URL are not accepted.';
        return null;
    }
    $host = strtolower(trim((string) $parts['host'], '[]'));
    if ($host === '') {
        $reason = 'Target URL has no host.';
        return null;
    }
    if (ope_host_is_restricted($host)) {
        $reason = 'Target resolves to a restricted address and was refused.';
        return null;
    }
    return $url;
}

/**
 * True when $host is an IP literal in a range OPE must never be pointed at,
 * or an obviously local name. Covers loopback, RFC1918, link-local (including
 * cloud metadata 169.254.169.254), CGNAT, and IPv6 loopback/ULA/link-local.
 */
function ope_host_is_restricted(string $host): bool
{
    if ($host === 'localhost' || str_ends_with($host, '.localhost') || str_ends_with($host, '.local')) {
        return true;
    }
    if (filter_var($host, FILTER_VALIDATE_IP) === false) {
        return false; // a hostname — the engine validates and pins resolution
    }
    // Any IP literal that is not a global unicast address is refused.
    $global = filter_var(
        $host,
        FILTER_VALIDATE_IP,
        FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE
    );
    if ($global === false) {
        return true;
    }
    // FILTER_FLAG_NO_RES_RANGE misses CGNAT (100.64.0.0/10); refuse it too.
    if (filter_var($host, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) !== false) {
        $long = ip2long($host);
        if ($long !== false && ($long & 0xFFC00000) === (ip2long('100.64.0.0') & 0xFFC00000)) {
            return true;
        }
    }
    return false;
}

/**
 * Forward an audit request to the configured Python OPE API and return its
 * decoded canonical envelope, or null on any transport/decode failure.
 *
 * Only ever contacts OPE_API_BASE. Redirects are NOT followed, so a compromised
 * or misconfigured upstream cannot bounce this server at an internal address.
 */
function ope_forward_audit(string $url, ?string &$error = null): ?array
{
    $error = null;
    $base = ope_api_base();
    if ($base === '') {
        $error = 'No upstream OPE API is configured.';
        return null;
    }
    $endpoint = $base . '/api/audit';
    $body = json_encode(['url' => $url], JSON_UNESCAPED_SLASHES);
    if ($body === false) {
        $error = 'Request could not be serialised.';
        return null;
    }
    $headers = ['Content-Type: application/json', 'Accept: application/json'];
    ope_load_config();
    if (defined('OPE_API_TOKEN') && trim((string) constant('OPE_API_TOKEN')) !== '') {
        $headers[] = 'Authorization: Bearer ' . trim((string) constant('OPE_API_TOKEN'));
    }

    if (function_exists('curl_init')) {
        $ch = curl_init($endpoint);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $body,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_TIMEOUT => 120,
            CURLOPT_CONNECTTIMEOUT => 10,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
        ]);
        $raw = curl_exec($ch);
        if ($raw === false) {
            $error = 'Upstream OPE API unreachable: ' . curl_error($ch);
            curl_close($ch);
            return null;
        }
        curl_close($ch);
    } else {
        $context = stream_context_create(['http' => [
            'method' => 'POST',
            'header' => implode("\r\n", $headers),
            'content' => $body,
            'timeout' => 120,
            'follow_location' => 0,
            'ignore_errors' => true,
        ], 'ssl' => ['verify_peer' => true, 'verify_peer_name' => true]]);
        $raw = @file_get_contents($endpoint, false, $context);
        if ($raw === false) {
            $error = 'Upstream OPE API unreachable.';
            return null;
        }
    }

    try {
        $decoded = json_decode((string) $raw, true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        $error = 'Upstream OPE API returned a malformed response.';
        return null;
    }
    if (!is_array($decoded)) {
        $error = 'Upstream OPE API returned an unexpected response.';
        return null;
    }
    return $decoded;
}
