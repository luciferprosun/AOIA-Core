from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath
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


class ActionProposalStatus(str, Enum):
    PROPOSAL_READY = "PROPOSAL_READY"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INVALID_TARGET = "INVALID_TARGET"
    UNSUPPORTED_ACTION_KIND = "UNSUPPORTED_ACTION_KIND"


class ActionProposalKind(str, Enum):
    FILE_WRITE = "FILE_WRITE"
    TEST_RUN = "TEST_RUN"
    SHELL_COMMAND = "SHELL_COMMAND"
    GIT_COMMIT = "GIT_COMMIT"
    GIT_PUSH = "GIT_PUSH"
    PACKAGE_INSTALL = "PACKAGE_INSTALL"
    PROVIDER_CALL = "PROVIDER_CALL"
    BROWSER_ACTION = "BROWSER_ACTION"
    UNKNOWN = "UNKNOWN"


class ActionProposalRiskFlag(str, Enum):
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    UNKNOWN_ACTION_KIND = "UNKNOWN_ACTION_KIND"
    INVALID_TARGET = "INVALID_TARGET"
    MUTATING_ACTION = "MUTATING_ACTION"
    FILESYSTEM_WRITE = "FILESYSTEM_WRITE"
    PROCESS_EXECUTION = "PROCESS_EXECUTION"
    GIT_OPERATION = "GIT_OPERATION"
    PACKAGE_INSTALL = "PACKAGE_INSTALL"
    NETWORK_RELATED = "NETWORK_RELATED"
    BROWSER_RELATED = "BROWSER_RELATED"
    HIGH_BLAST_RADIUS = "HIGH_BLAST_RADIUS"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"


class ActionProposalSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    CRITIC_METADATA = "CRITIC_METADATA"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ActionProposalRequest:
    action_kind: ActionProposalKind | str
    target_refs: tuple[str, ...] | list[str] = ()
    arguments: Any = None
    candidate_tool_id: str | None = None
    source_trust: ActionProposalSourceTrust | str = ActionProposalSourceTrust.UNKNOWN
    proposed_by: str = "unknown"
    summary: str = ""
    created_at_utc: str = "not_provided"


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
    schema_version: str = "AOIA_ACTION_PROPOSAL_1A"
    status: ActionProposalStatus = ActionProposalStatus.PROPOSAL_READY
    action_kind: ActionProposalKind = ActionProposalKind.UNKNOWN
    candidate_tool_id: str | None = None
    source_trust: ActionProposalSourceTrust = ActionProposalSourceTrust.UNKNOWN
    target_refs: tuple[str, ...] = ()
    normalized_arguments: Any = None
    proposal_hash: str = ""
    risk_flags: tuple[ActionProposalRiskFlag, ...] = ()
    summary: str = ""

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
        object.__setattr__(self, "schema_version", _coerce_text("schema_version", self.schema_version))
        object.__setattr__(self, "status", ActionProposalStatus(self.status))
        object.__setattr__(self, "action_kind", ActionProposalKind(self.action_kind))
        object.__setattr__(self, "candidate_tool_id", _optional_text(self.candidate_tool_id))
        object.__setattr__(self, "source_trust", ActionProposalSourceTrust(self.source_trust))
        object.__setattr__(self, "target_refs", _coerce_text_tuple("target_refs", self.target_refs))
        object.__setattr__(self, "normalized_arguments", _stable_json_value(self.normalized_arguments))
        object.__setattr__(self, "proposal_hash", _coerce_text("proposal_hash", self.proposal_hash))
        object.__setattr__(self, "risk_flags", _coerce_risk_flags(self.risk_flags))
        object.__setattr__(self, "summary", _coerce_text("summary", self.summary))

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
            "schema_version": self.schema_version,
            "status": self.status.value,
            "action_kind": self.action_kind.value,
            "candidate_tool_id": self.candidate_tool_id,
            "source_trust": self.source_trust.value,
            "target_refs": list(self.target_refs),
            "normalized_arguments": self.normalized_arguments,
            "proposal_hash": self.proposal_hash,
            "risk_flags": [flag.value for flag in self.risk_flags],
            "summary": self.summary,
        }


