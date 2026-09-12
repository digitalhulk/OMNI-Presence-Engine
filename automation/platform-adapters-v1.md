# OPE Platform Adapters v1

## Adapter principle
External platforms are evidence providers. Provider metrics are not universal truth; source, scope and timestamp stay attached to observations.

## Parallel
Role: live web research, extraction, monitoring and current evidence.
Jobs: search, extract, research, monitor, find_all, evidence_pack.
Use cases: competitor research, SERP/context investigation, local market discovery, source extraction and change monitoring.

## OpenSEO
Role: SEO measurement and execution data layer.
Use cases: keyword research, rankings, competitor data, backlinks, site audits and supported AI-visibility datasets.
Provider attribution is retained when external datasets are supplied by another provider.

## Google first-party
Inputs: Search Console, PageSpeed/Lighthouse/browser observations and official Search documentation.
Use cases: search performance, crawl/index evidence, performance measurement and policy/update evidence.

## Bing first-party
Inputs: Bing Webmaster Tools and AI Performance where available.
Use cases: search visibility, indexing and AI citation/grounding observations.
Citation counts are visibility measurements, not automatic authority or ranking scores.

## Analytics and logs
Inputs: GA4, server logs, CDN logs, CRM, call tracking and advertising platforms.
Use cases: behavior, attribution, conversion, revenue and request evidence.

## Normalization
Map every observation to entity, module, source/provider, timestamp, target, value, status, confidence, freshness and evidence reference.

## Conflict resolution
1. Prefer the source closest to the phenomenon.
2. Prefer first-party data for platform-specific behavior.
3. Prefer official documentation for policy claims.
4. Use independent research for triangulation.
5. Preserve conflicts rather than averaging them into false certainty.

## Credential rule
Secrets and private credentials never enter repository content. Runtime configuration belongs in the deployment secret manager or environment.
