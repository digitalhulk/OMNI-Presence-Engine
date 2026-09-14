import ope.audit as audit_module
from ope.audit import PageParser, _finding, audit


def test_parser_extracts_core_signals():
    p = PageParser()
    p.feed('<html lang="en"><head><title>Test</title><meta name="viewport" content="width=device-width"><link rel="canonical" href="https://example.com/"></head><body><h1>Hello</h1><img src="a.jpg" alt="A"><img src="b.jpg"><script type="application/ld+json">{}</script></body></html>')
    assert p.title == "Test"
    assert p.lang == "en"
    assert p.h1_count == 1
    assert p.images == 2
    assert p.images_missing_alt == 1
    assert p.json_ld == 1
    assert p.canonical == "https://example.com/"


def test_parser_extracts_landmarks_meta_robots_and_hreflang():
    p = PageParser()
    p.feed(
        '<html><head><meta name="robots" content="noindex">'
        '<link rel="alternate" hreflang="fr" href="https://example.com/fr"></head>'
        "<body><header></header><nav></nav><main></main><footer></footer></body></html>"
    )
    assert p.meta_robots == "noindex"
    assert p.hreflang_count == 1
    assert p.landmarks == {"header", "nav", "main", "footer"}


def test_priority_is_bounded():
    f = _finding("T-1", "03-code", "test", "medium", [], [], [], impact=1, urgency=1, fixability=1)
    assert 0 <= f.priority <= 100


def test_audit_wires_robots_and_new_inventory_signals(monkeypatch):
    def fake_request(url, timeout=15):
        html = (
            '<html lang="en"><head><title>Test</title>'
            '<meta name="viewport" content="width=device-width">'
            '<meta name="description" content="A description long enough to plausibly pass the snippet length check here.">'
            '<link rel="canonical" href="https://example.com/"></head>'
            "<body><header></header><nav></nav><main><h1>Hi</h1></main><footer></footer></body></html>"
        )
        headers = {"Strict-Transport-Security": "max-age=1", "X-Content-Type-Options": "nosniff"}
        return "https://example.com/", 200, headers, html.encode(), "utf-8"

    fake_robots = {
        "url": "https://example.com/robots.txt", "status": 200, "error": None, "rule_count": 0,
        "ai_crawlers": {}, "blocked_ai_crawlers": [], "allowed_ai_crawlers": [],
        "sitemaps": ["https://example.com/sitemap.xml"],
    }

    monkeypatch.setattr(audit_module, "_request", fake_request)
    monkeypatch.setattr(audit_module.crawler, "fetch_robots", lambda url, timeout=10: fake_robots)

    result = audit("https://example.com")
    inventory = result["inventory"]
    assert inventory["robots"] == fake_robots
    assert inventory["landmarks"] == ["footer", "header", "main", "nav"]
    assert inventory["hsts"] is True
    assert inventory["csp"] is False
    assert inventory["h1"] == 1
