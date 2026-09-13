from threading import Event, Thread

from ope.orchestrator import AuditOrchestrator
from ope.provider_registry import integration_inventory


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


def test_concurrent_execute_runs_audit_only_once():
    started = Event()
    release = Event()
    calls = []

    def fake_audit(target):
        calls.append(target)
        started.set()
        assert release.wait(timeout=2)
        return {"target": target, "modules": {}, "findings": [], "inventory": {}}

    engine = AuditOrchestrator(fake_audit, lambda result: dict(result), lambda _: {})
    run = engine.create_run("https://example.com")
    first = Thread(target=engine.execute, args=(run.run_id,))
    second = Thread(target=engine.execute, args=(run.run_id,))
    first.start()
    assert started.wait(timeout=2)
    second.start()
    second.join(timeout=2)
    release.set()
    first.join(timeout=2)

    assert calls == ["https://example.com"]
    assert engine.get_run(run.run_id).status == "COMPLETED"


def test_execute_after_completion_does_not_rerun():
    calls = []

    def fake_audit(target):
        calls.append(target)
        return {"target": target, "modules": {}, "findings": [], "inventory": {}}

    engine = AuditOrchestrator(fake_audit, lambda result: dict(result), lambda _: {})
    run = engine.create_run("https://example.com")
    first = engine.execute(run.run_id)
    second = engine.execute(run.run_id)

    assert first.status == second.status == "COMPLETED"
    assert calls == ["https://example.com"]


def test_cancellation_wins_over_finalization():
    entered_normalize = Event()
    release_normalize = Event()

    def fake_normalize(result):
        entered_normalize.set()
        assert release_normalize.wait(timeout=2)
        return dict(result)

    engine = AuditOrchestrator(
        lambda target: {"target": target, "modules": {}, "findings": [], "inventory": {}},
        fake_normalize,
        lambda _: {},
    )
    run = engine.create_run("https://example.com")
    worker = Thread(target=engine.execute, args=(run.run_id,))
    worker.start()
    assert entered_normalize.wait(timeout=2)
    assert engine.cancel(run.run_id) is True
    release_normalize.set()
    worker.join(timeout=2)

    assert engine.get_run(run.run_id).status == "CANCELLED"
    assert engine.get_run(run.run_id).result is None


def test_explicit_empty_environment_is_not_process_environment():
    inventory = integration_inventory({})
    assert all(not item["configured"] for item in inventory["providers"].values())
