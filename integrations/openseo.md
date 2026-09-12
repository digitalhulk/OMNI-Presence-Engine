# OpenSEO Integration

Status: FACT / ADAPTER

Repository: `every-app/open-seo`

OpenSEO is an open-source, self-hostable SEO application positioned as an alternative to Semrush/Ahrefs. Its documented workflows include keyword research, rank tracking, competitor insights, backlinks, site audits and AI visibility. It exposes MCP and agent skills, and uses DataForSEO for SEO data when self-hosted.

## OPE role

OpenSEO becomes the SEO measurement and execution-data layer inside OPE, while OPE remains the orchestration, root-cause, evidence, cross-platform and business system.

### Division of responsibility

| Need | OPE | OpenSEO |
|---|---|---|
| Entity model | Owner | Input |
| SEO project setup | Orchestrates | Executes/records SEO workflows |
| Keyword research | Strategy + normalization | SEO data workflow |
| Rank tracking | Cross-source interpretation | Rank data |
| Competitor intelligence | Cross-channel synthesis | Competitor SEO data |
| Backlinks | Authority model | Backlink data |
| Site audit | Root-cause framework | SEO audit data |
| AI visibility | Cross-platform model | OpenSEO AI-visibility data where supported |
| First-party analytics | Fusion layer | Optional connector |
| Business conversion | Owner | Supporting data |
| Continuous optimization | Owner | Data source + workflow |

## Required data contract

OpenSEO outputs should be normalized into OPE schemas instead of being copied as raw vendor dashboards.

Minimum fields:

- project/entity
- domain/page
- query/keyword
- location
- language
- device
- timestamp
- SERP/rank feature
- competitor
- backlink signal
- audit issue
- AI visibility/citation signal
- source/provider
- confidence
- cost

## DataForSEO boundary

OpenSEO itself is not a proprietary search index. Its current architecture uses DataForSEO as the SEO-data provider. Therefore OPE must label OpenSEO/DataForSEO-derived measurements separately from Google Search Console, Bing Webmaster, server logs and direct observation.

## MCP / agent layer

Where available, connect OpenSEO MCP to the OPE agent runtime so the engine can request SEO data as tools instead of scraping the OpenSEO UI.

Potential agent jobs:

- project setup
- keyword discovery
- keyword clustering
- competitive landscape
- competitor analysis
- link prospecting
- rank monitoring
- audit retrieval
- AI visibility checks

## Governance

Do not treat OpenSEO metrics as universal truth. Provider coverage, location, language, device, sampling and freshness can affect measurements. Store provider metadata and compare against first-party data when making business decisions.
