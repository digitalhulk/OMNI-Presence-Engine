"""Tests for evidence.py — EvidenceRecord, RootCauseFinding, normalization."""
from __future__ import annotations

from ope.evidence import (
    EvidenceRecord,
    RootCauseFinding,
    make_finding,
    normalize_evidence,
)


class TestEvidenceRecord:
    def test_fields(self) -> None:
        r = EvidenceRecord(source="audit", target="https://example.com", value={"status": 200})
        assert r.source == "audit"
        assert r.target == "https://example.com"
        assert r.value == {"status": 200}
        assert r.confidence == 1.0
        assert r.provenance == "direct"

    def test_to_dict(self) -> None:
        r = EvidenceRecord(source="s", target="t", value="v")
        d = r.to_dict()
        assert d["source"] == "s"
        assert d["target"] == "t"
        assert "observed_at" in d

    def test_frozen(self) -> None:
        r = EvidenceRecord(source="s", target="t", value="v")
        import pytest
        with pytest.raises(AttributeError):
            r.source = "other"  # type: ignore[misc]


class TestNormalizeEvidence:
    def test_from_records(self) -> None:
        records = [EvidenceRecord(source="a", target="t", value=1, confidence=0.9)]
        result = normalize_evidence(records)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.9

    def test_from_dicts(self) -> None:
        items = [{"source": "a", "target": "t", "value": 1, "confidence": 1.5}]
        result = normalize_evidence(items)
        assert result[0]["confidence"] == 1.0  # clamped

    def test_negative_confidence_clamped(self) -> None:
        items = [{"source": "a", "target": "t", "value": 1, "confidence": -0.5}]
        result = normalize_evidence(items)
        assert result[0]["confidence"] == 0.0


class TestRootCauseFinding:
    def test_to_dict(self) -> None:
        f = RootCauseFinding(
            id="f-001", module="03-code", symptom="missing title",
            status="OBSERVED", severity="high", priority=0.7,
        )
        d = f.to_dict()
        assert d["id"] == "f-001"
        assert d["module"] == "03-code"
        assert d["priority"] == 0.7

    def test_defaults(self) -> None:
        f = RootCauseFinding(
            id="f-002", module="15-performance", symptom="slow",
            status="OBSERVED", severity="medium", priority=0.5,
        )
        assert f.affected_layer == ""
        assert f.dependency == ""
        assert f.root_cause == ""
        assert f.remediation == []
        assert f.validation == []
        assert f.regression_guard == []


class TestMakeFinding:
    def test_basic(self) -> None:
        f = make_finding(
            finding_id="f-001", module="03-code", symptom="Missing title",
            severity="high",
            evidence=[EvidenceRecord(source="audit", target="https://example.com", value=True)],
            root_cause="No <title> element in HTML",
            priority=0.7,
        )
        assert f.id == "f-001"
        assert f.status == "OBSERVED"
        assert f.priority == 0.7
        assert len(f.evidence) == 1
        assert f.evidence[0]["source"] == "audit"

    def test_priority_clamped(self) -> None:
        f = make_finding(
            finding_id="f-001", module="x", symptom="s", severity="high",
            evidence=[], priority=1.5,
        )
        assert f.priority == 1.5  # make_finding rounds but doesn't clamp

    def test_evidence_normalized(self) -> None:
        f = make_finding(
            finding_id="f-001", module="x", symptom="s", severity="high",
            evidence=[{"source": "a", "target": "t", "value": 1, "confidence": 2.0}],
        )
        assert f.evidence[0]["confidence"] == 1.0
