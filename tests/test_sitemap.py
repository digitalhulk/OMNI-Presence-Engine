"""Tests for sitemap parsing and intelligence."""
from __future__ import annotations

from ope.sitemap import (
    SitemapResult,
    SitemapURL,
    compare_sitemap_crawl,
    parse_sitemap_xml,
    sitemap_url_inventory,
)

URLSET_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2024-01-01</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://example.com/about</loc>
    <lastmod>2024-06-15</lastmod>
  </url>
  <url>
    <loc>https://example.com/contact</loc>
  </url>
</urlset>"""

INDEX_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
  </sitemap>
</sitemapindex>"""

NO_NS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset>
  <url><loc>https://example.com/no-ns</loc></url>
</urlset>"""


class TestParseSitemapXML:
    def test_urlset(self) -> None:
        result = parse_sitemap_xml(URLSET_XML, "https://example.com/sitemap.xml")
        assert not result.is_index
        assert len(result.urls) == 3
        assert result.urls[0].loc == "https://example.com/"
        assert result.urls[0].lastmod == "2024-01-01"
        assert result.urls[0].priority == "1.0"
        assert result.urls[1].loc == "https://example.com/about"
        assert result.error is None

    def test_sitemapindex(self) -> None:
        result = parse_sitemap_xml(INDEX_XML, "https://example.com/sitemap_index.xml")
        assert result.is_index
        assert len(result.child_sitemaps) == 2
        assert "sitemap-pages.xml" in result.child_sitemaps[0]

    def test_invalid_xml(self) -> None:
        result = parse_sitemap_xml(b"not xml at all", "bad")
        assert result.error is not None
        assert "XML parse error" in result.error

    def test_no_namespace(self) -> None:
        result = parse_sitemap_xml(NO_NS_XML)
        assert len(result.urls) == 1
        assert result.urls[0].loc == "https://example.com/no-ns"

    def test_unrecognized_root(self) -> None:
        result = parse_sitemap_xml(b"<root><item>test</item></root>")
        assert result.error is not None
        assert "Unrecognized" in result.error

    def test_to_dict(self) -> None:
        result = parse_sitemap_xml(URLSET_XML, "test")
        d = result.to_dict()
        assert d["url_count"] == 3
        assert d["is_index"] is False


class TestSitemapURLInventory:
    def test_deduplication(self) -> None:
        results = [
            SitemapResult(url="a", urls=[SitemapURL(loc="https://example.com/"), SitemapURL(loc="https://example.com/about")]),
            SitemapResult(url="b", urls=[SitemapURL(loc="https://example.com/"), SitemapURL(loc="https://example.com/contact")]),
        ]
        inv = sitemap_url_inventory(results)
        assert len(inv) == 3

    def test_empty(self) -> None:
        assert sitemap_url_inventory([]) == {}


class TestCompareSitemapCrawl:
    def test_comparison(self) -> None:
        sitemap = {"https://example.com/", "https://example.com/about", "https://example.com/sitemap-only"}
        crawled = {"https://example.com/", "https://example.com/about", "https://example.com/crawl-only"}
        result = compare_sitemap_crawl(sitemap, crawled)
        assert result["in_both"] == 2
        assert result["sitemap_only"] == 1
        assert result["crawl_only"] == 1
        assert "https://example.com/sitemap-only" in result["sitemap_only_urls"]
        assert "https://example.com/crawl-only" in result["crawl_only_urls"]

    def test_perfect_overlap(self) -> None:
        urls = {"https://example.com/a", "https://example.com/b"}
        result = compare_sitemap_crawl(urls, urls)
        assert result["sitemap_only"] == 0
        assert result["crawl_only"] == 0
        assert result["sitemap_coverage"] == 1.0

    def test_empty_sets(self) -> None:
        result = compare_sitemap_crawl(set(), set())
        assert result["in_both"] == 0
        assert result["sitemap_coverage"] == 0.0
