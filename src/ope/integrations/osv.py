"""Dependency vulnerability scanning via OSV.dev (free, credential-less).

OSV (https://osv.dev) is Google's open vulnerability database with a stable,
public, key-free query API. This adapter detects client-side JavaScript
libraries whose exact name+version is embedded in a versioned CDN URL
(cdnjs / jsDelivr / unpkg) and asks OSV whether that version has known
vulnerabilities.

Scope is deliberately honest: only client-side libraries whose version is
unambiguously present in a CDN URL are checked — server-side dependencies are
invisible to a black-box web audit and are never guessed. The network scan is
opt-in (OPE_DEPENDENCY_SCAN) so a default audit stays hermetic; detection of the
libraries themselves is local and always available.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .. import USER_AGENT

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_DEPENDENCIES = 25  # bound how many libraries a single audit will look up

# A version token: digits and dots, optionally a pre-release/build suffix.
_VERSION = r"\d+(?:\.\d+){1,3}(?:-[0-9A-Za-z.]+)?"
# Versioned CDN URL patterns that embed an exact npm package name + version.
_CDN_PATTERNS = (
    re.compile(r"cdnjs\.cloudflare\.com/ajax/libs/(?P<name>[^/]+)/(?P<version>" + _VERSION + r")/"),
    re.compile(r"cdn\.jsdelivr\.net/npm/(?P<name>@?[^@/]+(?:/[^@/]+)?)@(?P<version>" + _VERSION + r")"),
    re.compile(r"unpkg\.com/(?P<name>@?[^@/]+(?:/[^@/]+)?)@(?P<version>" + _VERSION + r")"),
)


def detect_dependencies(script_srcs: list[str]) -> list[dict[str, str]]:
    """Extract {name, version, ecosystem, source} for versioned CDN libraries.

    Only unambiguous name@version / name/version CDN forms are returned; a
    script URL without an embedded version yields nothing (never a guess).
    Deduplicated and deterministically ordered.
    """
    found: dict[tuple[str, str], dict[str, str]] = {}
    for src in script_srcs or []:
        if not isinstance(src, str):
            continue
        for pattern in _CDN_PATTERNS:
            match = pattern.search(src)
            if match:
                name = match.group("name").strip("/")
                version = match.group("version")
                if name and version:
                    found[(name, version)] = {
                        "name": name,
                        "version": version,
                        "ecosystem": "npm",
                        "source": src,
                    }
                break
    return [found[key] for key in sorted(found)]


@dataclass(frozen=True)
class OSVConfig:
    base_url: str = "https://api.osv.dev"
    timeout: int = 15


class OSVError(RuntimeError):
    pass


class OSVClient:
    """Minimal stdlib-only OSV.dev query client (no credentials)."""

    def __init__(self, config: OSVConfig | None = None) -> None:
        self.config = config or OSVConfig()

    def query(self, name: str, version: str, ecosystem: str = "npm") -> list[dict[str, Any]]:
        payload = {"version": version, "package": {"name": name, "ecosystem": ecosystem}}
        request = urllib.request.Request(
            f"{self.config.base_url}/v1/query",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, min(self.config.timeout, 30))) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise OSVError(f"OSV response exceeds {MAX_RESPONSE_BYTES}-byte safety limit")
        except urllib.error.HTTPError as exc:
            raise OSVError(f"OSV HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise OSVError(f"OSV request failed: {exc.reason}") from exc
        try:
            data = json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise OSVError("OSV returned an invalid JSON response") from exc
        if not isinstance(data, dict):
            raise OSVError("OSV response JSON must be an object")
        vulns = data.get("vulns")
        return vulns if isinstance(vulns, list) else []


def scan_dependencies(dependencies: list[dict[str, str]], client: OSVClient | None = None) -> dict[str, Any] | None:
    """Query OSV for each detected dependency; None when nothing can be stated.

    Returns None when there are no detectable dependencies, or when OSV cannot
    be reached (so the check reports UNKNOWN rather than a fabricated clean
    result). On success returns the checked libraries and any vulnerable ones
    (with their OSV vulnerability ids) — never invented severities.
    """
    if not dependencies:
        return None
    active = client or OSVClient()
    vulnerable: list[dict[str, Any]] = []
    checked: list[dict[str, str]] = []
    try:
        for dep in dependencies[:MAX_DEPENDENCIES]:
            vulns = active.query(dep["name"], dep["version"], dep.get("ecosystem", "npm"))
            checked.append({"name": dep["name"], "version": dep["version"]})
            if vulns:
                ids = [str(v.get("id")) for v in vulns if isinstance(v, dict) and v.get("id")]
                vulnerable.append({"name": dep["name"], "version": dep["version"], "vulnerability_ids": ids})
    except OSVError:
        return None
    return {"checked": len(checked), "libraries": checked, "vulnerable": vulnerable, "source": "osv.dev"}


def scan_from_env(script_srcs: list[str], client: OSVClient | None = None) -> dict[str, Any] | None:
    """Opt-in entry point: scan only when OPE_DEPENDENCY_SCAN is set."""
    if not str(os.getenv("OPE_DEPENDENCY_SCAN", "")).strip():
        return None
    return scan_dependencies(detect_dependencies(script_srcs), client)
