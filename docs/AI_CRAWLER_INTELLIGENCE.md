# AI Crawler Intelligence

OPE treats crawler policy as **observed evidence**, not as a ranking verdict.

## Scope

The AI crawler capability records deterministic robots.txt observations for known AI/search crawlers and exposes them through the existing OPE evidence/check pipeline.

### Covered crawler identities

- GPTBot
- OAI-SearchBot
- ChatGPT-User
- ClaudeBot
- PerplexityBot
- Google-Extended
- GoogleOther
- Applebot-Extended
- Amazonbot
- FacebookBot
- CCBot
- anthropic-ai
- Bytespider
- cohere-ai

## Evidence flow

```text
robots.txt
   ↓
parse directives
   ↓
resolve effective User-agent group
   ↓
resolve Allow/Disallow for target path
   ↓
AI crawler access matrix
   ↓
OPE evidence
   ↓
04-crawl / 10-ai-search checks
   ↓
FAIL / PASS / UNKNOWN
```

## Truth rules

- `ALLOW` and `BLOCK` are observations of the published robots policy for the analyzed path.
- A crawler being allowed does **not** mean a search engine will crawl, index, cite, or rank the site.
- A crawler being blocked does **not** by itself prove an SEO or AI-search penalty.
- Missing/unavailable robots evidence remains `UNKNOWN` rather than being treated as `PASS`.
- OPE keeps its own execution/scoring semantics; external GEO scoring weights are not imported.

## Implementation

- `src/ope/crawler.py` — deterministic robots parser, effective-access resolver, AI crawler matrix, safe fetch limits.
- `src/ope/audit_pipeline.py` — binds robots observations to existing `04-crawl.robots_access`, `04-crawl.bot_access`, and `10-ai-search.agent_accessibility` registry checks.
- `tests/test_crawler.py` — parser, wildcard/specific-agent precedence, and observed matrix coverage.
- `tests/test_audit_pipeline.py` — evidence binding, blocked crawler failures, and missing-observation UNKNOWN semantics.

## Security boundaries

The robots fetch is restricted to absolute HTTP(S) targets and rejects DNS resolutions to private, loopback, link-local, reserved, multicast, or unspecified addresses. The response is capped at 256 KiB.

## External capability provenance

This capability is an OPE-native adaptation of useful AI-crawler intelligence patterns found during OSS research. The external repository architecture, orchestration, scoring authority, and reporting system are not imported into OPE.
