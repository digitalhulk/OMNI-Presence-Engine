from ope import engine


def _result(status="PASS"):
    return {
        "modules": {
            "01": {"status": status, "findings": []},
            "02": {"status": "PASS", "findings": []},
        },
        "findings": [],
        "inventory": {},
    }


def test_partial_registry_coverage_is_unknown(monkeypatch):
    def fake_execute(_):
        return {
            "checks": {
                "01-entity.identity": {
                    "module": "01-entity",
                    "status": "PASS",
                }
            }
        }

    monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
    output = engine.normalize_result(_result())
    assert output["modules"]["01"]["status"] == "UNKNOWN"


def test_failed_bound_check_is_fail(monkeypatch):
    def fake_execute(_):
        return {
            "checks": {
                "01-entity.identity": {
                    "module": "01-entity",
                    "status": "FAIL",
                }
            }
        }

    monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
    output = engine.normalize_result(_result())
    assert output["modules"]["01"]["status"] == "FAIL"


def test_existing_fail_is_not_overwritten(monkeypatch):
    def fake_execute(_):
        return {"checks": {}}

    monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
    output = engine.normalize_result(_result(status="FAIL"))
    assert output["modules"]["01"]["status"] == "FAIL"


def test_all_na_is_na(monkeypatch):
    def fake_execute(_):
        return {
            "checks": {
                check_id: {"module": "01-entity", "status": "N/A"}
                for check_id in engine.checks_for_module("01-entity")
            }
        }

    monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
    output = engine.normalize_result(_result())
    assert output["modules"]["01"]["status"] == "N/A"


def test_normalization_preserves_report_data(monkeypatch):
    def fake_execute(_):
        return {"checks": {}}

    monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
    result = _result()
    result["modules"]["01"]["findings"] = [{"id": "F-1"}]
    result["custom"] = {"keep": True}
    output = engine.normalize_result(result)
    assert output["modules"]["01"]["findings"] == [{"id": "F-1"}]
    assert output["custom"] == {"keep": True}
