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


def test_fetch_robots_returns_structured_result(monkeypatch):
    monkeypatch.setattr(crawler_module, "validate_url_strict", lambda url: url)

    class _FakeResponse:
        status = 200
        def __init__(self): self.headers = _FakeHeaders()
        def read(self, limit=None): return b"User-agent: *\nDisallow: /private\nSitemap: https://example.com/sitemap.xml\n"
        def __enter__(self): return self
        def __exit__(self, *_): return False

    class _FakeHeaders:
        def get_content_charset(self): return "utf-8"

    monkeypatch.setattr(crawler_module.urllib.request, "urlopen", lambda req, timeout=10: _FakeResponse())
    result = fetch_robots("https://example.com/")
    assert result["status"] == 200
    assert result["error"] is None
    assert result["url"] == "https://example.com/robots.txt"
    assert result["rule_count"] == 2
    assert result["sitemaps"] == ["https://example.com/sitemap.xml"]
    assert "GPTBot" in result["ai_crawlers"]


def test_fetch_robots_handles_network_error(monkeypatch):
    monkeypatch.setattr(crawler_module, "validate_url_strict", lambda url: url)
    monkeypatch.setattr(crawler_module.urllib.request, "urlopen", lambda req, timeout=10: (_ for _ in ()).throw(OSError("connection refused")))
    result = fetch_robots("https://example.com/")
    assert result["status"] is None
    assert "connection refused" in result["error"]
    assert result["rule_count"] == 0


def test_fetch_robots_enforces_size_limit(monkeypatch):
    monkeypatch.setattr(crawler_module, "validate_url_strict", lambda url: url)

    class _OversizedResponse:
        status = 200
        def __init__(self): self.headers = type("H", (), {"get_content_charset": lambda self: "utf-8"})()
        def read(self, limit=None): return b"x" * (crawler_module.MAX_ROBOTS_BYTES + 1)
        def __enter__(self): return self
        def __exit__(self, *_): return False

    monkeypatch.setattr(crawler_module.urllib.request, "urlopen", lambda req, timeout=10: _OversizedResponse())
    result = fetch_robots("https://example.com/")
    assert result["error"] is not None
    assert "safety limit" in result["error"]


def test_fetch_robots_uses_dynamic_user_agent(monkeypatch):
    monkeypatch.setattr(crawler_module, "validate_url_strict", lambda url: url)
    captured = {}

    class _Resp:
        status = 200
        def __init__(self): self.headers = type("H", (), {"get_content_charset": lambda self: "utf-8"})()
        def read(self, limit=None): return b""
        def __enter__(self): return self
        def __exit__(self, *_): return False

    def fake_open(req, timeout=10):
        captured["ua"] = req.get_header("User-agent")
        return _Resp()

    monkeypatch.setattr(crawler_module.urllib.request, "urlopen", fake_open)
    fetch_robots("https://example.com/")
    assert captured["ua"] == crawler_module.USER_AGENT
    # The UA is derived dynamically from the package version, not the old
    # hardcoded "OPE-Audit/0.1". Guard against that exact stale value rather
    # than a naive "0.1" substring, which collides with versions like 0.11.0.
    assert captured["ua"] != "OPE-Audit/0.1"
    assert captured["ua"].startswith("OPE-Audit/")
