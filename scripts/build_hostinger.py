"""Assemble the uploadable OPE Hostinger shared-hosting package.

Why a build step instead of a committed folder: the package's design system, its
client-side renderer and its API contract all have exactly one canonical home in
this repository. The build copies/derives them rather than letting a second copy
live in ``deploy/`` and drift:

    design/rawblock.css          -> assets/css/rawblock.css
    web/assets/ope-render.js     -> assets/js/ope-render.js
    src/ope/web_contract.py      -> api/contract.php   (generated constants)
    src/ope/registry.py          -> module/check counts baked into contract.php

Everything else (index.php, api/*.php, .htaccess, config.example.php) is copied
verbatim from ``deploy/hostinger/``.

Usage::

    python scripts/build_hostinger.py                   # -> dist/hostinger/
    python scripts/build_hostinger.py --zip             # also dist/ope-hostinger.zip
    python scripts/build_hostinger.py --out /tmp/pkg

The output contains no secrets: ``config.php`` is never generated or copied, only
``config.example.php``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "deploy" / "hostinger"
CANONICAL_CSS = REPO_ROOT / "design" / "rawblock.css"
CANONICAL_RENDERER = REPO_ROOT / "web" / "assets" / "ope-render.js"

#: Files copied verbatim from the template directory.
VERBATIM = (
    "index.php",
    ".htaccess",
    "config.example.php",
    "README.md",
    "api/_bootstrap.php",
    "api/health.php",
    "api/status.php",
    "api/audit.php",
)


def _php_literal(value: Any) -> str:
    """Render a Python scalar as a PHP literal (json_encode is valid PHP syntax)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def render_contract_php() -> str:
    """Generate api/contract.php from the canonical Python contract.

    Every constant here is read from ``ope.web_contract`` / the canonical
    registry, so the PHP shell and the Python engine can never disagree about
    the envelope, the runtime names, or how many checks exist.
    """
    from ope import web_contract as wc
    from ope.dependency_graph import MODULE_DEPENDENCIES

    caps = wc.engine_capabilities(wc.RUNTIME_HOSTINGER_SHARED)
    modules = sorted(MODULE_DEPENDENCIES)

    consts = {
        "OPE_WEB_CONTRACT_VERSION": wc.WEB_CONTRACT_VERSION,
        "OPE_ENGINE": wc.ENGINE,
        "OPE_ENGINE_VERSION": caps["engine_version"],
        "OPE_RUNTIME_PYTHON": wc.RUNTIME_PYTHON,
        "OPE_RUNTIME_HOSTINGER_SHARED": wc.RUNTIME_HOSTINGER_SHARED,
        "OPE_STATUS_SUCCESS": wc.STATUS_SUCCESS,
        "OPE_STATUS_RUNTIME_UNAVAILABLE": wc.STATUS_RUNTIME_UNAVAILABLE,
        "OPE_STATUS_INVALID_REQUEST": wc.STATUS_INVALID_REQUEST,
        "OPE_STATUS_ERROR": wc.STATUS_ERROR,
        "OPE_RUNTIME_UNAVAILABLE_MESSAGE": wc.RUNTIME_UNAVAILABLE_MESSAGE,
        "OPE_MODULE_COUNT": caps["module_count"],
        "OPE_CHECK_COUNT": caps["check_count"],
    }
    lines = [
        "<?php",
        "/**",
        " * OPE web contract constants — GENERATED FILE, DO NOT EDIT.",
        " *",
        " * Produced by scripts/build_hostinger.py from src/ope/web_contract.py and the",
        " * canonical check registry. Edit the Python source and rebuild; editing this",
        " * file by hand would let the PHP shell drift from the engine contract.",
        " */",
        "",
        "declare(strict_types=1);",
        "",
    ]
    for name, value in consts.items():
        lines.append(f"const {name} = {_php_literal(value)};")
    lines += [
        "",
        "/** Canonical module keys, from ope.dependency_graph.MODULE_DEPENDENCIES. */",
        "const OPE_MODULES = [",
    ]
    lines += [f"    {json.dumps(m, ensure_ascii=False)}," for m in modules]
    lines += [
        "];",
        "",
        "/**",
        " * The honest response when this runtime cannot execute the Python engine.",
        " * Mirrors ope.web_contract.runtime_unavailable_payload().",
        " */",
        "function ope_runtime_unavailable_payload(",
        "    string $runtime = OPE_RUNTIME_HOSTINGER_SHARED,",
        "    ?string $target = null,",
        "    string $message = OPE_RUNTIME_UNAVAILABLE_MESSAGE",
        "): array {",
        "    $payload = [",
        "        'status' => OPE_STATUS_RUNTIME_UNAVAILABLE,",
        "        'runtime' => $runtime,",
        "        'engine' => OPE_ENGINE,",
        "        'live_execution' => false,",
        "        'message' => $message,",
        "        'web_contract' => OPE_WEB_CONTRACT_VERSION,",
        "    ];",
        "    if ($target !== null && $target !== '') {",
        "        $payload['target'] = $target;",
        "    }",
        "    return $payload;",
        "}",
        "",
        "/**",
        " * A rejected request (unsafe or malformed input) — never an audit result.",
        " * Mirrors ope.web_contract.invalid_request_payload().",
        " */",
        "function ope_invalid_request_payload(",
        "    string $message,",
        "    string $runtime = OPE_RUNTIME_HOSTINGER_SHARED",
        "): array {",
        "    return [",
        "        'status' => OPE_STATUS_INVALID_REQUEST,",
        "        'runtime' => $runtime,",
        "        'engine' => OPE_ENGINE,",
        "        'live_execution' => false,",
        "        'message' => $message,",
        "        'web_contract' => OPE_WEB_CONTRACT_VERSION,",
        "    ];",
        "}",
        "",
    ]
    return "\n".join(lines)


