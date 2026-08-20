from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from runtime.git_ops.git_env import build_hardened_git_env
from runtime.safety.bounded_subprocess import run_bounded_subprocess
from runtime.git_ops.git_push_barrier import (
    GIT_PUSH_BARRIER_ELIGIBLE,
    GitPushBarrierRequest,
    GitPushBarrierResult,
    evaluate_git_push_barrier,
)
from runtime.git_ops.git_push_preview import (
    GIT_PUSH_PREVIEW_KIND,
    GIT_PUSH_PREVIEW_PASS,
    GIT_PUSH_PREVIEW_SCHEMA_VERSION,
    compute_git_push_preview_hash,
)


CONTROLLED_GIT_PUSH_PUSHED = "CONTROLLED_GIT_PUSH_PUSHED"
CONTROLLED_GIT_PUSH_BLOCKED = "CONTROLLED_GIT_PUSH_BLOCKED"

CONTROLLED_GIT_PUSH_BLOCKED_MISSING_PREVIEW = "CONTROLLED_GIT_PUSH_BLOCKED_MISSING_PREVIEW"
CONTROLLED_GIT_PUSH_BLOCKED_MALFORMED_PREVIEW = "CONTROLLED_GIT_PUSH_BLOCKED_MALFORMED_PREVIEW"
CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_HASH_MISMATCH = "CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_HASH_MISMATCH"
CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_NOT_PASS = "CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_NOT_PASS"
CONTROLLED_GIT_PUSH_BLOCKED_MISSING_BARRIER = "CONTROLLED_GIT_PUSH_BLOCKED_MISSING_BARRIER"
CONTROLLED_GIT_PUSH_BLOCKED_BARRIER_INVALID = "CONTROLLED_GIT_PUSH_BLOCKED_BARRIER_INVALID"
CONTROLLED_GIT_PUSH_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_GIT_PUSH_BLOCKED_AUTHORITY_CLAIM"
CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH = "CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH"
CONTROLLED_GIT_PUSH_BLOCKED_NON_GIT_REPO = "CONTROLLED_GIT_PUSH_BLOCKED_NON_GIT_REPO"
CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH = "CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH"
CONTROLLED_GIT_PUSH_BLOCKED_HEAD_CHANGED = "CONTROLLED_GIT_PUSH_BLOCKED_HEAD_CHANGED"
CONTROLLED_GIT_PUSH_BLOCKED_BRANCH_CHANGED = "CONTROLLED_GIT_PUSH_BLOCKED_BRANCH_CHANGED"
CONTROLLED_GIT_PUSH_BLOCKED_DIRTY_WORKTREE = "CONTROLLED_GIT_PUSH_BLOCKED_DIRTY_WORKTREE"
CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_CHANGED = "CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_CHANGED"
CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_HEAD_MISSING = "CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_HEAD_MISSING"
CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_REF_MISMATCH = "CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_REF_MISMATCH"
CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_NOT_LOCAL = "CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_NOT_LOCAL"
CONTROLLED_GIT_PUSH_BLOCKED_NON_FAST_FORWARD = "CONTROLLED_GIT_PUSH_BLOCKED_NON_FAST_FORWARD"
CONTROLLED_GIT_PUSH_BLOCKED_AHEAD_BEHIND_CHANGED = "CONTROLLED_GIT_PUSH_BLOCKED_AHEAD_BEHIND_CHANGED"
CONTROLLED_GIT_PUSH_BLOCKED_PUSH_FAILED = "CONTROLLED_GIT_PUSH_BLOCKED_PUSH_FAILED"
CONTROLLED_GIT_PUSH_BLOCKED_TIMEOUT = "CONTROLLED_GIT_PUSH_BLOCKED_TIMEOUT"
CONTROLLED_GIT_PUSH_BLOCKED_FAIL_CLOSED = "CONTROLLED_GIT_PUSH_BLOCKED_FAIL_CLOSED"

