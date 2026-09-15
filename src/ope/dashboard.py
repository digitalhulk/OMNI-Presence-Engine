"""Local OMNI Command Center dashboard server (stdlib only).

Serves a single-page dashboard and a small JSON API that runs the real OPE
engine via :mod:`ope.dashboard_service`. It binds to localhost by default and
holds no state beyond an in-memory cache of the most recent runs (keyed by
run id) so exports reproduce the exact run. There is no database and no cloud
dependency.

Security posture: localhost bind by default; request bodies are size-capped;
target URLs are validated by the engine's SSRF guard before any fetch; export
rendering reuses the canonical HTML renderer (which HTML-escapes all content);
no user input is used as a filesystem path.
"""
from __future__ import annotations

import http.server
import json
import socketserver
import threading
import urllib.parse
from typing import Any

from . import dashboard_service as service
from .dashboard_ui import render_index

MAX_BODY_BYTES = 8 * 1024 * 1024


class _State:
    """In-memory cache of recent canonical runs, so exports match the run exactly."""

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def store(self, result: dict[str, Any]) -> None:
        run_id = str(result.get("run_id") or "")
        if run_id:
            with self._lock:
                self._runs[run_id] = result
                # bound the cache
                if len(self._runs) > 32:
                    for stale in list(self._runs)[:-32]:
                        del self._runs[stale]

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._runs.get(run_id)


def _make_handler(state: _State) -> type[http.server.BaseHTTPRequestHandler]:
    class DashboardHandler(http.server.BaseHTTPRequestHandler):
        server_version = "OMNI-Dashboard"

        def log_message(self, *_args: Any) -> None:  # keep the console quiet
            pass

        # -- helpers -------------------------------------------------------
        def _send(self, status: int, body: bytes, content_type: str, *, download: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj: Any) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json")

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                raise ValueError("request body too large")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            return data

        # -- routing -------------------------------------------------------
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            route = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            try:
                if route == "/" or route == "/index.html":
                    self._send(200, render_index().encode("utf-8"), "text/html; charset=utf-8")
                elif route == "/api/providers":
                    self._json(200, {"providers": service.get_providers()})
                elif route == "/api/dependency-graph":
                    self._json(200, service.dependency_graph_view())
                elif route == "/api/history":
                    target = (query.get("target") or [""])[0]
                    self._json(200, {"target": target, "runs": service.get_history(target)})
                else:
                    self._json(404, {"error": "not found"})
            except Exception as exc:  # never leak a traceback to the client
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

        def do_POST(self) -> None:
            route = urllib.parse.urlparse(self.path).path
            try:
                body = self._read_json_body()
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            try:
                if route == "/api/audit":
                    self._handle_audit(body)
                elif route == "/api/multi-audit":
                    self._handle_multi(body)
                elif route == "/api/reason":
                    self._handle_reason(body)
                elif route == "/api/export":
                    self._handle_export(body)
                else:
                    self._json(404, {"error": "not found"})
            except ValueError as exc:
                # target validation / bad request — clean 400, no traceback
                self._json(400, {"error": f"{exc}"})
            except Exception as exc:
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

        def _handle_audit(self, body: dict[str, Any]) -> None:
            url = str(body.get("url") or "").strip()
            if not url:
                self._json(400, {"error": "url is required"})
                return
            timeout = int(body.get("timeout") or 15)
            result = service.run_single_audit(
                url, timeout=max(1, min(timeout, 60)),
                fetch_subresources=bool(body.get("fetch_subresources", True)),
                record_history=bool(body.get("record_history", True)),
            )
            state.store(result)
            self._json(200, result)

        def _handle_multi(self, body: dict[str, Any]) -> None:
            urls = body.get("urls")
            if not isinstance(urls, list) or not urls:
                self._json(400, {"error": "urls (non-empty list) is required"})
                return
            report = service.run_multi_audit(
                [str(u).strip() for u in urls][:50],
                timeout=max(1, min(int(body.get("timeout") or 15), 60)),
                max_workers=int(body.get("max_workers") or 4),
            )
            for entry in report.get("results", []):
                if entry.get("ok") and isinstance(entry.get("result"), dict):
                    state.store(entry["result"])
            self._json(200, report)

        def _handle_reason(self, body: dict[str, Any]) -> None:
            # Resolve the exact cached run (preferred) or a posted result, like export.
            run_id = str(body.get("run_id") or "")
            result = state.get(run_id) if run_id else None
            if result is None:
                result = body.get("result")
            if not isinstance(result, dict):
                self._json(400, {"error": "no run available to reason over (missing run_id/result)"})
                return
            self._json(200, {"reasoning": service.get_reasoning(result)})

        def _handle_export(self, body: dict[str, Any]) -> None:
            fmt = str(body.get("format") or "json")
            # Prefer a cached run (exact reproduction); fall back to a posted result.
            run_id = str(body.get("run_id") or "")
            result = state.get(run_id) if run_id else None
            if result is None:
                result = body.get("result")
            if not isinstance(result, dict):
                self._json(400, {"error": "no run available to export (missing run_id/result)"})
                return
            if fmt == "bundle":
                data, ctype, filename = service.export_bundle(result)
            elif fmt in ("pdf", "png"):
                try:
                    data, ctype, filename = service.export_visual(result, fmt)
                except service.ExportUnavailable as exc:
                    self._json(501, {"error": str(exc)})
                    return
            else:
                data, ctype, filename = service.export_result(result, fmt)
            self._send(200, data, ctype, download=filename)

    return DashboardHandler


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(host: str = "127.0.0.1", port: int = 8787) -> _Server:
    """Create (but do not start) the dashboard server bound to *host*:*port*."""
    handler = _make_handler(_State())
    return _Server((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8787) -> int:
    """Run the dashboard server until interrupted."""
    with create_server(host, port) as httpd:
        bound_host, bound_port = str(httpd.server_address[0]), int(httpd.server_address[1])
        print(f"OMNI Command Center → http://{bound_host}:{bound_port}/")
        print("Enter a URL and run a real OPE audit. Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nOMNI Command Center stopped.")
    return 0
