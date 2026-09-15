from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import history
from .audit import audit, markdown_report
from .engine import normalize_result
from .planner import diagnosis_markdown
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
        if args.html:
            path = write_html_report(result, args.html)
            print(f"RawBlock HTML report written: {path}", file=sys.stderr)
        if args.markdown:
            print(markdown_report(result))
        elif not args.html:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"OPE audit failed: {exc}", file=sys.stderr)
        return 2
    return 0


def site_audit_command(args: argparse.Namespace) -> int:
    from .engine import normalize_site_result
    from .report_html_site import write_site_html_report
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
        raw = run_site_audit(args.url, config=cfg)
        raw_dict = raw.to_dict()
        if not args.no_history:
            history.attach_baseline(raw_dict)
        result = normalize_site_result(raw_dict)
        if not args.no_history:
            history.save_run(result)
        if args.html:
            path = write_site_html_report(result, args.html)
            print(f"RawBlock HTML site-audit report written: {path}", file=sys.stderr)
        if args.markdown:
            print(site_audit_markdown_report(result))
        elif not args.html:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"OPE site-audit failed: {exc}", file=sys.stderr)
        return 2
    return 0


def site_audit_markdown_report(result: dict[str, Any]) -> str:
    """Generate a markdown summary from a normalized site audit result."""
    lines = [
        f"# OPE Site Audit — {result.get('target', 'unknown')}",
        "",
        f"**Status:** `{result.get('status', 'UNKNOWN')}`  ",
        f"**Pages crawled:** `{result.get('crawl_summary', {}).get('pages_crawled', 0) if isinstance(result.get('crawl_summary'), dict) else 0}`  ",
        f"**Findings:** `{len(result.get('findings', []))}`",
        "",
    ]
    lines += diagnosis_markdown(result)
    findings = result.get("findings", [])
    if findings:
        lines += ["## Findings", ""]
        for f in sorted(findings, key=lambda x: x.get("priority", 0), reverse=True):
            lines += [
                f"### {f.get('id', '?')} — {f.get('severity', '?').upper()} — Priority {f.get('priority', 0)}",
                f"**Module:** {f.get('module', '?')}",
                f"**Symptom:** {f.get('symptom', '?')}",
                "",
            ]
            if f.get("root_cause"):
                lines.append(f"**Root cause:** {f['root_cause']}")
            if f.get("remediation"):
                lines += ["", "**Remediation:**"] + [f"- {x}" for x in f["remediation"]]
            lines.append("")
    else:
        lines.append("No site-level findings were generated.")
    return "\n".join(lines)


def performance_audit_command(args: argparse.Namespace) -> int:
    from .browser import DeviceProfile
    from .engine import normalize_performance_result
    from .performance_audit import PerformanceAuditConfig
    from .performance_audit import performance_audit as run_perf_audit
    from .report_html_performance import write_performance_html_report

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
        raw = run_perf_audit(args.url, config=cfg)
        result = normalize_performance_result(raw.to_dict())
        if args.html:
            path = write_performance_html_report(result, args.html)
            print(f"RawBlock HTML performance-audit report written: {path}", file=sys.stderr)
        if args.markdown:
            print(performance_audit_markdown_report(result))
        elif not args.html:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"OPE performance-audit failed: {exc}", file=sys.stderr)
        return 2
    return 0


