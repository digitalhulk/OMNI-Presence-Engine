from ope.orchestrator import AuditOrchestrator


def test_execute_completes_and_keeps_advisory_optional():
    def fake_audit(target):
        return {"target": target, "modules": {}, "findings": [], "inventory": {}}

    def fake_normalize(result):
        result = dict(result)
        result["normalized"] = True
        return result

    def fake_reason(result):
        return {"provider": "test", "advisory": True}

    engine = AuditOrchestrator(fake_audit, fake_normalize, fake_reason)
    run = engine.create_run("https://example.com")
    done = engine.execute(run.run_id)

    assert done.status == "COMPLETED"
    assert done.result["normalized"] is True
    assert done.result["reasoning"]["advisory"] is True
    assert done.completed_modules == 20


def test_advisory_failure_does_not_fail_deterministic_audit():
    def fake_reason(_):
        raise RuntimeError("provider unavailable")

    engine = AuditOrchestrator(
        lambda target: {"target": target, "modules": {}, "findings": [], "inventory": {}},
        lambda result: dict(result),
        fake_reason,
    )
    run = engine.create_run("https://example.com")
    done = engine.execute(run.run_id)

    assert done.status == "COMPLETED"
    assert done.result["reasoning"]["advisory"] is False
    assert done.result["reasoning"]["error"] == "RuntimeError"


def test_cancelled_run_does_not_execute():
    called = []

    def fake_audit(target):
        called.append(target)
        return {"target": target, "modules": {}, "findings": [], "inventory": {}}

    engine = AuditOrchestrator(fake_audit)
    run = engine.create_run("https://example.com")
    assert engine.cancel(run.run_id) is True
    done = engine.execute(run.run_id)

    assert done.status == "CANCELLED"
    assert called == []
