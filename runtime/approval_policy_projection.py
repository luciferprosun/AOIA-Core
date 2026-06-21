from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from runtime.approval_policy_bridge import (
    APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION,
    APPROVAL_POLICY_EVALUATED_NO_EXECUTION,
    APPROVAL_POLICY_EVALUATION_BRIDGE,
    INERT_APPROVAL_POLICY_EVALUATOR,
    ApprovalPolicyBridgeBoundary,
    ApprovalPolicyBridgeResult,
    ApprovalPolicyBridgeStatus,
)
from runtime.policy_profiles import PolicyDecision
from runtime.provider_flow_audit import redact_audit_text, sanitize_audit_text


# AUTH-1C is not a UI, execution gate, writer, or authority. It renders status only.
APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION = (
    "APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION"
)
APPROVAL_POLICY_PROJECTION_SCHEMA_VERSION = "1.0"
HUMAN_READABLE_AUTHORITY_STATUS_ONLY = "HUMAN_READABLE_AUTHORITY_STATUS_ONLY"
HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION = (
    "HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION"
)

RECORD_ONLY = "RECORD_ONLY"
PROPOSAL_ONLY = "PROPOSAL_ONLY"
NOT_ALLOWED = "NOT_ALLOWED"
FUTURE_MILESTONE_REQUIRED = "FUTURE_MILESTONE_REQUIRED"

NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
NO_PROVIDER_LIVE_CALL = "NO_PROVIDER_LIVE_CALL"
NO_PROVIDER_TRUST_CHANGE = "NO_PROVIDER_TRUST_CHANGE"
NO_GITHUB_ACTION = "NO_GITHUB_ACTION"
NO_CANONICAL_PROMOTION = "NO_CANONICAL_PROMOTION"
PROJECTION_NOT_AUTHORITY = "PROJECTION_NOT_AUTHORITY"
HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY = (
    "HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY"
)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_BLOCKED_CAPABILITIES = (
    "EXECUTION",
    "ARTIFACT_WRITE",
    "PROVIDER_LIVE_CALL",
    "PROVIDER_TRUST_CHANGE",
    "GITHUB_ACTION",
    "CANONICAL_PROMOTION",
)


class ApprovalPolicyProjectionError(ValueError):
    """Raised when a source bridge result is not safe to project."""


class ApprovalPolicyAllowedAs(str, Enum):
    RECORD_ONLY = RECORD_ONLY
    PROPOSAL_ONLY = PROPOSAL_ONLY
    NOT_ALLOWED = NOT_ALLOWED
    FUTURE_MILESTONE_REQUIRED = FUTURE_MILESTONE_REQUIRED


class ApprovalPolicyProjectionBoundary(str, Enum):
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_PROVIDER_LIVE_CALL = NO_PROVIDER_LIVE_CALL
    NO_PROVIDER_TRUST_CHANGE = NO_PROVIDER_TRUST_CHANGE
    NO_GITHUB_ACTION = NO_GITHUB_ACTION
    NO_CANONICAL_PROMOTION = NO_CANONICAL_PROMOTION
    PROJECTION_NOT_AUTHORITY = PROJECTION_NOT_AUTHORITY
    HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY = (
        HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY
    )


