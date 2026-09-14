"""Extended metadata extraction — OG, Twitter Card, social, language signals."""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any


@dataclass
class PageMetadata:
    title: str = ""
    description: str = ""
    canonical: str = ""
    viewport: str = ""
    charset: str = ""
    lang: str = ""
    meta_robots: str = ""
    h1_count: int = 0
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    og_type: str = ""
    og_url: str = ""
    og_site_name: str = ""
    og_locale: str = ""
    twitter_card: str = ""
    twitter_title: str = ""
    twitter_description: str = ""
    twitter_image: str = ""
    twitter_site: str = ""
    twitter_creator: str = ""
    content_language: str = ""
    hreflang_tags: list[dict[str, str]] = field(default_factory=list)
    author: str = ""
    generator: str = ""
    theme_color: str = ""
    referrer: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if v or v == 0:
                d[k] = v
        return d

    def completeness_score(self) -> float:
        """0.0–1.0 score of how complete the essential metadata is."""
        checks = [
            bool(self.title), bool(self.description), bool(self.canonical),
            bool(self.viewport), bool(self.charset), bool(self.lang),
            bool(self.og_title), bool(self.og_description), bool(self.og_image),
            bool(self.twitter_card), bool(self.twitter_title),
        ]
        return round(sum(checks) / len(checks), 2)


class MetadataParser(HTMLParser):
    """Extracts comprehensive page metadata from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta = PageMetadata()
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html":
            self.meta.lang = a.get("lang", "") or ""
        if tag == "title":
            self._in_title = True; self._title_parts = []
        if tag == "h1":
            self.meta.h1_count += 1
        if tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            content = a.get("content", "") or ""
            http_equiv = (a.get("http-equiv") or "").lower()
            if a.get("charset"):
                self.meta.charset = a["charset"] or ""
            if name == "viewport": self.meta.viewport = content
            if name == "description": self.meta.description = content
            if name == "robots": self.meta.meta_robots = content
            if name == "author": self.meta.author = content
            if name == "generator": self.meta.generator = content
            if name == "theme-color": self.meta.theme_color = content
            if name == "referrer": self.meta.referrer = content
            if http_equiv == "content-language": self.meta.content_language = content
            for key in (name, prop):
                if not key:
                    continue
                if key == "og:title": self.meta.og_title = self.meta.og_title or content
                if key == "og:description": self.meta.og_description = self.meta.og_description or content
                if key == "og:image": self.meta.og_image = self.meta.og_image or content
                if key == "og:type": self.meta.og_type = self.meta.og_type or content
                if key == "og:url": self.meta.og_url = self.meta.og_url or content
                if key == "og:site_name": self.meta.og_site_name = self.meta.og_site_name or content
                if key == "og:locale": self.meta.og_locale = self.meta.og_locale or content
                if key == "twitter:card": self.meta.twitter_card = self.meta.twitter_card or content
                if key == "twitter:title": self.meta.twitter_title = self.meta.twitter_title or content
                if key == "twitter:description": self.meta.twitter_description = self.meta.twitter_description or content
                if key == "twitter:image": self.meta.twitter_image = self.meta.twitter_image or content
                if key == "twitter:site": self.meta.twitter_site = self.meta.twitter_site or content
                if key == "twitter:creator": self.meta.twitter_creator = self.meta.twitter_creator or content
        if tag == "link":
            rel = (a.get("rel") or "").lower().split()
            href = a.get("href", "") or ""
            if "canonical" in rel:
                self.meta.canonical = href
            if "alternate" in rel and a.get("hreflang"):
                self.meta.hreflang_tags.append({"hreflang": a["hreflang"] or "", "href": href})

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self.meta.title = " ".join("".join(self._title_parts).split())
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def extract_metadata(html: str | bytes, charset: str = "utf-8", content_language_header: str = "") -> PageMetadata:
    """Extract comprehensive metadata from HTML content."""
    if isinstance(html, bytes):
        try:
            text = html.decode(charset, errors="replace")
        except (LookupError, ValueError):
            text = html.decode("utf-8", errors="replace")
    else:
        text = html
    parser = MetadataParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        pass
    if content_language_header and not parser.meta.content_language:
        parser.meta.content_language = content_language_header
    return parser.meta
