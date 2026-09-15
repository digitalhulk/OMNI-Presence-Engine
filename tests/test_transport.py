"""Real-transport regression tests (local HTTP server, not mocks).

These exercise ope.audit._request against an actual HTTP server so the true
urllib behaviour is verified — 4xx/5xx status handling, redirect-hop SSRF
revalidation, and truncated Content-Length — rather than a mocked _request
that could mask production behaviour.
"""
from __future__ import annotations

import http.server
import threading

import pytest

import ope.audit as audit_module
import ope.net as net_module
import ope.url as url_module


class _Handler(http.server.BaseHTTPRequestHandler):
    routes: dict = {}

    def log_message(self, *_a):
        pass

    def do_GET(self):
        spec = self.routes.get(self.path, self.routes.get("/"))
        status = spec.get("status", 200)
        headers = dict(spec.get("headers", {}))
        body = spec.get("body", b"<html><head><title>t</title></head><body>ok</body></html>")
        raw = spec.get("raw_body")  # bytes written directly, bypassing full body (for truncation)
        self.send_response(status)
        headers.setdefault("Content-Type", "text/html")
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(raw if raw is not None else body)
        except Exception:
            pass


@pytest.fixture()
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield httpd, port
    httpd.shutdown()


@pytest.fixture()
def allow_loopback(monkeypatch):
    # Allow the loopback test server, but keep 10.0.0.1 (the redirect target)
    # genuinely restricted so the redirect-hop guard is really exercised.
    monkeypatch.setattr(url_module, "address_is_restricted", lambda a: str(a).startswith("10."))
    # Force the direct (pinned) path so we connect to the local server, not a proxy.
    monkeypatch.setattr(net_module, "uses_proxy", lambda url: False)


def _route(port, path, **spec):
    _Handler.routes = {path: spec}
    return f"http://127.0.0.1:{port}{path}"


class TestStatusCodesViaRealTransport:
    @pytest.mark.parametrize("status", [404, 500, 503])
    def test_4xx_5xx_becomes_a_response_not_a_crash(self, server, allow_loopback, status):
        _httpd, port = server
        url = _route(port, "/", status=status)
        resp = audit_module._request(url)
        assert resp.status == status  # HTTPError was caught and represented

    def test_http_error_status_produces_code_http_001_finding(self, server, allow_loopback):
        _httpd, port = server
        url = _route(port, "/", status=503)
        result = audit_module.audit(url, fetch_subresources=False)
        ids = {f["id"] for f in result["findings"]}
        assert "CODE-HTTP-001" in ids  # unreachable before the HTTPError fix

    def test_200_success_path_still_works(self, server, allow_loopback):
        _httpd, port = server
        url = _route(port, "/", status=200, body=b"<html><head><title>ok</title></head><body>hi</body></html>")
        resp = audit_module._request(url)
        assert resp.status == 200
        assert b"hi" in resp.body


class TestTruncationViaRealTransport:
    def test_body_shorter_than_content_length_is_rejected(self, server, allow_loopback):
        _httpd, port = server
        # Advertise 5000 bytes but send only a few.
        url = _route(port, "/", status=200,
                     headers={"Content-Length": "5000"}, raw_body=b"<html>short</html>")
        with pytest.raises(ValueError, match="Incomplete response"):
            audit_module._request(url)


class TestRedirectHopSSRFViaRealTransport:
    def test_redirect_to_private_ip_is_blocked_end_to_end(self, server, allow_loopback):
        _httpd, port = server
        # A public (loopback, allowed here) URL that 302-redirects to a private IP.
        url = _route(port, "/", status=302, headers={"Location": "http://10.0.0.1/secret"})
        with pytest.raises(ValueError, match="restricted"):
            audit_module._request(url)


class TestSafeRedirectHandlerUnit:
    @pytest.mark.parametrize("target", [
        "http://127.0.0.1/", "http://10.0.0.1/", "http://169.254.169.254/", "http://[::1]/",
    ])
    def test_redirect_to_restricted_target_raises(self, target):
        import urllib.request
        h = net_module.SafeRedirectHandler()
        req = urllib.request.Request("https://public.example/")
        with pytest.raises(ValueError):
            h.redirect_request(req, None, 302, "Found", {}, target)

    def test_redirect_limit_on_handler(self):
        assert net_module.SafeRedirectHandler.max_redirections == net_module.MAX_REDIRECTS