_RESULT_SCHEMA_VERSION = "AOIA_CONTROLLED_GIT_PUSH_1A"
_DEFAULT_TIMEOUT_SECONDS = 15
_HEX = frozenset("0123456789abcdef")
_REMOTE_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_UNSAFE_REF_MARKERS = frozenset(" ^~:?*[\\")
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
    "approval_granted",
    "write_authority_granted",
    "commit_authority_granted",
    "push_authority_granted",
    "approved",
    "eligible",
    "eligible_for_controlled_push",
    "authority",
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


class _GitPushCommand(str, Enum):
    REV_PARSE_TOPLEVEL = "REV_PARSE_TOPLEVEL"
    REV_PARSE_HEAD = "REV_PARSE_HEAD"
    REV_PARSE_BRANCH = "REV_PARSE_BRANCH"
    STATUS_PORCELAIN = "STATUS_PORCELAIN"
    REMOTE_GET_URL = "REMOTE_GET_URL"
    REMOTE_HEAD = "REMOTE_HEAD"
    REV_LIST_LEFT_RIGHT_COUNT = "REV_LIST_LEFT_RIGHT_COUNT"
    MERGE_BASE_IS_ANCESTOR = "MERGE_BASE_IS_ANCESTOR"
    PUSH_EXACT_REF = "PUSH_EXACT_REF"


@dataclass(frozen=True)
class ControlledGitPushResult:
    status: str
    repo_path: str | None
    remote_name: str | None
    remote_ref: str | None
    branch: str | None
    local_head_before: str | None
    local_head_after: str | None
    remote_head_before: str | None
    remote_head_after: str | None
    commits_ahead_before: int | None
    commits_behind_before: int | None
    reviewed_push_preview_hash: str | None
    barrier_evidence_hash: str | None
    human_barrier_hash: str | None
    human_decision_hash: str | None
    reason_code: str
    reason: str
    result_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _RESULT_SCHEMA_VERSION,
            "status": self.status,
            "repo_path": self.repo_path,
            "remote_name": self.remote_name,
            "remote_ref": self.remote_ref,
            "branch": self.branch,
            "local_head_before": self.local_head_before,
            "local_head_after": self.local_head_after,
            "remote_head_before": self.remote_head_before,
            "remote_head_after": self.remote_head_after,
            "commits_ahead_before": self.commits_ahead_before,
            "commits_behind_before": self.commits_behind_before,
            "reviewed_push_preview_hash": self.reviewed_push_preview_hash,
            "barrier_evidence_hash": self.barrier_evidence_hash,
            "human_barrier_hash": self.human_barrier_hash,
            "human_decision_hash": self.human_decision_hash,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "result_hash": self.result_hash,
        }


@dataclass(frozen=True)
class _GitRunnerResult:
    command_id: str
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    timeout_expired: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timeout_expired


class _ControlledGitPushTimeout(RuntimeError):
    def __init__(self, command_id: str) -> None:
        self.command_id = command_id
        super().__init__(command_id)


