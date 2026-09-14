from ope.root_cause import enrich_finding, enrich_result


def test_missing_root_cause_becomes_hypothesis():
    finding = enrich_finding({"module": "performance", "evidence": []})
    assert finding["status"] == "HYPOTHESIS"
    assert finding["evidence_status"] == "HYPOTHESIS"
    assert finding["root_cause"]
    assert 0 <= finding["confidence"] <= 1


def test_whitespace_only_root_cause_becomes_hypothesis():
    # Regression test: a root_cause of only whitespace is functionally
    # absent and must not be treated as a real explanation.
    finding = enrich_finding({"module": "performance", "root_cause": "   ", "evidence": []})
    assert finding["status"] == "HYPOTHESIS"
    assert finding["root_cause"] != "   "


def test_stated_root_cause_without_evidence_becomes_hypothesis():
    # Regression test: a finding with real root_cause text but zero
    # supporting evidence must not be allowed to stand as OBSERVED --
    # an unverified explanation is a hypothesis, not an observation.
    finding = enrich_finding({"module": "performance", "root_cause": "Server misconfigured.", "evidence": []})
    assert finding["status"] == "HYPOTHESIS"
    assert finding["evidence_status"] == "HYPOTHESIS"


def test_fact_status_without_evidence_is_demoted_to_hypothesis():
    # Regression test: a caller cannot assert status="FACT" -- the
    # strongest claim in evidence_status_enum -- with zero evidence behind
    # it. This is the hypothesis-presented-as-fact failure mode the engine
    # exists to prevent.
    finding = enrich_finding(
        {"module": "performance", "root_cause": "Definitely a caching bug.", "status": "FACT", "evidence": []}
    )
    assert finding["status"] == "HYPOTHESIS"
    assert finding["evidence_status"] == "HYPOTHESIS"


def test_fact_status_with_real_evidence_is_preserved():
    finding = enrich_finding(
        {
            "module": "performance",
            "root_cause": "Confirmed via HTTP 500 response.",
            "status": "FACT",
            "evidence": [{"source": "direct-http", "observed_at": "t", "confidence": 1.0}],
        }
    )
    assert finding["status"] == "FACT"


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
    assert finding["execution_status"] == "FAIL"


def test_result_gets_canonical_engine_contract():
    result = enrich_result({"findings": [{"module": "index"}]})
    assert result["engine_contract"] == "evidence-diagnostic-v1"
    assert result["findings"][0]["status"] == "HYPOTHESIS"
