"""End-to-end integration tests: audit.py's real output through the full
audit_pipeline.py / engine.py normalization chain.

This file exists to close a confirmed gap: every other test in this suite
either unit-tests a single module in isolation, or hand-constructs a
finding/inventory dict that *mimics* audit.py's shape. Until this file,
nothing actually ran audit()'s real return value through normalize_result()
or execute_audit_checks() -- so a mismatch between what audit.py truly
produces and what downstream code expects could exist even with 86/86
tests passing. HTTP is mocked at the ope.audit._request boundary (the same
boundary audit() itself calls through), so these tests exercise every real
code path in audit() -- HTML parsing, finding construction, module status
seeding -- without needing network access.
"""

from unittest.mock import patch

from ope.audit import audit
from ope.audit_pipeline import execute_audit_checks
from ope.engine import normalize_result


GOOD_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
<title>Example Page</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://example.com/">
<script type="application/ld+json">{"@type": "Organization", "name": "Example"}</script>
</head>
<body><img src="a.jpg" alt="a description"></body>
</html>"""

BAD_HTML = b"<html><body>no head metadata at all</body></html>"

GOOD_HEADERS = {
    "Content-Type": "text/html",
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=63072000",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def _mock_response(final_url="https://example.com/", status=200, headers=None, body=GOOD_HTML):
    def fake_request(url, timeout=15):
        return (final_url, status, headers or {}, body, "utf-8")
    return fake_request


def test_clean_page_produces_no_findings_and_survives_normalization():
    with patch("ope.audit._request", side_effect=_mock_response(headers=GOOD_HEADERS)):
        raw = audit("https://example.com")
    assert raw["findings"] == []

    out = normalize_result(raw)
    assert out["findings"] == []
    assert out["engine_contract"] == "evidence-diagnostic-v1"
    # No field loss on a clean run: inventory must survive unchanged.
    assert out["inventory"] == raw["inventory"]


def test_missing_security_headers_survive_normalization_without_loss():
    with patch("ope.audit._request", side_effect=_mock_response(headers={})):
        raw = audit("https://example.com")

    raw_ids = {f["id"] for f in raw["findings"]}
    assert raw_ids == {
        "16-SEC-CONTENT-SECURITY-POLICY",
        "16-SEC-STRICT-TRANSPORT-SECURITY",
        "16-SEC-X-CONTENT-TYPE-OPTIONS",
        "16-SEC-REFERRER-POLICY",
    }

    out = normalize_result(raw)
    out_ids = {f["id"] for f in out["findings"]}
    # No finding loss or gain through normalization.
    assert out_ids == raw_ids
    assert out["modules"]["16"]["status"] == "FAIL"

    for finding in out["findings"]:
        # audit.py never populates root_cause on any finding -- it only
        # observes symptoms, it does not diagnose root cause. Every one of
        # its findings must therefore be honestly demoted to HYPOTHESIS
        # rather than presented as OBSERVED fact, and execution_status
        # (the deterministic FAIL) must be preserved distinctly from
        # evidence_status (the HYPOTHESIS demotion) -- these are two
        # different axes and neither may erase the other.
        assert finding["status"] == "HYPOTHESIS"
        assert finding["execution_status"] == "FAIL"
        # Priority must survive at audit.py's real 0-100 scale, not be
        # collapsed to [0,1] (the Cluster B regression).
        assert 0.0 <= finding["priority"] <= 100.0
        assert finding["priority"] > 1.0  # these are real audit.py priorities, not the buggy collapsed value


def test_http_error_and_missing_title_both_surface_with_correct_finding_ids():
    with patch("ope.audit._request", side_effect=_mock_response(status=500, body=BAD_HTML)):
        raw = audit("https://example.com")

    raw_ids = {f["id"] for f in raw["findings"]}
    # HTTP 500 and missing title are independent, unrelated conditions --
    # this is the exact real-world case the Cluster B finding-ID
    # cross-wiring bug would have gotten wrong (head_metadata previously
    # kept checking for CODE-HTTP-001 instead of 03-CODE-META-001).
    assert "CODE-HTTP-001" in raw_ids
    assert "03-CODE-META-001" in raw_ids

    checks = execute_audit_checks(raw)["checks"]
    assert checks["02-infrastructure.hosting.availability"]["status"] == "FAIL"
    assert checks["03-code.head_metadata"]["status"] == "FAIL"


def test_good_title_is_not_cross_wired_to_unrelated_http_error():
    # The precise real-world reproduction of the Cluster B cross-wiring bug:
    # a genuinely fine title must not FAIL merely because the HTTP status
    # was also bad in the same audit run.
    good_title_bad_status_html = b"<html><head><title>A Perfectly Fine Title</title></head><body></body></html>"
    with patch("ope.audit._request", side_effect=_mock_response(status=500, body=good_title_bad_status_html)):
        raw = audit("https://example.com")

    assert "CODE-HTTP-001" in {f["id"] for f in raw["findings"]}
    assert "03-CODE-META-001" not in {f["id"] for f in raw["findings"]}

    checks = execute_audit_checks(raw)["checks"]
    assert checks["02-infrastructure.hosting.availability"]["status"] == "FAIL"
    assert checks["03-code.head_metadata"]["status"] == "PASS"


def test_registry_bound_checks_pass_with_real_schema_compliant_evidence():
    with patch("ope.audit._request", side_effect=_mock_response(headers=GOOD_HEADERS)):
        raw = audit("https://example.com")

    checks = execute_audit_checks(raw)["checks"]
    for check_id in (
        "02-infrastructure.hosting.availability",
        "03-code.head_metadata",
        "05-index.canonicalization",
        "06-semantics.structured_data",
        "13-ux.mobile_usability",
        "14-accessibility.alt_text",
        "17-language.language_declaration",
    ):
        result = checks[check_id]
        assert result["status"] == "PASS"
        # Every piece of evidence attached to a real PASS must be
        # schema-compliant (source + observed_at), matching the
        # module_runner.py _has_valid_evidence gate.
        assert result["evidence"]
        for entry in result["evidence"]:
            assert entry.get("source")
            assert entry.get("observed_at")


def test_normalize_result_is_idempotent_on_real_audit_output():
    with patch("ope.audit._request", side_effect=_mock_response(status=500, body=BAD_HTML)):
        raw = audit("https://example.com")

    once = normalize_result(raw)
    twice = normalize_result(once)
    assert once == twice


def test_normalize_result_does_not_mutate_real_audit_output():
    with patch("ope.audit._request", side_effect=_mock_response(status=500, body=BAD_HTML)):
        raw = audit("https://example.com")

    import copy
    snapshot = copy.deepcopy(raw)
    normalize_result(raw)
    assert raw == snapshot


def test_finding_and_check_ordering_is_deterministic_across_separate_runs():
    with patch("ope.audit._request", side_effect=_mock_response(status=500, body=BAD_HTML)):
        raw_a = audit("https://example.com")
        raw_b = audit("https://example.com")

    out_a = normalize_result(raw_a)
    out_b = normalize_result(raw_b)
    assert [f["id"] for f in out_a["findings"]] == [f["id"] for f in out_b["findings"]]

    checks_a = list(execute_audit_checks(raw_a)["checks"].keys())
    checks_b = list(execute_audit_checks(raw_b)["checks"].keys())
    assert checks_a == checks_b
    assert checks_a == sorted(checks_a)