class _ControlledGitPushRunner:
    def run(
        self,
        command_id: _GitPushCommand,
        repo_path: Path,
        *,
        remote_name: str | None = None,
        remote_ref: str | None = None,
        local_head: str | None = None,
        remote_head: str | None = None,
    ) -> _GitRunnerResult:
        if command_id is _GitPushCommand.REV_PARSE_TOPLEVEL:
            argv = ("git", "rev-parse", "--show-toplevel")
        elif command_id is _GitPushCommand.REV_PARSE_HEAD:
            argv = ("git", "rev-parse", "HEAD")
        elif command_id is _GitPushCommand.REV_PARSE_BRANCH:
            argv = ("git", "rev-parse", "--abbrev-ref", "HEAD")
        elif command_id is _GitPushCommand.STATUS_PORCELAIN:
            argv = ("git", "status", "--porcelain=v1", "--untracked-files=all")
        elif command_id is _GitPushCommand.REMOTE_GET_URL:
            if not _safe_remote_name(remote_name):
                return _GitRunnerResult(command_id.value, 2, b"", b"unsafe remote name")
            argv = ("git", "remote", "get-url", remote_name or "")
        elif command_id is _GitPushCommand.REMOTE_HEAD:
            if not _safe_remote_name(remote_name) or not _safe_remote_ref(remote_ref):
                return _GitRunnerResult(command_id.value, 2, b"", b"unsafe remote evidence")
            argv = ("git", "ls-remote", "--heads", remote_name or "", remote_ref or "")
        elif command_id is _GitPushCommand.REV_LIST_LEFT_RIGHT_COUNT:
            if not _sha_like(remote_head) or not _sha_like(local_head):
                return _GitRunnerResult(command_id.value, 2, b"", b"unsafe commit evidence")
            argv = ("git", "rev-list", "--left-right", "--count", f"{remote_head}...{local_head}")
        elif command_id is _GitPushCommand.MERGE_BASE_IS_ANCESTOR:
            if not _sha_like(remote_head) or not _sha_like(local_head):
                return _GitRunnerResult(command_id.value, 2, b"", b"unsafe commit evidence")
            argv = ("git", "merge-base", "--is-ancestor", remote_head or "", local_head or "")
        elif command_id is _GitPushCommand.PUSH_EXACT_REF:
            if not _safe_remote_name(remote_name) or not _safe_remote_ref(remote_ref) or not _sha_like(local_head):
                return _GitRunnerResult(command_id.value, 2, b"", b"unsafe push evidence")
            argv = ("git", "push", "--porcelain", remote_name or "", f"{local_head}:{remote_ref}")
        else:
            return _GitRunnerResult(command_id.value, 2, b"", b"unsupported command")

        try:
            completed = run_bounded_subprocess(
                list(argv),
                cwd=str(repo_path),
                env=build_hardened_git_env(),
                shell=False,
                capture_output=True,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            return _GitRunnerResult(command_id.value, None, _bytes(exc.stdout), _bytes(exc.stderr), timeout_expired=True)
        except (OSError, ValueError) as exc:
            return _GitRunnerResult(command_id.value, 1, b"", str(exc).encode("utf-8", errors="replace"))
        return _GitRunnerResult(command_id.value, completed.returncode, _bytes(completed.stdout), _bytes(completed.stderr))


def controlled_git_push(
    repo_path: str | Path,
    push_preview: Any,
    barrier_evidence: Any,
    *,
    workspace_root: str | Path | None = None,
    now: Any = None,
    runner: Any = None,
) -> ControlledGitPushResult:
    del now
    try:
        preview = _mapping(push_preview)
        if preview is None:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_MISSING_PREVIEW, "hash-bound push preview evidence is required")

        preview_hash = _text(preview.get("preview_hash"))
        preview_error = _preview_error(preview)
        if preview_error is not None:
            return _blocked(preview_error, "valid hash-bound push preview evidence is required", preview_hash=preview_hash)

        assert preview_hash is not None
        if barrier_evidence is None:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_MISSING_BARRIER, "hash-bound human barrier evidence is required", preview_hash=preview_hash)
        if _authority_claim_present(barrier_evidence):
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_AUTHORITY_CLAIM, "metadata authority claims cannot authorize controlled push", preview_hash=preview_hash)

        barrier = evaluate_git_push_barrier(
            GitPushBarrierRequest(
                push_preview=preview,
                human_barrier=barrier_evidence,
                expected_push_preview_hash=preview_hash,
                source_trust="USER_SUPPLIED",
            )
        )
        if barrier.status != GIT_PUSH_BARRIER_ELIGIBLE or not barrier.eligible_for_controlled_push:
            return _blocked(
                CONTROLLED_GIT_PUSH_BLOCKED_BARRIER_INVALID,
                "valid hash-bound human push barrier evidence is required",
                preview_hash=preview_hash,
                barrier=barrier,
            )

        repo, workspace, repo_error = _resolve_repo_path(repo_path, workspace_root)
        if repo_error is not None:
            return _blocked(repo_error, "repository path is outside the allowed workspace", preview_hash=preview_hash, barrier=barrier)
        assert repo is not None

        active_runner = runner or _ControlledGitPushRunner()
        toplevel = _run(active_runner, _GitPushCommand.REV_PARSE_TOPLEVEL, repo)
        if not toplevel.ok:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_NON_GIT_REPO, "repository path is not a usable git repository", repo=repo, preview_hash=preview_hash, barrier=barrier)
        resolved_toplevel = _resolved_existing_dir(_single_line(toplevel.stdout))
        if resolved_toplevel != repo:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH, "repository root differs from reviewed repository path", repo=repo, preview_hash=preview_hash, barrier=barrier)

        if _repo_root_error(preview, repo) is not None:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH, "push preview repository binding does not match the live repository", repo=repo, preview_hash=preview_hash, barrier=barrier)

        head_result = _run(active_runner, _GitPushCommand.REV_PARSE_HEAD, repo)
        if not head_result.ok:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_NON_GIT_REPO, "current repository HEAD could not be read", repo=repo, preview_hash=preview_hash, barrier=barrier)
        local_head = _single_line(head_result.stdout)
        if local_head != _text(preview.get("local_head")):
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_HEAD_CHANGED, "repository HEAD changed after push preview review", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)

        branch_result = _run(active_runner, _GitPushCommand.REV_PARSE_BRANCH, repo)
        if not branch_result.ok or _single_line(branch_result.stdout) != _text(preview.get("branch")):
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_BRANCH_CHANGED, "repository branch changed after push preview review", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)

        status_result = _run(active_runner, _GitPushCommand.STATUS_PORCELAIN, repo)
        if not status_result.ok:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_NON_GIT_REPO, "repository status could not be read", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)
        if status_result.stdout.strip():
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_DIRTY_WORKTREE, "dirty working tree blocks controlled push", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)

        remote_name = _text(preview.get("remote_name"))
        remote_ref = _text(preview.get("remote_ref"))
        if not _safe_remote_name(remote_name) or not _safe_remote_ref(remote_ref):
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_REF_MISMATCH, "reviewed remote name or ref is unsafe", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)

        remote_url_result = _run(active_runner, _GitPushCommand.REMOTE_GET_URL, repo, remote_name=remote_name)
        if not remote_url_result.ok:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_REF_MISMATCH, "reviewed remote is not configured", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)
        remote_path = _local_remote_path(_single_line(remote_url_result.stdout), repo, workspace)
        if remote_path is None:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_NOT_LOCAL, "controlled push requires a local remote path", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)

        before_remote_result = _run(active_runner, _GitPushCommand.REMOTE_HEAD, repo, remote_name=remote_name, remote_ref=remote_ref)
        before_remote_head = _remote_head_from_output(before_remote_result.stdout, remote_ref) if before_remote_result.ok else None
        if before_remote_head is None:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_HEAD_MISSING, "remote HEAD evidence is missing", repo=repo, local_head_before=local_head, preview_hash=preview_hash, barrier=barrier)
        if before_remote_head != _text(preview.get("remote_head")):
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_CHANGED, "remote HEAD changed after push preview review", repo=repo, local_head_before=local_head, remote_head_before=before_remote_head, preview_hash=preview_hash, barrier=barrier)

        count_result = _run(active_runner, _GitPushCommand.REV_LIST_LEFT_RIGHT_COUNT, repo, local_head=local_head, remote_head=before_remote_head)
        behind_count, ahead_count = _ahead_behind(count_result.stdout) if count_result.ok else (None, None)
        if behind_count is None or ahead_count is None:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_AHEAD_BEHIND_CHANGED, "ahead or behind evidence could not be rechecked", repo=repo, local_head_before=local_head, remote_head_before=before_remote_head, preview_hash=preview_hash, barrier=barrier)
        if behind_count != 0 or ahead_count != len(tuple(preview.get("commits_ahead") or ())):
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_AHEAD_BEHIND_CHANGED, "ahead or behind evidence changed after push preview review", repo=repo, local_head_before=local_head, remote_head_before=before_remote_head, commits_ahead_before=ahead_count, commits_behind_before=behind_count, preview_hash=preview_hash, barrier=barrier)

        ancestor_result = _run(active_runner, _GitPushCommand.MERGE_BASE_IS_ANCESTOR, repo, local_head=local_head, remote_head=before_remote_head)
        if not ancestor_result.ok:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_NON_FAST_FORWARD, "remote HEAD is not an ancestor of reviewed local HEAD", repo=repo, local_head_before=local_head, remote_head_before=before_remote_head, commits_ahead_before=ahead_count, commits_behind_before=behind_count, preview_hash=preview_hash, barrier=barrier)

        push_result = _run(active_runner, _GitPushCommand.PUSH_EXACT_REF, repo, remote_name=remote_name, remote_ref=remote_ref, local_head=local_head)
        if not push_result.ok:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_PUSH_FAILED, "controlled push command failed after evidence validation", repo=repo, local_head_before=local_head, remote_head_before=before_remote_head, commits_ahead_before=ahead_count, commits_behind_before=behind_count, preview_hash=preview_hash, barrier=barrier)

        after_head_result = _run(active_runner, _GitPushCommand.REV_PARSE_HEAD, repo)
        local_head_after = _single_line(after_head_result.stdout) if after_head_result.ok else None
        after_remote_result = _run(active_runner, _GitPushCommand.REMOTE_HEAD, repo, remote_name=remote_name, remote_ref=remote_ref)
        after_remote_head = _remote_head_from_output(after_remote_result.stdout, remote_ref) if after_remote_result.ok else None
        if local_head_after != local_head or after_remote_head != local_head:
            return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_FAIL_CLOSED, "post-push evidence did not match reviewed local HEAD", repo=repo, local_head_before=local_head, local_head_after=local_head_after, remote_head_before=before_remote_head, remote_head_after=after_remote_head, commits_ahead_before=ahead_count, commits_behind_before=behind_count, preview_hash=preview_hash, barrier=barrier)

        return _result(
            status=CONTROLLED_GIT_PUSH_PUSHED,
            reason_code=CONTROLLED_GIT_PUSH_PUSHED,
            reason="controlled push completed after hash-bound preview and human barrier validation",
            repo=repo,
            remote_name=remote_name,
            remote_ref=remote_ref,
            branch=_text(preview.get("branch")),
            local_head_before=local_head,
            local_head_after=local_head_after,
            remote_head_before=before_remote_head,
            remote_head_after=after_remote_head,
            commits_ahead_before=ahead_count,
            commits_behind_before=behind_count,
            preview_hash=preview_hash,
            barrier=barrier,
        )
    except _ControlledGitPushTimeout as exc:
        return _blocked(
            CONTROLLED_GIT_PUSH_BLOCKED_TIMEOUT,
            f"controlled Git process timed out during {exc.command_id}",
        )
    except Exception:
        return _blocked(CONTROLLED_GIT_PUSH_BLOCKED_FAIL_CLOSED, "controlled push failed closed")


