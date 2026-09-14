"""XML sitemap parser and intelligence."""
from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

MAX_SITEMAP_BYTES = 50 * 1024 * 1024
MAX_SITEMAP_URLS = 50_000
MAX_SITEMAP_DEPTH = 3

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@dataclass
class SitemapURL:
    loc: str
    lastmod: str = ""
    changefreq: str = ""
    priority: str = ""


@dataclass
class SitemapResult:
    url: str
    status: int = 0
    error: str | None = None
    urls: list[SitemapURL] = field(default_factory=list)
    child_sitemaps: list[str] = field(default_factory=list)
    is_index: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url, "status": self.status, "error": self.error,
            "url_count": len(self.urls), "is_index": self.is_index,
            "child_sitemaps": self.child_sitemaps,
            "urls": [{"loc": u.loc, "lastmod": u.lastmod, "changefreq": u.changefreq, "priority": u.priority} for u in self.urls],
        }


def parse_sitemap_xml(content: bytes, url: str = "") -> SitemapResult:
    """Parse a sitemap XML document (urlset or sitemapindex)."""
    result = SitemapResult(url=url)
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        result.error = f"XML parse error: {exc}"
        return result
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if tag == "sitemapindex":
        result.is_index = True
        for sitemap in root.findall("sm:sitemap", _NS):
            loc = sitemap.findtext("sm:loc", "", _NS).strip()
            if loc:
                result.child_sitemaps.append(loc)
        if not result.child_sitemaps:
            for sitemap in root.findall("sitemap"):
                loc_el = sitemap.find("loc")
                if loc_el is not None and loc_el.text:
                    result.child_sitemaps.append(loc_el.text.strip())
    elif tag == "urlset":
        for url_el in root.findall("sm:url", _NS)[:MAX_SITEMAP_URLS]:
            loc = url_el.findtext("sm:loc", "", _NS).strip()
            if loc:
                result.urls.append(SitemapURL(
                    loc=loc,
                    lastmod=url_el.findtext("sm:lastmod", "", _NS).strip(),
                    changefreq=url_el.findtext("sm:changefreq", "", _NS).strip(),
                    priority=url_el.findtext("sm:priority", "", _NS).strip(),
                ))
        if not result.urls:
            for url_el in root.findall("url")[:MAX_SITEMAP_URLS]:
                loc_el = url_el.find("loc")
                if loc_el is not None and loc_el.text:
                    result.urls.append(SitemapURL(
                        loc=loc_el.text.strip(),
                        lastmod=(url_el.findtext("lastmod") or "").strip(),
                        changefreq=(url_el.findtext("changefreq") or "").strip(),
                        priority=(url_el.findtext("priority") or "").strip(),
                    ))
    else:
        result.error = f"Unrecognized root element: {tag}"
    return result


def _fetch_sitemap_bytes(url: str, timeout: int = 15) -> tuple[bytes, int]:
    from .url import validate_url_strict
    safe = validate_url_strict(url)
    req = urllib.request.Request(safe, headers={"User-Agent": "OPE-Audit/0.1"}, method="GET")
    with urllib.request.urlopen(req, timeout=max(1, min(timeout, 30))) as resp:
        body = resp.read(MAX_SITEMAP_BYTES + 1)
        if len(body) > MAX_SITEMAP_BYTES:
            raise ValueError(f"Sitemap exceeds {MAX_SITEMAP_BYTES} byte limit")
        return body, resp.status


def fetch_sitemap(url: str, *, timeout: int = 15, max_depth: int = MAX_SITEMAP_DEPTH, _depth: int = 0) -> list[SitemapResult]:
    """Fetch and parse a sitemap, following sitemapindex references."""
    results: list[SitemapResult] = []
    try:
        body, status = _fetch_sitemap_bytes(url, timeout)
        result = parse_sitemap_xml(body, url)
        result.status = status
    except Exception as exc:
        result = SitemapResult(url=url, error=str(exc))
    results.append(result)
    if result.is_index and _depth < max_depth:
        for child_url in result.child_sitemaps:
            results.extend(fetch_sitemap(child_url, timeout=timeout, max_depth=max_depth, _depth=_depth + 1))
    return results


def discover_sitemaps(base_url: str, robots_sitemaps: list[str] | None = None, timeout: int = 15) -> list[SitemapResult]:
    """Discover and fetch all sitemaps for a site."""
    from .url import normalize_url
    parsed = urllib.parse.urlparse(normalize_url(base_url))
    origin = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = list(robots_sitemaps or [])
    well_known = f"{origin}/sitemap.xml"
    if well_known not in candidates:
        candidates.append(well_known)
    index_candidate = f"{origin}/sitemap_index.xml"
    if index_candidate not in candidates:
        candidates.append(index_candidate)
    all_results: list[SitemapResult] = []
    seen: set[str] = set()
    for sm_url in candidates:
        if sm_url in seen:
            continue
        seen.add(sm_url)
        fetched = fetch_sitemap(sm_url, timeout=timeout)
        all_results.extend(fetched)
        for r in fetched:
            seen.add(r.url)
    return all_results


def sitemap_url_inventory(results: list[SitemapResult]) -> dict[str, SitemapURL]:
    """Build a deduplicated URL inventory from sitemap results."""
    from .url import normalize_url
    inventory: dict[str, SitemapURL] = {}
    for result in results:
        for u in result.urls:
            try:
                norm = normalize_url(u.loc)
            except ValueError:
                norm = u.loc
            if norm not in inventory:
                inventory[norm] = u
    return inventory


def compare_sitemap_crawl(sitemap_urls: set[str], crawled_urls: set[str]) -> dict[str, Any]:
    """Compare sitemap inventory against crawl inventory."""
    in_both = sitemap_urls & crawled_urls
    sitemap_only = sitemap_urls - crawled_urls
    crawl_only = crawled_urls - sitemap_urls
    return {
        "in_both": len(in_both),
        "sitemap_only": len(sitemap_only),
        "crawl_only": len(crawl_only),
        "sitemap_only_urls": sorted(sitemap_only),
        "crawl_only_urls": sorted(crawl_only),
        "sitemap_coverage": round(len(in_both) / len(sitemap_urls), 3) if sitemap_urls else 0.0,
        "crawl_coverage": round(len(in_both) / len(crawled_urls), 3) if crawled_urls else 0.0,
    }
