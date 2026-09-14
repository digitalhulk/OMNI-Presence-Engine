/* Sample OPE audit result — generated from a real `ope audit --json` run
   against a fixed example page, so this file always matches the shape the
   engine actually emits. Regenerate with scripts/gen_sample_report.py. */
window.OPE_SAMPLE_REPORT = {
  "checks": {
    "01-entity.consistency": {
      "check_id": "01-entity.consistency",
      "duration_ms": 0.035,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259831+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "name_matches_title": true
          }
        }
      ],
      "findings": [],
      "module": "01-entity",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "01-entity.identifiers": {
      "check_id": "01-entity.identifiers",
      "duration_ms": 0.013,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259860+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_identifiers": true
          }
        }
      ],
      "findings": [],
      "module": "01-entity",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "01-entity.identity": {
      "check_id": "01-entity.identity",
      "duration_ms": 0.012,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259874+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "entity_types": [
              "organization"
            ]
          }
        }
      ],
      "findings": [],
      "module": "01-entity",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "01-entity.ownership": {
      "check_id": "01-entity.ownership",
      "duration_ms": 0.015,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259892+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "verification_tags": [
              "google-site-verification",
              "msvalidate.01"
            ]
          }
        }
      ],
      "findings": [],
      "module": "01-entity",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "01-entity.relationships": {
      "check_id": "01-entity.relationships",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259903+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_relationships": false
          }
        }
      ],
      "findings": [],
      "module": "01-entity",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "02-infrastructure.cdn.configuration": {
      "check_id": "02-infrastructure.cdn.configuration",
      "duration_ms": 0.015,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259916+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "cdn_markers": [
              "cf-ray",
              "server: cloudflare"
            ]
          }
        }
      ],
      "findings": [],
      "module": "02-infrastructure",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "02-infrastructure.dns.resolution": {
      "check_id": "02-infrastructure.dns.resolution",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259927+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "dns_ms": 18.4
          }
        }
      ],
      "findings": [],
      "module": "02-infrastructure",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "02-infrastructure.hosting.availability": {
      "check_id": "02-infrastructure.hosting.availability",
      "duration_ms": 0.049,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259975+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "status": 200
          }
        }
      ],
      "findings": [],
      "module": "02-infrastructure",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "02-infrastructure.server_reachability": {
      "check_id": "02-infrastructure.server_reachability",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259991+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "status": 200,
            "ttfb_ms": 236.0
          }
        }
      ],
      "findings": [],
      "module": "02-infrastructure",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "02-infrastructure.tls.valid": {
      "check_id": "02-infrastructure.tls.valid",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.259999+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "scheme": "https"
          }
        }
      ],
      "findings": [],
      "module": "02-infrastructure",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "03-code.css_cost": {
      "check_id": "03-code.css_cost",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260007+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget_bytes": 150000,
            "css_bytes": 88412,
            "fetched_requests": 1
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Measured from up to 1 fetched subresources; resources beyond the fetch cap are not counted.",
      "status": "PASS"
    },
    "03-code.forms": {
      "check_id": "03-code.forms",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260017+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "forms": 1,
            "forms_missing_action": 0
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "03-code.head_metadata": {
      "check_id": "03-code.head_metadata",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260026+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "title": "StarBrand — Digital Presence"
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "03-code.html.validity": {
      "check_id": "03-code.html.validity",
      "duration_ms": 0.01,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260038+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "defects": []
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "03-code.js_cost": {
      "check_id": "03-code.js_cost",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260045+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget_bytes": 300000,
            "fetched_requests": 1,
            "js_bytes": 0
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Measured from up to 1 fetched subresources; resources beyond the fetch cap are not counted.",
      "status": "PASS"
    },
    "03-code.semantic_html": {
      "check_id": "03-code.semantic_html",
      "duration_ms": 0.013,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260071+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "landmarks": [
              "footer",
              "header",
              "main",
              "nav"
            ]
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "03-code.structured_data": {
      "check_id": "03-code.structured_data",
      "duration_ms": 0.012,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260086+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "json_ld_blocks": 1
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "03-code.third_party_code": {
      "check_id": "03-code.third_party_code",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260095+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget": 5,
            "third_party_hosts": []
          }
        }
      ],
      "findings": [],
      "module": "03-code",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "04-crawl.bot_access": {
      "check_id": "04-crawl.bot_access",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260103+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "ai_crawlers": {
              "ClaudeBot": "BLOCK",
              "GPTBot": "ALLOW",
              "OAI-SearchBot": "ALLOW",
              "PerplexityBot": "ALLOW"
            },
            "blocked_ai_crawlers": [
              "ClaudeBot"
            ]
          }
        }
      ],
      "findings": [],
      "module": "04-crawl",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "04-crawl.crawl_budget_risk": {
      "check_id": "04-crawl.crawl_budget_risk",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260112+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget": 50,
            "discovered_requests": 1
          }
        }
      ],
      "findings": [],
      "module": "04-crawl",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "04-crawl.crawl_errors": {
      "check_id": "04-crawl.crawl_errors",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260119+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "soft_404": false,
            "status": 200
          }
        }
      ],
      "findings": [],
      "module": "04-crawl",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "04-crawl.robots_access": {
      "check_id": "04-crawl.robots_access",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260126+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "robots_status": 200,
            "rule_count": 4
          }
        }
      ],
      "findings": [],
      "module": "04-crawl",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "04-crawl.sitemap_discovery": {
      "check_id": "04-crawl.sitemap_discovery",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260132+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "sitemaps": [
              "https://starbrand.example.com/sitemap.xml"
            ]
          }
        }
      ],
      "findings": [],
      "module": "04-crawl",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "05-index.canonicalization": {
      "check_id": "05-index.canonicalization",
      "duration_ms": 0.01,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260143+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "canonical": "https://starbrand.example.com/"
          }
        }
      ],
      "findings": [],
      "module": "05-index",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "05-index.duplication": {
      "check_id": "05-index.duplication",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260150+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "canonical": "https://starbrand.example.com/",
            "canonical_is_self": true
          }
        }
      ],
      "findings": [],
      "module": "05-index",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "05-index.indexability": {
      "check_id": "05-index.indexability",
      "duration_ms": 0.013,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260161+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "meta_robots": "",
            "x_robots_tag": ""
          }
        }
      ],
      "findings": [],
      "module": "05-index",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "05-index.rendering_indexability": {
      "check_id": "05-index.rendering_indexability",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260171+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "noscript_content": true,
            "word_count": 100
          }
        }
      ],
      "findings": [],
      "module": "05-index",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "05-index.status_codes": {
      "check_id": "05-index.status_codes",
      "duration_ms": 0.01,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260177+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "status": 200
          }
        }
      ],
      "findings": [],
      "module": "05-index",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "06-semantics.entity_markup": {
      "check_id": "06-semantics.entity_markup",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260191+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "entity_types": [
              "organization"
            ]
          }
        }
      ],
      "findings": [],
      "module": "06-semantics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "06-semantics.knowledge_consistency": {
      "check_id": "06-semantics.knowledge_consistency",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260200+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "description_matches": true
          }
        }
      ],
      "findings": [],
      "module": "06-semantics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "06-semantics.query_intent": {
      "check_id": "06-semantics.query_intent",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260206+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "question_headings": 2
          }
        }
      ],
      "findings": [],
      "module": "06-semantics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "06-semantics.relationships": {
      "check_id": "06-semantics.relationships",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260213+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_relationships": false
          }
        }
      ],
      "findings": [],
      "module": "06-semantics",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "06-semantics.taxonomy": {
      "check_id": "06-semantics.taxonomy",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260222+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_breadcrumb": false
          }
        }
      ],
      "findings": [],
      "module": "06-semantics",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "06-semantics.topic_coverage": {
      "check_id": "06-semantics.topic_coverage",
      "duration_ms": 0.042,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260264+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "h1": 1,
            "subheadings": 2
          }
        }
      ],
      "findings": [],
      "module": "06-semantics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "07-content.completeness": {
      "check_id": "07-content.completeness",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260272+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget": 300,
            "word_count": 100
          }
        }
      ],
      "findings": [],
      "module": "07-content",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "07-content.conversion_context": {
      "check_id": "07-content.conversion_context",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260279+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_cta": true,
            "word_count": 100
          }
        }
      ],
      "findings": [],
      "module": "07-content",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "07-content.factual_accuracy": {
      "check_id": "07-content.factual_accuracy",
      "duration_ms": 0.009,
      "evidence": [],
      "findings": [],
      "module": "07-content",
      "reason": "Factual accuracy verification requires an external fact-checking service (not configured)",
      "status": "UNKNOWN"
    },
    "07-content.freshness": {
      "check_id": "07-content.freshness",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260295+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "article_modified": "",
            "last_modified": null
          }
        }
      ],
      "findings": [],
      "module": "07-content",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "07-content.helpfulness": {
      "check_id": "07-content.helpfulness",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260305+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "lists": 1,
            "subheadings": 2,
            "word_count": 100
          }
        }
      ],
      "findings": [],
      "module": "07-content",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "07-content.intent_match": {
      "check_id": "07-content.intent_match",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260312+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "intent_aligned": true
          }
        }
      ],
      "findings": [],
      "module": "07-content",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "07-content.internal_links": {
      "check_id": "07-content.internal_links",
      "duration_ms": 0.024,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260317+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "internal_links": 5
          }
        }
      ],
      "findings": [],
      "module": "07-content",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "07-content.originality": {
      "check_id": "07-content.originality",
      "duration_ms": 0.007,
      "evidence": [],
      "findings": [],
      "module": "07-content",
      "reason": "Originality assessment requires a content-comparison service (not configured)",
      "status": "UNKNOWN"
    },
    "08-media.captions_transcripts": {
      "check_id": "08-media.captions_transcripts",
      "duration_ms": 0.006,
      "evidence": [],
      "findings": [],
      "module": "08-media",
      "reason": "The page embeds no audio or video elements",
      "status": "N/A"
    },
    "08-media.image_metadata": {
      "check_id": "08-media.image_metadata",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260363+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "images": 3,
            "images_missing_dimensions": 1
          }
        }
      ],
      "findings": [],
      "module": "08-media",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "08-media.image_quality": {
      "check_id": "08-media.image_quality",
      "duration_ms": 0.01,
      "evidence": [],
      "findings": [],
      "module": "08-media",
      "reason": "Image quality assessment requires rendered visual analysis (not available in headless mode)",
      "status": "UNKNOWN"
    },
    "08-media.media_performance": {
      "check_id": "08-media.media_performance",
      "duration_ms": 0.011,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260387+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "images": 3,
            "lazy_images": 2
          }
        }
      ],
      "findings": [],
      "module": "08-media",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "08-media.responsive_media": {
      "check_id": "08-media.responsive_media",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260395+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "images": 3,
            "images_missing_srcset": 3
          }
        }
      ],
      "findings": [],
      "module": "08-media",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "08-media.video_metadata": {
      "check_id": "08-media.video_metadata",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "08-media",
      "reason": "The page embeds no video elements",
      "status": "N/A"
    },
    "09-search.image_visibility": {
      "check_id": "09-search.image_visibility",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260408+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "images": 3,
            "images_missing_alt": 1,
            "images_missing_dimensions": 1
          }
        }
      ],
      "findings": [],
      "module": "09-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "09-search.local_visibility": {
      "check_id": "09-search.local_visibility",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "09-search",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "09-search.query_visibility": {
      "check_id": "09-search.query_visibility",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "09-search",
      "reason": "Query visibility data requires Search Console API access (OPE_SEARCH_CONSOLE_KEY not configured)",
      "status": "UNKNOWN"
    },
    "09-search.serp_eligibility": {
      "check_id": "09-search.serp_eligibility",
      "duration_ms": 0.011,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260424+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_canonical": true,
            "has_description": true,
            "has_title": true,
            "noindex": false
          }
        }
      ],
      "findings": [],
      "module": "09-search",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "09-search.sitelinks": {
      "check_id": "09-search.sitelinks",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260437+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_breadcrumb": false,
            "has_nav": true,
            "internal_links": 5
          }
        }
      ],
      "findings": [],
      "module": "09-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "09-search.snippets": {
      "check_id": "09-search.snippets",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260443+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "description_length": 102
          }
        }
      ],
      "findings": [],
      "module": "09-search",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "10-ai-search.agent_accessibility": {
      "check_id": "10-ai-search.agent_accessibility",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260450+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "ai_crawlers": {
              "ClaudeBot": "BLOCK",
              "GPTBot": "ALLOW",
              "OAI-SearchBot": "ALLOW",
              "PerplexityBot": "ALLOW"
            },
            "blocked_ai_crawlers": [
              "ClaudeBot"
            ]
          }
        }
      ],
      "findings": [],
      "module": "10-ai-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "10-ai-search.ai_retrievability": {
      "check_id": "10-ai-search.ai_retrievability",
      "duration_ms": 0.014,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260465+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "average_citability_score": 38.8,
            "blocked_ai_crawlers": [
              "ClaudeBot"
            ],
            "budget": 50.0
          }
        }
      ],
      "findings": [],
      "module": "10-ai-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "10-ai-search.answer_eligibility": {
      "check_id": "10-ai-search.answer_eligibility",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260474+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "average_citability_score": 38.8
          }
        }
      ],
      "findings": [],
      "module": "10-ai-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "10-ai-search.citation_presence": {
      "check_id": "10-ai-search.citation_presence",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260480+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "grade_distribution": {
              "A": 0,
              "B": 0,
              "C": 1,
              "D": 1,
              "F": 2
            }
          }
        }
      ],
      "findings": [],
      "module": "10-ai-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "10-ai-search.factual_consistency": {
      "check_id": "10-ai-search.factual_consistency",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "10-ai-search",
      "reason": "Factual consistency verification requires an external fact-checking service (not configured)",
      "status": "UNKNOWN"
    },
    "10-ai-search.source_grounding": {
      "check_id": "10-ai-search.source_grounding",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260491+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "external_links": 0
          }
        }
      ],
      "findings": [],
      "module": "10-ai-search",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "11-authority.backlinks": {
      "check_id": "11-authority.backlinks",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "11-authority",
      "reason": "Backlink analysis requires a link-index API such as Ahrefs or Moz (OPE_BACKLINK_API_KEY not configured)",
      "status": "UNKNOWN"
    },
    "11-authority.brand_mentions": {
      "check_id": "11-authority.brand_mentions",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "11-authority",
      "reason": "Brand-mention monitoring requires an external brand-tracking API (not configured)",
      "status": "UNKNOWN"
    },
    "11-authority.citations": {
      "check_id": "11-authority.citations",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260506+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "external_links": 0
          }
        }
      ],
      "findings": [],
      "module": "11-authority",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "11-authority.consistency": {
      "check_id": "11-authority.consistency",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260512+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_social_profiles": true
          }
        }
      ],
      "findings": [],
      "module": "11-authority",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "11-authority.expert_signals": {
      "check_id": "11-authority.expert_signals",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260519+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_author": false
          }
        }
      ],
      "findings": [],
      "module": "11-authority",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "11-authority.reputation": {
      "check_id": "11-authority.reputation",
      "duration_ms": 0.005,
      "evidence": [],
      "findings": [],
      "module": "11-authority",
      "reason": "Reputation assessment requires a review-aggregation or sentiment API (not configured)",
      "status": "UNKNOWN"
    },
    "11-authority.reviews": {
      "check_id": "11-authority.reviews",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260531+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_review": false
          }
        }
      ],
      "findings": [],
      "module": "11-authority",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "12-local.gbp_presence": {
      "check_id": "12-local.gbp_presence",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "12-local",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "12-local.hours": {
      "check_id": "12-local.hours",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "12-local",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "12-local.local_pages": {
      "check_id": "12-local.local_pages",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "12-local",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "12-local.maps_presence": {
      "check_id": "12-local.maps_presence",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "12-local",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "12-local.nap_consistency": {
      "check_id": "12-local.nap_consistency",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260556+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "entity_types": [
              "organization"
            ],
            "has_nap": false
          }
        }
      ],
      "findings": [],
      "module": "12-local",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "12-local.reviews": {
      "check_id": "12-local.reviews",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "12-local",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "12-local.service_area": {
      "check_id": "12-local.service_area",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "12-local",
      "reason": "The page declares no local business, so local detail checks do not apply",
      "status": "N/A"
    },
    "13-ux.booking_friction": {
      "check_id": "13-ux.booking_friction",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260573+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "avg_inputs_per_form": 2.0,
            "forms": 1,
            "inputs": 2
          }
        }
      ],
      "findings": [],
      "module": "13-ux",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "13-ux.hierarchy": {
      "check_id": "13-ux.hierarchy",
      "duration_ms": 0.004,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260579+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "h1": 1
          }
        }
      ],
      "findings": [],
      "module": "13-ux",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "13-ux.interaction_clarity": {
      "check_id": "13-ux.interaction_clarity",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260585+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "buttons": 1,
            "buttons_without_text": 0
          }
        }
      ],
      "findings": [],
      "module": "13-ux",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "13-ux.mobile_usability": {
      "check_id": "13-ux.mobile_usability",
      "duration_ms": 0.014,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260598+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "viewport": "width=device-width, initial-scale=1"
          }
        }
      ],
      "findings": [],
      "module": "13-ux",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "13-ux.navigation": {
      "check_id": "13-ux.navigation",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260607+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "landmarks": [
              "footer",
              "header",
              "main",
              "nav"
            ]
          }
        }
      ],
      "findings": [],
      "module": "13-ux",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "13-ux.trust_visibility": {
      "check_id": "13-ux.trust_visibility",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260612+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_trust_links": true
          }
        }
      ],
      "findings": [],
      "module": "13-ux",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "14-accessibility.alt_text": {
      "check_id": "14-accessibility.alt_text",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260619+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "images_missing_alt": 1
          }
        }
      ],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "14-accessibility.captions": {
      "check_id": "14-accessibility.captions",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "14-accessibility",
      "reason": "The page embeds no audio or video elements",
      "status": "N/A"
    },
    "14-accessibility.contrast": {
      "check_id": "14-accessibility.contrast",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Colour-contrast verification requires a rendered-page screenshot and WCAG analysis (not available in headless mode)",
      "status": "UNKNOWN"
    },
    "14-accessibility.focus": {
      "check_id": "14-accessibility.focus",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260637+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_focus_visible": false,
            "suppresses_focus_outline": true
          }
        }
      ],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "14-accessibility.forms": {
      "check_id": "14-accessibility.forms",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260643+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "inputs": 2,
            "unlabelled_inputs": 0
          }
        }
      ],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "14-accessibility.keyboard": {
      "check_id": "14-accessibility.keyboard",
      "duration_ms": 0.004,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260649+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "positive_tabindex": 0
          }
        }
      ],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "14-accessibility.reduced_motion": {
      "check_id": "14-accessibility.reduced_motion",
      "duration_ms": 0.004,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260655+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_motion": true,
            "respects_reduced_motion": false
          }
        }
      ],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "14-accessibility.semantics": {
      "check_id": "14-accessibility.semantics",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260661+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "landmarks": [
              "footer",
              "header",
              "main",
              "nav"
            ]
          }
        }
      ],
      "findings": [],
      "module": "14-accessibility",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "15-performance.cls": {
      "check_id": "15-performance.cls",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "PageSpeed Insights evidence is not configured or unavailable",
      "status": "UNKNOWN"
    },
    "15-performance.dns": {
      "check_id": "15-performance.dns",
      "duration_ms": 0.004,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260671+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget_ms": 100.0,
            "dns_ms": 18.4
          }
        }
      ],
      "findings": [],
      "module": "15-performance",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "15-performance.fcp": {
      "check_id": "15-performance.fcp",
      "duration_ms": 0.002,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "PageSpeed Insights evidence is not configured or unavailable",
      "status": "UNKNOWN"
    },
    "15-performance.frame_cost": {
      "check_id": "15-performance.frame_cost",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "Frame-cost measurement requires a browser-based paint profiler (not available in headless mode)",
      "status": "UNKNOWN"
    },
    "15-performance.inp": {
      "check_id": "15-performance.inp",
      "duration_ms": 0.002,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "PageSpeed Insights evidence is not configured or unavailable",
      "status": "UNKNOWN"
    },
    "15-performance.lcp": {
      "check_id": "15-performance.lcp",
      "duration_ms": 0.002,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "PageSpeed Insights evidence is not configured or unavailable",
      "status": "UNKNOWN"
    },
    "15-performance.network": {
      "check_id": "15-performance.network",
      "duration_ms": 0.016,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260689+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget": 50,
            "requests": 2
          }
        }
      ],
      "findings": [],
      "module": "15-performance",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "15-performance.page_weight": {
      "check_id": "15-performance.page_weight",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260707+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget_bytes": 1000000,
            "css_bytes": 88412,
            "html_bytes": 2731,
            "js_bytes": 0,
            "page_weight_bytes": 91143
          }
        }
      ],
      "findings": [],
      "module": "15-performance",
      "reason": "Document plus fetched CSS/JS; images, fonts and media are not counted.",
      "status": "PASS"
    },
    "15-performance.render_cost": {
      "check_id": "15-performance.render_cost",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "Render-cost measurement requires a browser-based performance trace (not available in headless mode)",
      "status": "UNKNOWN"
    },
    "15-performance.tbt": {
      "check_id": "15-performance.tbt",
      "duration_ms": 0.002,
      "evidence": [],
      "findings": [],
      "module": "15-performance",
      "reason": "PageSpeed Insights evidence is not configured or unavailable",
      "status": "UNKNOWN"
    },
    "15-performance.ttfb": {
      "check_id": "15-performance.ttfb",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260723+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "budget_ms": 800.0,
            "ttfb_ms": 236.0
          }
        }
      ],
      "findings": [],
      "module": "15-performance",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "16-security.abuse_controls": {
      "check_id": "16-security.abuse_controls",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260731+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_captcha": false,
            "has_rate_limit_headers": false
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "16-security.auth": {
      "check_id": "16-security.auth",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "16-security",
      "reason": "The page has no login form to evaluate",
      "status": "N/A"
    },
    "16-security.cookies": {
      "check_id": "16-security.cookies",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260745+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "cookie_count": 1,
            "insecure_cookies": []
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "16-security.csp": {
      "check_id": "16-security.csp",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260751+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "present": false,
            "unsafe_directives": []
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "16-security.dependencies": {
      "check_id": "16-security.dependencies",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "16-security",
      "reason": "Dependency vulnerability scanning requires a CVE database or SCA tool (not configured)",
      "status": "UNKNOWN"
    },
    "16-security.https": {
      "check_id": "16-security.https",
      "duration_ms": 0.004,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260766+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "scheme": "https"
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "16-security.secrets": {
      "check_id": "16-security.secrets",
      "duration_ms": 0.005,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260771+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "exposed_secret_types": []
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "16-security.security_headers": {
      "check_id": "16-security.security_headers",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260780+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "csp": false,
            "hsts": true,
            "referrer_policy_header": true,
            "x_content_type_options": true
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "16-security.tls": {
      "check_id": "16-security.tls",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260787+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "cipher": "TLS_AES_256_GCM_SHA384",
            "days_until_expiry": 68,
            "protocol": "TLSv1.3"
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "16-security.waf": {
      "check_id": "16-security.waf",
      "duration_ms": 0.015,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260793+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "waf_markers": [
              "cf-ray",
              "server: cloudflare"
            ]
          }
        }
      ],
      "findings": [],
      "module": "16-security",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "17-language.hreflang": {
      "check_id": "17-language.hreflang",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260809+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "hreflang_count": 0
          }
        }
      ],
      "findings": [],
      "module": "17-language",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "17-language.language_declaration": {
      "check_id": "17-language.language_declaration",
      "duration_ms": 0.014,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260823+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "lang": "en"
          }
        }
      ],
      "findings": [],
      "module": "17-language",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "17-language.locale": {
      "check_id": "17-language.locale",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260836+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "lang": "en"
          }
        }
      ],
      "findings": [],
      "module": "17-language",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "17-language.regional_intent": {
      "check_id": "17-language.regional_intent",
      "duration_ms": 0.005,
      "evidence": [],
      "findings": [],
      "module": "17-language",
      "reason": "The page does not target a specific region (no local business markup)",
      "status": "N/A"
    },
    "17-language.translation_quality": {
      "check_id": "17-language.translation_quality",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "17-language",
      "reason": "Translation quality assessment requires multilingual NLP analysis (not configured)",
      "status": "UNKNOWN"
    },
    "17-language.transliteration": {
      "check_id": "17-language.transliteration",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "17-language",
      "reason": "Transliteration accuracy assessment requires script-conversion analysis (not configured)",
      "status": "UNKNOWN"
    },
    "17-language.unicode": {
      "check_id": "17-language.unicode",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260855+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "declared_charset": "utf-8"
          }
        }
      ],
      "findings": [],
      "module": "17-language",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "18-analytics.ai_referrals": {
      "check_id": "18-analytics.ai_referrals",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "18-analytics",
      "reason": "AI referral attribution requires analytics event-stream access (not available from a single-page audit)",
      "status": "UNKNOWN"
    },
    "18-analytics.attribution": {
      "check_id": "18-analytics.attribution",
      "duration_ms": 0.011,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260866+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_attribution_code": true
          }
        }
      ],
      "findings": [],
      "module": "18-analytics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "18-analytics.crm_linkage": {
      "check_id": "18-analytics.crm_linkage",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "18-analytics",
      "reason": "CRM linkage verification requires CRM API integration (not configured)",
      "status": "UNKNOWN"
    },
    "18-analytics.event_quality": {
      "check_id": "18-analytics.event_quality",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260884+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_event_tracking": true
          }
        }
      ],
      "findings": [],
      "module": "18-analytics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "18-analytics.measurement_coverage": {
      "check_id": "18-analytics.measurement_coverage",
      "duration_ms": 0.004,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260890+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_analytics": true
          }
        }
      ],
      "findings": [],
      "module": "18-analytics",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "18-analytics.search_data": {
      "check_id": "18-analytics.search_data",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "18-analytics",
      "reason": "Search performance data requires Search Console API access (OPE_SEARCH_CONSOLE_KEY not configured)",
      "status": "UNKNOWN"
    },
    "18-analytics.server_logs": {
      "check_id": "18-analytics.server_logs",
      "duration_ms": 0.002,
      "evidence": [],
      "findings": [],
      "module": "18-analytics",
      "reason": "Server log analysis requires direct log access or a log-aggregation API (not configured)",
      "status": "UNKNOWN"
    },
    "19-conversion.booking_completion": {
      "check_id": "19-conversion.booking_completion",
      "duration_ms": 0.006,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260904+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "buttons": 1,
            "forms": 1,
            "forms_missing_action": 0
          }
        }
      ],
      "findings": [],
      "module": "19-conversion",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "19-conversion.cta_clarity": {
      "check_id": "19-conversion.cta_clarity",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260910+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_cta": true
          }
        }
      ],
      "findings": [],
      "module": "19-conversion",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "19-conversion.funnel_dropoff": {
      "check_id": "19-conversion.funnel_dropoff",
      "duration_ms": 0.003,
      "evidence": [],
      "findings": [],
      "module": "19-conversion",
      "reason": "Funnel drop-off analysis requires analytics event data (not available from a single-page audit)",
      "status": "UNKNOWN"
    },
    "19-conversion.lead_capture": {
      "check_id": "19-conversion.lead_capture",
      "duration_ms": 0.007,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260924+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "contact_input": true,
            "forms": 1
          }
        }
      ],
      "findings": [],
      "module": "19-conversion",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "19-conversion.revenue_tracking": {
      "check_id": "19-conversion.revenue_tracking",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "19-conversion",
      "reason": "Revenue tracking verification requires payment-platform or analytics API integration (not configured)",
      "status": "UNKNOWN"
    },
    "19-conversion.trust_to_action": {
      "check_id": "19-conversion.trust_to_action",
      "duration_ms": 0.008,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260939+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "has_cta": true,
            "has_trust_links": true
          }
        }
      ],
      "findings": [],
      "module": "19-conversion",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "20-continuous-optimization.anomaly_detection": {
      "check_id": "20-continuous-optimization.anomaly_detection",
      "duration_ms": 0.005,
      "evidence": [],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "No previous run is stored for this target, so there is no baseline to compare against",
      "status": "N/A"
    },
    "20-continuous-optimization.monitoring": {
      "check_id": "20-continuous-optimization.monitoring",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "This is the first recorded run for the target, so there is no monitoring history yet",
      "status": "N/A"
    },
    "20-continuous-optimization.prioritization": {
      "check_id": "20-continuous-optimization.prioritization",
      "duration_ms": 0.011,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260963+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "findings": 2,
            "unranked": []
          }
        }
      ],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "20-continuous-optimization.regression_guards": {
      "check_id": "20-continuous-optimization.regression_guards",
      "duration_ms": 0.004,
      "evidence": [],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "No previous run is stored for this target, so there is no baseline to compare against",
      "status": "N/A"
    },
    "20-continuous-optimization.root_cause": {
      "check_id": "20-continuous-optimization.root_cause",
      "duration_ms": 0.009,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260978+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "findings": 2,
            "without_established_root_cause": [
              "14-A11Y-IMG-001",
              "16-SEC-CONTENT-SECURITY-POLICY"
            ]
          }
        }
      ],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "Direct audit observation",
      "status": "FAIL"
    },
    "20-continuous-optimization.update_pipeline": {
      "check_id": "20-continuous-optimization.update_pipeline",
      "duration_ms": 0.212,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.260986+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "store_writable": true
          }
        }
      ],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "Direct audit observation",
      "status": "PASS"
    },
    "20-continuous-optimization.validation": {
      "check_id": "20-continuous-optimization.validation",
      "duration_ms": 0.025,
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.261216+00:00",
          "provenance": "direct",
          "source": "ope-audit",
          "target": "https://starbrand.example.com/",
          "value": {
            "findings": 2,
            "without_validation_steps": []
          }
        }
      ],
      "findings": [],
      "module": "20-continuous-optimization",
      "reason": "Direct audit observation",
      "status": "PASS"
    }
  },
  "completed_at": 1726190402.4,
  "engine": "ope",
  "engine_contract": "evidence-diagnostic-v1",
  "final_url": "https://starbrand.example.com/",
  "findings": [
    {
      "affected_layer": "14-accessibility",
      "confidence": 1.0,
      "dependency": "",
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.257629+00:00",
          "source": "html-parser",
          "target": "https://starbrand.example.com/",
          "value": {
            "images": 3,
            "missing_alt": 1
          }
        }
      ],
      "evidence_status": "HYPOTHESIS",
      "execution_status": "FAIL",
      "id": "14-A11Y-IMG-001",
      "impact": "",
      "module": "14-accessibility",
      "priority": 1.0,
      "regression_guard": [],
      "remediation": [
        "Add meaningful alt text to informative images; use empty alt for decorative images."
      ],
      "root_cause": "Not yet established; additional evidence or dependency analysis is required.",
      "severity": "medium",
      "status": "HYPOTHESIS",
      "symptom": "1 of 3 images lack useful alt text",
      "validation": [
        "Re-run accessibility checks and inspect representative images."
      ]
    },
    {
      "affected_layer": "16-security",
      "confidence": 1.0,
      "dependency": "",
      "evidence": [
        {
          "confidence": 1.0,
          "observed_at": "2026-09-14T15:23:30.257629+00:00",
          "source": "http-headers",
          "target": "https://starbrand.example.com/",
          "value": {
            "content-security-policy": null
          }
        }
      ],
      "evidence_status": "HYPOTHESIS",
      "execution_status": "FAIL",
      "id": "16-SEC-CONTENT-SECURITY-POLICY",
      "impact": "",
      "module": "16-security",
      "priority": 1.0,
      "regression_guard": [],
      "remediation": [
        "Review and configure content-security-policy according to the application's threat model."
      ],
      "root_cause": "Not yet established; additional evidence or dependency analysis is required.",
      "severity": "low",
      "status": "HYPOTHESIS",
      "symptom": "Recommended security header not observed: content-security-policy",
      "validation": [
        "Re-fetch response headers and verify content-security-policy."
      ]
    }
  ],
  "headers": {
    "cf-ray": "8a1b2c3d4e5f",
    "content-type": "text/html; charset=utf-8",
    "referrer-policy": "strict-origin-when-cross-origin",
    "server": "cloudflare",
    "strict-transport-security": "max-age=31536000",
    "x-content-type-options": "nosniff"
  },
  "inventory": {
    "article_modified": "",
    "buttons": 1,
    "buttons_without_text": 0,
    "bytes": 2731,
    "canonical": "https://starbrand.example.com/",
    "canonical_is_self": true,
    "caption_tracks": 0,
    "cdn_markers": [
      "cf-ray",
      "server: cloudflare"
    ],
    "citability": {
      "average_citability_score": 38.8,
      "bottom_5_citable": [
        {
          "breakdown": {
            "answer_block_quality": 10,
            "self_containment": 12,
            "statistical_density": 0,
            "structural_readability": 2,
            "uniqueness_signals": 0
          },
          "grade": "F",
          "heading": "",
          "label": "Poor Citability",
          "total_score": 24,
          "word_count": 7
        },
        {
          "breakdown": {
            "answer_block_quality": 20,
            "self_containment": 12,
            "statistical_density": 0,
            "structural_readability": 2,
            "uniqueness_signals": 0
          },
          "grade": "F",
          "heading": "How does the audit work?",
          "label": "Poor Citability",
          "total_score": 34,
          "word_count": 7
        },
        {
          "breakdown": {
            "answer_block_quality": 30,
            "self_containment": 9,
            "statistical_density": 0,
            "structural_readability": 8,
            "uniqueness_signals": 0
          },
          "grade": "D",
          "heading": "What does StarBrand do?",
          "label": "Low Citability",
          "total_score": 47,
          "word_count": 43
        },
        {
          "breakdown": {
            "answer_block_quality": 30,
            "self_containment": 12,
            "statistical_density": 0,
            "structural_readability": 8,
            "uniqueness_signals": 0
          },
          "grade": "C",
          "heading": "How does the audit work?",
          "label": "Moderate Citability",
          "total_score": 50,
          "word_count": 43
        }
      ],
      "grade_distribution": {
        "A": 0,
        "B": 0,
        "C": 1,
        "D": 1,
        "F": 2
      },
      "optimal_length_passages": 0,
      "top_5_citable": [
        {
          "breakdown": {
            "answer_block_quality": 30,
            "self_containment": 12,
            "statistical_density": 0,
            "structural_readability": 8,
            "uniqueness_signals": 0
          },
          "grade": "C",
          "heading": "How does the audit work?",
          "label": "Moderate Citability",
          "total_score": 50,
          "word_count": 43
        },
        {
          "breakdown": {
            "answer_block_quality": 30,
            "self_containment": 9,
            "statistical_density": 0,
            "structural_readability": 8,
            "uniqueness_signals": 0
          },
          "grade": "D",
          "heading": "What does StarBrand do?",
          "label": "Low Citability",
          "total_score": 47,
          "word_count": 43
        },
        {
          "breakdown": {
            "answer_block_quality": 20,
            "self_containment": 12,
            "statistical_density": 0,
            "structural_readability": 2,
            "uniqueness_signals": 0
          },
          "grade": "F",
          "heading": "How does the audit work?",
          "label": "Poor Citability",
          "total_score": 34,
          "word_count": 7
        },
        {
          "breakdown": {
            "answer_block_quality": 10,
            "self_containment": 12,
            "statistical_density": 0,
            "structural_readability": 2,
            "uniqueness_signals": 0
          },
          "grade": "F",
          "heading": "",
          "label": "Poor Citability",
          "total_score": 24,
          "word_count": 7
        }
      ],
      "total_blocks_analyzed": 4
    },
    "contact_input": true,
    "cookies": {
      "cookie_count": 1,
      "insecure_cookies": []
    },
    "csp": false,
    "csp_profile": {
      "present": false,
      "unsafe_directives": []
    },
    "css_bytes": 88412,
    "declared_charset": "utf-8",
    "description": "StarBrand builds evidence-driven digital presence for growing businesses across search and AI answers.",
    "description_matches": true,
    "discovered_requests": 1,
    "dns_ms": 18.4,
    "doctype": "DOCTYPE html",
    "entity_types": [
      "organization"
    ],
    "exposed_secrets": [],
    "external_links": 0,
    "fetched_requests": 1,
    "forms": 1,
    "forms_missing_action": 0,
    "h1": 1,
    "has_address": false,
    "has_analytics": true,
    "has_attribution_code": true,
    "has_author": false,
    "has_breadcrumb": false,
    "has_captcha": false,
    "has_css": true,
    "has_cta": true,
    "has_entity_type": true,
    "has_event_tracking": true,
    "has_focus_visible": false,
    "has_geo": false,
    "has_google_profile": false,
    "has_identifiers": true,
    "has_motion": true,
    "has_nap": false,
    "has_opening_hours": false,
    "has_password_input": false,
    "has_rate_limit_headers": false,
    "has_relationships": false,
    "has_review": false,
    "has_service_area": false,
    "has_social_profiles": true,
    "has_trust_links": true,
    "headings": 3,
    "history": {
      "baseline_recorded_at": null,
      "baseline_run_id": null,
      "metric_regressions": null,
      "new_findings": null,
      "resolved_findings": null,
      "runs_recorded": 0,
      "store_writable": true
    },
    "hreflang_count": 0,
    "hsts": true,
    "images": 3,
    "images_missing_alt": 1,
    "images_missing_dimensions": 1,
    "images_missing_srcset": 3,
    "inputs": 2,
    "intent_aligned": true,
    "internal_links": 5,
    "is_local_business": false,
    "js_bytes": 0,
    "json_ld_blocks": 1,
    "landmarks": [
      "footer",
      "header",
      "main",
      "nav"
    ],
    "lang": "en",
    "last_modified": null,
    "lazy_images": 2,
    "links": 5,
    "lists": 1,
    "local_visibility_ready": false,
    "media_elements": 0,
    "meta_robots": "",
    "name_matches_title": true,
    "noscript_content": true,
    "page_weight_bytes": 91143,
    "pagespeed": null,
    "positive_tabindex": 0,
    "question_headings": 2,
    "referrer_policy_header": true,
    "respects_reduced_motion": false,
    "robots": {
      "ai_crawlers": {
        "ClaudeBot": "BLOCK",
        "GPTBot": "ALLOW",
        "OAI-SearchBot": "ALLOW",
        "PerplexityBot": "ALLOW"
      },
      "allowed_ai_crawlers": [
        "GPTBot",
        "OAI-SearchBot",
        "PerplexityBot"
      ],
      "blocked_ai_crawlers": [
        "ClaudeBot"
      ],
      "error": null,
      "rule_count": 4,
      "rules": [],
      "sitemaps": [
        "https://starbrand.example.com/sitemap.xml"
      ],
      "status": 200,
      "url": "https://starbrand.example.com/robots.txt"
    },
    "soft_404": false,
    "status": 200,
    "structure": [
      "body",
      "head",
      "html"
    ],
    "subheadings": 2,
    "suppresses_focus_outline": true,
    "tables": 1,
    "third_party_hosts": [],
    "title": "StarBrand — Digital Presence",
    "title_count": 1,
    "tls": {
      "cipher": "TLS_AES_256_GCM_SHA384",
      "days_until_expiry": 68,
      "error": null,
      "protocol": "TLSv1.3"
    },
    "ttfb_ms": 236.0,
    "unlabelled_inputs": 0,
    "verification_tags": [
      "google-site-verification",
      "msvalidate.01"
    ],
    "videos": 0,
    "videos_missing_metadata": 0,
    "viewport": "width=device-width, initial-scale=1",
    "waf_markers": [
      "cf-ray",
      "server: cloudflare"
    ],
    "word_count": 100,
    "x_content_type_options": true,
    "x_robots_tag": null
  },
  "modules": {
    "01": {
      "findings": [],
      "status": "FAIL"
    },
    "02": {
      "findings": [],
      "status": "PASS"
    },
    "03": {
      "findings": [],
      "status": "PASS"
    },
    "04": {
      "findings": [],
      "status": "FAIL"
    },
    "05": {
      "findings": [],
      "status": "PASS"
    },
    "06": {
      "findings": [],
      "status": "FAIL"
    },
    "07": {
      "findings": [],
      "status": "FAIL"
    },
    "08": {
      "findings": [],
      "status": "FAIL"
    },
    "09": {
      "findings": [],
      "status": "FAIL"
    },
    "10": {
      "findings": [],
      "status": "FAIL"
    },
    "11": {
      "findings": [],
      "status": "FAIL"
    },
    "12": {
      "findings": [],
      "status": "FAIL"
    },
    "13": {
      "findings": [],
      "status": "PASS"
    },
    "14": {
      "findings": [
        "14-A11Y-IMG-001"
      ],
      "status": "FAIL"
    },
    "15": {
      "findings": [],
      "status": "UNKNOWN"
    },
    "16": {
      "findings": [
        "16-SEC-CONTENT-SECURITY-POLICY"
      ],
      "status": "FAIL"
    },
    "17": {
      "findings": [],
      "status": "FAIL"
    },
    "18": {
      "findings": [],
      "status": "UNKNOWN"
    },
    "19": {
      "findings": [],
      "status": "UNKNOWN"
    },
    "20": {
      "findings": [],
      "status": "FAIL"
    }
  },
  "run_id": "ope-1726190400",
  "started_at": 1726190400,
  "summary": {
    "critical": 0,
    "finding_count": 2,
    "high": 0,
    "info": 0,
    "low": 1,
    "medium": 1
  },
  "target": "https://starbrand.example.com",
  "version": "0.3.0"
};
