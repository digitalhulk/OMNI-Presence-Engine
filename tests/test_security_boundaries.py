import socket
from unittest import mock

import pytest

from ope.url import validate_url_strict as _validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/",
        "http://0.0.0.0/",
        "http://[::1]/",
        "ftp://example.com/",
        "file:///etc/passwd",
        "gopher://example.com/",
    ],
)
def test_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        _validate_url(url)


def test_credential_bearing_url_validates_by_hostname_not_userinfo():
    # userinfo must not smuggle a different authority past the SSRF check;
    # validation uses the parsed hostname, which here resolves to a private IP.
    with mock.patch("ope.url.socket.getaddrinfo",
                    return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))]):
        with pytest.raises(ValueError, match="restricted"):
            _validate_url("http://user:pass@internal.example/")


def test_credential_bearing_public_url_is_allowed():
    with mock.patch("ope.url.socket.getaddrinfo",
                    return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]):
        # userinfo is not part of the SSRF decision and is stripped on normalization.
        assert _validate_url("http://user:pass@example.com/") == "http://example.com/"


def test_rejects_missing_hostname():
    with pytest.raises(ValueError):
        _validate_url("https:///broken")


def test_rejects_ipv6_loopback():
    with pytest.raises(ValueError):
        _validate_url("http://[::1]/")
