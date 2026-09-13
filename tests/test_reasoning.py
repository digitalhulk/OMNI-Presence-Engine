from ope.integrations.openrouter import OpenRouterConfig, OpenRouterError
from ope.reasoning import reason_about_result


class FakeClient:
    config = OpenRouterConfig(api_key="test", model="test/model")

    def chat_json(self, messages, *, temperature=0.0):
        assert messages[0]["role"] == "system"
        assert "Do not invent observations" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert temperature == 0.0
        return {
            "root_cause_hypotheses": [],
            "priorities": [],
            "recommendations": [],
            "content_opportunities": [],
            "validation_plan": [],
        }


def test_reasoning_is_advisory_and_does_not_mutate_result():
    result = {"target": "https://example.com", "modules": {"01": {"status": "UNKNOWN"}}, "findings": []}
    output = reason_about_result(result, FakeClient())
    assert output["provider"] == "openrouter"
    assert output["model"] == "test/model"
    assert output["advisory"] is True
    assert output["grounded_in"] == "deterministic-audit-evidence"
    assert result["modules"]["01"]["status"] == "UNKNOWN"


def test_missing_api_key_is_explicit(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert OpenRouterConfig.from_env() is None
    try:
        from ope.integrations.openrouter import OpenRouterClient
        OpenRouterClient()
    except OpenRouterError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("OpenRouterClient should reject missing credentials")
