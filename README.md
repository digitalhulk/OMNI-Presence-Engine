# 🛣️ SADAK SE UTHA KR ⭐ STAR BNA DUNGA

# OMNI-PRESENCE ENGINE

> **One Engine. Every Platform. Real Growth.**
>
> **ZERO → EXIST → DISCOVER → UNDERSTAND → TRUST → RANK → ANSWER → CITE → RECOMMEND → CONVERT → RETAIN → AUTHORITY → DOMINANCE**

OPE is an evidence-driven **digital presence engineering system** for legitimate people, brands, businesses, products, services, websites, applications and digital properties.

It connects infrastructure, code, crawlability, indexability, semantics, content, media, search, AI search, authority, local presence, UX, accessibility, performance, security, language, analytics and conversion into one dependency-aware architecture.

> **Sadak se uthana nahi — system se STAR banana hai.** 🚀

---

## 🚀 QUICK START

```bash
git clone https://github.com/digitalhulk/OMNI-Presence-Engine.git
cd OMNI-Presence-Engine
python3 -m pip install -e .
ope setup
ope audit https://YOUR-WEBSITE.com --markdown
```

Setup stores project configuration locally at `~/.ope/config.json`.

Available output modes:

```bash
ope audit https://example.com --json
ope audit https://example.com --markdown
ope audit https://example.com --html reports/audit.report.html
```

Audit options:

```bash
ope audit https://example.com --no-subresources   # skip fetching linked CSS/JS
ope audit https://example.com --no-history        # do not read or write local run history
ope audit https://example.com --timeout 30
```

Run history is stored locally at `~/.ope/runs` (override the base directory with `OPE_HOME`) and is what lets the engine detect regressions between runs.

Optional external evidence — set the environment variable and the matching checks upgrade from `UNKNOWN` to measured evidence; nothing is fabricated when it is absent:

| Variable | Unlocks |
| --- | --- |
| `OPE_PAGESPEED_API_KEY` | Core Web Vitals (LCP, FCP, CLS, TBT, INP) from Google PageSpeed Insights |
| `OPENROUTER_API_KEY` | Optional advisory reasoning layer over deterministic evidence |

Legacy `ope-audit` remains supported.

**Security:** API keys, OAuth tokens, cookies, passwords, private documents, production credentials and payment credentials must remain local or in a secret manager. Never commit real secrets.

---

# 🧠 ENGINE STATUS — VERIFIED FOUNDATION

The engine executes this pipeline end to end:

```text
PROJECT CONFIG
     ↓
OBSERVATION — HTTP · TLS · ROBOTS/AI-CRAWLERS · HTML · JSON-LD · CSS/JS · CITABILITY
     ↓
OPTIONAL EXTERNAL EVIDENCE — PAGESPEED INSIGHTS (KEY-GATED)
     ↓
RUN HISTORY BASELINE — REGRESSION / ANOMALY COMPARISON
     ↓
136-CHECK REGISTRY EXECUTION (DEPENDENCY-AWARE MODULE RUNNER)
     ↓
EXECUTION STATE — PASS · FAIL · UNKNOWN · N/A · BLOCKED
     ↓
EVIDENCE + ROOT-CAUSE NORMALIZATION
     ↓
PRIORITY / SCORING PRIMITIVES
     ↓
JSON / MARKDOWN / RAWBLOCK HTML REPORTING
     ↓
RUN RECORDED FOR THE NEXT COMPARISON
```

### Implemented on `main`

