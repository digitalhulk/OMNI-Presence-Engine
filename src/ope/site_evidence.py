"""Bridge from SiteAuditResult data into single-page audit inventory keys.

Pattern follows browser_evidence.py: inject site-level signals into an
inventory dict via setdefault() so the audit pipeline can consume them.
Never overwrites existing keys.
"""
from __future__ import annotations

from typing import Any


def inject_site_evidence(
    inventory: dict[str, Any],
    site_result: dict[str, Any],
) -> None:
    """Enrich an audit inventory with site-level signals.

    Writes new keys only — never overwrites existing inventory entries.
    Expects *site_result* to be the dict form of a SiteAuditResult.
    """
    if not isinstance(site_result, dict):
        return
    if site_result.get("status") != "COMPLETED":
        return

    _inject_crawl_stats(inventory, site_result)
    _inject_link_graph(inventory, site_result)
    _inject_duplicates(inventory, site_result)
    _inject_sitemap_coverage(inventory, site_result)
    _inject_metadata_summary(inventory, site_result)
    _inject_indexability_summary(inventory, site_result)


def _inject_crawl_stats(inventory: dict[str, Any], site_result: dict[str, Any]) -> None:
    cs = site_result.get("crawl_summary")
    if not isinstance(cs, dict):
        return
    crawlability = site_result.get("crawlability")
    depth_stats: dict[str, Any] = {}
    if isinstance(crawlability, dict):
        depth_stats = {
            "max_depth": crawlability.get("max_depth", 0),
            "avg_depth": crawlability.get("avg_depth", 0),
            "deep_pages": crawlability.get("deep_pages", 0),
            "orphan_pages": crawlability.get("orphan_pages", 0),
            "blocked_by_robots": crawlability.get("blocked_by_robots", 0),
        }

    stats: dict[str, Any] = {
        "pages_crawled": cs.get("pages_crawled", 0),
        "pages_discovered": cs.get("pages_discovered", 0),
        "errors": cs.get("errors", 0),
        "total_bytes": cs.get("total_bytes", 0),
        "duration_s": cs.get("duration_s", 0),
        **depth_stats,
    }
    inventory.setdefault("site_crawl_stats", stats)


def _inject_link_graph(inventory: dict[str, Any], site_result: dict[str, Any]) -> None:
    lg = site_result.get("link_graph")
    if not isinstance(lg, dict):
        return
    stats = lg.get("stats")
    if not isinstance(stats, dict):
        return
    graph_summary: dict[str, Any] = {
        "page_count": lg.get("page_count", 0),
        "link_count": lg.get("link_count", 0),
        "total_internal_links": stats.get("total_internal_links", 0),
        "total_external_links": stats.get("total_external_links", 0),
        "orphan_pages": stats.get("pages_with_no_incoming", 0),
        "avg_incoming": stats.get("avg_incoming", 0),
        "avg_outgoing": stats.get("avg_outgoing", 0),
        "max_incoming": stats.get("max_incoming", 0),
        "max_outgoing": stats.get("max_outgoing", 0),
        "orphan_candidates": lg.get("orphan_candidates", []),
    }
    inventory.setdefault("site_link_graph", graph_summary)


def _inject_duplicates(inventory: dict[str, Any], site_result: dict[str, Any]) -> None:
    dupes = site_result.get("duplicate_candidates")
    if not isinstance(dupes, list) or not dupes:
        return
    summary: dict[str, Any] = {
        "group_count": len(dupes),
        "groups": dupes,
    }
    inventory.setdefault("site_duplicates", summary)


def _inject_sitemap_coverage(inventory: dict[str, Any], site_result: dict[str, Any]) -> None:
    crawlability = site_result.get("crawlability")
    if not isinstance(crawlability, dict):
        return
    comparison = crawlability.get("sitemap_comparison")
    if not isinstance(comparison, dict):
        return
    coverage: dict[str, Any] = {
        "sitemap_urls": comparison.get("sitemap_urls", 0),
        "crawled_urls": comparison.get("crawled_urls", 0),
        "overlap": comparison.get("overlap", 0),
        "sitemap_only": comparison.get("sitemap_only", 0),
        "crawl_only": comparison.get("crawl_only", 0),
        "sitemap_coverage": comparison.get("sitemap_coverage", 0),
        "crawl_coverage": comparison.get("crawl_coverage", 0),
    }
    inventory.setdefault("site_sitemap_coverage", coverage)


def _inject_metadata_summary(inventory: dict[str, Any], site_result: dict[str, Any]) -> None:
    ms = site_result.get("metadata_summary")
    if not isinstance(ms, dict):
        return
    summary: dict[str, Any] = {
        "pages_analyzed": ms.get("pages_analyzed", 0),
        "missing_title": ms.get("missing_title", 0),
        "missing_description": ms.get("missing_description", 0),
        "missing_og": ms.get("missing_og", 0),
        "avg_completeness": ms.get("avg_completeness", 0),
    }
    inventory.setdefault("site_metadata", summary)


def _inject_indexability_summary(inventory: dict[str, Any], site_result: dict[str, Any]) -> None:
    idx_list = site_result.get("indexability")
    if not isinstance(idx_list, list) or not idx_list:
        return
    total = len(idx_list)
    non_indexable = sum(1 for i in idx_list if isinstance(i, dict) and i.get("status") == "NON_INDEXABLE")
    conditional = sum(1 for i in idx_list if isinstance(i, dict) and i.get("status") == "CONDITIONAL")
    indexable = sum(1 for i in idx_list if isinstance(i, dict) and i.get("status") == "INDEXABLE")
    summary: dict[str, Any] = {
        "total_pages": total,
        "indexable": indexable,
        "non_indexable": non_indexable,
        "conditional": conditional,
    }
    inventory.setdefault("site_indexability", summary)
