"""Tests for the read-only network diagnostics + error classifier.

These lock the contract that OPE distinguishes an ENVIRONMENT / proxy block
from a genuine WEBSITE failure, never leaks proxy credentials, and reuses the
canonical transport rather than a parallel client.
"""
from __future__ import annotations

import socket
import ssl
import urllib.error

from ope import audit as audit_mod
from ope.audit import Response
from ope.net_diagnostics import (
    classify_network_error,
    diagnose,
    looks_like_network_error,
)


def _urlerror(inner: BaseException) -> urllib.error.URLError:
    return urllib.error.URLError(inner)


# --- classify_network_error ------------------------------------------------

def test_proxy_tunnel_403_is_proxy_block():
    exc = _urlerror(OSError("Tunnel connection failed: 403 Forbidden"))
    cat, msg = classify_network_error(exc, proxied=True)
    assert cat == "PROXY_BLOCK"
    assert "403" in msg and "not a fault of the target" in msg.lower()


def test_dns_failure_classified():
    cat, msg = classify_network_error(_urlerror(socket.gaierror("Name or service not known")))
    assert cat == "DNS_FAILURE"


def test_tls_error_classified():
    cat, _ = classify_network_error(_urlerror(ssl.SSLError("certificate verify failed")))
    assert cat == "TLS_ERROR"


def test_connection_refused_classified():
    cat, _ = classify_network_error(_urlerror(ConnectionRefusedError("Connection refused")))
    assert cat == "CONNECTION_REFUSED"


def test_timeout_classified():
    cat, _ = classify_network_error(_urlerror(TimeoutError("timed out")))
    assert cat == "TIMEOUT"


def test_network_unreachable_classified():
    cat, msg = classify_network_error(_urlerror(OSError("Network is unreachable")))
    assert cat == "NETWORK_UNREACHABLE"
    assert "environment" in msg.lower()


def test_ssrf_blocked_from_value_error():
    cat, msg = classify_network_error(ValueError("Resolves to restricted address: 127.0.0.1"))
    assert cat == "SSRF_BLOCKED"
    assert "ssrf" in msg.lower()


def test_unsupported_scheme_is_invalid_url():
    cat, _ = classify_network_error(ValueError("Unsupported scheme: ftp"))
    assert cat == "INVALID_URL"


def test_original_cause_is_preserved_in_message():
    exc = _urlerror(OSError("Tunnel connection failed: 403 Forbidden"))
    _, msg = classify_network_error(exc, proxied=True)
    assert "Tunnel connection failed: 403 Forbidden" in msg  # underlying cause not lost


# --- looks_like_network_error ---------------------------------------------

def test_looks_like_network_error_true_for_transport():
    assert looks_like_network_error(_urlerror(OSError("x")))
    assert looks_like_network_error(socket.gaierror("x"))
    assert looks_like_network_error(TimeoutError("x"))
    assert looks_like_network_error(ValueError("Resolves to restricted address: 10.0.0.1"))


def test_looks_like_network_error_false_for_unrelated_bug():
    assert not looks_like_network_error(KeyError("findings"))
    assert not looks_like_network_error(ValueError("some unrelated engine error"))


# --- diagnose (layered probe) ---------------------------------------------

def _ok_response() -> Response:
    return Response(
        final_url="https://example.test/", status=200,
        headers={"content-type": "text/html"}, set_cookies=[],
        body=b"<html></html>", charset="utf-8", dns_ms=1.0, ttfb_ms=2.0,
    )


def _stub_valid_target(monkeypatch, normalized="https://example.test/"):
    """Make validate_target report VALID so the probe reaches the HTTP layer.

    example.test is intentionally non-resolvable (RFC 6761), so without this the
    probe would (correctly) stop at the DNS/validation layer.
    """
    from ope import url as url_mod
    from ope.url import TargetStatus, TargetValidation
    monkeypatch.setattr(
        "ope.net_diagnostics.validate_target",
        lambda u, **k: TargetValidation(url=u, status=TargetStatus.VALID,
                                        normalized=normalized, addresses=("93.184.216.34",)),
    )
    return url_mod


def test_diagnose_reachable(monkeypatch):
    _stub_valid_target(monkeypatch)
    monkeypatch.setattr(audit_mod, "_request", lambda url, timeout=15: _ok_response())
    monkeypatch.setattr("ope.crawler.fetch_robots", lambda url, timeout=10: {
        "url": url + "robots.txt", "status": 200, "error": None, "sitemaps": []})
    # sitemap probe uses net.open_url; stub it to a reachable response.
    class _Resp:
        status = 200
        def read(self, n): return b"<"
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr("ope.net.open_url", lambda url, timeout=15, headers=None: _Resp())
    report = diagnose("https://example.test/", timeout=10)
    assert report["verdict"] == "REACHABLE"
    assert report["layers"]["http"]["status"] == 200
    assert report["layers"]["robots"]["reachable"] is True


