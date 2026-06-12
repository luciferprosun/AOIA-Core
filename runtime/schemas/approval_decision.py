from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from runtime.schemas.action_proposal import ActionProposal
from runtime.schemas.command_proposal import APPROVAL_STATES


class ApprovalDecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    NEEDS_CHANGES = "NEEDS_CHANGES"
    DEFER = "DEFER"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"


class ApprovalDecisionState(str, Enum):
    RECORDED = "RECORDED"
    INVALID = "INVALID"
    SUPERSEDED = "SUPERSEDED"


class ApprovalActorType(str, Enum):
    HUMAN_REVIEWER = "HUMAN_REVIEWER"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    PROVIDER_MODEL = "PROVIDER_MODEL"
    UNKNOWN = "UNKNOWN"


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


def hash_action_proposal_payload(proposal: ActionProposal) -> str:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    return _hash_text(proposal.exact_payload)


@dataclass(frozen=True)
class ApprovalDecision:
    decision_id: str = ""
    created_at: str = ""
    proposal_id: str = ""
    proposal_type: str = ""
    decision_type: ApprovalDecisionType = ApprovalDecisionType.DEFER
    decision_state: ApprovalDecisionState = ApprovalDecisionState.RECORDED
    actor_type: ApprovalActorType = ApprovalActorType.UNKNOWN
    actor_id: str = ""
    reason: str = ""
    reviewed_exact_payload_hash: str = ""
    reviewed_payload_summary: str = ""
    human_reviewed: bool = False
    provider_generated: bool = False
    policy_blocked: bool = False
    execution_permitted: bool = False
    execution_triggered: bool = False
    expires_at: str = ""
    audit_event_id: str = ""
    notes: str = ""
    allowed: bool = False
    approval_state: str = "requires_human_review"
    dry_run: bool = True
    requires_human_review: bool = True

    def __post_init__(self) -> None:
        decision_type = ApprovalDecisionType(self.decision_type)
        decision_state = ApprovalDecisionState(self.decision_state)
        actor_type = ApprovalActorType(self.actor_type)

        object.__setattr__(self, "decision_id", _coerce_text("decision_id", self.decision_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "proposal_id", _coerce_text("proposal_id", self.proposal_id))
        object.__setattr__(self, "proposal_type", _coerce_text("proposal_type", self.proposal_type))
        object.__setattr__(self, "decision_type", decision_type)
        object.__setattr__(self, "decision_state", decision_state)
        object.__setattr__(self, "actor_type", actor_type)
        object.__setattr__(self, "actor_id", _coerce_text("actor_id", self.actor_id))
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))
        object.__setattr__(
            self,
            "reviewed_exact_payload_hash",
            _coerce_text("reviewed_exact_payload_hash", self.reviewed_exact_payload_hash),
        )
        object.__setattr__(
            self,
            "reviewed_payload_summary",
            _coerce_text("reviewed_payload_summary", self.reviewed_payload_summary),
        )
        object.__setattr__(self, "human_reviewed", _coerce_bool("human_reviewed", self.human_reviewed))
        object.__setattr__(self, "provider_generated", _coerce_bool("provider_generated", self.provider_generated))
        object.__setattr__(self, "policy_blocked", _coerce_bool("policy_blocked", self.policy_blocked))
        object.__setattr__(self, "expires_at", _coerce_text("expires_at", self.expires_at))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))
        object.__setattr__(self, "allowed", _coerce_bool("allowed", self.allowed))
        object.__setattr__(self, "approval_state", _coerce_text("approval_state", self.approval_state))
        object.__setattr__(self, "dry_run", _coerce_bool("dry_run", self.dry_run))
        object.__setattr__(
            self,
            "requires_human_review",
            _coerce_bool("requires_human_review", self.requires_human_review),
        )

        if self.approval_state not in APPROVAL_STATES:
            raise ValueError("approval_state must be one of the allowed values")
        if self.execution_permitted is not False:
            raise ValueError("execution_permitted must remain False in M4-A")
        if self.execution_triggered is not False:
            raise ValueError("execution_triggered must remain False in M4-A")
        object.__setattr__(self, "execution_permitted", False)
        object.__setattr__(self, "execution_triggered", False)

        if self.approval_state == "not_required" and self.requires_human_review:
            raise ValueError("requires_human_review must be False when approval_state is not_required")
        if self.approval_state == "requires_human_review" and not self.requires_human_review:
            raise ValueError("requires_human_review must be True when approval_state is requires_human_review")

        if decision_type is ApprovalDecisionType.APPROVE:
            invalid_actor = actor_type in {ApprovalActorType.PROVIDER_MODEL, ApprovalActorType.UNKNOWN}
            if invalid_actor or self.provider_generated or not self.human_reviewed:
                object.__setattr__(self, "decision_state", ApprovalDecisionState.INVALID)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "created_at": self.created_at,
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "decision_type": self.decision_type.value,
            "decision_state": self.decision_state.value,
            "actor_type": self.actor_type.value,
            "actor_id": self.actor_id,
            "reason": self.reason,
            "reviewed_exact_payload_hash": self.reviewed_exact_payload_hash,
            "reviewed_payload_summary": self.reviewed_payload_summary,
            "human_reviewed": self.human_reviewed,
            "provider_generated": self.provider_generated,
            "policy_blocked": self.policy_blocked,
            "execution_permitted": self.execution_permitted,
            "execution_triggered": self.execution_triggered,
            "expires_at": self.expires_at,
            "audit_event_id": self.audit_event_id,
            "notes": self.notes,
            "allowed": self.allowed,
            "approval_state": self.approval_state,
            "dry_run": self.dry_run,
            "requires_human_review": self.requires_human_review,
        }


