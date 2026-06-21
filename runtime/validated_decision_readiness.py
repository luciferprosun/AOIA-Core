from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.human_review_decision_projection import (
    HUMAN_REVIEW_DECISION_PROJECTION,
    HUMAN_REVIEW_DECISION_PROJECTION_BOUNDARY_TEXT,
    HUMAN_REVIEW_DECISION_PROJECTION_SCHEMA_VERSION,
    HumanReviewDecisionProjection,
)


VALIDATED_DECISION_READINESS_MAP = "VALIDATED_DECISION_READINESS_MAP"
VALIDATED_DECISION_READINESS_MAP_SCHEMA_VERSION = "1.0"
READINESS_BOUNDARY_TEXT = (
    "note: not an execution instruction\n"
    "note: no authority granted"
)
VALIDATED_SURFACES = (
    "decision record validated",
    "decision language validated",
    "decision projection validated",
    "decision and bundle identifiers preserved",
)
BLOCKED_SURFACES = (
    "execution blocked",
    "provider calls blocked",
    "persistence blocked",
    "artifact writes blocked",
    "dispatcher/router blocked",
    "shell/browser/network blocked",
    "approval gate modification blocked",
    "runtime authority blocked",
)
REQUIRED_BOUNDARIES = (
    "human review required",
    "validation required",
    "projection required",
    "audit review required before any future controlled handoff",
)
FORBIDDEN_TRANSITIONS = (
    "validated decision must not become permission",
    "readiness map must not become instruction",
    "review information must not become execution authority",
)
_READY_SUMMARY = (
    "Validated for review continuation only; all runtime and external surfaces remain blocked."
)
_FAILED_SUMMARY = (
    "Not ready for review continuation; source projection validation did not pass."
)
_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "readiness_map_executes_anything",
)
_PROJECTION_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "projection_executes_anything",
)


@dataclass(frozen=True)
class ValidatedDecisionReadinessMap:
    is_ready_for_review_continuation: bool
    is_review_only: bool
    source_projection_is_validated: bool
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    validated_surfaces: tuple[str, ...]
    blocked_surfaces: tuple[str, ...]
    required_boundaries: tuple[str, ...]
    forbidden_transitions: tuple[str, ...]
    readiness_summary: str
    boundary_text: str
    validation_failure_reasons: tuple[str, ...]
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    readiness_map_executes_anything: bool = False
    object_type: str = VALIDATED_DECISION_READINESS_MAP
    schema_version: str = VALIDATED_DECISION_READINESS_MAP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validated = self.source_projection_is_validated is True
        reasons = _normalize_reasons(self.validation_failure_reasons)
        object.__setattr__(self, "source_projection_is_validated", validated)
        object.__setattr__(self, "is_ready_for_review_continuation", validated)
        object.__setattr__(self, "is_review_only", True)
        object.__setattr__(self, "blocked_surfaces", BLOCKED_SURFACES)
        object.__setattr__(self, "required_boundaries", REQUIRED_BOUNDARIES)
        object.__setattr__(self, "forbidden_transitions", FORBIDDEN_TRANSITIONS)
        object.__setattr__(self, "boundary_text", READINESS_BOUNDARY_TEXT)
        object.__setattr__(self, "validation_failure_reasons", reasons)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", VALIDATED_DECISION_READINESS_MAP)
        object.__setattr__(
            self,
            "schema_version",
            VALIDATED_DECISION_READINESS_MAP_SCHEMA_VERSION,
        )

        if validated:
            if reasons:
                raise ValueError("validated readiness cannot contain validation failures")
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
            object.__setattr__(self, "validated_surfaces", VALIDATED_SURFACES)
            object.__setattr__(self, "readiness_summary", _READY_SUMMARY)
            return

        if not reasons:
            raise ValueError("failed readiness requires a validation failure reason")
        object.__setattr__(self, "validated_surfaces", ())
        object.__setattr__(self, "readiness_summary", _FAILED_SUMMARY)
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
            "is_ready_for_review_continuation": self.is_ready_for_review_continuation,
            "is_review_only": self.is_review_only,
            "source_projection_is_validated": self.source_projection_is_validated,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "decision_status": self.decision_status,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "validated_surfaces": list(self.validated_surfaces),
            "blocked_surfaces": list(self.blocked_surfaces),
            "required_boundaries": list(self.required_boundaries),
            "forbidden_transitions": list(self.forbidden_transitions),
            "readiness_summary": self.readiness_summary,
            "boundary_text": self.boundary_text,
            "validation_failure_reasons": list(self.validation_failure_reasons),
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "readiness_map_executes_anything": self.readiness_map_executes_anything,
        }