- **EvidenceRecord** — source, target, value, timestamp, confidence and provenance.
- **Evidence normalization** — bounded confidence and stable machine-readable records.
- **RootCauseFinding** — structured symptom, evidence, layer, dependency, root cause, impact, remediation, validation and regression-guard fields.
- **Canonical engine contract** — `evidence-diagnostic-v1`.
- **Root-cause normalizer** — missing root causes remain explicit hypotheses.
- **Priority primitive** — bounded remediation priority, not a fake ranking score.
- **Module scoring semantics** — `UNKNOWN`, `BLOCKED` and unexecuted states do not receive fabricated scores.
- **EvidenceProviderRegistry / Observation** — provider-backed evidence can be registered without coupling providers to the core engine.
- **Setup + audit CLI** — project configuration and executable website audits.
- **JSON / Markdown / RawBlock HTML reporting**.
- **Machine-readable audit/finding schemas**.
- **CI test foundation** and executable contract tests.
- **Dependency-aware `ModuleRunner`** executing the 136-check, 20-module registry.
- **Executable, validated dependency graph** — the 20-module dependency graph from `schemas/dependency-graph-v1.md` is encoded in `dependency_graph.py` as the single executable source of module dependencies, with deterministic topological ordering. Graph construction rejects malformed topology: dangling edges and cycles fail explicitly (iterative three-state DFS), never silently accepted.
- **Evidence-safe BLOCKED cascade** — a module is derived `BLOCKED` when it transitively depends on a failed module, but `BLOCKED` never replaces direct evidence: a module's own `FAIL` stays `FAIL` and its own `N/A` stays `N/A` (only `PASS`/`UNKNOWN` are converted; `UNKNOWN`/`N/A` upstream never cause a block). Cascade derives module status only and never fabricates check-level evidence. Graph-based root-cause traversal traces each BLOCKED module back to the upstream FAIL modules that caused it, never inventing a cause where none exists.
- **Graph-based scoring** — `global_health()` traverses the dependency graph in topological order so parallel branches (Content/Media, Search/AI, Authority/Local, UX tier) do not penalize each other. BLOCKED modules return `None` scores.
- **Score explainability** — every module carries a `score_basis` (derivation method, check tallies, evidence-weighted pass/total, and `blocked_by` root causes for BLOCKED modules) and the output carries a `health_basis` (the per-module topological rollup with upstream confidence). Scores are never opaque numbers — the number and its provenance come from a single computation and can never disagree.
- **Evidence-backed check bindings** — all 136 registry checks are bound; 115 execute deterministically against observations, 3 are finding-record checks, and 18 return `UNKNOWN` with a specific reason naming the missing external API or service.
- **Deterministic observation surface** — HTTP/TLS handshake, robots.txt and AI-crawler access, JSON-LD entity graph, HTML structure and accessibility signals, linked CSS/JS measurement, DNS/TTFB timing, content citability.
- **Local run history** — regression and anomaly comparison between runs of the same target.
- **Optional external evidence** — PageSpeed Insights (Core Web Vitals) and an advisory OpenRouter reasoning layer, both credential-gated.

### Check coverage by module

Bound checks per module — **136 of 136 total** (18 require external APIs and return `UNKNOWN` with a reason):

| Module | Bound | Module | Bound |
| --- | --- | --- | --- |
| 01-entity | 5/5 | 11-authority | 7/7 |
| 02-infrastructure | 5/5 | 12-local | 7/7 |
| 03-code | 8/8 | 13-ux | 6/6 |
| 04-crawl | 5/5 | 14-accessibility | 8/8 |
| 05-index | 5/5 | 15-performance | 11/11 |
| 06-semantics | 6/6 | 16-security | 10/10 |
| 07-content | 8/8 | 17-language | 7/7 |
| 08-media | 6/6 | 18-analytics | 7/7 |
| 09-search | 6/6 | 19-conversion | 6/6 |
| 10-ai-search | 6/6 | 20-continuous-optimization | 7/7 |

Every check executes — deterministic checks return `PASS`, `FAIL`, or `N/A`; external-evidence checks return `UNKNOWN` with a human-readable reason naming the missing API. Run this to print the live numbers rather than trusting this table:

```bash
python3 -c "from ope.registry import CHECKS; from ope.audit_pipeline import AUDIT_BINDINGS; print(len(AUDIT_BINDINGS), '/', len(CHECKS))"
```

### Not yet claimed as implemented

The following are architectural targets and are **not represented as active implementation on `main` until verified there**:

- provider adapters for external data sources beyond PageSpeed Insights (18 checks are bound but return `UNKNOWN` until their APIs are configured)
- orchestration and scheduling across multiple targets

This distinction is intentional: **documentation must never claim code that is not actually present.**

---

# 🔌 EVIDENCE-FIRST ARCHITECTURE