def _base_decision(
    *,
    proposal: ActionProposal,
    decision_type: ApprovalDecisionType,
    actor_type: ApprovalActorType,
    actor_id: str,
    reason: str,
    notes: str = "",
    policy_blocked: bool = False,
    created_at: str | None = None,
    decision_id: str | None = None,
    audit_event_id: str | None = None,
    expires_at: str = "",
    provider_generated: bool = False,
) -> ApprovalDecision:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    timestamp = created_at or _utc_now_iso()
    payload_hash = hash_action_proposal_payload(proposal)
    record_id = decision_id or "approval-decision-" + _hash_text(
        "\n".join([proposal.proposal_id, decision_type.value, actor_type.value, actor_id, payload_hash, timestamp])
    )[:24]
    event_id = audit_event_id or "approval-audit-" + _hash_text(record_id)[:24]
    human_reviewed = actor_type is ApprovalActorType.HUMAN_REVIEWER
    decision_state = ApprovalDecisionState.RECORDED
    if decision_type is ApprovalDecisionType.APPROVE and not human_reviewed:
        decision_state = ApprovalDecisionState.INVALID
    return ApprovalDecision(
        decision_id=record_id,
        created_at=timestamp,
        proposal_id=proposal.proposal_id,
        proposal_type=proposal.proposal_type.value,
        decision_type=decision_type,
        decision_state=decision_state,
        actor_type=actor_type,
        actor_id=actor_id,
        reason=reason,
        reviewed_exact_payload_hash=payload_hash,
        reviewed_payload_summary=proposal.payload_summary,
        human_reviewed=human_reviewed,
        provider_generated=provider_generated,
        policy_blocked=policy_blocked,
        execution_permitted=False,
        execution_triggered=False,
        expires_at=expires_at,
        audit_event_id=event_id,
        notes=notes,
        allowed=False,
        approval_state="requires_human_review",
        dry_run=True,
        requires_human_review=True,
    )


def create_human_approval_decision(
    proposal: ActionProposal,
    actor_id: str,
    reason: str,
    notes: str = "",
) -> ApprovalDecision:
    return _base_decision(
        proposal=proposal,
        decision_type=ApprovalDecisionType.APPROVE,
        actor_type=ApprovalActorType.HUMAN_REVIEWER,
        actor_id=actor_id,
        reason=reason,
        notes=notes,
    )


def create_rejection_decision(
    proposal: ActionProposal,
    actor_id: str,
    reason: str,
    notes: str = "",
) -> ApprovalDecision:
    return _base_decision(
        proposal=proposal,
        decision_type=ApprovalDecisionType.REJECT,
        actor_type=ApprovalActorType.HUMAN_REVIEWER,
        actor_id=actor_id,
        reason=reason,
        notes=notes,
    )


def create_needs_changes_decision(
    proposal: ActionProposal,
    actor_id: str,
    reason: str,
    notes: str = "",
) -> ApprovalDecision:
    return _base_decision(
        proposal=proposal,
        decision_type=ApprovalDecisionType.NEEDS_CHANGES,
        actor_type=ApprovalActorType.HUMAN_REVIEWER,
        actor_id=actor_id,
        reason=reason,
        notes=notes,
    )


def create_policy_block_decision(
    proposal: ActionProposal,
    reason: str,
    notes: str = "",
) -> ApprovalDecision:
    return _base_decision(
        proposal=proposal,
        decision_type=ApprovalDecisionType.BLOCKED_BY_POLICY,
        actor_type=ApprovalActorType.SYSTEM_POLICY,
        actor_id="system-policy",
        reason=reason,
        notes=notes,
        policy_blocked=True,
    )


def approval_decision_to_dict(decision: ApprovalDecision) -> dict[str, Any]:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    return decision.to_dict()
