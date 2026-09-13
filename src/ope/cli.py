from __future__ import annotations

import argparse
import json
import sys
from .audit import audit, markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(prog="ope-audit", description="OPE evidence-first web audit")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    try:
        result = audit(args.url, timeout=args.timeout)
    except Exception as exc:
        print(f"OPE audit failed: {exc}", file=sys.stderr)
        return 2
    if args.markdown:
        print(markdown_report(result))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
