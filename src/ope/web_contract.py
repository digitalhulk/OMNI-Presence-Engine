"""Deployment-runtime and web API contract for OPE front-ends.

OPE's brain is the canonical Python engine (``audit()`` -> ``normalize_result()``
-> dependency cascade -> scoring -> planner). Some deployment targets cannot
execute Python at all — notably PHP/Apache shared hosting. This module declares,
in one place, how a front-end reports *which runtime it is on* and *whether a
live audit can actually execute there*, so a Python-less deployment degrades
honestly instead of fabricating a result.

It is a **contract only**: it performs no audit, computes no score, and holds no
diagnostic logic. ``success_payload()`` embeds the canonical normalized result
verbatim under ``result`` — it never reshapes or re-derives it, so there is no
competing result format.

The PHP shell in ``deploy/hostinger/`` is *generated* from these values
(``scripts/build_hostinger.py`` writes ``api/contract.php``), which is why the
literals live here and not in hand-written PHP: the two cannot drift.
"""
from __future__ import annotations

from typing import Any

from . import __version__

#: Stable identifier for this envelope shape (not the engine result contract).
WEB_CONTRACT_VERSION = "ope-web-v1"

#: Runtime that CAN execute the canonical Python engine.
RUNTIME_PYTHON = "python"
#: PHP/Apache shared hosting: static + PHP only, no Python execution.
RUNTIME_HOSTINGER_SHARED = "hostinger_shared"

#: The engine is always Python — a front-end never becomes the engine.
ENGINE = "python"

STATUS_SUCCESS = "success"
STATUS_RUNTIME_UNAVAILABLE = "runtime_unavailable"
STATUS_INVALID_REQUEST = "invalid_request"
STATUS_ERROR = "error"

#: Operator-facing wording for a Python-less runtime. Deliberately calm: the
#: engine is healthy, only this hosting runtime lacks Python execution.
RUNTIME_UNAVAILABLE_MESSAGE = "Live OPE execution requires a Python-capable runtime."

#: Runtimes that can run a live audit. Used by front-ends to decide whether to
#: offer a "Run audit" action at all.
_LIVE_CAPABLE = frozenset({RUNTIME_PYTHON})


def runtime_supports_live_execution(runtime: str) -> bool:
    """True when *runtime* can execute the canonical Python engine."""
    return runtime in _LIVE_CAPABLE


def engine_capabilities(runtime: str = RUNTIME_PYTHON) -> dict[str, Any]:
    """Describe the engine and what *runtime* can do with it.

    Module and check counts are read from the canonical registry, so a
    front-end never hardcodes them and they cannot go stale.
    """
    from .dependency_graph import MODULE_DEPENDENCIES
    from .registry import registered_check_ids

    return {
        "web_contract": WEB_CONTRACT_VERSION,
        "engine": ENGINE,
        "engine_version": __version__,
        "runtime": runtime,
        "live_execution": runtime_supports_live_execution(runtime),
        "module_count": len(MODULE_DEPENDENCIES),
        "check_count": len(registered_check_ids()),
    }


def runtime_unavailable_payload(
    runtime: str = RUNTIME_HOSTINGER_SHARED,
    *,
    target: str | None = None,
    message: str = RUNTIME_UNAVAILABLE_MESSAGE,
) -> dict[str, Any]:
    """The honest response when a live audit cannot execute on this runtime.

    Never a failure of the engine or of the target site — only a statement that
    this deployment runtime has no Python. Carries no result, no score, and no
    findings, so a caller cannot mistake it for an audit.
    """
    payload: dict[str, Any] = {
        "status": STATUS_RUNTIME_UNAVAILABLE,
        "runtime": runtime,
        "engine": ENGINE,
        "live_execution": False,
        "message": message,
        "web_contract": WEB_CONTRACT_VERSION,
    }
    if target:
        payload["target"] = target
    return payload


def success_payload(result: dict[str, Any], *, runtime: str = RUNTIME_PYTHON) -> dict[str, Any]:
    """Wrap a canonical normalized result for transport.

    ``result`` is embedded verbatim — the canonical engine contract remains the
    only result format. ``target`` and ``engine_version`` are read back out of
    the result when present so the envelope never disagrees with its payload.
    """
    return {
        "status": STATUS_SUCCESS,
        "runtime": runtime,
        "engine": ENGINE,
        "engine_version": str(result.get("version") or __version__),
        "live_execution": True,
        "target": result.get("target"),
        "web_contract": WEB_CONTRACT_VERSION,
        "result": result,
    }


def invalid_request_payload(message: str, *, runtime: str = RUNTIME_HOSTINGER_SHARED) -> dict[str, Any]:
    """A rejected request (bad/unsafe URL, malformed JSON). Not an audit result."""
    return {
        "status": STATUS_INVALID_REQUEST,
        "runtime": runtime,
        "engine": ENGINE,
        "live_execution": False,
        "message": message,
        "web_contract": WEB_CONTRACT_VERSION,
    }
