from ope.crawler import analyze_robots, effective_access, parse_robots


def test_parse_robots_and_effective_ai_access():
    text = """User-agent: *\nDisallow: /private\nAllow: /private/public\n\nUser-agent: GPTBot\nDisallow: /\nAllow: /public\nSitemap: https://example.com/sitemap.xml\n"""
    rules = parse_robots(text)
    assert effective_access(rules, "GPTBot", "/") == "BLOCK"
    assert effective_access(rules, "GPTBot", "/public") == "ALLOW"
    assert effective_access(rules, "PerplexityBot", "/private") == "BLOCK"


def test_analyze_robots_returns_observed_ai_matrix():
    result = analyze_robots("User-agent: GPTBot\nDisallow: /\n")
    assert result["ai_crawlers"]["GPTBot"] == "BLOCK"
    assert "GPTBot" in result["blocked_ai_crawlers"]
    assert result["rule_count"] == 1


def test_specific_agent_overrides_wildcard():
    result = analyze_robots("User-agent: *\nDisallow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n")
    assert result["ai_crawlers"]["OAI-SearchBot"] == "ALLOW"
    assert result["ai_crawlers"]["ClaudeBot"] == "BLOCK"


def test_equal_length_allow_disallow_tie_favors_allow():
    # RFC 9309 / Google's published robots.txt precedence: when two rules
    # match with exactly the same path length, Allow wins the tie. This is
    # not documented in docs/AI_CRAWLER_INTELLIGENCE.md (which only covers
    # agent-specificity and longest-match), so this pins the tie-break
    # behavior explicitly rather than leaving it implicit.
    rules = parse_robots("User-agent: GPTBot\nDisallow: /private/\nAllow: /private/\n")
    assert effective_access(rules, "GPTBot", "/private/") == "ALLOW"


def test_longer_disallow_beats_shorter_allow():
    rules = parse_robots("User-agent: GPTBot\nAllow: /blog\nDisallow: /blog/private\n")
    assert effective_access(rules, "GPTBot", "/blog/private") == "BLOCK"
    assert effective_access(rules, "GPTBot", "/blog/public") == "ALLOW"
