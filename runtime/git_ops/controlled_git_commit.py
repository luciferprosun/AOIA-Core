from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from runtime.git_ops.git_commit_barrier import (
    GIT_COMMIT_BARRIER_ELIGIBLE,
    GitCommitBarrierRequest,
    GitCommitBarrierResult,
    evaluate_git_commit_barrier,
)
from runtime.git_ops.git_commit_preview import (
    GIT_COMMIT_PREVIEW_KIND,
    GIT_COMMIT_PREVIEW_PASS,
    GIT_COMMIT_PREVIEW_SCHEMA_VERSION,
    compute_commit_message_hash,
    compute_git_commit_preview_hash,
)
from runtime.git_ops.git_env import build_hardened_git_env
from runtime.git_ops.git_write_preview import GitWriteIntent


CONTROLLED_GIT_COMMIT_COMMITTED = "CONTROLLED_GIT_COMMIT_COMMITTED"
CONTROLLED_GIT_COMMIT_BLOCKED = "CONTROLLED_GIT_COMMIT_BLOCKED"

CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_PREVIEW = "CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_PREVIEW"
CONTROLLED_GIT_COMMIT_BLOCKED_MALFORMED_PREVIEW = "CONTROLLED_GIT_COMMIT_BLOCKED_MALFORMED_PREVIEW"
CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_HASH_MISMATCH = "CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_HASH_MISMATCH"
CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_NOT_PASS = "CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_NOT_PASS"
CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_REVIEWED_DIFF_HASH = "CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_REVIEWED_DIFF_HASH"
CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_BARRIER = "CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_BARRIER"
CONTROLLED_GIT_COMMIT_BLOCKED_BARRIER_INVALID = "CONTROLLED_GIT_COMMIT_BLOCKED_BARRIER_INVALID"
CONTROLLED_GIT_COMMIT_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_GIT_COMMIT_BLOCKED_AUTHORITY_CLAIM"
CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH = "CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH"
CONTROLLED_GIT_COMMIT_BLOCKED_NON_GIT_REPO = "CONTROLLED_GIT_COMMIT_BLOCKED_NON_GIT_REPO"
CONTROLLED_GIT_COMMIT_BLOCKED_REPO_MISMATCH = "CONTROLLED_GIT_COMMIT_BLOCKED_REPO_MISMATCH"
CONTROLLED_GIT_COMMIT_BLOCKED_HEAD_CHANGED = "CONTROLLED_GIT_COMMIT_BLOCKED_HEAD_CHANGED"
CONTROLLED_GIT_COMMIT_BLOCKED_BRANCH_CHANGED = "CONTROLLED_GIT_COMMIT_BLOCKED_BRANCH_CHANGED"
CONTROLLED_GIT_COMMIT_BLOCKED_EMPTY_STAGED_DIFF = "CONTROLLED_GIT_COMMIT_BLOCKED_EMPTY_STAGED_DIFF"
CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_DIFF_CHANGED = "CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_DIFF_CHANGED"
CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_PATHS_CHANGED = "CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_PATHS_CHANGED"
CONTROLLED_GIT_COMMIT_BLOCKED_UNSTAGED_CHANGES = "CONTROLLED_GIT_COMMIT_BLOCKED_UNSTAGED_CHANGES"
CONTROLLED_GIT_COMMIT_BLOCKED_UNTRACKED_CHANGES = "CONTROLLED_GIT_COMMIT_BLOCKED_UNTRACKED_CHANGES"
CONTROLLED_GIT_COMMIT_BLOCKED_MESSAGE_MISMATCH = "CONTROLLED_GIT_COMMIT_BLOCKED_MESSAGE_MISMATCH"
CONTROLLED_GIT_COMMIT_BLOCKED_GIT_COMMIT_FAILED = "CONTROLLED_GIT_COMMIT_BLOCKED_GIT_COMMIT_FAILED"
CONTROLLED_GIT_COMMIT_BLOCKED_FAIL_CLOSED = "CONTROLLED_GIT_COMMIT_BLOCKED_FAIL_CLOSED"

_RESULT_SCHEMA_VERSION = "AOIA_CONTROLLED_GIT_COMMIT_1A"
_DEFAULT_TIMEOUT_SECONDS = 15
_HEX = frozenset("0123456789abcdef")
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
    "eligible_for_controlled_commit",
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


