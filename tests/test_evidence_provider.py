from ope.evidence_provider import EvidenceProviderRegistry


def test_missing_provider_is_explicitly_unavailable():
    registry = EvidenceProviderRegistry()
    observation = registry.observe("dns", "example.com")
    assert observation.confidence == 0.0
    assert observation.provenance == "unavailable"
    assert observation.value is None


def test_provider_registration_and_observation():
    registry = EvidenceProviderRegistry()
    registry.register("static", lambda target: {"target": target, "ok": True})
    observation = registry.observe("static", "https://example.com")
    assert observation.source == "static"
    assert observation.value["ok"] is True
    assert observation.confidence == 1.0
    assert registry.sources() == ("static",)


def test_duplicate_provider_is_rejected():
    registry = EvidenceProviderRegistry()
    registry.register("static", lambda target: target)
    try:
        registry.register("static", lambda target: target)
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate provider was accepted")
