"""Regenerate web/sample-report.js from a real audit run against a fixed page."""
import json, tempfile
import ope.audit as A
from ope.audit import audit, Response
from ope.engine import normalize_result
from ope import history

PAGE = """<!DOCTYPE html><html lang="en"><head><title>StarBrand — Digital Presence</title>
<meta charset="utf-8">
<meta name="description" content="StarBrand builds evidence-driven digital presence for growing businesses across search and AI answers.">
<link rel="canonical" href="https://starbrand.example.com/">
<link rel="stylesheet" href="/assets/site.css">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"StarBrand","description":"StarBrand builds evidence-driven digital presence for growing businesses across search and AI answers.","sameAs":["https://linkedin.com/company/starbrand","https://instagram.com/starbrand"],"identifier":"SB-001"}</script>
</head><body><header></header><nav><a href="/work">Work</a><a href="/pricing">Pricing</a></nav>
<main><h1>StarBrand</h1>
<h2>What does StarBrand do?</h2>
<p>StarBrand is a digital presence studio. We audit infrastructure, code, crawlability, semantics and AI-search readiness, then fix what the evidence says is broken. Every recommendation is traced to an observation, and every fix is validated against the same measurement that found the problem.</p>
<h2>How does the audit work?</h2>
<p>An audit fetches the page, reads robots.txt, inspects the TLS handshake, parses structured data, measures linked stylesheets and scripts, and records the result so the next run can detect regressions. Nothing is estimated; a check with no evidence reports UNKNOWN instead of guessing.</p>
<img src="/hero.png" alt="StarBrand team at work">
<img src="/chart.png" alt="">
<form><input type="email" placeholder="Email"></form>
<button>Book an audit</button></main>
<footer><a href="/privacy">Privacy</a><a href="/terms">Terms</a></footer></body></html>"""

A._request = lambda url, timeout=15: Response(
    "https://starbrand.example.com/", 200,
    {"content-type": "text/html; charset=utf-8", "strict-transport-security": "max-age=31536000",
     "x-content-type-options": "nosniff", "cf-ray": "8a1b2c3d4e5f", "server": "cloudflare"},
    ["sid=abc; Path=/; Secure; HttpOnly; SameSite=Lax"], PAGE.encode(), "utf-8", 18.4, 236.0)
A.crawler.fetch_robots = lambda url, timeout=10: {
    "url": "https://starbrand.example.com/robots.txt", "status": 200, "error": None, "rule_count": 4,
    "ai_crawlers": {"GPTBot": "ALLOW", "OAI-SearchBot": "ALLOW", "ClaudeBot": "BLOCK", "PerplexityBot": "ALLOW"},
    "blocked_ai_crawlers": ["ClaudeBot"], "allowed_ai_crawlers": ["GPTBot", "OAI-SearchBot", "PerplexityBot"],
    "sitemaps": ["https://starbrand.example.com/sitemap.xml"], "rules": []}
A._tls_profile = lambda url, timeout=10: {"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384", "days_until_expiry": 68, "error": None}
A._fetch_subresources = lambda page, css, js, timeout=10: {
    "discovered_requests": 1, "fetched_requests": 1, "css_bytes": 88_412, "js_bytes": 0,
    "third_party_hosts": [], "css_text": "a{transition:color .2s} button{outline:none}"}

store = tempfile.mkdtemp()
raw = audit("https://starbrand.example.com")
raw["run_id"] = "ope-1726190400"
raw["started_at"] = 1726190400
raw["completed_at"] = 1726190402.4
history.attach_baseline(raw, store)
result = normalize_result(raw)

banner = ("/* Sample OPE audit result — generated from a real `ope audit --json` run\n"
          "   against a fixed example page, so this file always matches the shape the\n"
          "   engine actually emits. Regenerate with scripts/gen_sample_report.py. */\n")
body = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
open("web/sample-report.js", "w", encoding="utf-8").write(f"{banner}window.OPE_SAMPLE_REPORT = {body};\n")

totals = {}
for c in result["checks"].values():
    totals[c["status"]] = totals.get(c["status"], 0) + 1
print("status totals:", totals, "| contract:", result["engine_contract"], "| version:", result["version"])
