"""Real headless-browser test of the OMNI Command Center.

Drives the actual shipped dashboard (HTML+JS) in Chromium via Playwright against
the deterministic fixture transport — proving the operator flow renders the
canonical run in a real browser. Skips cleanly when Playwright or a Chromium
binary is not available (e.g. the stdlib-only CI image), so it never blocks the
core gate.
"""
from __future__ import annotations

import glob
import os
import threading

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")


def _find_chromium() -> str | None:
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if root:
        hits = sorted(glob.glob(os.path.join(root, "chromium-*/chrome-linux/chrome")))
        if hits:
            return hits[-1]
    return None  # let Playwright use its default; skip if that fails


@pytest.fixture()
def live_dashboard(monkeypatch):
    import ope.audit as a
    from ope import dashboard
    from ope.audit import Response
    html = (b"<html lang=en><head><title>Acme</title></head><body><h1>Acme</h1><img src=x>"
            b"</body></html>")
    monkeypatch.setattr(a, "_request", lambda url, timeout=15: Response(
        final_url="http://acme.example/", status=503, headers={"content-type": "text/html"},
        set_cookies=[], body=html, charset="utf-8", dns_ms=1.0, ttfb_ms=1.0))
    monkeypatch.setattr(a.crawler, "fetch_robots", lambda url, timeout=10: {
        "url": url, "status": 200, "bytes": 0, "ai_crawlers": {}, "blocked_ai_crawlers": [],
        "allowed_ai_crawlers": [], "rule_count": 0, "sitemaps": [], "rules": []})
    monkeypatch.setattr(a, "_tls_profile", lambda url, timeout=10: {})
    monkeypatch.setattr(a, "fetch_vitals", lambda url: None)
    monkeypatch.setattr(a, "fetch_query_visibility", lambda url: None)
    monkeypatch.setattr(a, "fetch_backlinks", lambda url: None)
    srv = dashboard.create_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


@pytest.fixture()
def browser():
    from playwright.sync_api import sync_playwright
    exe = _find_chromium()
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe \
                else pw.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # no usable browser binary in this environment
            pytest.skip(f"no Chromium available: {exc}")
        yield b
        b.close()


def test_operator_flow_in_real_browser(live_dashboard, browser):
    from ope.registry import registered_check_ids
    page = browser.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(live_dashboard, wait_until="networkidle")
    assert "OMNI Command Center" in page.content()

    # Run a real audit through the UI.
    page.fill("#omni-url", "http://acme.example/")
    page.click("#omni-run-btn")
    page.wait_for_selector("#omni-status.omni-status--ok", timeout=20000)

    # Overview reflects the run and derives the registry count (no literal).
    page.click('.omni-nav button[data-tab="overview"]')
    ov = page.inner_text("#sec-overview").lower()
    assert "omni health" in ov and "total checks" in ov
    assert str(len(registered_check_ids())) in ov  # dynamic registry total

    # Modules (all 20) and evidence-first finding detail.
    page.click('.omni-nav button[data-tab="modules"]')
    page.wait_for_selector("#sec-modules .omni-mod")
    assert page.locator("#sec-modules .omni-mod").count() == 20

    page.click('.omni-nav button[data-tab="findings"]')
    page.wait_for_selector("#sec-findings details.omni-det")
    page.eval_on_selector("#sec-findings details.omni-det", "d => d.open = true")
    fdet = page.inner_text("#sec-findings")
    assert "Evidence (why OPE concluded this)" in fdet and "source:" in fdet

    # Canonical graph rendered with one node per module.
    page.click('.omni-nav button[data-tab="graph"]')
    page.wait_for_selector("#sec-graph svg circle")
    assert page.locator("#sec-graph svg circle").count() == 20

    # AI reasoning is honestly unavailable without a key.
    page.click('.omni-nav button[data-tab="reasoning"]')
    page.click("#sec-reasoning button")
    page.wait_for_function(
        "document.querySelector('#reasoning-out') && document.querySelector('#reasoning-out').textContent.length > 0",
        timeout=10000)
    assert "unavailable" in page.inner_text("#sec-reasoning").lower()

    # JSON export downloads from the exact run.
    page.click('.omni-nav button[data-tab="exports"]')
    page.wait_for_selector("#sec-exports button")
    with page.expect_download(timeout=10000) as di:
        page.click('#sec-exports button:has-text("JSON")')
    assert di.value.suggested_filename.endswith(".json")

    # Narrow viewport: the document must not overflow horizontally.
    page.set_viewport_size({"width": 375, "height": 800})
    page.click('.omni-nav button[data-tab="overview"]')
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 2

    assert [e for e in errors if "favicon" not in e] == []  # no JS console errors
