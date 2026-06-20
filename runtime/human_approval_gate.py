from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from runtime.provider_flow_audit import redact_audit_text


# Approval-G0A records a hash-bound human decision. It is not an execution gate.
HASH_BOUND_HUMAN_APPROVAL_RECORD = "HASH_BOUND_HUMAN_APPROVAL_RECORD"
HUMAN_APPROVAL_SCHEMA_VERSION = "1.0"
HUMAN_DECISION_RECORD_ONLY = "HUMAN_DECISION_RECORD_ONLY"
NO_EXECUTION_AUTHORITY = "NO_EXECUTION_AUTHORITY"
HUMAN_DECISION_RECORDED_NO_EXECUTION = "HUMAN_DECISION_RECORDED_NO_EXECUTION"

NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
NO_PROVIDER_TRUST_CHANGE = "NO_PROVIDER_TRUST_CHANGE"
NO_CANONICAL_PROMOTION = "NO_CANONICAL_PROMOTION"
NO_GITHUB_ACTION = "NO_GITHUB_ACTION"
HASH_BOUND_DECISION_ONLY = "HASH_BOUND_DECISION_ONLY"
SUMMARY_NOT_AUTHORITY = "SUMMARY_NOT_AUTHORITY"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_HEX = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class HumanApprovalGateError(ValueError):
    """Raised when a human decision record violates the inert G0A boundary."""


class HumanApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CHANGES = "NEEDS_CHANGES"


class HumanApprovalTargetType(str, Enum):
    PLAN = "PLAN"
    DIFF = "DIFF"
    COMMAND = "COMMAND"
    GITHUB_ACTION = "GITHUB_ACTION"
    PROVIDER_FLOW_AUDIT = "PROVIDER_FLOW_AUDIT"
    OTHER = "OTHER"


class HumanApprovalBoundary(str, Enum):
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_PROVIDER_TRUST_CHANGE = NO_PROVIDER_TRUST_CHANGE
    NO_CANONICAL_PROMOTION = NO_CANONICAL_PROMOTION
    NO_GITHUB_ACTION = NO_GITHUB_ACTION
    HASH_BOUND_DECISION_ONLY = HASH_BOUND_DECISION_ONLY
    SUMMARY_NOT_AUTHORITY = SUMMARY_NOT_AUTHORITY


@dataclass(frozen=True)
class HashBoundHumanApprovalRecord:
    label: str
    schema_version: str
    approval_role: str
    approval_scope: str
    approval_id: str
    created_at_utc: str | None
    repo_path: str
    branch: str
    head_commit: str
    target_type: HumanApprovalTargetType
    target_hash: str
    target_summary: str | None
    allowed_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]
    decision: HumanApprovalDecision
    human_reviewer_ref: str | None
    reason: str | None
    provider_flow_audit_ref: str | None
    provider_flow_audit_hash: str | None
    approval_binding_hash: str
    final_status: str
    safety_boundaries: tuple[HumanApprovalBoundary, ...]
    execution_authority: bool
    artifact_write_authority: bool
    provider_trust_authority: bool
    canonical_promotion_authority: bool
    github_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "approval_role": self.approval_role,
            "approval_scope": self.approval_scope,
            "approval_id": self.approval_id,
            "created_at_utc": self.created_at_utc,
            "repo_path": self.repo_path,
            "branch": self.branch,
            "head_commit": self.head_commit,
            "target_type": self.target_type.value,
            "target_hash": self.target_hash,
            "target_summary": self.target_summary,
            "allowed_scope": list(self.allowed_scope),
            "forbidden_scope": list(self.forbidden_scope),
            "decision": self.decision.value,
            "human_reviewer_ref": self.human_reviewer_ref,
            "reason": self.reason,
            "provider_flow_audit_ref": self.provider_flow_audit_ref,
            "provider_flow_audit_hash": self.provider_flow_audit_hash,
            "approval_binding_hash": self.approval_binding_hash,
            "final_status": self.final_status,
            "safety_boundaries": [item.value for item in self.safety_boundaries],
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_trust_authority": self.provider_trust_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
            "github_authority": self.github_authority,
        }


