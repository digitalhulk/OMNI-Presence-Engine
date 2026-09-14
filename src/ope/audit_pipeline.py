from __future__ import annotations

import re
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
    "01-entity.identity",
    "06-semantics.entity_markup",
    "12-local.nap_consistency",
    "08-media.image_metadata",
    "08-media.responsive_media",
    "07-content.internal_links",
    "07-content.freshness",
    "18-analytics.measurement_coverage",
    "19-conversion.lead_capture",
    "06-semantics.taxonomy",
    "06-semantics.knowledge_consistency",
    "11-authority.reviews",
    "11-authority.expert_signals",
    "11-authority.consistency",
    "01-entity.identifiers",
    "01-entity.relationships",
    "01-entity.consistency",
    "12-local.local_pages",
    "12-local.hours",
    "12-local.maps_presence",
    "12-local.gbp_presence",
    "12-local.service_area",
    "12-local.reviews",
    "09-search.local_visibility",
    "16-security.tls",
    "16-security.csp",
    "16-security.cookies",
    "16-security.secrets",
    "16-security.waf",
    "02-infrastructure.cdn.configuration",
    "02-infrastructure.server_reachability",
    "14-accessibility.forms",
    "14-accessibility.semantics",
    "14-accessibility.captions",
    "14-accessibility.keyboard",
    "08-media.captions_transcripts",
    "08-media.video_metadata",
    "05-index.status_codes",
    "05-index.duplication",
    "17-language.locale",
    "17-language.unicode",
    "03-code.html.validity",
    "03-code.forms",
    "13-ux.trust_visibility",
    "13-ux.interaction_clarity",
    "19-conversion.cta_clarity",
    "07-content.completeness",
    "06-semantics.topic_coverage",
    "06-semantics.query_intent",
    "03-code.css_cost",
    "03-code.js_cost",
    "03-code.third_party_code",
    "15-performance.network",
    "14-accessibility.reduced_motion",
    "14-accessibility.focus",
)

# Measured subresource budgets, in transferred bytes.
_SUBRESOURCE_BUDGETS = {
    "03-code.css_cost": ("03-code", "css_bytes", 150_000),
    "03-code.js_cost": ("03-code", "js_bytes", 300_000),
}
_THIRD_PARTY_HOST_BUDGET = 5
_REQUEST_COUNT_BUDGET = 50
_PAGE_WEIGHT_BYTES_BUDGET_MEASURED = 1_000_000

# Checks that compare a "how many are broken" count against the population
# they belong to: N/A when the page contains none of that element at all,
# PASS when none are broken, FAIL otherwise.
_DEFECT_COUNT_CHECKS = {
    "14-accessibility.forms": ("14-accessibility", "inputs", "unlabelled_inputs", "The page has no labelable form inputs"),
    "14-accessibility.keyboard": ("14-accessibility", None, "positive_tabindex", ""),
    "08-media.video_metadata": ("08-media", "videos", "videos_missing_metadata", "The page embeds no video elements"),
    "13-ux.interaction_clarity": ("13-ux", "buttons", "buttons_without_text", "The page has no button elements"),
    "03-code.forms": ("03-code", "forms", "forms_missing_action", "The page has no forms"),
}
# Checks that pass when a boolean signal is published on the page.
_BOOLEAN_SIGNAL_CHECKS = {
    "13-ux.trust_visibility": ("13-ux", "has_trust_links"),
    "19-conversion.cta_clarity": ("19-conversion", "has_cta"),
}

