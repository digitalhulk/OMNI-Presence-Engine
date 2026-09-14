from __future__ import annotations

import ipaddress
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from . import citability, crawler
from .integrations.pagespeed import fetch_vitals

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
ALLOWED_SCHEMES = {"http", "https"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""; self.lang = ""; self.headings: list[str] = []; self.links: list[str] = []
        self.images = 0; self.images_missing_alt = 0; self.images_missing_dimensions = 0; self.images_missing_srcset = 0
        self.forms = 0; self.json_ld = 0; self.json_ld_raw: list[str] = []
        self.canonical = ""; self.viewport = ""; self.description = ""; self.h1_count = 0; self._in_title = False
        self.meta_robots = ""; self.hreflang_count = 0; self.landmarks: set[str] = set()
        self.article_modified = ""; self.contact_input = False; self.script_srcs: list[str] = []
        self._in_json_ld = False; self._json_ld_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang", "") or ""
        if tag == "title": self._in_title = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self.headings.append(tag)
        if tag == "h1": self.h1_count += 1
        if tag in {"header", "nav", "main", "footer"}: self.landmarks.add(tag)
        if tag == "a" and a.get("href"): self.links.append(a["href"] or "")
        if tag == "img":
            self.images += 1
            if not (a.get("alt") or "").strip(): self.images_missing_alt += 1
            if not (a.get("width") and a.get("height")): self.images_missing_dimensions += 1
            if not a.get("srcset"): self.images_missing_srcset += 1
        if tag == "input" and (a.get("type") or "").lower() in {"email", "tel"}: self.contact_input = True
        if tag == "form": self.forms += 1
        if tag == "link":
            rel = (a.get("rel") or "").lower().split()
            if "canonical" in rel: self.canonical = a.get("href", "") or ""
            if "alternate" in rel and a.get("hreflang"): self.hreflang_count += 1
        if tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            if name == "viewport": self.viewport = a.get("content", "") or ""
            if name == "description": self.description = a.get("content", "") or ""
            if name == "robots": self.meta_robots = a.get("content", "") or ""
            if prop == "article:modified_time": self.article_modified = a.get("content", "") or ""
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

    def handle_data(self, data: str) -> None:
        if self._in_title: self.title += data.strip()
        if self._in_json_ld: self._json_ld_buffer.append(data)


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


def _validate_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        raise ValueError("OPE accepts only absolute HTTP(S) URLs with a hostname")
    host = parsed.hostname.rstrip(".")
    try:
        addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for target: {host}") from exc
    if not addresses:
        raise ValueError(f"No address resolved for target: {host}")
    for addr in addresses:
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast or addr.is_unspecified:
            raise ValueError(f"Target resolves to a restricted network address: {addr}")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe = _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, safe)


