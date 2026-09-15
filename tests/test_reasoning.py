import io
import json

from ope.integrations import openrouter
from ope.integrations.openrouter import (
    MAX_RESPONSE_BYTES,
    OpenRouterClient,
    OpenRouterConfig,
    OpenRouterError,
)
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
        OpenRouterClient()
    except OpenRouterError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("OpenRouterClient should reject missing credentials")


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._buf = io.BytesIO(body)

    def read(self, amt: int | None = None) -> bytes:
        return self._buf.read(amt)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def test_oversized_response_body_is_rejected(monkeypatch):
    client = OpenRouterClient(OpenRouterConfig(api_key="test"))
    oversized = b"x" * (MAX_RESPONSE_BYTES + 10)
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(oversized))
    try:
        client.chat_json([{"role": "user", "content": "hi"}])
    except OpenRouterError as exc:
        assert "safety limit" in str(exc)
    else:
        raise AssertionError("oversized response body should be rejected")


def test_bounded_response_body_is_parsed(monkeypatch):
    client = OpenRouterClient(OpenRouterConfig(api_key="test"))
    payload = json.dumps({"choices": [{"message": {"content": json.dumps({"ok": True})}}]}).encode()
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload))
    assert client.chat_json([{"role": "user", "content": "hi"}]) == {"ok": True}


def test_user_agent_is_derived_from_version_not_hardcoded(monkeypatch):
    # The reasoning UA must track the package version, not a stale "0.1".
    assert openrouter.USER_AGENT.startswith("OPE-Reasoning/")
    assert openrouter.USER_AGENT != "OPE-Reasoning/0.1"

    captured: dict[str, str] = {}

    def fake_urlopen(req, timeout=None):
        captured["ua"] = req.get_header("User-agent")
        payload = json.dumps({"choices": [{"message": {"content": json.dumps({"ok": True})}}]}).encode()
        return _FakeResponse(payload)

    client = OpenRouterClient(OpenRouterConfig(api_key="test"))
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", fake_urlopen)
    client.chat_json([{"role": "user", "content": "hi"}])
    assert captured["ua"] == openrouter.USER_AGENT
