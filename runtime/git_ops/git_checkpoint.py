from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.git_ops.git_governance import GIT_GOVERNANCE_BLOCK, GIT_GOVERNANCE_NEEDS_REVIEW, GIT_GOVERNANCE_PASS
from runtime.git_ops.git_read import GIT_READ_READY


GIT_CHECKPOINT_KIND = "AOIA_GIT_NATIVE_STATE_CHECKPOINT"
GIT_CHECKPOINT_SCHEMA_VERSION = "1A"
GIT_CHECKPOINT_VALID = "VALID"
GIT_CHECKPOINT_INVALID = "INVALID"
GIT_CHECKPOINT_BLOCKED = "BLOCKED"
GIT_CHECKPOINT_CREATED = "CREATED"

GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ = "GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ"
GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE = "GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE"
GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ_HASH = "GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ_HASH"
GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH = "GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH"
GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH = "GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH"
GIT_CHECKPOINT_BLOCKED_GIT_READ_STATUS = "GIT_CHECKPOINT_BLOCKED_GIT_READ_STATUS"
GIT_CHECKPOINT_BLOCKED_GOVERNANCE_BLOCK = "GIT_CHECKPOINT_BLOCKED_GOVERNANCE_BLOCK"
GIT_CHECKPOINT_BLOCKED_GOVERNANCE_REVIEW = "GIT_CHECKPOINT_BLOCKED_GOVERNANCE_REVIEW"
GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT = "GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT"
GIT_CHECKPOINT_BLOCKED_MISSING_HEAD = "GIT_CHECKPOINT_BLOCKED_MISSING_HEAD"
GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH = "GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH"
GIT_CHECKPOINT_BLOCKED_DETACHED_HEAD = "GIT_CHECKPOINT_BLOCKED_DETACHED_HEAD"
GIT_CHECKPOINT_BLOCKED_AUTHORITY_CLAIM = "GIT_CHECKPOINT_BLOCKED_AUTHORITY_CLAIM"
GIT_CHECKPOINT_BLOCKED_MALFORMED_INPUT = "GIT_CHECKPOINT_BLOCKED_MALFORMED_INPUT"
GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH = "GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH"
GIT_CHECKPOINT_BLOCKED_KIND_MISMATCH = "GIT_CHECKPOINT_BLOCKED_KIND_MISMATCH"
GIT_CHECKPOINT_BLOCKED_SCHEMA_MISMATCH = "GIT_CHECKPOINT_BLOCKED_SCHEMA_MISMATCH"
GIT_CHECKPOINT_VALID_EVIDENCE_ONLY = "GIT_CHECKPOINT_VALID_EVIDENCE_ONLY"

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
_AUTHORITY_CLAIM_FIELDS = (*_AUTHORITY_FIELDS, "write_authority_granted", "approval_granted", "commit_authority_granted", "push_authority_granted")
_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class GitStateCheckpointRequest:
    git_read_result: Any
    git_governance_result: Any
    created_at: str
    checkpoint_nonce: str | None = None
    allow_review_checkpoint: bool = False
    require_branch: bool = True
    block_detached_head: bool = True
    claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class GitStateCheckpoint:
    checkpoint_kind: str
    schema_version: str
    checkpoint_hash: str
    git_read_hash: str
    governance_hash: str
    governance_status: str
    governance_policy_name: str
    governance_policy_version: str
    governance_input_git_read_hash: str
    repo_root: str
    repo_identity_hash: str
    head_sha: str
    branch_name: str | None
    detached_head: bool
    clean: bool | None
    staged_paths_hash: str
    unstaged_paths_hash: str
    untracked_paths_hash: str
    staged_paths: tuple[str, ...]
    unstaged_paths: tuple[str, ...]
    untracked_paths: tuple[str, ...]
    protected_path_finding_summary: tuple[str, ...]
    path_risk_finding_summary: tuple[str, ...]
    sanitizer_output_bound_evidence: tuple[str, ...]
    created_at: str
    checkpoint_nonce: str | None = None
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
        object.__setattr__(self, "staged_paths", tuple(sorted(set(self.staged_paths))))
        object.__setattr__(self, "unstaged_paths", tuple(sorted(set(self.unstaged_paths))))
        object.__setattr__(self, "untracked_paths", tuple(sorted(set(self.untracked_paths))))
        object.__setattr__(self, "protected_path_finding_summary", tuple(sorted(set(self.protected_path_finding_summary))))
        object.__setattr__(self, "path_risk_finding_summary", tuple(sorted(set(self.path_risk_finding_summary))))
        object.__setattr__(self, "sanitizer_output_bound_evidence", tuple(sorted(set(self.sanitizer_output_bound_evidence))))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_kind": self.checkpoint_kind,
            "schema_version": self.schema_version,
            "checkpoint_hash": self.checkpoint_hash,
            "git_read_hash": self.git_read_hash,
            "governance_hash": self.governance_hash,
            "governance_status": self.governance_status,
            "governance_policy_name": self.governance_policy_name,
            "governance_policy_version": self.governance_policy_version,
            "governance_input_git_read_hash": self.governance_input_git_read_hash,
            "repo_root": self.repo_root,
            "repo_identity_hash": self.repo_identity_hash,
            "head_sha": self.head_sha,
            "branch_name": self.branch_name,
            "detached_head": self.detached_head,
            "clean": self.clean,
            "staged_paths_hash": self.staged_paths_hash,
            "unstaged_paths_hash": self.unstaged_paths_hash,
            "untracked_paths_hash": self.untracked_paths_hash,
            "staged_paths": self.staged_paths,
            "unstaged_paths": self.unstaged_paths,
            "untracked_paths": self.untracked_paths,
            "protected_path_finding_summary": self.protected_path_finding_summary,
            "path_risk_finding_summary": self.path_risk_finding_summary,
            "sanitizer_output_bound_evidence": self.sanitizer_output_bound_evidence,
            "created_at": self.created_at,
            "checkpoint_nonce": self.checkpoint_nonce,
            **{field_name: getattr(self, field_name) for field_name in _AUTHORITY_FIELDS},
        }


