from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping

from runtime.git_ops.git_checkpoint import GIT_CHECKPOINT_KIND, GIT_CHECKPOINT_SCHEMA_VERSION


GIT_WRITE_PREVIEW_KIND = "AOIA_GIT_WRITE_PREVIEW"
GIT_WRITE_PREVIEW_SCHEMA_VERSION = "1A"
GIT_WRITE_PREVIEW_VALID = "VALID"
GIT_WRITE_PREVIEW_INVALID = "INVALID"
GIT_WRITE_PREVIEW_BLOCKED = "BLOCKED"
GIT_WRITE_PREVIEW_CREATED = "CREATED"

GIT_WRITE_PREVIEW_PASS = "PASS"
GIT_WRITE_PREVIEW_NEEDS_REVIEW = "NEEDS_REVIEW"
GIT_WRITE_PREVIEW_BLOCK = "BLOCK"

GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT = "GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT"
GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH = "GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH"
GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_INVALID = "GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_INVALID"
GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_KIND = "GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_KIND"
GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA = "GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA"
GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM = "GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM"
GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_BLOCK = "GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_BLOCK"
GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_REVIEW = "GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_REVIEW"
GIT_WRITE_PREVIEW_BLOCKED_MISSING_OPERATION_KIND = "GIT_WRITE_PREVIEW_BLOCKED_MISSING_OPERATION_KIND"
GIT_WRITE_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND = "GIT_WRITE_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND"
GIT_WRITE_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT = "GIT_WRITE_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT"
GIT_WRITE_PREVIEW_BLOCKED_MISSING_TARGET_PATHS = "GIT_WRITE_PREVIEW_BLOCKED_MISSING_TARGET_PATHS"
GIT_WRITE_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH = "GIT_WRITE_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH"
GIT_WRITE_PREVIEW_BLOCKED_TRAVERSAL_PATH = "GIT_WRITE_PREVIEW_BLOCKED_TRAVERSAL_PATH"
GIT_WRITE_PREVIEW_BLOCKED_PATHSPEC_MAGIC = "GIT_WRITE_PREVIEW_BLOCKED_PATHSPEC_MAGIC"
GIT_WRITE_PREVIEW_BLOCKED_OPTION_LIKE_PATH = "GIT_WRITE_PREVIEW_BLOCKED_OPTION_LIKE_PATH"
GIT_WRITE_PREVIEW_BLOCKED_ABSOLUTE_PATH = "GIT_WRITE_PREVIEW_BLOCKED_ABSOLUTE_PATH"
GIT_WRITE_PREVIEW_BLOCKED_GIT_INTERNAL_PATH = "GIT_WRITE_PREVIEW_BLOCKED_GIT_INTERNAL_PATH"
GIT_WRITE_PREVIEW_BLOCKED_PROTECTED_PATH = "GIT_WRITE_PREVIEW_BLOCKED_PROTECTED_PATH"
GIT_WRITE_PREVIEW_BLOCKED_GIT_METADATA_PATH = "GIT_WRITE_PREVIEW_BLOCKED_GIT_METADATA_PATH"
GIT_WRITE_PREVIEW_BLOCKED_RAW_COMMAND_TEXT = "GIT_WRITE_PREVIEW_BLOCKED_RAW_COMMAND_TEXT"
GIT_WRITE_PREVIEW_BLOCKED_SHELL_TEXT = "GIT_WRITE_PREVIEW_BLOCKED_SHELL_TEXT"
GIT_WRITE_PREVIEW_BLOCKED_HASH_MISMATCH = "GIT_WRITE_PREVIEW_BLOCKED_HASH_MISMATCH"
GIT_WRITE_PREVIEW_BLOCKED_REPLAY_MISMATCH = "GIT_WRITE_PREVIEW_BLOCKED_REPLAY_MISMATCH"
GIT_WRITE_PREVIEW_VALID_EVIDENCE_ONLY = "GIT_WRITE_PREVIEW_VALID_EVIDENCE_ONLY"

_DEFAULT_PROTECTED_PATH_PREFIXES = (
    "runtime/safety/",
    "runtime/control_write.py",
    "runtime/human_decision_gated_artifact_write.py",
    "runtime/patches/controlled_patch_apply.py",
    "runtime/git_ops/",
    "tests/test_static_capability_boundary_1a.py",
)
_GIT_METADATA_PATHS = (".gitmodules", ".gitattributes", ".lfsconfig")
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
_AUTHORITY_CLAIM_FIELDS = (*_AUTHORITY_FIELDS, "approval_granted", "write_authority_granted", "commit_authority_granted", "push_authority_granted")
_HEX = frozenset("0123456789abcdef")


