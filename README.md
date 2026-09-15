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

Audit several targets at once, or list what optional providers are configured:

```bash
ope multi-audit https://a.com https://b.com https://c.com --markdown
ope multi-audit https://a.com https://b.com --max-workers 4 --json
ope providers            # which optional providers are configured + what they upgrade
```

### OMNI Command Center (local dashboard)

```bash
ope dashboard                       # serves http://127.0.0.1:8787/ (local only)
ope dashboard --port 9000           # choose a port
```

Open the printed URL, enter a website, and click **Run audit**. The dashboard executes the **real** OPE pipeline (no dummy data, no second engine) and renders health, the 20-module grid, findings (filter/sort), root causes, the dependency-ordered remediation roadmap, an interactive dependency-graph coloured by module status, provider status, and history. Export the exact run as JSON, Markdown, Text, standalone offline HTML, or a complete ZIP bundle. PDF/PNG export is optional and needs the headless-browser extra:

```bash
pip install 'omni-presence-engine[report]' && playwright install chromium
```

Without it, PDF/PNG report a clear "unavailable" state instead of producing a fake file. The dashboard binds to localhost by default and preserves every engine security guarantee (SSRF/DNS-rebinding validation, HTML escaping, request-size caps, no credential exposure).

`multi-audit` runs targets with bounded concurrency and per-target isolation — one failing site never destroys the others — and returns a deterministic per-target + aggregate result.

Run history is stored locally at `~/.ope/runs` (override the base directory with `OPE_HOME`) and is what lets the engine detect regressions between runs.

Optional external evidence — set the environment variable and the matching checks upgrade from `UNKNOWN` to measured evidence; nothing is fabricated when it is absent:

| Variable | Unlocks |
| --- | --- |
| `OPE_PAGESPEED_API_KEY` | Core Web Vitals (LCP, FCP, CLS, TBT, INP) from Google PageSpeed Insights |
| `OPE_SEARCH_CONSOLE_KEY` | Query visibility from Google Search Console (`09-search.query_visibility`) |
| `OPE_BACKLINK_API_KEY` | Off-site authority links from a backlink index, Ahrefs v3 by default (`11-authority.backlinks`) |
| `OPENROUTER_API_KEY` | Optional advisory reasoning layer — surface it with `ope audit … --reason` |
| `OPE_DEPENDENCY_SCAN` | Enable the client-side dependency CVE scan via OSV.dev (`16-security.dependencies`); free, no key, needs network to api.osv.dev |

Add an optional advisory AI reasoning layer over the deterministic evidence (needs `OPENROUTER_API_KEY`; without it the layer reports a clean "unavailable" state and the deterministic audit is unaffected):

```bash
ope audit https://example.com --reason --markdown
```

Legacy `ope-audit` remains supported.

---

## 🎛️ RUN OPE COMMAND CENTER

The Command Center is a real operator UI over the canonical engine — every value
on screen is read from the same audit result the CLI produces (no second engine,
no mock data). Exact commands, start to finish:

```bash
# 1. Install (stdlib-only runtime; Python ≥ 3.10)
git clone https://github.com/digitalhulk/OMNI-Presence-Engine.git
cd OMNI-Presence-Engine
python3 -m pip install -e .

# 2. (Optional) configure external evidence — each is credential-gated and
#    degrades to an honest UNKNOWN when unset. Skip any you do not have.
export OPE_PAGESPEED_API_KEY=...     # Core Web Vitals
export OPE_SEARCH_CONSOLE_KEY=...    # query visibility
export OPE_BACKLINK_API_KEY=...      # off-site authority (Ahrefs v3 by default)
export OPE_DEPENDENCY_SCAN=1         # client-side dependency CVEs via OSV.dev (free)
export OPENROUTER_API_KEY=...        # optional advisory AI reasoning

# 3. Start the Command Center (localhost only by default)
ope dashboard                        # → http://127.0.0.1:8787/
# ope dashboard --port 9000          # choose a port

# 4. (Optional) real PDF/PNG export needs the headless-browser extra
pip install 'omni-presence-engine[report]' && playwright install chromium
```

**In the browser:**
1. Enter a website URL in the top bar and click **Run audit** — this executes the
   real OPE pipeline (validate → crawl → analyze → score → build graph → build plan).
2. **Overview** — OMNI health, check-level PASS/FAIL/UNKNOWN, finding severities,
   top root causes, and top remediation priorities for this run.
3. **Modules** — click any of the 20 modules for its status, score basis, and findings.
4. **Findings** — filter/sort; expand a finding to see its evidence (source, affected
   resource, value, confidence, provenance) — i.e. *why* OPE concluded it.
5. **Dependency Graph** — the canonical 20-module graph, coloured by this run; blocked
   modules trace back to their upstream root cause.
6. **Remediation** — the canonical "fix first" plan, ordered by unblock impact.
7. **AI Reasoning** — click *Generate* (needs `OPENROUTER_API_KEY`; otherwise it says
   "unavailable" honestly). Advisory only — never evidence or a PASS/FAIL.
8. **Providers** — each optional provider's status: ACTIVE / NOT CONFIGURED / PLANNED.
9. **History** — prior runs of the same target (scope-aware: page/site/performance
   histories never mix).
