from __future__ import annotations

import ipaddress
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

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


def _safe_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("OPE accepts only absolute HTTP(S) URLs with a hostname")
    host = parsed.hostname.rstrip(".")
    try:
        addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for target: {host}") from exc
    if not addresses:
        raise ValueError(f"No address resolved for target: {host}")
    if any(a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast or a.is_unspecified for a in addresses):
        raise ValueError("Robots target resolves to a restricted network address")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def robots_url(page_url: str) -> str:
    parsed = urllib.parse.urlparse(_safe_url(page_url))
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
    target = robots_url(page_url)
    request = urllib.request.Request(target, headers={"User-Agent": "OPE-Audit/0.1"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=max(1, min(timeout, 30))) as response:
            body = response.read(MAX_ROBOTS_BYTES + 1)
            if len(body) > MAX_ROBOTS_BYTES:
                raise ValueError(f"robots.txt exceeds OPE safety limit of {MAX_ROBOTS_BYTES} bytes")
            text = body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            result = analyze_robots(text)
            result.update({"url": target, "status": response.status, "bytes": len(body), "error": None})
            return result
    except Exception as exc:
        return {"url": target, "status": None, "bytes": 0, "error": str(exc), "ai_crawlers": {}, "blocked_ai_crawlers": [], "allowed_ai_crawlers": [], "rule_count": 0, "sitemaps": [], "rules": []}
