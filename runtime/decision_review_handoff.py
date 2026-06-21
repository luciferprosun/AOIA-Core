from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.decision_implication_review import (
    DECISION_IMPLICATION_REVIEW_PACKET,
    DECISION_IMPLICATION_REVIEW_PACKET_SCHEMA_VERSION,
    IMPLICATION_REVIEW_BLOCKED,
    IMPLICATION_REVIEW_INVALID,
    READY_FOR_IMPLICATION_REVIEW,
    DecisionImplicationReviewPacket,
)
from runtime.validated_decision_readiness import BLOCKED_SURFACES


DECISION_REVIEW_HANDOFF = "DECISION_REVIEW_HANDOFF"
DECISION_REVIEW_HANDOFF_SCHEMA_VERSION = "1.0"
HANDOFF_READY = "handoff_ready"
HANDOFF_BLOCKED = "blocked"
HANDOFF_INVALID = "invalid"
HANDOFF_BOUNDARY_WARNINGS = (
    "This handoff packet is not approval, permission, execution, dispatch, provider access, prompt generation, provider config, or secret handling.",
    "No runtime authority or automatic progression is granted.",
)
HANDOFF_BOUNDARY_TEXT = (
    "note: not an execution instruction\n"
    "note: no authority granted"
)
_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "prompt_packet_generated",
    "provider_config_mutated",
    "secret_accessed",
    "api_key_accessed",
    "handoff_executes_anything",
)
_IMPLICATION_FIELDS = {
    "object_type",
    "schema_version",
    "status",
    "source_readiness_state",
    "decision_id",
    "decision_hash",
    "decision_status",
    "bundle_id",
    "bundle_hash",
    "eligibility_reasons",
    "blockers",
    "blocked_surfaces",
    "review_questions",
    "warnings",
    "boundary_text",
    "is_review_only",
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "packet_executes_anything",
}


@dataclass(frozen=True)
class DecisionReviewHandoff:
    state: str
    source_implication_state: str
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    implication_reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    blocked_surfaces: tuple[str, ...]
    review_next: tuple[str, ...]
    warnings: tuple[str, ...]
    boundary_text: str
    is_review_only: bool = True
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    prompt_packet_generated: bool = False
    provider_config_mutated: bool = False
    secret_accessed: bool = False
    api_key_accessed: bool = False
    handoff_executes_anything: bool = False
    object_type: str = DECISION_REVIEW_HANDOFF
    schema_version: str = DECISION_REVIEW_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        state = _normalize_state(self.state)
        implication_reasons = _normalize_text_tuple(
            self.implication_reasons,
            "implication_reasons",
        )
        blockers = _normalize_text_tuple(self.blockers, "blockers")
        review_next = _normalize_text_tuple(self.review_next, "review_next")
        warnings = _merge_warnings(self.warnings)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "is_review_only", True)
        object.__setattr__(self, "blocked_surfaces", BLOCKED_SURFACES)
        object.__setattr__(self, "review_next", review_next)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "boundary_text", HANDOFF_BOUNDARY_TEXT)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", DECISION_REVIEW_HANDOFF)
        object.__setattr__(self, "schema_version", DECISION_REVIEW_HANDOFF_SCHEMA_VERSION)

        if state == HANDOFF_READY:
            if blockers:
                raise ValueError("ready review handoff cannot contain blockers")
            if not implication_reasons:
                raise ValueError("ready review handoff requires implication reasons")
            if not review_next:
                raise ValueError("ready review handoff requires review items")
            object.__setattr__(self, "source_implication_state", READY_FOR_IMPLICATION_REVIEW)
            object.__setattr__(self, "implication_reasons", implication_reasons)
            object.__setattr__(self, "blockers", ())
            for field_name in (
                "decision_id",
                "decision_hash",
                "decision_status",
                "bundle_id",
                "bundle_hash",
            ):
                object.__setattr__(
                    self,
                    field_name,
                    _required_text(getattr(self, field_name), field_name),
                )
            return

        if not blockers:
            raise ValueError("fail-closed review handoff requires blockers")
        object.__setattr__(self, "implication_reasons", ())
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self,
            "source_implication_state",
            IMPLICATION_REVIEW_BLOCKED if state == HANDOFF_BLOCKED else IMPLICATION_REVIEW_INVALID,
        )
        for field_name in (
            "decision_id",
            "decision_hash",
            "decision_status",
            "bundle_id",
            "bundle_hash",
        ):
            object.__setattr__(self, field_name, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "state": self.state,
            "source_implication_state": self.source_implication_state,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "decision_status": self.decision_status,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "implication_reasons": list(self.implication_reasons),
            "blockers": list(self.blockers),
            "blocked_surfaces": list(self.blocked_surfaces),
            "review_next": list(self.review_next),
            "warnings": list(self.warnings),
            "boundary_text": self.boundary_text,
            "is_review_only": self.is_review_only,
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "prompt_packet_generated": self.prompt_packet_generated,
            "provider_config_mutated": self.provider_config_mutated,
            "secret_accessed": self.secret_accessed,
            "api_key_accessed": self.api_key_accessed,
            "handoff_executes_anything": self.handoff_executes_anything,
        }