class _GitCommitCommand(str, Enum):
    REV_PARSE_TOPLEVEL = "REV_PARSE_TOPLEVEL"
    REV_PARSE_HEAD = "REV_PARSE_HEAD"
    REV_PARSE_BRANCH = "REV_PARSE_BRANCH"
    STATUS_PORCELAIN = "STATUS_PORCELAIN"
    DIFF_CACHED_BINARY = "DIFF_CACHED_BINARY"
    COMMIT = "COMMIT"


_ALLOWLIST: dict[_GitCommitCommand, tuple[str, ...]] = {
    _GitCommitCommand.REV_PARSE_TOPLEVEL: ("git", "rev-parse", "--show-toplevel"),
    _GitCommitCommand.REV_PARSE_HEAD: ("git", "rev-parse", "HEAD"),
    _GitCommitCommand.REV_PARSE_BRANCH: ("git", "rev-parse", "--abbrev-ref", "HEAD"),
    _GitCommitCommand.STATUS_PORCELAIN: ("git", "status", "--porcelain=v1", "--untracked-files=all"),
    _GitCommitCommand.DIFF_CACHED_BINARY: ("git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff"),
}


@dataclass(frozen=True)
class ControlledGitCommitResult:
    status: str
    repo_path: str | None
    previous_head: str | None
    new_head: str | None
    commit_hash: str | None
    reviewed_commit_preview_hash: str | None
    barrier_evidence_hash: str | None
    human_barrier_hash: str | None
    human_decision_hash: str | None
    staged_diff_hash: str | None
    committed_message_hash: str | None
    reason_code: str
    reason: str
    result_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _RESULT_SCHEMA_VERSION,
            "status": self.status,
            "repo_path": self.repo_path,
            "previous_head": self.previous_head,
            "new_head": self.new_head,
            "commit_hash": self.commit_hash,
            "reviewed_commit_preview_hash": self.reviewed_commit_preview_hash,
            "barrier_evidence_hash": self.barrier_evidence_hash,
            "human_barrier_hash": self.human_barrier_hash,
            "human_decision_hash": self.human_decision_hash,
            "staged_diff_hash": self.staged_diff_hash,
            "committed_message_hash": self.committed_message_hash,
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


