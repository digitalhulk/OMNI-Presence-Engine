"""Site-level audit orchestrator — ties crawl, inventory, and analysis together."""
from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from . import USER_AGENT
from . import crawler as robots_mod
from .crawlability import analyze_site_crawlability
from .indexability import analyze_indexability, find_duplicate_candidates
from .metadata import extract_metadata
from .page_record import LinkGraph, build_link_graph
from .site_crawler import CrawlConfig, CrawlResult, CrawlStatus, crawl
from .sitemap import discover_sitemaps, sitemap_url_inventory
from .url import TargetStatus, validate_target


@dataclass
class SiteAuditConfig:
    max_pages: int = 200
    max_depth: int = 10
    timeout: int = 15
    delay: float = 0.5
    allow_subdomains: bool = False
    fetch_sitemaps: bool = True
    fetch_robots: bool = True
    max_retries: int = 2
    user_agent: str = USER_AGENT


@dataclass
class SiteAuditResult:
    target: str
    normalized_target: str
    status: str
    started_at: float
    completed_at: float = 0.0
    duration_s: float = 0.0
    robots: dict[str, Any] | None = None
    sitemaps: list[dict[str, Any]] | None = None
    crawl_summary: dict[str, Any] | None = None
    pages: list[dict[str, Any]] = field(default_factory=list)
    link_graph: dict[str, Any] | None = None
    metadata_summary: dict[str, Any] | None = None
    indexability: list[dict[str, Any]] = field(default_factory=list)
    crawlability: dict[str, Any] | None = None
    duplicate_candidates: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "target": self.target, "normalized_target": self.normalized_target,
            "status": self.status, "started_at": self.started_at,
            "completed_at": self.completed_at, "duration_s": round(self.duration_s, 2),
        }
        for key in ("robots", "sitemaps", "crawl_summary", "pages", "link_graph",
                     "metadata_summary", "indexability", "crawlability",
                     "duplicate_candidates", "findings", "error"):
            val = getattr(self, key)
            if val:
                d[key] = val
        return d


def site_audit(url: str, config: SiteAuditConfig | None = None) -> SiteAuditResult:
    """Run a complete site-level audit."""
    cfg = config or SiteAuditConfig()
    started = time.time()

    validation = validate_target(url)
    if validation.status != TargetStatus.VALID:
        return SiteAuditResult(
            target=url, normalized_target=validation.normalized or url,
            status="INVALID_TARGET", started_at=started,
            completed_at=time.time(), duration_s=time.time() - started,
            error=validation.reason,
        )

    normalized = validation.normalized
    result = SiteAuditResult(target=url, normalized_target=normalized, status="RUNNING", started_at=started)
    parsed = urllib.parse.urlparse(normalized)
    origin_host = (parsed.hostname or "").lower()

    # 1. Robots
    robots_rules: list[robots_mod.RobotsRule] | None = None
    robots_sitemaps: list[str] = []
    if cfg.fetch_robots:
        try:
            robots_data = robots_mod.fetch_robots(normalized, timeout=cfg.timeout)
            result.robots = robots_data
            raw_rules = robots_data.get("rules", [])
            robots_rules = []
            for r in raw_rules:
                if isinstance(r, dict):
                    robots_rules.append(robots_mod.RobotsRule(
                        user_agent=r.get("user_agent", ""),
                        directive=r.get("directive", ""),
                        value=r.get("value", ""),
                        line=r.get("line", 0),
                    ))
            robots_sitemaps = robots_data.get("sitemaps", [])
        except Exception as exc:
            result.robots = {"error": str(exc)}

    # 2. Sitemaps
    sitemap_url_set: set[str] = set()
    if cfg.fetch_sitemaps:
        try:
            sitemap_results = discover_sitemaps(normalized, robots_sitemaps=robots_sitemaps, timeout=cfg.timeout)
            result.sitemaps = [sr.to_dict() for sr in sitemap_results]
            inv = sitemap_url_inventory(sitemap_results)
            sitemap_url_set = set(inv.keys())
        except Exception as exc:
            result.sitemaps = [{"error": str(exc)}]

    # 3. Crawl
    crawl_config = CrawlConfig(
        max_pages=cfg.max_pages, max_depth=cfg.max_depth, timeout=cfg.timeout,
        delay=cfg.delay, max_retries=cfg.max_retries,
        allow_subdomains=cfg.allow_subdomains, user_agent=cfg.user_agent,
        respect_robots=cfg.fetch_robots,
    )
    crawl_result = crawl(normalized, config=crawl_config, robots_rules=robots_rules)
    result.crawl_summary = crawl_result.to_dict()

    # 4. Link graph + inventory
    graph = build_link_graph(crawl_result.pages, origin_host)
    result.link_graph = graph.to_dict()
    result.pages = [p.to_dict() for p in graph.pages.values()]

    # 5. Metadata
    _analyze_metadata(result, crawl_result)

    # 6. Indexability
    _analyze_indexability(result, crawl_result, graph)

    # 7. Crawlability
    _analyze_crawlability(result, graph, robots_rules, sitemap_url_set, crawl_result)

    # 8. Duplicates
    page_dicts = [{"url": u, "title": p.title, "canonical": p.canonical} for u, p in graph.pages.items()]
    result.duplicate_candidates = find_duplicate_candidates(page_dicts)

    # 9. Findings
    result.findings = _generate_findings(result, graph)

    result.status = "COMPLETED"
    result.completed_at = time.time()
    result.duration_s = result.completed_at - result.started_at
    return result


def _analyze_metadata(result: SiteAuditResult, crawl_result: CrawlResult) -> None:
    missing_title = 0; missing_desc = 0; missing_og = 0; total = 0
    completeness: list[float] = []
    for page in crawl_result.pages:
        if not page.is_html() or page.crawl_status != CrawlStatus.SUCCESS:
            continue
        meta = extract_metadata(page.body, page.charset, page.headers.get("content-language", ""))
        total += 1
        completeness.append(meta.completeness_score())
        if not meta.title: missing_title += 1
        if not meta.description: missing_desc += 1
        if not (meta.og_title and meta.og_image): missing_og += 1
    result.metadata_summary = {
        "pages_analyzed": total, "missing_title": missing_title,
        "missing_description": missing_desc, "missing_og": missing_og,
        "avg_completeness": round(sum(completeness) / len(completeness), 2) if completeness else 0,
    }


def _analyze_indexability(result: SiteAuditResult, crawl_result: CrawlResult, graph: LinkGraph) -> None:
    for page in crawl_result.pages:
        pr = graph.pages.get(page.normalized_url)
        idx = analyze_indexability(
            page.normalized_url, status_code=page.status_code,
            meta_robots=pr.meta_robots if pr else "",
            canonical=pr.canonical if pr else "",
            redirect_target=page.final_url if page.final_url != page.normalized_url else "",
        )
        result.indexability.append(idx.to_dict())


def _analyze_crawlability(
    result: SiteAuditResult, graph: LinkGraph,
    robots_rules: list[robots_mod.RobotsRule] | None,
    sitemap_url_set: set[str], crawl_result: CrawlResult,
) -> None:
    crawl_page_dicts = [{
        "url": u, "meta_robots": p.meta_robots,
        "depth": p.depth, "incoming_links": len(p.incoming_links),
    } for u, p in graph.pages.items()]
    crawled_url_set = {p.normalized_url for p in crawl_result.pages if p.crawl_status == CrawlStatus.SUCCESS}
    result.crawlability = analyze_site_crawlability(
        crawl_page_dicts, robots_rules=robots_rules,
        sitemap_urls=sitemap_url_set or None,
        crawled_urls=crawled_url_set or None,
    )


_SEVERITY_PRIORITY: dict[str, float] = {
    "critical": 0.9, "high": 0.7, "medium": 0.5, "low": 0.3, "info": 0.1,
}


