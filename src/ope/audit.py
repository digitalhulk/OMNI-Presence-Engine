from __future__ import annotations

import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from typing import Any

from . import citability, crawler
from .integrations.pagespeed import fetch_vitals
from .net import build_opener as build_safe_opener
from .planner import diagnosis_markdown
from .scoring import priority as compute_priority
from .url import ALLOWED_SCHEMES, validate_url_strict

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 5


def _decode_content_encoding(body: bytes, encoding: str | None) -> bytes:
    """Decompress a response body per Content-Encoding, bounded against zip bombs.

    Handles servers that gzip/deflate even though OPE does not request it.
    Unknown encodings and malformed compressed data raise ValueError rather
    than yielding garbage that would be silently parsed as HTML.  The
    decompressed output is capped so a small compressed body cannot expand
    without limit.
    """
    enc = (encoding or "").strip().lower()
    if not enc or enc == "identity":
        return body
    if enc not in ("gzip", "x-gzip", "deflate"):
        raise ValueError(f"Unsupported content encoding: {enc}")
    # deflate is served either zlib-wrapped (RFC 1950, wbits 15) or raw
    # (RFC 1951, wbits -15); gzip is wbits 31. Try the plausible framings.
    wbits_options = (31,) if enc in ("gzip", "x-gzip") else (15, -15)
    last_error: Exception | None = None
    for wbits in wbits_options:
        decompressor = zlib.decompressobj(wbits)
        try:
            out = decompressor.decompress(body, MAX_DECOMPRESSED_BYTES + 1)
        except zlib.error as exc:
            last_error = exc
            continue
        if len(out) > MAX_DECOMPRESSED_BYTES or decompressor.unconsumed_tail:
            raise ValueError(
                f"Decompressed response exceeds OPE safety limit of {MAX_DECOMPRESSED_BYTES} bytes"
            )
        out += decompressor.flush()
        return out
    raise ValueError(f"Malformed {enc} response body") from last_error

try:
    # Reported in every audit result, so it is read from the installed package
    # rather than restated here where it would drift out of date.
    ENGINE_VERSION = _package_version("omni-presence-engine")
