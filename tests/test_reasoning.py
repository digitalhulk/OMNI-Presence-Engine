import pytest

from ope.integrations.openrouter import OpenRouterConfig, OpenRouterError
from ope.reasoning import REQUIRED_RESULT_KEYS, ReasoningContractError, reason_about_result


_DEFAULT_RESPONSE = {
    "root_cause_hypotheses": [],
    "priorities": [],
    "recommendations": [],
    "content_opportunities": [],
    "validation_plan": [],
}
_UNSET = object()


class FakeClient:
    config = OpenRouterConfig(api_key="test", model="test/model")

    def __init__(self, response=_UNSET):
        self._response = _DEFAULT_RESPONSE if response is _UNSET else response

    def chat_json(self, messages, *, temperature=0.0):
        assert messages[0]["role"] == "system"
        assert "Do not invent observations" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert temperature == 0.0
        return self._response


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


def test_response_missing_required_keys_normalizes_to_empty_lists():
    result = {"target": "https://example.com", "modules": {}, "findings": []}
    output = reason_about_result(result, FakeClient(response={"unexpected": "garbage"}))
    for key in REQUIRED_RESULT_KEYS:
        assert output["result"][key] == []
    assert "unexpected" not in output["result"]


def test_response_with_non_list_values_normalizes_to_empty_list():
    result = {"target": "https://example.com", "modules": {}, "findings": []}
    malformed = {
        "root_cause_hypotheses": "not a list",
        "priorities": 42,
        "recommendations": None,
        "content_opportunities": {"nested": "object"},
        "validation_plan": ["ok item"],
    }
    output = reason_about_result(result, FakeClient(response=malformed))
    assert output["result"]["root_cause_hypotheses"] == []
    assert output["result"]["priorities"] == []
    assert output["result"]["recommendations"] == []
    assert output["result"]["content_opportunities"] == []
    assert output["result"]["validation_plan"] == ["ok item"]


def test_non_dict_response_raises_contract_error():
    result = {"target": "https://example.com", "modules": {}, "findings": []}
    with pytest.raises(ReasoningContractError):
        reason_about_result(result, FakeClient(response=["not", "a", "dict"]))


def test_null_response_raises_contract_error():
    result = {"target": "https://example.com", "modules": {}, "findings": []}
    with pytest.raises(ReasoningContractError):
        reason_about_result(result, FakeClient(response=None))


def test_provider_transport_failure_is_not_swallowed():
    class FailingClient:
        config = OpenRouterConfig(api_key="test", model="test/model")

        def chat_json(self, messages, *, temperature=0.0):
            raise OpenRouterError("OpenRouter HTTP 500: upstream failure")

    result = {"target": "https://example.com", "modules": {}, "findings": []}
    with pytest.raises(OpenRouterError):
        reason_about_result(result, FailingClient())
