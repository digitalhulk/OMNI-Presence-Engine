"""SSRF-safe HTTP connections that pin a validated DNS resolution.

The audit path validates a target with :func:`ope.url.validate_url_strict`
before connecting, but stdlib ``urllib`` re-resolves the hostname when it
opens the socket. A DNS-rebinding attacker with a low-TTL record can answer
the validation query with a public address and the connection query with a
private one, defeating the check. This module closes that TOCTOU window for
**direct** connections: the socket connects to an address that is resolved
*and validated in the same step*, so what was validated is exactly what is
connected to.

When an egress proxy is configured for the request (``HTTP(S)_PROXY``), the
proxy performs resolution and enforces egress policy, so pinning is skipped
and the request flows through the proxy unchanged — preserving proxy
semantics. TLS certificate validation and SNI, redirects, IPv4/IPv6, and
timeouts are all preserved.
"""
from __future__ import annotations

import http.client
import socket
import ssl
import urllib.parse
import urllib.request
from typing import Any

from .url import resolve_and_validate, validate_url_strict

MAX_REDIRECTS = 5


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect hop against the SSRF policy.

    ``max_redirections`` is set here (urllib reads it off the handler), and
    each hop's target is passed through ``validate_url_strict`` so a
    ``public -> 302 -> private`` chain is rejected. Shared by every fetch path
    (main page, robots, sitemap, subresources) so no path can follow a
    redirect with an unvalidated destination.
    """

    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> urllib.request.Request | None:
        safe = validate_url_strict(newurl)
        return super().redirect_request(req, fp, code, msg, headers, safe)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        addresses = resolve_and_validate(self.host)
        self.sock = socket.create_connection((addresses[0], self.port), self.timeout, self.source_address)  # type: ignore[attr-defined]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self) -> None:
        addresses = resolve_and_validate(self.host)
        sock = socket.create_connection((addresses[0], self.port), self.timeout, self.source_address)  # type: ignore[attr-defined]
        # SNI and certificate validation use the hostname, not the pinned IP.
        context: ssl.SSLContext = self._context  # type: ignore[attr-defined]
        self.sock = context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(_PinnedHTTPConnection, req)  # type: ignore[return-value]


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(  # type: ignore[return-value]
            _PinnedHTTPSConnection, req,
            context=self._context, check_hostname=self._check_hostname,  # type: ignore[attr-defined]
        )


def uses_proxy(url: str) -> bool:
    """True when a configured egress proxy applies to *url*'s scheme/host.

    When it does, the proxy resolves and enforces policy, so client-side IP
    pinning is skipped (and would otherwise wrongly validate the proxy's own
    address).
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    proxies = urllib.request.getproxies()
    if scheme not in proxies:
        return False
    host = parsed.hostname or ""
    try:
        return not urllib.request.proxy_bypass(host)
    except Exception:
        # If proxy-bypass detection fails, assume the proxy is in effect.
        return True


def build_opener(url: str, redirect_handler: urllib.request.BaseHandler, context: ssl.SSLContext) -> urllib.request.OpenerDirector:
    """Build an opener for *url*: IP-pinned for direct connections, proxy-aware otherwise.

    The returned opener keeps the given redirect handler (which re-validates
    every hop) and, for direct connections, replaces the HTTP(S) handlers
    with pinning variants. When a proxy applies, the standard handlers are
    used so the request tunnels through the proxy as before.
    """
    if uses_proxy(url):
        return urllib.request.build_opener(redirect_handler, urllib.request.HTTPSHandler(context=context))
    opener = urllib.request.build_opener(
        redirect_handler, _PinnedHTTPHandler(), _PinnedHTTPSHandler(context=context),
    )
    return opener


def open_url(url: str, *, timeout: int, headers: dict[str, str] | None = None) -> Any:
    """Open *url* through the SSRF-safe, redirect-revalidating, IP-pinned opener.

    The single entry point every non-`audit._request` fetch path uses (robots,
    sitemap, subresources): the initial URL is validated, each redirect hop is
    re-validated, and direct connections pin the validated resolution. Returns
    the raw response object (a context manager); the caller reads it (bounded).
    """
    safe = validate_url_strict(url)
    ctx = ssl.create_default_context()
    opener = build_opener(safe, SafeRedirectHandler(), ctx)
    request = urllib.request.Request(safe, headers=headers or {}, method="GET")
    return opener.open(request, timeout=max(1, min(timeout, 60)))