except PackageNotFoundError:
    ENGINE_VERSION = "0.0.0+unknown"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""; self.lang = ""; self.headings: list[str] = []; self.links: list[str] = []
        self.images = 0; self.images_missing_alt = 0; self.images_missing_dimensions = 0; self.images_missing_srcset = 0
        self.forms = 0; self.json_ld = 0; self.json_ld_raw: list[str] = []
        self.canonical = ""; self.viewport = ""; self.description = ""; self.h1_count = 0; self._in_title = False
        self.meta_robots = ""; self.hreflang_count = 0; self.landmarks: set[str] = set()
        self.article_modified = ""; self.contact_input = False; self.script_srcs: list[str] = []; self.stylesheet_hrefs: list[str] = []
        self._in_json_ld = False; self._json_ld_buffer: list[str] = []
        self.doctype = ""; self.charset = ""; self.title_count = 0; self.structure: set[str] = set()
        self.heading_texts: list[str] = []; self.link_texts: list[str] = []
        self.inputs = 0; self.unlabelled_inputs = 0; self.buttons = 0; self.buttons_without_text = 0
        self.videos = 0; self.videos_missing_metadata = 0; self.media_elements = 0; self.caption_tracks = 0
        self.positive_tabindex = 0; self.forms_missing_action = 0
        self._label_for: set[str] = set(); self._input_ids: list[str] = []
        self._label_depth = 0; self._heading_buffer: list[str] = []; self._in_heading = False
        self._link_buffer: list[str] = []; self._in_link = False
        self._button_buffer: list[str] = []; self._in_button = False; self._button_labelled = False
        self.verification_tags: list[str] = []; self.lazy_images = 0; self.noscript_content = False; self.has_password_input = False
        self.lists = 0; self.tables = 0; self._in_noscript = False; self._noscript_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang", "") or ""
        if tag in {"html", "head", "body"}: self.structure.add(tag)
        if tag == "title": self._in_title = True; self.title_count += 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.append(tag); self._in_heading = True; self._heading_buffer = []
        if tag == "h1": self.h1_count += 1
        if tag in {"header", "nav", "main", "footer"}: self.landmarks.add(tag)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"] or ""); self._in_link = True; self._link_buffer = []
        if tag == "label":
            self._label_depth += 1
            if a.get("for"): self._label_for.add(a["for"] or "")
        if tag == "button":
            self.buttons += 1
            self._in_button = True
            self._button_buffer = []
            self._button_labelled = bool((a.get("aria-label") or "").strip() or a.get("aria-labelledby"))
        if tag in {"video", "audio"}:
            self.media_elements += 1
            if tag == "video":
                self.videos += 1
                if not (a.get("poster") and a.get("width") and a.get("height")): self.videos_missing_metadata += 1
        if tag == "track" and (a.get("kind") or "").lower() in {"captions", "subtitles"}: self.caption_tracks += 1
        try:
            if int(a.get("tabindex") or 0) > 0: self.positive_tabindex += 1
        except ValueError:
            pass
        if tag == "img":
            self.images += 1
            if not (a.get("alt") or "").strip(): self.images_missing_alt += 1
            if not (a.get("width") and a.get("height")): self.images_missing_dimensions += 1
            if not a.get("srcset"): self.images_missing_srcset += 1
            if (a.get("loading") or "").lower() == "lazy": self.lazy_images += 1
        if tag == "input":
            input_type = (a.get("type") or "text").lower()
            if input_type in {"email", "tel"}: self.contact_input = True
            if input_type == "password": self.has_password_input = True
            if input_type not in {"hidden", "submit", "button", "reset", "image"}:
                self.inputs += 1
                labelled = bool((a.get("aria-label") or "").strip() or a.get("aria-labelledby")) or self._label_depth > 0
                if labelled:
                    pass
                elif a.get("id"):
                    self._input_ids.append(a["id"] or "")
                else:
                    self.unlabelled_inputs += 1
        if tag == "form":
            self.forms += 1
            if not a.get("action"): self.forms_missing_action += 1
        if tag in ("ul", "ol"): self.lists += 1
        if tag == "table": self.tables += 1
        if tag == "noscript": self._in_noscript = True; self._noscript_buffer = []
        if tag == "link":
            rel = (a.get("rel") or "").lower().split()
            if "canonical" in rel: self.canonical = a.get("href", "") or ""
            if "alternate" in rel and a.get("hreflang"): self.hreflang_count += 1
            if "stylesheet" in rel and a.get("href"): self.stylesheet_hrefs.append(a["href"] or "")
        if tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            if a.get("charset"): self.charset = a["charset"] or ""
            if name == "viewport": self.viewport = a.get("content", "") or ""
            if name == "description": self.description = a.get("content", "") or ""
            if name == "robots": self.meta_robots = a.get("content", "") or ""
            if prop == "article:modified_time": self.article_modified = a.get("content", "") or ""
            for _vn in ("google-site-verification", "msvalidate.01", "yandex-verification", "p:domain_verify", "facebook-domain-verification"):
                if name == _vn and a.get("content"): self.verification_tags.append(_vn)
        if tag == "script":
            if a.get("src"): self.script_srcs.append(a["src"] or "")
            if (a.get("type") or "").lower() == "application/ld+json":
                self.json_ld += 1
                self._in_json_ld = True
                self._json_ld_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self._in_title = False
        if tag == "script" and self._in_json_ld:
            self.json_ld_raw.append("".join(self._json_ld_buffer))
            self._in_json_ld = False
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._in_heading:
            self.heading_texts.append(" ".join("".join(self._heading_buffer).split()))
            self._in_heading = False
        if tag == "a" and self._in_link:
            self.link_texts.append(" ".join("".join(self._link_buffer).split()))
            self._in_link = False
        if tag == "label" and self._label_depth:
            self._label_depth -= 1
        if tag == "button" and self._in_button:
            if not (self._button_labelled or "".join(self._button_buffer).strip()):
                self.buttons_without_text += 1
            self._in_button = False
        if tag == "noscript" and self._in_noscript:
            if "".join(self._noscript_buffer).strip(): self.noscript_content = True
            self._in_noscript = False

    def handle_decl(self, decl: str) -> None:
        self.doctype = decl.strip()

    def handle_data(self, data: str) -> None:
        if self._in_title: self.title += data.strip()
        if self._in_json_ld: self._json_ld_buffer.append(data)
        if self._in_heading: self._heading_buffer.append(data)
        if self._in_link: self._link_buffer.append(data)
        if self._in_button: self._button_buffer.append(data)
        if self._in_noscript: self._noscript_buffer.append(data)

    def close(self) -> None:
        super().close()
        # label[for=...] can appear after the input it labels, so id-based
        # association is resolved once the whole document has been seen.
        self.unlabelled_inputs += sum(1 for input_id in self._input_ids if input_id not in self._label_for)
        self._input_ids = []


@dataclass
class Response:
    """One fetched HTTP response plus the timings observed around it."""

    final_url: str
    status: int
    headers: dict[str, str]
    set_cookies: list[str]
    body: bytes
    charset: str
    dns_ms: float
    ttfb_ms: float


