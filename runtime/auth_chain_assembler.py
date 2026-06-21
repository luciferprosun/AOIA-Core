from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from runtime.approval_policy_bridge import (
    ApprovalPolicyBridgeError,
    ApprovalPolicyBridgeResult,
    ApprovalPolicyBridgeStatus,
    build_approval_policy_evaluation_request,
    evaluate_approval_policy_bridge,
)
from runtime.approval_policy_projection import (
    ApprovalPolicyHumanProjection,
    ApprovalPolicyProjectionError,
    project_approval_policy_evaluation_for_human,
)
from runtime.human_approval_gate import (
    HashBoundHumanApprovalRecord,
    HumanApprovalGateError,
    verify_hash_bound_human_approval_record,
)
from runtime.policy_profiles import (
    PolicyActionType,
    PolicyProfile,
    PolicyProfileError,
    evaluate_policy_action,
)
from runtime.proposal_intake import ProposalIntake
from runtime.proposal_review_packet import ProposalReviewPacket
from runtime.review_packet_projection import (
    AuthorityStatusProjectionError,
    HumanReadableReviewPacketProjection,
    create_human_readable_review_packet_projection,
)


# AUTH-1E assembles review data only. It is not an execution gate or authority.
INERT_AUTH_CHAIN_ASSEMBLY = "INERT_AUTH_CHAIN_ASSEMBLY"
AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION = "1.0"
END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY = (
    "END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY"
)
AUTH_CHAIN_ASSEMBLED_NO_EXECUTION = "AUTH_CHAIN_ASSEMBLED_NO_EXECUTION"

NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
NO_PROVIDER_LIVE_CALL = "NO_PROVIDER_LIVE_CALL"
NO_PROVIDER_TRUST_CHANGE = "NO_PROVIDER_TRUST_CHANGE"
NO_GITHUB_ACTION = "NO_GITHUB_ACTION"
NO_CANONICAL_PROMOTION = "NO_CANONICAL_PROMOTION"
ASSEMBLY_NOT_AUTHORITY = "ASSEMBLY_NOT_AUTHORITY"
REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION = (
    "REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION"
)
DEFAULT_DENY_ON_INVALID_CHAIN = "DEFAULT_DENY_ON_INVALID_CHAIN"


class AuthChainAssemblyError(ValueError):
    """Raised only for an invalid assembler call boundary."""


class AuthChainAssemblyStatus(str, Enum):
    AUTH_CHAIN_RECORD_ONLY = "AUTH_CHAIN_RECORD_ONLY"
    AUTH_CHAIN_PROPOSAL_ONLY = "AUTH_CHAIN_PROPOSAL_ONLY"
    AUTH_CHAIN_DENIED = "AUTH_CHAIN_DENIED"
    AUTH_CHAIN_REQUIRES_FUTURE_MILESTONE = (
        "AUTH_CHAIN_REQUIRES_FUTURE_MILESTONE"
    )
    AUTH_CHAIN_INVALID = "AUTH_CHAIN_INVALID"


class AuthChainAssemblyBoundary(str, Enum):
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_PROVIDER_LIVE_CALL = NO_PROVIDER_LIVE_CALL
    NO_PROVIDER_TRUST_CHANGE = NO_PROVIDER_TRUST_CHANGE
    NO_GITHUB_ACTION = NO_GITHUB_ACTION
    NO_CANONICAL_PROMOTION = NO_CANONICAL_PROMOTION
    ASSEMBLY_NOT_AUTHORITY = ASSEMBLY_NOT_AUTHORITY
    REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION = (
        REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION
    )
    DEFAULT_DENY_ON_INVALID_CHAIN = DEFAULT_DENY_ON_INVALID_CHAIN


@dataclass(frozen=True)
class AuthChainAssemblyResult:
    label: str
    schema_version: str
    assembly_role: str
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
    bridge_status: str | None
    bridge_evaluation_hash: str | None
    human_projection_status: str | None
    review_packet_status: str | None
    authority_status_present: bool
    assembly_status: AuthChainAssemblyStatus
    assembly_reason: str
    assembly_hash: str
    review_packet: HumanReadableReviewPacketProjection | None
    final_status: str
    safety_boundaries: tuple[AuthChainAssemblyBoundary, ...]
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
            "assembly_role": self.assembly_role,
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
            "bridge_status": self.bridge_status,
            "bridge_evaluation_hash": self.bridge_evaluation_hash,
            "human_projection_status": self.human_projection_status,
            "review_packet_status": self.review_packet_status,
            "authority_status_present": self.authority_status_present,
            "assembly_status": self.assembly_status.value,
            "assembly_reason": self.assembly_reason,
            "assembly_hash": self.assembly_hash,
            "review_packet": (
                self.review_packet.to_dict()
                if self.review_packet is not None
                else None
            ),
            "final_status": self.final_status,
            "safety_boundaries": [item.value for item in self.safety_boundaries],
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_live_call_authority": self.provider_live_call_authority,
            "provider_trust_authority": self.provider_trust_authority,
            "github_authority": self.github_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
        }


