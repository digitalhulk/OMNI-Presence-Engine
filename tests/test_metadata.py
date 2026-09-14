"""Tests for the metadata extraction engine."""
from __future__ import annotations

from ope.metadata import PageMetadata, extract_metadata

FULL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>My Test Page</title>
<meta name="description" content="A test description">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index, follow">
<meta name="author" content="Test Author">
<meta name="generator" content="OPE Tests">
<meta name="theme-color" content="#ff0000">
<meta name="referrer" content="no-referrer">
<meta property="og:title" content="OG Title">
<meta property="og:description" content="OG Description">
<meta property="og:image" content="https://example.com/image.png">
<meta property="og:type" content="website">
<meta property="og:url" content="https://example.com/">
<meta property="og:site_name" content="Example">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Twitter Title">
<meta name="twitter:description" content="Twitter Desc">
<meta name="twitter:image" content="https://example.com/tw.png">
<meta name="twitter:site" content="@example">
<meta name="twitter:creator" content="@author">
<link rel="canonical" href="https://example.com/">
<link rel="alternate" hreflang="es" href="https://example.com/es/">
<link rel="alternate" hreflang="fr" href="https://example.com/fr/">
</head>
<body>
<h1>Main Heading</h1>
<h1>Second H1</h1>
</body>
</html>"""


class TestExtractMetadata:
    def test_basic_fields(self) -> None:
        meta = extract_metadata(FULL_HTML)
        assert meta.title == "My Test Page"
        assert meta.description == "A test description"
        assert meta.viewport == "width=device-width, initial-scale=1"
        assert meta.charset == "utf-8"
        assert meta.lang == "en"
        assert meta.meta_robots == "index, follow"
        assert meta.author == "Test Author"

    def test_og_fields(self) -> None:
        meta = extract_metadata(FULL_HTML)
        assert meta.og_title == "OG Title"
        assert meta.og_description == "OG Description"
        assert meta.og_image == "https://example.com/image.png"
        assert meta.og_type == "website"
        assert meta.og_url == "https://example.com/"
        assert meta.og_site_name == "Example"
        assert meta.og_locale == "en_US"

    def test_twitter_fields(self) -> None:
        meta = extract_metadata(FULL_HTML)
        assert meta.twitter_card == "summary_large_image"
        assert meta.twitter_title == "Twitter Title"
        assert meta.twitter_description == "Twitter Desc"
        assert meta.twitter_image == "https://example.com/tw.png"
        assert meta.twitter_site == "@example"
        assert meta.twitter_creator == "@author"

    def test_canonical_and_hreflang(self) -> None:
        meta = extract_metadata(FULL_HTML)
        assert meta.canonical == "https://example.com/"
        assert len(meta.hreflang_tags) == 2
        assert meta.hreflang_tags[0]["hreflang"] == "es"

    def test_h1_count(self) -> None:
        meta = extract_metadata(FULL_HTML)
        assert meta.h1_count == 2

    def test_content_language_header(self) -> None:
        meta = extract_metadata("<html><head></head><body></body></html>", content_language_header="en-US")
        assert meta.content_language == "en-US"

    def test_content_language_http_equiv(self) -> None:
        html = '<html><head><meta http-equiv="content-language" content="de"></head></html>'
        meta = extract_metadata(html)
        assert meta.content_language == "de"

    def test_bytes_input(self) -> None:
        meta = extract_metadata(b"<html><head><title>Bytes</title></head></html>")
        assert meta.title == "Bytes"

    def test_empty_html(self) -> None:
        meta = extract_metadata("")
        assert meta.title == ""
        assert meta.completeness_score() == 0.0

    def test_og_via_name_attr(self) -> None:
        html = '<html><head><meta name="og:title" content="Name OG"></head></html>'
        meta = extract_metadata(html)
        assert meta.og_title == "Name OG"

    def test_twitter_via_property_attr(self) -> None:
        html = '<html><head><meta property="twitter:card" content="summary"></head></html>'
        meta = extract_metadata(html)
        assert meta.twitter_card == "summary"


class TestCompletenessScore:
    def test_full_metadata(self) -> None:
        meta = extract_metadata(FULL_HTML)
        score = meta.completeness_score()
        assert score > 0.9

    def test_minimal_metadata(self) -> None:
        meta = extract_metadata("<html><head><title>X</title></head></html>")
        assert meta.completeness_score() < 0.2

    def test_to_dict_excludes_empty(self) -> None:
        meta = PageMetadata(title="Test")
        d = meta.to_dict()
        assert "title" in d
        assert "og_title" not in d
        assert "h1_count" in d