OPE separates **what was observed** from **what the engine concludes**.

```text
SOURCE / PROVIDER
      ↓
OBSERVATION
      ↓
EVIDENCE RECORD
      ↓
CHECK / AUDIT
      ↓
EXECUTION STATE
      ↓
FINDING
      ↓
ROOT-CAUSE ANALYSIS
      ↓
PRIORITY
      ↓
REMEDIATION
      ↓
VALIDATION
      ↓
REGRESSION GUARD
```

Material observations should retain:

- source
- target
- observed timestamp
- value
- confidence
- provenance

OPE separates evidence states such as `FACT`, `OBSERVED`, `ESTIMATE`, `HYPOTHESIS`, `EXPERIMENT` and `DEPRECATED` from execution states such as `PASS`, `FAIL`, `UNKNOWN`, `BLOCKED` and `N/A`.

**UNKNOWN ≠ PASS.** Missing evidence must never silently become success.

---

# 🔥 ROOT-CAUSE ENGINE

```text
SYMPTOM
 ↓
AFFECTED LAYER
 ↓
DEPENDENCY
 ↓
EVIDENCE
 ↓
ROOT CAUSE
 ↓
IMPACT
 ↓
PRIORITY
 ↓
REMEDIATION
 ↓
VALIDATION
 ↓
REGRESSION GUARD
```

If evidence does not establish a root cause, OPE labels the result as a **hypothesis** rather than presenting an assumption as fact.

---

# 📊 PRIORITY ≠ RANKING SCORE

OPE does **not** pretend to calculate a universal Google/Bing/AI ranking score.

```text
PRIORITY = IMPACT × CONFIDENCE × URGENCY × FIXABILITY
```

The result is bounded to `0–100` and is a **remediation decision signal**, not a claim about any search engine's ranking algorithm.

---

# 🧠 20-MODULE TARGET ARCHITECTURE

| # | Module | Engineering Scope |
|---:|---|---|
| 01 | **Entity** | Identity, ownership, identifiers, relationships |
| 02 | **Infrastructure** | DNS, hosting, CDN, server, APIs |
| 03 | **Code** | HTML, DOM, CSS, JS, metadata, structured data |
| 04 | **Crawl** | Robots, sitemap, bot access, discovery |
| 05 | **Index** | Canonical, status, duplication, indexability |
| 06 | **Semantics** | Entities, topics, intent, taxonomy, relationships |
| 07 | **Content** | Intent, completeness, originality, accuracy, freshness |
| 08 | **Media** | Image, video, audio, graphics, accessibility, performance |
| 09 | **Search** | SEO, local, image, video, news, shopping |
| 10 | **AI Search** | AEO, GEO, LLMO, answers, citations, agents |
| 11 | **Authority** | Backlinks, mentions, PR, reviews, expertise, reputation |
| 12 | **Local** | Maps, GBP, NAP, service areas, local trust |
| 13 | **UX** | Navigation, hierarchy, mobile, interaction, conversion friction |
| 14 | **Accessibility** | WCAG, keyboard, focus, semantics, contrast, media |
| 15 | **Performance** | Network, loading, rendering, frames, runtime, page weight |
| 16 | **Security** | HTTPS, TLS, headers, CSP, cookies, auth, abuse controls |
| 17 | **Language** | Locale, translation, hreflang, multilingual intent |
| 18 | **Analytics** | GA4, search, logs, CRM, attribution, revenue |
| 19 | **Conversion** | CTA, leads, sales, funnel, revenue |
| 20 | **Continuous Optimization** | Observe → Diagnose → Fix → Validate → Monitor |

**Important:** this is the target system architecture. A module being listed here does not imply that every check inside it is currently executable.

---

# 🌐 DISCOVERY + SEARCH + AI PRESENCE

OPE treats digital presence as a connected retrieval system rather than only traditional SEO.

```text
DIGITAL ENTITY
      ↓
IDENTITY + SEMANTICS
      ↓
CONTENT + MEDIA
      ↓
CRAWL + INDEX
      ↓
SEARCH RETRIEVAL
      ↓
AI RETRIEVAL / GROUNDING
      ↓
ANSWER
      ↓
CITATION
      ↓
RECOMMENDATION
      ↓
HUMAN ACTION
```