@dataclass(frozen=True)
class GitStateCheckpointResult:
    status: str
    reason_codes: tuple[str, ...]
    checkpoint: GitStateCheckpoint | None = None
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
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": self.reason_codes,
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint is not None else None,
            **{field_name: getattr(self, field_name) for field_name in _AUTHORITY_FIELDS},
        }


def create_git_state_checkpoint(request: GitStateCheckpointRequest) -> GitStateCheckpointResult:
    git_read = _mapping(request.git_read_result)
    governance = _mapping(request.git_governance_result)
    reasons = _creation_blockers(request, git_read, governance)
    if reasons:
        return _blocked(reasons)

    assert git_read is not None
    assert governance is not None
    material = _checkpoint_material(
        git_read=git_read,
        governance=governance,
        created_at=request.created_at,
        checkpoint_nonce=request.checkpoint_nonce,
    )
    checkpoint_hash = compute_git_checkpoint_hash(material)
    checkpoint = GitStateCheckpoint(checkpoint_hash=checkpoint_hash, **material)
    if compute_git_checkpoint_hash(_checkpoint_hash_material(checkpoint.to_dict())) != checkpoint_hash:
        return _blocked((GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH,))
    return GitStateCheckpointResult(status=GIT_CHECKPOINT_CREATED, reason_codes=(GIT_CHECKPOINT_VALID_EVIDENCE_ONLY,), checkpoint=checkpoint)


def verify_git_state_checkpoint(
    checkpoint: GitStateCheckpoint | Mapping[str, Any] | Any,
    git_read_result: Any,
    git_governance_result: Any,
) -> GitStateCheckpointResult:
    checkpoint_mapping = _mapping(checkpoint)
    git_read = _mapping(git_read_result)
    governance = _mapping(git_governance_result)
    if checkpoint_mapping is None or git_read is None or governance is None:
        return _invalid((GIT_CHECKPOINT_BLOCKED_MALFORMED_INPUT,))

    reasons: list[str] = []
    if checkpoint_mapping.get("checkpoint_kind") != GIT_CHECKPOINT_KIND:
        reasons.append(GIT_CHECKPOINT_BLOCKED_KIND_MISMATCH)
    if checkpoint_mapping.get("schema_version") != GIT_CHECKPOINT_SCHEMA_VERSION:
        reasons.append(GIT_CHECKPOINT_BLOCKED_SCHEMA_MISMATCH)
    if _authority_claim_present(checkpoint_mapping) or _authority_claim_present(git_read) or _authority_claim_present(governance):
        reasons.append(GIT_CHECKPOINT_BLOCKED_AUTHORITY_CLAIM)

    bound_hash = _text(checkpoint_mapping.get("checkpoint_hash"))
    if not _hash_like(bound_hash):
        reasons.append(GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH)
    elif compute_git_checkpoint_hash(_checkpoint_hash_material(checkpoint_mapping)) != bound_hash:
        reasons.append(GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH)

    expected = _expected_bindings(git_read, governance)
    for key, expected_value in expected.items():
        if checkpoint_mapping.get(key) != expected_value:
            reasons.append(_verification_reason_for_key(key))

    if reasons:
        return _invalid(tuple(reasons))
    restored = GitStateCheckpoint(**checkpoint_mapping)
    return GitStateCheckpointResult(status=GIT_CHECKPOINT_VALID, reason_codes=(GIT_CHECKPOINT_VALID_EVIDENCE_ONLY,), checkpoint=restored)