def _preview_error(preview: Mapping[str, Any]) -> str | None:
    if _authority_claim_present(preview):
        return CONTROLLED_GIT_PUSH_BLOCKED_AUTHORITY_CLAIM
    if preview.get("preview_kind") != GIT_PUSH_PREVIEW_KIND or preview.get("schema_version") != GIT_PUSH_PREVIEW_SCHEMA_VERSION:
        return CONTROLLED_GIT_PUSH_BLOCKED_MALFORMED_PREVIEW
    if preview.get("status") != GIT_PUSH_PREVIEW_PASS:
        return CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_NOT_PASS
    if preview.get("requires_human_barrier") is not True:
        return CONTROLLED_GIT_PUSH_BLOCKED_MALFORMED_PREVIEW
    if preview.get("push_would_update_remote") is not True or preview.get("push_would_be_fast_forward") is not True:
        return CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_NOT_PASS
    if not _sha_like(_text(preview.get("local_head"))) or not _sha_like(_text(preview.get("remote_head"))):
        return CONTROLLED_GIT_PUSH_BLOCKED_MALFORMED_PREVIEW
    if tuple(preview.get("commits_behind") or ()):
        return CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_NOT_PASS
    preview_hash = _text(preview.get("preview_hash"))
    if not _sha256_like(preview_hash):
        return CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_HASH_MISMATCH
    if compute_git_push_preview_hash(_preview_hash_material(preview)) != preview_hash:
        return CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_HASH_MISMATCH
    return None


