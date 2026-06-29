from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.git_ops.git_commit_preview import (
    GIT_COMMIT_PREVIEW_KIND,
    GIT_COMMIT_PREVIEW_PASS,
    GIT_COMMIT_PREVIEW_SCHEMA_VERSION,
    compute_git_commit_preview_hash,
)


GIT_COMMIT_BARRIER_SCHEMA_VERSION = "1A"
GIT_COMMIT_BARRIER_ELIGIBLE = "ELIGIBLE"
GIT_COMMIT_BARRIER_BLOCKED = "BLOCKED"

GIT_COMMIT_BARRIER_ELIGIBLE_METADATA_ONLY = "GIT_COMMIT_BARRIER_ELIGIBLE_METADATA_ONLY"
GIT_COMMIT_BARRIER_BLOCKED_MISSING_COMMIT_PREVIEW = "GIT_COMMIT_BARRIER_BLOCKED_MISSING_COMMIT_PREVIEW"
GIT_COMMIT_BARRIER_BLOCKED_INVALID_COMMIT_PREVIEW = "GIT_COMMIT_BARRIER_BLOCKED_INVALID_COMMIT_PREVIEW"
GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH = "GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH"
GIT_COMMIT_BARRIER_BLOCKED_MISSING_HUMAN_BARRIER = "GIT_COMMIT_BARRIER_BLOCKED_MISSING_HUMAN_BARRIER"
GIT_COMMIT_BARRIER_BLOCKED_HUMAN_BARRIER_NOT_PASSED = "GIT_COMMIT_BARRIER_BLOCKED_HUMAN_BARRIER_NOT_PASSED"
GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_MISSING = "GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_MISSING"
GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_HASH_MISMATCH = "GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_HASH_MISMATCH"
GIT_COMMIT_BARRIER_BLOCKED_UNTRUSTED_BARRIER_SOURCE = "GIT_COMMIT_BARRIER_BLOCKED_UNTRUSTED_BARRIER_SOURCE"
GIT_COMMIT_BARRIER_BLOCKED_AUTHORITY_CLAIM = "GIT_COMMIT_BARRIER_BLOCKED_AUTHORITY_CLAIM"
GIT_COMMIT_BARRIER_BLOCKED_UNSAFE_RISK_FLAG = "GIT_COMMIT_BARRIER_BLOCKED_UNSAFE_RISK_FLAG"

_AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "git_write_authority_granted",
    "git_commit_authority_granted",
    "git_push_authority_granted",
    "provider_authority_granted",
    "execution_authority_granted",
)
_EFFECT_FIELDS = (
    "commit_performed",
    "push_performed",
    "subprocess_started",
    "shell_invoked",
    "command_executed",
    "network_called",
    "github_called",
    "provider_called",
    "env_read",
    "api_key_loaded",
    "approval_created",
    "gate_changed",
    "control_write_changed",
)
_UNTRUSTED_SOURCES = frozenset({"PROVIDER_MODEL", "PROVIDER_OUTPUT", "UNTRUSTED_PROVIDER_OUTPUT", "MODEL_UNTRUSTED"})
_UNSAFE_RISK_FLAG_VALUES = frozenset(
    {
        "UNSAFE_COMMAND",
        "SHELL_COMMAND_BLOCKED",
        "ARBITRARY_COMMAND",
        "GITHUB_WRITE",
        "GITHUB_PUSH",
        "NETWORK_ACCESS_BLOCKED",
        "PROVIDER_CALL",
        "ENV_ACCESS_BLOCKED",
        "API_KEY_ACCESS_BLOCKED",
        "APPROVAL_MUTATION",
        "GATE_CHANGE",
        "CONTROL_WRITE_CHANGE",
    }
)
_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class GitCommitBarrierRequest:
    commit_preview: Any
    human_barrier: Any
    expected_commit_preview_hash: str | None = None
    expected_human_decision_hash: str | None = None
    source_trust: str = "USER_SUPPLIED"
    metadata: Mapping[str, Any] | None = None
    claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class GitCommitBarrierResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    commit_preview_hash: str | None
    human_barrier_hash: str | None
    human_decision_hash: str | None
    commit_barrier_hash: str
    eligible_for_controlled_commit: bool = False
    commit_performed: bool = False
    push_performed: bool = False
    subprocess_started: bool = False
    shell_invoked: bool = False
    command_executed: bool = False
    network_called: bool = False
    github_called: bool = False
    provider_called: bool = False
    env_read: bool = False
    api_key_loaded: bool = False
    approval_created: bool = False
    gate_changed: bool = False
    control_write_changed: bool = False
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    git_write_authority_granted: bool = False
    git_commit_authority_granted: bool = False
    git_push_authority_granted: bool = False
    provider_authority_granted: bool = False
    execution_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        for field_name in (*_EFFECT_FIELDS, *_AUTHORITY_FIELDS):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "commit_preview_hash": self.commit_preview_hash,
            "human_barrier_hash": self.human_barrier_hash,
            "human_decision_hash": self.human_decision_hash,
            "commit_barrier_hash": self.commit_barrier_hash,
            "eligible_for_controlled_commit": self.eligible_for_controlled_commit,
            **{field_name: getattr(self, field_name) for field_name in (*_EFFECT_FIELDS, *_AUTHORITY_FIELDS)},
        }


