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
    "06-semantics.taxonomy",
    "06-semantics.knowledge_consistency",
    "11-authority.reviews",
    "11-authority.expert_signals",
    "11-authority.consistency",
    "01-entity.identifiers",
    "01-entity.relationships",
    "01-entity.consistency",
    "12-local.local_pages",
    "12-local.hours",
    "12-local.maps_presence",
    "12-local.gbp_presence",
    "12-local.service_area",
    "12-local.reviews",
    "09-search.local_visibility",
    "16-security.tls",
    "16-security.csp",
    "16-security.cookies",
    "16-security.secrets",
    "16-security.waf",
    "02-infrastructure.cdn.configuration",
    "02-infrastructure.server_reachability",
    "14-accessibility.forms",
    "14-accessibility.semantics",
    "14-accessibility.captions",
    "14-accessibility.keyboard",
    "08-media.captions_transcripts",
    "08-media.video_metadata",
    "05-index.status_codes",
    "05-index.duplication",
    "17-language.locale",
    "17-language.unicode",
    "03-code.html.validity",
    "03-code.forms",
    "13-ux.trust_visibility",
    "13-ux.interaction_clarity",
    "19-conversion.cta_clarity",
    "07-content.completeness",
    "06-semantics.topic_coverage",
    "06-semantics.query_intent",
    "03-code.css_cost",
    "03-code.js_cost",
    "03-code.third_party_code",
    "15-performance.network",
    "14-accessibility.reduced_motion",
    "14-accessibility.focus",
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
            "entity_types": ["organization", "restaurant"],
            "has_entity_type": True,
            "has_nap": True,
            "is_local_business": True,
            "has_address": True,
            "has_geo": True,
            "has_opening_hours": True,
            "has_service_area": True,
            "has_google_profile": True,
            "local_visibility_ready": True,
            "has_review": True,
            "has_author": True,
            "has_identifiers": True,
            "has_relationships": True,
            "has_social_profiles": True,
            "has_breadcrumb": True,
            "name_matches_title": True,
            "description_matches": True,
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
            "tls": {"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384", "days_until_expiry": 60, "error": None},
            "cookies": {"cookie_count": 1, "insecure_cookies": []},
            "csp_profile": {"present": True, "unsafe_directives": []},
            "exposed_secrets": [],
            "cdn_markers": ["cf-ray"],
            "waf_markers": ["cf-ray"],
            "doctype": "doctype html",
            "declared_charset": "utf-8",
            "title_count": 1,
            "structure": ["body", "head", "html"],
            "word_count": 850,
            "inputs": 2,
            "unlabelled_inputs": 0,
            "buttons": 2,
            "buttons_without_text": 0,
            "videos": 1,
            "videos_missing_metadata": 0,
            "media_elements": 1,
            "caption_tracks": 1,
            "positive_tabindex": 0,
            "forms_missing_action": 0,
            "has_trust_links": True,
            "has_cta": True,
            "question_headings": 2,
            "subheadings": 4,
            "canonical_is_self": True,
            "page_weight_bytes": 220_000,
            "discovered_requests": 6,
            "fetched_requests": 6,
            "css_bytes": 40_000,
            "js_bytes": 175_000,
            "third_party_hosts": ["cdn.example.net"],
            "has_css": True,
            "has_motion": True,
            "respects_reduced_motion": True,
            "suppresses_focus_outline": False,
            "has_focus_visible": True,
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


def test_heavy_document_fails_page_weight_budget_without_subresource_data():
    audit = _audit_result()
    audit["inventory"]["page_weight_bytes"] = None
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


def test_absent_structured_data_signals_fail_presence_checks():
    audit = _audit_result()
    audit["inventory"].update({"has_breadcrumb": False, "has_review": False, "has_author": False, "has_social_profiles": False})
    result = execute_audit_checks(audit)
    for check_id in ("06-semantics.taxonomy", "11-authority.reviews", "11-authority.expert_signals", "11-authority.consistency"):
        assert result["checks"][check_id]["status"] == "FAIL"


def test_non_local_site_makes_local_detail_checks_not_applicable():
    audit = _audit_result()
    audit["inventory"]["is_local_business"] = False
    result = execute_audit_checks(audit)
    for check_id in ("12-local.hours", "12-local.maps_presence", "12-local.gbp_presence", "12-local.service_area", "12-local.local_pages", "12-local.reviews", "09-search.local_visibility"):
        assert result["checks"][check_id]["status"] == "N/A"


def test_local_site_missing_details_fails_local_detail_checks():
    audit = _audit_result()
    audit["inventory"].update({"has_opening_hours": False, "has_geo": False, "has_google_profile": False, "local_visibility_ready": False})
    result = execute_audit_checks(audit)
    for check_id in ("12-local.hours", "12-local.maps_presence", "12-local.gbp_presence", "09-search.local_visibility"):
        assert result["checks"][check_id]["status"] == "FAIL"


