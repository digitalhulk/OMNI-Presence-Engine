"""Tests for the site-level audit orchestrator."""
from __future__ import annotations

from unittest import mock

from ope.engine import normalize_site_result
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


class TestSiteFindingSchema:
    """Verify site findings conform to the engine finding schema."""

    @mock.patch("ope.site_audit.crawl")
    @mock.patch("ope.site_audit.discover_sitemaps")
    @mock.patch("ope.site_audit.robots_mod.fetch_robots")
    @mock.patch("ope.site_audit.validate_target")
    def test_findings_have_engine_fields(
        self, mock_vt: mock.Mock, mock_robots: mock.Mock,
        mock_sitemaps: mock.Mock, mock_crawl: mock.Mock,
    ) -> None:
        from ope.site_crawler import CrawledPage, CrawlResult, CrawlStatus
        from ope.url import TargetStatus, TargetValidation

        mock_vt.return_value = TargetValidation(
            url="http://example.com", status=TargetStatus.VALID,
            normalized="http://example.com/", addresses=("93.184.216.34",),
        )
        mock_robots.return_value = {"rules": [], "sitemaps": []}
        mock_sitemaps.return_value = []

        seed = CrawledPage(
            url="http://example.com/", normalized_url="http://example.com/",
            status_code=200, crawl_status=CrawlStatus.SUCCESS,
            content_type="text/html",
            body=b"<html><head></head><body></body></html>",
            charset="utf-8", depth=0,
        )
        orphan = CrawledPage(
            url="http://example.com/orphan", normalized_url="http://example.com/orphan",
            status_code=200, crawl_status=CrawlStatus.SUCCESS,
            content_type="text/html",
            body=b"<html><head></head><body>orphan page</body></html>",
            charset="utf-8", depth=1,
        )
        mock_crawl.return_value = CrawlResult(
            seed_url="http://example.com/",
            pages=[seed, orphan],
            pages_crawled=2, pages_discovered=2,
        )

        result = site_audit("http://example.com", config=SiteAuditConfig(delay=0))
        assert result.status == "COMPLETED"
        assert len(result.findings) > 0

        for f in result.findings:
            assert "id" in f
            assert "module" in f
            assert "symptom" in f
            assert "severity" in f
            assert "status" in f
            assert "priority" in f
            assert isinstance(f["priority"], float)
            assert isinstance(f["evidence"], list)
            for e in f["evidence"]:
                assert "confidence" in e

    def test_findings_use_module_codes(self) -> None:
        """Module values should use NN-name format matching the 20-module registry."""
        from ope.page_record import LinkGraph, PageRecord
        from ope.site_audit import _generate_findings

        graph = LinkGraph()
        graph.add_page(PageRecord(url="http://example.com/", status_code=200, depth=0))

        result = SiteAuditResult(
            target="http://example.com",
            normalized_target="http://example.com/",
            status="COMPLETED",
            started_at=1000.0,
            metadata_summary={"pages_analyzed": 5, "missing_title": 2, "missing_description": 0, "missing_og": 0},
        )
        findings = _generate_findings(result, graph)
        for f in findings:
            assert "-" in f["module"], f"Module {f['module']} should use NN-name format"


class TestNormalizeSiteResult:
    def test_stamps_engine_contract(self) -> None:
        site = SiteAuditResult(
            target="http://example.com",
            normalized_target="http://example.com/",
            status="COMPLETED",
            started_at=1000.0,
            completed_at=1005.0,
            duration_s=5.0,
        )
        result = normalize_site_result(site.to_dict())
        assert result["engine_contract"] == "evidence-diagnostic-v1"
        assert result["engine_scope"] == "site"

    def test_findings_are_normalized(self) -> None:
        site_dict = {
            "status": "COMPLETED",
            "target": "http://example.com",
            "findings": [
                {"id": "site-001", "module": "04-crawl", "symptom": "orphans", "severity": "medium",
                 "status": "OBSERVED", "priority": 0.5,
                 "root_cause": "Pages are not linked from any other internal page",
                 "evidence": [{"source": "test", "confidence": 0.8}]},
            ],
        }
        result = normalize_site_result(site_dict)
        f = result["findings"][0]
        assert "confidence" in f
        assert "affected_layer" in f
        assert f["status"] == "OBSERVED"

    def test_checks_are_executed(self) -> None:
        site_dict = {
            "status": "COMPLETED",
            "target": "http://example.com",
            "findings": [],
        }
        result = normalize_site_result(site_dict)
        assert "checks" in result
        assert isinstance(result["checks"], dict)
        assert len(result["checks"]) > 0

    def test_modules_are_reconciled(self) -> None:
        site_dict = {
            "status": "COMPLETED",
            "target": "http://example.com",
            "findings": [],
        }
        result = normalize_site_result(site_dict)
        assert "modules" in result
        for module_number, module in result["modules"].items():
            assert "status" in module

    def test_site_evidence_injected_into_inventory(self) -> None:
        site_dict = {
            "status": "COMPLETED",
            "target": "http://example.com",
            "findings": [],
            "crawl_summary": {"pages_crawled": 10, "pages_discovered": 12, "errors": 1, "total_bytes": 50000, "duration_s": 5.0},
            "metadata_summary": {"pages_analyzed": 10, "missing_title": 1, "missing_description": 2, "missing_og": 3, "avg_completeness": 0.75},
        }
        result = normalize_site_result(site_dict)
        inv = result["inventory"]
        assert "site_crawl_stats" in inv
        assert inv["site_crawl_stats"]["pages_crawled"] == 10
        assert "site_metadata" in inv
        assert inv["site_metadata"]["missing_title"] == 1
