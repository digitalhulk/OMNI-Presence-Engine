from ope.audit_pipeline import execute_audit_checks


BOUND = {
    "02-infrastructure.hosting.availability",
    "03-code.head_metadata",
    "05-index.canonicalization",
    "03-code.structured_data",
    "13-ux.mobile_usability",
    "14-accessibility.alt_text",
    "17-language.language_declaration",
    "04-crawl.robots_access",
    "04-crawl.bot_access",
    "10-ai-search.agent_accessibility",
    "04-crawl.sitemap_discovery",
    "02-infrastructure.tls.valid",
    "16-security.https",
    "16-security.security_headers",
    "05-index.indexability",
    "13-ux.hierarchy",
    "13-ux.navigation",
    "03-code.semantic_html",
    "17-language.hreflang",
    "09-search.snippets",
    "02-infrastructure.dns.resolution",
    "15-performance.dns",
    "15-performance.ttfb",
    "15-performance.page_weight",
    "15-performance.lcp",
    "15-performance.fcp",
    "15-performance.cls",
    "15-performance.tbt",
    "15-performance.inp",
    "10-ai-search.answer_eligibility",
    "10-ai-search.citation_presence",
    "01-entity.identity",
    "06-semantics.entity_markup",
    "12-local.nap_consistency",
    "08-media.image_metadata",
    "08-media.responsive_media",
    "07-content.internal_links",
    "07-content.freshness",
    "18-analytics.measurement_coverage",
    "19-conversion.lead_capture",
}

PAGESPEED_SOURCED = {
    "15-performance.lcp",
    "15-performance.fcp",
    "15-performance.cls",
    "15-performance.tbt",
    "15-performance.inp",
}


def _audit_result():
    return {
        "target": "https://example.com",
        "final_url": "https://example.com",
        "inventory": {
            "status": 200,
            "title": "Example",
            "canonical": "https://example.com/",
            "json_ld_blocks": 1,
            "viewport": "width=device-width",
            "images_missing_alt": 0,
            "lang": "en",
            "h1": 1,
            "description": "OPE is an evidence-driven digital presence audit and root-cause engine for websites.",
            "meta_robots": "",
            "x_robots_tag": None,
            "hreflang_count": 1,
            "landmarks": ["header", "nav", "main", "footer"],
            "hsts": True,
            "csp": True,
            "x_content_type_options": True,
            "referrer_policy_header": True,
            "robots": {
                "url": "https://example.com/robots.txt",
                "status": 200,
                "error": None,
                "rule_count": 1,
                "ai_crawlers": {"GPTBot": "ALLOW", "OAI-SearchBot": "ALLOW"},
                "blocked_ai_crawlers": [],
                "allowed_ai_crawlers": ["GPTBot", "OAI-SearchBot"],
                "sitemaps": ["https://example.com/sitemap.xml"],
            },
            "dns_ms": 42.0,
            "ttfb_ms": 300.0,
            "bytes": 5000,
            "pagespeed": {"lcp_ms": 2000.0, "fcp_ms": 1200.0, "cls": 0.05, "tbt_ms": 100.0, "inp_ms": 150.0},
            "citability": {
                "total_blocks_analyzed": 3,
                "average_citability_score": 70.0,
                "grade_distribution": {"A": 1, "B": 1, "C": 1, "D": 0, "F": 0},
            },
            "entity_types": ["organization"],
            "has_entity_type": True,
            "has_nap": True,
            "images": 2,
            "images_missing_dimensions": 0,
            "images_missing_srcset": 0,
            "internal_links": 3,
            "external_links": 1,
            "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            "article_modified": "",
            "has_analytics": True,
            "forms": 1,
            "contact_input": True,
        },
        "findings": [],
    }


def test_bound_audit_checks_produce_schema_complete_evidence():
    result = execute_audit_checks(_audit_result())
    for check_id in BOUND:
        check = result["checks"][check_id]
        assert check["status"] == "PASS"
        assert check["evidence"]
        expected_source = "pagespeed-insights" if check_id in PAGESPEED_SOURCED else "ope-audit"
        for evidence in check["evidence"]:
            assert evidence["source"] == expected_source
            assert evidence["observed_at"]


def test_unbound_checks_remain_unknown():
    result = execute_audit_checks(_audit_result())
    assert result["checks"]["01-entity.ownership"]["status"] == "UNKNOWN"


def test_missing_http_status_is_unknown():
    audit = _audit_result()
    del audit["inventory"]["status"]
    result = execute_audit_checks(audit)
    assert result["checks"]["02-infrastructure.hosting.availability"]["status"] == "UNKNOWN"