@dataclass(frozen=True)
class HumanApprovalVerificationResult:
    valid: bool
    approval_id: str
    approval_binding_hash: str
    decision: HumanApprovalDecision
    target_hash: str
    final_status: str
    execution_authority: bool
    artifact_write_authority: bool
    provider_trust_authority: bool
    canonical_promotion_authority: bool
    github_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "approval_id": self.approval_id,
            "approval_binding_hash": self.approval_binding_hash,
            "decision": self.decision.value,
            "target_hash": self.target_hash,
            "final_status": self.final_status,
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_trust_authority": self.provider_trust_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
            "github_authority": self.github_authority,
        }


def compute_approval_binding_hash(
    *,
    repo_path: str,
    branch: str,
    head_commit: str,
    target_type: HumanApprovalTargetType | str,
    target_hash: str,
    allowed_scope: Iterable[str] = (),
    forbidden_scope: Iterable[str] = (),
    decision: HumanApprovalDecision | str,
    provider_flow_audit_ref: str | None = None,
    provider_flow_audit_hash: str | None = None,
    known_secrets: Iterable[str] = (),
) -> str:
    secrets = _known_secrets(known_secrets)
    material = _binding_material(
        repo_path=repo_path,
        branch=branch,
        head_commit=head_commit,
        target_type=target_type,
        target_hash=target_hash,
        allowed_scope=allowed_scope,
        forbidden_scope=forbidden_scope,
        decision=decision,
        provider_flow_audit_ref=provider_flow_audit_ref,
        provider_flow_audit_hash=provider_flow_audit_hash,
        known_secrets=secrets,
    )
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def build_hash_bound_human_approval_record(
    *,
    repo_path: str,
    branch: str,
    head_commit: str,
    target_type: HumanApprovalTargetType | str,
    target_hash: str,
    decision: HumanApprovalDecision | str,
    allowed_scope: Iterable[str] = (),
    forbidden_scope: Iterable[str] = (),
    target_summary: str | None = None,
    human_reviewer_ref: str | None = None,
    reason: str | None = None,
    provider_flow_audit_ref: str | None = None,
    provider_flow_audit_hash: str | None = None,
    created_at_utc: str | None = None,
    known_secrets: Iterable[str] = (),
) -> HashBoundHumanApprovalRecord:
    secrets = _known_secrets(known_secrets)
    material = _binding_material(
        repo_path=repo_path,
        branch=branch,
        head_commit=head_commit,
        target_type=target_type,
        target_hash=target_hash,
        allowed_scope=allowed_scope,
        forbidden_scope=forbidden_scope,
        decision=decision,
        provider_flow_audit_ref=provider_flow_audit_ref,
        provider_flow_audit_hash=provider_flow_audit_hash,
        known_secrets=secrets,
    )
    binding_hash = hashlib.sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    record = HashBoundHumanApprovalRecord(
        label=HASH_BOUND_HUMAN_APPROVAL_RECORD,
        schema_version=HUMAN_APPROVAL_SCHEMA_VERSION,
        approval_role=HUMAN_DECISION_RECORD_ONLY,
        approval_scope=NO_EXECUTION_AUTHORITY,
        approval_id="approval-g0a-" + binding_hash[:24],
        created_at_utc=_optional_text(created_at_utc, "created_at_utc", secrets, 128),
        repo_path=material["repo_path"],
        branch=material["branch"],
        head_commit=material["head_commit"],
        target_type=HumanApprovalTargetType(material["target_type"]),
        target_hash=material["target_hash"],
        target_summary=_optional_text(target_summary, "target_summary", secrets, 4096),
        allowed_scope=tuple(material["allowed_scope"]),
        forbidden_scope=tuple(material["forbidden_scope"]),
        decision=HumanApprovalDecision(material["decision"]),
        human_reviewer_ref=_optional_text(
            human_reviewer_ref,
            "human_reviewer_ref",
            secrets,
            256,
        ),
        reason=_optional_text(reason, "reason", secrets, 4096),
        provider_flow_audit_ref=material["provider_flow_audit_ref"],
        provider_flow_audit_hash=material["provider_flow_audit_hash"],
        approval_binding_hash=binding_hash,
        final_status=HUMAN_DECISION_RECORDED_NO_EXECUTION,
        safety_boundaries=_required_boundaries(),
        execution_authority=False,
        artifact_write_authority=False,
        provider_trust_authority=False,
        canonical_promotion_authority=False,
        github_authority=False,
    )
    verify_hash_bound_human_approval_record(record)
    return record


