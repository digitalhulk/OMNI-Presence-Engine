from ope.module_runner import CheckSpec, ExecutionStatus, ModuleRunner


def test_none_result_is_unknown():
    runner = ModuleRunner([CheckSpec("x.check", "01-entity", lambda _: None)])
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "UNKNOWN"
    assert result["modules"]["01-entity"]["status"] == "UNKNOWN"


def test_false_result_is_fail():
    runner = ModuleRunner([CheckSpec("x.check", "01-entity", lambda _: False)])
    result = runner.run()
    assert result["checks"]["x.check"]["status"] == "FAIL"


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
    assert result["checks"]["x.second"]["status"] == "PASS"


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
