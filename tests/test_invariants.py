"""Property-style invariant tests for OPE's core contracts.

These tests do not target a single bug; they assert properties that must
hold for ALL valid (and many invalid) inputs, using stdlib random +
parameterization rather than a third-party property-testing library, per
the instruction to avoid unnecessary dependencies. A fixed seed keeps
failures reproducible.

Each test targets exactly one of the nine invariants called out for this
cluster: PASS-requires-evidence, UNKNOWN-never-becomes-PASS,
FACT/OBSERVED-requires-evidence, partial-coverage-is-UNKNOWN,
priority-in-0..100, deterministic-reconciliation, normalization-does-not-
mutate, reasoning-does-not-mutate-deterministic-truth, and
deterministic-dependency-blocking.
"""

import copy
import random

import pytest

from ope.engine import normalize_finding, normalize_result
from ope.evidence import InvalidEvidenceError, normalize_evidence
from ope.module_runner import CheckResult, CheckSpec, ExecutionStatus, ModuleRunner
from ope.reasoning import reason_about_result
from ope.registry import CHECKS, checks_for_module
from ope.integrations.openrouter import OpenRouterConfig


_RNG = random.Random(20260914)  # fixed seed for reproducibility


# ---------------------------------------------------------------------------
# Invariant: PASS requires valid (schema-compliant) evidence.
# ---------------------------------------------------------------------------

def _random_evidence_entry(rng: random.Random, valid: bool) -> dict:
    if valid:
        return {
            "source": rng.choice(["ope-audit", "direct-http", "html-parser", "provider-x"]),
            "observed_at": "2026-01-01T00:00:00+00:00",
            "value": rng.choice([1, "x", {"a": 1}, [1, 2], None, True]),
            "confidence": rng.uniform(0.0, 1.0),
        }
    # Missing source, missing observed_at, wrong type, or empty dict --
    # any one of these must be enough to disqualify the entry.
    return rng.choice([
        {"observed_at": "2026-01-01T00:00:00+00:00"},  # no source
        {"source": "x"},  # no observed_at
        {"source": "", "observed_at": "2026-01-01T00:00:00+00:00"},  # empty source
        {},
        "not-a-dict",
        None,
    ])


@pytest.mark.parametrize("trial", range(30))
def test_pass_requires_all_valid_evidence(trial):
    rng = random.Random(_RNG.random() + trial)
    n_valid = rng.randint(0, 4)
    n_invalid = rng.randint(0, 3)
    evidence = [_random_evidence_entry(rng, True) for _ in range(n_valid)]
    evidence += [_random_evidence_entry(rng, False) for _ in range(n_invalid)]
    rng.shuffle(evidence)

    def runner(_ctx):
        return CheckResult("x.check", "01-entity", ExecutionStatus.PASS, evidence=evidence)

    result = ModuleRunner([CheckSpec("x.check", "01-entity", runner)]).run()
    status = result["checks"]["x.check"]["status"]

    if n_invalid == 0 and n_valid > 0:
        assert status == "PASS", f"all-valid evidence (n={n_valid}) must yield PASS"
    else:
        assert status == "UNKNOWN", (
            f"PASS must degrade to UNKNOWN when any evidence entry is invalid "
            f"(valid={n_valid}, invalid={n_invalid}), got {status}"
        )


