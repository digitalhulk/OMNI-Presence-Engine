"""Indexability analysis — whether a page should appear in search indexes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .url import normalize_url


class IndexabilityStatus(str, Enum):
    INDEXABLE = "INDEXABLE"
    NON_INDEXABLE = "NON_INDEXABLE"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class IndexabilitySignal:
    name: str
    value: str
    blocks_indexing: bool
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "blocks_indexing": self.blocks_indexing, "source": self.source}


@dataclass
class IndexabilityResult:
    url: str
    status: IndexabilityStatus
    signals: list[IndexabilitySignal] = field(default_factory=list)
    canonical_target: str = ""
    canonical_is_self: bool = True
    has_noindex: bool = False
    has_nofollow: bool = False
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url, "status": self.status.value,
            "signals": [s.to_dict() for s in self.signals],
            "canonical_target": self.canonical_target,
            "canonical_is_self": self.canonical_is_self,
            "has_noindex": self.has_noindex, "has_nofollow": self.has_nofollow,
            "conflicts": self.conflicts,
        }


def analyze_indexability(
    url: str, *,
    status_code: int = 200,
    meta_robots: str = "",
    x_robots_tag: str = "",
    canonical: str = "",
    redirect_target: str = "",
) -> IndexabilityResult:
    """Determine indexability from observed page signals."""
    result = IndexabilityResult(url=url, status=IndexabilityStatus.INDEXABLE)
    signals: list[IndexabilitySignal] = []

    if status_code >= 400:
        signals.append(IndexabilitySignal("http_error", str(status_code), True, "status_code"))
        result.status = IndexabilityStatus.NON_INDEXABLE
    elif 300 <= status_code < 400:
        signals.append(IndexabilitySignal("redirect", str(status_code), True, "status_code"))
        result.status = IndexabilityStatus.NON_INDEXABLE if redirect_target else IndexabilityStatus.CONDITIONAL

    for robots_str, source in [(meta_robots, "meta_robots"), (x_robots_tag, "x_robots_tag")]:
        if not robots_str:
            continue
        directives = {d.strip().lower() for d in robots_str.split(",")}
        if "noindex" in directives:
            signals.append(IndexabilitySignal("noindex", robots_str, True, source))
            result.has_noindex = True
            result.status = IndexabilityStatus.NON_INDEXABLE
        if "nofollow" in directives:
            signals.append(IndexabilitySignal("nofollow", robots_str, False, source))
            result.has_nofollow = True
        if "none" in directives:
            signals.append(IndexabilitySignal("none", robots_str, True, source))
            result.has_noindex = True; result.has_nofollow = True
            result.status = IndexabilityStatus.NON_INDEXABLE

    if canonical:
        try:
            norm_canonical = normalize_url(canonical)
            norm_url = normalize_url(url)
            result.canonical_target = norm_canonical
            result.canonical_is_self = norm_canonical == norm_url
            if not result.canonical_is_self:
                signals.append(IndexabilitySignal("canonical_other", canonical, True, "canonical"))
                if result.status == IndexabilityStatus.INDEXABLE:
                    result.status = IndexabilityStatus.NON_INDEXABLE
        except ValueError:
            result.canonical_target = canonical
            result.canonical_is_self = canonical.rstrip("/") == url.rstrip("/")

    if result.has_noindex and canonical and result.canonical_is_self:
        result.conflicts.append("noindex with self-referencing canonical")

    result.signals = signals
    return result


def find_duplicate_candidates(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect potential duplicate pages from title and canonical signals."""
    title_groups: dict[str, list[str]] = {}
    canonical_groups: dict[str, list[str]] = {}
    for page in pages:
        url = page.get("url", "")
        title = page.get("title", "").strip().lower()
        canonical = page.get("canonical", "")
        if title and len(title) > 10:
            title_groups.setdefault(title, []).append(url)
        if canonical:
            try:
                norm = normalize_url(canonical)
            except ValueError:
                norm = canonical
            canonical_groups.setdefault(norm, []).append(url)
    duplicates: list[dict[str, Any]] = []
    for title, urls in sorted(title_groups.items()):
        if len(urls) > 1:
            duplicates.append({"type": "duplicate_title", "title": title, "urls": sorted(urls)})
    for canonical, urls in sorted(canonical_groups.items()):
        if len(urls) > 1:
            duplicates.append({"type": "shared_canonical", "canonical": canonical, "urls": sorted(urls)})
    return duplicates
