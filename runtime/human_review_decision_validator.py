from __future__ import annotations

from runtime.human_review_decision import (
    HUMAN_REVIEW_DECISION_BOUNDARY_TEXT,
    HumanReviewDecision,
)


FORBIDDEN_DECISION_LANGUAGE = (
    "authority granted",
    "runtime authority",
    "execution approved",
    "execution authorized",
    "execute now",
    "execute this",
    "run this command",
    "run the command",
    "dispatch now",
    "dispatch this",
    "call the provider",
    "provider call authorized",
    "write the artifact",
    "artifact write authorized",
    "persist this",
    "save to database",
    "deploy now",
    "commit this",
    "push this",
)
_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "decision_executes_anything",
)


def validate_human_review_decision(decision: object) -> None:
    if not isinstance(decision, HumanReviewDecision):
        raise ValueError("decision must be a HumanReviewDecision")
    if any(getattr(decision, flag_name, None) is not False for flag_name in _INERT_FLAG_NAMES):
        raise ValueError("decision must be inert and authority-free")
    if decision.boundary_text != HUMAN_REVIEW_DECISION_BOUNDARY_TEXT:
        raise ValueError("decision boundary_text verification failed")

    validate_decision_language(decision.human_note)
    _verify_decision_integrity(decision)


def validate_decision_language(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("decision language must be a string")
    normalized = " ".join(value.casefold().split())
    for forbidden_phrase in FORBIDDEN_DECISION_LANGUAGE:
        if forbidden_phrase in normalized:
            raise ValueError("decision language implies forbidden runtime authority")


def _verify_decision_integrity(decision: HumanReviewDecision) -> None:
    HumanReviewDecision(
        decision_id=decision.decision_id,
        created_at_utc=decision.created_at_utc,
        bundle_id=decision.bundle_id,
        bundle_hash=decision.bundle_hash,
        decision_status=decision.decision_status,
        human_note=decision.human_note,
        boundary_text=decision.boundary_text,
        decision_hash=decision.decision_hash,
    )
