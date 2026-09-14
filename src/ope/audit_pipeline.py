from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .module_runner import CheckResult, ExecutionStatus
from .registry import build_runner, registered_check_ids


AUDIT_BINDINGS = (
    "02-infrastructure.hosting.availability",
    "03-code.head_metadata",
    "05-index.canonicalization",
    "03-code.structured_data",
    "13-ux.mobile_usability",
    "14-accessibility.alt_text",
    "17-language.language_declaration",
    "04-crawl.robots_access",
    "04-crawl.bot_access",
    "10-ai-search.agent_accessibility",
    "04-crawl.sitemap_discovery",
    "02-infrastructure.tls.valid",
    "16-security.https",
    "16-security.security_headers",
    "05-index.indexability",
    "13-ux.hierarchy",
    "13-ux.navigation",
    "03-code.semantic_html",
    "17-language.hreflang",
    "09-search.snippets",
    "02-infrastructure.dns.resolution",
    "15-performance.dns",
    "15-performance.ttfb",
    "15-performance.page_weight",
    "15-performance.lcp",
    "15-performance.fcp",
    "15-performance.cls",
    "15-performance.tbt",
    "15-performance.inp",
    "10-ai-search.answer_eligibility",
    "10-ai-search.citation_presence",
)

# Deterministic performance/citability thresholds. These are widely cited
# industry budgets (Core Web Vitals "good" thresholds; DNS/TTFB latency
# guidance), not fabricated data — the underlying measurements are real.
_DNS_MS_BUDGET = 100.0
_TTFB_MS_BUDGET = 800.0
_PAGE_WEIGHT_BYTES_BUDGET = 100_000
_PSI_VITALS = {
    "15-performance.lcp": ("lcp_ms", 2500.0),
    "15-performance.fcp": ("fcp_ms", 1800.0),
    "15-performance.cls": ("cls", 0.1),
    "15-performance.tbt": ("tbt_ms", 200.0),
    "15-performance.inp": ("inp_ms", 200.0),
}
_CITABILITY_SCORE_BUDGET = 50.0


def _evidence(target: str, value: Any, source: str = "ope-audit") -> list[dict[str, Any]]:
    return [{"source": source, "target": target, "value": value, "confidence": 1.0, "provenance": "direct", "observed_at": datetime.now(timezone.utc).isoformat()}]


def _check(check_id: str, module: str, passed: bool, target: str, value: Any, source: str = "ope-audit") -> CheckResult:
    return CheckResult(
        check_id=check_id,
        module=module,
        status=ExecutionStatus.PASS if passed else ExecutionStatus.FAIL,
        evidence=_evidence(target, value, source),
        reason="Direct audit observation",
    )


