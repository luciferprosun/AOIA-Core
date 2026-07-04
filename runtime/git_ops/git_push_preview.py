from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.git_ops.git_checkpoint import GIT_CHECKPOINT_KIND, GIT_CHECKPOINT_SCHEMA_VERSION


GIT_PUSH_PREVIEW_KIND = "AOIA_GIT_PUSH_PREVIEW"
GIT_PUSH_PREVIEW_SCHEMA_VERSION = "1A"
GIT_PUSH_PREVIEW_VALID = "VALID"
GIT_PUSH_PREVIEW_INVALID = "INVALID"
GIT_PUSH_PREVIEW_BLOCKED = "BLOCKED"
GIT_PUSH_PREVIEW_CREATED = "CREATED"

GIT_PUSH_PREVIEW_PASS = "PASS"
GIT_PUSH_PREVIEW_NEEDS_REVIEW = "NEEDS_REVIEW"
GIT_PUSH_PREVIEW_BLOCK = "BLOCK"

GIT_PUSH_PREVIEW_VALID_EVIDENCE_ONLY = "GIT_PUSH_PREVIEW_VALID_EVIDENCE_ONLY"
GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT = "GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT"
GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH = "GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH"
GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_INVALID = "GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_INVALID"
GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_KIND = "GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_KIND"
GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA = "GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA"
GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_BLOCK = "GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_BLOCK"
GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_REVIEW = "GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_REVIEW"
GIT_PUSH_PREVIEW_BLOCKED_MISSING_LOCAL_HEAD = "GIT_PUSH_PREVIEW_BLOCKED_MISSING_LOCAL_HEAD"
GIT_PUSH_PREVIEW_BLOCKED_MISSING_BRANCH = "GIT_PUSH_PREVIEW_BLOCKED_MISSING_BRANCH"
GIT_PUSH_PREVIEW_BLOCKED_BRANCH_MISMATCH = "GIT_PUSH_PREVIEW_BLOCKED_BRANCH_MISMATCH"
GIT_PUSH_PREVIEW_BLOCKED_DETACHED_HEAD = "GIT_PUSH_PREVIEW_BLOCKED_DETACHED_HEAD"
GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_NAME = "GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_NAME"
GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_NAME = "GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_NAME"
GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_REF = "GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_REF"
GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_REF = "GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_REF"
GIT_PUSH_PREVIEW_BLOCKED_TAG_REF = "GIT_PUSH_PREVIEW_BLOCKED_TAG_REF"
GIT_PUSH_PREVIEW_BLOCKED_REMOTE_HEAD = "GIT_PUSH_PREVIEW_BLOCKED_REMOTE_HEAD"
GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE = "GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE"
GIT_PUSH_PREVIEW_BLOCKED_DUPLICATE_COMMIT = "GIT_PUSH_PREVIEW_BLOCKED_DUPLICATE_COMMIT"
GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM = "GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM"
GIT_PUSH_PREVIEW_BLOCKED_RAW_COMMAND_TEXT = "GIT_PUSH_PREVIEW_BLOCKED_RAW_COMMAND_TEXT"
GIT_PUSH_PREVIEW_BLOCKED_SHELL_TEXT = "GIT_PUSH_PREVIEW_BLOCKED_SHELL_TEXT"
GIT_PUSH_PREVIEW_BLOCKED_HASH_MISMATCH = "GIT_PUSH_PREVIEW_BLOCKED_HASH_MISMATCH"
GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH = "GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH"
GIT_PUSH_PREVIEW_REVIEW_NO_REMOTE_HEAD = "GIT_PUSH_PREVIEW_REVIEW_NO_REMOTE_HEAD"
GIT_PUSH_PREVIEW_REVIEW_REMOTE_DIVERGED = "GIT_PUSH_PREVIEW_REVIEW_REMOTE_DIVERGED"
GIT_PUSH_PREVIEW_REVIEW_NO_AHEAD_COMMITS = "GIT_PUSH_PREVIEW_REVIEW_NO_AHEAD_COMMITS"

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
_REMOTE_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_UNSAFE_REF_MARKERS = frozenset(" ^~:?*[\\")


@dataclass(frozen=True)
class GitPushPreviewPolicy:
    policy_name: str = "AOIA_GIT_PUSH_PREVIEW"
    policy_version: str = "1A"
    allow_review_previews: bool = False
    block_detached_head: bool = True
    allow_new_remote_ref: bool = True
    allow_diverged_remote: bool = False
    allow_noop_preview: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "allow_review_previews": self.allow_review_previews,
            "block_detached_head": self.block_detached_head,
            "allow_new_remote_ref": self.allow_new_remote_ref,
            "allow_diverged_remote": self.allow_diverged_remote,
            "allow_noop_preview": self.allow_noop_preview,
        }