def canonical_git_checkpoint_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_git_checkpoint_hash(value: Any) -> str:
    return hashlib.sha256(canonical_git_checkpoint_json(value).encode("utf-8")).hexdigest()


def _creation_blockers(
    request: GitStateCheckpointRequest,
    git_read: dict[str, Any] | None,
    governance: dict[str, Any] | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if git_read is None:
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ)
    if governance is None:
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE)
    if git_read is None or governance is None:
        return tuple(reasons)

    git_read_hash = _text(git_read.get("git_read_hash"))
    governance_hash = _text(governance.get("governance_hash"))
    governance_input_hash = _text(governance.get("input_git_read_hash"))
    if not _hash_like(git_read_hash):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ_HASH)
    if not _hash_like(governance_hash):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH)
    if git_read_hash and governance_input_hash != git_read_hash:
        reasons.append(GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH)
    if git_read.get("status") != GIT_READ_READY:
        reasons.append(GIT_CHECKPOINT_BLOCKED_GIT_READ_STATUS)
    if governance.get("status") == GIT_GOVERNANCE_BLOCK:
        reasons.append(GIT_CHECKPOINT_BLOCKED_GOVERNANCE_BLOCK)
    elif governance.get("status") == GIT_GOVERNANCE_NEEDS_REVIEW and not request.allow_review_checkpoint:
        reasons.append(GIT_CHECKPOINT_BLOCKED_GOVERNANCE_REVIEW)
    elif governance.get("status") not in (GIT_GOVERNANCE_PASS, GIT_GOVERNANCE_NEEDS_REVIEW):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MALFORMED_INPUT)
    if not _text(git_read.get("repo_root")):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT)
    if not _hash_like(_text(git_read.get("head_sha")), allow_sha1=True):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_HEAD)
    if request.require_branch and git_read.get("detached_head") is not True and not _text(git_read.get("branch_name")):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH)
    if request.block_detached_head and git_read.get("detached_head") is True:
        reasons.append(GIT_CHECKPOINT_BLOCKED_DETACHED_HEAD)
    if _authority_claim_present(git_read) or _authority_claim_present(governance) or _authority_claim_present(request.claims or {}):
        reasons.append(GIT_CHECKPOINT_BLOCKED_AUTHORITY_CLAIM)
    if not _text(request.created_at):
        reasons.append(GIT_CHECKPOINT_BLOCKED_MALFORMED_INPUT)
    return tuple(reasons)


def _checkpoint_material(
    *,
    git_read: Mapping[str, Any],
    governance: Mapping[str, Any],
    created_at: str,
    checkpoint_nonce: str | None,
) -> dict[str, Any]:
    staged_paths = _safe_paths(git_read.get("staged_paths"))
    unstaged_paths = _safe_paths(git_read.get("unstaged_paths"))
    untracked_paths = _safe_paths(git_read.get("untracked_paths"))
    repo_root = _text(git_read.get("repo_root")) or ""
    return {
        "checkpoint_kind": GIT_CHECKPOINT_KIND,
        "schema_version": GIT_CHECKPOINT_SCHEMA_VERSION,
        "git_read_hash": _text(git_read.get("git_read_hash")) or "",
        "governance_hash": _text(governance.get("governance_hash")) or "",
        "governance_status": _text(governance.get("status")) or "",
        "governance_policy_name": _text(governance.get("policy_name")) or "",
        "governance_policy_version": _text(governance.get("policy_version")) or "",
        "governance_input_git_read_hash": _text(governance.get("input_git_read_hash")) or "",
        "repo_root": repo_root,
        "repo_identity_hash": compute_git_checkpoint_hash({"repo_root": repo_root}),
        "head_sha": _text(git_read.get("head_sha")) or "",
        "branch_name": _text(git_read.get("branch_name")),
        "detached_head": git_read.get("detached_head") is True,
        "clean": git_read.get("clean") if isinstance(git_read.get("clean"), bool) else None,
        "staged_paths_hash": compute_git_checkpoint_hash(staged_paths),
        "unstaged_paths_hash": compute_git_checkpoint_hash(unstaged_paths),
        "untracked_paths_hash": compute_git_checkpoint_hash(untracked_paths),
        "staged_paths": staged_paths,
        "unstaged_paths": unstaged_paths,
        "untracked_paths": untracked_paths,
        "protected_path_finding_summary": _finding_summary(governance, ("PROTECTED",)),
        "path_risk_finding_summary": _finding_summary(governance, ("PATH", "ATTRIBUTE", "DIRTY", "STAGED", "UNSTAGED", "UNTRACKED")),
        "sanitizer_output_bound_evidence": _sanitizer_output_bound_evidence(git_read),
        "created_at": created_at,
        "checkpoint_nonce": checkpoint_nonce,
    }


