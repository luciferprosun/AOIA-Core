from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from runtime.git_ops.git_checkpoint import GIT_CHECKPOINT_KIND, GIT_CHECKPOINT_SCHEMA_VERSION
from runtime.git_ops.git_write_preview import GIT_WRITE_PREVIEW_KIND, GIT_WRITE_PREVIEW_SCHEMA_VERSION, GitWriteIntent


GIT_COMMIT_PREVIEW_KIND = "AOIA_GIT_COMMIT_PREVIEW"
GIT_COMMIT_PREVIEW_SCHEMA_VERSION = "1A"
GIT_COMMIT_PREVIEW_VALID = "VALID"
GIT_COMMIT_PREVIEW_INVALID = "INVALID"
GIT_COMMIT_PREVIEW_BLOCKED = "BLOCKED"
GIT_COMMIT_PREVIEW_CREATED = "CREATED"

GIT_COMMIT_PREVIEW_PASS = "PASS"
GIT_COMMIT_PREVIEW_NEEDS_REVIEW = "NEEDS_REVIEW"
GIT_COMMIT_PREVIEW_BLOCK = "BLOCK"

GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW"
GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW_HASH = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW_HASH"
GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_INVALID = "GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_INVALID"
GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_KIND = "GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_KIND"
GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_SCHEMA = "GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_SCHEMA"
GIT_COMMIT_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND = "GIT_COMMIT_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND"
GIT_COMMIT_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT = "GIT_COMMIT_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT"
GIT_COMMIT_PREVIEW_BLOCKED_MISSING_CHECKPOINT = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_CHECKPOINT"
GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_INVALID = "GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_INVALID"
GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_HASH_MISMATCH = "GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_HASH_MISMATCH"
GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_BLOCK = "GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_BLOCK"
GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_REVIEW = "GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_REVIEW"
GIT_COMMIT_PREVIEW_BLOCKED_MISSING_PARENT_HEAD = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_PARENT_HEAD"
GIT_COMMIT_PREVIEW_BLOCKED_MISSING_BRANCH = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_BRANCH"
GIT_COMMIT_PREVIEW_BLOCKED_DETACHED_HEAD = "GIT_COMMIT_PREVIEW_BLOCKED_DETACHED_HEAD"
GIT_COMMIT_PREVIEW_BLOCKED_MISSING_TARGET_PATHS = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_TARGET_PATHS"
GIT_COMMIT_PREVIEW_BLOCKED_TARGET_PATH_HASH_MISMATCH = "GIT_COMMIT_PREVIEW_BLOCKED_TARGET_PATH_HASH_MISMATCH"
GIT_COMMIT_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH = "GIT_COMMIT_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH"
GIT_COMMIT_PREVIEW_BLOCKED_TRAVERSAL_PATH = "GIT_COMMIT_PREVIEW_BLOCKED_TRAVERSAL_PATH"
GIT_COMMIT_PREVIEW_BLOCKED_PATHSPEC_MAGIC = "GIT_COMMIT_PREVIEW_BLOCKED_PATHSPEC_MAGIC"
GIT_COMMIT_PREVIEW_BLOCKED_OPTION_LIKE_PATH = "GIT_COMMIT_PREVIEW_BLOCKED_OPTION_LIKE_PATH"
GIT_COMMIT_PREVIEW_BLOCKED_ABSOLUTE_PATH = "GIT_COMMIT_PREVIEW_BLOCKED_ABSOLUTE_PATH"
GIT_COMMIT_PREVIEW_BLOCKED_GIT_INTERNAL_PATH = "GIT_COMMIT_PREVIEW_BLOCKED_GIT_INTERNAL_PATH"
GIT_COMMIT_PREVIEW_BLOCKED_PROTECTED_PATH = "GIT_COMMIT_PREVIEW_BLOCKED_PROTECTED_PATH"
GIT_COMMIT_PREVIEW_BLOCKED_MISSING_MESSAGE = "GIT_COMMIT_PREVIEW_BLOCKED_MISSING_MESSAGE"
GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_FIRST_LINE_LENGTH = "GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_FIRST_LINE_LENGTH"
GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_BODY_LENGTH = "GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_BODY_LENGTH"
GIT_COMMIT_PREVIEW_BLOCKED_CONTROL_CHARACTER = "GIT_COMMIT_PREVIEW_BLOCKED_CONTROL_CHARACTER"
GIT_COMMIT_PREVIEW_BLOCKED_ANSI_ESCAPE = "GIT_COMMIT_PREVIEW_BLOCKED_ANSI_ESCAPE"
GIT_COMMIT_PREVIEW_BLOCKED_CREDENTIAL_URL = "GIT_COMMIT_PREVIEW_BLOCKED_CREDENTIAL_URL"
GIT_COMMIT_PREVIEW_BLOCKED_GITHUB_TOKEN = "GIT_COMMIT_PREVIEW_BLOCKED_GITHUB_TOKEN"
GIT_COMMIT_PREVIEW_BLOCKED_TOKEN_FIELD = "GIT_COMMIT_PREVIEW_BLOCKED_TOKEN_FIELD"
GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_LANGUAGE = "GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_LANGUAGE"
GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER = "GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER"
GIT_COMMIT_PREVIEW_BLOCKED_SKIP_CI = "GIT_COMMIT_PREVIEW_BLOCKED_SKIP_CI"
GIT_COMMIT_PREVIEW_BLOCKED_RAW_COMMAND_TEXT = "GIT_COMMIT_PREVIEW_BLOCKED_RAW_COMMAND_TEXT"
GIT_COMMIT_PREVIEW_BLOCKED_SHELL_TEXT = "GIT_COMMIT_PREVIEW_BLOCKED_SHELL_TEXT"
GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM = "GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM"
GIT_COMMIT_PREVIEW_BLOCKED_HASH_MISMATCH = "GIT_COMMIT_PREVIEW_BLOCKED_HASH_MISMATCH"
GIT_COMMIT_PREVIEW_BLOCKED_REPLAY_MISMATCH = "GIT_COMMIT_PREVIEW_BLOCKED_REPLAY_MISMATCH"
GIT_COMMIT_PREVIEW_VALID_EVIDENCE_ONLY = "GIT_COMMIT_PREVIEW_VALID_EVIDENCE_ONLY"

