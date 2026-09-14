"""Page inventory model, link graph, and orphan detection."""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from .url import normalize_url


class _PageInfoParser(HTMLParser):
    """Lightweight parser for page-record fields only."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""; self.description = ""; self.canonical = ""
        self.meta_robots = ""; self.lang = ""; self.h1_count = 0
        self._in_title = False; self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang", "") or ""
        if tag == "title": self._in_title = True; self._title_parts = []
        if tag == "h1": self.h1_count += 1
        if tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "description": self.description = a.get("content", "") or ""
            if name == "robots": self.meta_robots = a.get("content", "") or ""
        if tag == "link":
            rel = (a.get("rel") or "").lower().split()
            if "canonical" in rel: self.canonical = a.get("href", "") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self.title = " ".join("".join(self._title_parts).split())
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title: self._title_parts.append(data)


@dataclass
class LinkRecord:
    source: str
    target: str
    text: str = ""
    rel: str = ""
    is_internal: bool = True
    nofollow: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "text": self.text, "rel": self.rel, "is_internal": self.is_internal, "nofollow": self.nofollow}


@dataclass
class PageRecord:
    url: str
    status_code: int
    content_type: str = ""
    title: str = ""
    description: str = ""
    canonical: str = ""
    meta_robots: str = ""
    lang: str = ""
    h1_count: int = 0
    word_count: int = 0
    depth: int = 0
    is_indexable: bool = True
    outgoing_links: list[LinkRecord] = field(default_factory=list)
    incoming_links: list[LinkRecord] = field(default_factory=list)
    response_bytes: int = 0
    redirect_target: str = ""
    crawl_status: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url, "status_code": self.status_code,
            "content_type": self.content_type, "title": self.title,
            "description": self.description, "canonical": self.canonical,
            "meta_robots": self.meta_robots, "lang": self.lang,
            "h1_count": self.h1_count, "word_count": self.word_count,
            "depth": self.depth, "is_indexable": self.is_indexable,
            "outgoing_links_count": len(self.outgoing_links),
            "incoming_links_count": len(self.incoming_links),
            "response_bytes": self.response_bytes,
            "redirect_target": self.redirect_target,
            "crawl_status": self.crawl_status, "error": self.error,
        }


@dataclass
class LinkGraph:
    pages: dict[str, PageRecord] = field(default_factory=dict)
    links: list[LinkRecord] = field(default_factory=list)

    def add_page(self, record: PageRecord) -> None:
        self.pages[record.url] = record

    def add_link(self, link: LinkRecord) -> None:
        self.links.append(link)
        if link.source in self.pages:
            self.pages[link.source].outgoing_links.append(link)
        if link.is_internal and link.target in self.pages:
            self.pages[link.target].incoming_links.append(link)

    def rebuild_incoming(self) -> None:
        for p in self.pages.values():
            p.incoming_links = []
        for link in self.links:
            if link.is_internal and link.target in self.pages:
                self.pages[link.target].incoming_links.append(link)

    def orphan_candidates(self) -> list[str]:
        """Pages with zero incoming internal links (excluding the root)."""
        if not self.pages:
            return []
        seed = min(self.pages.values(), key=lambda p: p.depth)
        return sorted(url for url, page in self.pages.items() if url != seed.url and not page.incoming_links)

    def internal_link_stats(self) -> dict[str, Any]:
        internal = [link for link in self.links if link.is_internal]
        incoming_counts: dict[str, int] = {}
        outgoing_counts: dict[str, int] = {}
        for link in internal:
            outgoing_counts[link.source] = outgoing_counts.get(link.source, 0) + 1
            incoming_counts[link.target] = incoming_counts.get(link.target, 0) + 1
        return {
            "total_internal_links": len(internal),
            "total_external_links": sum(1 for link in self.links if not link.is_internal),
            "pages_with_no_incoming": sum(1 for url in self.pages if incoming_counts.get(url, 0) == 0 and self.pages[url].depth > 0),
            "avg_incoming": round(sum(incoming_counts.values()) / len(self.pages), 1) if self.pages else 0,
            "avg_outgoing": round(sum(outgoing_counts.values()) / len(self.pages), 1) if self.pages else 0,
            "max_incoming": max(incoming_counts.values(), default=0),
            "max_outgoing": max(outgoing_counts.values(), default=0),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_count": len(self.pages),
            "link_count": len(self.links),
            "pages": {url: p.to_dict() for url, p in sorted(self.pages.items())},
            "stats": self.internal_link_stats(),
            "orphan_candidates": self.orphan_candidates(),
        }


def build_link_graph(pages: list[Any], scope_host: str) -> LinkGraph:
    """Build a LinkGraph from CrawledPage instances."""
    from .site_crawler import CrawledPage, CrawlStatus

    graph = LinkGraph()
    for page in pages:
        if not isinstance(page, CrawledPage):
            continue
        record = PageRecord(
            url=page.normalized_url, status_code=page.status_code,
            content_type=page.content_type, depth=page.depth,
            response_bytes=page.response_bytes,
            crawl_status=page.crawl_status.value, error=page.error,
        )
        if page.final_url and page.final_url != page.normalized_url:
            record.redirect_target = page.final_url
        if page.is_html() and page.body and page.crawl_status == CrawlStatus.SUCCESS:
            try:
                text = page.body.decode(page.charset, errors="replace")
            except (LookupError, ValueError):
                text = page.body.decode("utf-8", errors="replace")
            parser = _PageInfoParser()
            try:
                parser.feed(text); parser.close()
            except Exception:
                pass
            record.title = parser.title
            record.description = parser.description
            record.canonical = parser.canonical
            record.meta_robots = parser.meta_robots
            record.lang = parser.lang
            record.h1_count = parser.h1_count
            record.word_count = len(text.split())
        graph.add_page(record)

    for page in pages:
        if not isinstance(page, CrawledPage) or not page.is_html():
            continue
        for href in page.links:
            try:
                target_norm = normalize_url(href)
            except ValueError:
                target_norm = href
            target_host = (urllib.parse.urlparse(target_norm).hostname or "").lower()
            is_internal = target_host == scope_host or target_host.endswith("." + scope_host)
            graph.add_link(LinkRecord(source=page.normalized_url, target=target_norm, is_internal=is_internal))

    graph.rebuild_incoming()
    return graph
