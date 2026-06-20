from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from runtime.human_approval_gate import (
    HashBoundHumanApprovalRecord,
    HumanApprovalDecision,
    HumanApprovalGateError,
    HumanApprovalTargetType,
    verify_hash_bound_human_approval_record,
)
from runtime.policy_profiles import (
    PolicyActionType,
    PolicyDecision,
    PolicyEvaluationResult,
    PolicyProfile,
    PolicyProfileError,
    PolicyProfileName,
    build_policy_profile,
    evaluate_policy_action,
)


# AUTH-1B evaluates authority state only. It cannot execute, write, call, or publish.
APPROVAL_POLICY_EVALUATION_BRIDGE = "APPROVAL_POLICY_EVALUATION_BRIDGE"
APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION = "1.0"
INERT_APPROVAL_POLICY_EVALUATOR = "INERT_APPROVAL_POLICY_EVALUATOR"
APPROVAL_POLICY_EVALUATED_NO_EXECUTION = "APPROVAL_POLICY_EVALUATED_NO_EXECUTION"

NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
NO_PROVIDER_LIVE_CALL = "NO_PROVIDER_LIVE_CALL"
NO_PROVIDER_TRUST_CHANGE = "NO_PROVIDER_TRUST_CHANGE"
NO_GITHUB_ACTION = "NO_GITHUB_ACTION"
NO_CANONICAL_PROMOTION = "NO_CANONICAL_PROMOTION"
APPROVAL_NOT_EXECUTION_AUTHORITY = "APPROVAL_NOT_EXECUTION_AUTHORITY"
POLICY_NOT_EXECUTION_AUTHORITY = "POLICY_NOT_EXECUTION_AUTHORITY"
HASH_MATCH_REQUIRED = "HASH_MATCH_REQUIRED"
DEFAULT_DENY = "DEFAULT_DENY"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_UNSAFE_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class ApprovalPolicyBridgeError(ValueError):
    """Raised for malformed bridge inputs, never to grant fallback authority."""


class ApprovalPolicyBridgeStatus(str, Enum):
    ALLOWED_RECORD_ONLY = "ALLOWED_RECORD_ONLY"
    ALLOWED_PROPOSAL_ONLY = "ALLOWED_PROPOSAL_ONLY"
    DENIED = "DENIED"
    REQUIRES_FUTURE_MILESTONE = "REQUIRES_FUTURE_MILESTONE"


class ApprovalPolicyBridgeBoundary(str, Enum):
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_PROVIDER_LIVE_CALL = NO_PROVIDER_LIVE_CALL
    NO_PROVIDER_TRUST_CHANGE = NO_PROVIDER_TRUST_CHANGE
    NO_GITHUB_ACTION = NO_GITHUB_ACTION
    NO_CANONICAL_PROMOTION = NO_CANONICAL_PROMOTION
    APPROVAL_NOT_EXECUTION_AUTHORITY = APPROVAL_NOT_EXECUTION_AUTHORITY
    POLICY_NOT_EXECUTION_AUTHORITY = POLICY_NOT_EXECUTION_AUTHORITY
    HASH_MATCH_REQUIRED = HASH_MATCH_REQUIRED
    DEFAULT_DENY = DEFAULT_DENY


@dataclass(frozen=True)
class ApprovalPolicyEvaluationRequest:
    repo_path: str
    branch: str
    head_commit: str
    requested_action_type: PolicyActionType | str
    requested_target_type: HumanApprovalTargetType | str
    requested_target_hash: str
    requested_target_paths: tuple[str, ...]
    approval_record: HashBoundHumanApprovalRecord | None
    policy_profile: PolicyProfile | PolicyProfileName | str | None
    provider_flow_audit_hash: str | None
    approval_binding_hash: str | None
    created_at_utc: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "branch": self.branch,
            "head_commit": self.head_commit,
            "requested_action_type": _enum_or_text(self.requested_action_type),
            "requested_target_type": _enum_or_text(self.requested_target_type),
            "requested_target_hash": self.requested_target_hash,
            "requested_target_paths": list(self.requested_target_paths),
            "approval_id": (
                self.approval_record.approval_id
                if isinstance(self.approval_record, HashBoundHumanApprovalRecord)
                else None
            ),
            "policy_profile_name": _policy_profile_name(self.policy_profile),
            "provider_flow_audit_hash": self.provider_flow_audit_hash,
            "approval_binding_hash": self.approval_binding_hash,
            "created_at_utc": self.created_at_utc,
        }


