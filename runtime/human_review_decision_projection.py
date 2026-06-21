from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.human_review_decision import HumanReviewDecision
from runtime.human_review_decision_validator import validate_human_review_decision


HUMAN_REVIEW_DECISION_PROJECTION = "HUMAN_REVIEW_DECISION_PROJECTION"
HUMAN_REVIEW_DECISION_PROJECTION_SCHEMA_VERSION = "1.0"
HUMAN_REVIEW_DECISION_PROJECTION_BOUNDARY_TEXT = (
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
    "projection_executes_anything",
)


@dataclass(frozen=True)
class HumanReviewDecisionProjection:
    is_projected: bool
    is_validated: bool
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    operator_summary: str
    boundary_text: str
    validation_failure_reasons: tuple[str, ...]
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    projection_executes_anything: bool = False
    object_type: str = HUMAN_REVIEW_DECISION_PROJECTION
    schema_version: str = HUMAN_REVIEW_DECISION_PROJECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        projected = self.is_projected is True and self.is_validated is True
        reasons = _normalize_failure_reasons(self.validation_failure_reasons)
        object.__setattr__(self, "is_projected", projected)
        object.__setattr__(self, "is_validated", projected)
        object.__setattr__(
            self,
            "boundary_text",
            HUMAN_REVIEW_DECISION_PROJECTION_BOUNDARY_TEXT,
        )
        object.__setattr__(self, "validation_failure_reasons", reasons)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", HUMAN_REVIEW_DECISION_PROJECTION)
        object.__setattr__(
            self,
            "schema_version",
            HUMAN_REVIEW_DECISION_PROJECTION_SCHEMA_VERSION,
        )

        if projected:
            if reasons:
                raise ValueError("projected review information cannot contain validation failures")
            for field_name in (
                "decision_id",
                "decision_hash",
                "decision_status",
                "bundle_id",
                "bundle_hash",
                "operator_summary",
            ):
                object.__setattr__(
                    self,
                    field_name,
                    _required_text(getattr(self, field_name), field_name),
                )
            return

        if not reasons:
            raise ValueError("failed review information requires a validation failure reason")
        for field_name in (
            "decision_id",
            "decision_hash",
            "decision_status",
            "bundle_id",
            "bundle_hash",
            "operator_summary",
        ):
            object.__setattr__(self, field_name, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "is_projected": self.is_projected,
            "is_validated": self.is_validated,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "decision_status": self.decision_status,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "operator_summary": self.operator_summary,
            "boundary_text": self.boundary_text,
            "validation_failure_reasons": list(self.validation_failure_reasons),
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "projection_executes_anything": self.projection_executes_anything,
        }


def project_human_review_decision(decision: object) -> HumanReviewDecisionProjection:
    try:
        validate_human_review_decision(decision)
    except ValueError as error:
        return _failed_projection(str(error))

    if not isinstance(decision, HumanReviewDecision):
        return _failed_projection("decision validation did not establish the required record type")

    return HumanReviewDecisionProjection(
        is_projected=True,
        is_validated=True,
        decision_id=decision.decision_id,
        decision_hash=decision.decision_hash,
        decision_status=decision.decision_status,
        bundle_id=decision.bundle_id,
        bundle_hash=decision.bundle_hash,
        operator_summary=_operator_summary(decision.decision_status),
        boundary_text=HUMAN_REVIEW_DECISION_PROJECTION_BOUNDARY_TEXT,
        validation_failure_reasons=(),
    )


def human_review_decision_projection_to_dict(projection: object) -> dict[str, Any]:
    if not isinstance(projection, HumanReviewDecisionProjection):
        raise ValueError("projection must be a HumanReviewDecisionProjection")
    return projection.to_dict()


def render_human_review_decision_projection(projection: object) -> str:
    if not isinstance(projection, HumanReviewDecisionProjection):
        raise ValueError("projection must be a HumanReviewDecisionProjection")
    if not projection.is_projected:
        reasons = " | ".join(projection.validation_failure_reasons)
        return (
            "human_review_decision_projection: NOT_PROJECTED\n"
            "validated: false\n"
            f"validation_failure_reasons: {reasons}\n"
            f"{projection.boundary_text}"
        )
    return (
        "human_review_decision_projection: PROJECTED\n"
        "validated: true\n"
        "review_information_only: true\n"
        f"decision_id: {projection.decision_id}\n"
        f"decision_hash: {projection.decision_hash}\n"
        f"decision_status: {projection.decision_status}\n"
        f"bundle_id: {projection.bundle_id}\n"
        f"bundle_hash: {projection.bundle_hash}\n"
        f"operator_summary: {projection.operator_summary}\n"
        f"{projection.boundary_text}"
    )


def _failed_projection(reason: str) -> HumanReviewDecisionProjection:
    return HumanReviewDecisionProjection(
        is_projected=False,
        is_validated=False,
        decision_id="",
        decision_hash="",
        decision_status="",
        bundle_id="",
        bundle_hash="",
        operator_summary="",
        boundary_text=HUMAN_REVIEW_DECISION_PROJECTION_BOUNDARY_TEXT,
        validation_failure_reasons=(_required_text(reason, "validation failure reason"),),
    )


def _operator_summary(decision_status: str) -> str:
    return (
        f"Review information only: {decision_status}. This status does not execute, "
        "dispatch, persist, call providers, or write artifacts, and grants no runtime authority."
    )


def _normalize_failure_reasons(value: object) -> tuple[str, ...]:
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
