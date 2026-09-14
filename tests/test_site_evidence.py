"""Tests for the site evidence injection module."""
from __future__ import annotations

from ope.site_evidence import inject_site_evidence


def _make_site_result(
    status: str = "COMPLETED",
    crawl_summary: dict | None = None,
    crawlability: dict | None = None,
    link_graph: dict | None = None,
    duplicate_candidates: list | None = None,
    metadata_summary: dict | None = None,
    indexability: list | None = None,
) -> dict:
    return {
        "status": status,
        "target": "https://example.com",
        "normalized_target": "https://example.com/",
        "crawl_summary": crawl_summary,
        "crawlability": crawlability,
        "link_graph": link_graph,
        "duplicate_candidates": duplicate_candidates,
        "metadata_summary": metadata_summary,
        "indexability": indexability,
    }


class TestInjectSiteEvidence:
    def test_non_completed_result_no_injection(self) -> None:
        inv: dict = {}
        inject_site_evidence(inv, _make_site_result(status="INVALID_TARGET"))
        assert not inv

    def test_non_dict_result_no_injection(self) -> None:
        inv: dict = {}
        inject_site_evidence(inv, "not a dict")  # type: ignore[arg-type]
        assert not inv

    def test_crawl_stats_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(
            crawl_summary={"pages_crawled": 50, "pages_discovered": 60, "errors": 2, "total_bytes": 500000, "duration_s": 12.5},
            crawlability={"max_depth": 4, "avg_depth": 2.1, "deep_pages": 1, "orphan_pages": 3, "blocked_by_robots": 0},
        )
        inject_site_evidence(inv, site)
        stats = inv["site_crawl_stats"]
        assert stats["pages_crawled"] == 50
        assert stats["errors"] == 2
        assert stats["max_depth"] == 4
        assert stats["orphan_pages"] == 3

    def test_crawl_stats_without_crawlability(self) -> None:
        inv: dict = {}
        site = _make_site_result(
            crawl_summary={"pages_crawled": 10, "pages_discovered": 10, "errors": 0, "total_bytes": 100000, "duration_s": 5.0},
        )
        inject_site_evidence(inv, site)
        stats = inv["site_crawl_stats"]
        assert stats["pages_crawled"] == 10
        assert "max_depth" not in stats

    def test_link_graph_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(link_graph={
            "page_count": 20,
            "link_count": 100,
            "stats": {
                "total_internal_links": 80,
                "total_external_links": 20,
                "pages_with_no_incoming": 2,
                "avg_incoming": 4.0,
                "avg_outgoing": 5.0,
                "max_incoming": 12,
                "max_outgoing": 8,
            },
            "orphan_candidates": ["/page-a", "/page-b"],
        })
        inject_site_evidence(inv, site)
        lg = inv["site_link_graph"]
        assert lg["page_count"] == 20
        assert lg["total_internal_links"] == 80
        assert lg["orphan_pages"] == 2
        assert lg["orphan_candidates"] == ["/page-a", "/page-b"]

    def test_link_graph_missing_stats(self) -> None:
        inv: dict = {}
        site = _make_site_result(link_graph={"page_count": 5, "link_count": 10})
        inject_site_evidence(inv, site)
        assert "site_link_graph" not in inv

    def test_duplicates_injected(self) -> None:
        inv: dict = {}
        dupes = [
            {"type": "duplicate_title", "key": "Home", "urls": ["/a", "/b"]},
            {"type": "shared_canonical", "key": "/c", "urls": ["/c", "/d"]},
        ]
        site = _make_site_result(duplicate_candidates=dupes)
        inject_site_evidence(inv, site)
        assert inv["site_duplicates"]["group_count"] == 2
        assert len(inv["site_duplicates"]["groups"]) == 2

    def test_empty_duplicates_not_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(duplicate_candidates=[])
        inject_site_evidence(inv, site)
        assert "site_duplicates" not in inv

    def test_sitemap_coverage_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(crawlability={
            "sitemap_comparison": {
                "sitemap_urls": 100,
                "crawled_urls": 80,
                "overlap": 70,
                "sitemap_only": 30,
                "crawl_only": 10,
                "sitemap_coverage": 0.7,
                "crawl_coverage": 0.875,
            },
        })
        inject_site_evidence(inv, site)
        cov = inv["site_sitemap_coverage"]
        assert cov["sitemap_urls"] == 100
        assert cov["overlap"] == 70
        assert cov["sitemap_only"] == 30

    def test_sitemap_coverage_no_comparison(self) -> None:
        inv: dict = {}
        site = _make_site_result(crawlability={"total_pages": 10})
        inject_site_evidence(inv, site)
        assert "site_sitemap_coverage" not in inv

    def test_metadata_summary_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(metadata_summary={
            "pages_analyzed": 30,
            "missing_title": 2,
            "missing_description": 5,
            "missing_og": 10,
            "avg_completeness": 0.72,
        })
        inject_site_evidence(inv, site)
        meta = inv["site_metadata"]
        assert meta["pages_analyzed"] == 30
        assert meta["missing_title"] == 2
        assert meta["avg_completeness"] == 0.72

    def test_indexability_summary_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(indexability=[
            {"url": "/a", "status": "INDEXABLE"},
            {"url": "/b", "status": "INDEXABLE"},
            {"url": "/c", "status": "NON_INDEXABLE"},
            {"url": "/d", "status": "CONDITIONAL"},
        ])
        inject_site_evidence(inv, site)
        idx = inv["site_indexability"]
        assert idx["total_pages"] == 4
        assert idx["indexable"] == 2
        assert idx["non_indexable"] == 1
        assert idx["conditional"] == 1

    def test_empty_indexability_not_injected(self) -> None:
        inv: dict = {}
        site = _make_site_result(indexability=[])
        inject_site_evidence(inv, site)
        assert "site_indexability" not in inv

    def test_no_overwrite_existing_keys(self) -> None:
        inv: dict = {"site_crawl_stats": {"pages_crawled": 999}}
        site = _make_site_result(
            crawl_summary={"pages_crawled": 50, "pages_discovered": 60, "errors": 0, "total_bytes": 100, "duration_s": 1},
        )
        inject_site_evidence(inv, site)
        assert inv["site_crawl_stats"]["pages_crawled"] == 999

    def test_full_injection(self) -> None:
        inv: dict = {}
        site = _make_site_result(
            crawl_summary={"pages_crawled": 20, "pages_discovered": 25, "errors": 1, "total_bytes": 200000, "duration_s": 8.0},
            crawlability={
                "max_depth": 3, "avg_depth": 1.5, "deep_pages": 0, "orphan_pages": 1, "blocked_by_robots": 0,
                "sitemap_comparison": {"sitemap_urls": 25, "crawled_urls": 20, "overlap": 18, "sitemap_only": 7, "crawl_only": 2, "sitemap_coverage": 0.72, "crawl_coverage": 0.9},
            },
            link_graph={
                "page_count": 20, "link_count": 60,
                "stats": {"total_internal_links": 50, "total_external_links": 10, "pages_with_no_incoming": 1, "avg_incoming": 2.5, "avg_outgoing": 3.0, "max_incoming": 8, "max_outgoing": 6},
                "orphan_candidates": ["/orphan"],
            },
            duplicate_candidates=[{"type": "duplicate_title", "key": "Test", "urls": ["/x", "/y"]}],
            metadata_summary={"pages_analyzed": 20, "missing_title": 1, "missing_description": 3, "missing_og": 5, "avg_completeness": 0.8},
            indexability=[{"url": "/a", "status": "INDEXABLE"}, {"url": "/b", "status": "NON_INDEXABLE"}],
        )
        inject_site_evidence(inv, site)
        assert "site_crawl_stats" in inv
        assert "site_link_graph" in inv
        assert "site_duplicates" in inv
        assert "site_sitemap_coverage" in inv
        assert "site_metadata" in inv
        assert "site_indexability" in inv
