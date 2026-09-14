from ope import engine
from ope.engine import normalize_performance_result, normalize_site_result


def _result(status="PASS"):
    return {
        "modules": {
            "01": {"status": status, "findings": []},
            "02": {"status": "PASS", "findings": []},
        },
        "findings": [],
        "inventory": {},
    }


def _full_result():
    return {
        "modules": {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)},
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


class TestScoringIntegration:
    def test_normalize_result_has_health(self, monkeypatch) -> None:
        def fake_execute(_):
            return {"checks": {}}

        monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
        output = engine.normalize_result(_full_result())
        assert "health" in output

    def test_normalize_result_modules_have_score(self, monkeypatch) -> None:
        def fake_execute(_):
            return {
                "checks": {
                    cid: {"module": "01-entity", "status": "PASS", "evidence": [{"confidence": 1.0}]}
                    for cid in engine.checks_for_module("01-entity")
                }
            }

        monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
        output = engine.normalize_result(_full_result())
        assert output["modules"]["01"]["score"] == 100.0

    def test_normalize_result_health_is_numeric_or_none(self, monkeypatch) -> None:
        def fake_execute(_):
            return {"checks": {}}

        monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
        output = engine.normalize_result(_full_result())
        health = output["health"]
        assert health is None or isinstance(health, float)

    def test_normalize_site_result_has_health(self) -> None:
        site = {"findings": [], "pages": [], "crawl_summary": {}, "inventory": {}}
        result = normalize_site_result(site)
        assert "health" in result
        for mod in result["modules"].values():
            assert "score" in mod

    def test_normalize_performance_result_has_health(self) -> None:
        perf = {
            "target": "https://example.com",
            "status": "COMPLETED",
            "performance_report": {"url": "https://example.com/", "findings": []},
        }
        result = normalize_performance_result(perf)
        assert "health" in result
        for mod in result["modules"].values():
            assert "score" in mod

    def test_all_pass_checks_give_full_score(self, monkeypatch) -> None:
        check_ids = engine.checks_for_module("01-entity")
        def fake_execute(_):
            return {
                "checks": {
                    cid: {"module": "01-entity", "status": "PASS", "evidence": [{"confidence": 0.9}]}
                    for cid in check_ids
                }
            }

        monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
        output = engine.normalize_result(_full_result())
        assert output["modules"]["01"]["score"] == 100.0

    def test_mixed_checks_give_partial_score(self, monkeypatch) -> None:
        check_ids = list(engine.checks_for_module("01-entity"))
        def fake_execute(_):
            checks = {}
            for i, cid in enumerate(check_ids):
                checks[cid] = {
                    "module": "01-entity",
                    "status": "PASS" if i % 2 == 0 else "FAIL",
                    "evidence": [{"confidence": 0.9}],
                }
            return {"checks": checks}

        monkeypatch.setattr(engine, "execute_audit_checks", fake_execute)
        output = engine.normalize_result(_full_result())
        score = output["modules"]["01"]["score"]
        assert score is not None
        assert 0.0 < score < 100.0