def build_decision_review_handoff(source: object) -> DecisionReviewHandoff:
    try:
        implication = _canonical_implication_packet(source)
    except ValueError as error:
        return _failed_handoff(HANDOFF_INVALID, (str(error),), (), ())

    if implication.status != READY_FOR_IMPLICATION_REVIEW:
        blockers = implication.blockers or ("source implication review is not ready",)
        state = HANDOFF_BLOCKED if implication.status == IMPLICATION_REVIEW_BLOCKED else HANDOFF_INVALID
        return _failed_handoff(
            state,
            blockers,
            implication.review_questions,
            implication.warnings,
        )

    return DecisionReviewHandoff(
        state=HANDOFF_READY,
        source_implication_state=implication.status,
        decision_id=implication.decision_id,
        decision_hash=implication.decision_hash,
        decision_status=implication.decision_status,
        bundle_id=implication.bundle_id,
        bundle_hash=implication.bundle_hash,
        implication_reasons=implication.eligibility_reasons,
        blockers=(),
        blocked_surfaces=implication.blocked_surfaces,
        review_next=implication.review_questions,
        warnings=implication.warnings,
        boundary_text=HANDOFF_BOUNDARY_TEXT,
    )


def decision_review_handoff_to_dict(handoff: object) -> dict[str, Any]:
    if not isinstance(handoff, DecisionReviewHandoff):
        raise ValueError("handoff must be a DecisionReviewHandoff")
    return handoff.to_dict()


def render_decision_review_handoff(handoff: object) -> str:
    if not isinstance(handoff, DecisionReviewHandoff):
        raise ValueError("handoff must be a DecisionReviewHandoff")
    blockers = " | ".join(handoff.blockers)
    blocked_surfaces = " | ".join(handoff.blocked_surfaces)
    review_next = " | ".join(handoff.review_next)
    warnings = " | ".join(handoff.warnings)
    if handoff.state != HANDOFF_READY:
        return (
            f"decision_review_handoff: {handoff.state}\n"
            "is_review_only: true\n"
            f"blockers: {blockers}\n"
            f"blocked_surfaces: {blocked_surfaces}\n"
            f"review_next: {review_next}\n"
            f"warnings: {warnings}\n"
            f"{handoff.boundary_text}"
        )
    reasons = " | ".join(handoff.implication_reasons)
    return (
        "decision_review_handoff: handoff_ready\n"
        "is_review_only: true\n"
        f"source_implication_state: {handoff.source_implication_state}\n"
        f"decision_id: {handoff.decision_id}\n"
        f"decision_hash: {handoff.decision_hash}\n"
        f"decision_status: {handoff.decision_status}\n"
        f"bundle_id: {handoff.bundle_id}\n"
        f"bundle_hash: {handoff.bundle_hash}\n"
        f"implication_reasons: {reasons}\n"
        f"blocked_surfaces: {blocked_surfaces}\n"
        f"review_next: {review_next}\n"
        f"warnings: {warnings}\n"
        f"{handoff.boundary_text}"
    )


