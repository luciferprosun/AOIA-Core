from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.validated_decision_readiness import (
    BLOCKED_SURFACES,
    VALIDATED_DECISION_READINESS_MAP,
    VALIDATED_DECISION_READINESS_MAP_SCHEMA_VERSION,
    ValidatedDecisionReadinessMap,
)


DECISION_IMPLICATION_REVIEW_PACKET = "DECISION_IMPLICATION_REVIEW_PACKET"
DECISION_IMPLICATION_REVIEW_PACKET_SCHEMA_VERSION = "1.0"
READY_FOR_IMPLICATION_REVIEW = "ready_for_implication_review"
IMPLICATION_REVIEW_BLOCKED = "blocked"
IMPLICATION_REVIEW_INVALID = "invalid"
SOURCE_READY_FOR_REVIEW_CONTINUATION = "ready_for_review_continuation"
SOURCE_NOT_READY_FOR_REVIEW_CONTINUATION = "not_ready_for_review_continuation"
SOURCE_READINESS_INVALID = "invalid"
REVIEW_QUESTIONS = (
    "Which downstream implications require human review?",
    "Do any implications contradict the validated decision?",
    "Which existing boundaries must remain in force?",
    "What evidence is required before any future controlled handoff?",
)
BOUNDARY_WARNINGS = (
    "This implication review packet is not approval, permission, or execution readiness.",
    "It grants no provider, dispatch, persistence, artifact-write, shell, browser, or network authority.",
)
IMPLICATION_REVIEW_BOUNDARY_TEXT = (
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
    "packet_executes_anything",
)
_READINESS_FIELDS = {
    "object_type",
    "schema_version",
    "is_ready_for_review_continuation",
    "is_review_only",
    "source_projection_is_validated",
    "decision_id",
    "decision_hash",
    "decision_status",
    "bundle_id",
    "bundle_hash",
    "validated_surfaces",
    "blocked_surfaces",
    "required_boundaries",
    "forbidden_transitions",
    "readiness_summary",
    "boundary_text",
    "validation_failure_reasons",
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "readiness_map_executes_anything",
}


@dataclass(frozen=True)
class DecisionImplicationReviewPacket:
    status: str
    source_readiness_state: str
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    eligibility_reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    blocked_surfaces: tuple[str, ...]
    review_questions: tuple[str, ...]
    warnings: tuple[str, ...]
    boundary_text: str
    is_review_only: bool = True
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    packet_executes_anything: bool = False
    object_type: str = DECISION_IMPLICATION_REVIEW_PACKET
    schema_version: str = DECISION_IMPLICATION_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        status = _normalize_status(self.status)
        eligibility = _normalize_text_tuple(self.eligibility_reasons, "eligibility_reasons")
        blockers = _normalize_text_tuple(self.blockers, "blockers")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "is_review_only", True)
        object.__setattr__(self, "blocked_surfaces", BLOCKED_SURFACES)
        object.__setattr__(self, "review_questions", REVIEW_QUESTIONS)
        object.__setattr__(self, "warnings", BOUNDARY_WARNINGS)
        object.__setattr__(self, "boundary_text", IMPLICATION_REVIEW_BOUNDARY_TEXT)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", DECISION_IMPLICATION_REVIEW_PACKET)
        object.__setattr__(
            self,
            "schema_version",
            DECISION_IMPLICATION_REVIEW_PACKET_SCHEMA_VERSION,
        )

        if status == READY_FOR_IMPLICATION_REVIEW:
            if blockers:
                raise ValueError("ready implication review packet cannot contain blockers")
            if not eligibility:
                raise ValueError("ready implication review packet requires eligibility reasons")
            object.__setattr__(
                self,
                "source_readiness_state",
                SOURCE_READY_FOR_REVIEW_CONTINUATION,
            )
            object.__setattr__(self, "eligibility_reasons", eligibility)
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
            raise ValueError("fail-closed implication review packet requires blockers")
        object.__setattr__(self, "eligibility_reasons", ())
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self,
            "source_readiness_state",
            (
                SOURCE_NOT_READY_FOR_REVIEW_CONTINUATION
                if status == IMPLICATION_REVIEW_BLOCKED
                else SOURCE_READINESS_INVALID
            ),
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
            "status": self.status,
            "source_readiness_state": self.source_readiness_state,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "decision_status": self.decision_status,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "eligibility_reasons": list(self.eligibility_reasons),
            "blockers": list(self.blockers),
            "blocked_surfaces": list(self.blocked_surfaces),
            "review_questions": list(self.review_questions),
            "warnings": list(self.warnings),
            "boundary_text": self.boundary_text,
            "is_review_only": self.is_review_only,
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "packet_executes_anything": self.packet_executes_anything,
        }


def build_decision_implication_review_packet(source: object) -> DecisionImplicationReviewPacket:
    try:
        readiness = _canonical_readiness(source)
    except ValueError as error:
        return _failed_packet(IMPLICATION_REVIEW_INVALID, (str(error),))

    if (
        not readiness.is_ready_for_review_continuation
        or not readiness.source_projection_is_validated
        or not readiness.is_review_only
        or readiness.validation_failure_reasons
    ):
        blockers = readiness.validation_failure_reasons or (
            "source readiness is not ready for implication review",
        )
        return _failed_packet(IMPLICATION_REVIEW_BLOCKED, blockers)

    reasons = tuple(readiness.validated_surfaces) + (readiness.readiness_summary,)
    return DecisionImplicationReviewPacket(
        status=READY_FOR_IMPLICATION_REVIEW,
        source_readiness_state=SOURCE_READY_FOR_REVIEW_CONTINUATION,
        decision_id=readiness.decision_id,
        decision_hash=readiness.decision_hash,
        decision_status=readiness.decision_status,
        bundle_id=readiness.bundle_id,
        bundle_hash=readiness.bundle_hash,
        eligibility_reasons=reasons,
        blockers=(),
        blocked_surfaces=readiness.blocked_surfaces,
        review_questions=REVIEW_QUESTIONS,
        warnings=BOUNDARY_WARNINGS,
        boundary_text=IMPLICATION_REVIEW_BOUNDARY_TEXT,
    )


