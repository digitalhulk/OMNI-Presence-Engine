#!/usr/bin/env python3
"""Tiny no-cache static server for previewing the RawBlock OPE UI.

Serves the repository root on 0.0.0.0:8080 with Cache-Control: no-store so
the preview iframe can never show a stale build.
"""
from __future__ import annotations

import http.server
import socketserver
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:  # noqa: D401 - stdlib hook
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    handler = partial(NoCacheHandler, directory=str(ROOT))
    with ReusableTCPServer(("0.0.0.0", port), handler) as httpd:
        print(f"OPE RawBlock UI → http://0.0.0.0:{port}/  (root: {ROOT})")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