@dataclass
class Evidence:
    source: str
    observed_at: str
    target: str
    value: Any
    confidence: float = 1.0


@dataclass
class Finding:
    id: str
    module: str
    symptom: str
    status: str
    severity: str
    priority: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    root_cause: str = ""
    remediation: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> urllib.request.Request | None:
        safe = validate_url_strict(newurl)
        return super().redirect_request(req, fp, code, msg, headers, safe)


def _request(url: str, timeout: int = 15) -> Response:
    safe_url = validate_url_strict(url)
    hostname = urllib.parse.urlparse(safe_url).hostname or ""
    dns_start = time.perf_counter()
    socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    dns_ms = round((time.perf_counter() - dns_start) * 1000, 1)
    req = urllib.request.Request(safe_url, headers={"User-Agent": f"OPE-Audit/{ENGINE_VERSION}"}, method="GET")
    ctx = ssl.create_default_context()
    # Pin the validated resolution for direct connections (closes the
    # DNS-rebinding TOCTOU); delegate to the egress proxy when one applies.
    opener = build_safe_opener(safe_url, _SafeRedirect(), ctx)
    opener.max_redirections = MAX_REDIRECTS  # type: ignore[attr-defined]
    ttfb_start = time.perf_counter()
    with opener.open(req, timeout=max(1, min(timeout, 60))) as r:
        ttfb_ms = round((time.perf_counter() - ttfb_start) * 1000, 1)
        content_type = (r.headers.get("Content-Type") or "").lower()
        if content_type and not any(x in content_type for x in ("text/html", "application/xhtml+xml")):
            raise ValueError(f"Unsupported target content type: {content_type}")
        body = r.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"Response exceeds OPE safety limit of {MAX_RESPONSE_BYTES} bytes")
        body = _decode_content_encoding(body, r.headers.get("Content-Encoding"))
        return Response(
            final_url=validate_url_strict(r.geturl()),
            status=r.status,
            headers={k.lower(): v for k, v in r.headers.items()},
            # get_all keeps every Set-Cookie; a plain dict would collapse
            # them to the last one and hide insecure cookies.
            set_cookies=list(r.headers.get_all("Set-Cookie") or []),
            body=body,
            charset=r.headers.get_content_charset() or "utf-8",
            dns_ms=dns_ms,
            ttfb_ms=ttfb_ms,
        )


_ENTITY_TYPES = {"organization", "person", "localbusiness", "corporation", "ngo", "educationalorganization", "governmentorganization"}
_ANALYTICS_MARKERS = ("googletagmanager.com", "google-analytics.com", "gtag/js")
# schema.org's documented direct LocalBusiness subtypes, so a Restaurant or
# Dentist is recognised as a local entity without declaring LocalBusiness.
_LOCAL_TYPES = {
    "localbusiness", "animalshelter", "archiveorganization", "automotivebusiness", "childcare",
    "dentist", "drycleaningorlaundry", "emergencyservice", "employmentagency",
    "entertainmentbusiness", "financialservice", "foodestablishment", "restaurant",
    "governmentoffice", "healthandbeautybusiness", "homeandconstructionbusiness",
    "insuranceagency", "legalservice", "library", "lodgingbusiness", "hotel",
    "medicalbusiness", "physician", "professionalservice", "radiostation", "realestateagent",
    "recyclingcenter", "selfstorage", "shoppingcenter", "sportsactivitylocation", "store",
    "televisionstation", "touristinformationcenter", "travelagency",
}
_SOCIAL_PROFILE_HOSTS = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "github.com", "wikipedia.org", "crunchbase.com", "pinterest.com", "tiktok.com")
_GOOGLE_PROFILE_MARKERS = ("google.com/maps", "business.google.com", "maps.app.goo.gl", "goo.gl/maps", "g.page")
_JSON_LD_MAX_NODES = 500
_REVIEW_TYPES = {"review", "aggregaterating", "userreview", "criticreview"}


def _json_ld_nodes(raw_blocks: list[str]) -> list[dict[str, Any]]:
    """Flatten every object in the page's JSON-LD into a node list.

    The walk is iterative and node-capped so nested @graph documents are
    covered without unbounded recursion. Malformed JSON-LD is common and
    is skipped rather than treated as an error.
    """
    nodes: list[dict[str, Any]] = []
    for raw in raw_blocks:
        try:
            parsed = json.loads(raw)
        except ValueError:
            continue
        stack: list[Any] = [parsed]
        while stack and len(nodes) < _JSON_LD_MAX_NODES:
            current = stack.pop()
            if isinstance(current, dict):
                nodes.append(current)
                stack.extend(current.values())
            elif isinstance(current, list):
                stack.extend(current)
    return nodes


