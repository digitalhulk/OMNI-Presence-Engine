from __future__ import annotations

from typing import Any

from .integrations.openrouter import OpenRouterClient


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
            {"role": "user", "content": __import__("json").dumps(_evidence_context(result), ensure_ascii=False, sort_keys=True)},
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
