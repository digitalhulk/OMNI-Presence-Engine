# OPE Scoring Engine v1

OPE scoring is a decision aid, not a search-engine ranking score.

## Finding priority

Priority = Impact x Confidence x Urgency x Fixability.

Normalize each factor to 0-1 before multiplication.

Impact combines visibility, trust, experience and business impact. Confidence is based on evidence quality. Urgency considers volatility, deadlines and damage. Fixability reflects expected effort and reversibility.

## Module health

Module health is evidence-weighted pass coverage, with critical failures capped by severity. Unknown is not treated as pass.

## Global health

Global health is dependency-aware. Upstream failures can reduce confidence in downstream scores, but downstream observations remain visible.

## Anti-gaming rules

Do not optimize the score directly. Do not delete difficult checks to improve the score. Do not substitute third-party estimates for first-party measurements. Keep historical scores and methodology versions.
