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


def test_normalize_finding_preserves_0_100_priority_scale():
    # Regression test: priority is a 0-100 scale per schemas/audit/finding-v1.yaml
    # and matches what audit.py and evidence.py already produce. A prior defect
    # clamped priority to [0, 1] (confidence's scale), which silently collapsed
    # every real-world priority above 1.0 to a flat 1.0 -- destroying remediation
    # ranking, since a priority-8.4 finding and a priority-72.9 finding both
    # became indistinguishable.
    result = normalize_result(
        {
            "findings": [
                {
                    "id": "A", "module": "03-code", "priority": 72.9,
                    "evidence": [{"source": "x", "observed_at": "t", "value": 1, "confidence": 1.0}],
                    "root_cause": "rc1",
                },
                {
                    "id": "B", "module": "03-code", "priority": 8.4,
                    "evidence": [{"source": "x", "observed_at": "t", "value": 1, "confidence": 1.0}],
                    "root_cause": "rc2",
                },
            ]
        }
    )
    by_id = {f["id"]: f for f in result["findings"]}
    assert by_id["A"]["priority"] == 72.9
    assert by_id["B"]["priority"] == 8.4
    assert by_id["A"]["priority"] != by_id["B"]["priority"]


def test_normalize_finding_clamps_priority_to_0_100_not_0_1():
    result = normalize_result(
        {
            "findings": [
                {"id": "high", "module": "01-entity", "priority": 250, "evidence": [], "root_cause": "rc"},
                {"id": "negative", "module": "01-entity", "priority": -10, "evidence": [], "root_cause": "rc"},
            ]
        }
    )
    by_id = {f["id"]: f for f in result["findings"]}
    assert by_id["high"]["priority"] == 100.0
    assert by_id["negative"]["priority"] == 0.0


def test_audit_rejects_local_targets():
    try:
        audit("http://127.0.0.1/")
    except ValueError as exc:
        assert "restricted" in str(exc)
    else:
        raise AssertionError("local target was not rejected")
