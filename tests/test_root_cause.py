from ope.root_cause import enrich_finding, enrich_result


def test_missing_root_cause_becomes_hypothesis():
    finding = enrich_finding({"module": "performance", "evidence": []})
    assert finding["status"] == "HYPOTHESIS"
    assert finding["root_cause"]
    assert 0 <= finding["confidence"] <= 1


def test_confidence_uses_lowest_evidence_confidence():
    finding = enrich_finding(
        {
            "module": "crawl",
            "evidence": [{"confidence": 0.9}, {"confidence": 0.4}],
            "root_cause": "Robots policy blocks crawler access.",
            "status": "OBSERVED",
        }
    )
    assert finding["confidence"] == 0.4
    assert finding["status"] == "OBSERVED"


def test_result_gets_engine_contract():
    result = enrich_result({"findings": [{"module": "index"}]})
    assert result["engine_contract"] == "evidence-root-cause-v1"
    assert result["findings"][0]["status"] == "HYPOTHESIS"
