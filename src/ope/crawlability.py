"""Crawlability analysis — robots, depth, linking, sitemap coverage."""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from . import crawler as robots_mod


@dataclass
class CrawlabilityResult:
    url: str
    is_crawlable: bool = True
    robots_status: str = "ALLOW"
    depth: int = 0
    incoming_links: int = 0
    signals: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url, "is_crawlable": self.is_crawlable,
            "robots_status": self.robots_status, "depth": self.depth,
            "incoming_links": self.incoming_links,
            "signals": self.signals, "conflicts": self.conflicts,
        }


def analyze_page_crawlability(
    url: str, *,
    robots_rules: list[Any] | None = None,
    meta_robots: str = "",
    depth: int = 0,
    incoming_links: int = 0,
) -> CrawlabilityResult:
    """Analyze crawlability of a single page from observed signals."""
    result = CrawlabilityResult(url=url, depth=depth, incoming_links=incoming_links)
    path = urllib.parse.urlparse(url).path or "/"

    if robots_rules is not None:
        for agent in ("Googlebot", "*"):
            access = robots_mod.effective_access(robots_rules, agent, path)
            if access == "BLOCK":
                result.signals.append({"signal": "robots_blocked", "agent": agent, "path": path})
                result.is_crawlable = False
                result.robots_status = "BLOCK"
                break

    if meta_robots:
        directives = {d.strip().lower() for d in meta_robots.split(",")}
        if "noindex" in directives:
            result.signals.append({"signal": "meta_noindex", "value": meta_robots})
        if "nofollow" in directives:
            result.signals.append({"signal": "meta_nofollow", "value": meta_robots})
        if "none" in directives:
            result.signals.append({"signal": "meta_none", "value": meta_robots})

    if depth > 5:
        result.signals.append({"signal": "deep_page", "depth": depth})

    if result.robots_status == "BLOCK" and meta_robots and "noindex" not in meta_robots.lower():
        result.conflicts.append("robots.txt blocks crawling but page has no noindex")

    if incoming_links == 0 and depth > 0:
        result.signals.append({"signal": "orphan_page", "incoming_links": 0})

    return result


def analyze_site_crawlability(
    pages: list[dict[str, Any]],
    robots_rules: list[Any] | None = None,
    sitemap_urls: set[str] | None = None,
    crawled_urls: set[str] | None = None,
) -> dict[str, Any]:
    """Site-level crawlability analysis."""
    results: list[dict[str, Any]] = []
    blocked_count = 0; deep_count = 0; orphan_count = 0

    for page in pages:
        r = analyze_page_crawlability(
            page.get("url", ""), robots_rules=robots_rules,
            meta_robots=page.get("meta_robots", ""),
            depth=page.get("depth", 0), incoming_links=page.get("incoming_links", 0),
        )
        results.append(r.to_dict())
        if not r.is_crawlable: blocked_count += 1
        if r.depth > 5: deep_count += 1
        if r.incoming_links == 0 and r.depth > 0: orphan_count += 1

    sitemap_comparison = None
    if sitemap_urls is not None and crawled_urls is not None:
        from .sitemap import compare_sitemap_crawl
        sitemap_comparison = compare_sitemap_crawl(sitemap_urls, crawled_urls)

    depths = [p.get("depth", 0) for p in pages]
    return {
        "total_pages": len(pages),
        "blocked_by_robots": blocked_count,
        "deep_pages": deep_count,
        "orphan_pages": orphan_count,
        "max_depth": max(depths, default=0),
        "avg_depth": round(sum(depths) / len(depths), 1) if depths else 0,
        "sitemap_comparison": sitemap_comparison,
        "page_results": results,
    }
