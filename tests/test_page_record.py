"""Tests for page inventory, link graph, and orphan detection."""
from __future__ import annotations

from ope.page_record import (
    LinkGraph,
    LinkRecord,
    PageRecord,
    build_link_graph,
)
from ope.site_crawler import CrawledPage, CrawlStatus


class TestPageRecord:
    def test_to_dict(self) -> None:
        r = PageRecord(url="http://example.com/", status_code=200, title="Home")
        d = r.to_dict()
        assert d["url"] == "http://example.com/"
        assert d["title"] == "Home"
        assert d["outgoing_links_count"] == 0


class TestLinkRecord:
    def test_to_dict(self) -> None:
        lr = LinkRecord(source="http://a.com/", target="http://b.com/", is_internal=False)
        d = lr.to_dict()
        assert d["source"] == "http://a.com/"
        assert d["is_internal"] is False


class TestLinkGraph:
    def _make_graph(self) -> LinkGraph:
        g = LinkGraph()
        g.add_page(PageRecord(url="http://example.com/", status_code=200, depth=0))
        g.add_page(PageRecord(url="http://example.com/about", status_code=200, depth=1))
        g.add_page(PageRecord(url="http://example.com/contact", status_code=200, depth=1))
        g.add_link(LinkRecord(source="http://example.com/", target="http://example.com/about", is_internal=True))
        g.rebuild_incoming()
        return g

    def test_add_page_and_link(self) -> None:
        g = self._make_graph()
        assert len(g.pages) == 3
        assert len(g.links) == 1

    def test_orphan_candidates(self) -> None:
        g = self._make_graph()
        orphans = g.orphan_candidates()
        assert "http://example.com/contact" in orphans
        assert "http://example.com/" not in orphans
        assert "http://example.com/about" not in orphans

    def test_orphan_excludes_root(self) -> None:
        g = LinkGraph()
        g.add_page(PageRecord(url="http://example.com/", status_code=200, depth=0))
        assert g.orphan_candidates() == []

    def test_internal_link_stats(self) -> None:
        g = self._make_graph()
        stats = g.internal_link_stats()
        assert stats["total_internal_links"] == 1
        assert stats["total_external_links"] == 0
        assert stats["pages_with_no_incoming"] == 1

    def test_to_dict(self) -> None:
        g = self._make_graph()
        d = g.to_dict()
        assert d["page_count"] == 3
        assert d["link_count"] == 1
        assert "stats" in d
        assert "orphan_candidates" in d

    def test_empty_graph(self) -> None:
        g = LinkGraph()
        assert g.orphan_candidates() == []
        stats = g.internal_link_stats()
        assert stats["total_internal_links"] == 0

    def test_rebuild_incoming(self) -> None:
        g = LinkGraph()
        g.add_page(PageRecord(url="http://example.com/", status_code=200, depth=0))
        g.add_page(PageRecord(url="http://example.com/a", status_code=200, depth=1))
        g.add_link(LinkRecord(source="http://example.com/", target="http://example.com/a", is_internal=True))
        g.rebuild_incoming()
        assert len(g.pages["http://example.com/a"].incoming_links) == 1
        g.rebuild_incoming()
        assert len(g.pages["http://example.com/a"].incoming_links) == 1


class TestBuildLinkGraph:
    def test_builds_from_crawled_pages(self) -> None:
        pages = [
            CrawledPage(
                url="http://example.com/",
                normalized_url="http://example.com/",
                status_code=200,
                crawl_status=CrawlStatus.SUCCESS,
                content_type="text/html",
                body=b"<html><head><title>Home</title></head><body><h1>Home</h1></body></html>",
                charset="utf-8",
                depth=0,
                links=["http://example.com/about"],
            ),
            CrawledPage(
                url="http://example.com/about",
                normalized_url="http://example.com/about",
                status_code=200,
                crawl_status=CrawlStatus.SUCCESS,
                content_type="text/html",
                body=b"<html><head><title>About</title></head><body><h1>About Us</h1></body></html>",
                charset="utf-8",
                depth=1,
                links=["http://example.com/"],
            ),
        ]
        graph = build_link_graph(pages, "example.com")
        assert len(graph.pages) == 2
        assert graph.pages["http://example.com/"].title == "Home"
        assert graph.pages["http://example.com/about"].title == "About"
        assert len(graph.links) == 2

    def test_external_links(self) -> None:
        pages = [
            CrawledPage(
                url="http://example.com/",
                normalized_url="http://example.com/",
                status_code=200,
                crawl_status=CrawlStatus.SUCCESS,
                content_type="text/html",
                body=b"<html><head><title>Home</title></head><body></body></html>",
                charset="utf-8",
                depth=0,
                links=["http://other.com/page"],
            ),
        ]
        graph = build_link_graph(pages, "example.com")
        assert len(graph.links) == 1
        assert not graph.links[0].is_internal

    def test_non_html_skipped(self) -> None:
        pages = [
            CrawledPage(
                url="http://example.com/data.json",
                normalized_url="http://example.com/data.json",
                status_code=200,
                crawl_status=CrawlStatus.SUCCESS,
                content_type="application/json",
                body=b'{"key": "value"}',
                charset="utf-8",
                depth=0,
                links=[],
            ),
        ]
        graph = build_link_graph(pages, "example.com")
        assert len(graph.pages) == 1
        assert graph.pages["http://example.com/data.json"].title == ""

    def test_skips_non_crawled_page_objects(self) -> None:
        graph = build_link_graph(["not a CrawledPage"], "example.com")
        assert len(graph.pages) == 0
