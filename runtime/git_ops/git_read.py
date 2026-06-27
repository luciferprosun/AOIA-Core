from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.git_ops.git_env import build_hardened_git_env
from runtime.git_ops.git_sanitize import sanitize_git_output
from runtime.safety.workspace_guard import validate_workspace_root


GIT_READ_READY = "READY"
GIT_READ_BLOCKED = "BLOCKED"
GIT_READ_ERROR = "ERROR"

GIT_READ_COMMAND_PASS = "PASS"
GIT_READ_COMMAND_BLOCKED = "BLOCKED"
GIT_READ_COMMAND_ERROR = "ERROR"

GIT_READ_READY_EVIDENCE_ONLY = "GIT_READ_READY_EVIDENCE_ONLY"
GIT_READ_BLOCKED_MISSING_WORKSPACE = "GIT_READ_BLOCKED_MISSING_WORKSPACE"
GIT_READ_BLOCKED_WORKSPACE_GUARD = "GIT_READ_BLOCKED_WORKSPACE_GUARD"
GIT_READ_BLOCKED_REPO_ROOT_OUTSIDE_WORKSPACE = "GIT_READ_BLOCKED_REPO_ROOT_OUTSIDE_WORKSPACE"
GIT_READ_BLOCKED_UNSAFE_PATH_ARGUMENT = "GIT_READ_BLOCKED_UNSAFE_PATH_ARGUMENT"
GIT_READ_BLOCKED_UNSUPPORTED_COMMAND = "GIT_READ_BLOCKED_UNSUPPORTED_COMMAND"
GIT_READ_BLOCKED_WRITE_COMMAND = "GIT_READ_BLOCKED_WRITE_COMMAND"
GIT_READ_BLOCKED_OUTPUT_LIMIT = "GIT_READ_BLOCKED_OUTPUT_LIMIT"
GIT_READ_ERROR_TIMEOUT = "GIT_READ_ERROR_TIMEOUT"
GIT_READ_ERROR_EXIT_CODE = "GIT_READ_ERROR_EXIT_CODE"
GIT_READ_ERROR_MALFORMED_HEAD = "GIT_READ_ERROR_MALFORMED_HEAD"
GIT_READ_ERROR_REPO_ROOT_MISMATCH = "GIT_READ_ERROR_REPO_ROOT_MISMATCH"
GIT_READ_ERROR_INTERNAL = "GIT_READ_ERROR_INTERNAL"

_SCHEMA_VERSION = "AOIA_GIT_READ_ADAPTER_1A"
_DEFAULT_TIMEOUT_SECONDS = 10
_DEFAULT_MAX_OUTPUT_BYTES = 12_000
_MIN_TIMEOUT_SECONDS = 1
_MAX_TIMEOUT_SECONDS = 60
_MIN_OUTPUT_BYTES = 256
_MAX_OUTPUT_BYTES = 50_000
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
    "provider_authority_granted",
    "execution_authority_granted",
)
_BLOCKED_COMMAND_IDS = frozenset(
    (
        "ADD",
        "COMMIT",
        "PUSH",
        "PULL",
        "FETCH",
        "CHECKOUT",
        "SWITCH",
        "RESET",
        "RESTORE",
        "STASH",
        "MERGE",
        "REBASE",
        "CLEAN",
        "REMOVE",
        "MOVE",
        "REMOTE",
        "LS_REMOTE",
    )
)


class GitReadCommand(str, Enum):
    SHOW_TOPLEVEL = "SHOW_TOPLEVEL"
    VERIFY_HEAD = "VERIFY_HEAD"
    BRANCH_NAME = "BRANCH_NAME"
    STATUS_PORCELAIN = "STATUS_PORCELAIN"
    DIFF_NAME_STATUS = "DIFF_NAME_STATUS"
    DIFF_CACHED_NAME_STATUS = "DIFF_CACHED_NAME_STATUS"
    LS_FILES_OTHERS = "LS_FILES_OTHERS"


_ALLOWLIST: dict[GitReadCommand, tuple[str, ...]] = {
    GitReadCommand.SHOW_TOPLEVEL: ("git", "rev-parse", "--show-toplevel"),
    GitReadCommand.VERIFY_HEAD: ("git", "rev-parse", "--verify", "HEAD"),
    GitReadCommand.BRANCH_NAME: ("git", "rev-parse", "--abbrev-ref", "HEAD"),
    GitReadCommand.STATUS_PORCELAIN: ("git", "status", "--porcelain=v1", "--untracked-files=all"),
    GitReadCommand.DIFF_NAME_STATUS: ("git", "diff", "--name-status"),
    GitReadCommand.DIFF_CACHED_NAME_STATUS: ("git", "diff", "--cached", "--name-status"),
    GitReadCommand.LS_FILES_OTHERS: ("git", "ls-files", "--others", "--exclude-standard"),
}