_DEFAULT_PROTECTED_PATH_PREFIXES = (
    "runtime/safety/",
    "runtime/control_write.py",
    "runtime/human_decision_gated_artifact_write.py",
    "runtime/patches/controlled_patch_apply.py",
    "runtime/git_ops/",
    "tests/test_static_capability_boundary_1a.py",
)
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


@dataclass(frozen=True)
class GitCommitPreviewPolicy:
    policy_name: str = "AOIA_GIT_COMMIT_PREVIEW"
    policy_version: str = "1A"
    allow_review_previews: bool = False
    block_detached_head: bool = True
    require_relative_paths: bool = True
    allow_protected_paths: bool = False
    first_line_max_length: int = 72
    body_max_length: int = 4096
    allow_tab: bool = True
    allow_signed_off_by: bool = False
    allow_reviewed_by: bool = False
    allow_skip_ci: bool = False
    protected_path_prefixes: tuple[str, ...] = _DEFAULT_PROTECTED_PATH_PREFIXES

    def __post_init__(self) -> None:
        object.__setattr__(self, "protected_path_prefixes", tuple(sorted(set(self.protected_path_prefixes))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "allow_review_previews": self.allow_review_previews,
            "block_detached_head": self.block_detached_head,
            "require_relative_paths": self.require_relative_paths,
            "allow_protected_paths": self.allow_protected_paths,
            "first_line_max_length": self.first_line_max_length,
            "body_max_length": self.body_max_length,
            "allow_tab": self.allow_tab,
            "allow_signed_off_by": self.allow_signed_off_by,
            "allow_reviewed_by": self.allow_reviewed_by,
            "allow_skip_ci": self.allow_skip_ci,
            "protected_path_prefixes": self.protected_path_prefixes,
        }


@dataclass(frozen=True)
class GitCommitPreviewFinding:
    severity: str
    reason_code: str
    message: str
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "paths", tuple(sorted(set(self.paths))))

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "reason_code": self.reason_code, "message": self.message, "paths": self.paths}


