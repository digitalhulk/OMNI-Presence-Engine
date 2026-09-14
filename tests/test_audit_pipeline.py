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
        },
        "findings": [],
    }


def test_bound_audit_checks_produce_schema_complete_evidence():
    result = execute_audit_checks(_audit_result())
    for check_id in BOUND:
        check = result["checks"][check_id]
        assert check["status"] == "PASS"
        assert check["evidence"]
        for evidence in check["evidence"]:
            assert evidence["source"] == "ope-audit"
            assert evidence["observed_at"]


def test_unbound_checks_remain_unknown():
    result = execute_audit_checks(_audit_result())
    assert result["checks"]["01-entity.identity"]["status"] == "UNKNOWN"


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
