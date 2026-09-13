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

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
ALLOWED_SCHEMES = {"http", "https"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""; self.lang = ""; self.headings: list[str] = []; self.links: list[str] = []
        self.images = 0; self.images_missing_alt = 0; self.forms = 0; self.json_ld = 0
        self.canonical = ""; self.viewport = ""; self.description = ""; self.h1_count = 0; self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang", "") or ""
        if tag == "title": self._in_title = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self.headings.append(tag)
        if tag == "h1": self.h1_count += 1
        if tag == "a" and a.get("href"): self.links.append(a["href"] or "")
        if tag == "img":
            self.images += 1
            if not (a.get("alt") or "").strip(): self.images_missing_alt += 1
        if tag == "form": self.forms += 1
        if tag == "link" and "canonical" in (a.get("rel") or "").lower().split(): self.canonical = a.get("href", "") or ""
        if tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "viewport": self.viewport = a.get("content", "") or ""
            if name == "description": self.description = a.get("content", "") or ""
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json": self.json_ld += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title: self.title += data.strip()


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


def _request(url: str, timeout: int = 15) -> tuple[str, int, dict[str, str], bytes, str]:
    safe_url = _validate_url(url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": "OPE-Audit/0.1"}, method="GET")
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(_SafeRedirect(), urllib.request.HTTPSHandler(context=ctx))
    opener.max_redirections = MAX_REDIRECTS
    with opener.open(req, timeout=max(1, min(timeout, 60))) as r:
        content_type = (r.headers.get("Content-Type") or "").lower()
        if content_type and not any(x in content_type for x in ("text/html", "application/xhtml+xml")):
            raise ValueError(f"Unsupported target content type: {content_type}")
        body = r.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"Response exceeds OPE safety limit of {MAX_RESPONSE_BYTES} bytes")
        final_url = _validate_url(r.geturl())
        return final_url, r.status, dict(r.headers.items()), body, r.headers.get_content_charset() or "utf-8"


def _finding(fid: str, module: str, symptom: str, severity: str, evidence: list[Evidence], remediation: list[str], validation: list[str], impact: float = .5, urgency: float = .5, fixability: float = .8) -> Finding:
    confidence = min((e.confidence for e in evidence), default=0.2)
    priority = round(100 * impact * confidence * urgency * fixability, 2)
    return Finding(fid, module, symptom, "OBSERVED", severity, priority, [asdict(e) for e in evidence], remediation=remediation, validation=validation)


def audit(url: str, timeout: int = 15) -> dict[str, Any]:
    started = time.time()
    normalized = url if urllib.parse.urlparse(url).scheme else "https://" + url
    final_url, status, headers, body, charset = _request(normalized, timeout)
    html = body.decode(charset, errors="replace")
    p = PageParser(); p.feed(html)
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
    for header in ("content-security-policy", "strict-transport-security", "x-content-type-options", "referrer-policy"):
        if header not in security_headers:
            findings.append(_finding(f"16-SEC-{header.upper()}", "16-security", f"Recommended security header not observed: {header}", "low", [Evidence("http-headers", now, final_url, {header: None})], [f"Review and configure {header} according to the application's threat model."], [f"Re-fetch response headers and verify {header}."], .4, .4, .7))

    modules = {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)}
    for f in findings:
        key = f.module.split("-")[0]
        modules[key]["findings"].append(f.id)
        modules[key]["status"] = "FAIL"
    return {"engine": "ope", "version": "0.1.0", "run_id": f"ope-{int(started)}", "target": normalized, "final_url": final_url, "started_at": started, "completed_at": time.time(), "inventory": {"status": status, "bytes": len(body), "title": p.title.strip(), "description": p.description, "lang": p.lang, "viewport": p.viewport, "canonical": p.canonical, "headings": len(p.headings), "h1": p.h1_count, "links": len(p.links), "images": p.images, "images_missing_alt": p.images_missing_alt, "forms": p.forms, "json_ld_blocks": p.json_ld}, "headers": {k.lower(): v for k, v in headers.items()}, "modules": modules, "findings": [asdict(f) for f in findings], "summary": {"finding_count": len(findings), **{level: sum(f.severity == level for f in findings) for level in ("critical", "high", "medium", "low", "info")}}}


def markdown_report(result: dict[str, Any]) -> str:
    lines = [f"# OPE Audit — {result['target']}", "", f"**Run:** `{result['run_id']}`  ", f"**HTTP:** `{result['inventory']['status']}`  ", f"**Findings:** `{result['summary']['finding_count']}`", "", "## Inventory", ""]
    lines += [f"- **{k}:** {v}" for k, v in result["inventory"].items()]
    lines += ["", "## Findings", ""]
    if not result["findings"]: lines.append("No findings were generated by the deterministic checks.")
    for f in sorted(result["findings"], key=lambda x: x["priority"], reverse=True):
        lines += [f"### {f['id']} — {f['severity'].upper()} — Priority {f['priority']}", f"**Module:** {f['module']}", f"**Symptom:** {f['symptom']}", "", "**Remediation:**"] + [f"- {x}" for x in f["remediation"]] + ["", "**Validation:**"] + [f"- {x}" for x in f["validation"]] + [""]
    return "\n".join(lines)
