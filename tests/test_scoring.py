from ope.scoring import clamp, global_health, module_score, priority


def test_priority_is_bounded():
    assert priority(impact=1, confidence=1, urgency=1, fixability=1) == 100.0
    assert priority(impact=2, confidence=2, urgency=2, fixability=2) == 100.0
    assert priority(impact=-1, confidence=1, urgency=1, fixability=1) == 0.0


def test_unknown_module_has_no_score():
    assert module_score({"status": "UNKNOWN", "findings": []}) is None
    assert module_score({"status": "BLOCKED", "findings": []}) is None


def test_fail_and_pass_scores_are_explicit():
    assert module_score({"status": "FAIL", "findings": ["x"]}) == 0.0
    assert module_score({"status": "PASS", "findings": ["checked"]}) == 100.0


def test_na_module_has_no_score():
    assert module_score({"status": "N/A"}) is None


def test_none_status_has_no_score():
    assert module_score({}) is None
    assert module_score({"status": None}) is None


def test_clamp_boundaries():
    assert clamp(-10.0) == 0.0
    assert clamp(200.0) == 100.0
    assert clamp(55.556) == 55.56


def test_module_score_with_checks_all_pass():
    checks = {
        "01-entity.identity": {"status": "PASS", "evidence": [{"confidence": 0.9}]},
        "01-entity.ownership": {"status": "PASS", "evidence": [{"confidence": 0.8}]},
    }
    score = module_score({"status": "PASS"}, module_checks=checks)
    assert score == 100.0


def test_module_score_with_checks_mixed():
    checks = {
        "01-entity.identity": {"status": "PASS", "evidence": [{"confidence": 0.9}]},
        "01-entity.ownership": {"status": "FAIL", "evidence": [{"confidence": 0.9}]},
    }
    score = module_score({"status": "FAIL"}, module_checks=checks)
    assert score is not None
    assert 45.0 <= score <= 55.0


def test_module_score_with_checks_all_fail():
    checks = {
        "01-entity.identity": {"status": "FAIL", "evidence": [{"confidence": 0.9}]},
        "01-entity.ownership": {"status": "FAIL", "evidence": [{"confidence": 0.9}]},
    }
    score = module_score({"status": "FAIL"}, module_checks=checks)
    assert score == 0.0


def test_module_score_unknown_counts_against():
    checks = {
        "01-entity.identity": {"status": "PASS", "evidence": [{"confidence": 1.0}]},
        "01-entity.ownership": {"status": "UNKNOWN", "evidence": []},
    }
    score = module_score({"status": "UNKNOWN"}, module_checks=checks)
    assert score is not None
    assert score < 100.0
    assert score == 50.0


def test_module_score_na_excluded_from_denominator():
    checks = {
        "01-entity.identity": {"status": "PASS", "evidence": [{"confidence": 1.0}]},
        "01-entity.ownership": {"status": "N/A"},
    }
    score = module_score({"status": "PASS"}, module_checks=checks)
    assert score == 100.0


def test_module_score_all_na_returns_none():
    checks = {
        "01-entity.identity": {"status": "N/A"},
        "01-entity.ownership": {"status": "N/A"},
    }
    assert module_score({"status": "N/A"}, module_checks=checks) is None


def test_module_score_evidence_weighting():
    checks = {
        "c1": {"status": "PASS", "evidence": [{"confidence": 1.0}]},
        "c2": {"status": "FAIL", "evidence": [{"confidence": 0.1}]},
    }
    score = module_score({"status": "FAIL"}, module_checks=checks)
    assert score is not None
    assert score > 50.0


def test_module_score_empty_checks_returns_none():
    assert module_score({"status": "UNKNOWN"}, module_checks={}) is None


def test_global_health_all_scored():
    scores = {"01": 100.0, "02": 80.0, "03": 60.0}
    health = global_health(scores)
    assert health is not None
    assert 60.0 <= health <= 100.0


def test_global_health_no_scores():
    assert global_health({}) is None
    assert global_health({"01": None, "02": None}) is None


def test_global_health_upstream_penalty():
    good = {"01": 100.0, "02": 100.0, "03": 100.0}
    bad_upstream = {"01": 20.0, "02": 100.0, "03": 100.0}
    h_good = global_health(good)
    h_bad = global_health(bad_upstream)
    assert h_good is not None
    assert h_bad is not None
    assert h_bad < h_good


def test_global_health_single_module():
    assert global_health({"05": 75.0}) == 75.0


def test_global_health_skips_none():
    scores = {"01": None, "02": 80.0, "03": None, "04": 60.0}
    health = global_health(scores)
    assert health is not None
    assert 60.0 <= health <= 80.0
