from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from runtime.schemas.action_proposal import ActionProposal, ActionProposalType
from runtime.schemas.approval_decision import ApprovalDecision, ApprovalDecisionType


class SandboxActionType(str, Enum):
    SHELL_COMMAND = "SHELL_COMMAND"
    BROWSER_ACTION = "BROWSER_ACTION"
    FILESYSTEM_ACTION = "FILESYSTEM_ACTION"
    GIT_ACTION = "GIT_ACTION"
    PROVIDER_CALL = "PROVIDER_CALL"
    CLOUD_ACTION = "CLOUD_ACTION"
    DOCUMENT_PARSE = "DOCUMENT_PARSE"
    HUMAN_REVIEW_ONLY = "HUMAN_REVIEW_ONLY"


class SandboxDecisionType(str, Enum):
    BLOCKED_BY_DEFAULT = "BLOCKED_BY_DEFAULT"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    REQUIRES_FUTURE_SANDBOX = "REQUIRES_FUTURE_SANDBOX"


class SandboxResultState(str, Enum):
    NOT_RUN = "NOT_RUN"
    BLOCKED = "BLOCKED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    INVALID = "INVALID"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _coerce_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    return value


def _action_type_from_proposal(proposal: ActionProposal) -> SandboxActionType:
    proposal_type = ActionProposalType(proposal.proposal_type)
    return SandboxActionType(proposal_type.value)