def assemble_inert_auth_chain(
    *,
    repo_path: str,
    branch: str,
    head_commit: str,
    requested_action_type: PolicyActionType | str,
    requested_target_type: Enum | str,
    requested_target_hash: str,
    requested_target_paths: Iterable[str] = (),
    approval_record: HashBoundHumanApprovalRecord | None,
    policy_profile: PolicyProfile | None,
    base_proposal: ProposalIntake | None = None,
    base_review_packet: ProposalReviewPacket | None = None,
    provider_flow_audit_hash: str | None = None,
    created_at_utc: str | None = None,
) -> AuthChainAssemblyResult:
    action_text = _enum_text(requested_action_type)
    target_type_text = _enum_text(requested_target_type)
    paths = _paths_or_none(requested_target_paths)
    audit_hash = (
        provider_flow_audit_hash
        if provider_flow_audit_hash is not None
        else approval_record.provider_flow_audit_hash
        if isinstance(approval_record, HashBoundHumanApprovalRecord)
        else None
    )
    if paths is None:
        return _finish(
            repo_path=_text(repo_path),
            branch=_text(branch),
            head_commit=_text(head_commit),
            action_type=action_text,
            target_type=target_type_text,
            target_hash=_text(requested_target_hash),
            target_paths=(),
            approval_record=approval_record,
            policy_profile=policy_profile,
            provider_flow_audit_hash=audit_hash,
            status=AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
            reason="requested target paths are malformed",
            created_at_utc=created_at_utc,
        )
    if not isinstance(approval_record, HashBoundHumanApprovalRecord):
        return _invalid(
            repo_path,
            branch,
            head_commit,
            action_text,
            target_type_text,
            requested_target_hash,
            paths,
            approval_record,
            policy_profile,
            audit_hash,
            "approval record is missing or invalid",
            created_at_utc,
        )
    if not isinstance(policy_profile, PolicyProfile):
        return _invalid(
            repo_path,
            branch,
            head_commit,
            action_text,
            target_type_text,
            requested_target_hash,
            paths,
            approval_record,
            policy_profile,
            audit_hash,
            "policy profile is missing or invalid",
            created_at_utc,
        )
    if not isinstance(base_proposal, ProposalIntake) or not isinstance(
        base_review_packet,
        ProposalReviewPacket,
    ):
        return _invalid(
            repo_path,
            branch,
            head_commit,
            action_text,
            target_type_text,
            requested_target_hash,
            paths,
            approval_record,
            policy_profile,
            audit_hash,
            "base proposal and review packet are required",
            created_at_utc,
        )

    try:
        verification = verify_hash_bound_human_approval_record(approval_record)
        evaluate_policy_action(
            profile_name=policy_profile,
            action_type=requested_action_type,
            repo_path=repo_path,
            branch=branch,
            head_commit=head_commit,
            target_paths=paths,
            target_hash=requested_target_hash,
            approval_binding_hash=verification.approval_binding_hash,
            provider_flow_audit_hash=audit_hash,
        )
        bridge_request = build_approval_policy_evaluation_request(
            repo_path=repo_path,
            branch=branch,
            head_commit=head_commit,
            requested_action_type=requested_action_type,
            requested_target_type=requested_target_type,
            requested_target_hash=requested_target_hash,
            requested_target_paths=paths,
            approval_record=approval_record,
            policy_profile=policy_profile,
            provider_flow_audit_hash=audit_hash,
            created_at_utc=created_at_utc,
        )
        bridge = evaluate_approval_policy_bridge(bridge_request)
        human_projection = project_approval_policy_evaluation_for_human(bridge)
        review_projection = create_human_readable_review_packet_projection(
            proposal=base_proposal,
            review_packet=base_review_packet,
            authority_projection=human_projection,
        )
        if review_projection.authority_status is None:
            raise AuthChainAssemblyError("authority_status attachment is missing")
    except (
        ApprovalPolicyBridgeError,
        ApprovalPolicyProjectionError,
        AuthorityStatusProjectionError,
        AuthChainAssemblyError,
        HumanApprovalGateError,
        PolicyProfileError,
        TypeError,
        ValueError,
    ):
        return _finish(
            repo_path=_text(repo_path),
            branch=_text(branch),
            head_commit=_text(head_commit),
            action_type=action_text,
            target_type=target_type_text,
            target_hash=_text(requested_target_hash),
            target_paths=paths,
            approval_record=approval_record,
            policy_profile=policy_profile,
            provider_flow_audit_hash=audit_hash,
            status=AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
            reason="AUTH chain validation or assembly failed closed",
            created_at_utc=created_at_utc,
        )

    status = _assembly_status(bridge.bridge_status)
    return _finish(
        repo_path=bridge.repo_path,
        branch=bridge.branch,
        head_commit=bridge.head_commit,
        action_type=bridge.requested_action_type,
        target_type=bridge.requested_target_type,
        target_hash=bridge.requested_target_hash,
        target_paths=tuple(bridge.requested_target_paths),
        approval_record=approval_record,
        policy_profile=policy_profile,
        provider_flow_audit_hash=audit_hash,
        status=status,
        reason=_assembly_reason(status),
        created_at_utc=created_at_utc,
        bridge=bridge,
        human_projection=human_projection,
        review_packet=review_projection,
    )


