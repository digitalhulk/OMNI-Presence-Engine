from ope.audit import audit
from ope.engine import normalize_result


def test_normalize_result_preserves_unknown_semantics():
    result = normalize_result({"findings": [], "modules": {"01": {"status": "UNKNOWN", "findings": []}}})
    assert result["engine_contract"] == "evidence-diagnostic-v1"
    assert result["modules"]["01"]["status"] == "UNKNOWN"


def test_normalize_finding_defaults_missing_root_cause_to_hypothesis():
    result = normalize_result({"findings": [{"id": "x", "module": "01-entity", "priority": 10, "evidence": []}]})
    finding = result["findings"][0]
    assert finding["status"] == "HYPOTHESIS"
    assert finding["root_cause"]
    assert finding["confidence"] == 0.2


def test_audit_rejects_local_targets():
    try:
        audit("http://127.0.0.1/")
    except ValueError as exc:
        assert "restricted" in str(exc)
    else:
        raise AssertionError("local target was not rejected")