class _ControlledGitCommitRunner:
    def run(self, command_id: _GitCommitCommand, repo_path: Path, message: str | None = None) -> _GitRunnerResult:
        if command_id is _GitCommitCommand.COMMIT:
            if not isinstance(message, str) or message == "":
                return _GitRunnerResult(command_id.value, 2, b"", b"missing commit message")
            argv = (
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "--no-verify",
                "-m",
                message,
            )
        else:
            argv = _ALLOWLIST[command_id]
        try:
            completed = subprocess.run(
                list(argv),
                cwd=str(repo_path),
                env=build_hardened_git_env(),
                shell=False,
                capture_output=True,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            return _GitRunnerResult(
                command_id.value,
                None,
                _bytes(exc.stdout),
                _bytes(exc.stderr),
                timeout_expired=True,
            )
        except (OSError, ValueError) as exc:
            return _GitRunnerResult(command_id.value, 1, b"", str(exc).encode("utf-8", errors="replace"))
        return _GitRunnerResult(command_id.value, completed.returncode, _bytes(completed.stdout), _bytes(completed.stderr))


def controlled_git_commit(
    repo_path: str | Path,
    commit_preview: Any,
    barrier_evidence: Any,
    *,
    workspace_root: str | Path | None = None,
    now: Any = None,
    runner: Any = None,
) -> ControlledGitCommitResult:
    del now
    try:
        preview = _mapping(commit_preview)
        if preview is None:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_PREVIEW, "hash-bound commit preview evidence is required")

        preview_hash = _text(preview.get("commit_preview_hash"))
        preview_error = _preview_error(preview)
        if preview_error is not None:
            return _blocked(preview_error, "valid hash-bound commit preview evidence is required", preview_hash=preview_hash)

        assert preview_hash is not None
        if barrier_evidence is None:
            return _blocked(
                CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_BARRIER,
                "hash-bound human barrier evidence is required",
                preview_hash=preview_hash,
            )
        if _authority_claim_present(barrier_evidence):
            return _blocked(
                CONTROLLED_GIT_COMMIT_BLOCKED_AUTHORITY_CLAIM,
                "metadata authority claims cannot authorize a commit",
                preview_hash=preview_hash,
            )

        barrier = evaluate_git_commit_barrier(
            GitCommitBarrierRequest(
                commit_preview=preview,
                human_barrier=barrier_evidence,
                expected_commit_preview_hash=preview_hash,
                source_trust="USER_SUPPLIED",
            )
        )
        if barrier.status != GIT_COMMIT_BARRIER_ELIGIBLE or not barrier.eligible_for_controlled_commit:
            return _blocked(
                CONTROLLED_GIT_COMMIT_BLOCKED_BARRIER_INVALID,
                "valid hash-bound human commit barrier evidence is required",
                preview_hash=preview_hash,
                barrier=barrier,
            )

        repo, repo_error = _resolve_repo_path(repo_path, workspace_root)
        if repo_error is not None:
            return _blocked(repo_error, "repository path is outside the allowed workspace", preview_hash=preview_hash, barrier=barrier)
        assert repo is not None

        active_runner = runner or _ControlledGitCommitRunner()
        toplevel = _run(active_runner, _GitCommitCommand.REV_PARSE_TOPLEVEL, repo)
        if not toplevel.ok:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_NON_GIT_REPO, "repository path is not a usable git repository", repo=repo, preview_hash=preview_hash, barrier=barrier)
        resolved_toplevel = _resolved_existing_dir(_single_line(toplevel.stdout))
        if resolved_toplevel != repo:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_REPO_MISMATCH, "git repository root differs from the reviewed repository path", repo=repo, preview_hash=preview_hash, barrier=barrier)

        repo_root_error = _repo_root_error(preview, repo)
        if repo_root_error is not None:
            return _blocked(repo_root_error, "commit preview repository binding does not match the live repository", repo=repo, preview_hash=preview_hash, barrier=barrier)

        head_result = _run(active_runner, _GitCommitCommand.REV_PARSE_HEAD, repo)
        if not head_result.ok:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_NON_GIT_REPO, "current repository HEAD could not be read", repo=repo, preview_hash=preview_hash, barrier=barrier)
        previous_head = _single_line(head_result.stdout)
        if previous_head != _text(preview.get("parent_head_sha")):
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_HEAD_CHANGED, "repository HEAD changed after commit preview review", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)

        branch_result = _run(active_runner, _GitCommitCommand.REV_PARSE_BRANCH, repo)
        if not branch_result.ok or _single_line(branch_result.stdout) != _text(preview.get("branch_name")):
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_BRANCH_CHANGED, "repository branch changed after commit preview review", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)

        status_result = _run(active_runner, _GitCommitCommand.STATUS_PORCELAIN, repo)
        if not status_result.ok:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_NON_GIT_REPO, "repository status could not be read", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)
        staged_paths, unstaged_paths, untracked_paths = _parse_status(status_result.stdout)
        if unstaged_paths:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_UNSTAGED_CHANGES, "unstaged changes are not included in the reviewed commit preview", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)
        if untracked_paths:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_UNTRACKED_CHANGES, "untracked changes are not included in the reviewed commit preview", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)

        diff_result = _run(active_runner, _GitCommitCommand.DIFF_CACHED_BINARY, repo)
        if not diff_result.ok:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_NON_GIT_REPO, "staged diff could not be read", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)
        if not diff_result.stdout:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_EMPTY_STAGED_DIFF, "empty staged diff cannot be committed through the controlled path", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)

        target_paths, target_error = _target_paths(preview.get("target_paths"))
        if target_error is not None:
            return _blocked(target_error, "commit preview target paths are unsafe or malformed", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)
        if staged_paths != target_paths:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_PATHS_CHANGED, "staged paths differ from the reviewed commit preview", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier)

        staged_diff_hash = hashlib.sha256(diff_result.stdout).hexdigest()
        if staged_diff_hash != _text(preview.get("reviewed_staged_diff_hash")):
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_DIFF_CHANGED, "staged diff changed after commit preview review", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier, staged_diff_hash=staged_diff_hash)

        message = _text(preview.get("normalized_commit_message_preview"))
        if message is None or preview.get("commit_message_hash") != compute_commit_message_hash(message):
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_MESSAGE_MISMATCH, "commit message does not match reviewed commit preview", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier, staged_diff_hash=staged_diff_hash)

        commit_result = _run(active_runner, _GitCommitCommand.COMMIT, repo, message=message)
        if not commit_result.ok:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_GIT_COMMIT_FAILED, "local git commit failed after evidence validation", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier, staged_diff_hash=staged_diff_hash, message_hash=compute_commit_message_hash(message))

        new_head_result = _run(active_runner, _GitCommitCommand.REV_PARSE_HEAD, repo)
        if not new_head_result.ok:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_FAIL_CLOSED, "new repository HEAD could not be read after commit", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier, staged_diff_hash=staged_diff_hash, message_hash=compute_commit_message_hash(message))
        new_head = _single_line(new_head_result.stdout)
        if not _sha_like(new_head) or new_head == previous_head:
            return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_FAIL_CLOSED, "controlled commit did not produce a new HEAD", repo=repo, previous_head=previous_head, preview_hash=preview_hash, barrier=barrier, staged_diff_hash=staged_diff_hash, message_hash=compute_commit_message_hash(message))

        return _result(
            status=CONTROLLED_GIT_COMMIT_COMMITTED,
            reason_code=CONTROLLED_GIT_COMMIT_COMMITTED,
            reason="local git commit completed after hash-bound preview and human barrier validation",
            repo=repo,
            previous_head=previous_head,
            new_head=new_head,
            commit_hash=new_head,
            preview_hash=preview_hash,
            barrier=barrier,
            staged_diff_hash=staged_diff_hash,
            message_hash=compute_commit_message_hash(message),
        )
    except Exception:
        return _blocked(CONTROLLED_GIT_COMMIT_BLOCKED_FAIL_CLOSED, "controlled git commit failed closed")