@dataclass(frozen=True)
class GitCommitPreviewRequest:
    write_preview: Any
    checkpoint: Any
    commit_message: str | None
    target_paths: tuple[str, ...] | list[str] | None = None
    created_at: str = ""
    preview_nonce: str | None = None
    policy: GitCommitPreviewPolicy | None = None
    author_policy_id: str = "AOIA_COMMIT_AUTHOR_POLICY"
    author_policy_name: str = "AOIA Commit Author Policy"
    author_policy_version: str = "1A"
    author_identity_policy: Mapping[str, Any] | None = None
    committer_identity_policy: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None
    claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class GitCommitPreview:
    preview_kind: str
    schema_version: str
    commit_preview_hash: str
    write_preview_hash: str
    write_preview_kind: str
    write_preview_schema_version: str
    checkpoint_hash: str
    checkpoint_kind: str
    checkpoint_schema_version: str
    git_read_hash: str
    governance_hash: str
    governance_status: str
    repo_identity_hash: str
    repo_root: str
    parent_head_sha: str
    branch_name: str
    detached_head: bool
    clean: bool | None
    operation_kind: str
    target_paths: tuple[str, ...]
    target_paths_hash: str
    commit_message_hash: str
    normalized_commit_message_preview: str
    author_policy_id: str
    author_policy_name: str
    author_policy_version: str
    author_identity_policy: dict[str, Any]
    committer_identity_policy: dict[str, Any]
    policy_name: str
    policy_version: str
    status: str
    findings: tuple[GitCommitPreviewFinding, ...]
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
        object.__setattr__(self, "author_identity_policy", _canonical_mapping(self.author_identity_policy))
        object.__setattr__(self, "committer_identity_policy", _canonical_mapping(self.committer_identity_policy))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preview_kind": self.preview_kind,
            "schema_version": self.schema_version,
            "commit_preview_hash": self.commit_preview_hash,
            "write_preview_hash": self.write_preview_hash,
            "write_preview_kind": self.write_preview_kind,
            "write_preview_schema_version": self.write_preview_schema_version,
            "checkpoint_hash": self.checkpoint_hash,
            "checkpoint_kind": self.checkpoint_kind,
            "checkpoint_schema_version": self.checkpoint_schema_version,
            "git_read_hash": self.git_read_hash,
            "governance_hash": self.governance_hash,
            "governance_status": self.governance_status,
            "repo_identity_hash": self.repo_identity_hash,
            "repo_root": self.repo_root,
            "parent_head_sha": self.parent_head_sha,
            "branch_name": self.branch_name,
            "detached_head": self.detached_head,
            "clean": self.clean,
            "operation_kind": self.operation_kind,
            "target_paths": self.target_paths,
            "target_paths_hash": self.target_paths_hash,
            "commit_message_hash": self.commit_message_hash,
            "normalized_commit_message_preview": self.normalized_commit_message_preview,
            "author_policy_id": self.author_policy_id,
            "author_policy_name": self.author_policy_name,
            "author_policy_version": self.author_policy_version,
            "author_identity_policy": self.author_identity_policy,
            "committer_identity_policy": self.committer_identity_policy,
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
class GitCommitPreviewResult:
    status: str
    reason_codes: tuple[str, ...]
    preview: GitCommitPreview | None = None
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


def create_git_commit_preview(request: GitCommitPreviewRequest) -> GitCommitPreviewResult:
    policy = request.policy or GitCommitPreviewPolicy()
    write_preview = _mapping(request.write_preview)
    checkpoint = _mapping(request.checkpoint)
    findings = list(_write_preview_findings(write_preview))
    findings.extend(_checkpoint_findings(write_preview, checkpoint, policy))
    normalized_paths, path_findings = _target_path_findings(request.target_paths, write_preview, policy)
    findings.extend(path_findings)
    message, message_findings = _commit_message_findings(request.commit_message, policy)
    findings.extend(message_findings)
    findings.extend(_metadata_findings(request.metadata))
    if _authority_claim_present(request.claims or {}):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Commit preview request contains authority-like claims."))

    sorted_findings = _sorted_findings(findings)
    if any(finding.severity == GIT_COMMIT_PREVIEW_BLOCK for finding in sorted_findings):
        return _blocked(tuple(finding.reason_code for finding in sorted_findings))

    assert write_preview is not None
    assert checkpoint is not None
    material = _preview_material(
        write_preview=write_preview,
        checkpoint=checkpoint,
        target_paths=normalized_paths,
        commit_message=message,
        policy=policy,
        findings=sorted_findings,
        created_at=request.created_at,
        preview_nonce=request.preview_nonce,
        author_policy_id=request.author_policy_id,
        author_policy_name=request.author_policy_name,
        author_policy_version=request.author_policy_version,
        author_identity_policy=request.author_identity_policy,
        committer_identity_policy=request.committer_identity_policy,
    )
    commit_preview_hash = compute_git_commit_preview_hash(material)
    preview = GitCommitPreview(commit_preview_hash=commit_preview_hash, **material)
    if compute_git_commit_preview_hash(_preview_hash_material(preview.to_dict())) != commit_preview_hash:
        return _blocked((GIT_COMMIT_PREVIEW_BLOCKED_HASH_MISMATCH,))
    return GitCommitPreviewResult(status=GIT_COMMIT_PREVIEW_CREATED, reason_codes=(GIT_COMMIT_PREVIEW_VALID_EVIDENCE_ONLY,), preview=preview)