def evaluate_git_commit_barrier(request: GitCommitBarrierRequest) -> GitCommitBarrierResult:
    if not isinstance(request, GitCommitBarrierRequest):
        return _result(
            reason_codes=(GIT_COMMIT_BARRIER_BLOCKED_MISSING_COMMIT_PREVIEW,),
            commit_preview_hash=None,
            human_barrier_hash=None,
            human_decision_hash=None,
        )

    commit_preview = _mapping(request.commit_preview)
    human_barrier = _mapping(request.human_barrier)
    reason_codes: list[str] = []

    commit_preview_hash = _text(commit_preview.get("commit_preview_hash"))
    human_barrier_hash = _text(human_barrier.get("execution_barrier_hash"))
    human_decision_hash = _text(human_barrier.get("human_decision_hash"))

    _extend_authority_claims(reason_codes, commit_preview, human_barrier, request.metadata, request.claims)

    if not commit_preview:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_MISSING_COMMIT_PREVIEW)
    elif not _valid_commit_preview(commit_preview):
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_INVALID_COMMIT_PREVIEW)
        if _looks_like_sha256(commit_preview_hash) and _recomputed_commit_preview_hash(commit_preview) != commit_preview_hash:
            reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH)

    expected_preview_hash = _text(request.expected_commit_preview_hash) or commit_preview_hash
    if not _looks_like_sha256(expected_preview_hash) or commit_preview_hash != expected_preview_hash:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH)

    if not human_barrier:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_MISSING_HUMAN_BARRIER)
    else:
        if human_barrier.get("execution_barrier_passed") is not True or _text(human_barrier.get("status")) != "EXECUTION_BARRIER_PASSED":
            reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_HUMAN_BARRIER_NOT_PASSED)
        if not _looks_like_sha256(human_barrier_hash):
            reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_MISSING_HUMAN_BARRIER)
        if not _looks_like_sha256(human_decision_hash):
            reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_MISSING)

    source_trust = _text(request.source_trust)
    if source_trust is not None and source_trust.upper() in _UNTRUSTED_SOURCES:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_UNTRUSTED_BARRIER_SOURCE)
    decision_source = _text(human_barrier.get("human_decision_source"))
    if decision_source is not None and decision_source.upper() in _UNTRUSTED_SOURCES:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_UNTRUSTED_BARRIER_SOURCE)

    expected_human_decision_hash = _text(request.expected_human_decision_hash)
    if expected_human_decision_hash and human_decision_hash != expected_human_decision_hash:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_HASH_MISMATCH)

    bound_preview_hash = _text(human_barrier.get("human_decision_binds_to_commit_preview_hash"))
    if bound_preview_hash is None:
        bound_preview_hash = _text(human_barrier.get("human_decision_binds_to_command_hash"))
    barrier_command_hash = _text(human_barrier.get("requested_command_hash"))
    if commit_preview_hash != bound_preview_hash or commit_preview_hash != barrier_command_hash:
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH)

    if _unsafe_risk_flags(commit_preview.get("risk_flags")) or _unsafe_risk_flags(human_barrier.get("risk_flags")):
        reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_UNSAFE_RISK_FLAG)

    if not reason_codes:
        reason_codes.append(GIT_COMMIT_BARRIER_ELIGIBLE_METADATA_ONLY)

    return _result(
        reason_codes=tuple(reason_codes),
        commit_preview_hash=commit_preview_hash,
        human_barrier_hash=human_barrier_hash,
        human_decision_hash=human_decision_hash,
    )


