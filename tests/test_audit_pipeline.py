from ope.audit_pipeline import execute_audit_checks


BOUND = {
    "02-infrastructure.hosting.availability",
    "03-code.head_metadata",
    "05-index.canonicalization",
    "06-semantics.structured_data",
    "13-ux.mobile_usability",
    "14-accessibility.alt_text",
    "17-language.language_declaration",
    "04-crawl.robots_access",
    "04-crawl.bot_access",
    "10-ai-search.agent_accessibility",
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
            "robots": {
                "url": "https://example.com/robots.txt",
                "status": 200,
                "error": None,
                "rule_count": 1,
                "ai_crawlers": {"GPTBot": "ALLOW", "OAI-SearchBot": "ALLOW"},
                "blocked_ai_crawlers": [],
                "allowed_ai_crawlers": ["GPTBot", "OAI-SearchBot"],
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