def test_no_entity_markup_makes_entity_detail_checks_not_applicable():
    audit = _audit_result()
    audit["inventory"]["has_entity_type"] = False
    result = execute_audit_checks(audit)
    for check_id in ("01-entity.identifiers", "01-entity.relationships", "01-entity.consistency", "06-semantics.knowledge_consistency"):
        assert result["checks"][check_id]["status"] == "N/A"


def test_unpublished_comparison_values_are_not_applicable():
    audit = _audit_result()
    audit["inventory"]["name_matches_title"] = None
    audit["inventory"]["description_matches"] = None
    result = execute_audit_checks(audit)
    assert result["checks"]["01-entity.consistency"]["status"] == "N/A"
    assert result["checks"]["06-semantics.knowledge_consistency"]["status"] == "N/A"


def test_mismatched_entity_name_fails_consistency_check():
    audit = _audit_result()
    audit["inventory"]["name_matches_title"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["01-entity.consistency"]["status"] == "FAIL"


def test_oversized_subresources_and_request_counts_fail():
    audit = _audit_result()
    audit["inventory"].update({"css_bytes": 900_000, "js_bytes": 2_000_000, "third_party_hosts": [f"h{i}.example.net" for i in range(9)], "discovered_requests": 120, "page_weight_bytes": 4_000_000})
    result = execute_audit_checks(audit)
    for check_id in ("03-code.css_cost", "03-code.js_cost", "03-code.third_party_code", "15-performance.network", "15-performance.page_weight"):
        assert result["checks"][check_id]["status"] == "FAIL"


def test_page_weight_falls_back_to_html_only_without_subresource_data():
    audit = _audit_result()
    audit["inventory"]["page_weight_bytes"] = None
    result = execute_audit_checks(audit)
    check = result["checks"]["15-performance.page_weight"]
    assert check["status"] == "PASS"
    assert "HTML document only" in check["reason"]


def test_motion_and_focus_checks_read_fetched_css():
    audit = _audit_result()
    audit["inventory"]["respects_reduced_motion"] = False
    audit["inventory"]["suppresses_focus_outline"] = True
    audit["inventory"]["has_focus_visible"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["14-accessibility.reduced_motion"]["status"] == "FAIL"
    assert result["checks"]["14-accessibility.focus"]["status"] == "FAIL"

    audit["inventory"]["has_motion"] = False
    assert execute_audit_checks(audit)["checks"]["14-accessibility.reduced_motion"]["status"] == "N/A"

    audit["inventory"]["has_css"] = False
    result = execute_audit_checks(audit)
    assert result["checks"]["14-accessibility.reduced_motion"]["status"] == "UNKNOWN"
    assert result["checks"]["14-accessibility.focus"]["status"] == "UNKNOWN"


def test_defect_counts_fail_and_empty_populations_are_not_applicable():
    audit = _audit_result()
    audit["inventory"].update({"unlabelled_inputs": 1, "positive_tabindex": 2, "videos_missing_metadata": 1, "buttons_without_text": 1, "forms_missing_action": 1})
    result = execute_audit_checks(audit)
    for check_id in ("14-accessibility.forms", "14-accessibility.keyboard", "08-media.video_metadata", "13-ux.interaction_clarity", "03-code.forms"):
        assert result["checks"][check_id]["status"] == "FAIL"

    empty = _audit_result()
    empty["inventory"].update({"inputs": 0, "videos": 0, "buttons": 0, "forms": 0})
    result = execute_audit_checks(empty)
    for check_id in ("14-accessibility.forms", "08-media.video_metadata", "13-ux.interaction_clarity", "03-code.forms"):
        assert result["checks"][check_id]["status"] == "N/A"


def test_uncaptioned_media_fails_and_no_media_is_not_applicable():
    audit = _audit_result()
    audit["inventory"]["caption_tracks"] = 0
    result = execute_audit_checks(audit)
    assert result["checks"]["14-accessibility.captions"]["status"] == "FAIL"
    assert result["checks"]["08-media.captions_transcripts"]["status"] == "FAIL"

    audit["inventory"]["media_elements"] = 0
    result = execute_audit_checks(audit)
    assert result["checks"]["14-accessibility.captions"]["status"] == "N/A"


def test_non_200_status_fails_status_codes_check():
    audit = _audit_result()
    audit["inventory"]["status"] = 301
    assert execute_audit_checks(audit)["checks"]["05-index.status_codes"]["status"] == "FAIL"


def test_cross_canonical_fails_duplication_and_absent_canonical_is_not_applicable():
    audit = _audit_result()
    audit["inventory"]["canonical_is_self"] = False
    assert execute_audit_checks(audit)["checks"]["05-index.duplication"]["status"] == "FAIL"
    audit["inventory"]["canonical_is_self"] = None
    assert execute_audit_checks(audit)["checks"]["05-index.duplication"]["status"] == "N/A"


def test_locale_and_charset_validation():
    audit = _audit_result()
    audit["inventory"]["lang"] = "english!"
    audit["inventory"]["declared_charset"] = "iso-8859-1"
    result = execute_audit_checks(audit)
    assert result["checks"]["17-language.locale"]["status"] == "FAIL"
    assert result["checks"]["17-language.unicode"]["status"] == "FAIL"

    audit["inventory"]["lang"] = "en-IN"
    audit["inventory"]["declared_charset"] = "UTF-8"
    result = execute_audit_checks(audit)
    assert result["checks"]["17-language.locale"]["status"] == "PASS"
    assert result["checks"]["17-language.unicode"]["status"] == "PASS"


def test_structural_defects_fail_html_validity_check():
    audit = _audit_result()
    audit["inventory"]["doctype"] = ""
    audit["inventory"]["title_count"] = 2
    result = execute_audit_checks(audit)
    check = result["checks"]["03-code.html.validity"]
    assert check["status"] == "FAIL"
    assert len(check["evidence"][0]["value"]["defects"]) == 2


def test_thin_content_and_flat_headings_fail_their_checks():
    audit = _audit_result()
    audit["inventory"].update({"word_count": 40, "subheadings": 0, "question_headings": 0, "has_trust_links": False, "has_cta": False})
    result = execute_audit_checks(audit)
    for check_id in ("07-content.completeness", "06-semantics.topic_coverage", "06-semantics.query_intent", "13-ux.trust_visibility", "19-conversion.cta_clarity"):
        assert result["checks"][check_id]["status"] == "FAIL"


def test_outdated_tls_or_expiring_certificate_fails_tls_check():
    audit = _audit_result()
    audit["inventory"]["tls"] = {"protocol": "TLSv1", "cipher": "X", "days_until_expiry": 60, "error": None}
    assert execute_audit_checks(audit)["checks"]["16-security.tls"]["status"] == "FAIL"
    audit["inventory"]["tls"] = {"protocol": "TLSv1.3", "cipher": "X", "days_until_expiry": 3, "error": None}
    assert execute_audit_checks(audit)["checks"]["16-security.tls"]["status"] == "FAIL"


def test_unreachable_tls_handshake_is_unknown_not_fail():
    audit = _audit_result()
    audit["inventory"]["tls"] = {"protocol": None, "days_until_expiry": None, "error": "TimeoutError: timed out"}
    assert execute_audit_checks(audit)["checks"]["16-security.tls"]["status"] == "UNKNOWN"


def test_unsafe_or_absent_csp_fails_csp_check():
    audit = _audit_result()
    audit["inventory"]["csp_profile"] = {"present": True, "unsafe_directives": ["unsafe-inline"]}
    assert execute_audit_checks(audit)["checks"]["16-security.csp"]["status"] == "FAIL"
    audit["inventory"]["csp_profile"] = {"present": False, "unsafe_directives": []}
    assert execute_audit_checks(audit)["checks"]["16-security.csp"]["status"] == "FAIL"


def test_insecure_cookie_fails_and_no_cookies_is_not_applicable():
    audit = _audit_result()
    audit["inventory"]["cookies"] = {"cookie_count": 2, "insecure_cookies": ["a: missing secure"]}
    assert execute_audit_checks(audit)["checks"]["16-security.cookies"]["status"] == "FAIL"
    audit["inventory"]["cookies"] = {"cookie_count": 0, "insecure_cookies": []}
    assert execute_audit_checks(audit)["checks"]["16-security.cookies"]["status"] == "N/A"


def test_exposed_secret_fails_secrets_check():
    audit = _audit_result()
    audit["inventory"]["exposed_secrets"] = ["aws_access_key"]
    assert execute_audit_checks(audit)["checks"]["16-security.secrets"]["status"] == "FAIL"


def test_undetected_edge_platform_is_unknown_not_fail():
    audit = _audit_result()
    audit["inventory"]["cdn_markers"] = []
    audit["inventory"]["waf_markers"] = []
    result = execute_audit_checks(audit)
    assert result["checks"]["02-infrastructure.cdn.configuration"]["status"] == "UNKNOWN"
    assert result["checks"]["16-security.waf"]["status"] == "UNKNOWN"


def test_server_reachability_passes_even_on_error_status():
    audit = _audit_result()
    audit["inventory"]["status"] = 503
    result = execute_audit_checks(audit)
    assert result["checks"]["02-infrastructure.server_reachability"]["status"] == "PASS"
    assert result["checks"]["02-infrastructure.hosting.availability"]["status"] == "FAIL"


def test_missing_structured_data_observation_is_unknown():
    audit = _audit_result()
    del audit["inventory"]["has_breadcrumb"]
    del audit["inventory"]["is_local_business"]
    result = execute_audit_checks(audit)
    assert result["checks"]["06-semantics.taxonomy"]["status"] == "UNKNOWN"
    assert result["checks"]["12-local.hours"]["status"] == "UNKNOWN"
