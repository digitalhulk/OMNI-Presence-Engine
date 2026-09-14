"""Security regression tests for OpenRouterClient.chat_json.

Covers OPE-SEC-001-A (unbounded response read) and OPE-SEC-001-C (HTTP
error body leakage into exception strings). Network is mocked at
urllib.request.urlopen -- the same boundary chat_json itself calls
through -- so these exercise the real bounded-read and error-sanitization
logic without needing network access.
"""

import io
import json
import urllib.error

import pytest

from ope.integrations.openrouter import (
    MAX_RESPONSE_BYTES,
    OpenRouterClient,
    OpenRouterConfig,
    OpenRouterError,
)


class _FakeResponse:
    """Mimics the subset of urllib's response object chat_json relies on.

    read(n) never returns more than n bytes, matching real socket/HTTP
    response semantics -- this is what makes the bounded-read test
    meaningful rather than trivially true.
    """

    def __init__(self, data: bytes):
        self._data = data

    def read(self, n: int = -1) -> bytes:
        if n == -1:
            return self._data
        return self._data[:n]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _config():
    return OpenRouterConfig(api_key="test-key", model="test/model")


def _valid_envelope_bytes(padding: bytes = b"") -> bytes:
    """A real, valid JSON envelope chat_json can fully parse, optionally
    padded with leading whitespace (still valid JSON) to reach an exact
    byte length for boundary testing."""
    inner = json.dumps({"root_cause_hypotheses": [], "priorities": []})
    envelope = {"choices": [{"message": {"content": inner}}]}
    return padding + json.dumps(envelope).encode("utf-8")


# ---------------------------------------------------------------------------
# OPE-SEC-001-A: bounded response read
# ---------------------------------------------------------------------------


def test_response_below_limit_succeeds(monkeypatch):
    body = _valid_envelope_bytes()
    assert len(body) < MAX_RESPONSE_BYTES
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(body))

    client = OpenRouterClient(_config())
    result = client.chat_json([{"role": "user", "content": "hi"}])
    assert result == {"root_cause_hypotheses": [], "priorities": []}


def test_response_exactly_at_limit_succeeds(monkeypatch):
    base = _valid_envelope_bytes()
    padding = b" " * (MAX_RESPONSE_BYTES - len(base))
    body = _valid_envelope_bytes(padding)
    assert len(body) == MAX_RESPONSE_BYTES
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(body))

    client = OpenRouterClient(_config())
    result = client.chat_json([{"role": "user", "content": "hi"}])
    assert result == {"root_cause_hypotheses": [], "priorities": []}


def test_response_above_limit_raises_openrouter_error(monkeypatch):
    base = _valid_envelope_bytes()
    padding = b" " * (MAX_RESPONSE_BYTES - len(base) + 1)  # exactly one byte over
    body = _valid_envelope_bytes(padding)
    assert len(body) == MAX_RESPONSE_BYTES + 1
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(body))

    client = OpenRouterClient(_config())
    with pytest.raises(OpenRouterError, match="exceeds safety limit"):
        client.chat_json([{"role": "user", "content": "hi"}])


def test_oversized_response_is_never_json_parsed(monkeypatch):
    # Deliberately invalid JSON padding -- if the oversized body were passed
    # to json.loads, it would raise a JSON-decode-shaped error instead of
    # the safety-limit error, revealing that the limit check happens after
    # (not before) parsing. This confirms the limit check gates parsing.
    invalid_padding = b"{not valid json at all" * (MAX_RESPONSE_BYTES // 20)
    body = invalid_padding[: MAX_RESPONSE_BYTES + 100]
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(body))

    client = OpenRouterClient(_config())
    with pytest.raises(OpenRouterError, match="exceeds safety limit"):
        client.chat_json([{"role": "user", "content": "hi"}])


def test_oversized_response_error_does_not_contain_body_content(monkeypatch):
    marker = b"UNIQUE_OVERSIZED_BODY_MARKER_98765"
    base = _valid_envelope_bytes()
    padding = b" " * (MAX_RESPONSE_BYTES - len(base) + 1)
    body = marker + padding + base
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(body))

    client = OpenRouterClient(_config())
    with pytest.raises(OpenRouterError) as exc_info:
        client.chat_json([{"role": "user", "content": "hi"}])
    assert marker.decode() not in str(exc_info.value)


# ---------------------------------------------------------------------------
# OPE-SEC-001-C: HTTP error body sanitization
# ---------------------------------------------------------------------------


def test_http_error_body_is_not_included_in_exception_string(monkeypatch):
    secret_marker = "SECRET_INTERNAL_TOKEN"
    error_body = json.dumps({"error": "upstream failure", "debug": secret_marker}).encode("utf-8")

    def raise_http_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(error_body),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_http_error)

    client = OpenRouterClient(_config())
    with pytest.raises(OpenRouterError) as exc_info:
        client.chat_json([{"role": "user", "content": "hi"}])

    message = str(exc_info.value)
    assert secret_marker not in message


def test_http_error_status_code_remains_available(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b"rate limited"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_http_error)

    client = OpenRouterClient(_config())
    with pytest.raises(OpenRouterError) as exc_info:
        client.chat_json([{"role": "user", "content": "hi"}])

    message = str(exc_info.value)
    assert "429" in message


def test_http_error_preserves_openrouter_error_type(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b"invalid api key"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_http_error)

    client = OpenRouterClient(_config())
    with pytest.raises(OpenRouterError):
        client.chat_json([{"role": "user", "content": "hi"}])


def test_api_key_never_appears_in_error_message(monkeypatch):
    # The API key must never leak into an exception string via any path --
    # neither the oversized-response path nor the HTTPError path construct
    # their message from request headers, but this pins that guarantee
    # explicitly against a realistic-looking secret value.
    secret_key = "sk-or-v1-topsecretapikeyvalue1234567890"

    def raise_http_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b"invalid credentials"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_http_error)

    client = OpenRouterClient(OpenRouterConfig(api_key=secret_key, model="test/model"))
    with pytest.raises(OpenRouterError) as exc_info:
        client.chat_json([{"role": "user", "content": "hi"}])

    assert secret_key not in str(exc_info.value)
