"""Tests for SSRF-safe pinned connections and the DNS-rebinding guard."""
from __future__ import annotations

import socket
from unittest import mock

import pytest

from ope import net
from ope.url import address_is_restricted, resolve_and_validate

_PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
_PRIVATE = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.5", 0))]
_METADATA = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))]
_MIXED = _PUBLIC + _PRIVATE


class TestAddressIsRestricted:
    @pytest.mark.parametrize("addr", [
        "127.0.0.1", "0.0.0.0", "10.0.0.1", "192.168.1.1", "172.16.0.1",
        "169.254.169.254", "::1", "::ffff:127.0.0.1", "::ffff:10.0.0.1", "fe80::1",
        "not-an-ip",
    ])
    def test_restricted(self, addr):
        assert address_is_restricted(addr) is True

    @pytest.mark.parametrize("addr", ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"])
    def test_allowed(self, addr):
        assert address_is_restricted(addr) is False


class TestResolveAndValidate:
    def test_public_ok(self):
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_PUBLIC):
            assert resolve_and_validate("example.com") == ("93.184.216.34",)

    def test_private_raises(self):
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_PRIVATE):
            with pytest.raises(ValueError, match="restricted"):
                resolve_and_validate("internal.example")

    def test_metadata_raises(self):
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_METADATA):
            with pytest.raises(ValueError, match="restricted"):
                resolve_and_validate("metadata.example")

    def test_mixed_public_private_raises(self):
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_MIXED):
            with pytest.raises(ValueError, match="restricted"):
                resolve_and_validate("rebind.example")

    def test_dns_failure_raises(self):
        with mock.patch("ope.url.socket.getaddrinfo", side_effect=socket.gaierror("x")):
            with pytest.raises(ValueError, match="DNS resolution failed"):
                resolve_and_validate("nope.invalid")


class TestPinnedConnections:
    def test_http_connect_blocks_restricted_before_connecting(self):
        conn = net._PinnedHTTPConnection("evil.example", 80)
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_PRIVATE), \
             mock.patch("ope.net.socket.create_connection") as create:
            with pytest.raises(ValueError, match="restricted"):
                conn.connect()
            create.assert_not_called()

    def test_https_connect_blocks_restricted_before_connecting(self):
        conn = net._PinnedHTTPSConnection("evil.example", 443)
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_METADATA), \
             mock.patch("ope.net.socket.create_connection") as create:
            with pytest.raises(ValueError, match="restricted"):
                conn.connect()
            create.assert_not_called()

    def test_http_connect_pins_validated_address(self):
        conn = net._PinnedHTTPConnection("example.com", 80)
        with mock.patch("ope.url.socket.getaddrinfo", return_value=_PUBLIC), \
             mock.patch("ope.net.socket.create_connection", return_value="sock") as create:
            conn.connect()
            # Connects to the validated IP literal, not the hostname.
            args = create.call_args[0][0]
            assert args == ("93.184.216.34", 80)


class TestUsesProxy:
    def test_no_proxy(self):
        with mock.patch("ope.net.urllib.request.getproxies", return_value={}):
            assert net.uses_proxy("https://example.com") is False

    def test_proxy_applies(self):
        with mock.patch("ope.net.urllib.request.getproxies", return_value={"https": "http://p:8080"}), \
             mock.patch("ope.net.urllib.request.proxy_bypass", return_value=False):
            assert net.uses_proxy("https://example.com") is True

    def test_proxy_bypassed_host(self):
        with mock.patch("ope.net.urllib.request.getproxies", return_value={"https": "http://p:8080"}), \
             mock.patch("ope.net.urllib.request.proxy_bypass", return_value=True):
            assert net.uses_proxy("https://internal.example") is False


class TestBuildOpener:
    def test_direct_uses_pinned_handlers(self):
        import ssl
        import urllib.request
        with mock.patch("ope.net.uses_proxy", return_value=False):
            opener = net.build_opener("https://example.com", urllib.request.HTTPRedirectHandler(), ssl.create_default_context())
        classes = {type(h) for h in opener.handlers}
        assert net._PinnedHTTPSHandler in classes
        assert net._PinnedHTTPHandler in classes

    def test_proxy_uses_standard_handlers(self):
        import ssl
        import urllib.request
        with mock.patch("ope.net.uses_proxy", return_value=True):
            opener = net.build_opener("https://example.com", urllib.request.HTTPRedirectHandler(), ssl.create_default_context())
        classes = {type(h) for h in opener.handlers}
        assert net._PinnedHTTPSHandler not in classes


def test_toctou_rebinding_is_closed_at_connect(monkeypatch):
    """A host that validates as public but rebinds to private at connect time
    is blocked by the pinned connection — the resolution used to validate is
    the one used to connect."""
    conn = net._PinnedHTTPSConnection("rebind.example", 443)
    # By connect time the record has rebound to a private address.
    with mock.patch("ope.url.socket.getaddrinfo", return_value=_PRIVATE), \
         mock.patch("ope.net.socket.create_connection") as create:
        with pytest.raises(ValueError, match="restricted"):
            conn.connect()
        create.assert_not_called()