def verify_hash_bound_human_approval_record(
    record: HashBoundHumanApprovalRecord,
) -> HumanApprovalVerificationResult:
    if not isinstance(record, HashBoundHumanApprovalRecord):
        raise HumanApprovalGateError(
            "record must be a HashBoundHumanApprovalRecord"
        )
    if (
        not isinstance(record.target_type, HumanApprovalTargetType)
        or not isinstance(record.decision, HumanApprovalDecision)
        or any(
            not isinstance(item, HumanApprovalBoundary)
            for item in record.safety_boundaries
        )
        or record.label != HASH_BOUND_HUMAN_APPROVAL_RECORD
        or record.schema_version != HUMAN_APPROVAL_SCHEMA_VERSION
        or record.approval_role != HUMAN_DECISION_RECORD_ONLY
        or record.approval_scope != NO_EXECUTION_AUTHORITY
        or record.final_status != HUMAN_DECISION_RECORDED_NO_EXECUTION
        or tuple(record.safety_boundaries) != _required_boundaries()
        or record.execution_authority is not False
        or record.artifact_write_authority is not False
        or record.provider_trust_authority is not False
        or record.canonical_promotion_authority is not False
        or record.github_authority is not False
    ):
        raise HumanApprovalGateError(
            "human decision record violates the no-authority boundary"
        )
    _assert_metadata_is_sanitized(record)
    normalized = _binding_material(
        repo_path=record.repo_path,
        branch=record.branch,
        head_commit=record.head_commit,
        target_type=record.target_type,
        target_hash=record.target_hash,
        allowed_scope=record.allowed_scope,
        forbidden_scope=record.forbidden_scope,
        decision=record.decision,
        provider_flow_audit_ref=record.provider_flow_audit_ref,
        provider_flow_audit_hash=record.provider_flow_audit_hash,
        known_secrets=(),
    )
    if (
        record.repo_path != normalized["repo_path"]
        or record.branch != normalized["branch"]
        or record.head_commit != normalized["head_commit"]
        or record.target_type.value != normalized["target_type"]
        or record.target_hash != normalized["target_hash"]
        or record.allowed_scope != tuple(normalized["allowed_scope"])
        or record.forbidden_scope != tuple(normalized["forbidden_scope"])
        or record.decision.value != normalized["decision"]
        or record.provider_flow_audit_ref
        != normalized["provider_flow_audit_ref"]
        or record.provider_flow_audit_hash
        != normalized["provider_flow_audit_hash"]
    ):
        raise HumanApprovalGateError("approval binding fields are not canonical")
    expected_hash = hashlib.sha256(
        _canonical_json(normalized).encode("utf-8")
    ).hexdigest()
    if record.approval_binding_hash != expected_hash:
        raise HumanApprovalGateError("approval binding hash mismatch")
    if record.approval_id != "approval-g0a-" + expected_hash[:24]:
        raise HumanApprovalGateError("approval id mismatch")
    return HumanApprovalVerificationResult(
        valid=True,
        approval_id=record.approval_id,
        approval_binding_hash=record.approval_binding_hash,
        decision=record.decision,
        target_hash=record.target_hash,
        final_status=record.final_status,
        execution_authority=False,
        artifact_write_authority=False,
        provider_trust_authority=False,
        canonical_promotion_authority=False,
        github_authority=False,
    )