def verify_git_commit_preview(preview: GitCommitPreview | Mapping[str, Any] | Any, write_preview: Any, checkpoint: Any) -> GitCommitPreviewResult:
    preview_mapping = _mapping(preview)
    write_preview_mapping = _mapping(write_preview)
    checkpoint_mapping = _mapping(checkpoint)
    if preview_mapping is None or write_preview_mapping is None or checkpoint_mapping is None:
        return _invalid((GIT_COMMIT_PREVIEW_BLOCKED_REPLAY_MISMATCH,))

    reasons: list[str] = []
    if preview_mapping.get("preview_kind") != GIT_COMMIT_PREVIEW_KIND:
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_KIND)
    if preview_mapping.get("schema_version") != GIT_COMMIT_PREVIEW_SCHEMA_VERSION:
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_SCHEMA)
    if _authority_claim_present(preview_mapping) or _authority_claim_present(write_preview_mapping) or _authority_claim_present(checkpoint_mapping):
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM)
    bound_hash = _text(preview_mapping.get("commit_preview_hash"))
    if not _hash_like(bound_hash) or compute_git_commit_preview_hash(_preview_hash_material(preview_mapping)) != bound_hash:
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_HASH_MISMATCH)
    expected = _expected_bindings(write_preview_mapping, checkpoint_mapping)
    for key, value in expected.items():
        if preview_mapping.get(key) != value:
            reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    paths = _safe_paths(preview_mapping.get("target_paths"))
    if preview_mapping.get("target_paths_hash") != compute_git_commit_preview_hash(paths):
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_TARGET_PATH_HASH_MISMATCH)
    if preview_mapping.get("target_paths_hash") != write_preview_mapping.get("target_paths_hash"):
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    message = _text(preview_mapping.get("normalized_commit_message_preview")) or ""
    if preview_mapping.get("commit_message_hash") != compute_commit_message_hash(message):
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_HASH_MISMATCH)
    if preview_mapping.get("operation_kind") != GitWriteIntent.LOCAL_COMMIT_INTENT.value:
        reasons.append(GIT_COMMIT_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND)
    if reasons:
        return _invalid(tuple(reasons))
    return GitCommitPreviewResult(status=GIT_COMMIT_PREVIEW_VALID, reason_codes=(GIT_COMMIT_PREVIEW_VALID_EVIDENCE_ONLY,), preview=GitCommitPreview(**preview_mapping))


def canonical_git_commit_preview_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_git_commit_preview_hash(value: Any) -> str:
    return hashlib.sha256(canonical_git_commit_preview_json(value).encode("utf-8")).hexdigest()


def sanitize_commit_message_for_preview(message: str | None) -> str:
    if not isinstance(message, str):
        return ""
    return message.replace("\r\n", "\n").replace("\r", "\n").strip()


def compute_commit_message_hash(message: str | None) -> str:
    return compute_git_commit_preview_hash(sanitize_commit_message_for_preview(message))


