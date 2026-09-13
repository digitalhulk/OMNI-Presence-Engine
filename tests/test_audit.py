from ope.audit import PageParser, _finding


def test_parser_extracts_core_signals():
    p = PageParser()
    p.feed('<html lang="en"><head><title>Test</title><meta name="viewport" content="width=device-width"><link rel="canonical" href="https://example.com/"></head><body><h1>Hello</h1><img src="a.jpg" alt="A"><img src="b.jpg"><script type="application/ld+json">{}</script></body></html>')
    assert p.title == "Test"
    assert p.lang == "en"
    assert p.h1_count == 1
    assert p.images == 2
    assert p.images_missing_alt == 1
    assert p.json_ld == 1
    assert p.canonical == "https://example.com/"


def test_priority_is_bounded():
    f = _finding("T-1", "03-code", "test", "medium", [], [], [], impact=1, urgency=1, fixability=1)
    assert 0 <= f.priority <= 100