@dataclass(frozen=True)
class GitReadRequest:
    workspace_root: str | Path | None
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    max_output_bytes: int = _DEFAULT_MAX_OUTPUT_BYTES


@dataclass(frozen=True)
class GitCommandEvidence:
    command_id: str
    status: str
    reason_code: str
    exit_code: int | None
    timeout_expired: bool
    stdout_preview: str
    stderr_preview: str
    stdout_truncated: bool
    stderr_truncated: bool
    command_hash: str
    subprocess_started: bool = False
    shell_invoked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "shell_invoked", False)
        object.__setattr__(self, "stdout_preview", sanitize_git_output(self.stdout_preview))
        object.__setattr__(self, "stderr_preview", sanitize_git_output(self.stderr_preview))

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "exit_code": self.exit_code,
            "timeout_expired": self.timeout_expired,
            "stdout_preview": self.stdout_preview,
            "stderr_preview": self.stderr_preview,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "command_hash": self.command_hash,
            "subprocess_started": self.subprocess_started,
            "shell_invoked": self.shell_invoked,
        }


@dataclass(frozen=True)
class GitReadResult:
    status: str
    git_read_hash: str
    repo_root: str | None
    head_sha: str | None
    branch_name: str | None
    detached_head: bool
    clean: bool | None
    staged_paths: tuple[str, ...]
    unstaged_paths: tuple[str, ...]
    untracked_paths: tuple[str, ...]
    command_evidence: tuple[GitCommandEvidence, ...]
    reason_codes: tuple[str, ...]
    reason: str
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    git_write_authority_granted: bool = False
    provider_authority_granted: bool = False
    execution_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "staged_paths", tuple(self.staged_paths))
        object.__setattr__(self, "unstaged_paths", tuple(self.unstaged_paths))
        object.__setattr__(self, "untracked_paths", tuple(self.untracked_paths))
        object.__setattr__(self, "command_evidence", tuple(self.command_evidence))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "git_read_hash": self.git_read_hash,
            "repo_root": self.repo_root,
            "head_sha": self.head_sha,
            "branch_name": self.branch_name,
            "detached_head": self.detached_head,
            "clean": self.clean,
            "staged_paths": self.staged_paths,
            "unstaged_paths": self.unstaged_paths,
            "untracked_paths": self.untracked_paths,
            "command_evidence": tuple(item.to_dict() for item in self.command_evidence),
            "reason_codes": self.reason_codes,
            "reason": self.reason,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "git_write_authority_granted": self.git_write_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
        }


def canonical_git_read_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_git_read_hash(value: Any) -> str:
    return hashlib.sha256(canonical_git_read_json(value).encode("utf-8")).hexdigest()


def validate_git_workspace_root(workspace_root: str | Path | None, path_argument: str | None = None) -> GitReadResult:
    path_reason = _validate_no_path_argument(path_argument)
    if path_reason is not None:
        return _result(
            status=GIT_READ_BLOCKED,
            repo_root=None,
            head_sha=None,
            branch_name=None,
            detached_head=False,
            clean=None,
            staged_paths=(),
            unstaged_paths=(),
            untracked_paths=(),
            command_evidence=(),
            reason_codes=(path_reason,),
            reason="Git read adapter does not accept path arguments in Step 27A.",
        )

    guard = validate_workspace_root(workspace_root)
    if not guard.allowed:
        code = GIT_READ_BLOCKED_MISSING_WORKSPACE if workspace_root is None else GIT_READ_BLOCKED_WORKSPACE_GUARD
        return _result(
            status=GIT_READ_BLOCKED,
            repo_root=guard.workspace_root,
            head_sha=None,
            branch_name=None,
            detached_head=False,
            clean=None,
            staged_paths=(),
            unstaged_paths=(),
            untracked_paths=(),
            command_evidence=(),
            reason_codes=(code, guard.reason_code),
            reason=guard.reason,
        )

    return _result(
        status=GIT_READ_READY,
        repo_root=guard.workspace_root,
        head_sha=None,
        branch_name=None,
        detached_head=False,
        clean=None,
        staged_paths=(),
        unstaged_paths=(),
        untracked_paths=(),
        command_evidence=(),
        reason_codes=(GIT_READ_READY_EVIDENCE_ONLY,),
        reason="Workspace root is valid for local Git read evidence only.",
    )