def _canonical_implication_packet(source: object) -> DecisionImplicationReviewPacket:
    if isinstance(source, DecisionImplicationReviewPacket):
        mapping = source.to_dict()
    elif isinstance(source, Mapping):
        mapping = dict(source)
    else:
        raise ValueError("source must be a decision implication review packet")
    if set(mapping) != _IMPLICATION_FIELDS:
        raise ValueError("source implication fields do not match the canonical schema")
    if mapping["object_type"] != DECISION_IMPLICATION_REVIEW_PACKET:
        raise ValueError("source implication object type is invalid")
    if mapping["schema_version"] != DECISION_IMPLICATION_REVIEW_PACKET_SCHEMA_VERSION:
        raise ValueError("source implication schema version is invalid")
    try:
        canonical = DecisionImplicationReviewPacket(
            status=mapping["status"],
            source_readiness_state=mapping["source_readiness_state"],
            decision_id=mapping["decision_id"],
            decision_hash=mapping["decision_hash"],
            decision_status=mapping["decision_status"],
            bundle_id=mapping["bundle_id"],
            bundle_hash=mapping["bundle_hash"],
            eligibility_reasons=mapping["eligibility_reasons"],
            blockers=mapping["blockers"],
            blocked_surfaces=mapping["blocked_surfaces"],
            review_questions=mapping["review_questions"],
            warnings=mapping["warnings"],
            boundary_text=mapping["boundary_text"],
            is_review_only=mapping["is_review_only"],
            authority_granted=mapping["authority_granted"],
            execution_allowed=mapping["execution_allowed"],
            dispatch_allowed=mapping["dispatch_allowed"],
            provider_call_allowed=mapping["provider_call_allowed"],
            artifact_write_allowed=mapping["artifact_write_allowed"],
            persistence_allowed=mapping["persistence_allowed"],
            packet_executes_anything=mapping["packet_executes_anything"],
            object_type=mapping["object_type"],
            schema_version=mapping["schema_version"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("source implication packet is malformed") from error
    if canonical.to_dict() != mapping:
        raise ValueError("source implication packet is not canonical")
    return canonical


def _failed_handoff(
    state: str,
    blockers: tuple[str, ...],
    review_next: tuple[str, ...],
    warnings: tuple[str, ...],
) -> DecisionReviewHandoff:
    return DecisionReviewHandoff(
        state=state,
        source_implication_state="",
        decision_id="",
        decision_hash="",
        decision_status="",
        bundle_id="",
        bundle_hash="",
        implication_reasons=(),
        blockers=blockers,
        blocked_surfaces=BLOCKED_SURFACES,
        review_next=review_next,
        warnings=warnings,
        boundary_text=HANDOFF_BOUNDARY_TEXT,
    )


def _normalize_state(value: object) -> str:
    if value not in (HANDOFF_READY, HANDOFF_BLOCKED, HANDOFF_INVALID):
        raise ValueError("state must be a supported review handoff state")
    return str(value)


def _normalize_text_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be a tuple or list")
    return tuple(_required_text(item, field_name) for item in value)


def _merge_warnings(value: object) -> tuple[str, ...]:
    warnings = list(_normalize_text_tuple(value, "warnings"))
    for warning in HANDOFF_BOUNDARY_WARNINGS:
        if warning not in warnings:
            warnings.append(warning)
    return tuple(warnings)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must contain non-empty strings")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must contain non-empty strings")
    return normalized