def _binding_material(
    *,
    repo_path: str,
    branch: str,
    head_commit: str,
    target_type: HumanApprovalTargetType | str,
    target_hash: str,
    allowed_scope: Iterable[str],
    forbidden_scope: Iterable[str],
    decision: HumanApprovalDecision | str,
    provider_flow_audit_ref: str | None,
    provider_flow_audit_hash: str | None,
    known_secrets: tuple[str, ...],
) -> dict[str, Any]:
    normalized_repo = _required_text(repo_path, "repo_path", known_secrets, 4096)
    normalized_branch = _required_text(branch, "branch", known_secrets, 512)
    normalized_head = _required_hash(
        head_commit,
        "head_commit",
        _GIT_COMMIT_HEX,
        "a 40- or 64-character lowercase Git commit hash",
    )
    normalized_target_hash = _required_hash(
        target_hash,
        "target_hash",
        _SHA256_HEX,
        "a lowercase SHA-256 hash",
    )
    target_kind = _enum_value(HumanApprovalTargetType, target_type, "target_type")
    decision_value = _enum_value(HumanApprovalDecision, decision, "decision")
    audit_hash = _optional_hash(provider_flow_audit_hash, "provider_flow_audit_hash")
    return {
        "repo_path": normalized_repo,
        "branch": normalized_branch,
        "head_commit": normalized_head,
        "target_type": target_kind,
        "target_hash": normalized_target_hash,
        "allowed_scope": list(
            _scope_values(allowed_scope, "allowed_scope", known_secrets)
        ),
        "forbidden_scope": list(
            _scope_values(forbidden_scope, "forbidden_scope", known_secrets)
        ),
        "decision": decision_value,
        "provider_flow_audit_ref": _optional_text(
            provider_flow_audit_ref,
            "provider_flow_audit_ref",
            known_secrets,
            512,
        ),
        "provider_flow_audit_hash": audit_hash,
    }


def _required_text(
    value: str,
    name: str,
    known_secrets: tuple[str, ...],
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise HumanApprovalGateError(f"{name} must be a string")
    sanitized = redact_audit_text(value, known_secrets=known_secrets).strip()
    if not sanitized:
        raise HumanApprovalGateError(f"{name} is required")
    if len(sanitized) > max_length:
        raise HumanApprovalGateError(f"{name} is too long")
    return sanitized


def _optional_text(
    value: str | None,
    name: str,
    known_secrets: tuple[str, ...],
    max_length: int,
) -> str | None:
    if value is None:
        return None
    sanitized = _required_text(value, name, known_secrets, max_length)
    return sanitized


def _scope_values(
    values: Iterable[str],
    name: str,
    known_secrets: tuple[str, ...],
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise HumanApprovalGateError(f"{name} must be an iterable of strings")
    try:
        normalized = {
            _required_text(value, name, known_secrets, 512) for value in values
        }
    except TypeError as error:
        raise HumanApprovalGateError(
            f"{name} must be an iterable of strings"
        ) from error
    return tuple(sorted(normalized))


def _required_hash(
    value: str,
    name: str,
    pattern: re.Pattern[str],
    description: str,
) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise HumanApprovalGateError(f"{name} must be {description}")
    return value


def _optional_hash(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    return _required_hash(value, name, _SHA256_HEX, "a lowercase SHA-256 hash")


def _enum_value(enum_type: type[Enum], value: Enum | str, name: str) -> str:
    try:
        return enum_type(value).value
    except (TypeError, ValueError) as error:
        raise HumanApprovalGateError(f"invalid {name}") from error


def _known_secrets(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise HumanApprovalGateError("known_secrets must be an iterable of strings")
    try:
        candidates = tuple(values)
    except TypeError as error:
        raise HumanApprovalGateError(
            "known_secrets must be an iterable of strings"
        ) from error
    if any(not isinstance(value, str) for value in candidates):
        raise HumanApprovalGateError("known_secrets must contain strings")
    return tuple(value for value in candidates if value)


def _required_boundaries() -> tuple[HumanApprovalBoundary, ...]:
    return (
        HumanApprovalBoundary.NO_EXECUTION,
        HumanApprovalBoundary.NO_ARTIFACT_WRITE,
        HumanApprovalBoundary.NO_PROVIDER_TRUST_CHANGE,
        HumanApprovalBoundary.NO_CANONICAL_PROMOTION,
        HumanApprovalBoundary.NO_GITHUB_ACTION,
        HumanApprovalBoundary.HASH_BOUND_DECISION_ONLY,
        HumanApprovalBoundary.SUMMARY_NOT_AUTHORITY,
    )


def _assert_metadata_is_sanitized(record: HashBoundHumanApprovalRecord) -> None:
    for name, value in (
        ("target_summary", record.target_summary),
        ("human_reviewer_ref", record.human_reviewer_ref),
        ("reason", record.reason),
        ("provider_flow_audit_ref", record.provider_flow_audit_ref),
        ("created_at_utc", record.created_at_utc),
    ):
        if value is not None and redact_audit_text(value) != value:
            raise HumanApprovalGateError(f"{name} contains unsafe audit text")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