def _node_types(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    return {str(t).lower() for t in (raw if isinstance(raw, list) else [raw]) if t}


def _flatten_urls(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(value.get("@id") or value.get("url") or "")]
    if isinstance(value, list):
        return [url for item in value for url in _flatten_urls(item)]
    return []


def _json_ld_summary(raw_blocks: list[str], title: str = "", description: str = "") -> dict[str, Any]:
    """Derive deterministic structured-data signals from the page's JSON-LD.

    Only what is actually published on the page is reported. Fields the
    page does not declare are reported as absent (or None where the
    comparison has no basis), never inferred.
    """
    nodes = _json_ld_nodes(raw_blocks)
    types: set[str] = set()
    for node in nodes:
        types |= _node_types(node)
    def present(*keys: str) -> bool:
        return any(node.get(key) for node in nodes for key in keys)
    local_nodes = [node for node in nodes if _node_types(node) & _LOCAL_TYPES]
    same_as = [url.lower() for node in nodes for url in _flatten_urls(node.get("sameAs")) if url]
    names = [str(node["name"]) for node in nodes if isinstance(node.get("name"), str)]
    descriptions = [str(node["description"]) for node in nodes if isinstance(node.get("description"), str)]
    has_address = bool(local_nodes) and any(node.get("address") for node in local_nodes)
    has_geo = bool(local_nodes) and any(node.get("geo") for node in local_nodes)
    return {
        "types": sorted(types),
        "has_entity_type": bool(types & _ENTITY_TYPES),
        "has_nap": any(node.get("address") and node.get("telephone") for node in local_nodes),
        "is_local_business": bool(local_nodes),
        "has_address": has_address,
        "has_geo": has_geo,
        "has_opening_hours": bool(local_nodes) and any(node.get("openingHours") or node.get("openingHoursSpecification") for node in local_nodes),
        "has_service_area": bool(local_nodes) and any(node.get("areaServed") or node.get("serviceArea") for node in local_nodes),
        "has_google_profile": any(marker in url for url in same_as for marker in _GOOGLE_PROFILE_MARKERS),
        "local_visibility_ready": has_address and has_geo,
        "has_review": bool(types & _REVIEW_TYPES) or present("aggregateRating", "review"),
        "has_author": present("author", "creator"),
        "has_identifiers": present("sameAs", "identifier", "vatID", "taxID", "duns", "leiCode"),
        "has_relationships": present("parentOrganization", "subOrganization", "memberOf", "brand", "worksFor", "affiliation", "isPartOf"),
        "has_social_profiles": sum(any(host in url for host in _SOCIAL_PROFILE_HOSTS) for url in same_as) >= 2,
        "has_breadcrumb": "breadcrumblist" in types,
        "name_matches_title": None if not (names and title) else any(name.lower() in title.lower() or title.lower() in name.lower() for name in names),
        "description_matches": None if not (descriptions and description) else any(desc.strip().lower() == description.strip().lower() for desc in descriptions),
    }


def _link_locality(links: list[str], final_url: str) -> dict[str, int]:
    origin = urllib.parse.urlparse(final_url).hostname or ""
    internal = external = 0
    for href in links:
        parsed = urllib.parse.urlparse(href)
        if parsed.scheme and parsed.scheme not in ALLOWED_SCHEMES:
            continue
        if not parsed.hostname or parsed.hostname == origin:
            internal += 1
        else:
            external += 1
    return {"internal_links": internal, "external_links": external}


# Narrow, high-confidence credential patterns. Only the pattern label and a
# count are ever reported — a matched secret is never copied into evidence.
_SECRET_PATTERNS = (
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("stripe_live_secret", re.compile(r"sk_live_[0-9A-Za-z]{16,}")),
    ("github_token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36}")),
)
_TRUST_PATH_MARKERS = ("privacy", "terms", "contact", "about", "refund", "imprint", "impressum", "legal", "disclaimer")
_CTA_PATTERN = re.compile(r"\b(get|start|book|buy|contact|sign\s?up|subscribe|request|call|order|download|demo|quote|register|apply|join|schedule|enquire|inquire)\b", re.IGNORECASE)
_QUESTION_PATTERN = re.compile(r"^(how|what|why|when|where|which|who|can|do|does|is|are|should)\b", re.IGNORECASE)
_CDN_HEADER_MARKERS = ("cf-ray", "x-amz-cf-id", "x-akamai-transformed", "x-vercel-id", "x-served-by", "x-cache", "x-fastly-request-id", "x-cdn", "cdn-cache")
_WAF_MARKERS = ("cf-ray", "x-sucuri-id", "x-iinfo", "x-akamai-transformed", "x-waf-status", "x-sitelock-id")