def _request(url: str, timeout: int = 15) -> Response:
    safe_url = _validate_url(url)
    hostname = urllib.parse.urlparse(safe_url).hostname or ""
    dns_start = time.perf_counter()
    socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    dns_ms = round((time.perf_counter() - dns_start) * 1000, 1)
    req = urllib.request.Request(safe_url, headers={"User-Agent": "OPE-Audit/0.1"}, method="GET")
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(_SafeRedirect(), urllib.request.HTTPSHandler(context=ctx))
    opener.max_redirections = MAX_REDIRECTS
    ttfb_start = time.perf_counter()
    with opener.open(req, timeout=max(1, min(timeout, 60))) as r:
        ttfb_ms = round((time.perf_counter() - ttfb_start) * 1000, 1)
        content_type = (r.headers.get("Content-Type") or "").lower()
        if content_type and not any(x in content_type for x in ("text/html", "application/xhtml+xml")):
            raise ValueError(f"Unsupported target content type: {content_type}")
        body = r.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"Response exceeds OPE safety limit of {MAX_RESPONSE_BYTES} bytes")
        return Response(
            final_url=_validate_url(r.geturl()),
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
    present = lambda *keys: any(node.get(key) for node in nodes for key in keys)
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


_MODERN_TLS = {"TLSv1.2", "TLSv1.3"}
_CERT_EXPIRY_WARNING_DAYS = 14
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
_CDN_HEADER_MARKERS = ("cf-ray", "x-amz-cf-id", "x-akamai-transformed", "x-vercel-id", "x-served-by", "x-cache", "x-fastly-request-id", "x-cdn", "cdn-cache")
_WAF_MARKERS = ("cf-ray", "x-sucuri-id", "x-iinfo", "x-akamai-transformed", "x-waf-status", "x-sitelock-id")


def _tls_profile(url: str, timeout: int = 10) -> dict[str, Any]:
    """Inspect the live TLS handshake for protocol version and certificate life.

    Returns an error entry rather than raising so an unreachable or
    proxy-intercepted endpoint becomes UNKNOWN evidence, not a false FAIL.
    """
    parsed = urllib.parse.urlparse(_validate_url(url))
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
            expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
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
    priority = round(100 * impact * confidence * urgency * fixability, 2)
    return Finding(fid, module, symptom, "OBSERVED", severity, priority, [asdict(e) for e in evidence], remediation=remediation, validation=validation)


def audit(url: str, timeout: int = 15) -> dict[str, Any]:
    started = time.time()
    normalized = url if urllib.parse.urlparse(url).scheme else "https://" + url
    response = _request(normalized, timeout)
    final_url, status, headers, body = response.final_url, response.status, response.headers, response.body
    dns_ms, ttfb_ms = response.dns_ms, response.ttfb_ms
    html = body.decode(response.charset, errors="replace")
    p = PageParser(); p.feed(html)
    robots = crawler.fetch_robots(final_url, timeout=timeout)
    citability_report = citability.analyze_blocks(citability.extract_content_blocks(html))
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

    modules = {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)}
    for f in findings:
        key = f.module.split("-")[0]
        modules[key]["findings"].append(f.id)
        modules[key]["status"] = "FAIL"
    return {"engine": "ope", "version": "0.1.0", "run_id": f"ope-{int(started)}", "target": normalized, "final_url": final_url, "started_at": started, "completed_at": time.time(), "inventory": {"status": status, "bytes": len(body), "title": p.title.strip(), "description": p.description, "lang": p.lang, "viewport": p.viewport, "canonical": p.canonical, "headings": len(p.headings), "h1": p.h1_count, "links": len(p.links), "images": p.images, "images_missing_alt": p.images_missing_alt, "forms": p.forms, "json_ld_blocks": p.json_ld, "robots": robots, "meta_robots": p.meta_robots, "x_robots_tag": security_headers.get("x-robots-tag"), "hreflang_count": p.hreflang_count, "landmarks": sorted(p.landmarks), "dns_ms": dns_ms, "ttfb_ms": ttfb_ms, "citability": citability_report, "pagespeed": pagespeed_vitals, "entity_types": entities["types"], **{key: value for key, value in entities.items() if key != "types"}, "internal_links": link_locality["internal_links"], "external_links": link_locality["external_links"], "last_modified": security_headers.get("last-modified"), "article_modified": p.article_modified, "has_analytics": has_analytics, "images_missing_dimensions": p.images_missing_dimensions, "images_missing_srcset": p.images_missing_srcset, "contact_input": p.contact_input, "tls": tls, "cookies": cookies, "csp_profile": csp, "exposed_secrets": exposed_secrets, "cdn_markers": cdn_markers, "waf_markers": waf_markers, **inventory_security_headers}, "headers": {k.lower(): v for k, v in headers.items()}, "modules": modules, "findings": [asdict(f) for f in findings], "summary": {"finding_count": len(findings), **{level: sum(f.severity == level for f in findings) for level in ("critical", "high", "medium", "low", "info")}}}


def markdown_report(result: dict[str, Any]) -> str:
    lines = [f"# OPE Audit — {result['target']}", "", f"**Run:** `{result['run_id']}`  ", f"**HTTP:** `{result['inventory']['status']}`  ", f"**Findings:** `{result['summary']['finding_count']}`", "", "## Inventory", ""]
    lines += [f"- **{k}:** {v}" for k, v in result["inventory"].items()]
    lines += ["", "## Findings", ""]
    if not result["findings"]: lines.append("No findings were generated by the deterministic checks.")
    for f in sorted(result["findings"], key=lambda x: x["priority"], reverse=True):
        lines += [f"### {f['id']} — {f['severity'].upper()} — Priority {f['priority']}", f"**Module:** {f['module']}", f"**Symptom:** {f['symptom']}", "", "**Remediation:**"] + [f"- {x}" for x in f["remediation"]] + ["", "**Validation:**"] + [f"- {x}" for x in f["validation"]] + [""]
    return "\n".join(lines)