def test_diagnose_proxy_block_is_environment(monkeypatch):
    _stub_valid_target(monkeypatch)
    def boom(url, timeout=15):
        raise _urlerror(OSError("Tunnel connection failed: 403 Forbidden"))
    monkeypatch.setattr(audit_mod, "_request", boom)
    monkeypatch.setattr("ope.net.uses_proxy", lambda url: True)
    report = diagnose("https://example.test/", timeout=10)
    assert report["verdict"] == "ENVIRONMENT_BLOCK"
    assert report["category"] == "PROXY_BLOCK"
    # robots/sitemap are skipped once the origin is unreachable.
    assert "robots" not in report["layers"]


def test_diagnose_website_unreachable_without_proxy(monkeypatch):
    _stub_valid_target(monkeypatch)
    def boom(url, timeout=15):
        raise _urlerror(ConnectionRefusedError("Connection refused"))
    monkeypatch.setattr(audit_mod, "_request", boom)
    monkeypatch.setattr("ope.net.uses_proxy", lambda url: False)
    report = diagnose("https://example.test/", timeout=10)
    assert report["verdict"] == "WEBSITE_UNREACHABLE"
    assert report["category"] == "CONNECTION_REFUSED"


def test_diagnose_never_leaks_proxy_values(monkeypatch):
    # A proxy URL with embedded credentials must never appear in the report.
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secretpw@proxy.internal:8080")
    monkeypatch.setattr(audit_mod, "_request", lambda url, timeout=15: _ok_response())
    monkeypatch.setattr("ope.crawler.fetch_robots", lambda url, timeout=10: {
        "url": url, "status": 200, "error": None, "sitemaps": []})
    class _Resp:
        status = 200
        def read(self, n): return b"<"
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr("ope.net.open_url", lambda url, timeout=15, headers=None: _Resp())
    report = diagnose("https://example.test/", timeout=10)
    blob = repr(report)
    assert "secretpw" not in blob and "user:secret" not in blob
    assert "HTTPS_PROXY" in report["layers"]["proxy"]["proxy_env_vars_set"]


def test_diagnose_ssrf_blocked(monkeypatch):
    # A target that resolves to a restricted address is refused at validation.
    from ope import url as url_mod
    from ope.url import TargetStatus, TargetValidation
    monkeypatch.setattr(url_mod, "validate_target", lambda u, **k: TargetValidation(
        url=u, status=TargetStatus.BLOCKED, normalized="http://x/", reason="Resolves to restricted address: 127.0.0.1"))
    # net_diagnostics imported the name; patch there too.
    monkeypatch.setattr("ope.net_diagnostics.validate_target", url_mod.validate_target)
    report = diagnose("http://x/", timeout=5)
    assert report["verdict"] == "SSRF_BLOCKED"
    assert report["category"] == "SSRF_BLOCKED"


def test_diagnose_does_not_raise_on_invalid_url():
    report = diagnose("ftp://example.test/", timeout=5)
    assert report["verdict"] == "INVALID_URL"


# --- CLI wiring ------------------------------------------------------------

def test_cli_audit_failure_message_classifies_proxy():
    from ope.cli import _audit_failure_message
    msg = _audit_failure_message("https://x.test/", _urlerror(OSError("Tunnel connection failed: 403 Forbidden")))
    assert "[PROXY_BLOCK]" in msg
    assert "ope doctor https://x.test/" in msg


def test_cli_audit_failure_message_passthrough_for_unrelated():
    from ope.cli import _audit_failure_message
    msg = _audit_failure_message("https://x.test/", KeyError("findings"))
    assert msg.startswith("OPE audit failed:")
    assert "[" not in msg  # not classified


def test_doctor_command_exit_codes(monkeypatch, capsys):
    import argparse

    from ope import cli
    monkeypatch.setattr("ope.net_diagnostics.diagnose", lambda url, timeout=15: {
        "target": url, "verdict": "REACHABLE", "category": "OK", "detail": "ok", "layers": {}})
    rc = cli.doctor_command(argparse.Namespace(url="https://x.test/", as_json=True, timeout=5))
    assert rc == 0
    monkeypatch.setattr("ope.net_diagnostics.diagnose", lambda url, timeout=15: {
        "target": url, "verdict": "ENVIRONMENT_BLOCK", "category": "PROXY_BLOCK", "detail": "blocked", "layers": {}})
    rc = cli.doctor_command(argparse.Namespace(url="https://x.test/", as_json=False, timeout=5))
    assert rc == 2


def test_doctor_is_registered_in_parser():
    from ope.cli import build_parser
    parser = build_parser()
    ns = parser.parse_args(["doctor", "https://x.test/", "--json"])
    assert ns.command == "doctor"
    assert ns.as_json is True
