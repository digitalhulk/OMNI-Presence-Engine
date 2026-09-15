"""Tests for optional-provider capability discovery."""
from __future__ import annotations

from ope.providers import provider_status, providers_markdown


def test_status_reports_all_providers_deterministically():
    a = provider_status({})
    b = provider_status({})
    assert a == b
    names = [p["provider"] for p in a]
    assert names == sorted(names)
    assert {"pagespeed", "search_console", "backlink_index", "openrouter"} <= set(names)


def test_unconfigured_by_default():
    for entry in provider_status({}):
        assert entry["configured"] is False


def test_configured_when_env_present():
    status = {p["provider"]: p for p in provider_status({"OPE_PAGESPEED_API_KEY": "k"})}
    assert status["pagespeed"]["configured"] is True
    assert status["search_console"]["configured"] is False


def test_blank_env_is_not_configured():
    status = {p["provider"]: p for p in provider_status({"OPE_PAGESPEED_API_KEY": "   "})}
    assert status["pagespeed"]["configured"] is False


def test_pagespeed_upgrades_named_checks():
    status = {p["provider"]: p for p in provider_status({})}
    assert "15-performance.lcp" in status["pagespeed"]["upgrades_checks"]


def test_markdown_renders_table():
    md = providers_markdown({"OPE_BACKLINK_API_KEY": "k"})
    assert "Optional Providers" in md
    assert "backlink_index" in md
    # backlink_index is configured here but has no executable adapter, so it is
    # rendered as "planned", not as an active upgrade.
    assert "| backlink_index | OPE_BACKLINK_API_KEY | yes | planned |" in md
    assert "| pagespeed | OPE_PAGESPEED_API_KEY | no | active |" in md


def test_status_reports_implemented_flag():
    status = {p["provider"]: p for p in provider_status({})}
    # Only providers with a real adapter consuming the credential are implemented.
    assert status["pagespeed"]["implemented"] is True
    assert status["openrouter"]["implemented"] is True
    assert status["search_console"]["implemented"] is False
    assert status["backlink_index"]["implemented"] is False


def test_unimplemented_providers_do_not_actually_upgrade_checks():
    # Honesty invariant: a provider flagged implemented=False must only claim to
    # upgrade checks that are hard-wired to stay UNKNOWN (no adapter feeds them),
    # so reporting it as "planned" is accurate rather than a false capability.
    from ope.audit_pipeline import _EXTERNAL_EVIDENCE_CHECKS, _PSI_VITALS
    for entry in provider_status({}):
        if entry["implemented"] or not entry["upgrades_checks"]:
            continue
        for check_id in entry["upgrades_checks"]:
            assert check_id in _EXTERNAL_EVIDENCE_CHECKS
            assert check_id not in _PSI_VITALS


def test_implemented_provider_checks_have_a_real_code_path():
    # pagespeed is implemented: its upgrade checks must be backed by a real
    # execution path (the PSI vitals table), not the always-UNKNOWN external map.
    from ope.audit_pipeline import _EXTERNAL_EVIDENCE_CHECKS, _PSI_VITALS
    status = {p["provider"]: p for p in provider_status({})}
    for check_id in status["pagespeed"]["upgrades_checks"]:
        assert check_id in _PSI_VITALS
        assert check_id not in _EXTERNAL_EVIDENCE_CHECKS


def test_provider_env_vars_match_check_reasons():
    # The provider registry's env vars must match the reasons the external
    # checks actually report, so capability discovery is truthful.
    from ope.audit_pipeline import _EXTERNAL_EVIDENCE_CHECKS
    reasons = " ".join(reason for _, reason in _EXTERNAL_EVIDENCE_CHECKS.values())
    for entry in provider_status({}):
        if entry["upgrades_checks"]:
            # every upgraded check id must be a real external-evidence check
            for check_id in entry["upgrades_checks"]:
                # performance checks are key-gated but not in the external map;
                # only assert for the ones declared external.
                if check_id in _EXTERNAL_EVIDENCE_CHECKS:
                    assert entry["env_var"] in reasons
