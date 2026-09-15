from __future__ import annotations

import json
from typing import Any

from .integrations.openrouter import OpenRouterClient, OpenRouterConfig, OpenRouterError

# The advisory result is expected to carry these sections (see SYSTEM_PROMPT).
_SECTIONS = (
    ("root_cause_hypotheses", "Root-cause hypotheses"),
    ("priorities", "Priorities"),
    ("recommendations", "Recommendations"),
    ("content_opportunities", "Content opportunities"),
    ("validation_plan", "Validation plan"),
)

SYSTEM_PROMPT = """You are OPE's reasoning layer. Reason only from the deterministic audit evidence supplied by OPE.
Do not invent observations, citations, measurements, rankings, customer facts, or evidence.
Do not turn UNKNOWN into PASS. Do not change deterministic execution statuses.
Treat root-cause statements without direct evidence as hypotheses.
Return JSON with exactly these top-level keys: root_cause_hypotheses, priorities, recommendations, content_opportunities, validation_plan.
Each item must be concise and traceable to supplied finding/check IDs when possible.
"""


def _evidence_context(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": result.get("target"),
        "inventory": result.get("inventory", {}),
        "modules": result.get("modules", {}),
        "findings": result.get("findings", []),
        "deterministic_checks": result.get("checks", {}),
    }


def reason_about_result(result: dict[str, Any], client: OpenRouterClient | None = None) -> dict[str, Any]:
    """Generate optional reasoning from deterministic OPE evidence.

    The returned reasoning is advisory metadata. It does not mutate the audit
    result and must not be used as evidence or as a deterministic PASS/FAIL.
    """
    active_client = client or OpenRouterClient()
    response = active_client.chat_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(_evidence_context(result), ensure_ascii=False, sort_keys=True)},
        ],
        temperature=0.0,
    )
    return {
        "provider": "openrouter",
        "model": active_client.config.model,
        "advisory": True,
        "grounded_in": "deterministic-audit-evidence",
        "result": response,
    }


def _unavailable(reason: str) -> dict[str, Any]:
    """A truthful 'reasoning not produced' record — never a fabricated result."""
    return {
        "provider": "openrouter",
        "advisory": True,
        "available": False,
        "grounded_in": "deterministic-audit-evidence",
        "reason": reason,
        "result": None,
    }


def reasoning_or_unavailable(result: dict[str, Any], client: OpenRouterClient | None = None) -> dict[str, Any]:
    """Produce the advisory reasoning block, or an honest 'unavailable' record.

    This is the surface-facing entry point (CLI, dashboard): it never raises and
    never fabricates. When ``OPENROUTER_API_KEY`` is absent, or the provider
    call fails for any reason, it returns an ``available: False`` record with a
    specific reason instead of a made-up result. On success it returns the
    advisory block with ``available: True``. The reason text never contains the
    credential (OpenRouter errors carry HTTP status/detail, not the key).
    """
    if client is None and OpenRouterConfig.from_env() is None:
        return _unavailable("OPENROUTER_API_KEY is not configured")
    try:
        reasoning = reason_about_result(result, client)
    except OpenRouterError as exc:
        return _unavailable(f"OpenRouter request failed: {exc}")
    except Exception as exc:  # never let an optional advisory layer break an audit
        return _unavailable(f"reasoning unavailable ({type(exc).__name__})")
    reasoning["available"] = True
    return reasoning


def _render_items(items: Any) -> list[str]:
    lines: list[str] = []
    if isinstance(items, list):
        for item in items:
            lines.append(f"- {item if isinstance(item, str) else json.dumps(item, ensure_ascii=False, sort_keys=True)}")
    elif isinstance(items, str):
        if items.strip():
            lines.append(f"- {items}")
    elif items not in (None, {}):
        lines.append(f"- {json.dumps(items, ensure_ascii=False, sort_keys=True)}")
    return lines


def reasoning_markdown(reasoning: dict[str, Any] | None) -> str:
    """Render an advisory-reasoning block (or its unavailable state) as markdown.

    Used by the CLI and markdown report. The output is clearly labelled advisory
    and never presented as deterministic evidence or a PASS/FAIL.
    """
    if not isinstance(reasoning, dict):
        return ""
    lines = ["## AI Reasoning (advisory)", ""]
    if not reasoning.get("available"):
        lines.append(f"_Unavailable — {reasoning.get('reason', 'not configured')}._")
        lines.append("")
        lines.append("This layer is optional; the deterministic findings above are unaffected.")
        return "\n".join(lines)
    lines.append(
        f"_Advisory only (model: {reasoning.get('model', 'unknown')}), grounded in the "
        "deterministic audit evidence. Not a measurement, not a PASS/FAIL, not evidence._"
    )
    body = reasoning.get("result")
    if not isinstance(body, dict):
        lines.append("")
        lines.append("_The provider returned no structured reasoning._")
        return "\n".join(lines)
    for key, title in _SECTIONS:
        rendered = _render_items(body.get(key))
        if rendered:
            lines.append("")
            lines.append(f"### {title}")
            lines.extend(rendered)
    return "\n".join(lines)
