"""Tests for the deterministic, evidence-based remediation planner."""
from __future__ import annotations

from ope.planner import build_remediation_plan, diagnosis_markdown


def _finding(fid: str, module: str, priority: float, *, remediation=None, symptom="s", severity="high"):
    return {
        "id": fid,
        "module": module,
        "symptom": symptom,
        "severity": severity,
        "priority": priority,
        "root_cause": "rc",
        "remediation": remediation or [],
        "validation": [],
    }


class TestBuildRemediationPlan:
    def test_no_failures_gives_empty_plan(self):
        result = {
            "modules": {f"{i:02d}": {"status": "PASS"} for i in range(1, 21)},
            "findings": [],
            "dependency_root_causes": {},
        }
        plan = build_remediation_plan(result)
        assert plan["root_causes"] == []
        assert plan["direct_failures"] == []
        assert plan["blocked"] == []
        assert plan["summary"]["planned_findings"] == 0

    def test_single_root_cause_lists_unblocked_modules(self):
        modules = {f"{i:02d}": {"status": "BLOCKED"} for i in range(3, 21)}
        modules["01"] = {"status": "PASS"}
        modules["02"] = {"status": "FAIL", "score": 0.0}
        result = {
            "modules": modules,
            "findings": [_finding("f1", "02-infrastructure", 0.9, remediation=["Fix hosting"])],
            "dependency_root_causes": {f"{i:02d}": ["02"] for i in range(3, 21)},
        }
        plan = build_remediation_plan(result)
        assert len(plan["root_causes"]) == 1
        step = plan["root_causes"][0]
        assert step["module"] == "02"
        assert step["unblock_count"] == 18
        assert step["findings"][0]["id"] == "f1"
        assert plan["summary"]["blocked_count"] == 18

    def test_root_causes_ordered_by_unblock_impact(self):
        # 02 unblocks many; 19 unblocks only 20.
        modules = {"02": {"status": "FAIL"}, "19": {"status": "FAIL"}, "20": {"status": "BLOCKED"}}
        modules.update({f"{i:02d}": {"status": "BLOCKED"} for i in range(3, 19)})
        rc = {f"{i:02d}": ["02"] for i in range(3, 20)}
        rc["20"] = ["02", "19"]
        result = {"modules": modules, "findings": [], "dependency_root_causes": rc}
        plan = build_remediation_plan(result)
        assert [s["module"] for s in plan["root_causes"]] == ["02", "19"]
        assert plan["root_causes"][0]["unblock_count"] > plan["root_causes"][1]["unblock_count"]

    def test_direct_failure_blocks_nothing(self):
        modules = {f"{i:02d}": {"status": "PASS"} for i in range(1, 20)}
        modules["20"] = {"status": "FAIL", "score": 0.0}
        result = {
            "modules": modules,
            "findings": [_finding("f9", "20-continuous-optimization", 0.5)],
            "dependency_root_causes": {},
        }
        plan = build_remediation_plan(result)
        assert plan["root_causes"] == []
        assert len(plan["direct_failures"]) == 1
        assert plan["direct_failures"][0]["module"] == "20"
        assert plan["direct_failures"][0]["unblock_count"] == 0

    def test_findings_sorted_by_priority_then_id(self):
        result = {
            "modules": {"02": {"status": "FAIL"}, "03": {"status": "BLOCKED"}},
            "findings": [
                _finding("b", "02-infrastructure", 0.5),
                _finding("a", "02-infrastructure", 0.9),
                _finding("c", "02-infrastructure", 0.9),
            ],
            "dependency_root_causes": {"03": ["02"]},
        }
        step = build_remediation_plan(result)["root_causes"][0]
        assert [f["id"] for f in step["findings"]] == ["a", "c", "b"]

    def test_root_cause_without_finding_record_is_honest(self):
        # Module 02 FAIL from a failing check, but no finding record exists.
        result = {
            "modules": {"02": {"status": "FAIL"}, "03": {"status": "BLOCKED"}},
            "findings": [],
            "dependency_root_causes": {"03": ["02"]},
        }
        step = build_remediation_plan(result)["root_causes"][0]
        assert step["module"] == "02"
        assert step["findings"] == []  # nothing invented
        assert step["finding_count"] == 0

    def test_blocked_modules_list_what_they_wait_on(self):
        result = {
            "modules": {"02": {"status": "FAIL"}, "03": {"status": "BLOCKED"}, "04": {"status": "BLOCKED"}},
            "findings": [],
            "dependency_root_causes": {"03": ["02"], "04": ["02"]},
        }
        plan = build_remediation_plan(result)
        blocked = {b["module"]: b["waiting_on"] for b in plan["blocked"]}
        assert blocked == {"03": ["02"], "04": ["02"]}

    def test_plan_is_deterministic(self):
        modules = {"02": {"status": "FAIL"}, "07": {"status": "FAIL"}, "09": {"status": "BLOCKED"}}
        result = {
            "modules": modules,
            "findings": [_finding("f1", "02-infrastructure", 0.5), _finding("f2", "07-content", 0.7)],
            "dependency_root_causes": {"09": ["02", "07"]},
        }
        assert build_remediation_plan(result) == build_remediation_plan(result)

    def test_planner_does_not_fabricate_remediation(self):
        result = {
            "modules": {"02": {"status": "FAIL"}, "03": {"status": "BLOCKED"}},
            "findings": [_finding("f1", "02-infrastructure", 0.9)],  # no remediation text
            "dependency_root_causes": {"03": ["02"]},
        }
        step = build_remediation_plan(result)["root_causes"][0]
        assert step["findings"][0]["remediation"] == []

    def test_unknown_only_run_has_empty_plan(self):
        # A run with no FAIL evidence (all UNKNOWN) must plan no work.
        result = {
            "modules": {f"{i:02d}": {"status": "UNKNOWN"} for i in range(1, 21)},
            "findings": [],
            "dependency_root_causes": {},
        }
        plan = build_remediation_plan(result)
        assert plan["root_causes"] == []
        assert plan["direct_failures"] == []
        assert plan["summary"]["planned_findings"] == 0

    def test_duplicate_finding_ids_are_handled_deterministically(self):
        result = {
            "modules": {"02": {"status": "FAIL"}, "03": {"status": "BLOCKED"}},
            "findings": [
                _finding("dup", "02-infrastructure", 0.9),
                _finding("dup", "02-infrastructure", 0.9),
            ],
            "dependency_root_causes": {"03": ["02"]},
        }
        step = build_remediation_plan(result)["root_causes"][0]
        # Findings are surfaced as-is (evidence is not invented or dropped),
        # and ordering is deterministic.
        assert [f["id"] for f in step["findings"]] == ["dup", "dup"]
        assert build_remediation_plan(result) == build_remediation_plan(result)