@dataclass(frozen=True)
class ApprovalPolicyHumanProjection:
    label: str
    schema_version: str
    projection_role: str
    source_bridge_label: str
    source_bridge_status: str
    source_evaluation_hash: str
    repo_path: str
    branch: str
    head_commit: str
    requested_action_type: str
    requested_target_type: str
    requested_target_hash: str
    requested_target_paths: tuple[str, ...]
    approval_decision: str | None
    policy_profile_name: str | None
    policy_decision: str
    plain_language_summary: str
    plain_language_reason: str
    allowed_as: ApprovalPolicyAllowedAs
    authority_summary: Mapping[str, bool]
    blocked_capabilities: tuple[str, ...]
    required_next_human_step: str
    final_status: str
    safety_boundaries: tuple[ApprovalPolicyProjectionBoundary, ...]
    execution_authority: bool
    artifact_write_authority: bool
    provider_live_call_authority: bool
    provider_trust_authority: bool
    github_authority: bool
    canonical_promotion_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "projection_role": self.projection_role,
            "source_bridge_label": self.source_bridge_label,
            "source_bridge_status": self.source_bridge_status,
            "source_evaluation_hash": self.source_evaluation_hash,
            "repo_path": self.repo_path,
            "branch": self.branch,
            "head_commit": self.head_commit,
            "requested_action_type": self.requested_action_type,
            "requested_target_type": self.requested_target_type,
            "requested_target_hash": self.requested_target_hash,
            "requested_target_paths": list(self.requested_target_paths),
            "approval_decision": self.approval_decision,
            "policy_profile_name": self.policy_profile_name,
            "policy_decision": self.policy_decision,
            "plain_language_summary": self.plain_language_summary,
            "plain_language_reason": self.plain_language_reason,
            "allowed_as": self.allowed_as.value,
            "authority_summary": dict(self.authority_summary),
            "blocked_capabilities": list(self.blocked_capabilities),
            "required_next_human_step": self.required_next_human_step,
            "final_status": self.final_status,
            "safety_boundaries": [item.value for item in self.safety_boundaries],
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_live_call_authority": self.provider_live_call_authority,
            "provider_trust_authority": self.provider_trust_authority,
            "github_authority": self.github_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
        }


def project_approval_policy_evaluation_for_human(
    bridge_result: ApprovalPolicyBridgeResult,
) -> ApprovalPolicyHumanProjection:
    _validate_bridge_result(bridge_result)
    allowed_as = _allowed_as(bridge_result.bridge_status)
    action = _display_text(bridge_result.requested_action_type, 256)
    summary = _summary(allowed_as, action)
    reason = _display_text(bridge_result.bridge_reason, 4096)
    authority = _authority_summary()
    next_step = _required_next_step(allowed_as)
    return ApprovalPolicyHumanProjection(
        label=APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION,
        schema_version=APPROVAL_POLICY_PROJECTION_SCHEMA_VERSION,
        projection_role=HUMAN_READABLE_AUTHORITY_STATUS_ONLY,
        source_bridge_label=bridge_result.label,
        source_bridge_status=bridge_result.bridge_status.value,
        source_evaluation_hash=bridge_result.evaluation_hash,
        repo_path=bridge_result.repo_path,
        branch=bridge_result.branch,
        head_commit=bridge_result.head_commit,
        requested_action_type=bridge_result.requested_action_type,
        requested_target_type=bridge_result.requested_target_type,
        requested_target_hash=bridge_result.requested_target_hash,
        requested_target_paths=tuple(bridge_result.requested_target_paths),
        approval_decision=bridge_result.approval_decision,
        policy_profile_name=bridge_result.policy_profile_name,
        policy_decision=bridge_result.policy_decision,
        plain_language_summary=summary,
        plain_language_reason=reason,
        allowed_as=allowed_as,
        authority_summary=authority,
        blocked_capabilities=_BLOCKED_CAPABILITIES,
        required_next_human_step=next_step,
        final_status=HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION,
        safety_boundaries=_required_boundaries(),
        execution_authority=False,
        artifact_write_authority=False,
        provider_live_call_authority=False,
        provider_trust_authority=False,
        github_authority=False,
        canonical_promotion_authority=False,
    )


