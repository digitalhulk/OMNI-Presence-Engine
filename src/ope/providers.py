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

# name -> (env var that enables it, human description, checks it upgrades,
# whether an executable adapter actually consumes the credential).
# An empty checks tuple means the provider adds an advisory layer rather than
# upgrading specific registry checks.
#
# ``implemented`` is True only when a real adapter reads the credential and
# feeds evidence into the pipeline:
#   pagespeed      -> inventory["pagespeed"]      -> Core Web Vitals checks
#   search_console -> inventory["search_console"] -> 09-search.query_visibility
#   backlink_index -> inventory["backlinks"]      -> 11-authority.backlinks
#   openrouter     -> advisory reasoning layer
# A provider left at False would be a documented-but-unwired capability whose
# credential is reported for status but upgrades no check. Surfacing this flag
# keeps capability discovery honest — a configured credential never implies an
# upgrade that would not actually happen.
_PROVIDERS: dict[str, tuple[str, str, tuple[str, ...], bool]] = {
    "pagespeed": (
        "OPE_PAGESPEED_API_KEY",
        "Google PageSpeed Insights — Core Web Vitals (LCP/CLS/INP)",
        ("15-performance.lcp", "15-performance.cls", "15-performance.inp"),
        True,
    ),
    "search_console": (
        "OPE_SEARCH_CONSOLE_KEY",
        "Google Search Console — query visibility",
        ("09-search.query_visibility",),
        True,
    ),
    "backlink_index": (
        "OPE_BACKLINK_API_KEY",
        "Backlink index (e.g. Ahrefs/Moz) — off-site authority links",
        ("11-authority.backlinks",),
        True,
    ),
    "openrouter": (
        "OPENROUTER_API_KEY",
        "Optional advisory reasoning layer over deterministic evidence",
        (),
        True,
    ),
    "osv_dependencies": (
        "OPE_DEPENDENCY_SCAN",
        "Client-side dependency CVE scan via OSV.dev (free, no key; set to enable network scan)",
        ("16-security.dependencies",),
        True,
    ),
}


def provider_status(env: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    """Report each optional provider: whether it is configured and what it upgrades.

    Deterministic and side-effect free. ``configured`` reflects only whether
    the credential is present in *env* — it makes no network call. ``implemented``
    reflects whether an executable adapter actually consumes the credential; a
    provider that is ``configured`` but not ``implemented`` upgrades no check.
    Providers are listed in a stable order.
    """
    environ = os.environ if env is None else env
    status: list[dict[str, Any]] = []
    for name in sorted(_PROVIDERS):
        env_var, description, checks, implemented = _PROVIDERS[name]
        status.append({
            "provider": name,
            "env_var": env_var,
            "configured": bool(str(environ.get(env_var, "")).strip()),
            "implemented": implemented,
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
        "Providers marked *planned* under Adapter have no executable adapter yet:",
        "setting their credential is reported but upgrades no check.",
        "",
        "| Provider | Env var | Configured | Adapter | Upgrades |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in provider_status(env):
        upgrades = ", ".join(entry["upgrades_checks"]) or "(advisory layer)"
        mark = "yes" if entry["configured"] else "no"
        adapter = "active" if entry["implemented"] else "planned"
        lines.append(f"| {entry['provider']} | {entry['env_var']} | {mark} | {adapter} | {upgrades} |")
    return "\n".join(lines)