class GitWriteIntent(str, Enum):
    LOCAL_COMMIT_INTENT = "LOCAL_COMMIT_INTENT"
    LOCAL_PUSH_INTENT = "LOCAL_PUSH_INTENT"
    GITHUB_WRITE_INTENT = "GITHUB_WRITE_INTENT"


@dataclass(frozen=True)
class GitWritePreviewPolicy:
    policy_name: str = "AOIA_GIT_WRITE_PREVIEW"
    policy_version: str = "1A"
    allow_review_previews: bool = False
    require_relative_paths: bool = True
    allow_protected_paths: bool = False
    block_git_metadata_paths: bool = True
    protected_path_prefixes: tuple[str, ...] = _DEFAULT_PROTECTED_PATH_PREFIXES

    def __post_init__(self) -> None:
        object.__setattr__(self, "protected_path_prefixes", tuple(sorted(set(self.protected_path_prefixes))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "allow_review_previews": self.allow_review_previews,
            "require_relative_paths": self.require_relative_paths,
            "allow_protected_paths": self.allow_protected_paths,
            "block_git_metadata_paths": self.block_git_metadata_paths,
            "protected_path_prefixes": self.protected_path_prefixes,
        }


@dataclass(frozen=True)
class GitWritePreviewFinding:
    severity: str
    reason_code: str
    message: str
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "paths", tuple(sorted(set(self.paths))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "reason_code": self.reason_code,
            "message": self.message,
            "paths": self.paths,
        }


@dataclass(frozen=True)
class GitWritePreviewRequest:
    checkpoint: Any
    operation_kind: str | GitWriteIntent | None
    target_paths: tuple[str, ...] | list[str] | None
    target_branch: str | None = None
    created_at: str = ""
    preview_nonce: str | None = None
    policy: GitWritePreviewPolicy | None = None
    metadata: Mapping[str, Any] | None = None
    claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class GitWritePreview:
    preview_kind: str
    schema_version: str
    preview_hash: str
    checkpoint_hash: str
    checkpoint_kind: str
    checkpoint_schema_version: str
    git_read_hash: str
    governance_hash: str
    governance_status: str
    repo_identity_hash: str
    repo_root: str
    head_sha: str
    branch_name: str | None
    detached_head: bool
    clean: bool | None
    staged_paths_hash: str
    unstaged_paths_hash: str
    untracked_paths_hash: str
    operation_kind: str
    target_paths: tuple[str, ...]
    target_paths_hash: str
    target_branch: str | None
    policy_name: str
    policy_version: str
    status: str
    findings: tuple[GitWritePreviewFinding, ...]
    risk_flags: tuple[str, ...]
    created_at: str
    preview_nonce: str | None = None
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
        object.__setattr__(self, "target_paths", tuple(sorted(set(self.target_paths))))
        object.__setattr__(self, "findings", _sorted_findings(self.findings))
        object.__setattr__(self, "risk_flags", tuple(sorted(set(self.risk_flags))))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preview_kind": self.preview_kind,
            "schema_version": self.schema_version,
            "preview_hash": self.preview_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "checkpoint_kind": self.checkpoint_kind,
            "checkpoint_schema_version": self.checkpoint_schema_version,
            "git_read_hash": self.git_read_hash,
            "governance_hash": self.governance_hash,
            "governance_status": self.governance_status,
            "repo_identity_hash": self.repo_identity_hash,
            "repo_root": self.repo_root,
            "head_sha": self.head_sha,
            "branch_name": self.branch_name,
            "detached_head": self.detached_head,
            "clean": self.clean,
            "staged_paths_hash": self.staged_paths_hash,
            "unstaged_paths_hash": self.unstaged_paths_hash,
            "untracked_paths_hash": self.untracked_paths_hash,
            "operation_kind": self.operation_kind,
            "target_paths": self.target_paths,
            "target_paths_hash": self.target_paths_hash,
            "target_branch": self.target_branch,
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "status": self.status,
            "findings": tuple(finding.to_dict() for finding in self.findings),
            "risk_flags": self.risk_flags,
            "created_at": self.created_at,
            "preview_nonce": self.preview_nonce,
            **{field_name: getattr(self, field_name) for field_name in _AUTHORITY_FIELDS},
        }