def performance_audit_markdown_report(result: dict[str, Any]) -> str:
    """Generate a markdown summary from a normalized performance audit result."""
    lines = [
        f"# OPE Performance Audit — {result.get('target', 'unknown')}",
        "",
        f"**Status:** `{result.get('status', 'UNKNOWN')}`  ",
        f"**Duration:** `{result.get('duration_s', 0):.1f}s`  ",
        f"**Findings:** `{len(result.get('findings', []))}`",
        "",
    ]
    report = result.get("performance_report")
    if isinstance(report, dict):
        vitals = report.get("vitals_summary")
        if isinstance(vitals, dict) and vitals:
            lines += ["## Core Web Vitals", ""]
            for profile, metrics in vitals.items():
                if not isinstance(metrics, dict):
                    continue
                lines.append(f"### {profile}")
                lines.append("")
                lines.append("| Metric | Value | Rating |")
                lines.append("|--------|-------|--------|")
                for metric, data in metrics.items():
                    if not isinstance(data, dict):
                        continue
                    val = data.get("value_ms") or data.get("value", "?")
                    unit = "ms" if "value_ms" in data else ""
                    lines.append(f"| {metric.upper()} | {val}{unit} | {data.get('rating', '?')} |")
                lines.append("")

    lines += diagnosis_markdown(result)
    findings = result.get("findings", [])
    if findings:
        lines += ["## Findings", ""]
        for f in sorted(findings, key=lambda x: x.get("priority", 0), reverse=True):
            lines += [
                f"### {f.get('id', '?')} — {f.get('severity', '?').upper()} — Priority {f.get('priority', 0)}",
                f"**Symptom:** {f.get('symptom', '?')}",
                "",
            ]
            if f.get("root_cause"):
                lines.append(f"**Root cause:** {f['root_cause']}")
            lines.append("")
    else:
        lines.append("No performance findings were generated.")
    return "\n".join(lines)


def multi_audit_command(args: argparse.Namespace) -> int:
    from .orchestrator import audit_targets, multi_audit_markdown
    try:
        report = audit_targets(
            list(args.urls),
            timeout=args.timeout,
            fetch_subresources=not args.no_subresources,
            max_workers=args.max_workers,
            record_history=not args.no_history,
        )
        if args.markdown:
            print(multi_audit_markdown(report))
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"OPE multi-audit failed: {exc}", file=sys.stderr)
        return 2
    # A batch where every target failed is itself a failure; otherwise success
    # (individual target failures are reported per-target in the output).
    if report["summary"]["target_count"] and report["summary"]["succeeded"] == 0:
        return 2
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
    sa.add_argument("--markdown", action="store_true", help="output a markdown summary instead of JSON")
    sa.add_argument("--html", metavar="PATH", help="write a RawBlock-branded standalone HTML site-audit report")
    sa.add_argument("--max-pages", type=int, default=200)
    sa.add_argument("--max-depth", type=int, default=10)
    sa.add_argument("--timeout", type=int, default=15)
    sa.add_argument("--delay", type=float, default=0.5)
    sa.add_argument("--allow-subdomains", action="store_true")
    sa.add_argument("--no-sitemaps", action="store_true", help="skip sitemap discovery")
    sa.add_argument("--no-robots", action="store_true", help="skip robots.txt fetch")
    sa.add_argument("--no-history", action="store_true", help="do not read or write the local run history")
    sa.set_defaults(handler=site_audit_command)
    pa = sub.add_parser("performance-audit", help="run browser-based performance audit")
    pa.add_argument("url")
    pa.add_argument("--timeout", type=int, default=30, help="browser timeout in seconds")
    pa.add_argument("--desktop-only", action="store_true", help="skip mobile profile")
    pa.add_argument("--mobile-only", action="store_true", help="skip desktop profile")
    pa.add_argument("--no-screenshot", action="store_true", help="skip screenshot capture")
    pa.add_argument("--markdown", action="store_true", help="output a markdown summary instead of JSON")
    pa.add_argument("--html", metavar="PATH", help="write a RawBlock-branded standalone HTML performance-audit report")
    pa.set_defaults(handler=performance_audit_command)
    ma = sub.add_parser("multi-audit", help="audit multiple targets with bounded concurrency")
    ma.add_argument("urls", nargs="+", help="one or more target URLs")
    ma.add_argument("--markdown", action="store_true", help="output an aggregate markdown summary instead of JSON")
    ma.add_argument("--timeout", type=int, default=15)
    ma.add_argument("--no-subresources", action="store_true", help="skip fetching linked CSS/JS")
    ma.add_argument("--max-workers", type=int, default=4, help="max concurrent target audits (default 4)")
    ma.add_argument("--no-history", action="store_true", help="do not read or write local run history")
    ma.set_defaults(handler=multi_audit_command)
    return parser


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] not in {"setup", "audit", "site-audit", "performance-audit", "multi-audit", "-h", "--help"}:
        argv = ["audit", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