def _invalid(
    repo_path: Any,
    branch: Any,
    head_commit: Any,
    action_type: str,
    target_type: str,
    target_hash: Any,
    target_paths: tuple[str, ...],
    approval_record: Any,
    policy_profile: Any,
    provider_flow_audit_hash: str | None,
    reason: str,
    created_at_utc: str | None,
) -> AuthChainAssemblyResult:
    return _finish(
        repo_path=_text(repo_path),
        branch=_text(branch),
        head_commit=_text(head_commit),
        action_type=action_type,
        target_type=target_type,
        target_hash=_text(target_hash),
        target_paths=target_paths,
        approval_record=approval_record,
        policy_profile=policy_profile,
        provider_flow_audit_hash=provider_flow_audit_hash,
        status=AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
        reason=reason,
        created_at_utc=created_at_utc,
    )


def _finish(
    *,
    repo_path: str,
    branch: str,
    head_commit: str,
    action_type: str,
    target_type: str,
    target_hash: str,
    target_paths: tuple[str, ...],
    approval_record: Any,
    policy_profile: Any,
    provider_flow_audit_hash: str | None,
    status: AuthChainAssemblyStatus,
    reason: str,
    created_at_utc: str | None,
    bridge: ApprovalPolicyBridgeResult | None = None,
    human_projection: ApprovalPolicyHumanProjection | None = None,
    review_packet: HumanReadableReviewPacketProjection | None = None,
) -> AuthChainAssemblyResult:
    approval_decision = (
        _enum_text(approval_record.decision)
        if isinstance(approval_record, HashBoundHumanApprovalRecord)
        else None
    )
    approval_hash = (
        approval_record.approval_binding_hash
        if isinstance(approval_record, HashBoundHumanApprovalRecord)
        else None
    )
    policy_name = (
        _enum_text(policy_profile.profile_name)
        if isinstance(policy_profile, PolicyProfile)
        else None
    )
    policy_hash = (
        policy_profile.policy_hash
        if isinstance(policy_profile, PolicyProfile)
        else None
    )
    boundaries = _required_boundaries()
    semantic = {
        "label": INERT_AUTH_CHAIN_ASSEMBLY,
        "schema_version": AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION,
        "assembly_role": END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY,
        "repo_path": repo_path,
        "branch": branch,
        "head_commit": head_commit,
        "requested_action_type": action_type,
        "requested_target_type": target_type,
        "requested_target_hash": target_hash,
        "requested_target_paths": list(target_paths),
        "approval_decision": approval_decision,
        "approval_binding_hash": approval_hash,
        "provider_flow_audit_hash": provider_flow_audit_hash,
        "policy_profile_name": policy_name,
        "policy_hash": policy_hash,
        "bridge_status": bridge.bridge_status.value if bridge is not None else None,
        "bridge_evaluation_hash": (
            bridge.evaluation_hash if bridge is not None else None
        ),
        "human_projection_status": (
            human_projection.final_status if human_projection is not None else None
        ),
        "review_packet_status": (
            review_packet.status if review_packet is not None else None
        ),
        "authority_status_present": (
            review_packet is not None and review_packet.authority_status is not None
        ),
        "assembly_status": status.value,
        "assembly_reason": reason,
        "review_packet": (
            review_packet.to_dict() if review_packet is not None else None
        ),
        "final_status": AUTH_CHAIN_ASSEMBLED_NO_EXECUTION,
        "safety_boundaries": [item.value for item in boundaries],
        "execution_authority": False,
        "artifact_write_authority": False,
        "provider_live_call_authority": False,
        "provider_trust_authority": False,
        "github_authority": False,
        "canonical_promotion_authority": False,
    }
    assembly_hash = _stable_hash(semantic)
    return AuthChainAssemblyResult(
        label=INERT_AUTH_CHAIN_ASSEMBLY,
        schema_version=AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION,
        assembly_role=END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY,
        created_at_utc=created_at_utc,
        repo_path=repo_path,
        branch=branch,
        head_commit=head_commit,
        requested_action_type=action_type,
        requested_target_type=target_type,
        requested_target_hash=target_hash,
        requested_target_paths=target_paths,
        approval_decision=approval_decision,
        approval_binding_hash=approval_hash,
        provider_flow_audit_hash=provider_flow_audit_hash,
        policy_profile_name=policy_name,
        policy_hash=policy_hash,
        bridge_status=semantic["bridge_status"],
        bridge_evaluation_hash=semantic["bridge_evaluation_hash"],
        human_projection_status=semantic["human_projection_status"],
        review_packet_status=semantic["review_packet_status"],
        authority_status_present=semantic["authority_status_present"],
        assembly_status=status,
        assembly_reason=reason,
        assembly_hash=assembly_hash,
        review_packet=review_packet,
        final_status=AUTH_CHAIN_ASSEMBLED_NO_EXECUTION,
        safety_boundaries=boundaries,
        execution_authority=False,
        artifact_write_authority=False,
        provider_live_call_authority=False,
        provider_trust_authority=False,
        github_authority=False,
        canonical_promotion_authority=False,
    )


