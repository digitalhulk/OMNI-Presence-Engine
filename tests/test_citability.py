from ope.citability import analyze_blocks, extract_content_blocks, score_passage


def test_score_is_bounded_and_has_all_signal_groups():
    result = score_passage(
        "Search visibility is the ability of a page to be discovered and understood by retrieval systems. "
        "According to Google, clear page structure helps systems interpret content. "
        "For example, a page can state its primary answer early, use descriptive headings, and include specific facts. "
        "Our research also records original observations.",
        "What is search visibility?",
    )
    assert 0 <= result["total_score"] <= 100
    assert sum(result["breakdown"].values()) == result["total_score"]
    assert len(result["breakdown"]) == 5


def test_analyze_blocks_returns_stable_summary():
    result = analyze_blocks([
        {"heading": "What is SEO?", "content": "SEO is the process of improving a website so search systems can discover and understand its pages."},
        {"heading": "Empty", "content": "   "},
    ])
    assert result["total_blocks_analyzed"] == 1
    assert 0 <= result["average_citability_score"] <= 100
    assert sum(result["grade_distribution"].values()) == 1


def test_extract_content_blocks_ignores_non_content_and_keeps_heading_context():
    html = """
    <html><head><script>ignore()</script><style>.x{}</style></head>
    <body><nav>Ignore navigation</nav><h2>What is SEO?</h2>
    <p>SEO is the process of improving a website so search systems can discover and understand its pages.</p>
    <p>Short</p><script>ignore()</script></body></html>
    """
    blocks = extract_content_blocks(html)
    assert blocks == [{
        "heading": "What is SEO?",
        "content": "SEO is the process of improving a website so search systems can discover and understand its pages.",
    }]
