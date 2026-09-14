from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit, markdown_report
from .engine import normalize_result
from .report_html import write_html_report

CONFIG_PATH = Path.home() / ".ope" / "config.json"


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    return input(f"{label}{suffix}: ").strip() or default


def setup_project() -> int:
    print("\nOPE Project Setup\n=================")
    name = prompt("Project/entity name")
    url = prompt("Canonical website URL")
    country = prompt("Country", "IN")
    market = prompt("Market")
    language = prompt("Primary language", "en")
    business_type = prompt("Business type", "business")
    goals = prompt("Goals (comma-separated)", "discoverability,trust,conversion")
    sources = prompt("Data source paths/URLs (comma-separated)")
    if not name or not url:
        print("OPE setup requires a project name and website URL.", file=sys.stderr)
        return 2
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "project_name": name, "website_url": url, "country": country,
        "market": market, "language": language, "business_type": business_type,
        "goals": [x.strip() for x in goals.split(",") if x.strip()],
        "data_sources": [x.strip() for x in sources.split(",") if x.strip()],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nSaved local OPE configuration: {CONFIG_PATH}")
    print("No credentials or secrets are written by this wizard.")
    print(f"Next: ope audit {url} --markdown")
    return 0


def audit_command(args: argparse.Namespace) -> int:
    try:
        result = normalize_result(audit(args.url, timeout=args.timeout, fetch_subresources=not args.no_subresources))
    except Exception as exc:
        print(f"OPE audit failed: {exc}", file=sys.stderr)
        return 2
    if args.html:
        path = write_html_report(result, args.html)
        print(f"RawBlock HTML report written: {path}", file=sys.stderr)
    if args.markdown:
        print(markdown_report(result))
    elif not args.html:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ope", description="OPE evidence-first digital presence engine")
    sub = parser.add_subparsers(dest="command")
    setup = sub.add_parser("setup", help="create local project configuration")
    setup.set_defaults(handler=lambda _args: setup_project())
    audit_parser = sub.add_parser("audit", help="run an evidence-first web audit")
    audit_parser.add_argument("url")
    audit_parser.add_argument("--json", action="store_true", dest="as_json")
    audit_parser.add_argument("--markdown", action="store_true")
    audit_parser.add_argument("--html", metavar="PATH", help="write a RawBlock-branded standalone HTML audit report")
    audit_parser.add_argument("--timeout", type=int, default=15)
    audit_parser.add_argument("--no-subresources", action="store_true", help="skip fetching linked CSS/JS (faster; leaves cost and stylesheet checks UNKNOWN)")
    audit_parser.set_defaults(handler=audit_command)
    return parser


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] not in {"setup", "audit", "-h", "--help"}:
        argv = ["audit", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