def build_action_proposal(request: ActionProposalRequest) -> ActionProposal:
    if not isinstance(request, ActionProposalRequest):
        return _fail_closed_step11_proposal(
            status=ActionProposalStatus.MALFORMED_REQUEST,
            action_kind=ActionProposalKind.UNKNOWN,
            source_trust=ActionProposalSourceTrust.UNKNOWN,
            candidate_tool_id=None,
            target_refs=(),
            normalized_arguments={},
            proposed_by="unknown",
            summary="Malformed action proposal request.",
            risk_flags=(
                ActionProposalRiskFlag.HUMAN_REVIEW_REQUIRED,
                ActionProposalRiskFlag.UNKNOWN_ACTION_KIND,
                ActionProposalRiskFlag.NOT_YET_GOVERNED,
            ),
        )

    action_kind = _normalize_action_kind(request.action_kind)
    source_trust = _normalize_source_trust(request.source_trust)
    candidate_tool_id = _optional_text(request.candidate_tool_id)
    proposed_by = _optional_text(request.proposed_by) or "unknown"
    summary = _optional_text(request.summary) or _default_summary(action_kind)

    try:
        normalized_arguments = _stable_json_value(request.arguments)
    except (TypeError, ValueError):
        normalized_arguments = {}
        status = ActionProposalStatus.MALFORMED_REQUEST
    else:
        status = ActionProposalStatus.PROPOSAL_READY

    target_refs, target_error = _normalize_target_refs(request.target_refs)
    if target_error:
        status = ActionProposalStatus.INVALID_TARGET
    elif action_kind is ActionProposalKind.UNKNOWN:
        status = ActionProposalStatus.UNSUPPORTED_ACTION_KIND

    risk_flags = _risk_flags_for(
        action_kind=action_kind,
        source_trust=source_trust,
        status=status,
        has_targets=bool(target_refs),
    )
    proposal_hash = _proposal_hash(
        schema_version="AOIA_ACTION_PROPOSAL_1A",
        status=status,
        action_kind=action_kind,
        candidate_tool_id=candidate_tool_id,
        source_trust=source_trust,
        target_refs=target_refs,
        normalized_arguments=normalized_arguments,
        human_review_required=True,
        risk_flags=risk_flags,
        summary=summary,
    )
    proposal_id = "action-proposal-" + proposal_hash[:24]
    legacy_type = _legacy_type_for_kind(action_kind)
    legacy_risk = _legacy_risk_for_step11(status, action_kind)
    return ActionProposal(
        proposal_id=proposal_id,
        created_at=_coerce_text("created_at_utc", request.created_at_utc),
        proposal_type=legacy_type,
        state=ActionProposalState.NEEDS_REVIEW,
        risk=legacy_risk,
        title=summary[:120],
        description=summary,
        proposed_by=proposed_by,
        source_record_id=proposal_id,
        source_record_type="ActionProposalRequest",
        payload_summary=summary,
        exact_payload=_canonical_json(
            {
                "action_kind": action_kind.value,
                "candidate_tool_id": candidate_tool_id,
                "source_trust": source_trust.value,
                "target_refs": list(target_refs),
                "normalized_arguments": normalized_arguments,
            }
        ),
        human_review_required=True,
        human_approved=False,
        execution_permitted=False,
        execution_implemented=False,
        provider_generated=source_trust is ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
        evidence_backed=False,
        audit_event_id="",
        notes="Step 11 ActionProposal 1A metadata only.",
        schema_version="AOIA_ACTION_PROPOSAL_1A",
        status=status,
        action_kind=action_kind,
        candidate_tool_id=candidate_tool_id,
        source_trust=source_trust,
        target_refs=target_refs,
        normalized_arguments=normalized_arguments,
        proposal_hash=proposal_hash,
        risk_flags=risk_flags,
        summary=summary,
    )


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