@dataclass(frozen=True)
class ApprovalPolicyBridgeResult:
    label: str
    schema_version: str
    bridge_role: str
    created_at_utc: str | None
    repo_path: str
    branch: str
    head_commit: str
    requested_action_type: str
    requested_target_type: str
    requested_target_hash: str
    requested_target_paths: tuple[str, ...]
    approval_decision: str | None
    approval_binding_hash: str | None
    provider_flow_audit_hash: str | None
    policy_profile_name: str | None
    policy_hash: str | None
    policy_decision: str
    bridge_status: ApprovalPolicyBridgeStatus
    bridge_reason: str
    evaluation_hash: str
    final_status: str
    safety_boundaries: tuple[ApprovalPolicyBridgeBoundary, ...]
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
            "bridge_role": self.bridge_role,
            "created_at_utc": self.created_at_utc,
            "repo_path": self.repo_path,
            "branch": self.branch,
            "head_commit": self.head_commit,
            "requested_action_type": self.requested_action_type,
            "requested_target_type": self.requested_target_type,
            "requested_target_hash": self.requested_target_hash,
            "requested_target_paths": list(self.requested_target_paths),
            "approval_decision": self.approval_decision,
            "approval_binding_hash": self.approval_binding_hash,
            "provider_flow_audit_hash": self.provider_flow_audit_hash,
            "policy_profile_name": self.policy_profile_name,
            "policy_hash": self.policy_hash,
            "policy_decision": self.policy_decision,
            "bridge_status": self.bridge_status.value,
            "bridge_reason": self.bridge_reason,
            "evaluation_hash": self.evaluation_hash,
            "final_status": self.final_status,
            "safety_boundaries": [item.value for item in self.safety_boundaries],
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_live_call_authority": self.provider_live_call_authority,
            "provider_trust_authority": self.provider_trust_authority,
            "github_authority": self.github_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
        }


def build_approval_policy_evaluation_request(
    *,
    repo_path: str,
    branch: str,
    head_commit: str,
    requested_action_type: PolicyActionType | str,
    requested_target_type: HumanApprovalTargetType | str,
    requested_target_hash: str,
    requested_target_paths: Iterable[str] = (),
    approval_record: HashBoundHumanApprovalRecord | None,
    policy_profile: PolicyProfile | PolicyProfileName | str | None,
    provider_flow_audit_hash: str | None = None,
    approval_binding_hash: str | None = None,
    created_at_utc: str | None = None,
) -> ApprovalPolicyEvaluationRequest:
    paths = _text_values(requested_target_paths, "requested_target_paths", 4096)
    record_binding = (
        approval_record.approval_binding_hash
        if isinstance(approval_record, HashBoundHumanApprovalRecord)
        else None
    )
    binding = record_binding if approval_binding_hash is None else approval_binding_hash
    return ApprovalPolicyEvaluationRequest(
        repo_path=_required_text(repo_path, "repo_path", 4096),
        branch=_required_text(branch, "branch", 512),
        head_commit=_required_text(head_commit, "head_commit", 128),
        requested_action_type=_enum_or_required_text(
            requested_action_type,
            "requested_action_type",
            128,
        ),
        requested_target_type=_enum_or_required_text(
            requested_target_type,
            "requested_target_type",
            128,
        ),
        requested_target_hash=_required_text(
            requested_target_hash,
            "requested_target_hash",
            128,
        ),
        requested_target_paths=paths,
        approval_record=approval_record,
        policy_profile=policy_profile,
        provider_flow_audit_hash=_optional_text(
            provider_flow_audit_hash,
            "provider_flow_audit_hash",
            128,
        ),
        approval_binding_hash=_optional_text(
            binding,
            "approval_binding_hash",
            128,
        ),
        created_at_utc=_optional_text(created_at_utc, "created_at_utc", 128),
    )


