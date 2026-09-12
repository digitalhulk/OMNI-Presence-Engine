# Parallel AI Integration

Status: FACT / ADAPTER

Parallel is the live-web research and retrieval layer for OPE. It is not the source of truth for SEO metrics; it is the web intelligence layer that discovers, extracts, monitors and researches current information.

## Why OPE uses Parallel

- Fresh web research for audits and competitive intelligence
- Search and extraction of public web pages
- Deep research for difficult multi-source questions
- Monitoring of changes and signals
- Cited evidence that can be stored with findings
- Agent-compatible retrieval through API, SDK or MCP

## OPE role

Parallel sits primarily in:

`Research -> Discovery -> Retrieval -> Evidence -> Diagnosis -> Update`

It can feed Entity, Semantics, Content, Search, AI Search, Authority, Local and Continuous Optimization modules.

## Core adapter jobs

1. `research(query, constraints)`
2. `search(query, freshness, domain_filters)`
3. `extract(url)`
4. `monitor(target, change_definition)`
5. `find_all(objective, constraints)`
6. `evidence_pack(claims)`

## Important separation

Parallel web research must not be confused with first-party analytics, Google Search Console, Bing Webmaster data, or SEO vendor metrics. Those sources retain ownership of their own measurements.

## ABC Taxis 247 reference

ABC Taxis 247 can use Parallel for live competitor research, local market research, SERP/content discovery, current service information, citation/evidence collection, and change monitoring. The exact production prompts and credentials remain implementation-specific and must never be committed to this repository.

## Credential policy

Never commit `PARALLEL_API_KEY`, tokens, cookies, OAuth secrets or MCP credentials. Use environment variables or the deployment secret manager.

Suggested environment names:

- `PARALLEL_API_KEY`
- `PARALLEL_BASE_URL`
- `PARALLEL_TIMEOUT_MS`
- `PARALLEL_MAX_COST_PER_RUN`

## Evidence record

Every material research result should retain:

- query/objective
- timestamp
- source URL
- source title/domain
- extracted claim or passage
- confidence/status
- freshness requirement
- downstream module(s)
- validation result

## Design principle

Parallel is an intelligence input, not an authority override. OPE validates consequential claims against appropriate primary/first-party sources whenever possible.