def _fail_closed_step11_proposal(
    *,
    status: ActionProposalStatus,
    action_kind: ActionProposalKind,
    source_trust: ActionProposalSourceTrust,
    candidate_tool_id: str | None,
    target_refs: tuple[str, ...],
    normalized_arguments: Any,
    proposed_by: str,
    summary: str,
    risk_flags: tuple[ActionProposalRiskFlag, ...],
) -> ActionProposal:
    proposal_hash = _proposal_hash(
        schema_version="AOIA_ACTION_PROPOSAL_1A",
        status=status,
        action_kind=action_kind,
        candidate_tool_id=candidate_tool_id,
        source_trust=source_trust,
        target_refs=target_refs,
        normalized_arguments=normalized_arguments,
        human_review_required=True,
        risk_flags=risk_flags,
        summary=summary,
    )
    proposal_id = "action-proposal-" + proposal_hash[:24]
    return ActionProposal(
        proposal_id=proposal_id,
        created_at="not_provided",
        proposal_type=ActionProposalType.HUMAN_REVIEW_ONLY,
        state=ActionProposalState.NEEDS_REVIEW,
        risk=ActionProposalRisk.UNKNOWN,
        title=summary[:120],
        description=summary,
        proposed_by=proposed_by,
        source_record_id=proposal_id,
        source_record_type="ActionProposalRequest",
        payload_summary=summary,
        exact_payload="{}",
        human_review_required=True,
        human_approved=False,
        execution_permitted=False,
        execution_implemented=False,
        provider_generated=False,
        evidence_backed=False,
        audit_event_id="",
        notes="Step 11 ActionProposal 1A fail-closed metadata.",
        schema_version="AOIA_ACTION_PROPOSAL_1A",
        status=status,
        action_kind=action_kind,
        candidate_tool_id=candidate_tool_id,
        source_trust=source_trust,
        target_refs=target_refs,
        normalized_arguments=normalized_arguments,
        proposal_hash=proposal_hash,
        risk_flags=risk_flags,
        summary=summary,
    )


def _normalize_action_kind(value: ActionProposalKind | str) -> ActionProposalKind:
    if isinstance(value, ActionProposalKind):
        return value
    if not isinstance(value, str):
        return ActionProposalKind.UNKNOWN
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    try:
        return ActionProposalKind(normalized)
    except ValueError:
        return ActionProposalKind.UNKNOWN


def _normalize_source_trust(value: ActionProposalSourceTrust | str) -> ActionProposalSourceTrust:
    if isinstance(value, ActionProposalSourceTrust):
        return value
    if not isinstance(value, str):
        return ActionProposalSourceTrust.UNKNOWN
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    try:
        return ActionProposalSourceTrust(normalized)
    except ValueError:
        return ActionProposalSourceTrust.UNKNOWN


def _normalize_target_refs(values: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], str]:
    if not isinstance(values, (tuple, list)):
        return (), "target refs must be a tuple or list"
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            return (), "target ref must be text"
        candidate = value.strip().replace("\\", "/")
        if not candidate or "\x00" in candidate:
            return (), "target ref is empty or malformed"
        if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
            return (), "absolute target refs are invalid"
        if ".." in PurePosixPath(candidate).parts:
            return (), "parent traversal target refs are invalid"
        normalized.append(PurePosixPath(candidate).as_posix())
    return tuple(normalized), ""


def _stable_json_value(value: Any) -> Any:
    if value is None:
        return {}
    return json.loads(_canonical_json(value))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _proposal_hash(**values: Any) -> str:
    canonical = _canonical_json(_stable_json_value(values))
    return _hash_text(canonical)


