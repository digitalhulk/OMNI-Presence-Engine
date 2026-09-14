from ope import engine
from ope.engine import normalize_performance_result


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


class TestNormalizePerformanceResult:
    def test_stamps_engine_contract(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {"url": "https://example.com/", "status": "COMPLETED", "findings": []},
        }
        result = normalize_performance_result(perf)
        assert result["engine_contract"] == "evidence-diagnostic-v1"
        assert result["engine_scope"] == "performance"

    def test_performance_findings_converted(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {
                "url": "https://example.com/",
                "status": "COMPLETED",
                "findings": [
                    {
                        "module": "performance.vitals",
                        "severity": "HIGH",
                        "symptom": "LCP is 5000ms (poor)",
                        "evidence": {"lcp_ms": 5000.0},
                        "recommendation": "Optimize LCP resource",
                    },
                ],
            },
        }
        result = normalize_performance_result(perf)
        assert len(result["findings"]) == 1
        f = result["findings"][0]
        assert f["id"] == "perf-001"
        assert f["severity"] == "high"
        assert f["status"] == "OBSERVED"
        assert f["priority"] == 0.8
        assert "confidence" in f

    def test_checks_are_executed(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {"url": "https://example.com/", "findings": []},
        }
        result = normalize_performance_result(perf)
        assert "checks" in result
        assert isinstance(result["checks"], dict)
        assert len(result["checks"]) > 0

    def test_modules_are_created(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {"url": "https://example.com/", "findings": []},
        }
        result = normalize_performance_result(perf)
        assert "modules" in result
        assert len(result["modules"]) == 20
        for mod in result["modules"].values():
            assert "status" in mod

    def test_evidence_injected_into_inventory(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {
                "url": "https://example.com/",
                "findings": [],
                "vitals_summary": {
                    "DESKTOP": {"lcp": {"value_ms": 2400.0, "rating": "GOOD"}},
                },
                "resource_analysis": {"total_requests": 50, "total_transfer_bytes": 1000000},
            },
        }
        result = normalize_performance_result(perf)
        inv = result["inventory"]
        assert "perf_vitals_summary" in inv
        assert "perf_resource_analysis" in inv

    def test_empty_result_still_normalizes(self) -> None:
        result = normalize_performance_result({})
        assert result["engine_contract"] == "evidence-diagnostic-v1"
        assert result["engine_scope"] == "performance"
        assert result["findings"] == []

    def test_non_completed_findings_empty(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "ERROR",
            "performance_report": {"url": "https://example.com/", "findings": [
                {"severity": "HIGH", "symptom": "test"},
            ]},
        }
        result = normalize_performance_result(perf)
        assert len(result["findings"]) == 1

    def test_finding_module_defaults_to_performance(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {
                "url": "https://example.com/",
                "findings": [
                    {"severity": "MEDIUM", "symptom": "Many requests", "module": "nodashmodule"},
                ],
            },
        }
        result = normalize_performance_result(perf)
        assert result["findings"][0]["module"] == "15-performance"