def decision_implication_review_packet_to_dict(packet: object) -> dict[str, Any]:
    if not isinstance(packet, DecisionImplicationReviewPacket):
        raise ValueError("packet must be a DecisionImplicationReviewPacket")
    return packet.to_dict()


def render_decision_implication_review_packet(packet: object) -> str:
    if not isinstance(packet, DecisionImplicationReviewPacket):
        raise ValueError("packet must be a DecisionImplicationReviewPacket")
    blockers = " | ".join(packet.blockers)
    blocked_surfaces = " | ".join(packet.blocked_surfaces)
    questions = " | ".join(packet.review_questions)
    warnings = " | ".join(packet.warnings)
    if packet.status != READY_FOR_IMPLICATION_REVIEW:
        return (
            f"decision_implication_review_packet: {packet.status}\n"
            "is_review_only: true\n"
            f"blockers: {blockers}\n"
            f"blocked_surfaces: {blocked_surfaces}\n"
            f"warnings: {warnings}\n"
            f"{packet.boundary_text}"
        )
    reasons = " | ".join(packet.eligibility_reasons)
    return (
        "decision_implication_review_packet: ready_for_implication_review\n"
        "is_review_only: true\n"
        f"source_readiness_state: {packet.source_readiness_state}\n"
        f"decision_id: {packet.decision_id}\n"
        f"decision_hash: {packet.decision_hash}\n"
        f"decision_status: {packet.decision_status}\n"
        f"bundle_id: {packet.bundle_id}\n"
        f"bundle_hash: {packet.bundle_hash}\n"
        f"eligibility_reasons: {reasons}\n"
        f"blocked_surfaces: {blocked_surfaces}\n"
        f"review_questions: {questions}\n"
        f"warnings: {warnings}\n"
        f"{packet.boundary_text}"
    )


def _canonical_readiness(source: object) -> ValidatedDecisionReadinessMap:
    if isinstance(source, ValidatedDecisionReadinessMap):
        mapping = source.to_dict()
    elif isinstance(source, Mapping):
        mapping = dict(source)
    else:
        raise ValueError("source must be a validated decision readiness map")
    if set(mapping) != _READINESS_FIELDS:
        raise ValueError("source readiness fields do not match the canonical schema")
    if mapping["object_type"] != VALIDATED_DECISION_READINESS_MAP:
        raise ValueError("source readiness object type is invalid")
    if mapping["schema_version"] != VALIDATED_DECISION_READINESS_MAP_SCHEMA_VERSION:
        raise ValueError("source readiness schema version is invalid")
    try:
        canonical = ValidatedDecisionReadinessMap(
            is_ready_for_review_continuation=mapping["is_ready_for_review_continuation"],
            is_review_only=mapping["is_review_only"],
            source_projection_is_validated=mapping["source_projection_is_validated"],
            decision_id=mapping["decision_id"],
            decision_hash=mapping["decision_hash"],
            decision_status=mapping["decision_status"],
            bundle_id=mapping["bundle_id"],
            bundle_hash=mapping["bundle_hash"],
            validated_surfaces=mapping["validated_surfaces"],
            blocked_surfaces=mapping["blocked_surfaces"],
            required_boundaries=mapping["required_boundaries"],
            forbidden_transitions=mapping["forbidden_transitions"],
            readiness_summary=mapping["readiness_summary"],
            boundary_text=mapping["boundary_text"],
            validation_failure_reasons=mapping["validation_failure_reasons"],
            authority_granted=mapping["authority_granted"],
            execution_allowed=mapping["execution_allowed"],
            dispatch_allowed=mapping["dispatch_allowed"],
            provider_call_allowed=mapping["provider_call_allowed"],
            artifact_write_allowed=mapping["artifact_write_allowed"],
            persistence_allowed=mapping["persistence_allowed"],
            readiness_map_executes_anything=mapping["readiness_map_executes_anything"],
            object_type=mapping["object_type"],
            schema_version=mapping["schema_version"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("source readiness is malformed") from error
    if canonical.to_dict() != mapping:
        raise ValueError("source readiness is not canonical")
    return canonical


def _failed_packet(status: str, blockers: tuple[str, ...]) -> DecisionImplicationReviewPacket:
    return DecisionImplicationReviewPacket(
        status=status,
        source_readiness_state="",
        decision_id="",
        decision_hash="",
        decision_status="",
        bundle_id="",
        bundle_hash="",
        eligibility_reasons=(),
        blockers=blockers,
        blocked_surfaces=BLOCKED_SURFACES,
        review_questions=REVIEW_QUESTIONS,
        warnings=BOUNDARY_WARNINGS,
        boundary_text=IMPLICATION_REVIEW_BOUNDARY_TEXT,
    )


def _normalize_status(value: object) -> str:
    if value not in (
        READY_FOR_IMPLICATION_REVIEW,
        IMPLICATION_REVIEW_BLOCKED,
        IMPLICATION_REVIEW_INVALID,
    ):
        raise ValueError("status must be a supported implication review state")
    return str(value)


def _normalize_text_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be a tuple or list")
    return tuple(_required_text(item, field_name) for item in value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must contain non-empty strings")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must contain non-empty strings")
    return normalized
