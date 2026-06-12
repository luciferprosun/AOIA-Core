from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ActionProposalType(str, Enum):
    SHELL_COMMAND = "SHELL_COMMAND"
    BROWSER_ACTION = "BROWSER_ACTION"
    FILESYSTEM_ACTION = "FILESYSTEM_ACTION"
    GIT_ACTION = "GIT_ACTION"
    PROVIDER_CALL = "PROVIDER_CALL"
    CLOUD_ACTION = "CLOUD_ACTION"
    DOCUMENT_PARSE = "DOCUMENT_PARSE"
    HUMAN_REVIEW_ONLY = "HUMAN_REVIEW_ONLY"


class ActionProposalRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN = "UNKNOWN"


class ActionProposalState(str, Enum):
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    EXECUTION_NOT_IMPLEMENTED = "EXECUTION_NOT_IMPLEMENTED"


_FORBIDDEN_PROPOSAL_TYPES = frozenset(
    {
        ActionProposalType.SHELL_COMMAND,
        ActionProposalType.BROWSER_ACTION,
        ActionProposalType.FILESYSTEM_ACTION,
        ActionProposalType.GIT_ACTION,
        ActionProposalType.PROVIDER_CALL,
        ActionProposalType.CLOUD_ACTION,
    }
)


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


def _default_risk_for_type(proposal_type: ActionProposalType) -> ActionProposalRisk:
    if proposal_type in _FORBIDDEN_PROPOSAL_TYPES:
        return ActionProposalRisk.FORBIDDEN
    if proposal_type is ActionProposalType.HUMAN_REVIEW_ONLY:
        return ActionProposalRisk.LOW
    return ActionProposalRisk.UNKNOWN


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    created_at: str
    proposal_type: ActionProposalType
    state: ActionProposalState
    risk: ActionProposalRisk
    title: str
    description: str
    proposed_by: str
    source_record_id: str
    source_record_type: str
    payload_summary: str
    exact_payload: str
    human_review_required: bool = True
    human_approved: bool = False
    execution_permitted: bool = False
    execution_implemented: bool = False
    provider_generated: bool = False
    evidence_backed: bool = False
    audit_event_id: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        proposal_type = ActionProposalType(self.proposal_type)
        state = ActionProposalState(self.state)
        risk = ActionProposalRisk(self.risk)
        if proposal_type in _FORBIDDEN_PROPOSAL_TYPES:
            risk = ActionProposalRisk.FORBIDDEN

        object.__setattr__(self, "proposal_id", _coerce_text("proposal_id", self.proposal_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "proposal_type", proposal_type)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "risk", risk)
        object.__setattr__(self, "title", _coerce_text("title", self.title))
        object.__setattr__(self, "description", _coerce_text("description", self.description))
        object.__setattr__(self, "proposed_by", _coerce_text("proposed_by", self.proposed_by))
        object.__setattr__(self, "source_record_id", _coerce_text("source_record_id", self.source_record_id))
        object.__setattr__(self, "source_record_type", _coerce_text("source_record_type", self.source_record_type))
        object.__setattr__(self, "payload_summary", _coerce_text("payload_summary", self.payload_summary))
        object.__setattr__(self, "exact_payload", _coerce_text("exact_payload", self.exact_payload))
        object.__setattr__(self, "human_review_required", _coerce_bool("human_review_required", self.human_review_required))
        object.__setattr__(self, "human_approved", _coerce_bool("human_approved", self.human_approved))
        object.__setattr__(self, "execution_permitted", False)
        object.__setattr__(self, "execution_implemented", False)
        object.__setattr__(self, "provider_generated", _coerce_bool("provider_generated", self.provider_generated))
        object.__setattr__(self, "evidence_backed", _coerce_bool("evidence_backed", self.evidence_backed))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "created_at": self.created_at,
            "proposal_type": self.proposal_type.value,
            "state": self.state.value,
            "risk": self.risk.value,
            "title": self.title,
            "description": self.description,
            "proposed_by": self.proposed_by,
            "source_record_id": self.source_record_id,
            "source_record_type": self.source_record_type,
            "payload_summary": self.payload_summary,
            "exact_payload": self.exact_payload,
            "human_review_required": self.human_review_required,
            "human_approved": self.human_approved,
            "execution_permitted": self.execution_permitted,
            "execution_implemented": self.execution_implemented,
            "provider_generated": self.provider_generated,
            "evidence_backed": self.evidence_backed,
            "audit_event_id": self.audit_event_id,
            "notes": self.notes,
        }


def create_inert_action_proposal(
    *,
    proposal_type: ActionProposalType | str,
    title: str,
    description: str,
    proposed_by: str,
    source_record_id: str = "",
    source_record_type: str = "",
    payload_summary: str = "",
    exact_payload: str = "",
    state: ActionProposalState | str = ActionProposalState.NEEDS_REVIEW,
    risk: ActionProposalRisk | str | None = None,
    human_approved: bool = False,
    provider_generated: bool = False,
    evidence_backed: bool = False,
    notes: str = "",
    created_at: str | None = None,
    proposal_id: str | None = None,
    audit_event_id: str | None = None,
) -> ActionProposal:
    proposal_type_value = ActionProposalType(proposal_type)
    timestamp = created_at or _utc_now_iso()
    payload = _coerce_text("exact_payload", exact_payload)
    source_id = _coerce_text("source_record_id", source_record_id)
    record_id = proposal_id or "action-proposal-" + _hash_text(
        "\n".join([proposal_type_value.value, source_id, payload, timestamp])
    )[:24]
    event_id = audit_event_id or "action-audit-" + _hash_text(record_id)[:24]
    risk_value = ActionProposalRisk(risk) if risk is not None else _default_risk_for_type(proposal_type_value)
    return ActionProposal(
        proposal_id=record_id,
        created_at=timestamp,
        proposal_type=proposal_type_value,
        state=ActionProposalState(state),
        risk=risk_value,
        title=title,
        description=description,
        proposed_by=proposed_by,
        source_record_id=source_id,
        source_record_type=source_record_type,
        payload_summary=payload_summary,
        exact_payload=payload,
        human_review_required=True,
        human_approved=human_approved,
        execution_permitted=False,
        execution_implemented=False,
        provider_generated=provider_generated,
        evidence_backed=evidence_backed,
        audit_event_id=event_id,
        notes=notes,
    )


def create_human_review_only_proposal(
    *,
    title: str,
    description: str,
    proposed_by: str = "human",
    source_record_id: str = "",
    source_record_type: str = "",
    payload_summary: str = "",
    exact_payload: str = "",
    human_approved: bool = False,
    evidence_backed: bool = False,
    notes: str = "",
    created_at: str | None = None,
    proposal_id: str | None = None,
) -> ActionProposal:
    state = ActionProposalState.HUMAN_APPROVED if human_approved else ActionProposalState.NEEDS_REVIEW
    return create_inert_action_proposal(
        proposal_type=ActionProposalType.HUMAN_REVIEW_ONLY,
        title=title,
        description=description,
        proposed_by=proposed_by,
        source_record_id=source_record_id,
        source_record_type=source_record_type,
        payload_summary=payload_summary,
        exact_payload=exact_payload,
        state=state,
        risk=ActionProposalRisk.LOW,
        human_approved=human_approved,
        provider_generated=False,
        evidence_backed=evidence_backed,
        notes=notes,
        created_at=created_at,
        proposal_id=proposal_id,
    )


def action_proposal_to_dict(proposal: ActionProposal) -> dict[str, Any]:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    return proposal.to_dict()