def _validate_bridge_result(bridge_result: ApprovalPolicyBridgeResult) -> None:
    if not isinstance(bridge_result, ApprovalPolicyBridgeResult):
        raise ApprovalPolicyProjectionError(
            "bridge_result must be an ApprovalPolicyBridgeResult"
        )
    expected_boundaries = (
        ApprovalPolicyBridgeBoundary.NO_EXECUTION,
        ApprovalPolicyBridgeBoundary.NO_ARTIFACT_WRITE,
        ApprovalPolicyBridgeBoundary.NO_PROVIDER_LIVE_CALL,
        ApprovalPolicyBridgeBoundary.NO_PROVIDER_TRUST_CHANGE,
        ApprovalPolicyBridgeBoundary.NO_GITHUB_ACTION,
        ApprovalPolicyBridgeBoundary.NO_CANONICAL_PROMOTION,
        ApprovalPolicyBridgeBoundary.APPROVAL_NOT_EXECUTION_AUTHORITY,
        ApprovalPolicyBridgeBoundary.POLICY_NOT_EXECUTION_AUTHORITY,
        ApprovalPolicyBridgeBoundary.HASH_MATCH_REQUIRED,
        ApprovalPolicyBridgeBoundary.DEFAULT_DENY,
    )
    if (
        not isinstance(bridge_result.bridge_status, ApprovalPolicyBridgeStatus)
        or bridge_result.label != APPROVAL_POLICY_EVALUATION_BRIDGE
        or bridge_result.schema_version != APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION
        or bridge_result.bridge_role != INERT_APPROVAL_POLICY_EVALUATOR
        or bridge_result.final_status != APPROVAL_POLICY_EVALUATED_NO_EXECUTION
        or tuple(bridge_result.safety_boundaries) != expected_boundaries
        or bridge_result.execution_authority is not False
        or bridge_result.artifact_write_authority is not False
        or bridge_result.provider_live_call_authority is not False
        or bridge_result.provider_trust_authority is not False
        or bridge_result.github_authority is not False
        or bridge_result.canonical_promotion_authority is not False
    ):
        raise ApprovalPolicyProjectionError(
            "bridge result violates the inert AUTH-1B boundary"
        )
    if not _SHA256_HEX.fullmatch(bridge_result.evaluation_hash):
        raise ApprovalPolicyProjectionError("source evaluation hash is invalid")
    _validate_bridge_status_mapping(bridge_result)
    _validate_preserved_identity_text(bridge_result)
    material = bridge_result.to_dict()
    material.pop("created_at_utc")
    material.pop("evaluation_hash")
    if bridge_result.evaluation_hash != _stable_hash(material):
        raise ApprovalPolicyProjectionError("source evaluation hash mismatch")


def _validate_bridge_status_mapping(
    bridge_result: ApprovalPolicyBridgeResult,
) -> None:
    expected_policy = {
        ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY: (
            PolicyDecision.ALLOW_RECORD_ONLY.value
        ),
        ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY: (
            PolicyDecision.ALLOW_PROPOSAL_ONLY.value
        ),
        ApprovalPolicyBridgeStatus.DENIED: PolicyDecision.DENY.value,
        ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE: (
            PolicyDecision.REQUIRES_FUTURE_MILESTONE.value
        ),
    }
    if bridge_result.policy_decision != expected_policy[bridge_result.bridge_status]:
        raise ApprovalPolicyProjectionError(
            "bridge status and policy decision do not match"
        )
    if (
        bridge_result.bridge_status
        in {
            ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY,
            ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY,
        }
        and bridge_result.approval_decision != "APPROVED"
    ):
        raise ApprovalPolicyProjectionError(
            "allowed bridge status requires an APPROVED human decision"
        )


def _validate_preserved_identity_text(
    bridge_result: ApprovalPolicyBridgeResult,
) -> None:
    values = (
        bridge_result.repo_path,
        bridge_result.branch,
        bridge_result.head_commit,
        bridge_result.requested_action_type,
        bridge_result.requested_target_type,
        bridge_result.requested_target_hash,
        *bridge_result.requested_target_paths,
    )
    for value in values:
        if not isinstance(value, str) or not value:
            raise ApprovalPolicyProjectionError(
                "bridge identity fields must be non-empty strings"
            )
        if sanitize_audit_text(value) != value or redact_audit_text(value) != value:
            raise ApprovalPolicyProjectionError(
                "bridge identity fields contain unsafe display text"
            )
    for value in (
        bridge_result.approval_decision,
        bridge_result.policy_profile_name,
        bridge_result.policy_decision,
    ):
        if value is None:
            continue
        if (
            not isinstance(value, str)
            or not value
            or sanitize_audit_text(value) != value
            or redact_audit_text(value) != value
        ):
            raise ApprovalPolicyProjectionError(
                "bridge decision fields contain unsafe display text"
            )