def evaluate_approval_policy_bridge(
    request: ApprovalPolicyEvaluationRequest,
) -> ApprovalPolicyBridgeResult:
    if not isinstance(request, ApprovalPolicyEvaluationRequest):
        raise ApprovalPolicyBridgeError(
            "request must be an ApprovalPolicyEvaluationRequest"
        )
    approval_decision, approval_hash = _approval_snapshot(request.approval_record)
    policy_name, policy_hash = _policy_snapshot(request.policy_profile)
    action_text = _enum_or_text(request.requested_action_type)
    target_type_text = _enum_or_text(request.requested_target_type)

    if request.approval_record is None:
        return _finish(
            request,
            approval_decision=None,
            approval_hash=request.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="missing approval record defaults to deny",
        )
    if not isinstance(request.approval_record, HashBoundHumanApprovalRecord):
        return _finish(
            request,
            approval_decision=approval_decision,
            approval_hash=request.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="invalid approval record defaults to deny",
        )
    if request.policy_profile is None:
        return _finish(
            request,
            approval_decision=approval_decision,
            approval_hash=approval_hash,
            policy_name=None,
            policy_hash=None,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="missing policy profile defaults to deny",
        )
    try:
        verification = verify_hash_bound_human_approval_record(
            request.approval_record
        )
    except (HumanApprovalGateError, TypeError, ValueError):
        return _finish(
            request,
            approval_decision=approval_decision,
            approval_hash=request.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="approval record verification failed",
        )
    if (
        request.approval_binding_hash is None
        or not _SHA256_HEX.fullmatch(request.approval_binding_hash)
        or request.approval_binding_hash != verification.approval_binding_hash
    ):
        return _finish(
            request,
            approval_decision=verification.decision.value,
            approval_hash=request.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="approval binding hash is missing, invalid, or mismatched",
        )
    mismatch = _approval_request_mismatch(request)
    if mismatch is not None:
        return _finish(
            request,
            approval_decision=verification.decision.value,
            approval_hash=verification.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason=mismatch,
        )
    if verification.decision is not HumanApprovalDecision.APPROVED:
        return _finish(
            request,
            approval_decision=verification.decision.value,
            approval_hash=verification.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="human approval decision is not APPROVED",
        )
    if (
        request.provider_flow_audit_hash is not None
        and request.approval_record.provider_flow_audit_hash is not None
        and request.provider_flow_audit_hash
        != request.approval_record.provider_flow_audit_hash
    ):
        return _finish(
            request,
            approval_decision=verification.decision.value,
            approval_hash=verification.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="provider flow audit hash does not match approval binding",
        )
    try:
        policy_result = evaluate_policy_action(
            profile_name=request.policy_profile,
            action_type=request.requested_action_type,
            repo_path=request.repo_path,
            branch=request.branch,
            head_commit=request.head_commit,
            target_paths=request.requested_target_paths,
            target_hash=request.requested_target_hash,
            approval_binding_hash=request.approval_binding_hash,
            provider_flow_audit_hash=request.provider_flow_audit_hash,
        )
    except (PolicyProfileError, TypeError, ValueError):
        return _finish(
            request,
            approval_decision=verification.decision.value,
            approval_hash=verification.approval_binding_hash,
            policy_name=policy_name,
            policy_hash=policy_hash,
            policy_decision=PolicyDecision.DENY,
            status=ApprovalPolicyBridgeStatus.DENIED,
            reason="policy profile or policy evaluation is invalid",
        )
    return _finish_from_policy(
        request,
        verification.decision,
        verification.approval_binding_hash,
        policy_result,
    )


def _approval_request_mismatch(
    request: ApprovalPolicyEvaluationRequest,
) -> str | None:
    record = request.approval_record
    if not isinstance(record, HashBoundHumanApprovalRecord):
        return "approval record is invalid"
    if request.repo_path != record.repo_path:
        return "requested repo_path does not match approval binding"
    if request.branch != record.branch:
        return "requested branch does not match approval binding"
    if request.head_commit != record.head_commit:
        return "requested head_commit does not match approval binding"
    if (
        not _SHA256_HEX.fullmatch(request.requested_target_hash)
        or request.requested_target_hash != record.target_hash
    ):
        return "requested target hash is invalid or mismatched"
    try:
        target_type = HumanApprovalTargetType(request.requested_target_type)
    except (TypeError, ValueError):
        return "requested target type is invalid"
    if target_type is not record.target_type:
        return "requested target type does not match approval binding"
    return None


def _finish_from_policy(
    request: ApprovalPolicyEvaluationRequest,
    approval_decision: HumanApprovalDecision,
    approval_hash: str,
    policy_result: PolicyEvaluationResult,
) -> ApprovalPolicyBridgeResult:
    mapping = {
        PolicyDecision.ALLOW_RECORD_ONLY: ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY,
        PolicyDecision.ALLOW_PROPOSAL_ONLY: ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY,
        PolicyDecision.DENY: ApprovalPolicyBridgeStatus.DENIED,
        PolicyDecision.REQUIRES_FUTURE_MILESTONE: (
            ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE
        ),
    }
    status = mapping[policy_result.decision]
    reason = (
        "approval and policy permit only an inert record operation"
        if status is ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY
        else "approval and policy permit only an inert proposal operation"
        if status is ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY
        else "policy requires a future milestone and grants no authority"
        if status is ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE
        else "policy default-deny evaluation denied the requested action"
    )
    return _finish(
        request,
        approval_decision=approval_decision.value,
        approval_hash=approval_hash,
        policy_name=policy_result.profile_name,
        policy_hash=policy_result.policy_hash,
        policy_decision=policy_result.decision,
        status=status,
        reason=reason,
        requested_paths=policy_result.target_paths,
    )


