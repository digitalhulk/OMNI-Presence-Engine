"""Production multi-page site crawler with safety limits and deduplication."""
from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
from typing import Any

from . import USER_AGENT
from .url import (
    normalize_url,
    resolve_url,
    url_depth,
    validate_url_strict,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 15
DEFAULT_DELAY = 0.5
MAX_RETRIES = 2


class CrawlStatus(str, Enum):
    SUCCESS = "SUCCESS"
    REDIRECT = "REDIRECT"
    CLIENT_ERROR = "CLIENT_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class CrawlConfig:
    max_pages: int = 200
    max_depth: int = 10
    max_total_bytes: int = 50 * 1024 * 1024
    timeout: int = DEFAULT_TIMEOUT
    delay: float = DEFAULT_DELAY
    max_retries: int = MAX_RETRIES
    allow_subdomains: bool = False
    user_agent: str = USER_AGENT
    respect_robots: bool = True


@dataclass
class CrawledPage:
    url: str
    normalized_url: str
    status_code: int
    crawl_status: CrawlStatus
    content_type: str = ""
    body: bytes = b""
    charset: str = "utf-8"
    headers: dict[str, str] = field(default_factory=dict)
    final_url: str = ""
    redirect_chain: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    depth: int = 0
    response_bytes: int = 0
    duration_ms: float = 0.0
    error: str = ""
    retries: int = 0

    def is_html(self) -> bool:
        ct = self.content_type.lower()
        return "text/html" in ct or "application/xhtml+xml" in ct


class _LinkExtractor(HTMLParser):
    """Minimal parser that extracts <a href> links."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                self.links.append(href)


class _RedirectTracker(urllib.request.HTTPRedirectHandler):
    """Records intermediate redirect URLs and validates each for SSRF."""
    def __init__(self) -> None:
        super().__init__()
        self.chain: list[str] = []

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> urllib.request.Request | None:
        safe = validate_url_strict(newurl)
        self.chain.append(safe)
        return super().redirect_request(req, fp, code, msg, headers, safe)


def _classify_status(code: int) -> CrawlStatus:
    if 200 <= code < 300: return CrawlStatus.SUCCESS
    if 300 <= code < 400: return CrawlStatus.REDIRECT
    if 400 <= code < 500: return CrawlStatus.CLIENT_ERROR
    if 500 <= code < 600: return CrawlStatus.SERVER_ERROR
    return CrawlStatus.ERROR


def _extract_links(body: bytes, charset: str, base_url: str) -> list[str]:
    try:
        text = body.decode(charset, errors="replace")
    except (LookupError, ValueError):
        text = body.decode("utf-8", errors="replace")
    parser = _LinkExtractor()
    try:
        parser.feed(text); parser.close()
    except Exception:
        pass
    resolved: list[str] = []
    for href in parser.links:
        try:
            resolved.append(resolve_url(base_url, href))
        except ValueError:
            continue
    return resolved


@dataclass
class CrawlResult:
    seed_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    total_bytes: int = 0
    duration_s: float = 0.0
    pages_crawled: int = 0
    pages_discovered: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_url": self.seed_url,
            "pages_crawled": self.pages_crawled,
            "pages_discovered": self.pages_discovered,
            "total_bytes": self.total_bytes,
            "duration_s": round(self.duration_s, 2),
            "errors": self.errors,
            "pages": [{
                "url": p.normalized_url, "status_code": p.status_code,
                "crawl_status": p.crawl_status.value, "content_type": p.content_type,
                "depth": p.depth, "response_bytes": p.response_bytes,
                "links_found": len(p.links), "final_url": p.final_url,
                "error": p.error, "duration_ms": round(p.duration_ms, 1),
            } for p in self.pages],
        }


def crawl(seed_url: str, config: CrawlConfig | None = None, robots_rules: list[Any] | None = None) -> CrawlResult:
    """BFS crawl starting from seed_url, staying within scope and limits."""
    from . import crawler as robots_mod
    from .url import make_scope

    cfg = config or CrawlConfig()
    result = CrawlResult(seed_url=seed_url)
    try:
        start_normalized = normalize_url(seed_url)
    except ValueError:
        result.errors = 1
        return result

    scope = make_scope(start_normalized, allow_subdomains=cfg.allow_subdomains,
                       max_depth=cfg.max_depth, max_pages=cfg.max_pages,
                       max_total_bytes=cfg.max_total_bytes)

    seen: dict[str, int] = {start_normalized: 0}
    queue: deque[tuple[str, int]] = deque([(start_normalized, 0)])
    start_time = time.monotonic()
    ctx = ssl.create_default_context()

    while queue and result.pages_crawled < cfg.max_pages:
        current_url, depth = queue.popleft()
        if depth > cfg.max_depth or result.total_bytes >= cfg.max_total_bytes:
            continue

        if cfg.respect_robots and robots_rules is not None:
            path = urllib.parse.urlparse(current_url).path or "/"
            access = robots_mod.effective_access(robots_rules, cfg.user_agent, path)
            if access == "BLOCK":
                result.pages.append(CrawledPage(
                    url=current_url, normalized_url=current_url,
                    status_code=0, crawl_status=CrawlStatus.BLOCKED,
                    depth=depth, error="Blocked by robots.txt",
                ))
                continue

        if result.pages_crawled > 0 and cfg.delay > 0:
            time.sleep(cfg.delay)

        page = _fetch_page(current_url, depth=depth, config=cfg, ssl_context=ctx)
        result.pages.append(page)
        result.pages_crawled += 1
        result.total_bytes += page.response_bytes
        if page.error:
            result.errors += 1

        if page.is_html() and page.crawl_status == CrawlStatus.SUCCESS:
            base = page.final_url or page.normalized_url
            links = _extract_links(page.body, page.charset, base)
            page.links = links
            for link in links:
                try:
                    norm = normalize_url(link)
                except ValueError:
                    continue
                if norm not in seen and scope.in_scope(norm) and url_depth(norm) <= cfg.max_depth:
                    seen[norm] = depth + 1
                    queue.append((norm, depth + 1))

    result.pages_discovered = len(seen)
    result.duration_s = time.monotonic() - start_time
    return result


def _fetch_page(url: str, *, depth: int, config: CrawlConfig, ssl_context: ssl.SSLContext) -> CrawledPage:
    """Fetch a single page with retry, SSRF protection, and redirect tracking."""
    page = CrawledPage(url=url, normalized_url=url, status_code=0, crawl_status=CrawlStatus.ERROR, depth=depth)

    for attempt in range(1 + config.max_retries):
        if attempt > 0:
            time.sleep(min(2 ** attempt, 10))
            page.retries = attempt

        try:
            safe_url = validate_url_strict(url)
        except ValueError as exc:
            page.crawl_status = CrawlStatus.BLOCKED; page.error = str(exc)
            return page

        tracker = _RedirectTracker()
        opener = urllib.request.build_opener(tracker, urllib.request.HTTPSHandler(context=ssl_context))
        opener.max_redirections = MAX_REDIRECTS  # type: ignore[attr-defined]
        start = time.perf_counter()

        try:
            req = urllib.request.Request(safe_url, headers={"User-Agent": config.user_agent}, method="GET")
            with opener.open(req, timeout=max(1, min(config.timeout, 60))) as resp:
                body = resp.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    page.error = f"Response exceeds {MAX_RESPONSE_BYTES} byte limit"
                    page.crawl_status = CrawlStatus.ERROR
                    return page
                page.status_code = resp.status
                page.crawl_status = _classify_status(resp.status)
                page.headers = {k.lower(): v for k, v in resp.headers.items()}
                page.content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                page.charset = resp.headers.get_content_charset() or "utf-8"
                page.body = body
                page.response_bytes = len(body)
                page.final_url = resp.geturl()
                page.redirect_chain = tracker.chain
                page.duration_ms = round((time.perf_counter() - start) * 1000, 1)
                page.error = ""
                return page
        except urllib.error.HTTPError as exc:
            page.status_code = exc.code
            page.crawl_status = _classify_status(exc.code)
            page.error = str(exc)
            page.duration_ms = round((time.perf_counter() - start) * 1000, 1)
            if 400 <= exc.code < 500:
                return page
        except urllib.error.URLError as exc:
            page.duration_ms = round((time.perf_counter() - start) * 1000, 1)
            reason = str(getattr(exc, "reason", exc))
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                page.crawl_status = CrawlStatus.TIMEOUT
            elif "name or service not known" in reason.lower() or "getaddrinfo" in reason.lower():
                page.crawl_status = CrawlStatus.DNS_ERROR
            else:
                page.crawl_status = CrawlStatus.ERROR
            page.error = reason
        except Exception as exc:
            page.duration_ms = round((time.perf_counter() - start) * 1000, 1)
            page.crawl_status = CrawlStatus.ERROR
            page.error = f"{type(exc).__name__}: {exc}"
    return page