def test_missing_observation_is_unknown_not_fail():
    audit = _audit_result()
    del audit["inventory"]["title"]
    result = execute_audit_checks(audit)
    assert result["checks"]["03-code.head_metadata"]["status"] == "UNKNOWN"


def test_failed_audit_observation_produces_fail():
    audit = _audit_result()
    audit["inventory"]["title"] = ""
    audit["findings"] = [{"id": "CODE-HTTP-001"}]
    result = execute_audit_checks(audit)
    assert result["checks"]["03-code.head_metadata"]["status"] == "FAIL"


def test_blocked_ai_crawler_produces_fail_for_ai_access_checks():
    audit = _audit_result()
    audit["inventory"]["robots"]["ai_crawlers"]["GPTBot"] = "BLOCK"
    audit["inventory"]["robots"]["blocked_ai_crawlers"] = ["GPTBot"]
    result = execute_audit_checks(audit)
    assert result["checks"]["04-crawl.bot_access"]["status"] == "FAIL"
    assert result["checks"]["10-ai-search.agent_accessibility"]["status"] == "FAIL"


def test_missing_robots_observation_is_unknown():
    audit = _audit_result()
    del audit["inventory"]["robots"]
    result = execute_audit_checks(audit)
    assert result["checks"]["04-crawl.robots_access"]["status"] == "UNKNOWN"
    assert result["checks"]["10-ai-search.agent_accessibility"]["status"] == "UNKNOWN"


def test_no_sitemap_is_fail():
    audit = _audit_result()
    audit["inventory"]["robots"]["sitemaps"] = []
    result = execute_audit_checks(audit)
    assert result["checks"]["04-crawl.sitemap_discovery"]["status"] == "FAIL"


def test_http_target_fails_tls_and_https_checks():
    audit = _audit_result()
    audit["target"] = "http://example.com"
    audit["final_url"] = "http://example.com"
    result = execute_audit_checks(audit)
    assert result["checks"]["02-infrastructure.tls.valid"]["status"] == "FAIL"
    assert result["checks"]["16-security.https"]["status"] == "FAIL"