10. **Exports** — JSON, Markdown, Text, offline HTML, ZIP bundle, and (with the extra)
    PDF/PNG — all rendered from the exact run on screen.

**Reading the states:** `PASS`/`FAIL`/`N/A` are direct evidence; `UNKNOWN` means no
evidence source (never treated as a pass); `BLOCKED` is a dependency-derived module
state whose root cause is shown. The dashboard binds to localhost, validates every
target against the SSRF/DNS-rebinding guard, escapes all rendered content, caps
request bodies, and never exposes credentials.

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
- **Dependency-ordered remediation plan** — `planner.build_remediation_plan()` turns the diagnosis into an actionable, deterministic plan (the executable `PLAN` stage): root-cause modules ordered by how many downstream modules each would unblock, each with its evidence-backed findings; direct failures and blocked-and-waiting modules listed separately. It orders existing evidence only — inventing no remediation — and every report now surfaces a "Diagnosis & Plan" section. `IMPLEMENT` stays human-owned.
- **Diagnostics in every report** — JSON, Markdown, and the RawBlock HTML report all expose the same diagnostic chain: global health, per-module status and score, dependency root causes, blocked modules, and the remediation plan. All rendered content is HTML-escaped (no XSS).
- **Real-response robustness** — the live fetch path validates the target against SSRF (loopback, private, link-local, cloud-metadata, IPv6 forms — all resolved-address-checked), revalidates every redirect hop, bounds the response and error bodies, and decompresses gzip/deflate responses under a decompression-bomb cap. Network failures produce a clean CLI error and a non-zero exit code, never a partial or fabricated result.
- **DNS-rebinding hardening** — for direct connections the fetch pins the validated DNS resolution: the address that is SSRF-validated is exactly the one connected to, closing the resolve→validate→connect TOCTOU window. TLS SNI/cert validation still use the hostname. When an egress proxy is configured it resolves and enforces policy, so pinning is skipped and proxy semantics are preserved.
- **Multi-target orchestration** — `ope multi-audit URL...` audits many targets with bounded concurrency and strict per-target isolation (one failure never destroys the others), deterministic input-order aggregation, and a per-target + aggregate summary in JSON or Markdown.
- **Optional-provider capability discovery** — `ope providers` lists each optional provider (PageSpeed, Search Console, backlink index, OpenRouter), whether its credential is configured, and which checks it would upgrade. Absent credentials keep the affected checks `UNKNOWN` with a specific reason — never fabricated.
- **Evidence-backed check bindings** — all 136 registry checks are bound; 118 execute against direct observations or an optional configured provider (PageSpeed, Search Console, backlink index, OSV dependency scan), 3 are finding-record checks, and 15 return `UNKNOWN` with a specific reason naming the missing external API or service.
- **Deterministic observation surface** — HTTP/TLS handshake, robots.txt and AI-crawler access, JSON-LD entity graph, HTML structure and accessibility signals, linked CSS/JS measurement, DNS/TTFB timing, content citability.
- **Local run history** — regression and anomaly comparison between runs of the same target.
- **Optional external evidence** — PageSpeed Insights (Core Web Vitals), Google Search Console (query visibility), a backlink index (off-site authority), and an advisory OpenRouter reasoning layer (surfaced by `ope audit … --reason` and the dashboard's AI Reasoning panel) — all credential-gated and honestly unavailable when unset.

### Check coverage by module

Bound checks per module — **136 of 136 total** (15 require external APIs with no adapter yet and return `UNKNOWN` with a reason):

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

- provider adapters for the remaining external data sources (15 checks are bound but return `UNKNOWN` until an evidence source exists for them; `ope providers` lists what each configured provider upgrades). PageSpeed, Search Console, the backlink index, and the OSV dependency-CVE scan have real, credential-gated adapters (`ope providers` shows them as *active*); the remaining external checks — brand mentions, reputation, factual accuracy, translation quality, colour contrast, analytics/server logs/CRM, and similar — have no adapter yet and stay `UNKNOWN` with a specific reason rather than a fabricated value. These are deliberately not built because each needs either a paid/OAuth API whose contract cannot be verified in this environment, or a data source that would require inventing a metric from fuzzy inputs (e.g. deriving "reputation" from web search), or an evidence type with no matching check in the fixed 136-check registry (e.g. keyword-rank data). Building any of them from a guessed contract would violate the project's no-fabrication rule.
- a standalone scheduler daemon. Multi-target orchestration (`ope multi-audit`) and per-target run history are implemented as the reusable primitives; an external scheduler (cron, CI, a queue) supplies the target list and cadence and calls the engine. The engine deliberately owns *how* to audit and aggregate, not *when* to run.

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

**Version:** `1.2.0`  
**Stage:** Stable release + OMNI Command Center dashboard — public contract (engine output, CLI commands/exit codes, dependency graph, 136-check registry, report shape) is stable and follows semantic versioning  
**Contract:** `evidence-diagnostic-v1`

Capabilities: 136/136 checks bound · validated dependency graph · evidence firewall · root-cause traversal · explainable scoring · dependency-ordered remediation planning · diagnostics in JSON/Markdown/HTML · DNS-rebinding-hardened SSRF · multi-target orchestration · provider capability discovery · run history/regression.

The repository is intentionally being built in verified increments. **If a capability is not executable and validated on `main`, it is documented as a target—not as completed engineering.**
