"""Optional external evidence providers — capability discovery.

OPE's core checks are deterministic and run from direct observation. A small
set of checks can be *upgraded* from ``UNKNOWN`` to measured evidence when an
optional provider is configured via an environment variable. Providers are
isolated from the deterministic core: when a provider's credential is absent
the affected checks stay ``UNKNOWN`` with a specific reason, and evidence is
never fabricated.

This module makes that contract explicit and queryable — it answers "what is
configured, and what would enabling a credential improve?" — without adding a
dynamic plugin framework there is no second real provider to justify.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

# name -> (env var that enables it, human description, checks it upgrades).
# An empty checks tuple means the provider adds an advisory layer rather than
# upgrading specific registry checks.
_PROVIDERS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "pagespeed": (
        "OPE_PAGESPEED_API_KEY",
        "Google PageSpeed Insights — Core Web Vitals (LCP/CLS/INP)",
        ("15-performance.lcp", "15-performance.cls", "15-performance.inp"),
    ),
    "search_console": (
        "OPE_SEARCH_CONSOLE_KEY",
        "Google Search Console — query visibility",
        ("09-search.query_visibility",),
    ),
    "backlink_index": (
        "OPE_BACKLINK_API_KEY",
        "Backlink index (e.g. Ahrefs/Moz) — off-site authority links",
        ("11-authority.backlinks",),
    ),
    "openrouter": (
        "OPENROUTER_API_KEY",
        "Optional advisory reasoning layer over deterministic evidence",
        (),
    ),
}


def provider_status(env: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    """Report each optional provider: whether it is configured and what it upgrades.

    Deterministic and side-effect free. ``configured`` reflects only whether
    the credential is present in *env* — it makes no network call. Providers
    are listed in a stable order.
    """
    environ = os.environ if env is None else env
    status: list[dict[str, Any]] = []
    for name in sorted(_PROVIDERS):
        env_var, description, checks = _PROVIDERS[name]
        status.append({
            "provider": name,
            "env_var": env_var,
            "configured": bool(str(environ.get(env_var, "")).strip()),
            "description": description,
            "upgrades_checks": list(checks),
        })
    return status


def providers_markdown(env: Mapping[str, str] | None = None) -> str:
    """Render provider capability discovery as markdown."""
    lines = [
        "# OPE Optional Providers",
        "",
        "Core checks are deterministic. These optional providers upgrade specific",
        "checks from UNKNOWN to measured evidence when their credential is set.",
        "",
        "| Provider | Env var | Configured | Upgrades |",
        "| --- | --- | --- | --- |",
    ]
    for entry in provider_status(env):
        upgrades = ", ".join(entry["upgrades_checks"]) or "(advisory layer)"
        mark = "yes" if entry["configured"] else "no"
        lines.append(f"| {entry['provider']} | {entry['env_var']} | {mark} | {upgrades} |")
    return "\n".join(lines)