def _preview_hash_material(preview: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(preview)
    material.pop("preview_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _resolve_repo_path(repo_path: str | Path, workspace_root: str | Path | None) -> tuple[Path | None, Path | None, str | None]:
    raw_repo = str(repo_path)
    if not raw_repo or "\x00" in raw_repo or ".." in Path(raw_repo).parts:
        return None, None, CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH
    try:
        workspace = None
        if workspace_root is not None:
            raw_workspace = str(workspace_root)
            if not raw_workspace or "\x00" in raw_workspace or ".." in Path(raw_workspace).parts:
                return None, None, CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH
            workspace = Path(workspace_root).resolve(strict=True)
            candidate = Path(repo_path)
            if not candidate.is_absolute():
                candidate = workspace / candidate
            resolved = candidate.resolve(strict=True)
            if not _is_relative_to(resolved, workspace):
                return None, None, CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH
        else:
            resolved = Path(repo_path).resolve(strict=True)
    except OSError:
        return None, None, CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH
    if not resolved.is_dir():
        return None, None, CONTROLLED_GIT_PUSH_BLOCKED_WORKSPACE_PATH
    return resolved, workspace, None


def _repo_root_error(preview: Mapping[str, Any], repo: Path) -> str | None:
    preview_root = _text(preview.get("repo_path"))
    if preview_root is None:
        return CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH
    try:
        if Path(preview_root).resolve(strict=True) != repo:
            return CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH
    except OSError:
        return CONTROLLED_GIT_PUSH_BLOCKED_REPO_MISMATCH
    return None


def _local_remote_path(url: str, repo: Path, workspace: Path | None) -> Path | None:
    if not url or "\x00" in url:
        return None
    if url.startswith("file://"):
        raw_path = url[7:]
    elif "://" in url:
        return None
    elif ":" in url and not Path(url).is_absolute():
        return None
    else:
        raw_path = url
    try:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = repo / candidate
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    if not resolved.is_dir():
        return None
    if workspace is not None and not _is_relative_to(resolved, workspace):
        return None
    return resolved


def _run(
    runner: Any,
    command_id: _GitPushCommand,
    repo: Path,
    *,
    remote_name: str | None = None,
    remote_ref: str | None = None,
    local_head: str | None = None,
    remote_head: str | None = None,
) -> _GitRunnerResult:
    result = runner.run(command_id, repo, remote_name=remote_name, remote_ref=remote_ref, local_head=local_head, remote_head=remote_head)
    if isinstance(result, _GitRunnerResult):
        normalized = result
    else:
        normalized = _GitRunnerResult(
            command_id.value,
            getattr(result, "exit_code", 1),
            _bytes(getattr(result, "stdout", b"")),
            _bytes(getattr(result, "stderr", b"")),
            bool(getattr(result, "timeout_expired", False)),
        )
    if normalized.timeout_expired:
        raise _ControlledGitPushTimeout(command_id.value)
    return normalized


def _remote_head_from_output(value: bytes, remote_ref: str | None) -> str | None:
    if not _safe_remote_ref(remote_ref):
        return None
    for line in value.decode("utf-8", errors="replace").splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1] == remote_ref and _sha_like(parts[0]):
            return parts[0].lower()
    return None


def _ahead_behind(value: bytes) -> tuple[int | None, int | None]:
    parts = value.decode("utf-8", errors="replace").strip().split()
    if len(parts) != 2:
        return None, None
    try:
        behind = int(parts[0])
        ahead = int(parts[1])
    except ValueError:
        return None, None
    return behind, ahead


def _safe_remote_name(value: str | None) -> bool:
    return isinstance(value, str) and bool(value) and not value.startswith("-") and "/" not in value and all(char in _REMOTE_NAME_CHARS for char in value)


def _safe_remote_ref(value: str | None) -> bool:
    if not isinstance(value, str) or not value.startswith("refs/heads/"):
        return False
    parts = tuple(part for part in value.split("/") if part)
    return not (
        value.startswith("-")
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or ".." in parts
        or any(char in _UNSAFE_REF_MARKERS for char in value)
        or any(part in (".", "..") for part in parts)
    )


def _authority_claim_present(value: Any) -> bool:
    mapping = _mapping(value)
    if mapping is None:
        return False
    return any(mapping.get(field_name) is True for field_name in _AUTHORITY_FIELDS)


def _blocked(
    reason_code: str,
    reason: str,
    *,
    repo: Path | None = None,
    remote_name: str | None = None,
    remote_ref: str | None = None,
    branch: str | None = None,
    local_head_before: str | None = None,
    local_head_after: str | None = None,
    remote_head_before: str | None = None,
    remote_head_after: str | None = None,
    commits_ahead_before: int | None = None,
    commits_behind_before: int | None = None,
    preview_hash: str | None = None,
    barrier: GitPushBarrierResult | None = None,
) -> ControlledGitPushResult:
    return _result(
        status=CONTROLLED_GIT_PUSH_BLOCKED,
        reason_code=reason_code,
        reason=reason,
        repo=repo,
        remote_name=remote_name,
        remote_ref=remote_ref,
        branch=branch,
        local_head_before=local_head_before,
        local_head_after=local_head_after,
        remote_head_before=remote_head_before,
        remote_head_after=remote_head_after,
        commits_ahead_before=commits_ahead_before,
        commits_behind_before=commits_behind_before,
        preview_hash=preview_hash,
        barrier=barrier,
    )


def _result(
    *,
    status: str,
    reason_code: str,
    reason: str,
    repo: Path | None,
    remote_name: str | None = None,
    remote_ref: str | None = None,
    branch: str | None = None,
    local_head_before: str | None = None,
    local_head_after: str | None = None,
    remote_head_before: str | None = None,
    remote_head_after: str | None = None,
    commits_ahead_before: int | None = None,
    commits_behind_before: int | None = None,
    preview_hash: str | None = None,
    barrier: GitPushBarrierResult | None = None,
) -> ControlledGitPushResult:
    material = {
        "schema_version": _RESULT_SCHEMA_VERSION,
        "status": status,
        "repo_path": str(repo) if repo is not None else None,
        "remote_name": remote_name,
        "remote_ref": remote_ref,
        "branch": branch,
        "local_head_before": local_head_before,
        "local_head_after": local_head_after,
        "remote_head_before": remote_head_before,
        "remote_head_after": remote_head_after,
        "commits_ahead_before": commits_ahead_before,
        "commits_behind_before": commits_behind_before,
        "reviewed_push_preview_hash": preview_hash,
        "barrier_evidence_hash": barrier.push_barrier_hash if barrier is not None else None,
        "human_barrier_hash": barrier.human_barrier_hash if barrier is not None else None,
        "human_decision_hash": barrier.human_decision_hash if barrier is not None else None,
        "reason_code": reason_code,
        "reason": reason,
    }
    return ControlledGitPushResult(
        status=status,
        repo_path=material["repo_path"],
        remote_name=remote_name,
        remote_ref=remote_ref,
        branch=branch,
        local_head_before=local_head_before,
        local_head_after=local_head_after,
        remote_head_before=remote_head_before,
        remote_head_after=remote_head_after,
        commits_ahead_before=commits_ahead_before,
        commits_behind_before=commits_behind_before,
        reviewed_push_preview_hash=preview_hash,
        barrier_evidence_hash=material["barrier_evidence_hash"],
        human_barrier_hash=material["human_barrier_hash"],
        human_decision_hash=material["human_decision_hash"],
        reason_code=reason_code,
        reason=reason,
        result_hash=hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest(),
    )


def _mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return dict(data)
    return None


def _single_line(value: bytes) -> str:
    return value.decode("utf-8", errors="replace").strip().splitlines()[0].strip() if value.strip() else ""


def _resolved_existing_dir(value: str) -> Path | None:
    try:
        path = Path(value).resolve(strict=True)
    except OSError:
        return None
    return path if path.is_dir() else None


def _bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8", errors="replace")


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _sha256_like(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _sha_like(value: str | None) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(char in _HEX for char in value.lower())


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