@dataclass(frozen=True)
class GitPushPreviewFinding:
    severity: str
    reason_code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "reason_code": self.reason_code, "message": self.message}


@dataclass(frozen=True)
class GitPushPreviewRequest:
    checkpoint: Any
    remote_name: str | None
    remote_ref: str | None
    remote_head: str | None
    commits_ahead: tuple[str, ...] | list[str]
    commits_behind: tuple[str, ...] | list[str] = ()
    branch: str | None = None
    created_at: str = ""
    preview_nonce: str | None = None
    policy: GitPushPreviewPolicy | None = None
    metadata: Mapping[str, Any] | None = None
    claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class GitPushPreview:
    schema_version: str
    repo_path: str
    branch: str
    remote_name: str
    remote_ref: str
    local_head: str
    remote_head: str | None
    commits_ahead: tuple[str, ...]
    commits_behind: tuple[str, ...]
    push_would_update_remote: bool
    push_would_be_fast_forward: bool
    requires_human_barrier: bool
    preview_hash: str
    preview_kind: str
    checkpoint_hash: str
    git_read_hash: str
    governance_hash: str
    governance_status: str
    repo_identity_hash: str
    policy_name: str
    policy_version: str
    status: str
    findings: tuple[GitPushPreviewFinding, ...]
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
        object.__setattr__(self, "commits_ahead", tuple(self.commits_ahead))
        object.__setattr__(self, "commits_behind", tuple(self.commits_behind))
        object.__setattr__(self, "findings", _sorted_findings(self.findings))
        object.__setattr__(self, "risk_flags", tuple(sorted(set(self.risk_flags))))
        object.__setattr__(self, "requires_human_barrier", True)
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo_path": self.repo_path,
            "branch": self.branch,
            "remote_name": self.remote_name,
            "remote_ref": self.remote_ref,
            "local_head": self.local_head,
            "remote_head": self.remote_head,
            "commits_ahead": self.commits_ahead,
            "commits_behind": self.commits_behind,
            "push_would_update_remote": self.push_would_update_remote,
            "push_would_be_fast_forward": self.push_would_be_fast_forward,
            "requires_human_barrier": self.requires_human_barrier,
            "preview_hash": self.preview_hash,
            "preview_kind": self.preview_kind,
            "checkpoint_hash": self.checkpoint_hash,
            "git_read_hash": self.git_read_hash,
            "governance_hash": self.governance_hash,
            "governance_status": self.governance_status,
            "repo_identity_hash": self.repo_identity_hash,
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
class GitPushPreviewResult:
    status: str
    reason_codes: tuple[str, ...]
    preview: GitPushPreview | None = None
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


def create_git_push_preview(request: GitPushPreviewRequest) -> GitPushPreviewResult:
    policy = request.policy or GitPushPreviewPolicy()
    checkpoint = _mapping(request.checkpoint)
    findings = list(_checkpoint_findings(checkpoint, policy))
    branch = _branch_value(request.branch, checkpoint)
    findings.extend(_branch_findings(branch, request.branch, checkpoint, policy))
    remote_name, remote_name_findings = _remote_name_findings(request.remote_name)
    remote_ref, remote_ref_findings = _remote_ref_findings(request.remote_ref)
    remote_head, remote_head_findings = _remote_head_findings(request.remote_head)
    commits_ahead, ahead_findings = _commit_sequence_findings(request.commits_ahead)
    commits_behind, behind_findings = _commit_sequence_findings(request.commits_behind)
    findings.extend(remote_name_findings)
    findings.extend(remote_ref_findings)
    findings.extend(remote_head_findings)
    findings.extend(ahead_findings)
    findings.extend(behind_findings)
    findings.extend(_relationship_findings(remote_head, commits_ahead, commits_behind, policy))
    findings.extend(_metadata_findings(request.metadata))
    if _authority_claim_present(request.claims or {}):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Preview request contains authority-like claims."))

    sorted_findings = _sorted_findings(findings)
    if any(finding.severity == GIT_PUSH_PREVIEW_BLOCK for finding in sorted_findings):
        return _blocked(tuple(finding.reason_code for finding in sorted_findings))

    assert checkpoint is not None
    assert branch is not None
    assert remote_name is not None
    assert remote_ref is not None
    material = _preview_material(
        checkpoint=checkpoint,
        branch=branch,
        remote_name=remote_name,
        remote_ref=remote_ref,
        remote_head=remote_head,
        commits_ahead=commits_ahead,
        commits_behind=commits_behind,
        policy=policy,
        findings=sorted_findings,
        created_at=request.created_at,
        preview_nonce=request.preview_nonce,
    )
    preview_hash = compute_git_push_preview_hash(material)
    preview = GitPushPreview(preview_hash=preview_hash, **material)
    if compute_git_push_preview_hash(_preview_hash_material(preview.to_dict())) != preview_hash:
        return _blocked((GIT_PUSH_PREVIEW_BLOCKED_HASH_MISMATCH,))
    return GitPushPreviewResult(status=GIT_PUSH_PREVIEW_CREATED, reason_codes=(GIT_PUSH_PREVIEW_VALID_EVIDENCE_ONLY,), preview=preview)


