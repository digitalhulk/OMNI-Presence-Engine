"""Tests for URL normalization, target validation, and crawl scope."""
from __future__ import annotations

import socket
from unittest import mock

import pytest

from ope.url import (
    TargetStatus,
    make_scope,
    normalize_url,
    resolve_url,
    url_depth,
    validate_target,
    validate_url_strict,
)

# ---- A. URL normalization ----

class TestNormalizeURL:
    def test_lowercase_scheme_and_host(self) -> None:
        assert normalize_url("HTTP://Example.COM/path") == "http://example.com/path"

    def test_strip_default_port_http(self) -> None:
        assert normalize_url("http://example.com:80/") == "http://example.com/"

    def test_strip_default_port_https(self) -> None:
        assert normalize_url("https://example.com:443/p") == "https://example.com/p"

    def test_keep_non_default_port(self) -> None:
        assert normalize_url("http://example.com:8080/p") == "http://example.com:8080/p"

    def test_empty_path_becomes_slash(self) -> None:
        assert normalize_url("http://example.com") == "http://example.com/"

    def test_trailing_slash_preserved(self) -> None:
        assert normalize_url("http://example.com/dir/") == "http://example.com/dir/"

    def test_trailing_slash_absent_preserved(self) -> None:
        assert normalize_url("http://example.com/page") == "http://example.com/page"

    def test_path_normalization_dot(self) -> None:
        assert normalize_url("http://example.com/a/./b") == "http://example.com/a/b"

    def test_path_normalization_dotdot(self) -> None:
        assert normalize_url("http://example.com/a/b/../c") == "http://example.com/a/c"

    def test_query_params_sorted(self) -> None:
        assert normalize_url("http://example.com/?b=2&a=1") == "http://example.com/?a=1&b=2"

    def test_fragment_stripped(self) -> None:
        assert normalize_url("http://example.com/page#section") == "http://example.com/page"

    def test_strip_trailing_dot_from_host(self) -> None:
        assert normalize_url("http://example.com./path") == "http://example.com/path"

    def test_idempotent(self) -> None:
        url = "http://example.com/path?a=1"
        assert normalize_url(normalize_url(url)) == normalize_url(url)

    def test_unsupported_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported scheme"):
            normalize_url("ftp://example.com")

    def test_no_hostname_raises(self) -> None:
        with pytest.raises(ValueError, match="no hostname"):
            normalize_url("http:///path")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            normalize_url("http://example.com/" + "a" * 9000)

    def test_percent_encoding_normalized(self) -> None:
        result = normalize_url("http://example.com/p%61th")
        assert result == "http://example.com/path"

    def test_keeps_needed_encoding(self) -> None:
        result = normalize_url("http://example.com/a%20b")
        assert "%20" in result

    def test_empty_query_preserved(self) -> None:
        result = normalize_url("http://example.com/?key=")
        assert "key=" in result

    def test_too_many_query_params_raises(self) -> None:
        params = "&".join(f"p{i}=v" for i in range(200))
        with pytest.raises(ValueError, match="query parameters"):
            normalize_url(f"http://example.com/?{params}")


# ---- B. Target validation ----

class TestValidateTarget:
    def test_valid_without_dns(self) -> None:
        result = validate_target("https://example.com", resolve_dns=False)
        assert result.status == TargetStatus.VALID
        assert result.normalized == "https://example.com/"

    def test_invalid_scheme(self) -> None:
        result = validate_target("ftp://example.com")
        assert result.status == TargetStatus.UNSUPPORTED

    def test_empty_url(self) -> None:
        result = validate_target("")
        assert result.status == TargetStatus.INVALID

    def test_none_url(self) -> None:
        result = validate_target(None)  # type: ignore[arg-type]
        assert result.status == TargetStatus.INVALID

    def test_loopback_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))]
            result = validate_target("http://evil.example.com")
            assert result.status == TargetStatus.BLOCKED
            assert "restricted" in result.reason.lower()

    def test_private_ip_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))]
            result = validate_target("http://internal.example.com")
            assert result.status == TargetStatus.BLOCKED

    def test_dns_failure(self) -> None:
        with mock.patch("socket.getaddrinfo", side_effect=socket.gaierror("fail")):
            result = validate_target("http://nonexistent.invalid")
            assert result.status == TargetStatus.INVALID
            assert "DNS" in result.reason

    def test_valid_public_ip(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
            result = validate_target("http://example.com")
            assert result.status == TargetStatus.VALID
            assert "93.184.216.34" in result.addresses

    def test_validate_url_strict_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_url_strict("ftp://example.com")

    def test_validate_url_strict_ok(self) -> None:
        with mock.patch("socket.getaddrinfo") as m:
            m.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
            result = validate_url_strict("http://example.com/path")
            assert result == "http://example.com/path"


# ---- C. Crawl scope ----

class TestCrawlScope:
    def test_same_origin_in_scope(self) -> None:
        scope = make_scope("https://example.com")
        assert scope.in_scope("https://example.com/page")

    def test_different_host_out_of_scope(self) -> None:
        scope = make_scope("https://example.com")
        assert not scope.in_scope("https://other.com/page")

    def test_different_scheme_out_of_scope(self) -> None:
        scope = make_scope("https://example.com")
        assert not scope.in_scope("http://example.com/page")

    def test_subdomain_out_by_default(self) -> None:
        scope = make_scope("https://example.com")
        assert not scope.in_scope("https://blog.example.com/post")

    def test_subdomain_in_when_allowed(self) -> None:
        scope = make_scope("https://example.com", allow_subdomains=True)
        assert scope.in_scope("https://blog.example.com/post")

    def test_non_default_port_out_of_scope(self) -> None:
        scope = make_scope("https://example.com")
        assert not scope.in_scope("https://example.com:8443/page")

    def test_invalid_url_out_of_scope(self) -> None:
        scope = make_scope("https://example.com")
        assert not scope.in_scope("not-a-url")

    def test_ftp_out_of_scope(self) -> None:
        scope = make_scope("https://example.com")
        assert not scope.in_scope("ftp://example.com/file")


# ---- URL depth ----

class TestURLDepth:
    def test_root(self) -> None:
        assert url_depth("http://example.com/") == 0

    def test_one_level(self) -> None:
        assert url_depth("http://example.com/about") == 1

    def test_deep(self) -> None:
        assert url_depth("http://example.com/a/b/c/d") == 4

    def test_trailing_slash(self) -> None:
        assert url_depth("http://example.com/a/b/") == 2


class TestResolveURL:
    def test_absolute(self) -> None:
        assert resolve_url("http://example.com/", "http://other.com/page") == "http://other.com/page"

    def test_relative_path(self) -> None:
        assert resolve_url("http://example.com/dir/page", "other") == "http://example.com/dir/other"

    def test_root_relative(self) -> None:
        assert resolve_url("http://example.com/dir/page", "/top") == "http://example.com/top"

    def test_protocol_relative(self) -> None:
        result = resolve_url("https://example.com/page", "//cdn.example.com/js/app.js")
        assert result == "https://cdn.example.com/js/app.js"
