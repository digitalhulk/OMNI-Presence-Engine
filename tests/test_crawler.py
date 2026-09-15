import pytest

import ope.crawler as crawler_module
from ope.crawler import analyze_robots, effective_access, fetch_robots, parse_robots, robots_url


def test_parse_robots_and_effective_ai_access():
    text = """User-agent: *\nDisallow: /private\nAllow: /private/public\n\nUser-agent: GPTBot\nDisallow: /\nAllow: /public\nSitemap: https://example.com/sitemap.xml\n"""
    rules = parse_robots(text)
    assert effective_access(rules, "GPTBot", "/") == "BLOCK"
    assert effective_access(rules, "GPTBot", "/public") == "ALLOW"
    assert effective_access(rules, "PerplexityBot", "/private") == "BLOCK"


def test_analyze_robots_returns_observed_ai_matrix():
    result = analyze_robots("User-agent: GPTBot\nDisallow: /\n")
    assert result["ai_crawlers"]["GPTBot"] == "BLOCK"
    assert "GPTBot" in result["blocked_ai_crawlers"]
    assert result["rule_count"] == 1


def test_specific_agent_overrides_wildcard():
    result = analyze_robots("User-agent: *\nDisallow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n")
    assert result["ai_crawlers"]["OAI-SearchBot"] == "ALLOW"
    assert result["ai_crawlers"]["ClaudeBot"] == "BLOCK"


def test_robots_url_constructs_correct_path(monkeypatch):
    monkeypatch.setattr(crawler_module, "validate_url_strict", lambda url: url)
    assert robots_url("https://example.com/some/page") == "https://example.com/robots.txt"


def test_robots_url_preserves_port(monkeypatch):
    monkeypatch.setattr(crawler_module, "validate_url_strict", lambda url: url)
    assert robots_url("https://example.com:8443/page") == "https://example.com:8443/robots.txt"


def test_robots_url_rejects_unsafe_target():
    with pytest.raises(ValueError):
        robots_url("http://127.0.0.1/")


class _FakeResp:
    """Context-manager response for mocking ope.net.open_url."""
    def __init__(self, body=b"", status=200):
        self._body = body
        self.status = status
        self.headers = type("H", (), {"get_content_charset": lambda self: "utf-8"})()

    def read(self, limit=None):
        return self._body[:limit] if limit is not None else self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _fake_open_url(monkeypatch, body=b"", status=200, error=None, capture=None):
    def opener(url, *, timeout=10, headers=None):
        if capture is not None:
            capture["url"] = url
            capture["headers"] = headers or {}
        if error is not None:
            raise error
        return _FakeResp(body, status)
    import ope.net as net_module
    monkeypatch.setattr(net_module, "open_url", opener)


def test_fetch_robots_returns_structured_result(monkeypatch):
    _fake_open_url(monkeypatch, body=b"User-agent: *\nDisallow: /private\nSitemap: https://example.com/sitemap.xml\n")
    result = fetch_robots("https://example.com/")
    assert result["status"] == 200
    assert result["error"] is None
    assert result["url"] == "https://example.com/robots.txt"
    assert result["rule_count"] == 2
    assert result["sitemaps"] == ["https://example.com/sitemap.xml"]
    assert "GPTBot" in result["ai_crawlers"]


def test_fetch_robots_handles_network_error(monkeypatch):
    _fake_open_url(monkeypatch, error=OSError("connection refused"))
    result = fetch_robots("https://example.com/")
    assert result["status"] is None
    assert "connection refused" in result["error"]
    assert result["rule_count"] == 0


def test_fetch_robots_enforces_size_limit(monkeypatch):
    _fake_open_url(monkeypatch, body=b"x" * (crawler_module.MAX_ROBOTS_BYTES + 1))
    result = fetch_robots("https://example.com/")
    assert result["error"] is not None
    assert "safety limit" in result["error"]


def test_fetch_robots_uses_dynamic_user_agent(monkeypatch):
    capture = {}
    _fake_open_url(monkeypatch, body=b"", capture=capture)
    fetch_robots("https://example.com/")
    ua = capture["headers"].get("User-Agent")
    assert ua == crawler_module.USER_AGENT
    # Derived from the package version, never the stale hardcoded "OPE-Audit/0.1".
    assert ua != "OPE-Audit/0.1"
    assert ua.startswith("OPE-Audit/")