@dataclass(frozen=True)
class GitWritePreviewResult:
    status: str
    reason_codes: tuple[str, ...]
    preview: GitWritePreview | None = None
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
            "preview": self.preview.to_dict() if self.preview is not None else None,
            **{field_name: getattr(self, field_name) for field_name in _AUTHORITY_FIELDS},
        }


def create_git_write_preview(request: GitWritePreviewRequest) -> GitWritePreviewResult:
    policy = request.policy or GitWritePreviewPolicy()
    checkpoint = _mapping(request.checkpoint)
    findings = list(_checkpoint_findings(checkpoint, policy))
    operation_kind = _operation_kind(request.operation_kind)
    findings.extend(_operation_findings(operation_kind))
    normalized_paths, path_findings = _target_path_findings(request.target_paths, policy)
    findings.extend(path_findings)
    findings.extend(_metadata_findings(request.metadata))
    if _authority_claim_present(request.claims or {}):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Preview request contains authority-like claims."))

    sorted_findings = _sorted_findings(findings)
    if any(finding.severity == GIT_WRITE_PREVIEW_BLOCK for finding in sorted_findings):
        return _blocked(tuple(finding.reason_code for finding in sorted_findings))

    assert checkpoint is not None
    assert operation_kind is not None
    material = _preview_material(
        checkpoint=checkpoint,
        operation_kind=operation_kind,
        target_paths=normalized_paths,
        target_branch=request.target_branch,
        policy=policy,
        findings=sorted_findings,
        created_at=request.created_at,
        preview_nonce=request.preview_nonce,
    )
    preview_hash = compute_git_write_preview_hash(material)
    preview = GitWritePreview(preview_hash=preview_hash, **material)
    if compute_git_write_preview_hash(_preview_hash_material(preview.to_dict())) != preview_hash:
        return _blocked((GIT_WRITE_PREVIEW_BLOCKED_HASH_MISMATCH,))
    return GitWritePreviewResult(status=GIT_WRITE_PREVIEW_CREATED, reason_codes=(GIT_WRITE_PREVIEW_VALID_EVIDENCE_ONLY,), preview=preview)


def verify_git_write_preview(preview: GitWritePreview | Mapping[str, Any] | Any, checkpoint: Any) -> GitWritePreviewResult:
    preview_mapping = _mapping(preview)
    checkpoint_mapping = _mapping(checkpoint)
    if preview_mapping is None or checkpoint_mapping is None:
        return _invalid((GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT,))

    reasons: list[str] = []
    if preview_mapping.get("preview_kind") != GIT_WRITE_PREVIEW_KIND:
        reasons.append(GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_KIND)
    if preview_mapping.get("schema_version") != GIT_WRITE_PREVIEW_SCHEMA_VERSION:
        reasons.append(GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA)
    if _authority_claim_present(preview_mapping) or _authority_claim_present(checkpoint_mapping):
        reasons.append(GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM)
    bound_hash = _text(preview_mapping.get("preview_hash"))
    if not _hash_like(bound_hash) or compute_git_write_preview_hash(_preview_hash_material(preview_mapping)) != bound_hash:
        reasons.append(GIT_WRITE_PREVIEW_BLOCKED_HASH_MISMATCH)
    expected = _expected_bindings(checkpoint_mapping)
    for key, value in expected.items():
        if preview_mapping.get(key) != value:
            reasons.append(GIT_WRITE_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    paths = _safe_paths(preview_mapping.get("target_paths"))
    if preview_mapping.get("target_paths_hash") != compute_git_write_preview_hash(paths):
        reasons.append(GIT_WRITE_PREVIEW_BLOCKED_HASH_MISMATCH)
    if preview_mapping.get("operation_kind") != GitWriteIntent.LOCAL_COMMIT_INTENT.value:
        reasons.append(GIT_WRITE_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND)
    if reasons:
        return _invalid(tuple(reasons))
    return GitWritePreviewResult(status=GIT_WRITE_PREVIEW_VALID, reason_codes=(GIT_WRITE_PREVIEW_VALID_EVIDENCE_ONLY,), preview=GitWritePreview(**preview_mapping))


def canonical_git_write_preview_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_git_write_preview_hash(value: Any) -> str:
    return hashlib.sha256(canonical_git_write_preview_json(value).encode("utf-8")).hexdigest()


def _checkpoint_findings(checkpoint: dict[str, Any] | None, policy: GitWritePreviewPolicy) -> tuple[GitWritePreviewFinding, ...]:
    if checkpoint is None:
        return (_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT, "Checkpoint evidence is missing."),)
    findings: list[GitWritePreviewFinding] = []
    if not _hash_like(_text(checkpoint.get("checkpoint_hash"))):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH, "Checkpoint hash is missing."))
    elif compute_git_write_preview_hash(_checkpoint_hash_material(checkpoint)) != checkpoint.get("checkpoint_hash"):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_INVALID, "Checkpoint hash does not match checkpoint content."))
    if checkpoint.get("checkpoint_kind") != GIT_CHECKPOINT_KIND:
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_KIND, "Checkpoint kind is unexpected."))
    if checkpoint.get("schema_version") != GIT_CHECKPOINT_SCHEMA_VERSION:
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA, "Checkpoint schema is unexpected."))
    if _authority_claim_present(checkpoint):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Checkpoint contains authority-like claims."))
    if checkpoint.get("governance_status") == "BLOCK":
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_BLOCK, "Blocked governance checkpoint cannot create write preview."))
    elif checkpoint.get("governance_status") == "NEEDS_REVIEW" and not policy.allow_review_previews:
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_REVIEW, "Review governance checkpoint requires explicit preview policy."))
    return tuple(findings)


