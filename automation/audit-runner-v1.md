# OPE Audit Runner v1

## Purpose
Turn the module registry into a deterministic, evidence-first audit execution plan.

## Run contract
1. Load entity/project configuration.
2. Resolve targets, markets, languages and devices.
3. Load the 20-module registry.
4. Resolve module dependencies in order.
5. Execute checks only when their prerequisites are available.
6. Collect raw observations with source, timestamp, target and provider metadata.
7. Normalize observations into `ope.audit.finding` records.
8. Classify each result as FACT, OBSERVED, ESTIMATE, HYPOTHESIS or EXPERIMENT.
9. Trace symptom to dependency and root cause.
10. Calculate priority using `ope.priority`.
11. Produce remediation, validation and regression requirements.
12. Re-run affected checks after implementation.
13. Register durable monitoring for high-impact findings.

## Dependency gates
Entity -> Infrastructure -> Code -> Crawl -> Index -> Semantics -> Content/Media -> Search/AI -> Authority/Local -> UX/Accessibility/Performance/Security/Language -> Analytics -> Conversion -> Continuous Optimization.

A downstream check must not convert missing upstream evidence into a PASS. It must return BLOCKED, UNKNOWN or NOT_APPLICABLE with a reason.

## Evidence contract
Every observation should carry:
- source/provider
- observed_at
- target URL/property/entity
- raw value or measurement
- method/tool where applicable
- confidence
- freshness
- provider attribution

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
- Never manufacture evidence to fill gaps.

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

## ABC Taxis 247 first implementation
Prioritize: entity identity, local presence, airport/service queries, booking path, mobile performance, analytics/attribution, AI search visibility, trust/reviews, and conversion completion. Transaction fields should be modeled as structured data where applicable: pickup, destination, date, time, vehicle, passengers, luggage, airport, route, fare, driver, booking and support.