def test_missing_security_header_is_fail():
    audit = _audit_result()
    audit["inventory"]["hsts"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["16-security.security_headers"]["status"] == "FAIL"


def test_noindex_directive_is_fail():
    audit = _audit_result()
    audit["inventory"]["meta_robots"] = "noindex, nofollow"
    result = execute_audit_checks(audit)
    assert result["checks"]["05-index.indexability"]["status"] == "FAIL"


def test_missing_indexability_observation_is_unknown():
    audit = _audit_result()
    del audit["inventory"]["meta_robots"]
    del audit["inventory"]["x_robots_tag"]
    result = execute_audit_checks(audit)
    assert result["checks"]["05-index.indexability"]["status"] == "UNKNOWN"


def test_multiple_h1_fails_hierarchy_check():
    audit = _audit_result()
    audit["inventory"]["h1"] = 2
    result = execute_audit_checks(audit)
    assert result["checks"]["13-ux.hierarchy"]["status"] == "FAIL"


def test_missing_landmarks_fail_navigation_and_semantic_html():
    audit = _audit_result()
    audit["inventory"]["landmarks"] = ["header"]
    result = execute_audit_checks(audit)
    assert result["checks"]["13-ux.navigation"]["status"] == "FAIL"
    assert result["checks"]["03-code.semantic_html"]["status"] == "FAIL"


def test_no_hreflang_is_fail():
    audit = _audit_result()
    audit["inventory"]["hreflang_count"] = 0
    result = execute_audit_checks(audit)
    assert result["checks"]["17-language.hreflang"]["status"] == "FAIL"


def test_short_description_fails_snippet_check():
    audit = _audit_result()
    audit["inventory"]["description"] = "Too short."
    result = execute_audit_checks(audit)
    assert result["checks"]["09-search.snippets"]["status"] == "FAIL"


def test_slow_dns_and_ttfb_fail_performance_budgets():
    audit = _audit_result()
    audit["inventory"]["dns_ms"] = 500.0
    audit["inventory"]["ttfb_ms"] = 2000.0
    result = execute_audit_checks(audit)
    assert result["checks"]["15-performance.dns"]["status"] == "FAIL"
    assert result["checks"]["15-performance.ttfb"]["status"] == "FAIL"
    assert result["checks"]["02-infrastructure.dns.resolution"]["status"] == "PASS"


def test_heavy_document_fails_page_weight_budget():
    audit = _audit_result()
    audit["inventory"]["bytes"] = 500_000
    result = execute_audit_checks(audit)
    assert result["checks"]["15-performance.page_weight"]["status"] == "FAIL"


def test_missing_pagespeed_evidence_is_unknown():
    audit = _audit_result()
    audit["inventory"]["pagespeed"] = None
    result = execute_audit_checks(audit)
    for check_id in ("15-performance.lcp", "15-performance.fcp", "15-performance.cls", "15-performance.tbt", "15-performance.inp"):
        assert result["checks"][check_id]["status"] == "UNKNOWN"


def test_poor_web_vitals_fail_their_checks():
    audit = _audit_result()
    audit["inventory"]["pagespeed"] = {"lcp_ms": 5000.0, "fcp_ms": 3000.0, "cls": 0.4, "tbt_ms": 600.0, "inp_ms": 600.0}
    result = execute_audit_checks(audit)
    for check_id in ("15-performance.lcp", "15-performance.fcp", "15-performance.cls", "15-performance.tbt", "15-performance.inp"):
        assert result["checks"][check_id]["status"] == "FAIL"


def test_missing_citability_observation_is_unknown():
    audit = _audit_result()
    audit["inventory"]["citability"] = {"total_blocks_analyzed": 0, "average_citability_score": 0.0, "grade_distribution": {}}
    result = execute_audit_checks(audit)
    assert result["checks"]["10-ai-search.answer_eligibility"]["status"] == "UNKNOWN"
    assert result["checks"]["10-ai-search.citation_presence"]["status"] == "UNKNOWN"


def test_weak_citability_fails_ai_search_checks():
    audit = _audit_result()
    audit["inventory"]["citability"] = {
        "total_blocks_analyzed": 4,
        "average_citability_score": 20.0,
        "grade_distribution": {"A": 0, "B": 0, "C": 1, "D": 1, "F": 2},
    }
    result = execute_audit_checks(audit)
    assert result["checks"]["10-ai-search.answer_eligibility"]["status"] == "FAIL"
    assert result["checks"]["10-ai-search.citation_presence"]["status"] == "FAIL"


def test_no_entity_type_fails_identity_and_entity_markup_checks():
    audit = _audit_result()
    audit["inventory"]["has_entity_type"] = False
    audit["inventory"]["entity_types"] = []
    result = execute_audit_checks(audit)
    assert result["checks"]["01-entity.identity"]["status"] == "FAIL"
    assert result["checks"]["06-semantics.entity_markup"]["status"] == "FAIL"


def test_missing_entity_observation_is_unknown():
    audit = _audit_result()
    del audit["inventory"]["has_entity_type"]
    result = execute_audit_checks(audit)
    assert result["checks"]["01-entity.identity"]["status"] == "UNKNOWN"


def test_no_nap_fails_local_consistency_check():
    audit = _audit_result()
    audit["inventory"]["has_nap"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["12-local.nap_consistency"]["status"] == "FAIL"


def test_missing_image_dimensions_and_srcset_fail_media_checks():
    audit = _audit_result()
    audit["inventory"]["images_missing_dimensions"] = 1
    audit["inventory"]["images_missing_srcset"] = 2
    result = execute_audit_checks(audit)
    assert result["checks"]["08-media.image_metadata"]["status"] == "FAIL"
    assert result["checks"]["08-media.responsive_media"]["status"] == "FAIL"


def test_no_images_makes_media_checks_unknown():
    audit = _audit_result()
    audit["inventory"]["images"] = 0
    result = execute_audit_checks(audit)
    assert result["checks"]["08-media.image_metadata"]["status"] == "UNKNOWN"
    assert result["checks"]["08-media.responsive_media"]["status"] == "UNKNOWN"


def test_no_internal_links_fails_content_check():
    audit = _audit_result()
    audit["inventory"]["internal_links"] = 0
    result = execute_audit_checks(audit)
    assert result["checks"]["07-content.internal_links"]["status"] == "FAIL"


def test_no_freshness_signal_fails_freshness_check():
    audit = _audit_result()
    audit["inventory"]["last_modified"] = None
    audit["inventory"]["article_modified"] = ""
    result = execute_audit_checks(audit)
    assert result["checks"]["07-content.freshness"]["status"] == "FAIL"


def test_no_analytics_fails_measurement_coverage_check():
    audit = _audit_result()
    audit["inventory"]["has_analytics"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["18-analytics.measurement_coverage"]["status"] == "FAIL"


def test_no_contact_input_fails_lead_capture_check():
    audit = _audit_result()
    audit["inventory"]["contact_input"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["19-conversion.lead_capture"]["status"] == "FAIL"


def test_no_forms_makes_lead_capture_check_unknown():
    audit = _audit_result()
    audit["inventory"]["forms"] = 0
    result = execute_audit_checks(audit)
    assert result["checks"]["19-conversion.lead_capture"]["status"] == "UNKNOWN"
