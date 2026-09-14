"""Shared test fixtures for the OPE test suite."""
from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture()
def minimal_audit_result() -> dict[str, Any]:
    """A minimal normalized audit result for testing report renderers."""
    return {
        "target": "https://example.com",
        "run_id": "test-001",
        "started_at": 1700000000,
        "version": "0.9.0",
        "engine_contract": "evidence-diagnostic-v1",
        "status": "COMPLETED",
        "inventory": {"status": 200, "url": "https://example.com"},
        "summary": {"finding_count": 1, "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
        "modules": {f"{i:02d}": {"status": "UNKNOWN", "findings": []} for i in range(1, 21)},
        "findings": [
            {
                "id": "test-f1",
                "module": "02-infrastructure",
                "symptom": "Missing HSTS header",
                "severity": "high",
                "status": "OBSERVED",
                "priority": 0.7,
                "root_cause": "Server does not set Strict-Transport-Security",
                "confidence": 0.9,
                "evidence": [{"source": "http-headers", "confidence": 0.9}],
                "remediation": ["Add HSTS header"],
                "validation": ["Check header presence"],
            }
        ],
        "checks": {},
    }


@pytest.fixture()
def minimal_site_result(minimal_audit_result: dict[str, Any]) -> dict[str, Any]:
    """A minimal normalized site audit result."""
    result = dict(minimal_audit_result)
    result["engine_scope"] = "site"
    result["crawl_summary"] = {
        "pages_crawled": 5,
        "max_depth_reached": 2,
        "internal_links": 12,
        "external_links": 3,
        "orphan_pages": 1,
        "error_count": 0,
    }
    result["pages"] = [
        {"url": "https://example.com/", "status_code": 200, "depth": 0, "findings": []},
        {"url": "https://example.com/about", "status_code": 200, "depth": 1, "findings": []},
    ]
    return result


@pytest.fixture()
def minimal_performance_result(minimal_audit_result: dict[str, Any]) -> dict[str, Any]:
    """A minimal normalized performance audit result."""
    result = dict(minimal_audit_result)
    result["engine_scope"] = "performance"
    result["duration_s"] = 4.2
    result["performance_report"] = {
        "vitals_summary": {
            "DESKTOP": {
                "lcp": {"value_ms": 1200, "rating": "good"},
                "fcp": {"value_ms": 800, "rating": "good"},
                "cls": {"value": 0.05, "rating": "good"},
            }
        },
        "resource_summary": {
            "total_requests": 42,
            "total_bytes": 1_500_000,
            "js_requests": 12,
            "css_requests": 5,
            "image_requests": 18,
            "font_requests": 3,
        },
        "findings": [],
    }
    return result
