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


def test_pass_with_evidence_is_preserved():
    evidence = [{"source": "test", "target": "x", "value": True, "confidence": 1.0, "observed_at": "2026-01-01T00:00:00+00:00"}]
    runner = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=evidence))]
    )
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "PASS"
    assert result["checks"]["x.check"]["evidence"] == evidence


def test_pass_with_malformed_evidence_is_unknown():
    # Regression test: a non-empty evidence list is not automatically valid
    # evidence. Each entry must have 'source' and 'observed_at' per
    # schemas/audit/finding-v1.yaml; evidence lacking either must not be
    # sufficient to justify PASS.
    evidence = [{"target": "x", "value": True}]  # missing source and observed_at
    runner = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=evidence))]
    )
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"
    assert "malformed" in result["checks"]["x.check"]["reason"]


def test_pass_with_partially_malformed_evidence_list_is_unknown():
    # One valid entry and one invalid entry must not average out to PASS --
    # every evidence entry attached to a PASS result must be trustworthy.
    evidence = [
        {"source": "good", "observed_at": "2026-01-01T00:00:00+00:00", "value": 1},
        {"value": "no source or timestamp"},
    ]
    runner = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=evidence))]
    )
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"


def test_dict_pass_with_malformed_evidence_is_unknown():
    runner = ModuleRunner(
        [CheckSpec("x.check", "01-entity", lambda _: {"status": "PASS", "evidence": [{"no": "source or timestamp"}]})]
    )
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"


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
