from ope.scoring import module_score, priority


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