def _risk_flags_for(
    *,
    action_kind: ActionProposalKind,
    source_trust: ActionProposalSourceTrust,
    status: ActionProposalStatus,
    has_targets: bool,
) -> tuple[ActionProposalRiskFlag, ...]:
    flags = {ActionProposalRiskFlag.HUMAN_REVIEW_REQUIRED}
    if source_trust is ActionProposalSourceTrust.PROVIDER_UNTRUSTED:
        flags.add(ActionProposalRiskFlag.PROVIDER_OUTPUT_UNTRUSTED)
    if status is ActionProposalStatus.INVALID_TARGET:
        flags.add(ActionProposalRiskFlag.INVALID_TARGET)
    if status is ActionProposalStatus.UNSUPPORTED_ACTION_KIND or action_kind is ActionProposalKind.UNKNOWN:
        flags.add(ActionProposalRiskFlag.UNKNOWN_ACTION_KIND)
        flags.add(ActionProposalRiskFlag.NOT_YET_GOVERNED)
    if action_kind is ActionProposalKind.FILE_WRITE:
        flags.add(ActionProposalRiskFlag.MUTATING_ACTION)
        flags.add(ActionProposalRiskFlag.FILESYSTEM_WRITE)
    elif action_kind in (ActionProposalKind.SHELL_COMMAND, ActionProposalKind.TEST_RUN):
        flags.add(ActionProposalRiskFlag.PROCESS_EXECUTION)
        flags.add(ActionProposalRiskFlag.NOT_YET_GOVERNED)
    elif action_kind in (ActionProposalKind.GIT_COMMIT, ActionProposalKind.GIT_PUSH):
        flags.add(ActionProposalRiskFlag.MUTATING_ACTION)
        flags.add(ActionProposalRiskFlag.GIT_OPERATION)
        flags.add(ActionProposalRiskFlag.HIGH_BLAST_RADIUS)
        flags.add(ActionProposalRiskFlag.NOT_YET_GOVERNED)
    elif action_kind is ActionProposalKind.PACKAGE_INSTALL:
        flags.add(ActionProposalRiskFlag.MUTATING_ACTION)
        flags.add(ActionProposalRiskFlag.PACKAGE_INSTALL)
        flags.add(ActionProposalRiskFlag.NETWORK_RELATED)
        flags.add(ActionProposalRiskFlag.HIGH_BLAST_RADIUS)
        flags.add(ActionProposalRiskFlag.NOT_YET_GOVERNED)
    elif action_kind is ActionProposalKind.PROVIDER_CALL:
        flags.add(ActionProposalRiskFlag.NETWORK_RELATED)
        flags.add(ActionProposalRiskFlag.NOT_YET_GOVERNED)
    elif action_kind is ActionProposalKind.BROWSER_ACTION:
        flags.add(ActionProposalRiskFlag.BROWSER_RELATED)
        flags.add(ActionProposalRiskFlag.NETWORK_RELATED)
        flags.add(ActionProposalRiskFlag.NOT_YET_GOVERNED)
    if not has_targets and action_kind is ActionProposalKind.FILE_WRITE:
        flags.add(ActionProposalRiskFlag.INVALID_TARGET)
    return tuple(sorted(flags, key=lambda flag: flag.value))


def _legacy_type_for_kind(action_kind: ActionProposalKind) -> ActionProposalType:
    if action_kind is ActionProposalKind.FILE_WRITE:
        return ActionProposalType.FILESYSTEM_ACTION
    if action_kind in (ActionProposalKind.SHELL_COMMAND, ActionProposalKind.TEST_RUN):
        return ActionProposalType.SHELL_COMMAND
    if action_kind in (ActionProposalKind.GIT_COMMIT, ActionProposalKind.GIT_PUSH):
        return ActionProposalType.GIT_ACTION
    if action_kind is ActionProposalKind.PROVIDER_CALL:
        return ActionProposalType.PROVIDER_CALL
    if action_kind is ActionProposalKind.BROWSER_ACTION:
        return ActionProposalType.BROWSER_ACTION
    return ActionProposalType.HUMAN_REVIEW_ONLY


def _legacy_risk_for_step11(
    status: ActionProposalStatus,
    action_kind: ActionProposalKind,
) -> ActionProposalRisk:
    if status is not ActionProposalStatus.PROPOSAL_READY:
        return ActionProposalRisk.UNKNOWN
    if _legacy_type_for_kind(action_kind) in _FORBIDDEN_PROPOSAL_TYPES:
        return ActionProposalRisk.FORBIDDEN
    return ActionProposalRisk.UNKNOWN


def _default_summary(action_kind: ActionProposalKind) -> str:
    return f"Action proposal metadata for {action_kind.value}."


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text value must be a string or None")
    text = value.strip()
    return text or None


def _coerce_text_tuple(name: str, values: Any) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{name} must be a tuple or list of strings")
    result = []
    for value in values:
        result.append(_coerce_text(name, value))
    return tuple(result)


def _coerce_risk_flags(values: Any) -> tuple[ActionProposalRiskFlag, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("risk_flags must be a tuple or list")
    return tuple(ActionProposalRiskFlag(value) for value in values)
