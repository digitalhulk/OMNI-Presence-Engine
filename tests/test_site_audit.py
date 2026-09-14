"""Tests for the site-level audit orchestrator."""
from __future__ import annotations

from unittest import mock

from ope.site_audit import SiteAuditConfig, SiteAuditResult, site_audit


class TestSiteAuditInvalidTarget:
    def test_invalid_url(self) -> None:
        result = site_audit("")
        assert result.status == "INVALID_TARGET"
        assert result.error

    def test_ftp_url(self) -> None:
        result = site_audit("ftp://example.com")
        assert result.status == "INVALID_TARGET"

    @mock.patch("ope.site_audit.validate_target")
    def test_blocked_target(self, mock_vt: mock.Mock) -> None:
        from ope.url import TargetStatus, TargetValidation
        mock_vt.return_value = TargetValidation(
            url="http://evil.local", status=TargetStatus.BLOCKED,
            normalized="", reason="Restricted address",
        )
        result = site_audit("http://evil.local")
        assert result.status == "INVALID_TARGET"
        assert "Restricted" in result.error


class TestSiteAuditConfig:
    def test_defaults(self) -> None:
        c = SiteAuditConfig()
        assert c.max_pages == 200
        assert c.fetch_sitemaps is True
        assert c.fetch_robots is True


class TestSiteAuditResult:
    def test_to_dict_minimal(self) -> None:
        r = SiteAuditResult(
            target="http://example.com",
            normalized_target="http://example.com/",
            status="COMPLETED",
            started_at=1000.0,
            completed_at=1005.0,
            duration_s=5.0,
        )
        d = r.to_dict()
        assert d["status"] == "COMPLETED"
        assert d["duration_s"] == 5.0
        assert "error" not in d

    def test_to_dict_with_error(self) -> None:
        r = SiteAuditResult(
            target="http://example.com",
            normalized_target="",
            status="INVALID_TARGET",
            started_at=1000.0,
            error="bad url",
        )
        d = r.to_dict()
        assert d["error"] == "bad url"


class TestSiteAuditOrchestration:
    @mock.patch("ope.site_audit.crawl")
    @mock.patch("ope.site_audit.discover_sitemaps")
    @mock.patch("ope.site_audit.robots_mod.fetch_robots")
    @mock.patch("ope.site_audit.validate_target")
    def test_full_orchestration(
        self, mock_vt: mock.Mock, mock_robots: mock.Mock,
        mock_sitemaps: mock.Mock, mock_crawl: mock.Mock,
    ) -> None:
        from ope.site_crawler import CrawledPage, CrawlResult, CrawlStatus
        from ope.url import TargetStatus, TargetValidation

        mock_vt.return_value = TargetValidation(
            url="http://example.com",
            status=TargetStatus.VALID,
            normalized="http://example.com/",
            addresses=("93.184.216.34",),
        )
        mock_robots.return_value = {"rules": [], "sitemaps": []}
        mock_sitemaps.return_value = []

        page = CrawledPage(
            url="http://example.com/",
            normalized_url="http://example.com/",
            status_code=200,
            crawl_status=CrawlStatus.SUCCESS,
            content_type="text/html",
            body=b"<html><head><title>Home</title><meta name='description' content='Test'></head><body><h1>Hello</h1></body></html>",
            charset="utf-8",
            depth=0,
        )
        mock_crawl.return_value = CrawlResult(
            seed_url="http://example.com/",
            pages=[page],
            pages_crawled=1,
            pages_discovered=1,
        )

        result = site_audit("http://example.com", config=SiteAuditConfig(delay=0))
        assert result.status == "COMPLETED"
        assert result.crawl_summary is not None
        assert result.link_graph is not None
        assert result.metadata_summary is not None
        assert result.crawlability is not None
        assert isinstance(result.findings, list)

    @mock.patch("ope.site_audit.crawl")
    @mock.patch("ope.site_audit.discover_sitemaps")
    @mock.patch("ope.site_audit.robots_mod.fetch_robots")
    @mock.patch("ope.site_audit.validate_target")
    def test_robots_exception_handled(
        self, mock_vt: mock.Mock, mock_robots: mock.Mock,
        mock_sitemaps: mock.Mock, mock_crawl: mock.Mock,
    ) -> None:
        from ope.site_crawler import CrawledPage, CrawlResult, CrawlStatus
        from ope.url import TargetStatus, TargetValidation

        mock_vt.return_value = TargetValidation(
            url="http://example.com",
            status=TargetStatus.VALID,
            normalized="http://example.com/",
            addresses=("93.184.216.34",),
        )
        mock_robots.side_effect = Exception("Robots fetch failed")
        mock_sitemaps.return_value = []

        page = CrawledPage(
            url="http://example.com/",
            normalized_url="http://example.com/",
            status_code=200,
            crawl_status=CrawlStatus.SUCCESS,
            content_type="text/html",
            body=b"<html><head><title>Test</title></head><body></body></html>",
            charset="utf-8",
            depth=0,
        )
        mock_crawl.return_value = CrawlResult(
            seed_url="http://example.com/",
            pages=[page],
            pages_crawled=1,
            pages_discovered=1,
        )

        result = site_audit("http://example.com", config=SiteAuditConfig(delay=0))
        assert result.status == "COMPLETED"
        assert result.robots is not None
        assert "error" in result.robots