MAX_SUBRESOURCES = 12
MAX_SUBRESOURCE_BYTES = 512 * 1024


def _fetch_subresources(page_url: str, stylesheets: list[str], scripts: list[str], timeout: int = 10) -> dict[str, Any]:
    """Measure the CSS/JS the page links, within strict fetch limits.

    Every discovered resource is counted and classified from the markup;
    only a capped subset is downloaded to measure bytes, so the reported
    byte totals are explicitly a measured sample rather than a claim
    about the full page.
    """
    origin = urllib.parse.urlparse(page_url).hostname or ""
    discovered = [("css", href) for href in stylesheets] + [("js", src) for src in scripts]
    third_party_hosts: set[str] = set()
    resolved: list[tuple[str, str]] = []
    for kind, reference in discovered:
        absolute = urllib.parse.urljoin(page_url, reference)
        host = urllib.parse.urlparse(absolute).hostname or ""
        if host and host != origin:
            third_party_hosts.add(host)
        resolved.append((kind, absolute))

    measured = {"css": 0, "js": 0}
    fetched = 0
    css_text: list[str] = []
    ctx = ssl.create_default_context()
    for kind, absolute in resolved[:MAX_SUBRESOURCES]:
        try:
            safe_url = validate_url_strict(absolute)
            request = urllib.request.Request(safe_url, headers={"User-Agent": f"OPE-Audit/{ENGINE_VERSION}"}, method="GET")
            # Same SSRF pinning + redirect revalidation as the main fetch.
            opener = build_safe_opener(safe_url, _SafeRedirect(), ctx)
            with opener.open(request, timeout=max(1, min(timeout, 20))) as response:
                payload = response.read(MAX_SUBRESOURCE_BYTES)
        except Exception:
            continue
        fetched += 1
        measured[kind] += len(payload)
        if kind == "css":
            css_text.append(payload.decode("utf-8", errors="replace"))
    return {
        "discovered_requests": len(discovered),
        "fetched_requests": fetched,
        "css_bytes": measured["css"],
        "js_bytes": measured["js"],
        "third_party_hosts": sorted(third_party_hosts),
        "css_text": "\n".join(css_text),
    }


def _css_behaviour(css_text: str) -> dict[str, Any]:
    """Read motion and focus handling out of the stylesheets actually served."""
    lowered = css_text.lower()
    return {
        "has_css": bool(lowered.strip()),
        "has_motion": "animation" in lowered or "transition" in lowered,
        "respects_reduced_motion": "prefers-reduced-motion" in lowered,
        "suppresses_focus_outline": bool(re.search(r"outline\s*:\s*(none|0)", lowered)),
        "has_focus_visible": ":focus-visible" in lowered,
    }