def _write_preview_findings(write_preview: dict[str, Any] | None) -> tuple[GitCommitPreviewFinding, ...]:
    if write_preview is None:
        return (_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW, "Git write preview evidence is missing."),)
    findings: list[GitCommitPreviewFinding] = []
    if not _hash_like(_text(write_preview.get("preview_hash"))):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW_HASH, "Git write preview hash is missing."))
    elif compute_git_commit_preview_hash(_write_preview_hash_material(write_preview)) != write_preview.get("preview_hash"):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_INVALID, "Git write preview hash does not match preview content."))
    if write_preview.get("preview_kind") != GIT_WRITE_PREVIEW_KIND:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_KIND, "Git write preview kind is unexpected."))
    if write_preview.get("schema_version") != GIT_WRITE_PREVIEW_SCHEMA_VERSION:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_SCHEMA, "Git write preview schema is unexpected."))
    operation_kind = _text(write_preview.get("operation_kind"))
    if operation_kind in (GitWriteIntent.LOCAL_PUSH_INTENT.value, GitWriteIntent.GITHUB_WRITE_INTENT.value):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT, "Push and GitHub intents are unsupported in Step 31."))
    elif operation_kind != GitWriteIntent.LOCAL_COMMIT_INTENT.value:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND, "Commit preview requires LOCAL_COMMIT_INTENT."))
    if _authority_claim_present(write_preview):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Git write preview contains authority-like claims."))
    return tuple(findings)


def _checkpoint_findings(write_preview: dict[str, Any] | None, checkpoint: dict[str, Any] | None, policy: GitCommitPreviewPolicy) -> tuple[GitCommitPreviewFinding, ...]:
    if checkpoint is None:
        return (_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_CHECKPOINT, "Checkpoint evidence is missing."),)
    findings: list[GitCommitPreviewFinding] = []
    if compute_git_commit_preview_hash(_checkpoint_hash_material(checkpoint)) != checkpoint.get("checkpoint_hash"):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_INVALID, "Checkpoint hash does not match checkpoint content."))
    if write_preview is not None and write_preview.get("checkpoint_hash") != checkpoint.get("checkpoint_hash"):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_HASH_MISMATCH, "Git write preview checkpoint binding does not match supplied checkpoint."))
    if checkpoint.get("checkpoint_kind") != GIT_CHECKPOINT_KIND or checkpoint.get("schema_version") != GIT_CHECKPOINT_SCHEMA_VERSION:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_INVALID, "Checkpoint kind or schema is unexpected."))
    if _authority_claim_present(checkpoint):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Checkpoint contains authority-like claims."))
    if checkpoint.get("governance_status") == "BLOCK":
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_BLOCK, "Blocked governance checkpoint cannot create commit preview."))
    elif checkpoint.get("governance_status") == "NEEDS_REVIEW" and not policy.allow_review_previews:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_REVIEW, "Review governance checkpoint requires explicit commit preview policy."))
    if not _text(checkpoint.get("head_sha")):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_PARENT_HEAD, "Parent HEAD SHA is missing."))
    if not _text(checkpoint.get("branch_name")):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_BRANCH, "Branch name is missing."))
    if checkpoint.get("detached_head") is True and policy.block_detached_head:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_DETACHED_HEAD, "Detached HEAD is blocked by default."))
    return tuple(findings)


def _target_path_findings(value: Any, write_preview: dict[str, Any] | None, policy: GitCommitPreviewPolicy) -> tuple[tuple[str, ...], tuple[GitCommitPreviewFinding, ...]]:
    raw_value = value if value is not None else (write_preview or {}).get("target_paths")
    raw_paths = tuple(str(item).strip() for item in _sequence(raw_value) if isinstance(item, str) and item.strip())
    if not raw_paths:
        return (), (_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_TARGET_PATHS, "Target paths are required."),)
    normalized = tuple(_normalize_path(path) for path in raw_paths)
    findings: list[GitCommitPreviewFinding] = []
    if len(set(normalized)) != len(normalized):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH, "Duplicate target paths are not allowed."))
    for path in normalized:
        parts = PurePosixPath(path).parts
        if "\x00" in path or "\\" in path or any(part == ".." for part in parts):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_TRAVERSAL_PATH, "Target path contains traversal markers.", (path,)))
        if any(marker in path for marker in (":(glob)", ":(attr)", ":(top)", ":/")):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_PATHSPEC_MAGIC, "Target path contains Git pathspec magic.", (path,)))
        if path.startswith("-"):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_OPTION_LIKE_PATH, "Target path looks like an option.", (path,)))
        if policy.require_relative_paths and path.startswith("/"):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_ABSOLUTE_PATH, "Absolute target paths are blocked.", (path,)))
        if path == ".git" or path.startswith(".git/"):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_GIT_INTERNAL_PATH, "Git internal paths are blocked.", (path,)))
        if not policy.allow_protected_paths and _matches_prefix(path, policy.protected_path_prefixes):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_PROTECTED_PATH, "Protected paths are blocked by default.", (path,)))
    normalized_paths = tuple(sorted(set(normalized)))
    if write_preview is not None and write_preview.get("target_paths_hash") != compute_git_commit_preview_hash(normalized_paths):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_TARGET_PATH_HASH_MISMATCH, "Target paths do not match Git write preview binding."))
    return normalized_paths, tuple(findings)


