# OPE Data Source Matrix

OPE uses multiple sources because no single SEO/AI/search provider is a complete source of truth.

| Layer | Primary source | Secondary source | Purpose |
|---|---|---|---|
| Live web research | Parallel | Direct web retrieval | Current facts, research, evidence |
| SEO external data | OpenSEO/DataForSEO | Other providers | Keywords, SERPs, ranks, backlinks, audits |
| Google first-party search | Search Console | Google Search documentation | Queries, clicks, impressions, indexing evidence |
| Bing first-party search | Bing Webmaster / AI Performance | Bing documentation | Search + AI citation/grounding signals |
| AI discovery | Platform-specific measurements | Controlled query tests | Citation/recommendation visibility |
| Website behavior | GA4 / server logs | CDN logs | Engagement and conversion |
| Technical truth | Browser/Lighthouse/PageSpeed + server/CDN | Synthetic tests | Performance, rendering, network |
| Accessibility | Automated + manual testing | Browser/accessibility tree | Human and machine accessibility |
| Security | Headers/TLS/WAF/dependency checks | Security scanners | Security posture |

## Source precedence

For a claim, prefer the source closest to the phenomenon being measured. First-party platform data beats inferred third-party estimates for that platform. Primary documents beat summaries for policy decisions. Live web research is used to discover and triangulate evidence, not to overwrite first-party measurements.

## Evidence labels

- `FACT`: directly supported by an authoritative source
- `OBSERVED`: directly measured by OPE
- `ESTIMATE`: provider/model estimate
- `HYPOTHESIS`: reasoned but not yet validated
- `EXPERIMENT`: controlled test
- `DEPRECATED`: no longer recommended