# Structured-data checks, split by what absence of the signal actually means.
#
# Presence checks answer "is this signal published at all?", so an absent
# signal is a FAIL (matching the existing structured_data/hreflang bindings).
# Detail checks describe markup that only exists in context — the details of
# a declared entity, or of a declared local business — so when that parent
# markup is absent there is nothing to evaluate and the result is N/A rather
# than a pile-on FAIL for sites the check does not apply to.
_SD_PRESENCE_CHECKS = {
    "06-semantics.taxonomy": ("06-semantics", "has_breadcrumb"),
    "11-authority.reviews": ("11-authority", "has_review"),
    "11-authority.expert_signals": ("11-authority", "has_author"),
    "11-authority.consistency": ("11-authority", "has_social_profiles"),
}
_SD_ENTITY_DETAIL_CHECKS = {
    "01-entity.identifiers": ("01-entity", "has_identifiers"),
    "01-entity.relationships": ("01-entity", "has_relationships"),
    "01-entity.consistency": ("01-entity", "name_matches_title"),
    "06-semantics.knowledge_consistency": ("06-semantics", "description_matches"),
}
_SD_LOCAL_DETAIL_CHECKS = {
    "12-local.local_pages": ("12-local", "has_address"),
    "12-local.hours": ("12-local", "has_opening_hours"),
    "12-local.maps_presence": ("12-local", "has_geo"),
    "12-local.gbp_presence": ("12-local", "has_google_profile"),
    "12-local.service_area": ("12-local", "has_service_area"),
    "12-local.reviews": ("12-local", "has_review"),
    "09-search.local_visibility": ("09-search", "local_visibility_ready"),
}

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
_MODERN_TLS = {"TLSv1.2", "TLSv1.3"}
_CERT_EXPIRY_WARNING_DAYS = 14
_LOCALE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_CONTENT_WORD_BUDGET = 300


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
        measured = inventory.get("page_weight_bytes")
        if isinstance(measured, int):
            result = _check(check_id, "15-performance", measured <= _PAGE_WEIGHT_BYTES_BUDGET_MEASURED, target, {"page_weight_bytes": measured, "html_bytes": inventory.get("bytes"), "css_bytes": inventory.get("css_bytes"), "js_bytes": inventory.get("js_bytes"), "budget_bytes": _PAGE_WEIGHT_BYTES_BUDGET_MEASURED})
            result.reason = "Document plus fetched CSS/JS; images, fonts and media are not counted."
            return result
        doc_bytes = inventory.get("bytes")
        if not isinstance(doc_bytes, int):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason="Response size observation is missing")
        result = _check(check_id, "15-performance", doc_bytes <= _PAGE_WEIGHT_BYTES_BUDGET, target, {"html_bytes": doc_bytes, "budget_bytes": _PAGE_WEIGHT_BYTES_BUDGET})
        result.reason = "Subresources were not fetched, so this measures the main HTML document only."
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

    if check_id in {"01-entity.identity", "06-semantics.entity_markup"}:
        module = check_id.split(".", 1)[0]
        if "has_entity_type" not in inventory:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="JSON-LD entity observation is missing")
        types = list(inventory.get("entity_types") or [])
        return _check(check_id, module, bool(inventory.get("has_entity_type")), target, {"entity_types": types})

    if check_id == "12-local.nap_consistency":
        if "has_nap" not in inventory:
            return CheckResult(check_id, "12-local", ExecutionStatus.UNKNOWN, reason="LocalBusiness JSON-LD observation is missing")
        return _check(check_id, "12-local", bool(inventory.get("has_nap")), target, {"has_nap": inventory.get("has_nap"), "entity_types": list(inventory.get("entity_types") or [])})

    if check_id in {"08-media.image_metadata", "08-media.responsive_media"}:
        if inventory.get("images", 0) == 0:
            return CheckResult(check_id, "08-media", ExecutionStatus.UNKNOWN, reason="Page has no images to evaluate")
        key = "images_missing_dimensions" if check_id == "08-media.image_metadata" else "images_missing_srcset"
        missing = inventory.get(key)
        if not isinstance(missing, int):
            return CheckResult(check_id, "08-media", ExecutionStatus.UNKNOWN, reason=f"'{key}' observation is missing")
        return _check(check_id, "08-media", missing == 0, target, {key: missing, "images": inventory.get("images")})

    if check_id == "07-content.internal_links":
        internal = inventory.get("internal_links")
        if not isinstance(internal, int):
            return CheckResult(check_id, "07-content", ExecutionStatus.UNKNOWN, reason="Link observation is missing")
        return _check(check_id, "07-content", internal > 0, target, {"internal_links": internal})

    if check_id == "07-content.freshness":
        if "last_modified" not in inventory and "article_modified" not in inventory:
            return CheckResult(check_id, "07-content", ExecutionStatus.UNKNOWN, reason="Freshness observation is missing")
        has_freshness_signal = bool(inventory.get("last_modified") or inventory.get("article_modified"))
        return _check(check_id, "07-content", has_freshness_signal, target, {"last_modified": inventory.get("last_modified"), "article_modified": inventory.get("article_modified")})

    if check_id == "18-analytics.measurement_coverage":
        if "has_analytics" not in inventory:
            return CheckResult(check_id, "18-analytics", ExecutionStatus.UNKNOWN, reason="Analytics observation is missing")
        return _check(check_id, "18-analytics", bool(inventory.get("has_analytics")), target, {"has_analytics": inventory.get("has_analytics")})

    if check_id in _SUBRESOURCE_BUDGETS:
        module, key, budget = _SUBRESOURCE_BUDGETS[check_id]
        measured = inventory.get(key)
        if not isinstance(measured, int):
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Subresource measurement is unavailable")
        result = _check(check_id, module, measured <= budget, target, {key: measured, "budget_bytes": budget, "fetched_requests": inventory.get("fetched_requests")})
        result.reason = f"Measured from up to {inventory.get('fetched_requests')} fetched subresources; resources beyond the fetch cap are not counted."
        return result

    if check_id == "03-code.third_party_code":
        hosts = inventory.get("third_party_hosts")
        if hosts is None:
            return CheckResult(check_id, "03-code", ExecutionStatus.UNKNOWN, reason="Subresource measurement is unavailable")
        hosts = list(hosts)
        return _check(check_id, "03-code", len(hosts) <= _THIRD_PARTY_HOST_BUDGET, target, {"third_party_hosts": hosts, "budget": _THIRD_PARTY_HOST_BUDGET})

    if check_id == "15-performance.network":
        discovered = inventory.get("discovered_requests")
        if not isinstance(discovered, int):
            return CheckResult(check_id, "15-performance", ExecutionStatus.UNKNOWN, reason="Request-count observation is unavailable")
        # The document itself is one request on top of what it references.
        total_requests = discovered + 1
        return _check(check_id, "15-performance", total_requests <= _REQUEST_COUNT_BUDGET, target, {"requests": total_requests, "budget": _REQUEST_COUNT_BUDGET})

    if check_id == "14-accessibility.reduced_motion":
        if "has_css" not in inventory:
            return CheckResult(check_id, "14-accessibility", ExecutionStatus.UNKNOWN, reason="Stylesheet evidence is unavailable")
        if not inventory.get("has_css"):
            return CheckResult(check_id, "14-accessibility", ExecutionStatus.UNKNOWN, reason="No stylesheet could be fetched to evaluate motion handling")
        if not inventory.get("has_motion"):
            return CheckResult(check_id, "14-accessibility", ExecutionStatus.NA, reason="The fetched stylesheets declare no animation or transition")
        return _check(check_id, "14-accessibility", bool(inventory.get("respects_reduced_motion")), target, {"has_motion": True, "respects_reduced_motion": inventory.get("respects_reduced_motion")})

    if check_id == "14-accessibility.focus":
        if "has_css" not in inventory:
            return CheckResult(check_id, "14-accessibility", ExecutionStatus.UNKNOWN, reason="Stylesheet evidence is unavailable")
        if not inventory.get("has_css"):
            return CheckResult(check_id, "14-accessibility", ExecutionStatus.UNKNOWN, reason="No stylesheet could be fetched to evaluate focus handling")
        suppressed = bool(inventory.get("suppresses_focus_outline"))
        restored = bool(inventory.get("has_focus_visible"))
        return _check(check_id, "14-accessibility", not suppressed or restored, target, {"suppresses_focus_outline": suppressed, "has_focus_visible": restored})

    if check_id in _DEFECT_COUNT_CHECKS:
        module, population_key, defect_key, empty_reason = _DEFECT_COUNT_CHECKS[check_id]
        defects = inventory.get(defect_key)
        if not isinstance(defects, int):
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason=f"'{defect_key}' observation is missing")
        if population_key is not None:
            population = inventory.get(population_key)
            if not isinstance(population, int):
                return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason=f"'{population_key}' observation is missing")
            if population == 0:
                return CheckResult(check_id, module, ExecutionStatus.NA, reason=empty_reason)
            return _check(check_id, module, defects == 0, target, {defect_key: defects, population_key: population})
        return _check(check_id, module, defects == 0, target, {defect_key: defects})

    if check_id in _BOOLEAN_SIGNAL_CHECKS:
        module, key = _BOOLEAN_SIGNAL_CHECKS[check_id]
        if key not in inventory:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason=f"'{key}' observation is missing")
        return _check(check_id, module, bool(inventory.get(key)), target, {key: inventory.get(key)})

    if check_id == "14-accessibility.semantics":
        landmarks = inventory.get("landmarks")
        if landmarks is None:
            return CheckResult(check_id, "14-accessibility", ExecutionStatus.UNKNOWN, reason="Landmark observation is missing")
        landmarks = list(landmarks)
        return _check(check_id, "14-accessibility", {"header", "main", "footer"}.issubset(landmarks), target, {"landmarks": landmarks})

    if check_id in {"14-accessibility.captions", "08-media.captions_transcripts"}:
        module = check_id.split(".", 1)[0]
        media = inventory.get("media_elements")
        tracks = inventory.get("caption_tracks")
        if not isinstance(media, int) or not isinstance(tracks, int):
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Media observation is missing")
        if media == 0:
            return CheckResult(check_id, module, ExecutionStatus.NA, reason="The page embeds no audio or video elements")
        return _check(check_id, module, tracks >= media, target, {"media_elements": media, "caption_tracks": tracks})

    if check_id == "05-index.status_codes":
        status = inventory.get("status")
        if not isinstance(status, int):
            return CheckResult(check_id, "05-index", ExecutionStatus.UNKNOWN, reason="HTTP status observation is missing")
        return _check(check_id, "05-index", status == 200, target, {"status": status})

    if check_id == "05-index.duplication":
        if "canonical_is_self" not in inventory:
            return CheckResult(check_id, "05-index", ExecutionStatus.UNKNOWN, reason="Canonical observation is missing")
        canonical_is_self = inventory.get("canonical_is_self")
        if canonical_is_self is None:
            return CheckResult(check_id, "05-index", ExecutionStatus.NA, reason="The page declares no canonical URL to compare against")
        return _check(check_id, "05-index", bool(canonical_is_self), target, {"canonical": inventory.get("canonical"), "canonical_is_self": canonical_is_self})

    if check_id == "17-language.locale":
        if "lang" not in inventory:
            return CheckResult(check_id, "17-language", ExecutionStatus.UNKNOWN, reason="Language observation is missing")
        lang = str(inventory.get("lang") or "").strip()
        if not lang:
            return CheckResult(check_id, "17-language", ExecutionStatus.NA, reason="No language is declared, so there is no locale tag to validate")
        return _check(check_id, "17-language", bool(_LOCALE_PATTERN.match(lang)), target, {"lang": lang})

    if check_id == "17-language.unicode":
        if "declared_charset" not in inventory:
            return CheckResult(check_id, "17-language", ExecutionStatus.UNKNOWN, reason="Charset observation is missing")
        charset = str(inventory.get("declared_charset") or "").lower()
        return _check(check_id, "17-language", charset.replace("-", "") == "utf8", target, {"declared_charset": charset})

    if check_id == "03-code.html.validity":
        if "structure" not in inventory or "doctype" not in inventory:
            return CheckResult(check_id, "03-code", ExecutionStatus.UNKNOWN, reason="Document structure observation is missing")
        structure = set(inventory.get("structure") or [])
        doctype = str(inventory.get("doctype") or "").lower()
        title_count = inventory.get("title_count", 0)
        defects = []
        if not doctype.startswith("doctype html"): defects.append("missing or non-HTML5 doctype")
        for element in ("html", "head", "body"):
            if element not in structure: defects.append(f"missing <{element}>")
        if title_count != 1: defects.append(f"expected exactly one <title>, found {title_count}")
        return _check(check_id, "03-code", not defects, target, {"defects": defects})

    if check_id == "07-content.completeness":
        word_count = inventory.get("word_count")
        if not isinstance(word_count, int):
            return CheckResult(check_id, "07-content", ExecutionStatus.UNKNOWN, reason="Content word-count observation is missing")
        return _check(check_id, "07-content", word_count >= _CONTENT_WORD_BUDGET, target, {"word_count": word_count, "budget": _CONTENT_WORD_BUDGET})

    if check_id == "06-semantics.topic_coverage":
        h1 = inventory.get("h1")
        subheadings = inventory.get("subheadings")
        if not isinstance(h1, int) or not isinstance(subheadings, int):
            return CheckResult(check_id, "06-semantics", ExecutionStatus.UNKNOWN, reason="Heading observation is missing")
        return _check(check_id, "06-semantics", h1 >= 1 and subheadings >= 2, target, {"h1": h1, "subheadings": subheadings})

    if check_id == "06-semantics.query_intent":
        question_headings = inventory.get("question_headings")
        if not isinstance(question_headings, int):
            return CheckResult(check_id, "06-semantics", ExecutionStatus.UNKNOWN, reason="Heading-text observation is missing")
        return _check(check_id, "06-semantics", question_headings > 0, target, {"question_headings": question_headings})

    if check_id == "16-security.tls":
        tls = inventory.get("tls")
        if not isinstance(tls, dict):
            return CheckResult(check_id, "16-security", ExecutionStatus.UNKNOWN, reason="TLS observation is missing")
        if tls.get("error") or not tls.get("protocol"):
            return CheckResult(check_id, "16-security", ExecutionStatus.UNKNOWN, reason=f"TLS handshake evidence is unavailable: {tls.get('error') or 'no protocol reported'}")
        days = tls.get("days_until_expiry")
        modern = str(tls.get("protocol")) in _MODERN_TLS
        healthy_certificate = days is None or days > _CERT_EXPIRY_WARNING_DAYS
        return _check(check_id, "16-security", modern and healthy_certificate, target, {"protocol": tls.get("protocol"), "cipher": tls.get("cipher"), "days_until_expiry": days})

    if check_id == "16-security.csp":
        profile = inventory.get("csp_profile")
        if not isinstance(profile, dict):
            return CheckResult(check_id, "16-security", ExecutionStatus.UNKNOWN, reason="Content-Security-Policy observation is missing")
        unsafe = list(profile.get("unsafe_directives", []))
        return _check(check_id, "16-security", bool(profile.get("present")) and not unsafe, target, {"present": profile.get("present"), "unsafe_directives": unsafe})

    if check_id == "16-security.cookies":
        profile = inventory.get("cookies")
        if not isinstance(profile, dict):
            return CheckResult(check_id, "16-security", ExecutionStatus.UNKNOWN, reason="Cookie observation is missing")
        if not profile.get("cookie_count"):
            return CheckResult(check_id, "16-security", ExecutionStatus.NA, reason="The response sets no cookies")
        insecure = list(profile.get("insecure_cookies", []))
        return _check(check_id, "16-security", not insecure, target, {"cookie_count": profile.get("cookie_count"), "insecure_cookies": insecure})

    if check_id == "16-security.secrets":
        exposed = inventory.get("exposed_secrets")
        if exposed is None:
            return CheckResult(check_id, "16-security", ExecutionStatus.UNKNOWN, reason="Secret-scan observation is missing")
        exposed = list(exposed)
        return _check(check_id, "16-security", not exposed, target, {"exposed_secret_types": exposed})

    if check_id in {"16-security.waf", "02-infrastructure.cdn.configuration"}:
        # Edge platforms are detected from response headers. Their absence
        # does not prove a site has none (many strip identifying headers),
        # so an undetected edge stays UNKNOWN rather than becoming a FAIL.
        module, key, label = ("16-security", "waf_markers", "WAF") if check_id == "16-security.waf" else ("02-infrastructure", "cdn_markers", "CDN")
        markers = inventory.get(key)
        if markers is None:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason=f"{label} observation is missing")
        markers = list(markers)
        if not markers:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason=f"No {label} signature was advertised in response headers; absence does not prove none is deployed")
        return _check(check_id, module, True, target, {f"{label.lower()}_markers": markers})

    if check_id == "02-infrastructure.server_reachability":
        status = inventory.get("status")
        if not isinstance(status, int):
            return CheckResult(check_id, "02-infrastructure", ExecutionStatus.UNKNOWN, reason="No response was observed from the origin")
        return _check(check_id, "02-infrastructure", True, target, {"status": status, "ttfb_ms": inventory.get("ttfb_ms")})

    if check_id in _SD_PRESENCE_CHECKS:
        module, key = _SD_PRESENCE_CHECKS[check_id]
        if key not in inventory:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Structured-data observation is missing")
        return _check(check_id, module, bool(inventory.get(key)), target, {key: inventory.get(key)})

    if check_id in _SD_ENTITY_DETAIL_CHECKS or check_id in _SD_LOCAL_DETAIL_CHECKS:
        entity_detail = check_id in _SD_ENTITY_DETAIL_CHECKS
        module, key = (_SD_ENTITY_DETAIL_CHECKS if entity_detail else _SD_LOCAL_DETAIL_CHECKS)[check_id]
        parent_key = "has_entity_type" if entity_detail else "is_local_business"
        if parent_key not in inventory or key not in inventory:
            return CheckResult(check_id, module, ExecutionStatus.UNKNOWN, reason="Structured-data observation is missing")
        if not inventory.get(parent_key):
            reason = "No entity markup is published, so this detail has nothing to evaluate" if entity_detail else "The page declares no local business, so local detail checks do not apply"
            return CheckResult(check_id, module, ExecutionStatus.NA, reason=reason)
        value = inventory.get(key)
        if value is None:
            return CheckResult(check_id, module, ExecutionStatus.NA, reason="The markup publishes no comparable value for this check")
        return _check(check_id, module, bool(value), target, {key: value})

    if check_id == "19-conversion.lead_capture":
        if inventory.get("forms", 0) == 0:
            return CheckResult(check_id, "19-conversion", ExecutionStatus.UNKNOWN, reason="Page has no forms to evaluate")
        if "contact_input" not in inventory:
            return CheckResult(check_id, "19-conversion", ExecutionStatus.UNKNOWN, reason="Contact-field observation is missing")
        return _check(check_id, "19-conversion", bool(inventory.get("contact_input")), target, {"contact_input": inventory.get("contact_input"), "forms": inventory.get("forms")})

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