def _assembly_status(status: ApprovalPolicyBridgeStatus) -> AuthChainAssemblyStatus:
    return {
        ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY: (
            AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY
        ),
        ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY: (
            AuthChainAssemblyStatus.AUTH_CHAIN_PROPOSAL_ONLY
        ),
        ApprovalPolicyBridgeStatus.DENIED: (
            AuthChainAssemblyStatus.AUTH_CHAIN_DENIED
        ),
        ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE: (
            AuthChainAssemblyStatus.AUTH_CHAIN_REQUIRES_FUTURE_MILESTONE
        ),
    }[status]


def _assembly_reason(status: AuthChainAssemblyStatus) -> str:
    return {
        AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY: (
            "AUTH chain assembled for inert record review only"
        ),
        AuthChainAssemblyStatus.AUTH_CHAIN_PROPOSAL_ONLY: (
            "AUTH chain assembled for inert proposal review only"
        ),
        AuthChainAssemblyStatus.AUTH_CHAIN_DENIED: (
            "AUTH chain assembled with a default-deny result"
        ),
        AuthChainAssemblyStatus.AUTH_CHAIN_REQUIRES_FUTURE_MILESTONE: (
            "AUTH chain requires a separately reviewed future milestone"
        ),
        AuthChainAssemblyStatus.AUTH_CHAIN_INVALID: (
            "AUTH chain failed closed as invalid"
        ),
    }[status]


def _required_boundaries() -> tuple[AuthChainAssemblyBoundary, ...]:
    return (
        AuthChainAssemblyBoundary.NO_EXECUTION,
        AuthChainAssemblyBoundary.NO_ARTIFACT_WRITE,
        AuthChainAssemblyBoundary.NO_PROVIDER_LIVE_CALL,
        AuthChainAssemblyBoundary.NO_PROVIDER_TRUST_CHANGE,
        AuthChainAssemblyBoundary.NO_GITHUB_ACTION,
        AuthChainAssemblyBoundary.NO_CANONICAL_PROMOTION,
        AuthChainAssemblyBoundary.ASSEMBLY_NOT_AUTHORITY,
        AuthChainAssemblyBoundary.REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION,
        AuthChainAssemblyBoundary.DEFAULT_DENY_ON_INVALID_CHAIN,
    )


def _paths_or_none(values: Iterable[str]) -> tuple[str, ...] | None:
    if isinstance(values, (str, bytes)):
        return None
    try:
        paths = tuple(values)
    except TypeError:
        return None
    if any(not isinstance(value, str) or not value for value in paths):
        return None
    return paths


def _enum_text(value: Any) -> str:
    return str(value.value) if isinstance(value, Enum) else _text(value)


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
