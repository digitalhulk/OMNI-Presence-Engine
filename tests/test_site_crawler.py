"""Tests for the production site crawler."""
from __future__ import annotations

from unittest import mock

from ope.site_crawler import (
    CrawlConfig,
    CrawledPage,
    CrawlResult,
    CrawlStatus,
    _classify_status,
    _extract_links,
    crawl,
)


class TestClassifyStatus:
    def test_200(self) -> None:
        assert _classify_status(200) == CrawlStatus.SUCCESS

    def test_301(self) -> None:
        assert _classify_status(301) == CrawlStatus.REDIRECT

    def test_404(self) -> None:
        assert _classify_status(404) == CrawlStatus.CLIENT_ERROR

    def test_500(self) -> None:
        assert _classify_status(500) == CrawlStatus.SERVER_ERROR

    def test_999(self) -> None:
        assert _classify_status(999) == CrawlStatus.ERROR


class TestCrawledPage:
    def test_is_html_text(self) -> None:
        p = CrawledPage(url="u", normalized_url="u", status_code=200, crawl_status=CrawlStatus.SUCCESS, content_type="text/html")
        assert p.is_html()

    def test_is_html_xhtml(self) -> None:
        p = CrawledPage(url="u", normalized_url="u", status_code=200, crawl_status=CrawlStatus.SUCCESS, content_type="application/xhtml+xml")
        assert p.is_html()

    def test_is_html_json(self) -> None:
        p = CrawledPage(url="u", normalized_url="u", status_code=200, crawl_status=CrawlStatus.SUCCESS, content_type="application/json")
        assert not p.is_html()

    def test_is_html_with_charset(self) -> None:
        p = CrawledPage(url="u", normalized_url="u", status_code=200, crawl_status=CrawlStatus.SUCCESS, content_type="text/html; charset=utf-8")
        assert p.is_html()


class TestExtractLinks:
    def test_basic_links(self) -> None:
        html = b'<html><body><a href="/about">About</a><a href="/contact">Contact</a></body></html>'
        links = _extract_links(html, "utf-8", "http://example.com/")
        assert len(links) == 2
        assert "http://example.com/about" in links
        assert "http://example.com/contact" in links

    def test_skips_fragments(self) -> None:
        html = b'<a href="#top">Top</a><a href="/real">Real</a>'
        links = _extract_links(html, "utf-8", "http://example.com/")
        assert len(links) == 1

    def test_skips_javascript(self) -> None:
        html = b'<a href="javascript:void(0)">JS</a>'
        links = _extract_links(html, "utf-8", "http://example.com/")
        assert len(links) == 0

    def test_skips_mailto(self) -> None:
        html = b'<a href="mailto:a@b.com">Mail</a>'
        links = _extract_links(html, "utf-8", "http://example.com/")
        assert len(links) == 0

    def test_resolves_relative(self) -> None:
        html = b'<a href="sub/page">Sub</a>'
        links = _extract_links(html, "utf-8", "http://example.com/dir/")
        assert "http://example.com/dir/sub/page" in links

    def test_bad_charset_fallback(self) -> None:
        html = b'<a href="/ok">OK</a>'
        links = _extract_links(html, "bogus-encoding", "http://example.com/")
        assert len(links) == 1


class TestCrawlConfig:
    def test_defaults(self) -> None:
        c = CrawlConfig()
        assert c.max_pages == 200
        assert c.max_depth == 10
        assert c.delay == 0.5
        assert c.respect_robots is True


class TestCrawlResult:
    def test_to_dict(self) -> None:
        r = CrawlResult(seed_url="http://example.com/")
        r.pages_crawled = 5
        r.pages_discovered = 10
        d = r.to_dict()
        assert d["pages_crawled"] == 5
        assert d["pages_discovered"] == 10
        assert d["seed_url"] == "http://example.com/"


class TestCrawlFunction:
    def test_invalid_seed(self) -> None:
        result = crawl("not-a-url")
        assert result.errors == 1
        assert result.pages_crawled == 0

    @mock.patch("ope.site_crawler._fetch_page")
    @mock.patch("ope.site_crawler.time.sleep")
    def test_single_page_no_links(self, mock_sleep: mock.Mock, mock_fetch: mock.Mock) -> None:
        mock_fetch.return_value = CrawledPage(
            url="http://example.com/",
            normalized_url="http://example.com/",
            status_code=200,
            crawl_status=CrawlStatus.SUCCESS,
            content_type="text/html",
            body=b"<html><body>Hello</body></html>",
            charset="utf-8",
        )
        cfg = CrawlConfig(max_pages=10, delay=0)
        result = crawl("http://example.com/", config=cfg)
        assert result.pages_crawled == 1
        assert result.errors == 0

    @mock.patch("ope.site_crawler._fetch_page")
    @mock.patch("ope.site_crawler.time.sleep")
    def test_respects_max_pages(self, mock_sleep: mock.Mock, mock_fetch: mock.Mock) -> None:
        def make_page(url: str, **kw: object) -> CrawledPage:
            return CrawledPage(
                url=url, normalized_url=url, status_code=200,
                crawl_status=CrawlStatus.SUCCESS, content_type="text/html",
                body=b'<a href="/a">A</a><a href="/b">B</a><a href="/c">C</a>',
                charset="utf-8",
            )
        mock_fetch.side_effect = make_page
        cfg = CrawlConfig(max_pages=2, delay=0)
        result = crawl("http://example.com/", config=cfg)
        assert result.pages_crawled == 2
