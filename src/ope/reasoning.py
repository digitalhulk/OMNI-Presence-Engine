from __future__ import annotations

import json
from typing import Any

from .integrations.openrouter import OpenRouterClient


SYSTEM_PROMPT = """You are OPE's reasoning layer. Reason only from the deterministic audit evidence supplied by OPE.
Do not invent observations, citations, measurements, rankings, customer facts, or evidence.
Do not turn UNKNOWN into PASS. Do not change deterministic execution statuses.
Treat root-cause statements without direct evidence as hypotheses.
Return JSON with exactly these top-level keys: root_cause_hypotheses, priorities, recommendations, content_opportunities, validation_plan.
Each item must be concise and traceable to supplied finding/check IDs when possible.
"""

REQUIRED_RESULT_KEYS = (
    "root_cause_hypotheses",
    "priorities",
    "recommendations",
    "content_opportunities",
    "validation_plan",
)


class ReasoningContractError(RuntimeError):
    """Raised when an LLM response does not match the advisory contract.

    Distinct from OpenRouterError (transport/provider failure): this signals
    a response was received but its shape cannot be trusted, so it must not
    be passed downstream as if it were validated structured advisory data.
    """


def _evidence_context(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": result.get("target"),
        "inventory": result.get("inventory", {}),
        "modules": result.get("modules", {}),
        "findings": result.get("findings", []),
        "deterministic_checks": result.get("checks", {}),
    }


def _validate_response_shape(response: Any) -> dict[str, list[Any]]:
    """Enforce the advisory response contract before it leaves this module.

    The LLM cannot be trusted to reliably emit exactly the requested shape.
    Rather than forward arbitrary/malformed JSON downstream as if it were
    structured advisory data, this normalizes strictly: every required key
    must be present and must be a list. Missing or non-list keys become an
    empty list rather than being fabricated or coerced from unrelated data,
    and unrecognized top-level keys are dropped so stray model output cannot
    masquerade as a recognized field.
    """
    if not isinstance(response, dict):
        raise ReasoningContractError(
            f"OpenRouter response must be a JSON object, got {type(response).__name__}"
        )
    normalized: dict[str, list[Any]] = {}
    for key in REQUIRED_RESULT_KEYS:
        value = response.get(key)
        normalized[key] = value if isinstance(value, list) else []
    return normalized


def reason_about_result(result: dict[str, Any], client: OpenRouterClient | None = None) -> dict[str, Any]:
    """Generate optional reasoning from deterministic OPE evidence.

    The returned reasoning is advisory metadata. It does not mutate the audit
    result and must not be used as evidence or as a deterministic PASS/FAIL.

    Raises OpenRouterError on transport/provider failure (bad key, timeout,
    non-2xx, unparsable envelope) and ReasoningContractError when a response
    was received but does not match the required advisory shape. Callers
    should treat both as "reasoning unavailable" and keep the deterministic
    result authoritative rather than blocking the audit on either.
    """
    active_client = client or OpenRouterClient()
    response = active_client.chat_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(_evidence_context(result), ensure_ascii=False, sort_keys=True)},
        ],
        temperature=0.0,
    )
    validated = _validate_response_shape(response)
    return {
        "provider": "openrouter",
        "model": active_client.config.model,
        "advisory": True,
        "grounded_in": "deterministic-audit-evidence",
        "result": validated,
    }