def _preview_error(preview: Mapping[str, Any]) -> str | None:
    if _authority_claim_present(preview):
        return CONTROLLED_GIT_COMMIT_BLOCKED_AUTHORITY_CLAIM
    if preview.get("preview_kind") != GIT_COMMIT_PREVIEW_KIND or preview.get("schema_version") != GIT_COMMIT_PREVIEW_SCHEMA_VERSION:
        return CONTROLLED_GIT_COMMIT_BLOCKED_MALFORMED_PREVIEW
    if preview.get("status") != GIT_COMMIT_PREVIEW_PASS:
        return CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_NOT_PASS
    preview_hash = _text(preview.get("commit_preview_hash"))
    if not _sha256_like(preview_hash):
        return CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_HASH_MISMATCH
    if compute_git_commit_preview_hash(_preview_hash_material(preview)) != preview_hash:
        return CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_HASH_MISMATCH
    if preview.get("operation_kind") != GitWriteIntent.LOCAL_COMMIT_INTENT.value:
        return CONTROLLED_GIT_COMMIT_BLOCKED_MALFORMED_PREVIEW
    if preview.get("commit_message_hash") != compute_commit_message_hash(_text(preview.get("normalized_commit_message_preview"))):
        return CONTROLLED_GIT_COMMIT_BLOCKED_MESSAGE_MISMATCH
    if not _sha256_like(_text(preview.get("reviewed_staged_diff_hash"))):
        return CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_REVIEWED_DIFF_HASH
    return None


def _resolve_repo_path(repo_path: str | Path, workspace_root: str | Path | None) -> tuple[Path | None, str | None]:
    raw_repo = str(repo_path)
    if not raw_repo or "\x00" in raw_repo or ".." in Path(raw_repo).parts:
        return None, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
    try:
        if workspace_root is not None:
            raw_workspace = str(workspace_root)
            if not raw_workspace or "\x00" in raw_workspace or ".." in Path(raw_workspace).parts:
                return None, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
            workspace = Path(workspace_root).resolve(strict=True)
            candidate = Path(repo_path)
            if not candidate.is_absolute():
                candidate = workspace / candidate
            resolved = candidate.resolve(strict=True)
            if not _is_relative_to(resolved, workspace):
                return None, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
        else:
            resolved = Path(repo_path).resolve(strict=True)
    except OSError:
        return None, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
    if not resolved.is_dir():
        return None, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
    return resolved, None


def _repo_root_error(preview: Mapping[str, Any], repo: Path) -> str | None:
    preview_root = _text(preview.get("repo_root"))
    if preview_root is None:
        return CONTROLLED_GIT_COMMIT_BLOCKED_REPO_MISMATCH
    try:
        if Path(preview_root).resolve(strict=True) != repo:
            return CONTROLLED_GIT_COMMIT_BLOCKED_REPO_MISMATCH
    except OSError:
        return CONTROLLED_GIT_COMMIT_BLOCKED_REPO_MISMATCH
    return None


