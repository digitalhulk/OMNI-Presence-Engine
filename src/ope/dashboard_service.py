"""Audit service layer for the OMNI Command Center dashboard.

This is a thin orchestration/presentation boundary over the canonical OPE
engine. It performs NO scoring, dependency, root-cause, remediation, or
evidence logic of its own — every value it returns comes straight from
``audit()`` → ``normalize_result()``, ``orchestrator.audit_targets()``,
``history.load_runs()``, ``providers.provider_status()``, and the canonical
report renderers. The dashboard server and UI consume this module; there is
exactly one source of diagnostic truth (the engine).
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from typing import Any

from . import history as history_module
from .audit import audit, markdown_report
from .orchestrator import audit_targets
from .providers import provider_status
from .report_html import html_report

REPORT_SCHEMA = "evidence-diagnostic-v1"


def run_single_audit(
    url: str,
    *,
    timeout: int = 15,
    fetch_subresources: bool = True,
    record_history: bool = True,
) -> dict[str, Any]:
    """Run the real single-target pipeline and return the canonical result.

    Raises ValueError for an unsafe/invalid target (SSRF, DNS, scheme) exactly
    as the engine does — the caller maps that to a clean client error. The
    engine validates the URL internally; this adds no separate validation and
    no fabricated fields.
    """
    raw = audit(url, timeout=timeout, fetch_subresources=fetch_subresources)
    if record_history:
        history_module.attach_baseline(raw)
    result = _normalize(raw)
    if record_history:
        history_module.save_run(result)
    return result


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    # Imported lazily so a mock of audit()/normalize_result() in tests is honored.
    from .engine import normalize_result
    return normalize_result(raw)


def run_multi_audit(urls: list[str], *, timeout: int = 15, fetch_subresources: bool = True, max_workers: int = 4) -> dict[str, Any]:
    """Delegate to the canonical multi-target orchestrator."""
    return audit_targets(
        urls, timeout=timeout, fetch_subresources=fetch_subresources,
        max_workers=max_workers, record_history=True,
    )


def get_providers() -> list[dict[str, Any]]:
    """Optional-provider capability discovery (no network, no secrets)."""
    return provider_status()


def get_history(target: str) -> list[dict[str, Any]]:
    """Locally stored run snapshots for a target, newest first (may be empty)."""
    return history_module.load_runs(target)


def dependency_graph_view() -> dict[str, Any]:
    """The declared 20-module dependency graph for visualization (structure only)."""
    from .dependency_graph import MODULE_DEPENDENCIES, TOPOLOGICAL_ORDER_NUMBERS
    nodes = [{"module": name.split("-", 1)[0], "name": name} for name in MODULE_DEPENDENCIES]
    edges = [
        {"from": dep.split("-", 1)[0], "to": name.split("-", 1)[0]}
        for name, deps in MODULE_DEPENDENCIES.items()
        for dep in deps
    ]
    return {"nodes": nodes, "edges": edges, "topological_order": list(TOPOLOGICAL_ORDER_NUMBERS)}


_EXPORTS = {
    "json": ("application/json", "report.json"),
    "md": ("text/markdown; charset=utf-8", "report.md"),
    "txt": ("text/plain; charset=utf-8", "report.txt"),
    "html": ("text/html; charset=utf-8", "report.html"),
}


def export_result(result: dict[str, Any], fmt: str) -> tuple[bytes, str, str]:
    """Render one export format from a canonical result.

    All formats are derived from the same result object, so they represent
    the same diagnosis (presentation differs, conclusions do not).
    """
    if fmt == "json":
        body = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    elif fmt in ("md", "txt"):
        body = markdown_report(result)
    elif fmt == "html":
        body = html_report(result)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    content_type, filename = _EXPORTS[fmt]
    return body.encode("utf-8"), content_type, filename


def _manifest(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": result.get("target"),
        "final_url": result.get("final_url"),
        "run_id": result.get("run_id"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ope_version": result.get("version"),
        "engine_contract": result.get("engine_contract"),
        "report_schema": REPORT_SCHEMA,
        "health": result.get("health"),
        "providers": [
            {"provider": p["provider"], "configured": p["configured"]}
            for p in provider_status()
        ],
        "files": ["report.json", "report.md", "report.txt", "report.html", "manifest.json"],
    }


class ExportUnavailable(RuntimeError):
    """Raised when an optional export (PDF/PNG) needs a dependency that is absent."""


def _load_playwright() -> Any:
    """Import the optional headless-browser backend, or raise ExportUnavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # ImportError, or a partial install
        raise ExportUnavailable(
            "PDF/PNG export requires the optional 'playwright' dependency. "
            "Install it with: pip install 'omni-presence-engine[report]' && playwright install chromium"
        ) from exc
    return sync_playwright


def export_visual(result: dict[str, Any], fmt: str) -> tuple[bytes, str, str]:
    """Render the canonical HTML report to a real PDF or PNG via headless Chromium.

    This is an explicitly optional capability: when the browser backend is not
    installed it raises :class:`ExportUnavailable` with a clear message rather
    than degrading to a fake artifact (a PDF is a real PDF, not renamed HTML).
    """
    if fmt not in ("pdf", "png"):
        raise ValueError(f"Unsupported visual export format: {fmt}")
    import pathlib
    import tempfile

    sync_playwright = _load_playwright()
    html = html_report(result)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = pathlib.Path(tmp) / "report.html"
            html_path.write_text(html, encoding="utf-8")
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                try:
                    page = browser.new_page()
                    page.goto(html_path.as_uri(), wait_until="load")
                    if fmt == "pdf":
                        data = page.pdf(format="A4", print_background=True)
                        return data, "application/pdf", "report.pdf"
                    data = page.screenshot(full_page=True)
                    return data, "image/png", "report.png"
                finally:
                    browser.close()
    except ExportUnavailable:
        raise
    except Exception as exc:
        # A missing/mismatched browser binary is an optional-dependency problem,
        # not a server error: report it as unavailable, never as a fake file.
        raise ExportUnavailable(
            f"PDF/PNG export backend is not usable ({type(exc).__name__}). "
            "Ensure a headless browser is installed: playwright install chromium"
        ) from exc


def export_bundle(result: dict[str, Any]) -> tuple[bytes, str, str]:
    """A single offline ZIP bundle of every text export for the same run.

    The bundle is deterministic in structure and corresponds to exactly one
    audit run (identified in manifest.json). PDF/PNG are intentionally not
    included here — they are an optional, browser-dependent export handled
    separately with an explicit fallback.
    """
    buffer = io.BytesIO()
    manifest = _manifest(result)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for fmt in ("json", "md", "txt", "html"):
            body, _, filename = export_result(result, fmt)
            archive.writestr(filename, body)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    return buffer.getvalue(), "application/zip", "omni-report-bundle.zip"
