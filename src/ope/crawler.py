from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any

from . import USER_AGENT
from .url import validate_url_strict

AI_CRAWLERS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "GoogleOther",
    "Applebot-Extended",
    "Amazonbot",
    "FacebookBot",
    "CCBot",
    "anthropic-ai",
    "Bytespider",
    "cohere-ai",
)

MAX_ROBOTS_BYTES = 256 * 1024


@dataclass(frozen=True)
class RobotsRule:
    user_agent: str
    directive: str
    value: str
    line: int


def robots_url(page_url: str) -> str:
    parsed = urllib.parse.urlparse(validate_url_strict(page_url))
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


def parse_robots(text: str) -> list[RobotsRule]:
    rules: list[RobotsRule] = []
    agents: list[str] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            agents = [value]
        elif key in {"allow", "disallow", "crawl-delay", "sitemap"} and agents:
            for agent in agents:
                rules.append(RobotsRule(agent, key, value, number))
    return rules


def _rules_for_agent(rules: list[RobotsRule], agent: str) -> list[RobotsRule]:
    exact = [r for r in rules if r.user_agent.lower() == agent.lower()]
    wildcard = [r for r in rules if r.user_agent == "*"]
    return exact or wildcard


def effective_access(rules: list[RobotsRule], agent: str, path: str = "/") -> str:
    candidates = [r for r in _rules_for_agent(rules, agent) if r.directive in {"allow", "disallow"}]
    matches = [r for r in candidates if r.value == "" or path.startswith(r.value)]
    if not matches:
        return "ALLOW"
    best = max(matches, key=lambda r: (len(r.value), r.directive == "allow"))
    return "BLOCK" if best.directive == "disallow" else "ALLOW"


def analyze_robots(text: str, path: str = "/") -> dict[str, Any]:
    rules = parse_robots(text)
    crawler_access = {agent: effective_access(rules, agent, path) for agent in AI_CRAWLERS}
    return {
        "ai_crawlers": crawler_access,
        "blocked_ai_crawlers": [a for a, state in crawler_access.items() if state == "BLOCK"],
        "allowed_ai_crawlers": [a for a, state in crawler_access.items() if state == "ALLOW"],
        "rule_count": len(rules),
        "sitemaps": [r.value for r in rules if r.directive == "sitemap"],
        "rules": [r.__dict__ for r in rules],
    }


def fetch_robots(page_url: str, timeout: int = 10) -> dict[str, Any]:
    from .net import open_url
    target = robots_url(page_url)
    try:
        # SSRF-safe: validates the target, re-validates every redirect hop, and
        # pins the validated resolution for direct connections.
        with open_url(target, timeout=max(1, min(timeout, 30)), headers={"User-Agent": USER_AGENT}) as response:
            body = response.read(MAX_ROBOTS_BYTES + 1)
            if len(body) > MAX_ROBOTS_BYTES:
                raise ValueError(f"robots.txt exceeds OPE safety limit of {MAX_ROBOTS_BYTES} bytes")
            text = body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            result = analyze_robots(text)
            result.update({"url": target, "status": response.status, "bytes": len(body), "error": None})
            return result
    except Exception as exc:
        return {"url": target, "status": None, "bytes": 0, "error": str(exc), "ai_crawlers": {}, "blocked_ai_crawlers": [], "allowed_ai_crawlers": [], "rule_count": 0, "sitemaps": [], "rules": []}