def _commit_message_findings(message: str | None, policy: GitCommitPreviewPolicy) -> tuple[str, tuple[GitCommitPreviewFinding, ...]]:
    normalized = sanitize_commit_message_for_preview(message)
    if not normalized:
        return "", (_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_MESSAGE, "Commit message is required."),)
    findings: list[GitCommitPreviewFinding] = []
    first_line = normalized.split("\n", 1)[0]
    body = normalized[len(first_line) :]
    if len(first_line) > policy.first_line_max_length:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_FIRST_LINE_LENGTH, "Commit message first line is too long."))
    if len(body) > policy.body_max_length:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_BODY_LENGTH, "Commit message body is too long."))
    if "\x1b[" in normalized:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_ANSI_ESCAPE, "ANSI escape sequences are blocked."))
    for char in normalized:
        codepoint = ord(char)
        if codepoint == 0 or (codepoint < 32 and char not in ("\n", "\t" if policy.allow_tab else "")):
            findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_CONTROL_CHARACTER, "Control characters are blocked."))
            break
    lower = normalized.lower()
    if "://" in lower and "@" in lower:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_CREDENTIAL_URL, "Credential-like URLs are blocked."))
    if "ghp_" in normalized or "github_pat_" in normalized:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_GITHUB_TOKEN, "GitHub-token-like text is blocked."))
    if "token=" in lower or "access_token=" in lower:
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_TOKEN_FIELD, "Token fields are blocked."))
    authority_terms = ("approved by ai", "approved by model", "human approved", "authority granted", "auto-approved", "can commit", "can push")
    if any(term in lower for term in authority_terms):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_LANGUAGE, "Authority-like commit message language is blocked."))
    trailer_prefixes = ("approved-by:", "authority:")
    if any(line.lower().startswith(trailer_prefixes) for line in normalized.splitlines()):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER, "Authority-like trailers are blocked."))
    if not policy.allow_reviewed_by and any(line.lower().startswith("reviewed-by:") for line in normalized.splitlines()):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER, "Reviewed-by trailers are blocked by default."))
    if not policy.allow_signed_off_by and any(line.lower().startswith("signed-off-by:") for line in normalized.splitlines()):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER, "Signed-off-by trailers are blocked by default."))
    if not policy.allow_skip_ci and ("[skip ci]" in lower or "[ci skip]" in lower):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_SKIP_CI, "CI skip markers are blocked by default."))
    return normalized, tuple(findings)


