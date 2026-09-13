import pytest

from ope.audit import _validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/",
        "ftp://example.com/",
        "file:///etc/passwd",
    ],
)
def test_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        _validate_url(url)


def test_rejects_missing_hostname():
    with pytest.raises(ValueError):
        _validate_url("https:///broken")


def test_rejects_ipv6_loopback():
    with pytest.raises(ValueError):
        _validate_url("http://[::1]/")