# ---------------------------------------------------------------------------
# Invariant: UNKNOWN can never silently become PASS through reconciliation,
# regardless of how many (or which) module checks happen to be bound.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trial", range(20))
def test_partial_coverage_never_reconciles_to_pass(trial):
    rng = random.Random(_RNG.random() + trial)
    module_id = rng.choice(sorted({c.module for c in CHECKS}))
    all_check_ids = checks_for_module(module_id)
    if len(all_check_ids) < 2:
        pytest.skip("module has fewer than 2 checks; partial coverage is not meaningful")

    # Bind a random non-empty, non-total subset of this module's checks, all PASS.
    n_bound = rng.randint(1, len(all_check_ids) - 1)
    bound_ids = rng.sample(all_check_ids, n_bound)
    fake_checks = {
        cid: {"module": module_id, "status": "PASS"} for cid in bound_ids
    }

    def fake_execute(_):
        return {"checks": fake_checks}

    import ope.engine as engine_mod
    original = engine_mod.execute_audit_checks
    engine_mod.execute_audit_checks = fake_execute
    try:
        module_code = module_id.split("-", 1)[0]
        result = {
            "findings": [],
            "modules": {module_code: {"status": "UNKNOWN", "findings": []}},
        }
        output = normalize_result(result)
    finally:
        engine_mod.execute_audit_checks = original

    assert output["modules"][module_code]["status"] == "UNKNOWN", (
        f"module {module_id} with {n_bound}/{len(all_check_ids)} checks bound (all PASS) "
        f"must reconcile to UNKNOWN, not PASS"
    )


# ---------------------------------------------------------------------------
# Invariant: a finding cannot claim FACT/OBSERVED without valid evidence,
# and priority always lands in [0, 100] regardless of input.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trial", range(30))
def test_fact_observed_requires_evidence_and_priority_stays_bounded(trial):
    rng = random.Random(_RNG.random() + trial)
    has_evidence = rng.choice([True, False])
    claimed_status = rng.choice(["FACT", "OBSERVED", "HYPOTHESIS", None])
    raw_priority = rng.choice([
        rng.uniform(-500, 500), "not-a-number", None, float("inf"), float("-inf"),
        float("nan"), rng.randint(-1000, 1000),
    ])
    root_cause = rng.choice(["a real explanation", "   ", "", None])

    finding = {
        "module": "01-entity",
        "root_cause": root_cause,
        "priority": raw_priority,
        "evidence": [{"source": "x", "observed_at": "t", "confidence": 1.0}] if has_evidence else [],
    }
    if claimed_status is not None:
        finding["status"] = claimed_status

    out = normalize_finding(finding)

    # priority invariant: always a finite float in [0, 100], never NaN/inf,
    # regardless of how malformed the input was.
    assert isinstance(out["priority"], float)
    assert 0.0 <= out["priority"] <= 100.0

    # FACT/OBSERVED invariant: cannot stand without evidence AND a real
    # (non-whitespace) root cause.
    root_cause_present = bool((root_cause or "").strip())
    if claimed_status in ("FACT", "OBSERVED") and not (has_evidence and root_cause_present):
        assert out["status"] == "HYPOTHESIS", (
            f"status={claimed_status} evidence={has_evidence} root_cause={root_cause!r} "
            f"must demote to HYPOTHESIS, got {out['status']}"
        )


# ---------------------------------------------------------------------------
# Invariant: module reconciliation is a deterministic pure function of its
# inputs -- same (existing, check_statuses) always yields the same result.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trial", range(20))
def test_module_reconciliation_is_deterministic(trial):
    rng = random.Random(_RNG.random() + trial)
    from ope.engine import _reconcile_module_status

    existing = rng.choice([None, "UNKNOWN", "FAIL", "BLOCKED", "N/A", "PASS"])
    n = rng.randint(0, 5)
    statuses = [rng.choice(["PASS", "FAIL", "UNKNOWN", "BLOCKED", "N/A"]) for _ in range(n)]

    r1 = _reconcile_module_status(existing, statuses)
    r2 = _reconcile_module_status(existing, list(statuses))  # fresh list, same content
    assert r1 == r2, "reconciliation must be a pure function of its inputs"

    # Order of check_statuses must not matter.
    shuffled = list(statuses)
    rng.shuffle(shuffled)
    r3 = _reconcile_module_status(existing, shuffled)
    assert r1 == r3, "reconciliation must not depend on check_statuses ordering"


