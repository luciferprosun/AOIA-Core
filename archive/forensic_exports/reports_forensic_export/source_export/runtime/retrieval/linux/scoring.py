from __future__ import annotations

from dataclasses import dataclass


EXACT_MATCH_SCORE = 100
ALIAS_MATCH_SCORE = 92
SUBCOMMAND_MATCH_SCORE = 84
CATEGORY_MATCH_SCORE = 65
FAMILY_MATCH_SCORE = 58
KEYWORD_MATCH_SCORE = 45
LOW_CONFIDENCE_SCORE = 20
REFUSAL_THRESHOLD = 30


@dataclass(frozen=True)
class ScoreDecision:
    score: int
    confidence: str
    match_type: str


def confidence_for(score: int) -> str:
    if score >= 90:
        return "high"
    if score >= 60:
        return "medium"
    if score >= REFUSAL_THRESHOLD:
        return "low"
    return "none"


def score_decision(match_type: str, base_score: int, result_count: int = 1) -> ScoreDecision:
    bounded_count_bonus = min(max(result_count - 1, 0), 3) * 2
    score = min(100, base_score + bounded_count_bonus)
    return ScoreDecision(score=score, confidence=confidence_for(score), match_type=match_type)


def should_refuse(score: int) -> bool:
    return score < REFUSAL_THRESHOLD