class TestDiagnosisMarkdown:
    def test_renders_health_and_no_failures(self):
        result = {
            "modules": {f"{i:02d}": {"status": "PASS", "score": 100.0} for i in range(1, 21)},
            "findings": [],
            "dependency_root_causes": {},
            "health": 100.0,
        }
        md = "\n".join(diagnosis_markdown(result))
        assert "Global health:" in md
        assert "no remediation is required" in md.lower()

    def test_renders_root_cause_and_unblock_impact(self):
        modules = {"02": {"status": "FAIL", "score": 0.0}, "03": {"status": "BLOCKED", "score": None}}
        result = {
            "modules": modules,
            "findings": [_finding("f1", "02-infrastructure", 0.9, remediation=["Fix hosting"])],
            "dependency_root_causes": {"03": ["02"]},
            "health": 0.0,
        }
        md = "\n".join(diagnosis_markdown(result))
        assert "Remediation plan" in md
        assert "Module 02" in md
        assert "unblocks 1 module" in md
        assert "Fix hosting" in md
        assert "Module 03" in md  # blocked, waiting

    def test_health_none_is_labelled(self):
        result = {"modules": {}, "findings": [], "dependency_root_causes": {}, "health": None}
        md = "\n".join(diagnosis_markdown(result))
        assert "N/A (insufficient evidence)" in md