def _finish(
    request: ApprovalPolicyEvaluationRequest,
    *,
    approval_decision: str | None,
    approval_hash: str | None,
    policy_name: str | None,
    policy_hash: str | None,
    policy_decision: PolicyDecision,
    status: ApprovalPolicyBridgeStatus,
    reason: str,
    requested_paths: tuple[str, ...] | None = None,
) -> ApprovalPolicyBridgeResult:
    paths = request.requested_target_paths if requested_paths is None else requested_paths
    boundaries = _required_boundaries()
    semantic = {
        "label": APPROVAL_POLICY_EVALUATION_BRIDGE,
        "schema_version": APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION,
        "bridge_role": INERT_APPROVAL_POLICY_EVALUATOR,
        "repo_path": request.repo_path,
        "branch": request.branch,
        "head_commit": request.head_commit,
        "requested_action_type": _enum_or_text(request.requested_action_type),
        "requested_target_type": _enum_or_text(request.requested_target_type),
        "requested_target_hash": request.requested_target_hash,
        "requested_target_paths": list(paths),
        "approval_decision": approval_decision,
        "approval_binding_hash": approval_hash,
        "provider_flow_audit_hash": request.provider_flow_audit_hash,
        "policy_profile_name": policy_name,
        "policy_hash": policy_hash,
        "policy_decision": policy_decision.value,
        "bridge_status": status.value,
        "bridge_reason": reason,
        "final_status": APPROVAL_POLICY_EVALUATED_NO_EXECUTION,
        "safety_boundaries": [item.value for item in boundaries],
        "execution_authority": False,
        "artifact_write_authority": False,
        "provider_live_call_authority": False,
        "provider_trust_authority": False,
        "github_authority": False,
        "canonical_promotion_authority": False,
    }
    evaluation_hash = _stable_hash(semantic)
    return ApprovalPolicyBridgeResult(
        label=APPROVAL_POLICY_EVALUATION_BRIDGE,
        schema_version=APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION,
        bridge_role=INERT_APPROVAL_POLICY_EVALUATOR,
        created_at_utc=request.created_at_utc,
        repo_path=request.repo_path,
        branch=request.branch,
        head_commit=request.head_commit,
        requested_action_type=semantic["requested_action_type"],
        requested_target_type=semantic["requested_target_type"],
        requested_target_hash=request.requested_target_hash,
        requested_target_paths=paths,
        approval_decision=approval_decision,
        approval_binding_hash=approval_hash,
        provider_flow_audit_hash=request.provider_flow_audit_hash,
        policy_profile_name=policy_name,
        policy_hash=policy_hash,
        policy_decision=policy_decision.value,
        bridge_status=status,
        bridge_reason=reason,
        evaluation_hash=evaluation_hash,
        final_status=APPROVAL_POLICY_EVALUATED_NO_EXECUTION,
        safety_boundaries=boundaries,
        execution_authority=False,
        artifact_write_authority=False,
        provider_live_call_authority=False,
        provider_trust_authority=False,
        github_authority=False,
        canonical_promotion_authority=False,
    )


def _approval_snapshot(
    record: HashBoundHumanApprovalRecord | None,
) -> tuple[str | None, str | None]:
    if not isinstance(record, HashBoundHumanApprovalRecord):
        return None, None
    return _enum_or_text(record.decision), record.approval_binding_hash


def _policy_snapshot(
    profile: PolicyProfile | PolicyProfileName | str | None,
) -> tuple[str | None, str | None]:
    if profile is None:
        return None, None
    if isinstance(profile, PolicyProfile):
        return _enum_or_text(profile.profile_name), profile.policy_hash
    if isinstance(profile, (PolicyProfileName, str)):
        try:
            built = build_policy_profile(profile)
        except (PolicyProfileError, TypeError, ValueError):
            return _enum_or_text(profile), None
        return _enum_or_text(profile), built.policy_hash
    return None, None


def _policy_profile_name(
    profile: PolicyProfile | PolicyProfileName | str | None,
) -> str | None:
    return _policy_snapshot(profile)[0]


def _required_boundaries() -> tuple[ApprovalPolicyBridgeBoundary, ...]:
    return (
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


def _enum_or_required_text(value: Enum | str, name: str, max_length: int) -> Enum | str:
    if isinstance(value, Enum):
        return value
    return _required_text(value, name, max_length)


def _enum_or_text(value: Enum | str) -> str:
    return str(value.value) if isinstance(value, Enum) else str(value)


def _text_values(values: Iterable[str], name: str, max_length: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ApprovalPolicyBridgeError(f"{name} must be an iterable of strings")
    try:
        candidates = tuple(values)
    except TypeError as error:
        raise ApprovalPolicyBridgeError(f"{name} must be iterable") from error
    return tuple(_required_text(value, name, max_length) for value in candidates)


def _required_text(value: Any, name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ApprovalPolicyBridgeError(f"{name} must be a string")
    text = value.strip()
    if not text or len(text) > max_length or _UNSAFE_CONTROL.search(text):
        raise ApprovalPolicyBridgeError(f"{name} is malformed")
    return text


def _optional_text(value: str | None, name: str, max_length: int) -> str | None:
    if value is None:
        return None
    return _required_text(value, name, max_length)


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
