from __future__ import annotations

from typing import Any

from runtime.execution_readiness_gate import (
    EXECUTION_READINESS_RECORD,
    EXECUTION_READINESS_REJECTION,
    EXECUTION_READINESS_SCHEMA_VERSION,
    ExecutionReadinessRecord,
    ExecutionReadinessRejection,
)


class OperatorReviewSurface:
    """Read-only AUTH-1G formatter for AUTH-1F terminal inert objects only."""

    _record_note = "not an execution instruction"
    _authority_note = "no authority granted"
    _not_reviewable = "NOT_REVIEWABLE"

    def __new__(cls, *_args: object, **_kwargs: object) -> "OperatorReviewSurface":
        raise TypeError("OperatorReviewSurface is static-only")

    @staticmethod
    def render(record_or_rejection: object) -> str:
        summary = OperatorReviewSurface.summary_fields(record_or_rejection)
        if summary["reviewable"] is not True:
            return "\n".join(
                (
                    "operator_review_surface: NOT_REVIEWABLE",
                    f"status: {summary['status']}",
                    f"reason: {summary['reason']}",
                    f"note: {OperatorReviewSurface._record_note}",
                    f"note: {OperatorReviewSurface._authority_note}",
                )
            )

        ordered_keys = (
            "object_type",
            "status",
            "assembly_hash",
            "surface_hash",
            "source_status_summary",
            "rejection_reason",
            "execution_allowed",
            "dispatch_allowed",
            "artifact_write_allowed",
            "provider_call_allowed",
            "github_action_allowed",
        )
        lines = ["operator_review_surface: REVIEWABLE"]
        for key in ordered_keys:
            value = summary.get(key)
            if value is None:
                continue
            lines.append(f"{key}: {value}")
        lines.append(f"note: {OperatorReviewSurface._record_note}")
        lines.append(f"note: {OperatorReviewSurface._authority_note}")
        return "\n".join(lines)

    @staticmethod
    def summary_fields(record_or_rejection: object) -> dict[str, bool | str]:
        if isinstance(record_or_rejection, ExecutionReadinessRecord):
            if not OperatorReviewSurface._valid_record(record_or_rejection):
                return OperatorReviewSurface._fail_closed(
                    "malformed ExecutionReadinessRecord"
                )
            return {
                "reviewable": True,
                "object_type": record_or_rejection.label,
                "status": record_or_rejection.readiness_status,
                "assembly_hash": record_or_rejection.assembly_hash,
                "surface_hash": record_or_rejection.readiness_hash,
                "source_status_summary": record_or_rejection.source_status_summary,
                "execution_allowed": record_or_rejection.execution_allowed,
                "dispatch_allowed": record_or_rejection.dispatch_allowed,
                "artifact_write_allowed": record_or_rejection.artifact_write_allowed,
                "provider_call_allowed": record_or_rejection.provider_call_allowed,
                "github_action_allowed": record_or_rejection.github_action_allowed,
            }
        if isinstance(record_or_rejection, ExecutionReadinessRejection):
            if not OperatorReviewSurface._valid_rejection(record_or_rejection):
                return OperatorReviewSurface._fail_closed(
                    "malformed ExecutionReadinessRejection"
                )
            return {
                "reviewable": True,
                "object_type": record_or_rejection.label,
                "status": "READINESS_REJECTED",
                "assembly_hash": record_or_rejection.assembly_hash or "NOT_AVAILABLE",
                "surface_hash": record_or_rejection.rejection_hash,
                "source_status_summary": record_or_rejection.source_status_summary,
                "rejection_reason": record_or_rejection.rejection_reason,
                "execution_allowed": record_or_rejection.execution_allowed,
                "dispatch_allowed": record_or_rejection.dispatch_allowed,
                "artifact_write_allowed": record_or_rejection.artifact_write_allowed,
                "provider_call_allowed": record_or_rejection.provider_call_allowed,
                "github_action_allowed": record_or_rejection.github_action_allowed,
            }
        return OperatorReviewSurface._fail_closed(
            "input is not an AUTH-1F readiness object"
        )

    @staticmethod
    def _valid_record(value: ExecutionReadinessRecord) -> bool:
        return (
            value.label == EXECUTION_READINESS_RECORD
            and value.schema_version == EXECUTION_READINESS_SCHEMA_VERSION
            and OperatorReviewSurface._valid_text(value.readiness_status)
            and OperatorReviewSurface._valid_text(value.assembly_hash)
            and OperatorReviewSurface._valid_text(value.readiness_hash)
            and OperatorReviewSurface._valid_text(value.source_status_summary)
            and value.execution_allowed is False
            and value.dispatch_allowed is False
            and value.artifact_write_allowed is False
            and value.provider_call_allowed is False
            and value.github_action_allowed is False
        )

    @staticmethod
    def _valid_rejection(value: ExecutionReadinessRejection) -> bool:
        assembly_hash = value.assembly_hash
        return (
            value.label == EXECUTION_READINESS_REJECTION
            and value.schema_version == EXECUTION_READINESS_SCHEMA_VERSION
            and OperatorReviewSurface._valid_text(value.rejection_reason)
            and (assembly_hash is None or OperatorReviewSurface._valid_text(assembly_hash))
            and OperatorReviewSurface._valid_text(value.rejection_hash)
            and OperatorReviewSurface._valid_text(value.source_status_summary)
            and value.execution_allowed is False
            and value.dispatch_allowed is False
            and value.artifact_write_allowed is False
            and value.provider_call_allowed is False
            and value.github_action_allowed is False
        )

    @staticmethod
    def _valid_text(value: Any) -> bool:
        return isinstance(value, str) and value.strip() != ""

    @staticmethod
    def _fail_closed(reason: str) -> dict[str, bool | str]:
        return {
            "reviewable": False,
            "status": OperatorReviewSurface._not_reviewable,
            "reason": reason,
        }
