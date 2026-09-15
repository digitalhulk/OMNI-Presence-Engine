"""Read-only network diagnostics for the audit transport.

Answers one operational question: when ``ope audit <url>`` cannot reach a site,
is the *target* at fault, or is *this machine's* network/proxy blocking
outbound egress? A proxy that answers ``403`` to a CONNECT tunnel is an
environment block, not a website failure, and conflating the two produces a
misleading audit.

This module is a thin probe, never a second engine:

- It reuses the exact SSRF validation (:func:`ope.url.validate_target`),
  proxy detection (:func:`ope.net.uses_proxy`), transport
  (:func:`ope.audit._request`), and the canonical robots/sitemap fetchers.
  It performs GET/HEAD reads only, honours the same timeouts and caps, and
  weakens no TLS or SSRF control.
- It runs *no* audit checks, computes *no* score, and produces *no* findings.
  Its whole output is a per-layer connectivity report plus a classification.

:func:`classify_network_error` maps a raw transport exception to an actionable
category (and never prints proxy credentials). :func:`diagnose` walks the
request path layer by layer and returns a structured result whose ``verdict``
separates ``ENVIRONMENT_BLOCK`` / ``WEBSITE_UNREACHABLE`` / ``SSRF_BLOCKED`` /
``INVALID_URL`` / ``REACHABLE`` so an operator (or the CLI) can tell an
environment limitation apart from a real site problem.
"""
from __future__ import annotations

import os
import socket
import ssl
import urllib.error
import urllib.parse
from typing import Any

from . import USER_AGENT
from .url import TargetStatus, validate_target

# Category -> the layer of the network stack it belongs to. Categories are the
# stable contract other code (CLI, tests) keys on; messages may be refined.
NETWORK_CATEGORIES = (
    "INVALID_URL",        # the URL is malformed or an unsupported scheme
    "SSRF_BLOCKED",       # target resolves to a restricted address (policy)
    "DNS_FAILURE",        # the hostname does not resolve from this machine
    "PROXY_BLOCK",        # a configured egress proxy refused the connection
    "CONNECTION_REFUSED", # TCP was actively refused by the host
    "NETWORK_UNREACHABLE",# no route to the host/network from this machine
    "TIMEOUT",            # the connection or read timed out
    "TLS_ERROR",          # the TLS handshake / certificate validation failed
    "TRANSPORT_ERROR",    # any other transport-level failure
)

# Verdicts separate *where* the block lives. ENVIRONMENT_BLOCK must never be
# reported as a website failure, and vice versa.
_ENVIRONMENT_CATEGORIES = frozenset({"PROXY_BLOCK", "NETWORK_UNREACHABLE"})
_WEBSITE_CATEGORIES = frozenset({"DNS_FAILURE", "CONNECTION_REFUSED", "TIMEOUT", "TLS_ERROR"})


def _proxy_context(url: str) -> dict[str, Any]:
    """Report proxy applicability for *url* by env-var NAME only.

    Proxy URLs can embed credentials, so their *values* are never returned —
    only which standard variables are set and whether a proxy applies to this
    request. Import is local to avoid a circular import with :mod:`ope.net`.
    """
    from .net import uses_proxy

    present = [name for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                                 "http_proxy", "https_proxy", "all_proxy", "no_proxy")
               if os.environ.get(name)]
    try:
        applies = uses_proxy(url)
    except Exception:
        applies = False
    return {
        "proxy_env_vars_set": present,           # names only, never values
        "proxy_applies_to_target": applies,
        "mode": "proxied" if applies else "direct",
    }


def classify_network_error(exc: BaseException, *, proxied: bool = False) -> tuple[str, str]:
    """Map a transport exception to ``(category, actionable_message)``.

    ``category`` is one of :data:`NETWORK_CATEGORIES`. The message is
    operator-facing and actionable; the original exception text is preserved in
    it so the underlying cause is never lost. ``proxied`` says whether an egress
    proxy applied to the request, which disambiguates a refused tunnel (proxy
    policy) from a refused origin connection.
    """
    cause = exc
    # urllib wraps the real socket/ssl error in URLError.reason; unwrap it so we
    # classify the underlying failure rather than the wrapper.
    if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
        reason = exc.reason
        if isinstance(reason, BaseException):
            cause = reason
        else:
            cause = exc  # reason is a plain string
    text = str(getattr(cause, "reason", cause) or cause)
    low = text.lower()

    # SSRF / validation failures surface as ValueError from validate_url_strict.
    if isinstance(exc, ValueError):
        if "restricted address" in low:
            return "SSRF_BLOCKED", f"Target resolves to a restricted (private/loopback/metadata) address and was blocked by OPE's SSRF policy: {text}"
        if "dns resolution failed" in low or "no addresses" in low:
            return "DNS_FAILURE", f"Hostname did not resolve from this machine: {text}"
        return "INVALID_URL", f"URL rejected before any connection was attempted: {text}"

    # A CONNECT tunnel refusal from an egress proxy (e.g. '403 Forbidden').
    if "tunnel connection failed" in low or ("proxy" in low and ("403" in low or "forbidden" in low or "denied" in low)):
        return "PROXY_BLOCK", (
            "Outbound HTTPS was refused by a configured egress proxy "
            f"(CONNECT tunnel rejected): {text}. This is an environment/network "
            "restriction on this machine, not a fault of the target website."
        )

    if isinstance(cause, socket.gaierror) or "name or service not known" in low or "nodename nor servname" in low or "temporary failure in name resolution" in low:
        return "DNS_FAILURE", f"DNS resolution failed for the target host: {text}"
    if isinstance(cause, (ssl.SSLError, ssl.SSLCertVerificationError)) or "ssl" in low or "certificate" in low:
        return "TLS_ERROR", f"TLS handshake or certificate validation failed: {text}"
    if isinstance(cause, ConnectionRefusedError) or "connection refused" in low:
        return "CONNECTION_REFUSED", f"The host actively refused the TCP connection: {text}"
    if isinstance(cause, (TimeoutError, socket.timeout)) or "timed out" in low or "timeout" in low:
        return "TIMEOUT", f"The connection or read timed out: {text}"
    if "network is unreachable" in low or "no route to host" in low or "unreachable" in low:
        return "NETWORK_UNREACHABLE", (
            f"No route to the target from this machine: {text}. This is an "
            "environment/network restriction, not a website fault."
        )
    if proxied and isinstance(cause, OSError):
        # An OSError on a proxied request that did not match a clearer rule is
        # most likely the proxy layer refusing egress.
        return "PROXY_BLOCK", (
            "Outbound request failed while an egress proxy was in effect: "
            f"{text}. Treated as an environment/network restriction."
        )
    return "TRANSPORT_ERROR", f"Transport-level failure reaching the target: {text}"


_VALIDATION_SIGNATURES = (
    "restricted address", "dns resolution failed", "no addresses",
    "unsupported scheme", "url has no hostname", "url exceeds",
    "more than", "query parameters",
)


def looks_like_network_error(exc: BaseException) -> bool:
    """True when *exc* is a transport/validation failure worth reclassifying.

    Lets a caller (the CLI) apply :func:`classify_network_error` only to real
    network conditions, and fall back to the raw message for unrelated bugs
    (e.g. a reporting error) so those are never mislabelled as a transport
    problem.
    """
    if isinstance(exc, (urllib.error.URLError, OSError, ssl.SSLError,
                        socket.timeout, TimeoutError, socket.gaierror)):
        return True
    if isinstance(exc, ValueError):
        low = str(exc).lower()
        return any(sig in low for sig in _VALIDATION_SIGNATURES)
    return False


def _verdict_for(category: str, *, proxied: bool) -> str:
    if category == "SSRF_BLOCKED":
        return "SSRF_BLOCKED"
    if category == "INVALID_URL":
        return "INVALID_URL"
    if category in _ENVIRONMENT_CATEGORIES:
        return "ENVIRONMENT_BLOCK"
    if category == "DNS_FAILURE" and proxied:
        # With a proxy in effect the client does not resolve DNS itself; a DNS
        # failure here points at the environment's resolver/proxy, not the site.
        return "ENVIRONMENT_BLOCK"
    if category in _WEBSITE_CATEGORIES:
        return "WEBSITE_UNREACHABLE"
    return "WEBSITE_UNREACHABLE"


def diagnose(url: str, *, timeout: int = 15) -> dict[str, Any]:
    """Run a layered, read-only connectivity probe against *url*.

    Returns a structured report with a per-layer breakdown and a top-level
    ``verdict``. Never raises for a network condition — a failure at any layer
    is captured and classified. Only ``GET``/``HEAD`` reads are performed,
    through the same SSRF-safe transport the auditor uses.
    """
    report: dict[str, Any] = {
        "target": url,
        "verdict": None,
        "category": None,
        "detail": None,
        "layers": {},
    }
    layers = report["layers"]

    # Layer 1 — URL validation + DNS + SSRF policy (no bytes sent yet).
    validation = validate_target(url)
    normalized = validation.normalized or url
    layers["validation"] = {
        "status": validation.status.value,
        "normalized_url": validation.normalized or None,
        "resolved_addresses": list(validation.addresses),
        "reason": validation.reason or None,
    }
    proxy = _proxy_context(normalized if validation.normalized else url)
    layers["proxy"] = proxy
    proxied = bool(proxy["proxy_applies_to_target"])

    if validation.status != TargetStatus.VALID:
        # Map the validation status to a transport category via the same
        # classifier, so INVALID/BLOCKED/DNS are reported consistently.
        category, detail = classify_network_error(ValueError(validation.reason or validation.status.value), proxied=proxied)
        report["category"], report["detail"] = category, detail
        report["verdict"] = _verdict_for(category, proxied=proxied)
        return report

    parsed = urllib.parse.urlparse(normalized)
    layers["dns"] = {"host": parsed.hostname, "addresses": list(validation.addresses), "resolved": bool(validation.addresses)}

    # Layer 2 — HTTP fetch through the canonical transport. _request returns a
    # Response even for 4xx/5xx (a real HTTP answer = the site is reachable) and
    # raises only on a transport failure.
    from .audit import _request

    try:
        response = _request(normalized, timeout=timeout)
        layers["http"] = {
            "reachable": True,
            "status": response.status,
            "final_url": response.final_url,
            "redirected": response.final_url.rstrip("/") != normalized.rstrip("/"),
            "dns_ms": response.dns_ms,
            "ttfb_ms": response.ttfb_ms,
        }
        report["verdict"] = "REACHABLE"
        report["category"] = "OK"
        report["detail"] = f"HTTP {response.status} from {response.final_url}"
    except Exception as exc:  # transport failure — classify, do not raise
        category, detail = classify_network_error(exc, proxied=proxied)
        layers["http"] = {"reachable": False, "category": category, "error": detail}
        report["category"], report["detail"] = category, detail
        report["verdict"] = _verdict_for(category, proxied=proxied)
        # If the origin itself is unreachable, robots/sitemap will be too; skip
        # them to avoid repeating the same failure noise.
        return report

    # Layer 3 — robots.txt reachability (canonical fetcher; SSRF-safe).
    from .crawler import fetch_robots

    robots = fetch_robots(normalized, timeout=min(timeout, 10))
    layers["robots"] = {
        "url": robots.get("url"),
        "status": robots.get("status"),
        "reachable": robots.get("status") is not None and robots.get("error") is None,
        "error": robots.get("error"),
        "declared_sitemaps": robots.get("sitemaps", []),
    }

    # Layer 4 — sitemap reachability. Prefer a robots-declared sitemap, else the
    # conventional /sitemap.xml. A missing sitemap is not an error, only a fact.
    sitemap_target = None
    declared = robots.get("sitemaps") or []
    if declared:
        sitemap_target = declared[0]
    else:
        sitemap_target = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/sitemap.xml", "", "", ""))
    layers["sitemap"] = _probe_sitemap(sitemap_target, timeout=min(timeout, 10))

    return report


def _probe_sitemap(url: str, *, timeout: int) -> dict[str, Any]:
    """Reachability-only probe of a sitemap URL (does not parse the document)."""
    from .net import open_url

    try:
        with open_url(url, timeout=timeout, headers={"User-Agent": USER_AGENT}) as resp:
            # Read a bounded probe only — reachability, not the sitemap body.
            resp.read(1)
            return {"url": url, "status": resp.status, "reachable": True, "error": None}
    except Exception as exc:
        category, _ = classify_network_error(exc)
        return {"url": url, "status": None, "reachable": False, "error": str(exc), "category": category}
