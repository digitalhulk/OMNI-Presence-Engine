"""URL normalization, target validation, and crawl-scope enforcement."""
from __future__ import annotations

import ipaddress
import posixpath
import socket
import urllib.parse
from dataclasses import dataclass
from enum import Enum

_DEFAULT_PORTS = {"http": 80, "https": 443}
ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_URL_LENGTH = 8192
MAX_QUERY_PARAMS = 128
_PATH_SAFE = "/:@!$&'()*+,;=-._~"


class TargetStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class TargetValidation:
    url: str
    status: TargetStatus
    normalized: str
    reason: str = ""
    addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class CrawlScope:
    origin_scheme: str
    origin_host: str
    origin_port: int
    allow_subdomains: bool = False
    max_depth: int = 10
    max_pages: int = 200
    max_total_bytes: int = 50 * 1024 * 1024

    def in_scope(self, url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(normalize_url(url))
        except ValueError:
            return False
        if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
            return False
        host = parsed.hostname
        port = parsed.port or _DEFAULT_PORTS.get(parsed.scheme, 0)
        if parsed.scheme != self.origin_scheme or port != self.origin_port:
            return False
        if host == self.origin_host:
            return True
        return self.allow_subdomains and host.endswith("." + self.origin_host)


def normalize_url(url: str) -> str:
    """Canonicalize a URL for deduplication — deterministic, idempotent."""
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds {MAX_URL_LENGTH} characters")
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Unsupported scheme: {scheme or '(empty)'}")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError("URL has no hostname")
    port = parsed.port
    if port == _DEFAULT_PORTS.get(scheme):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = parsed.path or "/"
    path = urllib.parse.unquote(path)
    original_trailing = path.endswith("/") and len(path) > 1
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = "/" + path
    if original_trailing and not path.endswith("/"):
        path += "/"
    path = urllib.parse.quote(path, safe=_PATH_SAFE)
    query = parsed.query
    if query:
        params = urllib.parse.parse_qsl(query, keep_blank_values=True)
        if len(params) > MAX_QUERY_PARAMS:
            raise ValueError(f"URL has more than {MAX_QUERY_PARAMS} query parameters")
        params.sort()
        query = urllib.parse.urlencode(params)
    return urllib.parse.urlunparse((scheme, netloc, path, parsed.params, query, ""))


def validate_target(url: str, *, resolve_dns: bool = True) -> TargetValidation:
    """Validate a URL for safety — SSRF, scheme, DNS resolution."""
    if not url or not isinstance(url, str):
        return TargetValidation(url=str(url), status=TargetStatus.INVALID, normalized="", reason="Empty or non-string URL")
    try:
        normalized = normalize_url(url)
    except ValueError as exc:
        status = TargetStatus.UNSUPPORTED if "scheme" in str(exc).lower() else TargetStatus.INVALID
        return TargetValidation(url=url, status=status, normalized="", reason=str(exc))
    if not resolve_dns:
        return TargetValidation(url=url, status=TargetStatus.VALID, normalized=normalized)
    host = urllib.parse.urlparse(normalized).hostname or ""
    try:
        raw = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = tuple(sorted({str(info[4][0]) for info in raw}))
    except socket.gaierror:
        return TargetValidation(url=url, status=TargetStatus.INVALID, normalized=normalized, reason=f"DNS resolution failed: {host}")
    if not addresses:
        return TargetValidation(url=url, status=TargetStatus.INVALID, normalized=normalized, reason=f"No addresses resolved for {host}")
    for addr_str in addresses:
        if address_is_restricted(addr_str):
            return TargetValidation(url=url, status=TargetStatus.BLOCKED, normalized=normalized, reason=f"Resolves to restricted address: {addr_str}", addresses=addresses)
    return TargetValidation(url=url, status=TargetStatus.VALID, normalized=normalized, addresses=addresses)


def address_is_restricted(addr_str: str) -> bool:
    """True when an IP literal is one OPE must never connect to (SSRF guard).

    Covers loopback, private (RFC1918/ULA), link-local (incl. cloud metadata
    169.254.169.254), reserved, multicast, and unspecified ranges, for both
    IPv4 and IPv6 — including IPv4-mapped IPv6 forms, which ``ipaddress``
    classifies by their embedded IPv4 address.
    """
    try:
        addr = ipaddress.ip_address(addr_str)
    except ValueError:
        return True  # unparseable address is not something we will connect to
    return bool(
        addr.is_private or addr.is_loopback or addr.is_link_local
        or addr.is_reserved or addr.is_multicast or addr.is_unspecified
    )


def resolve_and_validate(host: str) -> tuple[str, ...]:
    """Resolve *host* and return its addresses, or raise ValueError if unsafe.

    Raises when the host does not resolve or resolves to *any* restricted
    address. Used at connection time to pin a validated resolution, closing
    the DNS-rebinding TOCTOU window between validation and connect: the same
    resolution that is validated here is the one the socket connects to.
    """
    try:
        raw = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed: {host}") from exc
    addresses = tuple(sorted({str(info[4][0]) for info in raw}))
    if not addresses:
        raise ValueError(f"No addresses resolved for {host}")
    for addr_str in addresses:
        if address_is_restricted(addr_str):
            raise ValueError(f"Resolves to restricted address: {addr_str}")
    return addresses


def validate_url_strict(url: str) -> str:
    """Validate and normalize, raising ValueError if unsafe. Drop-in for audit._validate_url."""
    result = validate_target(url)
    if result.status != TargetStatus.VALID:
        raise ValueError(result.reason or f"URL validation failed: {result.status.value}")
    return result.normalized


def make_scope(
    url: str, *, allow_subdomains: bool = False, max_depth: int = 10,
    max_pages: int = 200, max_total_bytes: int = 50 * 1024 * 1024,
) -> CrawlScope:
    """Create a CrawlScope from a seed URL."""
    normalized = normalize_url(url)
    parsed = urllib.parse.urlparse(normalized)
    return CrawlScope(
        origin_scheme=parsed.scheme,
        origin_host=parsed.hostname or "",
        origin_port=parsed.port or _DEFAULT_PORTS.get(parsed.scheme, 0),
        allow_subdomains=allow_subdomains, max_depth=max_depth,
        max_pages=max_pages, max_total_bytes=max_total_bytes,
    )


def url_depth(url: str) -> int:
    """Count meaningful path segments (proxy for click-depth from root)."""
    segments = [s for s in (urllib.parse.urlparse(url).path or "/").split("/") if s]
    return len(segments)


def resolve_url(base: str, relative: str) -> str:
    """Resolve a relative URL against a base, then normalize."""
    absolute = urllib.parse.urljoin(base, relative)
    try:
        return normalize_url(absolute)
    except ValueError:
        return absolute