def _tls_profile(url: str, timeout: int = 10) -> dict[str, Any]:
    """Inspect the live TLS handshake for protocol version and certificate life.

    Returns an error entry rather than raising so an unreachable or
    proxy-intercepted endpoint becomes UNKNOWN evidence, not a false FAIL.
    """
    parsed = urllib.parse.urlparse(validate_url_strict(url))
    if parsed.scheme != "https":
        return {"protocol": None, "days_until_expiry": None, "error": "Target is not served over HTTPS"}
    context = ssl.create_default_context()
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=max(1, min(timeout, 30))) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=parsed.hostname) as tls_socket:
                protocol = tls_socket.version()
                cipher = tls_socket.cipher()
                certificate = tls_socket.getpeercert() or {}
    except Exception as exc:
        return {"protocol": None, "days_until_expiry": None, "error": f"{type(exc).__name__}: {exc}"}
    days_until_expiry = None
    not_after = certificate.get("notAfter")
    if not_after:
        try:
            expires_at = datetime.strptime(str(not_after), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_until_expiry = (expires_at - datetime.now(timezone.utc)).days
        except ValueError:
            days_until_expiry = None
    return {"protocol": protocol, "cipher": cipher[0] if cipher else None, "days_until_expiry": days_until_expiry, "error": None}


def _cookie_profile(set_cookies: list[str]) -> dict[str, Any]:
    """Summarise Set-Cookie flag hygiene without recording cookie values."""
    insecure: list[str] = []
    for raw in set_cookies:
        attributes = raw.lower()
        name = raw.split("=", 1)[0].strip()
        missing = [flag for flag in ("secure", "httponly", "samesite") if flag not in attributes]
        if missing:
            insecure.append(f"{name}: missing {', '.join(missing)}")
    return {"cookie_count": len(set_cookies), "insecure_cookies": insecure}


def _csp_profile(header_value: str | None) -> dict[str, Any]:
    if not header_value:
        return {"present": False, "unsafe_directives": []}
    lowered = header_value.lower()
    unsafe = [token for token in ("unsafe-inline", "unsafe-eval") if token in lowered]
    return {"present": True, "unsafe_directives": unsafe}


def _scan_secrets(html: str) -> list[str]:
    """Return the labels of credential patterns exposed in the page source."""
    return sorted({label for label, pattern in _SECRET_PATTERNS if pattern.search(html)})


def _edge_markers(headers: dict[str, str], markers: tuple[str, ...]) -> list[str]:
    server = (headers.get("server") or "").lower()
    detected = [marker for marker in markers if marker in headers]
    if "cloudflare" in server:
        detected.append("server: cloudflare")
    return sorted(set(detected))


def _finding(fid: str, module: str, symptom: str, severity: str, evidence: list[Evidence], remediation: list[str], validation: list[str], impact: float = .5, urgency: float = .5, fixability: float = .8) -> Finding:
    confidence = min((e.confidence for e in evidence), default=0.2)
    prio = compute_priority(impact=impact, confidence=confidence, urgency=urgency, fixability=fixability)
    return Finding(fid, module, symptom, "OBSERVED", severity, prio, [asdict(e) for e in evidence], remediation=remediation, validation=validation)


def _run_browser_pass(
    final_url: str,
    inventory: dict[str, Any],
    browser_timeout: int,
    browser_profiles: list[str] | None,
) -> dict[str, Any]:
    """Execute browser audit and inject evidence into inventory. Returns extra result keys."""
    try:
        from .browser import BrowserConfig, DeviceProfile, execute_browser_audit
        from .browser_evidence import inject_browser_evidence
        from .performance import analyze_performance

        profiles: list[DeviceProfile] = []
        for name in (browser_profiles or ["DESKTOP"]):
            profiles.append(DeviceProfile(name.upper()))

        config = BrowserConfig(
            timeout_ms=browser_timeout * 1000,
            navigation_timeout_ms=browser_timeout * 1000,
            profiles=profiles,
        )
        browser_results = execute_browser_audit(final_url, config=config)
        inject_browser_evidence(inventory, browser_results)
        perf_report = analyze_performance(browser_results)
        return {
            "browser": [br.to_dict() for br in browser_results],
            "performance_report": perf_report.to_dict(),
        }
    except Exception:
        return {}


def audit(url: str, timeout: int = 15, fetch_subresources: bool = True, browser: bool = False, browser_timeout: int = 30, browser_profiles: list[str] | None = None) -> dict[str, Any]:
    started = time.time()
    normalized = url if urllib.parse.urlparse(url).scheme else "https://" + url
    response = _request(normalized, timeout)
    final_url, status, headers, body = response.final_url, response.status, response.headers, response.body
    dns_ms, ttfb_ms = response.dns_ms, response.ttfb_ms
    html = body.decode(response.charset, errors="replace")
    p = PageParser(); p.feed(html); p.close()
    robots = crawler.fetch_robots(final_url, timeout=timeout)
    content_blocks = citability.extract_content_blocks(html)
    word_count = sum(len(str(block.get("content", "")).split()) for block in content_blocks)
    citability_report = citability.analyze_blocks(content_blocks)
    pagespeed_vitals = fetch_vitals(final_url)
    entities = _json_ld_summary(p.json_ld_raw, p.title.strip(), p.description)
    link_locality = _link_locality(p.links, final_url)
    has_analytics = any(marker in html for marker in _ANALYTICS_MARKERS)
    tls = _tls_profile(final_url, timeout)
    cookies = _cookie_profile(response.set_cookies)
    csp = _csp_profile(headers.get("content-security-policy"))
    exposed_secrets = _scan_secrets(html)
    cdn_markers = _edge_markers(headers, _CDN_HEADER_MARKERS)
    waf_markers = _edge_markers(headers, _WAF_MARKERS)
    declared_charset = (p.charset or response.charset or "").lower()
    has_trust_links = any(marker in (href + " " + text).lower() for href, text in zip(p.links, p.link_texts + [""] * len(p.links)) for marker in _TRUST_PATH_MARKERS)
    has_cta = p.buttons > 0 or any(_CTA_PATTERN.search(text) for text in p.link_texts)
    question_headings = sum(1 for text in p.heading_texts if text.endswith("?") or _QUESTION_PATTERN.match(text))
    canonical_is_self = None if not p.canonical else urllib.parse.urljoin(final_url, p.canonical).rstrip("/") == final_url.rstrip("/")
    subresources = _fetch_subresources(final_url, p.stylesheet_hrefs, p.script_srcs, timeout) if fetch_subresources else {}
    css_behaviour = _css_behaviour(subresources.get("css_text", "")) if subresources else {}
    page_weight_bytes = len(body) + subresources.get("css_bytes", 0) + subresources.get("js_bytes", 0) if subresources else None
    has_captcha = any(marker in html.lower() for marker in ("recaptcha", "hcaptcha", "turnstile"))
    has_event_tracking = any(marker in html for marker in ("dataLayer.push", "gtag(", "fbq(", "plausible(", "umami."))
    has_attribution_code = "utm_" in html.lower()
    soft_404 = status == 200 and any(phrase in (p.title.lower() + " " + " ".join(t.lower() for t in p.heading_texts)) for phrase in ("page not found", "404 not found", "404 error"))
    has_rate_limit_headers = any(key.startswith("x-ratelimit") or key == "retry-after" for key in headers)
    title_words = {w for w in p.title.lower().split() if len(w) > 3}
    h1_raw = p.heading_texts[:p.h1_count]
    intent_aligned = bool(title_words) and bool(h1_raw) and any(len(title_words & {w for w in h.lower().split() if len(w) > 3}) >= 2 for h in h1_raw)
    now = datetime.now(timezone.utc).isoformat()
    evidence_base = Evidence("direct-http", now, final_url, {"status": status, "bytes": len(body)})
    findings: list[Finding] = []

    if status >= 400:
        findings.append(_finding("CODE-HTTP-001", "03-code", f"Target returned HTTP {status}", "high", [evidence_base], ["Resolve the server/application error before downstream optimization."], ["Re-run audit and confirm a successful response."], .9, .9))
    if not final_url.startswith("https://"):
        findings.append(_finding("02-INFRA-TLS-001", "02-infrastructure", "Canonical target is not HTTPS", "high", [evidence_base], ["Serve the site over HTTPS and redirect HTTP to HTTPS."], ["Confirm HTTPS response and secure canonicalization."], .8, .8))
    checks = [
        (not p.title.strip(), "03-CODE-META-001", "03-code", "Document has no title", "medium", {"title": p.title}, ["Add a unique, descriptive title aligned to page intent."], ["Re-audit title presence and uniqueness."], .7, .7),
        (not p.viewport, "13-UX-MOBILE-001", "13-ux", "Viewport metadata is missing", "medium", {"viewport": p.viewport}, ["Add an appropriate responsive viewport declaration."], ["Validate mobile rendering across representative devices."], .7, .6),
        (not p.lang, "17-LANG-001", "17-language", "HTML language is not declared", "low", {"lang": p.lang}, ["Declare the primary document language on html."], ["Confirm correct language metadata."], .5, .4),
        (p.images_missing_alt > 0, "14-A11Y-IMG-001", "14-accessibility", f"{p.images_missing_alt} of {p.images} images lack useful alt text", "medium", {"images": p.images, "missing_alt": p.images_missing_alt}, ["Add meaningful alt text to informative images; use empty alt for decorative images."], ["Re-run accessibility checks and inspect representative images."], .6, .6),
        (not p.canonical, "05-INDEX-CAN-001", "05-index", "No canonical link was detected", "medium", {"canonical": p.canonical}, ["Define canonicalization deliberately for indexable URLs."], ["Confirm canonical points to the intended URL."], .7, .5),
        (not p.json_ld, "06-SEM-JSONLD-001", "06-semantics", "No JSON-LD structured data was detected", "info", {"json_ld_blocks": p.json_ld}, ["Add only accurate structured data supported by visible content."], ["Validate structured data against visible content."], .4, .3),
    ]
    for failed, fid, module, symptom, severity, value, remediation, validation, impact, urgency in checks:
        if failed:
            findings.append(_finding(fid, module, symptom, severity, [Evidence("html-parser", now, final_url, value)], remediation, validation, impact, urgency))

    security_headers = {k.lower(): v for k, v in headers.items()}
    inventory_security_headers = {
        "hsts": "strict-transport-security" in security_headers,
        "csp": "content-security-policy" in security_headers,
        "x_content_type_options": "x-content-type-options" in security_headers,
        "referrer_policy_header": "referrer-policy" in security_headers,
    }
    for header in ("content-security-policy", "strict-transport-security", "x-content-type-options", "referrer-policy"):
        if header not in security_headers:
            findings.append(_finding(f"16-SEC-{header.upper()}", "16-security", f"Recommended security header not observed: {header}", "low", [Evidence("http-headers", now, final_url, {header: None})], [f"Review and configure {header} according to the application's threat model."], [f"Re-fetch response headers and verify {header}."], .4, .4, .7))

    modules: dict[str, dict[str, Any]] = {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)}
    for f in findings:
        key = f.module.split("-")[0]
        modules[key]["findings"].append(f.id)
        modules[key]["status"] = "FAIL"

    inventory: dict[str, Any] = {"status": status, "bytes": len(body), "title": p.title.strip(), "description": p.description, "lang": p.lang, "viewport": p.viewport, "canonical": p.canonical, "headings": len(p.headings), "h1": p.h1_count, "links": len(p.links), "images": p.images, "images_missing_alt": p.images_missing_alt, "forms": p.forms, "json_ld_blocks": p.json_ld, "robots": robots, "meta_robots": p.meta_robots, "x_robots_tag": security_headers.get("x-robots-tag"), "hreflang_count": p.hreflang_count, "landmarks": sorted(p.landmarks), "dns_ms": dns_ms, "ttfb_ms": ttfb_ms, "citability": citability_report, "pagespeed": pagespeed_vitals, "entity_types": entities["types"], **{key: value for key, value in entities.items() if key != "types"}, "internal_links": link_locality["internal_links"], "external_links": link_locality["external_links"], "last_modified": security_headers.get("last-modified"), "article_modified": p.article_modified, "has_analytics": has_analytics, "images_missing_dimensions": p.images_missing_dimensions, "images_missing_srcset": p.images_missing_srcset, "contact_input": p.contact_input, "tls": tls, "cookies": cookies, "csp_profile": csp, "exposed_secrets": exposed_secrets, "cdn_markers": cdn_markers, "waf_markers": waf_markers, "doctype": p.doctype, "declared_charset": declared_charset, "title_count": p.title_count, "structure": sorted(p.structure), "word_count": word_count, "inputs": p.inputs, "unlabelled_inputs": p.unlabelled_inputs, "buttons": p.buttons, "buttons_without_text": p.buttons_without_text, "videos": p.videos, "videos_missing_metadata": p.videos_missing_metadata, "media_elements": p.media_elements, "caption_tracks": p.caption_tracks, "positive_tabindex": p.positive_tabindex, "forms_missing_action": p.forms_missing_action, "has_trust_links": has_trust_links, "has_cta": has_cta, "question_headings": question_headings, "subheadings": len(p.headings) - p.h1_count, "canonical_is_self": canonical_is_self, "page_weight_bytes": page_weight_bytes, **{key: value for key, value in subresources.items() if key != "css_text"}, **css_behaviour, **inventory_security_headers, "verification_tags": p.verification_tags, "lazy_images": p.lazy_images, "noscript_content": p.noscript_content, "has_password_input": p.has_password_input, "lists": p.lists, "tables": p.tables, "has_captcha": has_captcha, "has_event_tracking": has_event_tracking, "has_attribution_code": has_attribution_code, "soft_404": soft_404, "has_rate_limit_headers": has_rate_limit_headers, "intent_aligned": intent_aligned}

    browser_data: dict[str, Any] = {}
    if browser:
        browser_data = _run_browser_pass(final_url, inventory, browser_timeout, browser_profiles)

    return {"engine": "ope", "version": ENGINE_VERSION, "run_id": f"ope-{int(started)}", "target": normalized, "final_url": final_url, "started_at": started, "completed_at": time.time(), "inventory": inventory, "headers": {k.lower(): v for k, v in headers.items()}, "modules": modules, "findings": [asdict(f) for f in findings], "summary": {"finding_count": len(findings), **{level: sum(f.severity == level for f in findings) for level in ("critical", "high", "medium", "low", "info")}}, **browser_data}


def markdown_report(result: dict[str, Any]) -> str:
    lines = [f"# OPE Audit — {result['target']}", "", f"**Run:** `{result['run_id']}`  ", f"**HTTP:** `{result['inventory']['status']}`  ", f"**Findings:** `{result['summary']['finding_count']}`", "", "## Inventory", ""]
    lines += [f"- **{k}:** {v}" for k, v in result["inventory"].items()]
    lines += ["", *diagnosis_markdown(result)]
    lines += ["## Findings", ""]
    if not result["findings"]: lines.append("No findings were generated by the deterministic checks.")
    for f in sorted(result["findings"], key=lambda x: x["priority"], reverse=True):
        lines += [f"### {f['id']} — {f['severity'].upper()} — Priority {f['priority']}", f"**Module:** {f['module']}", f"**Symptom:** {f['symptom']}", "", "**Remediation:**"] + [f"- {x}" for x in f["remediation"]] + ["", "**Validation:**"] + [f"- {x}" for x in f["validation"]] + [""]
    return "\n".join(lines)
