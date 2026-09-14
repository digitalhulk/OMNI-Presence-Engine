# OPE Audit Runner v1

## Purpose
Turn the module registry into a deterministic, evidence-first audit execution plan.

## Implementation status

This document is the contract. What of it runs today:

| Contract step | Status |
| --- | --- |
| Load configuration, resolve target | `ope.cli` / `ope.audit` |
| Load the 20-module registry, resolve dependencies, execute checks | `ope.registry` + `ope.module_runner` — all 136 checks execute every run |
| Collect observations with source, timestamp and target | `ope.audit` (HTTP, TLS, robots, HTML, JSON-LD, CSS/JS), `ope.crawler`, `ope.citability`, `ope.integrations.pagespeed` |
| Normalize into finding records, keep evidence lifecycle separate from execution state | `ope.engine` |
| Priority calculation | `ope.scoring` / `ope.audit` |
| Remediation and validation requirements | Finding records carry both |
| Re-run and compare after implementation | `ope.history` — metric and finding regression against the previous run |
| Durable monitoring registration | Not implemented: runs are local and manual, with no scheduler |
| Dataset and research execution classes | Not implemented: no backlink, ranking or research provider is bound |

All 136 registry checks have a bound evidence provider: 113 deterministic checks, 3 finding-record checks (N/A when no findings exist), and 20 external-evidence checks (UNKNOWN with a specific reason naming the missing API). The rest of the contract below applies to all checks.

## Run contract
1. Load entity/project configuration.
2. Resolve targets, markets, languages and devices.
3. Load the 20-module registry.
4. Resolve module dependencies in order.
5. Execute checks only when prerequisites are available.
6. Collect raw observations with source, timestamp, target and provider metadata.
7. Normalize observations into `ope.audit.finding` records.
8. Keep evidence lifecycle (`FACT`, `OBSERVED`, `ESTIMATE`, `HYPOTHESIS`, `EXPERIMENT`, `DEPRECATED`) separate from execution state (`PASS`, `FAIL`, `UNKNOWN`, `BLOCKED`, `N/A`).
9. Trace symptom to dependency and root cause.
10. Calculate priority using `ope.priority`.
11. Produce remediation, validation and regression requirements.
12. Re-run affected checks after implementation.
13. Register durable monitoring for high-impact findings.

## Dependency gates
Entity -> Infrastructure -> Code -> Crawl -> Index -> Semantics -> Content/Media -> Search/AI -> Authority/Local -> UX/Accessibility/Performance/Security/Language -> Analytics -> Conversion -> Continuous Optimization.

A downstream check must not convert missing upstream evidence into a PASS. It must return BLOCKED or UNKNOWN with a reason. A module with no executed checks is UNKNOWN, not PASS.

## Evidence contract
Every observation should carry:
- source/provider
- observed_at
- target URL/property/entity
- raw value or measurement
- method/tool where applicable
- confidence
- freshness where applicable
- provider attribution

Evidence must be attributable and reproducible where the provider permits it. Never manufacture evidence to fill gaps.

## Execution classes
- deterministic: headers, status, robots, sitemap, canonical, HTML metadata
- measurement: performance, accessibility, security, analytics coverage
- dataset: search visibility, backlinks, rankings, citations
- research: current web evidence, competitor/context analysis
- human/UX: usability, trust, clarity, conversion friction

## Safety
- Never commit credentials or secrets.
- Destructive changes require explicit approval.
- Third-party provider estimates remain estimates.
- Preserve approved visual and functional behavior during optimization.
- Validate every redirect target before following it.
- Reject localhost, loopback, private, link-local and otherwise reserved network targets in fetchers.
- Apply bounded timeouts, redirect limits and response-size limits.
- Treat client-side claims as unverified until backed by trusted evidence.

## Output
A run returns:
1. target inventory
2. dependency status
3. evidence set
4. findings
5. root-cause graph
6. module scores
7. prioritized action queue
8. validation plan
9. regression guards
10. monitoring plan
11. run metadata and changelog entry