def _run(runner: Any, command_id: _GitCommitCommand, repo: Path, message: str | None = None) -> _GitRunnerResult:
    result = runner.run(command_id, repo, message=message)
    if isinstance(result, _GitRunnerResult):
        return result
    return _GitRunnerResult(
        command_id.value,
        getattr(result, "exit_code", 1),
        _bytes(getattr(result, "stdout", b"")),
        _bytes(getattr(result, "stderr", b"")),
        bool(getattr(result, "timeout_expired", False)),
    )


def _target_paths(value: Any) -> tuple[tuple[str, ...], str | None]:
    if not isinstance(value, (tuple, list)):
        return (), CONTROLLED_GIT_COMMIT_BLOCKED_MALFORMED_PREVIEW
    raw_paths = tuple(str(item).strip().replace("//", "/") for item in value if isinstance(item, str) and item.strip())
    if not raw_paths or len(set(raw_paths)) != len(raw_paths):
        return (), CONTROLLED_GIT_COMMIT_BLOCKED_MALFORMED_PREVIEW
    for path in raw_paths:
        parts = PurePosixPath(path).parts
        if "\x00" in path or "\\" in path or PurePosixPath(path).is_absolute() or any(part == ".." for part in parts):
            return (), CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
        if path.startswith("-") or path == ".git" or path.startswith(".git/") or any(marker in path for marker in (":(glob)", ":(attr)", ":(top)", ":/")):
            return (), CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH
    return tuple(sorted(set(raw_paths))), None


def _parse_status(value: bytes) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in value.decode("utf-8", errors="replace").splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path = _status_path(line[3:])
        if code == "??":
            untracked.append(path)
            continue
        if code[0] != " ":
            staged.append(path)
        if code[1] != " ":
            unstaged.append(path)
    return tuple(sorted(set(staged))), tuple(sorted(set(unstaged))), tuple(sorted(set(untracked)))


def _status_path(value: str) -> str:
    text = value.strip()
    if " -> " in text:
        text = text.split(" -> ", 1)[1].strip()
    return text


def _preview_hash_material(preview: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(preview)
    material.pop("commit_preview_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


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
    previous_head: str | None = None,
    preview_hash: str | None = None,
    barrier: GitCommitBarrierResult | None = None,
    staged_diff_hash: str | None = None,
    message_hash: str | None = None,
) -> ControlledGitCommitResult:
    return _result(
        status=CONTROLLED_GIT_COMMIT_BLOCKED,
        reason_code=reason_code,
        reason=reason,
        repo=repo,
        previous_head=previous_head,
        new_head=None,
        commit_hash=None,
        preview_hash=preview_hash,
        barrier=barrier,
        staged_diff_hash=staged_diff_hash,
        message_hash=message_hash,
    )


def _result(
    *,
    status: str,
    reason_code: str,
    reason: str,
    repo: Path | None,
    previous_head: str | None,
    new_head: str | None,
    commit_hash: str | None,
    preview_hash: str | None,
    barrier: GitCommitBarrierResult | None,
    staged_diff_hash: str | None,
    message_hash: str | None,
) -> ControlledGitCommitResult:
    material = {
        "schema_version": _RESULT_SCHEMA_VERSION,
        "status": status,
        "repo_path": str(repo) if repo is not None else None,
        "previous_head": previous_head,
        "new_head": new_head,
        "commit_hash": commit_hash,
        "reviewed_commit_preview_hash": preview_hash,
        "barrier_evidence_hash": barrier.commit_barrier_hash if barrier is not None else None,
        "human_barrier_hash": barrier.human_barrier_hash if barrier is not None else None,
        "human_decision_hash": barrier.human_decision_hash if barrier is not None else None,
        "staged_diff_hash": staged_diff_hash,
        "committed_message_hash": message_hash,
        "reason_code": reason_code,
        "reason": reason,
    }
    return ControlledGitCommitResult(
        status=status,
        repo_path=material["repo_path"],
        previous_head=previous_head,
        new_head=new_head,
        commit_hash=commit_hash,
        reviewed_commit_preview_hash=preview_hash,
        barrier_evidence_hash=material["barrier_evidence_hash"],
        human_barrier_hash=material["human_barrier_hash"],
        human_decision_hash=material["human_decision_hash"],
        staged_diff_hash=staged_diff_hash,
        committed_message_hash=message_hash,
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
