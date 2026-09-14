"""Tests for crawlability analysis."""
from __future__ import annotations

from ope.crawlability import analyze_page_crawlability, analyze_site_crawlability
from ope.crawler import RobotsRule


def _block_rules() -> list[RobotsRule]:
    return [RobotsRule(user_agent="*", directive="disallow", value="/blocked", line=1)]


class TestAnalyzePageCrawlability:
    def test_default_crawlable(self) -> None:
        r = analyze_page_crawlability("http://example.com/page")
        assert r.is_crawlable
        assert r.robots_status == "ALLOW"

    def test_robots_blocked(self) -> None:
        rules = _block_rules()
        r = analyze_page_crawlability("http://example.com/blocked", robots_rules=rules)
        assert not r.is_crawlable
        assert r.robots_status == "BLOCK"
        assert any(s["signal"] == "robots_blocked" for s in r.signals)

    def test_robots_allowed(self) -> None:
        rules = _block_rules()
        r = analyze_page_crawlability("http://example.com/allowed", robots_rules=rules)
        assert r.is_crawlable

    def test_meta_noindex_signal(self) -> None:
        r = analyze_page_crawlability("http://example.com/page", meta_robots="noindex, follow")
        assert any(s["signal"] == "meta_noindex" for s in r.signals)

    def test_meta_nofollow_signal(self) -> None:
        r = analyze_page_crawlability("http://example.com/page", meta_robots="nofollow")
        assert any(s["signal"] == "meta_nofollow" for s in r.signals)

    def test_meta_none_signal(self) -> None:
        r = analyze_page_crawlability("http://example.com/page", meta_robots="none")
        assert any(s["signal"] == "meta_none" for s in r.signals)

    def test_deep_page_signal(self) -> None:
        r = analyze_page_crawlability("http://example.com/deep", depth=7)
        assert any(s["signal"] == "deep_page" for s in r.signals)

    def test_no_deep_signal_at_5(self) -> None:
        r = analyze_page_crawlability("http://example.com/page", depth=5)
        assert not any(s["signal"] == "deep_page" for s in r.signals)

    def test_orphan_signal(self) -> None:
        r = analyze_page_crawlability("http://example.com/orphan", depth=1, incoming_links=0)
        assert any(s["signal"] == "orphan_page" for s in r.signals)

    def test_no_orphan_at_root(self) -> None:
        r = analyze_page_crawlability("http://example.com/", depth=0, incoming_links=0)
        assert not any(s["signal"] == "orphan_page" for s in r.signals)

    def test_conflict_robots_block_no_noindex(self) -> None:
        rules = _block_rules()
        r = analyze_page_crawlability("http://example.com/blocked", robots_rules=rules, meta_robots="follow")
        assert len(r.conflicts) > 0
        assert "robots.txt blocks" in r.conflicts[0]

    def test_to_dict(self) -> None:
        r = analyze_page_crawlability("http://example.com/page", depth=2)
        d = r.to_dict()
        assert d["url"] == "http://example.com/page"
        assert d["depth"] == 2


class TestAnalyzeSiteCrawlability:
    def test_basic_analysis(self) -> None:
        pages = [
            {"url": "http://example.com/", "meta_robots": "", "depth": 0, "incoming_links": 5},
            {"url": "http://example.com/about", "meta_robots": "", "depth": 1, "incoming_links": 2},
            {"url": "http://example.com/deep", "meta_robots": "", "depth": 7, "incoming_links": 1},
        ]
        result = analyze_site_crawlability(pages)
        assert result["total_pages"] == 3
        assert result["deep_pages"] == 1
        assert result["max_depth"] == 7

    def test_with_robots_blocked(self) -> None:
        rules = _block_rules()
        pages = [
            {"url": "http://example.com/blocked", "meta_robots": "", "depth": 1, "incoming_links": 0},
        ]
        result = analyze_site_crawlability(pages, robots_rules=rules)
        assert result["blocked_by_robots"] == 1

    def test_sitemap_comparison(self) -> None:
        pages = [{"url": "http://example.com/", "meta_robots": "", "depth": 0, "incoming_links": 0}]
        sitemap = {"http://example.com/", "http://example.com/extra"}
        crawled = {"http://example.com/"}
        result = analyze_site_crawlability(pages, sitemap_urls=sitemap, crawled_urls=crawled)
        assert result["sitemap_comparison"] is not None
        assert result["sitemap_comparison"]["sitemap_only"] == 1

    def test_no_sitemap_comparison_without_urls(self) -> None:
        result = analyze_site_crawlability([])
        assert result["sitemap_comparison"] is None

    def test_empty_pages(self) -> None:
        result = analyze_site_crawlability([])
        assert result["total_pages"] == 0
        assert result["avg_depth"] == 0