def verify_git_push_preview(preview: GitPushPreview | Mapping[str, Any] | Any, checkpoint: Any) -> GitPushPreviewResult:
    preview_mapping = _mapping(preview)
    checkpoint_mapping = _mapping(checkpoint)
    if preview_mapping is None or checkpoint_mapping is None:
        return _invalid((GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT,))

    reasons: list[str] = []
    if preview_mapping.get("preview_kind") != GIT_PUSH_PREVIEW_KIND:
        reasons.append(GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    if preview_mapping.get("schema_version") != GIT_PUSH_PREVIEW_SCHEMA_VERSION:
        reasons.append(GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    if _authority_claim_present(preview_mapping) or _authority_claim_present(checkpoint_mapping):
        reasons.append(GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM)
    bound_hash = _text(preview_mapping.get("preview_hash"))
    if not _hash_like(bound_hash) or compute_git_push_preview_hash(_preview_hash_material(preview_mapping)) != bound_hash:
        reasons.append(GIT_PUSH_PREVIEW_BLOCKED_HASH_MISMATCH)
    expected = _expected_bindings(checkpoint_mapping)
    for key, value in expected.items():
        if preview_mapping.get(key) != value:
            reasons.append(GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    if not _sequence_hashes_ok(preview_mapping.get("commits_ahead")) or not _sequence_hashes_ok(preview_mapping.get("commits_behind")):
        reasons.append(GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE)
    if preview_mapping.get("requires_human_barrier") is not True:
        reasons.append(GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH)
    if reasons:
        return _invalid(tuple(reasons))
    return GitPushPreviewResult(status=GIT_PUSH_PREVIEW_VALID, reason_codes=(GIT_PUSH_PREVIEW_VALID_EVIDENCE_ONLY,), preview=GitPushPreview(**preview_mapping))


def canonical_git_push_preview_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_git_push_preview_hash(value: Any) -> str:
    return hashlib.sha256(canonical_git_push_preview_json(value).encode("utf-8")).hexdigest()


def _checkpoint_findings(checkpoint: dict[str, Any] | None, policy: GitPushPreviewPolicy) -> tuple[GitPushPreviewFinding, ...]:
    if checkpoint is None:
        return (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT, "Checkpoint evidence is missing."),)
    findings: list[GitPushPreviewFinding] = []
    if not _hash_like(_text(checkpoint.get("checkpoint_hash"))):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH, "Checkpoint hash is missing."))
    elif compute_git_push_preview_hash(_checkpoint_hash_material(checkpoint)) != checkpoint.get("checkpoint_hash"):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_INVALID, "Checkpoint hash does not match checkpoint content."))
    if checkpoint.get("checkpoint_kind") != GIT_CHECKPOINT_KIND:
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_KIND, "Checkpoint kind is unexpected."))
    if checkpoint.get("schema_version") != GIT_CHECKPOINT_SCHEMA_VERSION:
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA, "Checkpoint schema is unexpected."))
    if checkpoint.get("governance_status") == "BLOCK":
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_BLOCK, "Blocked governance checkpoint cannot create push preview."))
    elif checkpoint.get("governance_status") == "NEEDS_REVIEW" and not policy.allow_review_previews:
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_REVIEW, "Review governance checkpoint requires explicit push preview policy."))
    if not _hash_like(_text(checkpoint.get("head_sha")), allow_sha1=True):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_LOCAL_HEAD, "Local HEAD evidence is missing."))
    if not _text(checkpoint.get("branch_name")):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_BRANCH, "Branch evidence is missing."))
    if checkpoint.get("detached_head") is True and policy.block_detached_head:
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_DETACHED_HEAD, "Detached HEAD is blocked by default."))
    if _authority_claim_present(checkpoint):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Checkpoint contains authority-like claims."))
    return tuple(findings)


