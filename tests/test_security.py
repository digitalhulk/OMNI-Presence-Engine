"""Security boundary tests — SSRF, private networks, resource limits."""
from __future__ import annotations

import socket
from unittest import mock

import pytest

from ope.url import TargetStatus, normalize_url, validate_target, validate_url_strict


class TestSSRFProtection:
    """Verify that private/loopback/reserved addresses are blocked."""

    def test_localhost_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]
            result = validate_target("http://localhost")
            assert result.status == TargetStatus.BLOCKED

    def test_loopback_ipv4_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]
            result = validate_target("http://127.0.0.1")
            assert result.status == TargetStatus.BLOCKED

    def test_loopback_ipv6_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0))]
            result = validate_target("http://ipv6-loopback.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_private_10_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))]
            result = validate_target("http://internal.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_private_172_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("172.16.0.1", 0))]
            result = validate_target("http://internal2.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_private_192_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))]
            result = validate_target("http://router.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_link_local_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.1.1", 0))]
            result = validate_target("http://link-local.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_multicast_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("224.0.0.1", 0))]
            result = validate_target("http://multicast.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_unspecified_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("0.0.0.0", 0))]
            result = validate_target("http://zero.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_public_ip_allowed(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
            result = validate_target("http://example.com")
            assert result.status == TargetStatus.VALID

    def test_validate_url_strict_raises_on_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]
            with pytest.raises(ValueError, match="restricted"):
                validate_url_strict("http://localhost")


class TestSchemeRestrictions:
    def test_ftp_rejected(self) -> None:
        result = validate_target("ftp://example.com")
        assert result.status == TargetStatus.UNSUPPORTED

    def test_file_rejected(self) -> None:
        with pytest.raises(ValueError, match="scheme"):
            normalize_url("file:///etc/passwd")

    def test_data_rejected(self) -> None:
        with pytest.raises(ValueError, match="scheme"):
            normalize_url("data:text/html,<h1>hi</h1>")

    def test_javascript_rejected(self) -> None:
        with pytest.raises(ValueError, match="scheme"):
            normalize_url("javascript:alert(1)")

    def test_empty_url(self) -> None:
        result = validate_target("")
        assert result.status == TargetStatus.INVALID

    def test_none_url(self) -> None:
        result = validate_target(None)  # type: ignore[arg-type]
        assert result.status == TargetStatus.INVALID


class TestResourceLimits:
    def test_url_too_long(self) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            normalize_url("http://example.com/" + "a" * 9000)

    def test_too_many_query_params(self) -> None:
        params = "&".join(f"p{i}=v" for i in range(200))
        with pytest.raises(ValueError, match="query parameters"):
            normalize_url(f"http://example.com/?{params}")


class TestDNSErrors:
    def test_dns_failure(self) -> None:
        with mock.patch("socket.getaddrinfo", side_effect=socket.gaierror("fail")):
            result = validate_target("http://nonexistent.invalid")
            assert result.status == TargetStatus.INVALID
            assert "DNS" in result.reason

    def test_no_addresses(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = []
            result = validate_target("http://empty.example.com")
            assert result.status == TargetStatus.INVALID


class TestMalformedInput:
    def test_malformed_xml_sitemap(self) -> None:
        from ope.sitemap import parse_sitemap_xml
        result = parse_sitemap_xml(b"<not-valid-xml!!!><<<")
        assert result.error is not None

    def test_unrecognized_xml_root(self) -> None:
        from ope.sitemap import parse_sitemap_xml
        result = parse_sitemap_xml(b"<root><item>test</item></root>")
        assert result.error is not None
        assert "Unrecognized" in result.error

    def test_malformed_html_metadata(self) -> None:
        from ope.metadata import extract_metadata
        meta = extract_metadata("<not>real<html at='all")
        assert meta.title == ""

    def test_empty_html_metadata(self) -> None:
        from ope.metadata import extract_metadata
        meta = extract_metadata("")
        assert meta.completeness_score() == 0.0

    def test_deeply_nested_html(self) -> None:
        from ope.metadata import extract_metadata
        html = "<div>" * 500 + "<title>Deep</title>" + "</div>" * 500
        meta = extract_metadata(html)
        assert meta.title == "Deep"


class TestCrawlerSafety:
    def test_crawl_invalid_seed(self) -> None:
        from ope.site_crawler import crawl
        result = crawl("not-a-url")
        assert result.errors == 1
        assert result.pages_crawled == 0

    def test_crawl_config_limits(self) -> None:
        from ope.site_crawler import CrawlConfig
        cfg = CrawlConfig()
        assert cfg.max_pages == 200
        assert cfg.max_depth == 10
        assert cfg.max_total_bytes == 50 * 1024 * 1024
        assert cfg.max_retries == 2

    def test_link_extractor_skips_dangerous(self) -> None:
        from ope.site_crawler import _extract_links
        html = b'''
        <a href="javascript:alert(1)">XSS</a>
        <a href="data:text/html,<h1>x</h1>">Data</a>
        <a href="mailto:x@y.com">Mail</a>
        <a href="tel:+1234">Phone</a>
        <a href="#section">Fragment</a>
        <a href="/safe">Safe</a>
        '''
        links = _extract_links(html, "utf-8", "http://example.com/")
        assert len(links) == 1
        assert "safe" in links[0]


class TestRedirectSafety:
    def test_site_audit_blocked_target(self) -> None:
        from ope.site_audit import site_audit
        result = site_audit("")
        assert result.status == "INVALID_TARGET"

    def test_site_audit_ftp(self) -> None:
        from ope.site_audit import site_audit
        result = site_audit("ftp://example.com")
        assert result.status == "INVALID_TARGET"