def _metadata_findings(metadata: Mapping[str, Any] | None) -> tuple[GitCommitPreviewFinding, ...]:
    mapping = dict(metadata or {})
    text = " ".join(str(value) for value in mapping.values() if isinstance(value, str))
    findings: list[GitCommitPreviewFinding] = []
    if any(key in mapping for key in ("command", "command_text", "raw_command", "argv", "raw_args")) or "git " in text.lower():
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_RAW_COMMAND_TEXT, "Raw Git command text is blocked in commit preview metadata."))
    if any(marker in text for marker in (";", "&&", "||", "|", "$(", "`", "\n")):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_SHELL_TEXT, "Shell-like command text is blocked in commit preview metadata."))
    if _authority_claim_present(mapping) or any(term in text.lower() for term in ("provider authority", "approve this", "permission to commit", "permission to push")):
        findings.append(_finding(GIT_COMMIT_PREVIEW_BLOCK, GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Authority-like metadata is blocked."))
    return tuple(findings)


def _preview_material(
    *,
    write_preview: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    target_paths: tuple[str, ...],
    commit_message: str,
    policy: GitCommitPreviewPolicy,
    findings: tuple[GitCommitPreviewFinding, ...],
    created_at: str,
    preview_nonce: str | None,
    author_policy_id: str,
    author_policy_name: str,
    author_policy_version: str,
    author_identity_policy: Mapping[str, Any] | None,
    committer_identity_policy: Mapping[str, Any] | None,
) -> dict[str, Any]:
    risk_flags = tuple(finding.reason_code for finding in findings)
    return {
        "preview_kind": GIT_COMMIT_PREVIEW_KIND,
        "schema_version": GIT_COMMIT_PREVIEW_SCHEMA_VERSION,
        **_expected_bindings(write_preview, checkpoint),
        "operation_kind": GitWriteIntent.LOCAL_COMMIT_INTENT.value,
        "target_paths": target_paths,
        "target_paths_hash": compute_git_commit_preview_hash(target_paths),
        "commit_message_hash": compute_commit_message_hash(commit_message),
        "normalized_commit_message_preview": commit_message,
        "author_policy_id": _text(author_policy_id) or "",
        "author_policy_name": _text(author_policy_name) or "",
        "author_policy_version": _text(author_policy_version) or "",
        "author_identity_policy": _canonical_mapping(author_identity_policy),
        "committer_identity_policy": _canonical_mapping(committer_identity_policy),
        "policy_name": policy.policy_name,
        "policy_version": policy.policy_version,
        "status": GIT_COMMIT_PREVIEW_NEEDS_REVIEW if findings else GIT_COMMIT_PREVIEW_PASS,
        "findings": _sorted_findings(findings),
        "risk_flags": risk_flags,
        "created_at": created_at,
        "preview_nonce": preview_nonce,
    }


def _expected_bindings(write_preview: Mapping[str, Any], checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "write_preview_hash": _text(write_preview.get("preview_hash")) or "",
        "write_preview_kind": _text(write_preview.get("preview_kind")) or "",
        "write_preview_schema_version": _text(write_preview.get("schema_version")) or "",
        "checkpoint_hash": _text(checkpoint.get("checkpoint_hash")) or "",
        "checkpoint_kind": _text(checkpoint.get("checkpoint_kind")) or "",
        "checkpoint_schema_version": _text(checkpoint.get("schema_version")) or "",
        "git_read_hash": _text(checkpoint.get("git_read_hash")) or "",
        "governance_hash": _text(checkpoint.get("governance_hash")) or "",
        "governance_status": _text(checkpoint.get("governance_status")) or "",
        "repo_identity_hash": _text(checkpoint.get("repo_identity_hash")) or "",
        "repo_root": _text(checkpoint.get("repo_root")) or "",
        "parent_head_sha": _text(checkpoint.get("head_sha")) or "",
        "branch_name": _text(checkpoint.get("branch_name")) or "",
        "detached_head": checkpoint.get("detached_head") is True,
        "clean": checkpoint.get("clean") if isinstance(checkpoint.get("clean"), bool) else None,
    }


def _write_preview_hash_material(preview: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(preview)
    material.pop("preview_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _checkpoint_hash_material(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(checkpoint)
    material.pop("checkpoint_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _preview_hash_material(preview: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(preview)
    material.pop("commit_preview_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _finding(severity: str, reason_code: str, message: str, paths: tuple[str, ...] = ()) -> GitCommitPreviewFinding:
    return GitCommitPreviewFinding(severity=severity, reason_code=reason_code, message=message, paths=paths)


def _sorted_findings(findings: tuple[GitCommitPreviewFinding, ...] | list[GitCommitPreviewFinding]) -> tuple[GitCommitPreviewFinding, ...]:
    unique = {canonical_git_commit_preview_json(finding.to_dict()): finding for finding in findings}
    return tuple(unique[key] for key in sorted(unique))


def _blocked(reason_codes: tuple[str, ...]) -> GitCommitPreviewResult:
    return GitCommitPreviewResult(status=GIT_COMMIT_PREVIEW_BLOCKED, reason_codes=reason_codes)


def _invalid(reason_codes: tuple[str, ...]) -> GitCommitPreviewResult:
    return GitCommitPreviewResult(status=GIT_COMMIT_PREVIEW_INVALID, reason_codes=reason_codes)


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


def _canonical_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _jsonable(value[key]) for key in sorted(value)}


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
