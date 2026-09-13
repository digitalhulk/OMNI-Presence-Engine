from __future__ import annotations

import re
from typing import Any, Iterable


# Adapted from external GEO citability research as independent deterministic
# signals. These are heuristics, not claims about any search engine ranking or
# citation algorithm.
_DEFINITION_PATTERNS = (
    r"\b\w+\s+is\s+(?:a|an|the)\s",
    r"\b\w+\s+refers?\s+to\s",
    r"\b\w+\s+means?\s",
    r"\b\w+\s+(?:can be |are )?defined\s+as\s",
)
_SOURCE_PATTERNS = (
    r"(?:according to|per|from|by)\s+[A-Z]",
    r"\b(?:Gartner|Forrester|McKinsey|Harvard|Stanford|MIT|Google|Microsoft|OpenAI|Anthropic)\b",
)
_PRONOUN_PATTERN = r"\b(?:it|they|them|their|this|that|these|those|he|she|his|her)\b"


def _clamp(value: int, maximum: int) -> int:
    return max(0, min(maximum, value))


def score_passage(text: str, heading: str | None = None) -> dict[str, Any]:
    """Score one content passage for deterministic AI-citability signals."""
    words = text.split()
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    answer = 0
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in _DEFINITION_PATTERNS):
        answer += 15
    first_60 = " ".join(words[:60])
    if re.search(r"\b(?:is|are|was|were|means?|refers?)\b|\d+%|\$[\d,]+", first_60, re.IGNORECASE):
        answer += 15
    if heading and heading.rstrip().endswith("?"):
        answer += 10
    if sentences:
        clear = sum(1 for sentence in sentences if 5 <= len(sentence.split()) <= 25)
        answer += int((clear / len(sentences)) * 10)
    if any(re.search(pattern, text) for pattern in _SOURCE_PATTERNS):
        answer += 10

    containment = 0
    if 134 <= word_count <= 167:
        containment += 10
    elif 100 <= word_count <= 200:
        containment += 7
    elif 80 <= word_count <= 250:
        containment += 4
    pronouns = len(re.findall(_PRONOUN_PATTERN, text, re.IGNORECASE))
    if word_count and pronouns / word_count < 0.02:
        containment += 8
    elif word_count and pronouns / word_count < 0.04:
        containment += 5
    elif word_count and pronouns / word_count < 0.06:
        containment += 3
    entities = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
    containment += 7 if entities >= 3 else 4 if entities >= 1 else 0

    structure = 0
    if sentences:
        average = word_count / len(sentences)
        structure += 8 if 10 <= average <= 20 else 5 if 8 <= average <= 25 else 2
    if re.search(r"\b(?:first|second|third|finally|additionally|moreover|furthermore)\b", text, re.IGNORECASE):
        structure += 4
    if re.search(r"(?:\d+[.)]\s|\b(?:step|tip|point)\s+\d+)", text, re.IGNORECASE):
        structure += 4
    if "\n" in text:
        structure += 4

    statistical = 0
    statistical += min(len(re.findall(r"\d+(?:\.\d+)?%", text)) * 3, 6)
    statistical += min(len(re.findall(r"\$[\d,]+(?:\.\d+)?", text)) * 3, 5)
    statistical += min(len(re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+(?:users|customers|pages|sites|companies|businesses|people|percent|times|x)\b", text, re.IGNORECASE)) * 2, 4)
    if re.search(r"\b20(?:2[3-9]|1\d)\b", text):
        statistical += 2
    if any(re.search(pattern, text) for pattern in _SOURCE_PATTERNS):
        statistical += 2

    uniqueness = 0
    if re.search(r"\b(?:our research|our study|our data|our analysis|our survey|our findings|we found|we discovered|we analyzed|we surveyed|we measured)\b", text, re.IGNORECASE):
        uniqueness += 5
    if re.search(r"\b(?:case study|for example|for instance|in practice|real-world|hands-on)\b", text, re.IGNORECASE):
        uniqueness += 3
    if re.search(r"(?:using|with|via|through)\s+[A-Z][a-z]+", text):
        uniqueness += 2

    breakdown = {
        "answer_block_quality": _clamp(answer, 30),
        "self_containment": _clamp(containment, 25),
        "structural_readability": _clamp(structure, 20),
        "statistical_density": _clamp(statistical, 15),
        "uniqueness_signals": _clamp(uniqueness, 10),
    }
    total = sum(breakdown.values())
    if total >= 80:
        grade, label = "A", "Highly Citable"
    elif total >= 65:
        grade, label = "B", "Good Citability"
    elif total >= 50:
        grade, label = "C", "Moderate Citability"
    elif total >= 35:
        grade, label = "D", "Low Citability"
    else:
        grade, label = "F", "Poor Citability"

    return {
        "heading": heading,
        "word_count": word_count,
        "total_score": total,
        "grade": grade,
        "label": label,
        "breakdown": breakdown,
    }


def analyze_blocks(blocks: Iterable[dict[str, str]]) -> dict[str, Any]:
    """Analyze pre-collected content blocks without performing network I/O."""
    scored = [score_passage(str(block.get("content", "")), block.get("heading")) for block in blocks if str(block.get("content", "")).strip()]
    average = round(sum(item["total_score"] for item in scored) / len(scored), 1) if scored else 0.0
    return {
        "total_blocks_analyzed": len(scored),
        "average_citability_score": average,
        "optimal_length_passages": sum(134 <= item["word_count"] <= 167 for item in scored),
        "grade_distribution": {grade: sum(item["grade"] == grade for item in scored) for grade in ("A", "B", "C", "D", "F")},
        "top_5_citable": sorted(scored, key=lambda item: item["total_score"], reverse=True)[:5],
        "bottom_5_citable": sorted(scored, key=lambda item: item["total_score"])[:5],
    }