def _bound(check_id: str, audit_result: dict[str, Any]) -> CheckResult:
    inventory = audit_result.get("inventory", {})
    target = str(audit_result.get("final_url") or audit_result.get("target") or "")
    finding_ids = {str(item.get("id")) for item in audit_result.get("findings", []) if isinstance(item, dict)}

    if check_id == "02-infrastructure.hosting.availability":
        status = inventory.get("status")
        if not isinstance(status, int):
            return CheckResult(check_id, "02-infrastructure", ExecutionStatus.UNKNOWN, reason="HTTP status observation is missing or invalid")
        return _check(check_id, "02-infrastructure", status < 400, target, {"status": status})

    if check_id in {"04-crawl.robots_access", "04-crawl.bot_access", "10-ai-search.agent_accessibility", "04-crawl.sitemap_discovery"}:
        robots = inventory.get("robots")
        if not isinstance(robots, dict):
            return CheckResult(check_id, check_id.split(".", 1)[0], ExecutionStatus.UNKNOWN, reason="robots.txt observation is missing")
        if robots.get("error"):
            return CheckResult(check_id, check_id.split(".", 1)[0], ExecutionStatus.UNKNOWN, reason="robots.txt observation is unavailable")
        if check_id == "04-crawl.sitemap_discovery":
            sitemaps = list(robots.get("sitemaps", []))
            return _check(check_id, "04-crawl", bool(sitemaps), target, {"sitemaps": sitemaps})
        if not isinstance(robots.get("ai_crawlers"), dict):
            return CheckResult(check_id, check_id.split(".", 1)[0], ExecutionStatus.UNKNOWN, reason="robots.txt observation is unavailable")
        blocked = list(robots.get("blocked_ai_crawlers", []))
        if check_id == "04-crawl.robots_access":
            return _check(check_id, "04-crawl", True, target, {"robots_status": robots.get("status"), "rule_count": robots.get("rule_count")})
        if check_id == "04-crawl.bot_access":
            return _check(check_id, "04-crawl", not blocked, target, {"blocked_ai_crawlers": blocked, "ai_crawlers": robots["ai_crawlers"]})
        return _check(check_id, "10-ai-search", not blocked, target, {"blocked_ai_crawlers": blocked, "ai_crawlers": robots["ai_crawlers"]})

    if check_id in {"02-infrastructure.tls.valid", "16-security.https"}:
        module = check_id.split(".", 1)[0]
        if not target:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Target URL observation is missing")
        is_https = target.startswith("https://")
        return _check(check_id, module, is_https, target, {"scheme": "https" if is_https else "http"})

    if check_id == "16-security.security_headers":
        required = ("hsts", "csp", "x_content_type_options", "referrer_policy_header")
        if not all(key in inventory for key in required):
            return CheckResult(check_id, "16-security", ExecutionStatus.UNKNOWN, reason="Security header observation is missing")
        present = {key: bool(inventory.get(key)) for key in required}
        return _check(check_id, "16-security", all(present.values()), target, present)

    if check_id == "05-index.indexability":
        if "meta_robots" not in inventory and "x_robots_tag" not in inventory:
            return CheckResult(check_id, "05-index", ExecutionStatus.UNKNOWN, reason="Indexability observation is missing")
        meta_robots = str(inventory.get("meta_robots") or "").lower()
        x_robots_tag = str(inventory.get("x_robots_tag") or "").lower()
        noindex = "noindex" in meta_robots or "noindex" in x_robots_tag
        return _check(check_id, "05-index", not noindex, target, {"meta_robots": meta_robots, "x_robots_tag": x_robots_tag})

    if check_id == "13-ux.hierarchy":
        h1 = inventory.get("h1")
        if not isinstance(h1, int):
            return CheckResult(check_id, "13-ux", ExecutionStatus.UNKNOWN, reason="Heading observation is missing or invalid")
        return _check(check_id, "13-ux", h1 == 1, target, {"h1": h1})

    if check_id in {"13-ux.navigation", "03-code.semantic_html"}:
        module = check_id.split(".", 1)[0]
        landmarks = inventory.get("landmarks")
        if landmarks is None:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Landmark observation is missing")
        landmarks = list(landmarks)
        if check_id == "13-ux.navigation":
            return _check(check_id, module, "nav" in landmarks, target, {"landmarks": landmarks})
        return _check(check_id, module, {"header", "main", "footer"}.issubset(landmarks), target, {"landmarks": landmarks})

    if check_id == "17-language.hreflang":
        count = inventory.get("hreflang_count")
        if not isinstance(count, int):
            return CheckResult(check_id, "17-language", ExecutionStatus.UNKNOWN, reason="Hreflang observation is missing or invalid")
        return _check(check_id, "17-language", count > 0, target, {"hreflang_count": count})

    if check_id == "09-search.snippets":
        if "description" not in inventory:
            return CheckResult(check_id, "09-search", ExecutionStatus.UNKNOWN, reason="Meta description observation is missing")
        length = len(str(inventory.get("description") or "").strip())
        return _check(check_id, "09-search", 50 <= length <= 160, target, {"description_length": length})

    if check_id == "02-infrastructure.dns.resolution":
        dns_ms = inventory.get("dns_ms")
        if not isinstance(dns_ms, (int, float)):
            return CheckResult(check_id, "02-infrastructure", ExecutionStatus.UNKNOWN, reason="DNS timing observation is missing")
        return _check(check_id, "02-infrastructure", True, target, {"dns_ms": dns_ms})

    if check_id == "15-performance.dns":
        dns_ms = inventory.get("dns_ms")
        if not isinstance(dns_ms, (int, float)):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason="DNS timing observation is missing")
        return _check(check_id, "15-performance", dns_ms <= _DNS_MS_BUDGET, target, {"dns_ms": dns_ms, "budget_ms": _DNS_MS_BUDGET})

    if check_id == "15-performance.ttfb":
        ttfb_ms = inventory.get("ttfb_ms")
        if not isinstance(ttfb_ms, (int, float)):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason="TTFB timing observation is missing")
        return _check(check_id, "15-performance", ttfb_ms <= _TTFB_MS_BUDGET, target, {"ttfb_ms": ttfb_ms, "budget_ms": _TTFB_MS_BUDGET})

    if check_id == "15-performance.page_weight":
        doc_bytes = inventory.get("bytes")
        if not isinstance(doc_bytes, int):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason="Response size observation is missing")
        result = _check(check_id, "15-performance", doc_bytes <= _PAGE_WEIGHT_BYTES_BUDGET, target, {"html_bytes": doc_bytes, "budget_bytes": _PAGE_WEIGHT_BYTES_BUDGET})
        result.reason = "Measures the main HTML document only; excludes images, CSS, and JavaScript payload."
        return result

    if check_id in _PSI_VITALS:
        vitals = inventory.get("pagespeed")
        if not isinstance(vitals, dict):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason="PageSpeed Insights evidence is not configured or unavailable")
        key, budget = _PSI_VITALS[check_id]
        value = vitals.get(key)
        if not isinstance(value, (int, float)):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason=f"PageSpeed Insights did not report '{key}'")
        return _check(check_id, "15-performance", value <= budget, target, {key: value, "budget": budget}, source="pagespeed-insights")

    if check_id in {"10-ai-search.answer_eligibility", "10-ai-search.citation_presence"}:
        report = inventory.get("citability")
        if not isinstance(report, dict) or not report.get("total_blocks_analyzed"):
            return CheckResult(check_id, "10-ai-search", ExecutionStatus.UNKNOWN, reason="Citability observation is missing or has no analyzable content blocks")
        if check_id == "10-ai-search.answer_eligibility":
            score = report.get("average_citability_score")
            if not isinstance(score, (int, float)):
                return CheckResult(check_id, "10-ai-search", ExecutionStatus.UNKNOWN, reason="Citability score is missing")
            return _check(check_id, "10-ai-search", score >= _CITABILITY_SCORE_BUDGET, target, {"average_citability_score": score})
        distribution = report.get("grade_distribution") or {}
        strong = int(distribution.get("A", 0)) + int(distribution.get("B", 0))
        return _check(check_id, "10-ai-search", strong > 0, target, {"grade_distribution": distribution})

    rules = {
        "03-code.head_metadata": ("03-code", "CODE-HTTP-001", "title"),
        "05-index.canonicalization": ("05-index", "05-INDEX-CAN-001", "canonical"),
        "03-code.structured_data": ("03-code", "06-SEM-JSONLD-001", "json_ld_blocks"),
        "13-ux.mobile_usability": ("13-ux", "13-UX-MOBILE-001", "viewport"),
        "14-accessibility.alt_text": ("14-accessibility", "14-A11Y-IMG-001", "images_missing_alt"),
        "17-language.language_declaration": ("17-language", "17-LANG-001", "lang"),
    }
    module, finding_id, field = rules[check_id]
    if field not in inventory:
        return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason=f"Audit observation '{field}' is missing")
    value = inventory.get(field)
    failed = finding_id in finding_ids
    if field == "images_missing_alt":
        if not isinstance(value, int):
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Alt-text image count is missing or invalid")
        failed = failed or value > 0
    else:
        failed = failed or not bool(value)
    return _check(check_id, module, not failed, target, {field: value})


def execute_audit_checks(audit_result: dict[str, Any]) -> dict[str, Any]:
    """Execute registry checks that have direct audit evidence bindings."""
    bindings = {
        check_id: (lambda _context, cid=check_id: _bound(cid, audit_result))
        for check_id in AUDIT_BINDINGS
        if check_id in registered_check_ids()
    }
    return build_runner(bindings).run({"audit": audit_result})