def build_validated_decision_readiness_map(
    projection: object,
) -> ValidatedDecisionReadinessMap:
    if not isinstance(projection, HumanReviewDecisionProjection):
        return _failed_readiness(("source must be a human review decision projection",))
    try:
        _verify_projection(projection)
    except ValueError as error:
        reasons = projection.validation_failure_reasons
        return _failed_readiness(reasons or (str(error),))

    return ValidatedDecisionReadinessMap(
        is_ready_for_review_continuation=True,
        is_review_only=True,
        source_projection_is_validated=True,
        decision_id=projection.decision_id,
        decision_hash=projection.decision_hash,
        decision_status=projection.decision_status,
        bundle_id=projection.bundle_id,
        bundle_hash=projection.bundle_hash,
        validated_surfaces=VALIDATED_SURFACES,
        blocked_surfaces=BLOCKED_SURFACES,
        required_boundaries=REQUIRED_BOUNDARIES,
        forbidden_transitions=FORBIDDEN_TRANSITIONS,
        readiness_summary=_READY_SUMMARY,
        boundary_text=READINESS_BOUNDARY_TEXT,
        validation_failure_reasons=(),
    )


def validated_decision_readiness_map_to_dict(readiness: object) -> dict[str, Any]:
    if not isinstance(readiness, ValidatedDecisionReadinessMap):
        raise ValueError("readiness must be a ValidatedDecisionReadinessMap")
    return readiness.to_dict()


def render_validated_decision_readiness_map(readiness: object) -> str:
    if not isinstance(readiness, ValidatedDecisionReadinessMap):
        raise ValueError("readiness must be a ValidatedDecisionReadinessMap")
    blocked = " | ".join(readiness.blocked_surfaces)
    boundaries = " | ".join(readiness.required_boundaries)
    transitions = " | ".join(readiness.forbidden_transitions)
    if not readiness.source_projection_is_validated:
        reasons = " | ".join(readiness.validation_failure_reasons)
        return (
            "validated_decision_readiness_map: NOT_VALIDATED\n"
            "is_ready_for_review_continuation: false\n"
            "is_review_only: true\n"
            f"validation_failure_reasons: {reasons}\n"
            f"blocked_surfaces: {blocked}\n"
            f"required_boundaries: {boundaries}\n"
            f"forbidden_transitions: {transitions}\n"
            f"{readiness.boundary_text}"
        )
    validated = " | ".join(readiness.validated_surfaces)
    return (
        "validated_decision_readiness_map: REVIEW_ONLY\n"
        "is_ready_for_review_continuation: true\n"
        "is_review_only: true\n"
        "source_projection_is_validated: true\n"
        f"decision_id: {readiness.decision_id}\n"
        f"decision_hash: {readiness.decision_hash}\n"
        f"decision_status: {readiness.decision_status}\n"
        f"bundle_id: {readiness.bundle_id}\n"
        f"bundle_hash: {readiness.bundle_hash}\n"
        f"validated_surfaces: {validated}\n"
        f"blocked_surfaces: {blocked}\n"
        f"required_boundaries: {boundaries}\n"
        f"forbidden_transitions: {transitions}\n"
        f"readiness_summary: {readiness.readiness_summary}\n"
        f"{readiness.boundary_text}"
    )


def _verify_projection(projection: HumanReviewDecisionProjection) -> None:
    if any(
        getattr(projection, flag_name, None) is not False
        for flag_name in _PROJECTION_INERT_FLAG_NAMES
    ):
        raise ValueError("source projection must remain inert and authority-free")
    if not projection.is_projected or not projection.is_validated:
        raise ValueError("source projection is not validated")
    if projection.validation_failure_reasons:
        raise ValueError("source projection reports validation failures")
    if projection.boundary_text != HUMAN_REVIEW_DECISION_PROJECTION_BOUNDARY_TEXT:
        raise ValueError("source projection boundary verification failed")
    if projection.object_type != HUMAN_REVIEW_DECISION_PROJECTION:
        raise ValueError("source projection object type verification failed")
    if projection.schema_version != HUMAN_REVIEW_DECISION_PROJECTION_SCHEMA_VERSION:
        raise ValueError("source projection schema verification failed")
    HumanReviewDecisionProjection(
        is_projected=projection.is_projected,
        is_validated=projection.is_validated,
        decision_id=projection.decision_id,
        decision_hash=projection.decision_hash,
        decision_status=projection.decision_status,
        bundle_id=projection.bundle_id,
        bundle_hash=projection.bundle_hash,
        operator_summary=projection.operator_summary,
        boundary_text=projection.boundary_text,
        validation_failure_reasons=projection.validation_failure_reasons,
    )


def _failed_readiness(reasons: object) -> ValidatedDecisionReadinessMap:
    normalized_reasons = _normalize_reasons(reasons)
    if not normalized_reasons:
        normalized_reasons = ("source projection validation failed",)
    return ValidatedDecisionReadinessMap(
        is_ready_for_review_continuation=False,
        is_review_only=True,
        source_projection_is_validated=False,
        decision_id="",
        decision_hash="",
        decision_status="",
        bundle_id="",
        bundle_hash="",
        validated_surfaces=(),
        blocked_surfaces=BLOCKED_SURFACES,
        required_boundaries=REQUIRED_BOUNDARIES,
        forbidden_transitions=FORBIDDEN_TRANSITIONS,
        readiness_summary=_FAILED_SUMMARY,
        boundary_text=READINESS_BOUNDARY_TEXT,
        validation_failure_reasons=normalized_reasons,
    )


def _normalize_reasons(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("validation_failure_reasons must be a tuple or list")
    return tuple(_required_text(reason, "validation failure reason") for reason in value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if normalized == "":
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized
