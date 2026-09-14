import ope.audit as audit_module
from ope.audit import PageParser, _finding, _json_ld_summary, _link_locality, audit


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


def test_json_ld_summary_extracts_types_and_skips_malformed_blocks():
    result = _json_ld_summary(['{"@type": "Organization"}', "not json", '{"@type": ["LocalBusiness"], "address": "1 Main St", "telephone": "555-0100"}'])
    assert result["types"] == ["localbusiness", "organization"]
    assert result["has_entity_type"] is True
    assert result["has_nap"] is True
    assert result["is_local_business"] is True


def test_json_ld_summary_without_nap_fields_is_false():
    result = _json_ld_summary(['{"@type": "LocalBusiness"}'])
    assert result["has_nap"] is False
    assert result["has_address"] is False


def test_json_ld_summary_recognises_local_subtypes_and_details():
    result = _json_ld_summary([
        '{"@type": "Restaurant", "address": {"@type": "PostalAddress", "streetAddress": "1 Main St"},'
        ' "telephone": "555-0100", "geo": {"latitude": 1.0, "longitude": 2.0},'
        ' "openingHours": "Mo-Fr 09:00-17:00", "areaServed": "Mumbai",'
        ' "sameAs": ["https://g.page/acme", "https://linkedin.com/company/acme", "https://instagram.com/acme"],'
        ' "aggregateRating": {"@type": "AggregateRating", "ratingValue": 4.5}}'
    ])
    assert result["is_local_business"] is True
    assert result["has_geo"] is True
    assert result["has_opening_hours"] is True
    assert result["has_service_area"] is True
    assert result["has_google_profile"] is True
    assert result["has_social_profiles"] is True
    assert result["has_review"] is True
    assert result["local_visibility_ready"] is True


def test_json_ld_summary_walks_nested_graph_documents():
    result = _json_ld_summary(['{"@graph": [{"@type": "BreadcrumbList"}, {"@type": "Organization", "author": {"@type": "Person", "name": "A"}}]}'])
    assert result["has_breadcrumb"] is True
    assert result["has_author"] is True
    assert result["has_entity_type"] is True


def test_json_ld_summary_consistency_is_none_without_comparable_values():
    result = _json_ld_summary(['{"@type": "Organization"}'], title="Acme", description="Desc")
    assert result["name_matches_title"] is None
    assert result["description_matches"] is None
    matched = _json_ld_summary(['{"@type": "Organization", "name": "Acme", "description": "Desc"}'], title="Acme — Home", description="Desc")
    assert matched["name_matches_title"] is True
    assert matched["description_matches"] is True


def test_parser_resolves_input_labels_declared_after_the_input():
    p = PageParser()
    p.feed(
        "<form>"
        '<input type="text" id="named">'
        '<label for="named">Named</label>'
        '<label>Wrapped <input type="text"></label>'
        '<input type="text" aria-label="Aria">'
        '<input type="text" id="orphan">'
        '<input type="hidden" name="csrf">'
        "</form>"
    )
    p.close()
    assert p.inputs == 4
    assert p.unlabelled_inputs == 1


def test_parser_extracts_structure_media_and_interaction_signals():
    p = PageParser()
    p.feed(
        "<!DOCTYPE html><html><head><title>T</title><meta charset=\"utf-8\"></head>"
        "<body><h1>Main</h1><h2>How does it work?</h2><h2>Pricing</h2>"
        '<video src="v.mp4"></video><video src="w.mp4" poster="p.jpg" width="4" height="3"><track kind="captions" src="c.vtt"></video>'
        '<a href="/privacy">Privacy policy</a><a href="/x">Book a demo</a>'
        '<button aria-label="Close"></button><button></button>'
        '<div tabindex="3">trap</div>'
        "</body></html>"
    )
    p.close()
    assert p.doctype.lower() == "doctype html"
    assert p.charset == "utf-8"
    assert p.title_count == 1
    assert p.structure == {"html", "head", "body"}
    assert p.heading_texts == ["Main", "How does it work?", "Pricing"]
    assert p.videos == 2 and p.videos_missing_metadata == 1
    assert p.media_elements == 2 and p.caption_tracks == 1
    assert p.link_texts == ["Privacy policy", "Book a demo"]
    assert p.buttons == 2 and p.buttons_without_text == 1
    assert p.positive_tabindex == 1


def test_cookie_profile_flags_missing_attributes_without_recording_values():
    profile = audit_module._cookie_profile([
        "session=secret-value; Path=/; Secure; HttpOnly; SameSite=Lax",
        "tracker=another-secret; Path=/",
    ])
    assert profile["cookie_count"] == 2
    assert profile["insecure_cookies"] == ["tracker: missing secure, httponly, samesite"]
    assert "secret-value" not in str(profile)
    assert "another-secret" not in str(profile)


def test_csp_profile_detects_unsafe_directives():
    assert audit_module._csp_profile(None) == {"present": False, "unsafe_directives": []}
    profile = audit_module._csp_profile("default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval'")
    assert profile["present"] is True
    assert profile["unsafe_directives"] == ["unsafe-inline", "unsafe-eval"]


def test_secret_scan_reports_labels_only_never_the_secret():
    html = '<script>const key = "AKIAIOSFODNN7EXAMPLE"; const g = "AIza' + "a" * 35 + '";</script>'
    labels = audit_module._scan_secrets(html)
    assert labels == ["aws_access_key", "google_api_key"]
    assert "AKIAIOSFODNN7EXAMPLE" not in str(labels)
    assert audit_module._scan_secrets("<p>nothing sensitive here</p>") == []


def test_css_behaviour_reads_motion_and_focus_handling():
    assert audit_module._css_behaviour("") == {"has_css": False, "has_motion": False, "respects_reduced_motion": False, "suppresses_focus_outline": False, "has_focus_visible": False}
    behaviour = audit_module._css_behaviour("a{transition:all .2s}@media (prefers-reduced-motion: reduce){a{transition:none}} button{outline: 0} button:focus-visible{outline:2px solid}")
    assert behaviour == {"has_css": True, "has_motion": True, "respects_reduced_motion": True, "suppresses_focus_outline": True, "has_focus_visible": True}


def test_subresource_fetch_classifies_third_party_hosts_and_survives_failures(monkeypatch):
    monkeypatch.setattr(audit_module, "validate_url_strict", lambda url: url)

    class _FakeResponse:
        def __init__(self, payload): self._payload = payload
        def read(self, _limit=None): return self._payload
        def __enter__(self): return self
        def __exit__(self, *_): return False

    def fake_urlopen(request, timeout=10):
        url = request.full_url
        if "broken" in url:
            raise OSError("unreachable")
        return _FakeResponse(b"x" * 100 if url.endswith(".css") else b"y" * 250)

    monkeypatch.setattr(audit_module.urllib.request, "urlopen", fake_urlopen)
    result = audit_module._fetch_subresources(
        "https://example.com/",
        ["/site.css", "https://cdn.other.net/lib.css"],
        ["/app.js", "https://cdn.other.net/broken.js"],
    )
    assert result["discovered_requests"] == 4
    assert result["fetched_requests"] == 3
    assert result["css_bytes"] == 200
    assert result["js_bytes"] == 250
    assert result["third_party_hosts"] == ["cdn.other.net"]


def test_tls_profile_reports_error_instead_of_raising_for_plain_http():
    profile = audit_module._tls_profile("http://example.com/")
    assert profile["protocol"] is None
    assert profile["error"]


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
        return audit_module.Response(
            final_url="https://example.com/",
            status=200,
            headers={"strict-transport-security": "max-age=1", "x-content-type-options": "nosniff", "cf-ray": "abc123"},
            set_cookies=["session=1; Path=/"],
            body=html.encode(),
            charset="utf-8",
            dns_ms=12.3,
            ttfb_ms=250.0,
        )

    fake_robots = {
        "url": "https://example.com/robots.txt", "status": 200, "error": None, "rule_count": 0,
        "ai_crawlers": {}, "blocked_ai_crawlers": [], "allowed_ai_crawlers": [],
        "sitemaps": ["https://example.com/sitemap.xml"],
    }

    monkeypatch.setattr(audit_module, "_request", fake_request)
    monkeypatch.setattr(audit_module.crawler, "fetch_robots", lambda url, timeout=10: fake_robots)
    monkeypatch.setattr(audit_module, "_tls_profile", lambda url, timeout=10: {"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384", "days_until_expiry": 60, "error": None})

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
    assert inventory["tls"]["protocol"] == "TLSv1.3"
    assert inventory["cookies"]["insecure_cookies"] == ["session: missing secure, httponly, samesite"]
    assert inventory["cdn_markers"] == ["cf-ray"]
    assert inventory["exposed_secrets"] == []
