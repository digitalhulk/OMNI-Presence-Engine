import pytest

from ope.evidence import (
    EvidenceRecord,
    InvalidEvidenceError,
    make_finding,
    normalize_evidence,
)


def test_valid_evidence_is_preserved():
    normalized = normalize_evidence(
        [{"source": "ope-audit", "target": "https://example.com", "value": {"status": 200}, "confidence": 0.9}]
    )
    assert normalized[0]["source"] == "ope-audit"
    assert normalized[0]["target"] == "https://example.com"
    assert normalized[0]["value"] == {"status": 200}
    assert normalized[0]["confidence"] == 0.9


def test_evidence_record_passthrough():
    record = EvidenceRecord(source="s", target="t", value=1, confidence=0.5)
    normalized = normalize_evidence([record])
    assert normalized[0]["confidence"] == 0.5
    assert normalized[0]["source"] == "s"


def test_malformed_confidence_degrades_to_zero_not_a_crash():
    normalized = normalize_evidence(
        [{"source": "x", "target": "y", "value": 1, "confidence": "not-a-number"}]
    )
    assert normalized[0]["confidence"] == 0.0


def test_missing_confidence_defaults_to_full_confidence():
    normalized = normalize_evidence([{"source": "x", "target": "y", "value": 1}])
    assert normalized[0]["confidence"] == 1.0


def test_out_of_range_confidence_is_clamped():
    high = normalize_evidence([{"source": "x", "target": "y", "value": 1, "confidence": 5.0}])
    low = normalize_evidence([{"source": "x", "target": "y", "value": 1, "confidence": -5.0}])
    assert high[0]["confidence"] == 1.0
    assert low[0]["confidence"] == 0.0


def test_missing_source_raises_invalid_evidence_error():
    with pytest.raises(InvalidEvidenceError):
        normalize_evidence([{"target": "y", "value": 1}])


def test_missing_target_raises_invalid_evidence_error():
    with pytest.raises(InvalidEvidenceError):
        normalize_evidence([{"source": "x", "value": 1}])


def test_empty_source_raises_invalid_evidence_error():
    with pytest.raises(InvalidEvidenceError):
        normalize_evidence([{"source": "", "target": "y", "value": 1}])


def test_non_dict_non_record_item_raises_invalid_evidence_error():
    with pytest.raises(InvalidEvidenceError):
        normalize_evidence(["not-a-valid-evidence-item"])


def test_make_finding_with_malformed_priority_does_not_crash():
    finding = make_finding(
        finding_id="F-1",
        module="01-entity",
        symptom="test symptom",
        severity="low",
        evidence=[{"source": "a", "target": "b", "value": 1}],
        priority="garbage",
    )
    assert finding.priority == 0.0


def test_make_finding_clamps_out_of_range_priority():
    finding = make_finding(
        finding_id="F-1",
        module="01-entity",
        symptom="test symptom",
        severity="low",
        evidence=[{"source": "a", "target": "b", "value": 1}],
        priority=250,
    )
    assert finding.priority == 100.0


def test_make_finding_propagates_invalid_evidence():
    with pytest.raises(InvalidEvidenceError):
        make_finding(
            finding_id="F-1",
            module="01-entity",
            symptom="test symptom",
            severity="low",
            evidence=[{"value": 1}],
        )