def _generate_findings(result: SiteAuditResult, graph: LinkGraph) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    fid = 0

    def add(
        module: str, symptom: str, severity: str,
        evidence: list[dict[str, Any]],
        root_cause: str = "", **kw: Any,
    ) -> None:
        nonlocal fid
        fid += 1
        for e in evidence:
            e.setdefault("confidence", 0.8)
        findings.append({
            "id": f"site-{fid:03d}",
            "module": module,
            "symptom": symptom,
            "severity": severity,
            "status": "OBSERVED",
            "priority": _SEVERITY_PRIORITY.get(severity, 0.5),
            "root_cause": root_cause,
            "evidence": evidence,
            **kw,
        })

    orphans = graph.orphan_candidates()
    if orphans:
        add("04-crawl", f"{len(orphans)} orphan page(s) with no incoming internal links", "medium",
            [{"source": "link_graph", "value": orphans[:20]}],
            root_cause="Pages are not linked from any other internal page",
            remediation=["Add internal links to orphan pages from relevant content pages"],
            validation=["Re-crawl and verify all pages have at least one incoming internal link"])

    deep = [u for u, p in graph.pages.items() if p.depth > 5]
    if deep:
        add("04-crawl", f"{len(deep)} page(s) at depth > 5", "low",
            [{"source": "crawl", "value": {"count": len(deep), "urls": deep[:10]}}],
            root_cause="Site structure places content too many clicks from the homepage",
            remediation=["Reduce click depth by improving internal linking"],
            validation=["Re-crawl and verify max depth is 5 or fewer"])

    ms = result.metadata_summary or {}
    if ms.get("missing_title", 0):
        add("03-code", f"{ms['missing_title']} page(s) missing title tag", "high",
            [{"source": "metadata_analysis", "value": {"missing_title": ms["missing_title"]}}],
            root_cause="Pages lack a <title> element",
            remediation=["Add unique, descriptive <title> to every page"],
            validation=["Re-crawl and verify all pages have a non-empty title tag"])
    if ms.get("missing_description", 0):
        add("03-code", f"{ms['missing_description']} page(s) missing meta description", "medium",
            [{"source": "metadata_analysis", "value": {"missing_description": ms["missing_description"]}}],
            root_cause="Pages lack a meta description element",
            remediation=["Add meta description to improve CTR in search results"],
            validation=["Re-crawl and verify all pages have a meta description"])
    if ms.get("missing_og", 0):
        add("03-code", f"{ms['missing_og']} page(s) missing Open Graph metadata", "low",
            [{"source": "metadata_analysis", "value": {"missing_og": ms["missing_og"]}}],
            root_cause="Pages lack og:title and/or og:image tags",
            remediation=["Add og:title and og:image for social sharing"],
            validation=["Re-crawl and verify Open Graph tags are present"])

    non_idx = [i for i in result.indexability if i.get("status") == "NON_INDEXABLE"]
    if non_idx:
        add("05-index", f"{len(non_idx)} page(s) are non-indexable", "medium",
            [{"source": "indexability_analysis", "value": {"count": len(non_idx), "urls": [i["url"] for i in non_idx[:10]]}}],
            root_cause="Pages are blocked from indexing by meta robots, X-Robots-Tag, or non-2xx status")

    if result.duplicate_candidates:
        add("05-index", f"{len(result.duplicate_candidates)} potential duplicate content group(s)", "medium",
            [{"source": "duplicate_detection", "value": result.duplicate_candidates[:5]}],
            root_cause="Multiple pages share the same title or canonical URL",
            remediation=["Consolidate duplicate pages with canonical tags or redirects"],
            validation=["Re-crawl and verify duplicate groups are resolved"])

    cs = result.crawl_summary or {}
    if cs.get("errors", 0):
        add("04-crawl", f"{cs['errors']} page(s) returned crawl errors", "medium",
            [{"source": "crawl", "value": {"error_count": cs["errors"]}}],
            root_cause="Server returned error status codes during crawl")

    comparison = (result.crawlability or {}).get("sitemap_comparison")
    if comparison:
        so = comparison.get("sitemap_only", 0)
        co = comparison.get("crawl_only", 0)
        if so:
            add("04-crawl", f"{so} URL(s) in sitemap but not discovered by crawl", "medium",
                [{"source": "sitemap_crawl_comparison", "value": {"sitemap_only": so}}],
                root_cause="Sitemap contains URLs that are not reachable through internal links",
                remediation=["Ensure sitemap-only URLs are linked from the site or remove from sitemap"],
                validation=["Re-crawl and verify sitemap/crawl overlap"])
        if co:
            add("04-crawl", f"{co} crawled URL(s) missing from sitemap", "low",
                [{"source": "sitemap_crawl_comparison", "value": {"crawl_only": co}}],
                root_cause="Crawled pages are not listed in the sitemap",
                remediation=["Add crawled URLs to sitemap for faster discovery"],
                validation=["Verify all indexable URLs appear in the sitemap"])

    return findings