def _valid_commit_preview(commit_preview: Mapping[str, Any]) -> bool:
    if commit_preview.get("preview_kind") != GIT_COMMIT_PREVIEW_KIND:
        return False
    if commit_preview.get("schema_version") != GIT_COMMIT_PREVIEW_SCHEMA_VERSION:
        return False
    if commit_preview.get("status") != GIT_COMMIT_PREVIEW_PASS:
        return False
    preview_hash = _text(commit_preview.get("commit_preview_hash"))
    if not _looks_like_sha256(preview_hash):
        return False
    return _recomputed_commit_preview_hash(commit_preview) == preview_hash


def _recomputed_commit_preview_hash(commit_preview: Mapping[str, Any]) -> str:
    material = dict(commit_preview)
    material.pop("commit_preview_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return compute_git_commit_preview_hash(material)


def _result(
    *,
    reason_codes: tuple[str, ...],
    commit_preview_hash: str | None,
    human_barrier_hash: str | None,
    human_decision_hash: str | None,
) -> GitCommitBarrierResult:
    blocked = any(code != GIT_COMMIT_BARRIER_ELIGIBLE_METADATA_ONLY for code in reason_codes)
    status = GIT_COMMIT_BARRIER_BLOCKED if blocked else GIT_COMMIT_BARRIER_ELIGIBLE
    payload = {
        "schema_version": GIT_COMMIT_BARRIER_SCHEMA_VERSION,
        "status": status,
        "reason_codes": sorted(set(reason_codes)),
        "commit_preview_hash": commit_preview_hash,
        "human_barrier_hash": human_barrier_hash,
        "human_decision_hash": human_decision_hash,
        "eligible_for_controlled_commit": not blocked,
    }
    return GitCommitBarrierResult(
        schema_version=GIT_COMMIT_BARRIER_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        commit_preview_hash=commit_preview_hash,
        human_barrier_hash=human_barrier_hash,
        human_decision_hash=human_decision_hash,
        commit_barrier_hash=_hash_json(payload),
        eligible_for_controlled_commit=not blocked,
    )


def _extend_authority_claims(reason_codes: list[str], *values: Any) -> None:
    for value in values:
        mapping = _mapping(value)
        if any(mapping.get(field_name) is True for field_name in (*_AUTHORITY_FIELDS, *_EFFECT_FIELDS)):
            reason_codes.append(GIT_COMMIT_BARRIER_BLOCKED_AUTHORITY_CLAIM)


def _unsafe_risk_flags(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        items = (value,)
    elif isinstance(value, (tuple, list, set, frozenset)):
        items = value
    else:
        return True
    return bool({_text(item).upper() for item in items if _text(item) is not None} & _UNSAFE_RISK_FLAG_VALUES)


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _looks_like_sha256(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value)


def _hash_json(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
