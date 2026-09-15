from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .module_runner import CheckResult, CheckRunner, CheckSpec, ExecutionStatus, ModuleRunner


@dataclass(frozen=True)
class RegisteredCheck:
    """Canonical executable check metadata."""

    id: str
    module: str
    check_name: str
    depends_on: tuple[str, ...] = ()


# The YAML module registry documents module evidence requirements and
# illustrative weights; scoring does not consume those weights (see
# schemas/scoring-v1.md — evidence-weighted coverage + graph topology).
# Executable IDs are namespaced by module so repeated check names (for example
# forms, reviews, captions, dns, and consistency) cannot collide globally.
_CHECK_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("01-entity", "identity ownership identifiers relationships consistency"),
    ("02-infrastructure", "dns.resolution tls.valid hosting.availability cdn.configuration server_reachability"),
    ("03-code", "html.validity semantic_html head_metadata structured_data css_cost js_cost third_party_code forms"),
    ("04-crawl", "robots_access sitemap_discovery bot_access crawl_errors crawl_budget_risk"),
    ("05-index", "indexability canonicalization status_codes duplication rendering_indexability"),
    ("06-semantics", "entity_markup topic_coverage query_intent relationships taxonomy knowledge_consistency"),
    ("07-content", "intent_match completeness originality factual_accuracy helpfulness freshness internal_links conversion_context"),
    ("08-media", "image_quality image_metadata responsive_media video_metadata captions_transcripts media_performance"),
    ("09-search", "query_visibility serp_eligibility snippets sitelinks image_visibility local_visibility"),
    ("10-ai-search", "ai_retrievability answer_eligibility citation_presence source_grounding agent_accessibility factual_consistency"),
    ("11-authority", "brand_mentions backlinks citations reviews expert_signals reputation consistency"),
    ("12-local", "gbp_presence maps_presence nap_consistency service_area hours local_pages reviews"),
    ("13-ux", "navigation hierarchy mobile_usability interaction_clarity booking_friction trust_visibility"),
    ("14-accessibility", "keyboard focus contrast semantics alt_text forms captions reduced_motion"),
    ("15-performance", "dns ttfb fcp lcp inp cls tbt network render_cost frame_cost page_weight"),
    ("16-security", "https tls security_headers csp cookies auth dependencies secrets waf abuse_controls"),
    ("17-language", "language_declaration locale translation_quality hreflang unicode regional_intent transliteration"),
    ("18-analytics", "measurement_coverage event_quality attribution search_data server_logs crm_linkage ai_referrals"),
    ("19-conversion", "cta_clarity lead_capture booking_completion trust_to_action funnel_dropoff revenue_tracking"),
    ("20-continuous-optimization", "monitoring anomaly_detection root_cause prioritization validation regression_guards update_pipeline"),
)


CHECKS: tuple[RegisteredCheck, ...] = tuple(
    RegisteredCheck(
        id=f"{module}.{name}",
        module=module,
        check_name=name,
    )
    for module, names in _CHECK_DEFINITIONS
    for name in names.split()
)


def _unknown_runner(check: RegisteredCheck) -> CheckRunner:
    def run(_: dict[str, Any]) -> CheckResult:
        return CheckResult(
            check_id=check.id,
            module=check.module,
            status=ExecutionStatus.UNKNOWN,
            reason="No evidence provider is bound for this check.",
        )

    return run


def build_runner(bindings: dict[str, Any] | None = None) -> ModuleRunner:
    """Build the complete executable registry.

    Unbound checks deliberately return UNKNOWN. This prevents missing providers
    from being interpreted as successful checks.
    """
    bindings = bindings or {}
    specs = []
    for check in CHECKS:
        runner = bindings.get(check.id) or _unknown_runner(check)
        specs.append(CheckSpec(check.id, check.module, runner, check.depends_on))
    return ModuleRunner(specs)


def registered_check_ids() -> tuple[str, ...]:
    return tuple(check.id for check in CHECKS)


def checks_for_module(module: str) -> tuple[str, ...]:
    return tuple(check.id for check in CHECKS if check.module == module)