# ---------------------------------------------------------------------------
# Invariant: normalize_result / normalize_finding never mutate their input.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trial", range(15))
def test_normalize_result_never_mutates_input(trial):
    rng = random.Random(_RNG.random() + trial)
    result = {
        "target": "https://x.com",
        "findings": [
            {
                "id": f"F-{i}",
                "module": "01-entity",
                "priority": rng.uniform(0, 100),
                "evidence": [{"source": "x", "observed_at": "t", "confidence": rng.uniform(0, 1)}],
                "root_cause": rng.choice(["real cause", "", None]),
            }
            for i in range(rng.randint(0, 4))
        ],
        "modules": {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)},
    }
    snapshot = copy.deepcopy(result)
    normalize_result(result)
    assert result == snapshot, "normalize_result must not mutate its input"


# ---------------------------------------------------------------------------
# Invariant: advisory reasoning never mutates the deterministic result it
# was given, regardless of what the (possibly malformed) LLM response says.
# ---------------------------------------------------------------------------

class _FakeReasoningClient:
    def __init__(self, response):
        self.config = OpenRouterConfig(api_key="t", model="m")
        self._response = response

    def chat_json(self, messages, *, temperature=0.0):
        return self._response


@pytest.mark.parametrize("trial", range(15))
def test_reasoning_never_mutates_deterministic_result(trial):
    rng = random.Random(_RNG.random() + trial)
    result = {
        "target": "https://x.com",
        "modules": {"01": {"status": rng.choice(["PASS", "FAIL", "UNKNOWN"])}},
        "findings": [{"id": "F-1", "status": rng.choice(["HYPOTHESIS", "OBSERVED", "FACT"])}],
    }
    snapshot = copy.deepcopy(result)

    fabricated_response = rng.choice([
        {"root_cause_hypotheses": ["the deterministic result is wrong"], "priorities": [], "recommendations": [], "content_opportunities": [], "validation_plan": []},
        {"status": "PASS", "modules": {"01": {"status": "PASS"}}},  # attempts to look like a result
        "not even a dict",
        None,
        {},
    ])
    client = _FakeReasoningClient(fabricated_response)

    try:
        reason_about_result(result, client)
    except Exception:
        pass  # contract errors are expected for malformed responses; only mutation matters here

    assert result == snapshot, "reasoning must never mutate the deterministic result, even given a fabricated-looking response"


# ---------------------------------------------------------------------------
# Invariant: dependency blocking in ModuleRunner is deterministic --
# the same dependency graph and statuses always produce the same BLOCKED set.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trial", range(15))
def test_dependency_blocking_is_deterministic(trial):
    rng = random.Random(_RNG.random() + trial)
    n = rng.randint(2, 6)
    ids = [f"c{i}" for i in range(n)]
    outcomes = {cid: rng.choice(["PASS", "FAIL", "UNKNOWN"]) for cid in ids}

    def make_runner(status_str):
        status = ExecutionStatus(status_str)
        evidence = [{"source": "x", "observed_at": "t"}] if status == ExecutionStatus.PASS else []
        return lambda _ctx, s=status, e=evidence: CheckResult(_ctx.get("__id__", ""), "01-entity", s, evidence=e)

    def build_specs():
        specs = []
        for i, cid in enumerate(ids):
            deps = tuple(ids[:i]) if i > 0 and rng.random() < 0.5 else ()
            status = outcomes[cid]
            evidence = [{"source": "x", "observed_at": "t"}] if status == "PASS" else []
            runner = (lambda s=status, e=evidence, c=cid, m="01-entity": lambda ctx: CheckResult(c, m, ExecutionStatus(s), evidence=e))()
            specs.append(CheckSpec(cid, "01-entity", runner, deps))
        return specs

    rng_state = rng.getstate()
    specs_a = build_specs()
    rng.setstate(rng_state)  # replay identical randomness for the second build
    specs_b = build_specs()

    result_a = ModuleRunner(specs_a).run()
    result_b = ModuleRunner(specs_b).run()

    statuses_a = {cid: result_a["checks"][cid]["status"] for cid in ids}
    statuses_b = {cid: result_b["checks"][cid]["status"] for cid in ids}
    assert statuses_a == statuses_b, "identical dependency graphs and outcomes must block identically"