def run_allowlisted_git_read(
    request: GitReadRequest,
    command_id: GitReadCommand,
) -> GitCommandEvidence:
    if not isinstance(command_id, GitReadCommand):
        return _command_blocked(str(command_id), GIT_READ_BLOCKED_UNSUPPORTED_COMMAND)
    if command_id.value in _BLOCKED_COMMAND_IDS:
        return _command_blocked(command_id.value, GIT_READ_BLOCKED_WRITE_COMMAND)

    workspace = validate_git_workspace_root(request.workspace_root)
    if workspace.status != GIT_READ_READY or workspace.repo_root is None:
        return _command_blocked(command_id.value, GIT_READ_BLOCKED_WORKSPACE_GUARD)

    timeout = _clamp_timeout(request.timeout_seconds)
    max_output = _clamp_output_bytes(request.max_output_bytes)
    argv = _ALLOWLIST[command_id]
    command_hash = compute_git_read_hash({"command_id": command_id.value, "argv": argv})
    try:
        completed = subprocess.run(
            argv,
            cwd=workspace.repo_root,
            env=build_hardened_git_env(),
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return GitCommandEvidence(
            command_id=command_id.value,
            status=GIT_READ_COMMAND_ERROR,
            reason_code=GIT_READ_ERROR_TIMEOUT,
            exit_code=None,
            timeout_expired=True,
            stdout_preview=_bounded_text(exc.stdout, max_output)[0],
            stderr_preview=_bounded_text(exc.stderr, max_output)[0],
            stdout_truncated=_bounded_text(exc.stdout, max_output)[1],
            stderr_truncated=_bounded_text(exc.stderr, max_output)[1],
            command_hash=command_hash,
            subprocess_started=True,
        )
    except (OSError, ValueError) as exc:
        return GitCommandEvidence(
            command_id=command_id.value,
            status=GIT_READ_COMMAND_ERROR,
            reason_code=GIT_READ_ERROR_INTERNAL,
            exit_code=None,
            timeout_expired=False,
            stdout_preview="",
            stderr_preview=sanitize_git_output(str(exc)),
            stdout_truncated=False,
            stderr_truncated=False,
            command_hash=command_hash,
            subprocess_started=False,
        )

    stdout_preview, stdout_truncated = _bounded_text(completed.stdout, max_output)
    stderr_preview, stderr_truncated = _bounded_text(completed.stderr, max_output)
    if stdout_truncated or stderr_truncated:
        return GitCommandEvidence(
            command_id=command_id.value,
            status=GIT_READ_COMMAND_ERROR,
            reason_code=GIT_READ_BLOCKED_OUTPUT_LIMIT,
            exit_code=completed.returncode,
            timeout_expired=False,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            command_hash=command_hash,
            subprocess_started=True,
        )
    if completed.returncode != 0:
        return GitCommandEvidence(
            command_id=command_id.value,
            status=GIT_READ_COMMAND_ERROR,
            reason_code=GIT_READ_ERROR_EXIT_CODE,
            exit_code=completed.returncode,
            timeout_expired=False,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            stdout_truncated=False,
            stderr_truncated=False,
            command_hash=command_hash,
            subprocess_started=True,
        )
    return GitCommandEvidence(
        command_id=command_id.value,
        status=GIT_READ_COMMAND_PASS,
        reason_code=GIT_READ_READY_EVIDENCE_ONLY,
        exit_code=completed.returncode,
        timeout_expired=False,
        stdout_preview=stdout_preview,
        stderr_preview=stderr_preview,
        stdout_truncated=False,
        stderr_truncated=False,
        command_hash=command_hash,
        subprocess_started=True,
    )


def read_local_git_state(request: GitReadRequest) -> GitReadResult:
    workspace = validate_git_workspace_root(request.workspace_root)
    if workspace.status != GIT_READ_READY or workspace.repo_root is None:
        return workspace

    toplevel = run_allowlisted_git_read(request, GitReadCommand.SHOW_TOPLEVEL)
    if toplevel.status != GIT_READ_COMMAND_PASS:
        return _command_failure_result(workspace.repo_root, (toplevel,), "Git repository root could not be read.")

    repo_root = _single_line(toplevel.stdout_preview)
    if not repo_root:
        return _command_failure_result(workspace.repo_root, (toplevel,), "Git repository root output was empty.")

    resolved_workspace = Path(workspace.repo_root).resolve(strict=True)
    try:
        resolved_repo = Path(repo_root).resolve(strict=True)
    except OSError:
        return _command_failure_result(workspace.repo_root, (toplevel,), "Git repository root could not be resolved.")

    if not _is_relative_to(resolved_repo, resolved_workspace):
        return _result(
            status=GIT_READ_BLOCKED,
            repo_root=str(resolved_repo),
            head_sha=None,
            branch_name=None,
            detached_head=False,
            clean=None,
            staged_paths=(),
            unstaged_paths=(),
            untracked_paths=(),
            command_evidence=(toplevel,),
            reason_codes=(GIT_READ_BLOCKED_REPO_ROOT_OUTSIDE_WORKSPACE,),
            reason="Git repository root is outside the validated workspace root.",
        )

    evidence = [
        toplevel,
        run_allowlisted_git_read(request, GitReadCommand.VERIFY_HEAD),
        run_allowlisted_git_read(request, GitReadCommand.BRANCH_NAME),
        run_allowlisted_git_read(request, GitReadCommand.STATUS_PORCELAIN),
        run_allowlisted_git_read(request, GitReadCommand.DIFF_NAME_STATUS),
        run_allowlisted_git_read(request, GitReadCommand.DIFF_CACHED_NAME_STATUS),
        run_allowlisted_git_read(request, GitReadCommand.LS_FILES_OTHERS),
    ]
    failed = tuple(item for item in evidence if item.status != GIT_READ_COMMAND_PASS)
    if failed:
        return _command_failure_result(str(resolved_repo), tuple(evidence), "One or more Git read commands failed.")

    head_sha = _single_line(evidence[1].stdout_preview)
    if not _is_hex_sha(head_sha):
        return _result(
            status=GIT_READ_ERROR,
            repo_root=str(resolved_repo),
            head_sha=None,
            branch_name=None,
            detached_head=False,
            clean=None,
            staged_paths=(),
            unstaged_paths=(),
            untracked_paths=(),
            command_evidence=tuple(evidence),
            reason_codes=(GIT_READ_ERROR_MALFORMED_HEAD,),
            reason="Git HEAD output was not a valid commit hash.",
        )

    branch_output = _single_line(evidence[2].stdout_preview)
    detached = branch_output == "HEAD"
    branch_name = None if detached else branch_output
    status_paths = _parse_porcelain_paths(evidence[3].stdout_preview)
    unstaged_paths = _merge_paths(status_paths["unstaged"], _parse_name_status_paths(evidence[4].stdout_preview))
    staged_paths = _merge_paths(status_paths["staged"], _parse_name_status_paths(evidence[5].stdout_preview))
    untracked_paths = _merge_paths(status_paths["untracked"], _safe_lines(evidence[6].stdout_preview))
    clean = not staged_paths and not unstaged_paths and not untracked_paths
    return _result(
        status=GIT_READ_READY,
        repo_root=str(resolved_repo),
        head_sha=head_sha,
        branch_name=branch_name,
        detached_head=detached,
        clean=clean,
        staged_paths=staged_paths,
        unstaged_paths=unstaged_paths,
        untracked_paths=untracked_paths,
        command_evidence=tuple(evidence),
        reason_codes=(GIT_READ_READY_EVIDENCE_ONLY,),
        reason="Local Git state read is deterministic evidence only and grants no authority.",
    )


def _command_failure_result(repo_root: str | None, evidence: tuple[GitCommandEvidence, ...], reason: str) -> GitReadResult:
    reason_codes = tuple(item.reason_code for item in evidence if item.status != GIT_READ_COMMAND_PASS)
    status = GIT_READ_ERROR if any(item.reason_code == GIT_READ_ERROR_TIMEOUT for item in evidence) else GIT_READ_BLOCKED
    return _result(
        status=status,
        repo_root=repo_root,
        head_sha=None,
        branch_name=None,
        detached_head=False,
        clean=None,
        staged_paths=(),
        unstaged_paths=(),
        untracked_paths=(),
        command_evidence=evidence,
        reason_codes=reason_codes or (GIT_READ_ERROR_EXIT_CODE,),
        reason=reason,
    )


def _result(
    *,
    status: str,
    repo_root: str | None,
    head_sha: str | None,
    branch_name: str | None,
    detached_head: bool,
    clean: bool | None,
    staged_paths: tuple[str, ...],
    unstaged_paths: tuple[str, ...],
    untracked_paths: tuple[str, ...],
    command_evidence: tuple[GitCommandEvidence, ...],
    reason_codes: tuple[str, ...],
    reason: str,
) -> GitReadResult:
    material = {
        "schema_version": _SCHEMA_VERSION,
        "status": status,
        "repo_root": repo_root,
        "head_sha": head_sha,
        "branch_name": branch_name,
        "detached_head": detached_head,
        "clean": clean,
        "staged_paths": staged_paths,
        "unstaged_paths": unstaged_paths,
        "untracked_paths": untracked_paths,
        "command_evidence": tuple(item.to_dict() for item in command_evidence),
        "reason_codes": reason_codes,
        "reason": reason,
        "authority": {field_name: False for field_name in _AUTHORITY_FIELDS},
    }
    return GitReadResult(
        status=status,
        git_read_hash=compute_git_read_hash(material),
        repo_root=repo_root,
        head_sha=head_sha,
        branch_name=branch_name,
        detached_head=detached_head,
        clean=clean,
        staged_paths=staged_paths,
        unstaged_paths=unstaged_paths,
        untracked_paths=untracked_paths,
        command_evidence=command_evidence,
        reason_codes=reason_codes,
        reason=reason,
    )


def _command_blocked(command_id: str, reason_code: str) -> GitCommandEvidence:
    return GitCommandEvidence(
        command_id=sanitize_git_output(command_id),
        status=GIT_READ_COMMAND_BLOCKED,
        reason_code=reason_code,
        exit_code=None,
        timeout_expired=False,
        stdout_preview="",
        stderr_preview="",
        stdout_truncated=False,
        stderr_truncated=False,
        command_hash=compute_git_read_hash({"command_id": command_id, "blocked": reason_code}),
        subprocess_started=False,
    )


def _bounded_text(value: str | bytes | None, max_output_bytes: int) -> tuple[str, bool]:
    if value is None:
        return "", False
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    sanitized = sanitize_git_output(text)
    encoded = sanitized.encode("utf-8")
    if len(encoded) <= max_output_bytes:
        return sanitized, False
    truncated = encoded[:max_output_bytes].decode("utf-8", errors="ignore")
    return sanitize_git_output(truncated), True


def _clamp_timeout(value: int) -> int:
    if not isinstance(value, int):
        return _DEFAULT_TIMEOUT_SECONDS
    return max(_MIN_TIMEOUT_SECONDS, min(value, _MAX_TIMEOUT_SECONDS))


def _clamp_output_bytes(value: int) -> int:
    if not isinstance(value, int):
        return _DEFAULT_MAX_OUTPUT_BYTES
    return max(_MIN_OUTPUT_BYTES, min(value, _MAX_OUTPUT_BYTES))


def _single_line(value: str) -> str:
    lines = _safe_lines(value)
    return lines[0] if lines else ""


def _safe_lines(value: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in sanitize_git_output(value).splitlines() if line.strip())


def _parse_porcelain_paths(value: str) -> dict[str, tuple[str, ...]]:
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in _safe_lines(value):
        if len(line) < 4:
            continue
        code = line[:2]
        path = _sanitize_status_path(line[3:])
        if code == "??":
            untracked.append(path)
            continue
        if code[0] != " ":
            staged.append(path)
        if code[1] != " ":
            unstaged.append(path)
    return {
        "staged": _dedupe(staged),
        "unstaged": _dedupe(unstaged),
        "untracked": _dedupe(untracked),
    }


def _parse_name_status_paths(value: str) -> tuple[str, ...]:
    paths: list[str] = []
    for line in _safe_lines(value):
        parts = line.split("\t")
        if len(parts) >= 2:
            paths.append(_sanitize_status_path(parts[-1]))
    return _dedupe(paths)


def _sanitize_status_path(path: str) -> str:
    cleaned = sanitize_git_output(path).strip()
    if " -> " in cleaned:
        cleaned = cleaned.split(" -> ", 1)[1].strip()
    return cleaned


def _merge_paths(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        merged.extend(group)
    return _dedupe(merged)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _is_hex_sha(value: str) -> bool:
    return len(value) in (40, 64) and all(char in _HEX for char in value.lower())


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_no_path_argument(value: str | None) -> str | None:
    if value is None:
        return None
    if value.strip():
        return GIT_READ_BLOCKED_UNSAFE_PATH_ARGUMENT
    return None


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