def _branch_value(branch: str | None, checkpoint: dict[str, Any] | None) -> str | None:
    return _text(branch) or (_text((checkpoint or {}).get("branch_name")))


def _branch_findings(branch: str | None, requested_branch: str | None, checkpoint: dict[str, Any] | None, policy: GitPushPreviewPolicy) -> tuple[GitPushPreviewFinding, ...]:
    del policy
    checkpoint_branch = _text((checkpoint or {}).get("branch_name"))
    if branch is None:
        return (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_BRANCH, "Branch is required."),)
    if requested_branch is not None and checkpoint_branch is not None and branch != checkpoint_branch:
        return (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_BRANCH_MISMATCH, "Requested branch does not match checkpoint branch."),)
    return ()


def _remote_name_findings(value: str | None) -> tuple[str | None, tuple[GitPushPreviewFinding, ...]]:
    text = _text(value)
    if text is None:
        return None, (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_NAME, "Remote name is required."),)
    if text.startswith("-") or "/" in text or any(char not in _REMOTE_NAME_CHARS for char in text):
        return text, (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_NAME, "Remote name is unsafe."),)
    return text, ()


def _remote_ref_findings(value: str | None) -> tuple[str | None, tuple[GitPushPreviewFinding, ...]]:
    text = _text(value)
    if text is None:
        return None, (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_REF, "Remote ref is required."),)
    if text.startswith("refs/tags/"):
        return text, (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_TAG_REF, "Tag refs are outside Step 34 push preview."),)
    parts = tuple(part for part in text.split("/") if part)
    unsafe = (
        text.startswith("-")
        or text.startswith("/")
        or text.endswith("/")
        or "//" in text
        or ".." in parts
        or any(char in _UNSAFE_REF_MARKERS for char in text)
        or any(part in (".", "..") for part in parts)
    )
    if unsafe:
        return text, (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_REF, "Remote ref is unsafe."),)
    return text, ()


def _remote_head_findings(value: str | None) -> tuple[str | None, tuple[GitPushPreviewFinding, ...]]:
    text = _text(value)
    if text is None:
        return None, ()
    if not _hash_like(text, allow_sha1=True):
        return text, (_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_REMOTE_HEAD, "Remote HEAD evidence is malformed."),)
    return text.lower(), ()


def _commit_sequence_findings(value: Any) -> tuple[tuple[str, ...], tuple[GitPushPreviewFinding, ...]]:
    commits: list[str] = []
    findings: list[GitPushPreviewFinding] = []
    for item in _sequence(value):
        text = _text(item)
        if text is None:
            findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE, "Commit evidence must be SHA-1 hashes."))
        else:
            commits.append(text.lower())
    if len(set(commits)) != len(commits):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_DUPLICATE_COMMIT, "Duplicate commit evidence is not allowed."))
    if any(not _hash_like(commit, allow_sha1=True) for commit in commits):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE, "Commit evidence must be SHA-1 hashes."))
    return tuple(commits), tuple(findings)


def _relationship_findings(
    remote_head: str | None,
    commits_ahead: tuple[str, ...],
    commits_behind: tuple[str, ...],
    policy: GitPushPreviewPolicy,
) -> tuple[GitPushPreviewFinding, ...]:
    findings: list[GitPushPreviewFinding] = []
    if remote_head is None and not policy.allow_new_remote_ref:
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_REVIEW_NO_REMOTE_HEAD, "Remote HEAD is missing and new remote refs are disabled."))
    elif remote_head is None:
        findings.append(_finding(GIT_PUSH_PREVIEW_NEEDS_REVIEW, GIT_PUSH_PREVIEW_REVIEW_NO_REMOTE_HEAD, "Remote HEAD is missing; preview treats this as new remote-ref evidence."))
    if commits_behind and not policy.allow_diverged_remote:
        findings.append(_finding(GIT_PUSH_PREVIEW_NEEDS_REVIEW, GIT_PUSH_PREVIEW_REVIEW_REMOTE_DIVERGED, "Remote contains commits not present locally."))
    if not commits_ahead and not policy.allow_noop_preview:
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_REVIEW_NO_AHEAD_COMMITS, "No ahead commits are available for preview."))
    elif not commits_ahead:
        findings.append(_finding(GIT_PUSH_PREVIEW_NEEDS_REVIEW, GIT_PUSH_PREVIEW_REVIEW_NO_AHEAD_COMMITS, "No ahead commits are available for preview."))
    return tuple(findings)