def build(out_dir: Path, *, make_zip: bool = False) -> Path:
    """Assemble the package into *out_dir*, returning the directory."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "api").mkdir(parents=True)
    (out_dir / "assets" / "css").mkdir(parents=True)
    (out_dir / "assets" / "js").mkdir(parents=True)
    (out_dir / "reports").mkdir(parents=True)

    for rel in VERBATIM:
        src = TEMPLATE_DIR / rel
        if not src.is_file():
            raise FileNotFoundError(f"missing template file: {src}")
        shutil.copy2(src, out_dir / rel)

    # Canonical assets — copied, never re-authored.
    shutil.copy2(CANONICAL_CSS, out_dir / "assets" / "css" / "rawblock.css")
    shutil.copy2(CANONICAL_RENDERER, out_dir / "assets" / "js" / "ope-render.js")

    # Generated contract, derived from the Python source of truth.
    (out_dir / "api" / "contract.php").write_text(render_contract_php(), encoding="utf-8")

    # An empty, valid report index so /api/status works before anything is published.
    (out_dir / "reports" / "index.json").write_text(
        json.dumps({"reports": []}, indent=2) + "\n", encoding="utf-8"
    )
    # Keep the directory listing-proof even if .htaccess is not honoured.
    (out_dir / "reports" / "index.html").write_text(
        "<!doctype html><title>OPE reports</title><p>No report selected. "
        '<a href="../index.php">Back to the Command Center</a>.\n',
        encoding="utf-8",
    )

    from ope import web_contract as wc

    caps = wc.engine_capabilities(wc.RUNTIME_HOSTINGER_SHARED)
    (out_dir / "BUILD.json").write_text(
        json.dumps(
            {
                "package": "ope-hostinger-shared",
                "web_contract": caps["web_contract"],
                "engine": caps["engine"],
                "engine_version": caps["engine_version"],
                "runtime": caps["runtime"],
                "live_execution": caps["live_execution"],
                "module_count": caps["module_count"],
                "check_count": caps["check_count"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if make_zip:
        archive = out_dir.parent / "ope-hostinger.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(out_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(out_dir))
        print(f"zip: {archive}")
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the OPE Hostinger deployment package")
    parser.add_argument("--out", default=str(REPO_ROOT / "dist" / "hostinger"), help="output directory")
    parser.add_argument("--zip", action="store_true", dest="make_zip", help="also write dist/ope-hostinger.zip")
    args = parser.parse_args()
    out = build(Path(args.out), make_zip=args.make_zip)
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"built: {out} ({files} files)")
    print("upload the CONTENTS of this directory into your domain's public_html root")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
