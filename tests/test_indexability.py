"""Tests for indexability analysis."""
from __future__ import annotations

from ope.indexability import (
    IndexabilityStatus,
    analyze_indexability,
    find_duplicate_candidates,
)


class TestAnalyzeIndexability:
    def test_normal_200_indexable(self) -> None:
        result = analyze_indexability("http://example.com/page", status_code=200)
        assert result.status == IndexabilityStatus.INDEXABLE
        assert not result.has_noindex

    def test_404_non_indexable(self) -> None:
        result = analyze_indexability("http://example.com/missing", status_code=404)
        assert result.status == IndexabilityStatus.NON_INDEXABLE

    def test_500_non_indexable(self) -> None:
        result = analyze_indexability("http://example.com/error", status_code=500)
        assert result.status == IndexabilityStatus.NON_INDEXABLE

    def test_301_with_target(self) -> None:
        result = analyze_indexability("http://example.com/old", status_code=301, redirect_target="http://example.com/new")
        assert result.status == IndexabilityStatus.NON_INDEXABLE

    def test_301_without_target(self) -> None:
        result = analyze_indexability("http://example.com/old", status_code=301)
        assert result.status == IndexabilityStatus.CONDITIONAL

    def test_noindex_meta(self) -> None:
        result = analyze_indexability("http://example.com/page", meta_robots="noindex, follow")
        assert result.status == IndexabilityStatus.NON_INDEXABLE
        assert result.has_noindex
        assert not result.has_nofollow

    def test_nofollow_meta(self) -> None:
        result = analyze_indexability("http://example.com/page", meta_robots="nofollow")
        assert result.status == IndexabilityStatus.INDEXABLE
        assert result.has_nofollow

    def test_none_directive(self) -> None:
        result = analyze_indexability("http://example.com/page", meta_robots="none")
        assert result.has_noindex
        assert result.has_nofollow
        assert result.status == IndexabilityStatus.NON_INDEXABLE

    def test_x_robots_tag(self) -> None:
        result = analyze_indexability("http://example.com/page", x_robots_tag="noindex")
        assert result.has_noindex

    def test_canonical_self(self) -> None:
        result = analyze_indexability("http://example.com/page", canonical="http://example.com/page")
        assert result.canonical_is_self
        assert result.status == IndexabilityStatus.INDEXABLE

    def test_canonical_other(self) -> None:
        result = analyze_indexability("http://example.com/page", canonical="http://example.com/canonical")
        assert not result.canonical_is_self
        assert result.status == IndexabilityStatus.NON_INDEXABLE

    def test_conflict_noindex_self_canonical(self) -> None:
        result = analyze_indexability("http://example.com/page", meta_robots="noindex", canonical="http://example.com/page")
        assert "noindex with self-referencing canonical" in result.conflicts

    def test_to_dict(self) -> None:
        result = analyze_indexability("http://example.com/page", status_code=200)
        d = result.to_dict()
        assert d["status"] == "INDEXABLE"
        assert isinstance(d["signals"], list)


class TestDuplicateCandidates:
    def test_duplicate_titles(self) -> None:
        pages = [
            {"url": "http://example.com/a", "title": "Same Long Title Here", "canonical": ""},
            {"url": "http://example.com/b", "title": "Same Long Title Here", "canonical": ""},
        ]
        dupes = find_duplicate_candidates(pages)
        assert any(d["type"] == "duplicate_title" for d in dupes)

    def test_shared_canonical(self) -> None:
        pages = [
            {"url": "http://example.com/a", "title": "Title A", "canonical": "http://example.com/canonical"},
            {"url": "http://example.com/b", "title": "Title B", "canonical": "http://example.com/canonical"},
        ]
        dupes = find_duplicate_candidates(pages)
        assert any(d["type"] == "shared_canonical" for d in dupes)

    def test_short_titles_ignored(self) -> None:
        pages = [
            {"url": "http://example.com/a", "title": "Short", "canonical": ""},
            {"url": "http://example.com/b", "title": "Short", "canonical": ""},
        ]
        dupes = find_duplicate_candidates(pages)
        assert not any(d["type"] == "duplicate_title" for d in dupes)

    def test_no_duplicates(self) -> None:
        pages = [
            {"url": "http://example.com/a", "title": "Unique Title For Page A", "canonical": "http://example.com/a"},
            {"url": "http://example.com/b", "title": "Unique Title For Page B", "canonical": "http://example.com/b"},
        ]
        assert find_duplicate_candidates(pages) == []