def _metadata_findings(metadata: Mapping[str, Any] | None) -> tuple[GitPushPreviewFinding, ...]:
    mapping = dict(metadata or {})
    text = " ".join(str(value) for value in mapping.values() if isinstance(value, str))
    findings: list[GitPushPreviewFinding] = []
    if any(key in mapping for key in ("command", "command_text", "raw_command", "argv", "raw_args")) or "git " in text.lower():
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_RAW_COMMAND_TEXT, "Raw command text is blocked in push preview metadata."))
    if any(marker in text for marker in (";", "&&", "||", "|", "$(", "`", "\n")):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_SHELL_TEXT, "Shell-like text is blocked in push preview metadata."))
    if _authority_claim_present(mapping) or any(term in text.lower() for term in ("provider authority", "approve this", "permission to push", "authority granted")):
        findings.append(_finding(GIT_PUSH_PREVIEW_BLOCK, GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM, "Authority-like metadata is blocked."))
    return tuple(findings)


def _preview_material(
    *,
    checkpoint: Mapping[str, Any],
    branch: str,
    remote_name: str,
    remote_ref: str,
    remote_head: str | None,
    commits_ahead: tuple[str, ...],
    commits_behind: tuple[str, ...],
    policy: GitPushPreviewPolicy,
    findings: tuple[GitPushPreviewFinding, ...],
    created_at: str,
    preview_nonce: str | None,
) -> dict[str, Any]:
    risk_flags = tuple(finding.reason_code for finding in findings)
    push_would_update_remote = bool(commits_ahead)
    push_would_be_fast_forward = remote_head is not None and push_would_update_remote and not commits_behind
    return {
        "schema_version": GIT_PUSH_PREVIEW_SCHEMA_VERSION,
        "repo_path": _text(checkpoint.get("repo_root")) or "",
        "branch": branch,
        "remote_name": remote_name,
        "remote_ref": remote_ref,
        "local_head": _text(checkpoint.get("head_sha")) or "",
        "remote_head": remote_head,
        "commits_ahead": commits_ahead,
        "commits_behind": commits_behind,
        "push_would_update_remote": push_would_update_remote,
        "push_would_be_fast_forward": push_would_be_fast_forward,
        "requires_human_barrier": True,
        "preview_kind": GIT_PUSH_PREVIEW_KIND,
        **_expected_bindings(checkpoint),
        "policy_name": policy.policy_name,
        "policy_version": policy.policy_version,
        "status": GIT_PUSH_PREVIEW_NEEDS_REVIEW if findings else GIT_PUSH_PREVIEW_PASS,
        "findings": _sorted_findings(findings),
        "risk_flags": risk_flags,
        "created_at": created_at,
        "preview_nonce": preview_nonce,
    }


def _expected_bindings(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_hash": _text(checkpoint.get("checkpoint_hash")) or "",
        "git_read_hash": _text(checkpoint.get("git_read_hash")) or "",
        "governance_hash": _text(checkpoint.get("governance_hash")) or "",
        "governance_status": _text(checkpoint.get("governance_status")) or "",
        "repo_identity_hash": _text(checkpoint.get("repo_identity_hash")) or "",
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


def _finding(severity: str, reason_code: str, message: str) -> GitPushPreviewFinding:
    return GitPushPreviewFinding(severity=severity, reason_code=reason_code, message=message)


def _sorted_findings(findings: tuple[GitPushPreviewFinding, ...] | list[GitPushPreviewFinding]) -> tuple[GitPushPreviewFinding, ...]:
    unique = {canonical_git_push_preview_json(finding.to_dict()): finding for finding in findings}
    return tuple(unique[key] for key in sorted(unique))


def _blocked(reason_codes: tuple[str, ...]) -> GitPushPreviewResult:
    return GitPushPreviewResult(status=GIT_PUSH_PREVIEW_BLOCKED, reason_codes=reason_codes)


def _invalid(reason_codes: tuple[str, ...]) -> GitPushPreviewResult:
    return GitPushPreviewResult(status=GIT_PUSH_PREVIEW_INVALID, reason_codes=reason_codes)


def _sequence_hashes_ok(value: Any) -> bool:
    return all(_hash_like(item, allow_sha1=True) for item in _sequence(value))


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


def _hash_like(value: str | None, *, allow_sha1: bool = False) -> bool:
    lengths = (40, 64) if allow_sha1 else (64,)
    return isinstance(value, str) and len(value) in lengths and all(char in _HEX for char in value.lower())


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