The architecture covers:

- search ecosystems
- SEO
- AEO
- GEO
- LLMO
- local discovery
- image/video discovery
- AI search and answer systems
- browser/agent accessibility
- authority and third-party references

OPE is designed around durable evidence and entity understanding—not ranking tricks or prompt hacks.

---

# 🧪 EXECUTION VISION

The long-term control loop is:

```text
DISCOVER → INVENTORY → AUDIT → EVIDENCE → NORMALIZE
→ DIAGNOSE → PRIORITIZE → PLAN → IMPLEMENT → VALIDATE → MONITOR → ↺
```

The complete system is intended to produce:

- entity and technical inventory
- evidence set
- module execution states
- root-cause findings
- confidence and provenance
- remediation priorities
- implementation plans
- validation criteria
- regression guards
- monitoring requirements
- historical comparisons

Only capabilities actually backed by executable code should be reported as implemented.

---

# 🎨 RAW//BLOCK UI

OPE uses the **RawBlock** brutalist design language: structural layouts, thick borders, zero rounded corners, high-contrast primitives and explicit information hierarchy.

```text
design/DESIGN.md       → canonical UI specification
design/rawblock.css    → design tokens + components
design/showcase.html   → component showcase
tests/                 → executable contract coverage
src/ope/               → executable engine + CLI
```

Generate a standalone HTML report:

```bash
ope audit https://example.com --html reports/audit.report.html
```

Generated reports are gitignored.

---

# 🏗️ REPOSITORY MAP

```text
schemas/       → machine-readable contracts
docs/          → module and system specifications
automation/    → execution, adapters, monitoring targets (specs)
integrations/  → external evidence providers (specs + pagespeed/openrouter)
design/        → RawBlock design system
web/           → dashboard + report viewer
src/ope/       → executable engine and CLI
tests/         → executable contract coverage
scripts/       → report generation and utilities
```

---

# 🛡️ ENGINEERING RULES

- **Root cause over patch fix.**
- **Evidence over assumptions.**
- **UNKNOWN is never silently converted to PASS.**
- **Provider estimates remain estimates.**
- **Hypotheses are explicitly labeled.**
- **Human experience over vanity scores.**
- **Machine readability without sacrificing humans.**
- **Preserve approved visual/function experience during performance optimization.**
- **Provider metrics remain attributed to their provider.**
- **Destructive changes require explicit approval.**
- **Secrets never enter Git.**
- **No fake AI tricks.**
- **No acronym worship.**

---

# 🔐 PRIVATE BY DESIGN

This repository is **PRIVATE**.

Never commit API keys, OAuth tokens, cookies, session credentials, customer secrets, private analytics exports or production credentials.

Use environment variables or a deployment secret manager.

Client-specific implementations, credentials and private business data must remain outside the core repository unless explicitly intended as generic, sanitized examples.

---

# 💥 THE CRAZY SLOGAN

<div align="center">

## 🛣️ **SADAK SE UTHA KR STAR BNA DUNGA.** ⭐

### **From Invisible → Discoverable → Trusted → Recommended → Unstoppable.**

**Search Everywhere.**  
**Visible Everywhere.**  
**Trusted Everywhere.**  
**Chosen When It Matters.**

### `Your digital journey. Our engineering system. Limitless possibilities.`

</div>

---

# 🎯 MISSION

Build a durable engineering system that turns digital properties from **unknown → discoverable → understandable → trusted → retrievable → recommendable → convertible**, using evidence instead of assumptions.

## VISION

> **One engine. Every layer. Every legitimate digital property.**
>
> **No patch fixes. No fake scores. No fake certainty. Build the system. Prove the result.**

---

## 📌 CURRENT RELEASE

**Version:** `0.10.0`  
**Stage:** Evidence-driven executable foundation — 136/136 checks bound, dependency graph active, explainable scoring integrated  
**Contract:** `evidence-diagnostic-v1`

The repository is intentionally being built in verified increments. **If a capability is not executable and validated on `main`, it is documented as a target—not as completed engineering.**