def _allowed_as(status: ApprovalPolicyBridgeStatus) -> ApprovalPolicyAllowedAs:
    return {
        ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY: (
            ApprovalPolicyAllowedAs.RECORD_ONLY
        ),
        ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY: (
            ApprovalPolicyAllowedAs.PROPOSAL_ONLY
        ),
        ApprovalPolicyBridgeStatus.DENIED: ApprovalPolicyAllowedAs.NOT_ALLOWED,
        ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE: (
            ApprovalPolicyAllowedAs.FUTURE_MILESTONE_REQUIRED
        ),
    }[status]


def _summary(allowed_as: ApprovalPolicyAllowedAs, action: str) -> str:
    if allowed_as is ApprovalPolicyAllowedAs.RECORD_ONLY:
        return (
            f"{action} is permitted only as an inert record operation; "
            "it grants no execution or write authority."
        )
    if allowed_as is ApprovalPolicyAllowedAs.PROPOSAL_ONLY:
        return (
            f"{action} is permitted only as an inert proposal operation; "
            "it grants no execution or write authority."
        )
    if allowed_as is ApprovalPolicyAllowedAs.FUTURE_MILESTONE_REQUIRED:
        return (
            f"{action} is not permitted now; a separately reviewed future "
            "milestone is required before authority can be considered."
        )
    return f"{action} is not allowed by the approval and policy evaluation."


def _required_next_step(allowed_as: ApprovalPolicyAllowedAs) -> str:
    if allowed_as is ApprovalPolicyAllowedAs.RECORD_ONLY:
        return (
            "A human may review the inert record; any future authority requires "
            "a separate milestone and a fresh hash-bound decision."
        )
    if allowed_as is ApprovalPolicyAllowedAs.PROPOSAL_ONLY:
        return (
            "A human may review the inert proposal; any future authority requires "
            "a separate milestone and a fresh hash-bound decision."
        )
    if allowed_as is ApprovalPolicyAllowedAs.FUTURE_MILESTONE_REQUIRED:
        return (
            "Do not proceed. Define and review the required future milestone "
            "before considering any new authority."
        )
    return (
        "Do not proceed. Resolve the denial and obtain a new hash-bound human "
        "decision and policy evaluation."
    )


def _authority_summary() -> dict[str, bool]:
    return {
        "execution_authority": False,
        "artifact_write_authority": False,
        "provider_live_call_authority": False,
        "provider_trust_authority": False,
        "github_authority": False,
        "canonical_promotion_authority": False,
    }


def _required_boundaries() -> tuple[ApprovalPolicyProjectionBoundary, ...]:
    return (
        ApprovalPolicyProjectionBoundary.NO_EXECUTION,
        ApprovalPolicyProjectionBoundary.NO_ARTIFACT_WRITE,
        ApprovalPolicyProjectionBoundary.NO_PROVIDER_LIVE_CALL,
        ApprovalPolicyProjectionBoundary.NO_PROVIDER_TRUST_CHANGE,
        ApprovalPolicyProjectionBoundary.NO_GITHUB_ACTION,
        ApprovalPolicyProjectionBoundary.NO_CANONICAL_PROMOTION,
        ApprovalPolicyProjectionBoundary.PROJECTION_NOT_AUTHORITY,
        ApprovalPolicyProjectionBoundary.HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY,
    )


def _display_text(value: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ApprovalPolicyProjectionError("human-readable text must be a string")
    text = redact_audit_text(value)[:max_length]
    return text or "Source text was removed during safety sanitization."


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