def _operation_findings(operation_kind: str | None) -> tuple[GitWritePreviewFinding, ...]:
    if operation_kind is None:
        return (_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_MISSING_OPERATION_KIND, "Git write operation kind is missing."),)
    if operation_kind in (GitWriteIntent.LOCAL_PUSH_INTENT.value, GitWriteIntent.GITHUB_WRITE_INTENT.value):
        return (_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT, "Push and GitHub intents are unsupported in Step 30."),)
    if operation_kind != GitWriteIntent.LOCAL_COMMIT_INTENT.value:
        return (_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND, "Git write operation kind is unsupported."),)
    return ()


def _target_path_findings(value: Any, policy: GitWritePreviewPolicy) -> tuple[tuple[str, ...], tuple[GitWritePreviewFinding, ...]]:
    raw_paths = tuple(str(item).strip() for item in _sequence(value) if isinstance(item, str) and item.strip())
    if not raw_paths:
        return (), (_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_MISSING_TARGET_PATHS, "Target paths are required."),)
    normalized = tuple(_normalize_path(path) for path in raw_paths)
    findings: list[GitWritePreviewFinding] = []
    if len(set(normalized)) != len(normalized):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH, "Duplicate target paths are not allowed."))
    for path in normalized:
        parts = PurePosixPath(path).parts
        if "\x00" in path or "\\" in path or any(part == ".." for part in parts):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_TRAVERSAL_PATH, "Target path contains traversal markers.", (path,)))
        if any(marker in path for marker in (":(glob)", ":(attr)", ":(top)", ":/")):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_PATHSPEC_MAGIC, "Target path contains Git pathspec magic.", (path,)))
        if path.startswith("-"):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_OPTION_LIKE_PATH, "Target path looks like an option.", (path,)))
        if policy.require_relative_paths and path.startswith("/"):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_ABSOLUTE_PATH, "Absolute target paths are blocked.", (path,)))
        if path == ".git" or path.startswith(".git/"):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_GIT_INTERNAL_PATH, "Git internal paths are blocked.", (path,)))
        if not policy.allow_protected_paths and _matches_prefix(path, policy.protected_path_prefixes):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_PROTECTED_PATH, "Protected paths are blocked by default.", (path,)))
        if policy.block_git_metadata_paths and (path in _GIT_METADATA_PATHS or any(path.endswith("/" + item) for item in _GIT_METADATA_PATHS)):
            findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_GIT_METADATA_PATH, "Git metadata paths are blocked by default.", (path,)))
    return tuple(sorted(set(normalized))), tuple(findings)


