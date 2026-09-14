from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import history
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
        browser_profiles = None
        if getattr(args, "browser_desktop_only", False):
            browser_profiles = ["DESKTOP"]
        elif getattr(args, "browser_mobile_only", False):
            browser_profiles = ["MOBILE"]
        raw = audit(args.url, timeout=args.timeout, fetch_subresources=not args.no_subresources, browser=getattr(args, "browser", False), browser_timeout=getattr(args, "browser_timeout", 30), browser_profiles=browser_profiles)
        if not args.no_history:
            history.attach_baseline(raw)
        result = normalize_result(raw)
        if not args.no_history:
            history.save_run(result)
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


def site_audit_command(args: argparse.Namespace) -> int:
    from .site_audit import SiteAuditConfig
    from .site_audit import site_audit as run_site_audit

    cfg = SiteAuditConfig(
        max_pages=args.max_pages, max_depth=args.max_depth,
        timeout=args.timeout, delay=args.delay,
        allow_subdomains=args.allow_subdomains,
        fetch_sitemaps=not args.no_sitemaps,
        fetch_robots=not args.no_robots,
    )
    try:
        result = run_site_audit(args.url, config=cfg)
    except Exception as exc:
        print(f"OPE site-audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


def performance_audit_command(args: argparse.Namespace) -> int:
    from .browser import DeviceProfile
    from .performance_audit import PerformanceAuditConfig
    from .performance_audit import performance_audit as run_perf_audit

    profiles: list[DeviceProfile] = []
    if args.mobile_only:
        profiles = [DeviceProfile.MOBILE]
    elif args.desktop_only:
        profiles = [DeviceProfile.DESKTOP]
    else:
        profiles = [DeviceProfile.DESKTOP, DeviceProfile.MOBILE]

    cfg = PerformanceAuditConfig(
        profiles=profiles,
        timeout_ms=args.timeout * 1000,
        navigation_timeout_ms=args.timeout * 1000,
        capture_screenshot=not args.no_screenshot,
    )
    try:
        result = run_perf_audit(args.url, config=cfg)
    except Exception as exc:
        print(f"OPE performance-audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
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
    audit_parser.add_argument("--no-history", action="store_true", help="do not read or write the local run history used for regression comparison")
    audit_parser.add_argument("--browser", action="store_true", help="run browser-based performance audit alongside HTTP audit")
    audit_parser.add_argument("--browser-timeout", type=int, default=30, help="browser timeout in seconds (default 30)")
    audit_parser.add_argument("--browser-desktop-only", action="store_true", help="browser audit: skip mobile profile")
    audit_parser.add_argument("--browser-mobile-only", action="store_true", help="browser audit: skip desktop profile")
    audit_parser.set_defaults(handler=audit_command)
    sa = sub.add_parser("site-audit", help="run a multi-page site-level audit")
    sa.add_argument("url")
    sa.add_argument("--max-pages", type=int, default=200)
    sa.add_argument("--max-depth", type=int, default=10)
    sa.add_argument("--timeout", type=int, default=15)
    sa.add_argument("--delay", type=float, default=0.5)
    sa.add_argument("--allow-subdomains", action="store_true")
    sa.add_argument("--no-sitemaps", action="store_true", help="skip sitemap discovery")
    sa.add_argument("--no-robots", action="store_true", help="skip robots.txt fetch")
    sa.set_defaults(handler=site_audit_command)
    pa = sub.add_parser("performance-audit", help="run browser-based performance audit")
    pa.add_argument("url")
    pa.add_argument("--timeout", type=int, default=30, help="browser timeout in seconds")
    pa.add_argument("--desktop-only", action="store_true", help="skip mobile profile")
    pa.add_argument("--mobile-only", action="store_true", help="skip desktop profile")
    pa.add_argument("--no-screenshot", action="store_true", help="skip screenshot capture")
    pa.set_defaults(handler=performance_audit_command)
    return parser


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] not in {"setup", "audit", "site-audit", "performance-audit", "-h", "--help"}:
        argv = ["audit", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