def _expected_bindings(git_read: Mapping[str, Any], governance: Mapping[str, Any]) -> dict[str, Any]:
    material = _checkpoint_material(
        git_read=git_read,
        governance=governance,
        created_at="verification-placeholder",
        checkpoint_nonce=None,
    )
    return {
        "git_read_hash": material["git_read_hash"],
        "governance_hash": material["governance_hash"],
        "governance_input_git_read_hash": material["governance_input_git_read_hash"],
        "repo_root": material["repo_root"],
        "repo_identity_hash": material["repo_identity_hash"],
        "head_sha": material["head_sha"],
        "branch_name": material["branch_name"],
        "detached_head": material["detached_head"],
        "clean": material["clean"],
        "staged_paths_hash": material["staged_paths_hash"],
        "unstaged_paths_hash": material["unstaged_paths_hash"],
        "untracked_paths_hash": material["untracked_paths_hash"],
    }


def _checkpoint_hash_material(checkpoint_mapping: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(checkpoint_mapping)
    material.pop("checkpoint_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _finding_summary(governance: Mapping[str, Any], markers: tuple[str, ...]) -> tuple[str, ...]:
    summary: list[str] = []
    for finding in _sequence(governance.get("findings")):
        item = _mapping(finding)
        if item is None:
            continue
        reason = _text(item.get("reason_code")) or ""
        if any(marker in reason for marker in markers):
            paths = _safe_paths(item.get("paths"))
            summary.append(canonical_git_checkpoint_json({"reason_code": reason, "severity": item.get("severity"), "paths": paths}))
    return tuple(sorted(set(summary)))


def _sanitizer_output_bound_evidence(git_read: Mapping[str, Any]) -> tuple[str, ...]:
    evidence: list[str] = []
    for item in _sequence(git_read.get("command_evidence")):
        command = _mapping(item)
        if command is None:
            continue
        if command.get("stdout_truncated") is True or command.get("stderr_truncated") is True or command.get("timeout_expired") is True:
            evidence.append(canonical_git_checkpoint_json({
                "command_id": command.get("command_id"),
                "stdout_truncated": command.get("stdout_truncated") is True,
                "stderr_truncated": command.get("stderr_truncated") is True,
                "timeout_expired": command.get("timeout_expired") is True,
            }))
    return tuple(sorted(set(evidence)))


def _blocked(reason_codes: tuple[str, ...]) -> GitStateCheckpointResult:
    return GitStateCheckpointResult(status=GIT_CHECKPOINT_BLOCKED, reason_codes=reason_codes)


def _invalid(reason_codes: tuple[str, ...]) -> GitStateCheckpointResult:
    return GitStateCheckpointResult(status=GIT_CHECKPOINT_INVALID, reason_codes=reason_codes)


def _verification_reason_for_key(key: str) -> str:
    if key in ("git_read_hash", "governance_input_git_read_hash"):
        return GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH
    if key == "governance_hash":
        return GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH
    if key in ("repo_root", "repo_identity_hash"):
        return GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT
    if key == "head_sha":
        return GIT_CHECKPOINT_BLOCKED_MISSING_HEAD
    if key == "branch_name":
        return GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH
    if key in ("staged_paths_hash", "unstaged_paths_hash", "untracked_paths_hash"):
        return GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH
    return GIT_CHECKPOINT_BLOCKED_MALFORMED_INPUT


def _mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return dict(data)
    return None


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(value)
    return ()


def _safe_paths(value: Any) -> tuple[str, ...]:
    return tuple(sorted(set(str(item).strip() for item in _sequence(value) if isinstance(item, str) and item.strip())))


def _authority_claim_present(mapping: Mapping[str, Any]) -> bool:
    return any(mapping.get(field_name) is True for field_name in _AUTHORITY_CLAIM_FIELDS)


def _hash_like(value: str | None, allow_sha1: bool = False) -> bool:
    if value is None:
        return False
    lengths = (40, 64) if allow_sha1 else (64,)
    return len(value) in lengths and all(char in _HEX for char in value.lower())


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