def _metadata_findings(metadata: Mapping[str, Any] | None) -> tuple[GitWritePreviewFinding, ...]:
    mapping = dict(metadata or {})
    text = " ".join(str(value) for value in mapping.values() if isinstance(value, str))
    findings: list[GitWritePreviewFinding] = []
    if any(key in mapping for key in ("command", "command_text", "raw_command", "argv", "raw_args")) or "git " in text.lower():
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_RAW_COMMAND_TEXT, "Raw Git command text is blocked in write preview metadata."))
    if any(marker in text for marker in (";", "&&", "||", "|", "$(", "`", "\n")):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_SHELL_TEXT, "Shell-like command text is blocked in write preview metadata."))
    if _authority_claim_present(mapping) or any(term in text.lower() for term in ("provider authority", "approve this", "permission to commit", "permission to push")):
        findings.append(_finding(GIT_WRITE_PREVIEW_BLOCK, GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Authority-like metadata is blocked."))
    return tuple(findings)


def _preview_material(
    *,
    checkpoint: Mapping[str, Any],
    operation_kind: str,
    target_paths: tuple[str, ...],
    target_branch: str | None,
    policy: GitWritePreviewPolicy,
    findings: tuple[GitWritePreviewFinding, ...],
    created_at: str,
    preview_nonce: str | None,
) -> dict[str, Any]:
    risk_flags = tuple(finding.reason_code for finding in findings)
    return {
        "preview_kind": GIT_WRITE_PREVIEW_KIND,
        "schema_version": GIT_WRITE_PREVIEW_SCHEMA_VERSION,
        **_expected_bindings(checkpoint),
        "operation_kind": operation_kind,
        "target_paths": target_paths,
        "target_paths_hash": compute_git_write_preview_hash(target_paths),
        "target_branch": _text(target_branch),
        "policy_name": policy.policy_name,
        "policy_version": policy.policy_version,
        "status": GIT_WRITE_PREVIEW_NEEDS_REVIEW if findings else GIT_WRITE_PREVIEW_PASS,
        "findings": _sorted_findings(findings),
        "risk_flags": risk_flags,
        "created_at": created_at,
        "preview_nonce": preview_nonce,
    }


def _expected_bindings(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_hash": _text(checkpoint.get("checkpoint_hash")) or "",
        "checkpoint_kind": _text(checkpoint.get("checkpoint_kind")) or "",
        "checkpoint_schema_version": _text(checkpoint.get("schema_version")) or "",
        "git_read_hash": _text(checkpoint.get("git_read_hash")) or "",
        "governance_hash": _text(checkpoint.get("governance_hash")) or "",
        "governance_status": _text(checkpoint.get("governance_status")) or "",
        "repo_identity_hash": _text(checkpoint.get("repo_identity_hash")) or "",
        "repo_root": _text(checkpoint.get("repo_root")) or "",
        "head_sha": _text(checkpoint.get("head_sha")) or "",
        "branch_name": _text(checkpoint.get("branch_name")),
        "detached_head": checkpoint.get("detached_head") is True,
        "clean": checkpoint.get("clean") if isinstance(checkpoint.get("clean"), bool) else None,
        "staged_paths_hash": _text(checkpoint.get("staged_paths_hash")) or "",
        "unstaged_paths_hash": _text(checkpoint.get("unstaged_paths_hash")) or "",
        "untracked_paths_hash": _text(checkpoint.get("untracked_paths_hash")) or "",
    }


def _checkpoint_hash_material(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(checkpoint)
    material.pop("checkpoint_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _preview_hash_material(preview: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(preview)
    material.pop("preview_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _operation_kind(value: str | GitWriteIntent | None) -> str | None:
    if isinstance(value, GitWriteIntent):
        return value.value
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _finding(severity: str, reason_code: str, message: str, paths: tuple[str, ...] = ()) -> GitWritePreviewFinding:
    return GitWritePreviewFinding(severity=severity, reason_code=reason_code, message=message, paths=paths)


def _sorted_findings(findings: tuple[GitWritePreviewFinding, ...] | list[GitWritePreviewFinding]) -> tuple[GitWritePreviewFinding, ...]:
    unique = {canonical_git_write_preview_json(finding.to_dict()): finding for finding in findings}
    return tuple(unique[key] for key in sorted(unique))


def _blocked(reason_codes: tuple[str, ...]) -> GitWritePreviewResult:
    return GitWritePreviewResult(status=GIT_WRITE_PREVIEW_BLOCKED, reason_codes=reason_codes)


def _invalid(reason_codes: tuple[str, ...]) -> GitWritePreviewResult:
    return GitWritePreviewResult(status=GIT_WRITE_PREVIEW_INVALID, reason_codes=reason_codes)


def _normalize_path(path: str) -> str:
    return path.strip().replace("//", "/")


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _safe_paths(value: Any) -> tuple[str, ...]:
    return tuple(sorted(set(str(item).strip() for item in _sequence(value) if isinstance(item, str) and item.strip())))


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(value)
    return ()


def _mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return dict(data)
    return None


def _authority_claim_present(mapping: Mapping[str, Any]) -> bool:
    return any(mapping.get(field_name) is True for field_name in _AUTHORITY_CLAIM_FIELDS)


def _hash_like(value: str | None) -> bool:
    return value is not None and len(value) == 64 and all(char in _HEX for char in value.lower())


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
