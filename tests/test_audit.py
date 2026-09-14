import ope.audit as audit_module
from ope.audit import PageParser, _finding, _json_ld_entities, _link_locality, audit


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


def test_parser_extracts_json_ld_content_images_and_forms():
    p = PageParser()
    p.feed(
        '<html><body>'
        '<script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>'
        '<img src="a.jpg" alt="A" width="100" height="100" srcset="a-2x.jpg 2x">'
        '<img src="b.jpg" alt="B">'
        '<form><input type="email" name="email"></form>'
        '<script src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script>'
        "</body></html>"
    )
    assert p.json_ld_raw == ['{"@type": "Organization", "name": "Acme"}']
    assert p.images_missing_dimensions == 1
    assert p.images_missing_srcset == 1
    assert p.contact_input is True
    assert p.script_srcs == ["https://www.googletagmanager.com/gtag/js?id=G-XXXX"]


def test_json_ld_entities_extracts_types_and_skips_malformed_blocks():
    result = _json_ld_entities(['{"@type": "Organization"}', "not json", '{"@type": ["LocalBusiness"], "address": "1 Main St", "telephone": "555-0100"}'])
    assert result["types"] == ["localbusiness", "organization"]
    assert result["has_entity_type"] is True
    assert result["has_nap"] is True


def test_json_ld_entities_without_nap_fields_is_false():
    result = _json_ld_entities(['{"@type": "LocalBusiness"}'])
    assert result["has_nap"] is False


def test_link_locality_splits_internal_and_external():
    result = _link_locality(["/about", "https://example.com/contact", "https://other.com/page", "mailto:a@example.com"], "https://example.com/")
    assert result["internal_links"] == 2
    assert result["external_links"] == 1


def test_audit_wires_robots_and_new_inventory_signals(monkeypatch):
    def fake_request(url, timeout=15):
        html = (
            '<html lang="en"><head><title>Test</title>'
            '<meta name="viewport" content="width=device-width">'
            '<meta name="description" content="A description long enough to plausibly pass the snippet length check here.">'
            '<link rel="canonical" href="https://example.com/"></head>'
            '<body><header></header><nav></nav><main><h1>Hi</h1>'
            '<script type="application/ld+json">{"@type": "Organization"}</script>'
            '<a href="/about">About</a>'
            "</main><footer></footer></body></html>"
        )
        headers = {"Strict-Transport-Security": "max-age=1", "X-Content-Type-Options": "nosniff"}
        return "https://example.com/", 200, headers, html.encode(), "utf-8", 12.3, 250.0

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
    assert inventory["dns_ms"] == 12.3
    assert inventory["ttfb_ms"] == 250.0
    assert inventory["citability"]["total_blocks_analyzed"] == 0
    assert inventory["pagespeed"] is None
    assert inventory["has_entity_type"] is True
    assert inventory["entity_types"] == ["organization"]
    assert inventory["internal_links"] == 1
    assert inventory["has_analytics"] is False
    assert inventory["contact_input"] is False
