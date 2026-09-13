from ope.module_runner import CheckResult, CheckSpec, ExecutionStatus, ModuleRunner


def test_none_result_is_unknown():
    runner = ModuleRunner([CheckSpec("x.check", "01-entity", lambda _: None)])
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"
    assert result["modules"]["01-entity"]["status"] == "UNKNOWN"


def test_false_result_is_fail():
    runner = ModuleRunner([CheckSpec("x.check", "01-entity", lambda _: False)])
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "FAIL"


def test_true_result_without_evidence_is_unknown():
    runner = ModuleRunner([CheckSpec("x.check", "01-entity", lambda _: True)])
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"
    assert result["checks"]["x.check"]["reason"] == "check returned PASS without evidence"


def test_pass_check_result_requires_evidence():
    runner = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS))]
    )
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"


def test_malformed_pass_evidence_is_unknown():
    result = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=[{}]))]
    ).run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"


def test_invalid_confidence_makes_pass_unknown():
    evidence = [{"source": "test", "observed_at": "2026-09-13T00:00:00Z", "confidence": 2.0}]
    result = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=evidence))]
    ).run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"


def test_demoting_pass_preserves_findings_and_reason():
    finding = {"id": "F-1", "symptom": "missing title"}
    result = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, findings=[finding], reason="observed"))]
    ).run()
    check = result["checks"]["x.check"]
    assert check["status"] == "UNKNOWN"
    assert check["findings"] == [finding]
    assert check["reason"] == "observed"


def test_pass_with_evidence_is_preserved():
    evidence = [{"source": "test", "observed_at": "2026-09-13T00:00:00Z", "target": "x", "value": True, "confidence": 1.0}]
    runner = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=evidence))]
    )
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "PASS"
    assert result["checks"]["x.check"]["evidence"] == evidence


def test_empty_block_on_is_respected():
    runner = ModuleRunner(
        [
            CheckSpec("x.first", "01-entity", lambda _: False),
            CheckSpec("x.second", "01-entity", lambda _: True, ("x.first",)),
        ],
        block_on=frozenset(),
    )
    result = runner.run()
    assert result["checks"]["x.first"]["status"] == "FAIL"
    assert result["checks"]["x.second"]["status"] == "UNKNOWN"


def test_default_blocking_preserves_unknown_semantics():
    runner = ModuleRunner(
        [
            CheckSpec("x.first", "01-entity", lambda _: None),
            CheckSpec("x.second", "01-entity", lambda _: True, ("x.first",)),
        ]
    )
    result = runner.run()
    assert result["checks"]["x.first"]["status"] == "UNKNOWN"
    assert result["checks"]["x.second"]["status"] == "BLOCKED"
