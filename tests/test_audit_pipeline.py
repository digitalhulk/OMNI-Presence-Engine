from ope.audit_pipeline import execute_audit_checks


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
        },
        "findings": [],
    }


def test_bound_audit_checks_produce_evidence_backed_passes():
    result = execute_audit_checks(_audit_result())
    assert result["checks"]["02-infrastructure.hosting.availability"]["status"] == "PASS"
    assert result["checks"]["03-code.head_metadata"]["status"] == "PASS"
    assert result["checks"]["05-index.canonicalization"]["status"] == "PASS"
    assert result["checks"]["06-semantics.structured_data"]["status"] == "PASS"
    assert result["checks"]["14-accessibility.alt_text"]["status"] == "PASS"
    for check_id in result["checks"]:
        if check_id in {
            "02-infrastructure.hosting.availability",
            "03-code.head_metadata",
            "05-index.canonicalization",
            "06-semantics.structured_data",
            "13-ux.mobile_usability",
            "14-accessibility.alt_text",
            "17-language.language_declaration",
        }:
            assert result["checks"][check_id]["evidence"]


def test_unbound_checks_remain_unknown():
    result = execute_audit_checks(_audit_result())
    assert result["checks"]["01-entity.identity"]["status"] == "UNKNOWN"


def test_failed_audit_observation_produces_fail():
    audit = _audit_result()
    audit["inventory"]["title"] = ""
    audit["findings"] = [{"id": "CODE-HTTP-001"}]
    result = execute_audit_checks(audit)
    assert result["checks"]["03-code.head_metadata"]["status"] == "FAIL"
