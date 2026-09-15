"""Tests for the Hostinger shared-hosting deployment layer.

These lock the properties that matter for this deployment target:

* the web/API contract is honest (runtime_unavailable is never an audit),
* the PHP shell is *generated from* the canonical Python contract, so it cannot
  drift from the engine,
* the package duplicates no engine logic and ships no fixture data,
* the built package is complete, PHP-valid, and hardened.

PHP-level behaviour is exercised through the real ``php`` binary when one is
available, and skipped cleanly otherwise so the core gate never depends on it.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from ope import web_contract as wc

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "deploy" / "hostinger"
RENDERER = REPO_ROOT / "web" / "assets" / "ope-render.js"

PHP = shutil.which("php")
requires_php = pytest.mark.skipif(PHP is None, reason="php binary not available")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    """Build the deployment package once into a temp directory."""
    from scripts.build_hostinger import build

    out = tmp_path_factory.mktemp("hostinger") / "pkg"
    return build(out)


# --- contract honesty ------------------------------------------------------

def test_runtime_unavailable_is_not_an_audit():
    p = wc.runtime_unavailable_payload()
    assert p["status"] == "runtime_unavailable"
    assert p["runtime"] == "hostinger_shared"
    assert p["engine"] == "python"
    assert p["live_execution"] is False
    # It must carry nothing that could be mistaken for a result.
    for forbidden in ("result", "health", "score", "findings", "modules", "checks", "summary"):
        assert forbidden not in p


def test_shared_runtime_never_claims_live_execution():
    assert wc.runtime_supports_live_execution(wc.RUNTIME_PYTHON) is True
    assert wc.runtime_supports_live_execution(wc.RUNTIME_HOSTINGER_SHARED) is False
    caps = wc.engine_capabilities(wc.RUNTIME_HOSTINGER_SHARED)
    assert caps["live_execution"] is False


def test_capabilities_come_from_the_canonical_registry():
    from ope.dependency_graph import MODULE_DEPENDENCIES
    from ope.registry import registered_check_ids

    caps = wc.engine_capabilities()
    assert caps["module_count"] == len(MODULE_DEPENDENCIES) == 20
    assert caps["check_count"] == len(registered_check_ids()) == 136


def test_success_payload_embeds_canonical_result_verbatim():
    result = {"target": "https://example.com", "version": "9.9.9", "health": 42.0, "checks": {"a": 1}}
    p = wc.success_payload(result)
    assert p["status"] == "success"
    assert p["live_execution"] is True
    assert p["result"] is result  # not copied, not reshaped
    assert p["target"] == "https://example.com"
    assert p["engine_version"] == "9.9.9"


def test_invalid_request_is_distinct_from_runtime_unavailable():
    p = wc.invalid_request_payload("bad url")
    assert p["status"] == "invalid_request"
    assert p["status"] != wc.STATUS_RUNTIME_UNAVAILABLE
    assert p["live_execution"] is False


# --- generated PHP cannot drift from Python -------------------------------

def test_generated_php_matches_python_contract(built: Path):
    php = (built / "api" / "contract.php").read_text(encoding="utf-8")
    assert "DO NOT EDIT" in php
    for literal in (
        wc.WEB_CONTRACT_VERSION,
        wc.RUNTIME_HOSTINGER_SHARED,
        wc.RUNTIME_PYTHON,
        wc.STATUS_RUNTIME_UNAVAILABLE,
        wc.STATUS_SUCCESS,
        wc.STATUS_INVALID_REQUEST,
        wc.RUNTIME_UNAVAILABLE_MESSAGE,
    ):
        assert literal in php, f"generated PHP is missing canonical literal: {literal}"
    caps = wc.engine_capabilities()
    assert f"const OPE_MODULE_COUNT = {caps['module_count']};" in php
    assert f"const OPE_CHECK_COUNT = {caps['check_count']};" in php


def test_package_never_hardcodes_counts_outside_generated_contract(built: Path):
    """136/20 may only appear in the generated contract, never hand-written."""
    for path in sorted(built.rglob("*.php")):
        if path.name == "contract.php":
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b136\b", text), f"hardcoded check count in {path.name}"


# --- no duplicated engine logic, no fixture data --------------------------

def test_no_audit_logic_in_the_php_shell(built: Path):
    """The shell must not reimplement scoring/cascade/root-cause/registry."""
    banned = ("cascade_blocked", "find_root_causes", "module_score_basis",
              "health_basis =", "normalize_result", "remediation_plan =")
    for path in sorted(built.rglob("*.php")):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} appears to duplicate engine logic: {token}"


def test_package_ships_no_fixture_or_sample_data(built: Path):
    names = [p.name for p in built.rglob("*")]
    assert "sample-report.js" not in names
    assert "sample-report.html" not in names
    # The published-report index ships empty — nothing is presented as real.
    index = json.loads((built / "reports" / "index.json").read_text(encoding="utf-8"))
    assert index == {"reports": []}


def test_no_dangerous_php_constructs(built: Path):
    banned = ("eval(", "shell_exec", "proc_open", "passthru", "system(",
              "popen(", "assert(", "create_function", "extract(", "$$")
    for path in sorted(built.rglob("*.php")):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} uses dangerous construct: {token}"


def test_no_secrets_in_the_package(built: Path):
    assert not (built / "config.php").exists(), "operator config must never be built/shipped"
    assert (built / "config.example.php").exists()
    example = (built / "config.example.php").read_text(encoding="utf-8")
    # The example must only show commented-out placeholders.
    assert "define('OPE_API_BASE'" not in example.replace("// define('OPE_API_BASE'", "")


# --- package completeness + hardening ------------------------------------

def test_package_is_complete(built: Path):
    for rel in ("index.php", ".htaccess", "config.example.php", "BUILD.json",
                "api/contract.php", "api/_bootstrap.php", "api/health.php",
                "api/status.php", "api/audit.php",
                "assets/css/rawblock.css", "assets/js/ope-render.js",
                "reports/index.json"):
        assert (built / rel).is_file(), f"missing {rel}"


def test_assets_are_byte_identical_to_canonical_sources(built: Path):
    """Assets are copied, never re-authored — one source of truth."""
    assert (built / "assets" / "js" / "ope-render.js").read_bytes() == RENDERER.read_bytes()
    assert (built / "assets" / "css" / "rawblock.css").read_bytes() == \
        (REPO_ROOT / "design" / "rawblock.css").read_bytes()


def test_build_manifest_reports_the_runtime_truthfully(built: Path):
    manifest = json.loads((built / "BUILD.json").read_text(encoding="utf-8"))
    assert manifest["runtime"] == wc.RUNTIME_HOSTINGER_SHARED
    assert manifest["live_execution"] is False
    assert manifest["engine"] == "python"


def test_htaccess_hardening(built: Path):
    ht = (built / ".htaccess").read_text(encoding="utf-8")
    assert "Options -Indexes" in ht
    for denied in (r"\.git", "config.php", "^api/_", r"\.(py|pyc"):
        assert denied in ht, f".htaccess does not deny {denied}"
    assert "RewriteCond %{HTTPS} !=on" in ht          # forces HTTPS
    assert "Content-Security-Policy" in ht
    assert "X-Content-Type-Options" in ht
    assert "Strict-Transport-Security" in ht
    # Report permalinks must not permit traversal.
    assert "^report/([A-Za-z0-9._-]+)/?$" in ht


# --- renderer safety ------------------------------------------------------

def test_renderer_escapes_and_holds_no_engine_logic():
    js = RENDERER.read_text(encoding="utf-8")
    assert "function esc(" in js
    # Ban IMPLEMENTATIONS of engine logic (naming the Python functions in a
    # comment is legitimate documentation).
    for banned in ("eval(", "new Function", "function cascade", "function findRootCause",
                   "function computeHealth", "function score("):
        assert banned not in js, f"renderer must not contain {banned}"
    # Values reach the DOM only via esc(); spot-check the target interpolation.
    assert "esc(r.target)" in js


def test_renderer_is_valid_javascript():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    subprocess.run([node, "--check", str(RENDERER)], check=True, capture_output=True)


def test_web_index_uses_the_shared_renderer_not_a_fork():
    html = (REPO_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "assets/ope-render.js" in html
    # The old inline copy must be gone (no second renderer in the repo).
    assert "function findingCard(" not in html
    assert "window.OPERender.render" in html
    # Fixture data must be labelled wherever it is displayed.
    assert "development fixture" in html.lower()


# --- real PHP execution ---------------------------------------------------

@requires_php
def test_audit_endpoint_rejects_wrong_method(php_server: str):
    status, payload = _request(php_server, "/api/audit.php", method="GET")
    assert status == 405
    assert payload["status"] == "invalid_request"


@requires_php
def test_all_php_files_lint(built: Path):
    for path in sorted(built.rglob("*.php")):
        proc = subprocess.run([str(PHP), "-l", str(path)], capture_output=True, text=True)
        assert proc.returncode == 0, f"{path.name}: {proc.stdout}{proc.stderr}"


@pytest.fixture(scope="module")
def php_server(built: Path):
    """Serve the built package with PHP's built-in server.

    The endpoints are exercised over real HTTP rather than through the PHP CLI:
    `php -q file.php` does not populate `php://input` the way a web SAPI does,
    so request-body handling can only be tested honestly through a server.
    """
    if PHP is None:
        pytest.skip("php binary not available")
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    proc = subprocess.Popen(
        [str(PHP), "-S", f"127.0.0.1:{port}", "-t", str(built)],
        cwd=str(built), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base + "/api/health.php", timeout=1).read()
            break
        except Exception:
            if proc.poll() is not None:
                pytest.skip("php built-in server failed to start")
            time.sleep(0.2)
    else:  # pragma: no cover - server never came up
        proc.terminate()
        pytest.skip("php built-in server did not become ready")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def _request(base: str, path: str, *, method: str = "GET", body: str | None = None,
             content_type: str | None = None) -> tuple[int, dict]:
    """Make one HTTP request to the PHP server and decode the JSON envelope."""
    data = body.encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if content_type:
        req.add_header("Content-Type", content_type)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status, raw = resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry the envelope
        status, raw = exc.code, exc.read().decode()
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, {"_raw": raw}


@requires_php
def test_health_endpoint_reports_shared_runtime(php_server: str):
    _, payload = _request(php_server, "/api/health.php")
    assert payload["status"] == "ok"
    assert payload["runtime"] == wc.RUNTIME_HOSTINGER_SHARED
    assert payload["live_execution"] is False
    assert payload["engine"] == "python"


@requires_php
def test_status_endpoint_exposes_canonical_counts(php_server: str):
    _, payload = _request(php_server, "/api/status.php")
    caps = wc.engine_capabilities()
    assert payload["module_count"] == caps["module_count"]
    assert payload["check_count"] == caps["check_count"]
    assert payload["capabilities"]["live_audit"] is False
    assert payload["capabilities"]["render_existing_reports"] is True
    assert payload["reports"] == []


@requires_php
def test_audit_endpoint_reports_runtime_unavailable_for_valid_url(php_server: str):
    status, payload = _request(
        php_server, "/api/audit.php", method="POST",
        body=json.dumps({"url": "https://example.com"}),
        content_type="application/json",
    )
    assert status == 503  # capability absent, not a server fault
    assert payload["status"] == "runtime_unavailable"
    assert payload["live_execution"] is False
    assert payload["target"] == "https://example.com"
    assert "result" not in payload  # never a fabricated audit


@requires_php
@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",           # loopback
    "http://169.254.169.254/",     # cloud metadata
    "http://10.0.0.1/",            # RFC1918
    "http://192.168.1.1/",         # RFC1918
    "http://100.64.0.1/",          # CGNAT
    "http://localhost/",           # local name
    "http://[::1]/",               # IPv6 loopback
])
def test_audit_endpoint_refuses_ssrf_targets(php_server: str, url: str):
    _, payload = _request(
        php_server, "/api/audit.php", method="POST",
        body=json.dumps({"url": url}), content_type="application/json",
    )
    assert payload["status"] == "invalid_request", f"{url} was not refused"
    assert "restricted" in payload["message"].lower()


@requires_php
@pytest.mark.parametrize("body,expect", [
    ('{"url":"ftp://example.com/"}', "scheme"),
    ('{"url":"http://user:pw@example.com/"}', "credentials"),
    ('{"url":""}', "required"),
    ('{"url":123}', "string"),
    ('{}', "string"),
    ('not json at all', None),
])
def test_audit_endpoint_rejects_bad_requests(php_server: str, body: str, expect: str | None):
    _, payload = _request(
        php_server, "/api/audit.php", method="POST", body=body,
        content_type="application/json",
    )
    assert payload["status"] == "invalid_request"
    if expect:
        assert expect in payload["message"].lower()


@requires_php
def test_audit_endpoint_rejects_non_json_content_type(php_server: str):
    """A browser form post cannot drive the API (stateless CSRF defence)."""
    _, payload = _request(
        php_server, "/api/audit.php", method="POST", body="url=http://example.com",
        content_type="application/x-www-form-urlencoded",
    )
    assert payload["status"] == "invalid_request"


@requires_php
def test_audit_endpoint_rejects_oversized_body(php_server: str):
    big = json.dumps({"url": "https://example.com/" + "a" * 20000})
    _, payload = _request(
        php_server, "/api/audit.php", method="POST", body=big,
        content_type="application/json",
    )
    assert payload["status"] == "invalid_request"


@requires_php
def test_index_renders_runtime_unavailable_banner(php_server: str):
    with urllib.request.urlopen(php_server + "/index.php", timeout=20) as resp:
        html = resp.read().decode()
    assert "OMNI-PRESENCE ENGINE" in html
    assert "LIVE ENGINE — UNAVAILABLE ON THIS RUNTIME" in html
    assert "RUN OPE AUDIT" in html
    assert "assets/js/ope-render.js" in html
    # Honest, non-alarming: no "broken"/"error"/"failed" framing of the runtime.
    banner = html[html.find("OPE ENGINE RUNTIME"):html.find("AUDIT CONSOLE")]
    for alarming in ("broken", "failure", "fatal", "crashed"):
        assert alarming not in banner.lower()
    # The engine is described as healthy.
    assert "engine itself is healthy" in banner.lower()
    # No fabricated numbers anywhere in the shell before a report is loaded.
    assert "OMNI HEALTH" not in html