@dataclass(frozen=True)
class SandboxRequest:
    sandbox_request_id: str
    created_at: str
    proposal_id: str
    proposal_type: str
    requested_action_type: SandboxActionType
    exact_payload_hash: str
    payload_summary: str
    requested_by: str
    human_approved: bool
    audit_event_id: str
    execution_requested: bool
    notes: str

    def __post_init__(self) -> None:
        requested_action_type = SandboxActionType(self.requested_action_type)
        object.__setattr__(
            self,
            "sandbox_request_id",
            _coerce_text("sandbox_request_id", self.sandbox_request_id),
        )
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "proposal_id", _coerce_text("proposal_id", self.proposal_id))
        object.__setattr__(self, "proposal_type", _coerce_text("proposal_type", self.proposal_type))
        object.__setattr__(self, "requested_action_type", requested_action_type)
        object.__setattr__(
            self,
            "exact_payload_hash",
            _coerce_text("exact_payload_hash", self.exact_payload_hash),
        )
        object.__setattr__(self, "payload_summary", _coerce_text("payload_summary", self.payload_summary))
        object.__setattr__(self, "requested_by", _coerce_text("requested_by", self.requested_by))
        object.__setattr__(self, "human_approved", _coerce_bool("human_approved", self.human_approved))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(
            self,
            "execution_requested",
            _coerce_bool("execution_requested", self.execution_requested),
        )
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_request_id": self.sandbox_request_id,
            "created_at": self.created_at,
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "requested_action_type": self.requested_action_type.value,
            "exact_payload_hash": self.exact_payload_hash,
            "payload_summary": self.payload_summary,
            "requested_by": self.requested_by,
            "human_approved": self.human_approved,
            "audit_event_id": self.audit_event_id,
            "execution_requested": self.execution_requested,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SandboxPolicyDecision:
    decision_id: str
    created_at: str
    sandbox_request_id: str
    decision_type: SandboxDecisionType
    reason: str
    execution_allowed: bool
    execution_implemented: bool
    requires_future_sandbox: bool
    policy_blocked: bool
    audit_event_id: str
    notes: str

    def __post_init__(self) -> None:
        decision_type = SandboxDecisionType(self.decision_type)
        object.__setattr__(self, "decision_id", _coerce_text("decision_id", self.decision_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(
            self,
            "sandbox_request_id",
            _coerce_text("sandbox_request_id", self.sandbox_request_id),
        )
        object.__setattr__(self, "decision_type", decision_type)
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))
        object.__setattr__(
            self,
            "requires_future_sandbox",
            _coerce_bool("requires_future_sandbox", self.requires_future_sandbox),
        )
        object.__setattr__(self, "policy_blocked", _coerce_bool("policy_blocked", self.policy_blocked))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

        if self.execution_allowed is not False:
            raise ValueError("execution_allowed must remain False in M6-A")
        if self.execution_implemented is not False:
            raise ValueError("execution_implemented must remain False in M6-A")
        object.__setattr__(self, "execution_allowed", False)
        object.__setattr__(self, "execution_implemented", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "created_at": self.created_at,
            "sandbox_request_id": self.sandbox_request_id,
            "decision_type": self.decision_type.value,
            "reason": self.reason,
            "execution_allowed": self.execution_allowed,
            "execution_implemented": self.execution_implemented,
            "requires_future_sandbox": self.requires_future_sandbox,
            "policy_blocked": self.policy_blocked,
            "audit_event_id": self.audit_event_id,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SandboxResult:
    result_id: str
    created_at: str
    sandbox_request_id: str
    policy_decision_id: str
    result_state: SandboxResultState
    execution_attempted: bool
    execution_completed: bool
    output_summary: str
    error_summary: str
    audit_event_id: str
    notes: str

    def __post_init__(self) -> None:
        result_state = SandboxResultState(self.result_state)
        object.__setattr__(self, "result_id", _coerce_text("result_id", self.result_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(
            self,
            "sandbox_request_id",
            _coerce_text("sandbox_request_id", self.sandbox_request_id),
        )
        object.__setattr__(
            self,
            "policy_decision_id",
            _coerce_text("policy_decision_id", self.policy_decision_id),
        )
        object.__setattr__(self, "result_state", result_state)
        object.__setattr__(self, "output_summary", _coerce_text("output_summary", self.output_summary))
        object.__setattr__(self, "error_summary", _coerce_text("error_summary", self.error_summary))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

        if self.execution_attempted is not False:
            raise ValueError("execution_attempted must remain False in M6-A")
        if self.execution_completed is not False:
            raise ValueError("execution_completed must remain False in M6-A")
        object.__setattr__(self, "execution_attempted", False)
        object.__setattr__(self, "execution_completed", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "created_at": self.created_at,
            "sandbox_request_id": self.sandbox_request_id,
            "policy_decision_id": self.policy_decision_id,
            "result_state": self.result_state.value,
            "execution_attempted": self.execution_attempted,
            "execution_completed": self.execution_completed,
            "output_summary": self.output_summary,
            "error_summary": self.error_summary,
            "audit_event_id": self.audit_event_id,
            "notes": self.notes,
        }


def create_sandbox_request_from_action_proposal(
    proposal: ActionProposal,
    approval_decision: ApprovalDecision | None = None,
    audit_event_id: str = "",
    notes: str = "",
) -> SandboxRequest:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if approval_decision is not None and not isinstance(approval_decision, ApprovalDecision):
        raise TypeError("approval_decision must be an ApprovalDecision or None")
    timestamp = _utc_now_iso()
    action_type = _action_type_from_proposal(proposal)
    payload_hash = _hash_text(proposal.exact_payload)
    human_approved = bool(proposal.human_approved)
    if approval_decision is not None:
        human_approved = (
            approval_decision.decision_type is ApprovalDecisionType.APPROVE
            and approval_decision.human_reviewed
            and not approval_decision.provider_generated
        )
    request_id = "sandbox-request-" + _hash_text(
        "\n".join([proposal.proposal_id, action_type.value, payload_hash, timestamp])
    )[:24]
    event_id = audit_event_id or "sandbox-request-audit-" + _hash_text(request_id)[:24]
    return SandboxRequest(
        sandbox_request_id=request_id,
        created_at=timestamp,
        proposal_id=proposal.proposal_id,
        proposal_type=proposal.proposal_type.value,
        requested_action_type=action_type,
        exact_payload_hash=payload_hash,
        payload_summary=proposal.payload_summary,
        requested_by=proposal.proposed_by,
        human_approved=human_approved,
        audit_event_id=event_id,
        execution_requested=True,
        notes=notes,
    )


def create_blocked_sandbox_policy_decision(
    request: SandboxRequest,
    reason: str,
) -> SandboxPolicyDecision:
    return _create_sandbox_policy_decision(
        request,
        SandboxDecisionType.BLOCKED_BY_POLICY,
        SandboxDecisionType.BLOCKED_BY_POLICY.value.lower(),
        reason,
        requires_future_sandbox=True,
        policy_blocked=True,
    )


def create_not_implemented_sandbox_policy_decision(
    request: SandboxRequest,
    reason: str,
) -> SandboxPolicyDecision:
    return _create_sandbox_policy_decision(
        request,
        SandboxDecisionType.NOT_IMPLEMENTED,
        SandboxDecisionType.NOT_IMPLEMENTED.value.lower(),
        reason,
        requires_future_sandbox=True,
        policy_blocked=False,
    )


def _create_sandbox_policy_decision(
    request: SandboxRequest,
    decision_type: SandboxDecisionType,
    id_seed: str,
    reason: str,
    *,
    requires_future_sandbox: bool,
    policy_blocked: bool,
) -> SandboxPolicyDecision:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    timestamp = _utc_now_iso()
    record_id = "sandbox-decision-" + _hash_text(
        "\n".join([request.sandbox_request_id, id_seed, reason, timestamp])
    )[:24]
    event_id = "sandbox-decision-audit-" + _hash_text(record_id)[:24]
    return SandboxPolicyDecision(
        decision_id=record_id,
        created_at=timestamp,
        sandbox_request_id=request.sandbox_request_id,
        decision_type=decision_type,
        reason=reason,
        execution_allowed=False,
        execution_implemented=False,
        requires_future_sandbox=requires_future_sandbox,
        policy_blocked=policy_blocked,
        audit_event_id=event_id,
        notes="M6-A sandbox contract only; no runner exists",
    )


def create_blocked_sandbox_result(
    request: SandboxRequest,
    decision: SandboxPolicyDecision,
    reason: str,
) -> SandboxResult:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    if not isinstance(decision, SandboxPolicyDecision):
        raise TypeError("decision must be a SandboxPolicyDecision")
    if decision.sandbox_request_id != request.sandbox_request_id:
        raise ValueError("decision sandbox_request_id must match request")
    timestamp = _utc_now_iso()
    record_id = "sandbox-result-" + _hash_text(
        "\n".join([request.sandbox_request_id, decision.decision_id, reason, timestamp])
    )[:24]
    event_id = "sandbox-result-audit-" + _hash_text(record_id)[:24]
    result_state = (
        SandboxResultState.NOT_IMPLEMENTED
        if decision.decision_type is SandboxDecisionType.NOT_IMPLEMENTED
        else SandboxResultState.BLOCKED
    )
    return SandboxResult(
        result_id=record_id,
        created_at=timestamp,
        sandbox_request_id=request.sandbox_request_id,
        policy_decision_id=decision.decision_id,
        result_state=result_state,
        execution_attempted=False,
        execution_completed=False,
        output_summary="",
        error_summary=reason,
        audit_event_id=event_id,
        notes="M6-A records a non-running sandbox result",
    )


def sandbox_request_to_dict(request: SandboxRequest) -> dict[str, Any]:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    return request.to_dict()


def sandbox_policy_decision_to_dict(decision: SandboxPolicyDecision) -> dict[str, Any]:
    if not isinstance(decision, SandboxPolicyDecision):
        raise TypeError("decision must be a SandboxPolicyDecision")
    return decision.to_dict()


def sandbox_result_to_dict(result: SandboxResult) -> dict[str, Any]:
    if not isinstance(result, SandboxResult):
        raise TypeError("result must be a SandboxResult")
    return result.to_dict()
