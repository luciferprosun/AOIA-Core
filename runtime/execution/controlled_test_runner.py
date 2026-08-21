from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.safety.subprocess_env import build_subprocess_env
from runtime.safety.bounded_subprocess import (
    SubprocessContainmentError,
    SubprocessResourceLimitError,
    SubprocessResourceProfileName,
    run_bounded_subprocess,
)


CONTROLLED_TEST_EXECUTION_SCHEMA_VERSION = "AOIA_CONTROLLED_TEST_EXECUTION_1A"
_DEFAULT_TIMEOUT_SECONDS = 30
_MAX_TIMEOUT_SECONDS = 300
_DEFAULT_MAX_OUTPUT_BYTES = 20000
_MINIMAL_ENV = {
    "PYTHONPATH": "runtime:.",
    "PYTHONNOUSERSITE": "1",
}
_CONTROLLED_PYCACHE_PREFIX = "aoia-controlled-test-pycache-"


class ControlledTestExecutionStatus(str, Enum):
    CONTROLLED_TEST_EXECUTION_COMPLETED = "CONTROLLED_TEST_EXECUTION_COMPLETED"
    CONTROLLED_TEST_EXECUTION_FAILED = "CONTROLLED_TEST_EXECUTION_FAILED"
    CONTROLLED_TEST_EXECUTION_TIMEOUT = "CONTROLLED_TEST_EXECUTION_TIMEOUT"
    BLOCKED_UNCONFIRMED_EXECUTION = "BLOCKED_UNCONFIRMED_EXECUTION"
    BLOCKED_UNTRUSTED_SOURCE = "BLOCKED_UNTRUSTED_SOURCE"
    BLOCKED_UNSAFE_COMMAND = "BLOCKED_UNSAFE_COMMAND"
    BLOCKED_UNSUPPORTED_COMMAND = "BLOCKED_UNSUPPORTED_COMMAND"
    BLOCKED_INVALID_SANDBOX_ENVELOPE = "BLOCKED_INVALID_SANDBOX_ENVELOPE"
    BLOCKED_INVALID_TEST_CONTROLLER_PREVIEW = "BLOCKED_INVALID_TEST_CONTROLLER_PREVIEW"
    BLOCKED_MISSING_EXECUTION_BARRIER = "BLOCKED_MISSING_EXECUTION_BARRIER"
    BLOCKED_EXECUTION_BARRIER_NOT_PASSED = "BLOCKED_EXECUTION_BARRIER_NOT_PASSED"
    BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH = "BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH"
    BLOCKED_EXECUTION_BARRIER_STALE_OR_INVALID = "BLOCKED_EXECUTION_BARRIER_STALE_OR_INVALID"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INTERNAL_EXECUTION_ERROR = "INTERNAL_EXECUTION_ERROR"


class ControlledTestExecutionFlag(str, Enum):
    CONTROLLED_TEST_EXECUTION_ONLY = "CONTROLLED_TEST_EXECUTION_ONLY"
    NO_SHELL = "NO_SHELL"
    NO_ARBITRARY_COMMAND = "NO_ARBITRARY_COMMAND"
    NO_BROWSER = "NO_BROWSER"
    NO_DOWNLOAD = "NO_DOWNLOAD"
    NO_PROVIDER_CALL = "NO_PROVIDER_CALL"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_GIT_WRITE = "NO_GIT_WRITE"
    NO_CONTROL_WRITE = "NO_CONTROL_WRITE"
    NO_APPROVAL_MUTATION = "NO_APPROVAL_MUTATION"
    OPERATOR_CONFIRMATION_REQUIRED = "OPERATOR_CONFIRMATION_REQUIRED"
    OPERATOR_CONFIRMED = "OPERATOR_CONFIRMED"
    SOURCE_TRUST_REQUIRED = "SOURCE_TRUST_REQUIRED"
    UNTRUSTED_SOURCE_BLOCKED = "UNTRUSTED_SOURCE_BLOCKED"
    SANDBOX_ENVELOPE_REQUIRED = "SANDBOX_ENVELOPE_REQUIRED"
    TEST_CONTROLLER_PREVIEW_REQUIRED = "TEST_CONTROLLER_PREVIEW_REQUIRED"
    ALLOWLISTED_UNITTEST_FOCUSED = "ALLOWLISTED_UNITTEST_FOCUSED"
    ALLOWLISTED_UNITTEST_DISCOVER = "ALLOWLISTED_UNITTEST_DISCOVER"
    ALLOWLISTED_COMPILEALL = "ALLOWLISTED_COMPILEALL"
    UNSUPPORTED_COMMAND_BLOCKED = "UNSUPPORTED_COMMAND_BLOCKED"
    UNSAFE_COMMAND_BLOCKED = "UNSAFE_COMMAND_BLOCKED"
    OUTPUT_BOUNDED = "OUTPUT_BOUNDED"
    TIMEOUT_ENFORCED = "TIMEOUT_ENFORCED"
    SANDBOX_METADATA_ACCEPTED = "SANDBOX_METADATA_ACCEPTED"
    TEST_CONTROLLER_METADATA_ACCEPTED = "TEST_CONTROLLER_METADATA_ACCEPTED"
    POLICY_METADATA_ONLY = "POLICY_METADATA_ONLY"
    HUMAN_EXECUTION_BARRIER_REQUIRED = "HUMAN_EXECUTION_BARRIER_REQUIRED"
    HUMAN_EXECUTION_BARRIER_PRESENT = "HUMAN_EXECUTION_BARRIER_PRESENT"
    HUMAN_EXECUTION_BARRIER_VERIFIED = "HUMAN_EXECUTION_BARRIER_VERIFIED"
    HUMAN_EXECUTION_BARRIER_HASH_BOUND = "HUMAN_EXECUTION_BARRIER_HASH_BOUND"
    HUMAN_EXECUTION_BARRIER_MISSING = "HUMAN_EXECUTION_BARRIER_MISSING"
    HUMAN_EXECUTION_BARRIER_NOT_PASSED = "HUMAN_EXECUTION_BARRIER_NOT_PASSED"
    HUMAN_EXECUTION_BARRIER_HASH_MISMATCH = "HUMAN_EXECUTION_BARRIER_HASH_MISMATCH"
    NO_BARRIER_BYPASS = "NO_BARRIER_BYPASS"
    INTERNAL_EXECUTION_ERROR = "INTERNAL_EXECUTION_ERROR"


class ControlledTestCommandKind(str, Enum):
    UNITTEST_FOCUSED = "UNITTEST_FOCUSED"
    UNITTEST_DISCOVER = "UNITTEST_DISCOVER"
    COMPILEALL = "COMPILEALL"
    UNKNOWN = "UNKNOWN"


class ControlledTestSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    CRITIC_METADATA = "CRITIC_METADATA"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ControlledTestExecutionRequest:
    requested_command: str
    repo_root: str
    explicit_operator_execution_confirmed: bool
    command_kind: ControlledTestCommandKind | str = ControlledTestCommandKind.UNKNOWN
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    max_output_bytes: int = _DEFAULT_MAX_OUTPUT_BYTES
    source_trust: ControlledTestSourceTrust | str = ControlledTestSourceTrust.UNKNOWN
    source_test_runner_control_id: str | None = None
    source_test_runner_control_hash: str | None = None
    source_test_runner_control_status: str | None = None
    source_sandbox_envelope_id: str | None = None
    source_sandbox_envelope_hash: str | None = None
    source_sandbox_envelope_status: str | None = None
    source_policy_check_id: str | None = None
    source_policy_check_hash: str | None = None
    source_execution_barrier_id: str | None = None
    source_execution_barrier_hash: str | None = None
    source_execution_barrier_status: str | None = None
    source_execution_barrier_passed: bool = False
    barrier_bound_command_hash: str | None = None
    barrier_bound_test_runner_control_hash: str | None = None
    barrier_bound_sandbox_envelope_hash: str | None = None
    barrier_bound_policy_check_hash: str | None = None
    source_human_decision_id: str | None = None
    source_human_decision_hash: str | None = None
    human_review_required: bool = True
    risk_flags: tuple[str, ...] | list[str] = ()
    schema_version: str = CONTROLLED_TEST_EXECUTION_SCHEMA_VERSION


@dataclass(frozen=True)
class ControlledTestExecutionResult:
    schema_version: str
    execution_result_id: str
    execution_result_hash: str
    status: ControlledTestExecutionStatus
    command_kind: ControlledTestCommandKind
    requested_command: str
    normalized_command: str
    executed_args_preview: tuple[str, ...]
    repo_root: str
    exit_code: int | None
    timeout_seconds: int
    timeout_expired: bool
    stdout_preview: str
    stderr_preview: str
    stdout_truncated: bool
    stderr_truncated: bool
    source_test_runner_control_id: str | None
    source_test_runner_control_hash: str | None
    source_sandbox_envelope_id: str | None
    source_sandbox_envelope_hash: str | None
    source_policy_check_id: str | None
    source_policy_check_hash: str | None
    source_execution_barrier_id: str | None
    source_execution_barrier_hash: str | None
    source_execution_barrier_status: str | None
    source_execution_barrier_passed: bool
    source_human_decision_id: str | None
    source_human_decision_hash: str | None
    barrier_verified: bool
    barrier_hashes_matched: bool
    flags: tuple[ControlledTestExecutionFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    execution_performed: bool = False
    subprocess_started: bool = False
    shell_invoked: bool = False
    command_executed: bool = False
    test_command_executed: bool = False
    browser_opened: bool = False
    download_performed: bool = False
    file_written_by_aoia: bool = False
    network_called_by_aoia: bool = False
    env_read: bool = False
    api_key_loaded: bool = False
    provider_called: bool = False
    approval_created: bool = False
    gate_changed: bool = False
    control_write_changed: bool = False
    tool_called: bool = False
    can_call_tool: bool = False
    can_execute_arbitrary_command: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_change_approval_gate: bool = False
    can_change_policy: bool = False
    can_access_network: bool = False
    can_read_env: bool = False
    can_load_api_key: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text("schema_version", self.schema_version))
        object.__setattr__(self, "execution_result_id", _text("execution_result_id", self.execution_result_id))
        object.__setattr__(self, "execution_result_hash", _text("execution_result_hash", self.execution_result_hash))
        object.__setattr__(self, "status", ControlledTestExecutionStatus(self.status))
        object.__setattr__(self, "command_kind", ControlledTestCommandKind(self.command_kind))
        object.__setattr__(self, "requested_command", _text("requested_command", self.requested_command))
        object.__setattr__(self, "normalized_command", _text("normalized_command", self.normalized_command))
        object.__setattr__(self, "executed_args_preview", _text_tuple("executed_args_preview", self.executed_args_preview))
        object.__setattr__(self, "repo_root", _text("repo_root", self.repo_root))
        object.__setattr__(self, "timeout_seconds", _hard_timeout_seconds(self.timeout_seconds))
        object.__setattr__(self, "timeout_expired", bool(self.timeout_expired))
        object.__setattr__(self, "stdout_preview", _text("stdout_preview", self.stdout_preview))
        object.__setattr__(self, "stderr_preview", _text("stderr_preview", self.stderr_preview))
        object.__setattr__(self, "stdout_truncated", bool(self.stdout_truncated))
        object.__setattr__(self, "stderr_truncated", bool(self.stderr_truncated))
        object.__setattr__(self, "source_test_runner_control_id", _optional_text(self.source_test_runner_control_id))
        object.__setattr__(self, "source_test_runner_control_hash", _optional_text(self.source_test_runner_control_hash))
        object.__setattr__(self, "source_sandbox_envelope_id", _optional_text(self.source_sandbox_envelope_id))
        object.__setattr__(self, "source_sandbox_envelope_hash", _optional_text(self.source_sandbox_envelope_hash))
        object.__setattr__(self, "source_policy_check_id", _optional_text(self.source_policy_check_id))
        object.__setattr__(self, "source_policy_check_hash", _optional_text(self.source_policy_check_hash))
        object.__setattr__(self, "source_execution_barrier_id", _optional_text(self.source_execution_barrier_id))
        object.__setattr__(self, "source_execution_barrier_hash", _optional_text(self.source_execution_barrier_hash))
        object.__setattr__(self, "source_execution_barrier_status", _optional_text(self.source_execution_barrier_status))
        object.__setattr__(self, "source_execution_barrier_passed", bool(self.source_execution_barrier_passed))
        object.__setattr__(self, "source_human_decision_id", _optional_text(self.source_human_decision_id))
        object.__setattr__(self, "source_human_decision_hash", _optional_text(self.source_human_decision_hash))
        barrier_verified = self.status in {
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
        }
        object.__setattr__(self, "barrier_verified", barrier_verified)
        object.__setattr__(self, "barrier_hashes_matched", barrier_verified)
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "display_summary", _bounded_text(_text("display_summary", self.display_summary), 420))
        attempted = self.status in {
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
        }
        object.__setattr__(self, "execution_performed", attempted)
        object.__setattr__(self, "subprocess_started", attempted)
        object.__setattr__(self, "command_executed", attempted and not self.timeout_expired)
        object.__setattr__(self, "test_command_executed", attempted and not self.timeout_expired)
        for field_name in (
            "shell_invoked",
            "browser_opened",
            "download_performed",
            "file_written_by_aoia",
            "network_called_by_aoia",
            "env_read",
            "api_key_loaded",
            "provider_called",
            "approval_created",
            "gate_changed",
            "control_write_changed",
            "tool_called",
            "can_call_tool",
            "can_execute_arbitrary_command",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "execution_result_id": self.execution_result_id,
            "execution_result_hash": self.execution_result_hash,
            "status": self.status.value,
            "command_kind": self.command_kind.value,
            "requested_command": self.requested_command,
            "normalized_command": self.normalized_command,
            "executed_args_preview": list(self.executed_args_preview),
            "repo_root": self.repo_root,
            "exit_code": self.exit_code,
            "timeout_seconds": self.timeout_seconds,
            "timeout_expired": self.timeout_expired,
            "stdout_preview": self.stdout_preview,
            "stderr_preview": self.stderr_preview,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "source_test_runner_control_id": self.source_test_runner_control_id,
            "source_test_runner_control_hash": self.source_test_runner_control_hash,
            "source_sandbox_envelope_id": self.source_sandbox_envelope_id,
            "source_sandbox_envelope_hash": self.source_sandbox_envelope_hash,
            "source_policy_check_id": self.source_policy_check_id,
            "source_policy_check_hash": self.source_policy_check_hash,
            "source_execution_barrier_id": self.source_execution_barrier_id,
            "source_execution_barrier_hash": self.source_execution_barrier_hash,
            "source_execution_barrier_status": self.source_execution_barrier_status,
            "source_execution_barrier_passed": self.source_execution_barrier_passed,
            "source_human_decision_id": self.source_human_decision_id,
            "source_human_decision_hash": self.source_human_decision_hash,
            "barrier_verified": self.barrier_verified,
            "barrier_hashes_matched": self.barrier_hashes_matched,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "display_summary": self.display_summary,
            "execution_performed": self.execution_performed,
            "subprocess_started": self.subprocess_started,
            "shell_invoked": self.shell_invoked,
            "command_executed": self.command_executed,
            "test_command_executed": self.test_command_executed,
            "browser_opened": self.browser_opened,
            "download_performed": self.download_performed,
            "file_written_by_aoia": self.file_written_by_aoia,
            "network_called_by_aoia": self.network_called_by_aoia,
            "env_read": self.env_read,
            "api_key_loaded": self.api_key_loaded,
            "provider_called": self.provider_called,
            "approval_created": self.approval_created,
            "gate_changed": self.gate_changed,
            "control_write_changed": self.control_write_changed,
            "tool_called": self.tool_called,
            "can_call_tool": self.can_call_tool,
            "can_execute_arbitrary_command": self.can_execute_arbitrary_command,
            "can_write": self.can_write,
            "can_commit": self.can_commit,
            "can_change_approval_gate": self.can_change_approval_gate,
            "can_change_policy": self.can_change_policy,
            "can_access_network": self.can_access_network,
            "can_read_env": self.can_read_env,
            "can_load_api_key": self.can_load_api_key,
        }


def _validated_external_temp_parent(repo_root: str) -> Path:
    repository = Path(repo_root).resolve(strict=True)
    temp_parent = Path(tempfile.gettempdir())
    if not temp_parent.is_absolute() or temp_parent.is_symlink():
        raise ValueError("controlled test temporary parent must be an absolute non-symlink path")
    resolved_parent = temp_parent.resolve(strict=True)
    if not resolved_parent.is_dir():
        raise ValueError("controlled test temporary parent must be a directory")
    if resolved_parent == repository or repository in resolved_parent.parents:
        raise ValueError("controlled test temporary parent must be outside the repository")
    return resolved_parent


def _build_controlled_child_environment(*, repo_root: str, pycache_root: str) -> dict[str, str]:
    repository = Path(repo_root).resolve(strict=True)
    cache_path = Path(pycache_root)
    if not cache_path.is_absolute() or cache_path.is_symlink():
        raise ValueError("controlled child pycache root must be an absolute non-symlink path")
    resolved_cache = cache_path.resolve(strict=True)
    if not resolved_cache.is_dir():
        raise ValueError("controlled child pycache root must be a directory")
    if resolved_cache == repository or repository in resolved_cache.parents:
        raise ValueError("controlled child pycache root must be outside the repository")
    return build_subprocess_env(
        inherit_names=(),
        fixed={
            **_MINIMAL_ENV,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(resolved_cache),
        },
    )


def execute_controlled_test_run(request: ControlledTestExecutionRequest) -> ControlledTestExecutionResult:
    if not isinstance(request, ControlledTestExecutionRequest):
        return _blocked_result(
            request_data=_empty_request_data(),
            status=ControlledTestExecutionStatus.MALFORMED_REQUEST,
            command_kind=ControlledTestCommandKind.UNKNOWN,
            flags={ControlledTestExecutionFlag.UNSUPPORTED_COMMAND_BLOCKED},
            risk_notes=("Malformed ControlledTestExecutionRequest input.",),
        )

    try:
        request_data = _request_data(request)
    except (TypeError, ValueError):
        return _blocked_result(
            request_data=_empty_request_data(),
            status=ControlledTestExecutionStatus.MALFORMED_REQUEST,
            command_kind=ControlledTestCommandKind.UNKNOWN,
            flags={ControlledTestExecutionFlag.UNSUPPORTED_COMMAND_BLOCKED},
            risk_notes=("Request metadata was malformed or non-deterministic.",),
        )

    command_kind, args, command_flags, command_notes = _allowlisted_args(request_data["normalized_command"])
    flags = set(command_flags)
    risk_notes = list(command_notes)

    if not request_data["explicit_operator_execution_confirmed"]:
        return _blocked_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.BLOCKED_UNCONFIRMED_EXECUTION,
            command_kind=command_kind,
            flags=flags | {ControlledTestExecutionFlag.OPERATOR_CONFIRMATION_REQUIRED},
            risk_notes=tuple(risk_notes + ["Explicit local operator execution confirmation is required."]),
            executed_args=args,
        )
    flags.add(ControlledTestExecutionFlag.OPERATOR_CONFIRMED)

    if _provider_untrusted(request_data["source_trust"]):
        return _blocked_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.BLOCKED_UNTRUSTED_SOURCE,
            command_kind=command_kind,
            flags=flags | {ControlledTestExecutionFlag.UNTRUSTED_SOURCE_BLOCKED},
            risk_notes=tuple(risk_notes + ["Provider or model output cannot authorize controlled test execution."]),
            executed_args=args,
        )
    flags.add(ControlledTestExecutionFlag.SOURCE_TRUST_REQUIRED)

    if not _valid_test_controller_metadata(request_data):
        return _blocked_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.BLOCKED_INVALID_TEST_CONTROLLER_PREVIEW,
            command_kind=command_kind,
            flags=flags | {ControlledTestExecutionFlag.TEST_CONTROLLER_PREVIEW_REQUIRED},
            risk_notes=tuple(risk_notes + ["Valid test-runner controller preview metadata is required."]),
            executed_args=args,
        )
    flags.add(ControlledTestExecutionFlag.TEST_CONTROLLER_METADATA_ACCEPTED)

    if not _valid_sandbox_metadata(request_data):
        return _blocked_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.BLOCKED_INVALID_SANDBOX_ENVELOPE,
            command_kind=command_kind,
            flags=flags | {ControlledTestExecutionFlag.SANDBOX_ENVELOPE_REQUIRED},
            risk_notes=tuple(risk_notes + ["Valid safe-execution sandbox envelope metadata is required."]),
            executed_args=args,
        )
    flags.add(ControlledTestExecutionFlag.SANDBOX_METADATA_ACCEPTED)

    if _unsafe_command(request_data["normalized_command"]):
        return _blocked_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.BLOCKED_UNSAFE_COMMAND,
            command_kind=command_kind,
            flags=flags | {ControlledTestExecutionFlag.UNSAFE_COMMAND_BLOCKED},
            risk_notes=tuple(risk_notes + ["Unsafe command pattern was blocked before execution."]),
            executed_args=args,
        )

    if not args:
        return _blocked_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.BLOCKED_UNSUPPORTED_COMMAND,
            command_kind=command_kind,
            flags=flags | {ControlledTestExecutionFlag.UNSUPPORTED_COMMAND_BLOCKED},
            risk_notes=tuple(risk_notes + ["Command is not in the controlled local Python test allowlist."]),
            executed_args=args,
        )

    barrier_status, barrier_flags, barrier_notes = _barrier_status(request_data)
    flags |= barrier_flags
    risk_notes.extend(barrier_notes)
    if barrier_status is not None:
        return _blocked_result(
            request_data=request_data,
            status=barrier_status,
            command_kind=command_kind,
            flags=flags,
            risk_notes=tuple(risk_notes),
            executed_args=args,
        )
    flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_VERIFIED)
    flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_HASH_BOUND)

    try:
        temp_parent = _validated_external_temp_parent(request_data["repo_root"])
        with tempfile.TemporaryDirectory(prefix=_CONTROLLED_PYCACHE_PREFIX, dir=temp_parent) as pycache_root:
            completed = run_bounded_subprocess(
                args,
                cwd=request_data["repo_root"],
                env=_build_controlled_child_environment(
                    repo_root=request_data["repo_root"],
                    pycache_root=pycache_root,
                ),
                timeout=request_data["timeout_seconds"],
                resource_profile=SubprocessResourceProfileName.CONTROLLED_TEST,
                capture_output=True,
                text=True,
                shell=False,
            )
    except subprocess.TimeoutExpired as exc:
        stdout_preview, stdout_truncated = _bound_output(_timeout_output(exc.stdout), request_data["max_output_bytes"])
        stderr_preview, stderr_truncated = _bound_output(_timeout_output(exc.stderr), request_data["max_output_bytes"])
        stdout_truncated = stdout_truncated or getattr(exc, "stdout_truncated", False)
        stderr_truncated = stderr_truncated or getattr(exc, "stderr_truncated", False)
        return _execution_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            command_kind=command_kind,
            executed_args=args,
            exit_code=None,
            timeout_expired=True,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            flags=flags,
            risk_notes=tuple(risk_notes + ["Controlled test execution timed out."]),
        )
    except (SubprocessResourceLimitError, SubprocessContainmentError) as exc:
        stdout_preview, stdout_truncated = _bound_output(
            getattr(exc, "stdout", None), request_data["max_output_bytes"]
        )
        stderr_preview, stderr_truncated = _bound_output(
            getattr(exc, "stderr", None), request_data["max_output_bytes"]
        )
        stdout_truncated = stdout_truncated or getattr(exc, "stdout_truncated", False)
        stderr_truncated = stderr_truncated or getattr(exc, "stderr_truncated", False)
        return _execution_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            command_kind=command_kind,
            executed_args=args,
            exit_code=getattr(exc, "returncode", None),
            timeout_expired=False,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            flags=flags,
            risk_notes=tuple(risk_notes + [f"Process containment reason: {exc.reason_code}."]),
        )
    except Exception as exc:
        stderr_preview, stderr_truncated = _bound_output(type(exc).__name__, request_data["max_output_bytes"])
        return _execution_result(
            request_data=request_data,
            status=ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
            command_kind=command_kind,
            executed_args=args,
            exit_code=None,
            timeout_expired=False,
            stdout_preview="",
            stderr_preview=stderr_preview,
            stdout_truncated=False,
            stderr_truncated=stderr_truncated,
            flags=flags | {ControlledTestExecutionFlag.INTERNAL_EXECUTION_ERROR},
            risk_notes=tuple(risk_notes + ["Controlled test execution adapter caught an internal execution error."]),
        )

    stdout_preview, stdout_truncated = _bound_output(completed.stdout, request_data["max_output_bytes"])
    stderr_preview, stderr_truncated = _bound_output(completed.stderr, request_data["max_output_bytes"])
    stdout_truncated = stdout_truncated or getattr(completed, "stdout_truncated", False)
    stderr_truncated = stderr_truncated or getattr(completed, "stderr_truncated", False)
    status = (
        ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED
        if completed.returncode == 0
        else ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED
    )
    return _execution_result(
        request_data=request_data,
        status=status,
        command_kind=command_kind,
        executed_args=args,
        exit_code=completed.returncode,
        timeout_expired=False,
        stdout_preview=stdout_preview,
        stderr_preview=stderr_preview,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _blocked_result(
    *,
    request_data: dict[str, Any],
    status: ControlledTestExecutionStatus,
    command_kind: ControlledTestCommandKind,
    flags: set[ControlledTestExecutionFlag],
    risk_notes: tuple[str, ...],
    executed_args: tuple[str, ...] = (),
) -> ControlledTestExecutionResult:
    return _execution_result(
        request_data=request_data,
        status=status,
        command_kind=command_kind,
        executed_args=executed_args,
        exit_code=None,
        timeout_expired=False,
        stdout_preview="",
        stderr_preview="",
        stdout_truncated=False,
        stderr_truncated=False,
        flags=flags,
        risk_notes=risk_notes,
    )


def _execution_result(
    *,
    request_data: dict[str, Any],
    status: ControlledTestExecutionStatus,
    command_kind: ControlledTestCommandKind,
    executed_args: tuple[str, ...],
    exit_code: int | None,
    timeout_expired: bool,
    stdout_preview: str,
    stderr_preview: str,
    stdout_truncated: bool,
    stderr_truncated: bool,
    flags: set[ControlledTestExecutionFlag],
    risk_notes: tuple[str, ...],
) -> ControlledTestExecutionResult:
    base_flags = {
        ControlledTestExecutionFlag.CONTROLLED_TEST_EXECUTION_ONLY,
        ControlledTestExecutionFlag.NO_SHELL,
        ControlledTestExecutionFlag.NO_ARBITRARY_COMMAND,
        ControlledTestExecutionFlag.NO_BROWSER,
        ControlledTestExecutionFlag.NO_DOWNLOAD,
        ControlledTestExecutionFlag.NO_PROVIDER_CALL,
        ControlledTestExecutionFlag.NO_API_KEY_ACCESS,
        ControlledTestExecutionFlag.NO_ENV_ACCESS,
        ControlledTestExecutionFlag.NO_GIT_WRITE,
        ControlledTestExecutionFlag.NO_CONTROL_WRITE,
        ControlledTestExecutionFlag.NO_APPROVAL_MUTATION,
        ControlledTestExecutionFlag.OUTPUT_BOUNDED,
        ControlledTestExecutionFlag.TIMEOUT_ENFORCED,
        ControlledTestExecutionFlag.POLICY_METADATA_ONLY,
        ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_REQUIRED,
        ControlledTestExecutionFlag.NO_BARRIER_BYPASS,
    }
    all_flags = base_flags | set(flags)
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    normalized_command = request_data["normalized_command"]
    stable_payload = {
        "schema_version": CONTROLLED_TEST_EXECUTION_SCHEMA_VERSION,
        "status": status.value,
        "command_kind": command_kind.value,
        "requested_command": request_data["requested_command"],
        "normalized_command": normalized_command,
        "command_hash": request_data["command_hash"],
        "executed_args_preview": list(executed_args),
        "repo_root": request_data["repo_root"],
        "exit_code": exit_code,
        "timeout_seconds": request_data["timeout_seconds"],
        "timeout_expired": timeout_expired,
        "stdout_preview": stdout_preview,
        "stderr_preview": stderr_preview,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "source_test_runner_control_id": request_data["source_test_runner_control_id"],
        "source_test_runner_control_hash": request_data["source_test_runner_control_hash"],
        "source_sandbox_envelope_id": request_data["source_sandbox_envelope_id"],
        "source_sandbox_envelope_hash": request_data["source_sandbox_envelope_hash"],
        "source_policy_check_id": request_data["source_policy_check_id"],
        "source_policy_check_hash": request_data["source_policy_check_hash"],
        "source_execution_barrier_id": request_data["source_execution_barrier_id"],
        "source_execution_barrier_hash": request_data["source_execution_barrier_hash"],
        "source_execution_barrier_status": request_data["source_execution_barrier_status"],
        "source_execution_barrier_passed": request_data["source_execution_barrier_passed"],
        "source_human_decision_id": request_data["source_human_decision_id"],
        "source_human_decision_hash": request_data["source_human_decision_hash"],
        "barrier_verified": status
        in {
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
        },
        "barrier_hashes_matched": status
        in {
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
        },
        "flags": [flag.value for flag in ordered_flags],
        "risk_notes": list(ordered_notes),
    }
    result_hash = _hash_json(stable_payload)
    return ControlledTestExecutionResult(
        schema_version=CONTROLLED_TEST_EXECUTION_SCHEMA_VERSION,
        execution_result_id=f"controlled-test-exec-{result_hash[:24]}",
        execution_result_hash=result_hash,
        status=status,
        command_kind=command_kind,
        requested_command=request_data["requested_command"],
        normalized_command=normalized_command,
        executed_args_preview=executed_args,
        repo_root=request_data["repo_root"],
        exit_code=exit_code,
        timeout_seconds=request_data["timeout_seconds"],
        timeout_expired=timeout_expired,
        stdout_preview=stdout_preview,
        stderr_preview=stderr_preview,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        source_test_runner_control_id=request_data["source_test_runner_control_id"],
        source_test_runner_control_hash=request_data["source_test_runner_control_hash"],
        source_sandbox_envelope_id=request_data["source_sandbox_envelope_id"],
        source_sandbox_envelope_hash=request_data["source_sandbox_envelope_hash"],
        source_policy_check_id=request_data["source_policy_check_id"],
        source_policy_check_hash=request_data["source_policy_check_hash"],
        source_execution_barrier_id=request_data["source_execution_barrier_id"],
        source_execution_barrier_hash=request_data["source_execution_barrier_hash"],
        source_execution_barrier_status=request_data["source_execution_barrier_status"],
        source_execution_barrier_passed=request_data["source_execution_barrier_passed"],
        source_human_decision_id=request_data["source_human_decision_id"],
        source_human_decision_hash=request_data["source_human_decision_hash"],
        barrier_verified=status
        in {
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
        },
        barrier_hashes_matched=status
        in {
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_FAILED,
            ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_TIMEOUT,
            ControlledTestExecutionStatus.INTERNAL_EXECUTION_ERROR,
        },
        flags=ordered_flags,
        risk_notes=ordered_notes,
        display_summary=_summary(status, command_kind, exit_code, timeout_expired),
    )


def _request_data(request: ControlledTestExecutionRequest) -> dict[str, Any]:
    return {
        "schema_version": _text("schema_version", request.schema_version),
        "requested_command": _text("requested_command", request.requested_command),
        "normalized_command": _normalize_command(request.requested_command),
        "command_hash": _hash_text(_normalize_command(request.requested_command)),
        "command_kind": _normalize_command_kind(request.command_kind).value,
        "repo_root": _safe_repo_root_text(request.repo_root),
        "timeout_seconds": _hard_timeout_seconds(request.timeout_seconds),
        "max_output_bytes": _positive_int("max_output_bytes", request.max_output_bytes),
        "source_trust": _normalize_source_trust(request.source_trust).value,
        "explicit_operator_execution_confirmed": bool(request.explicit_operator_execution_confirmed),
        "source_test_runner_control_id": _optional_text(request.source_test_runner_control_id),
        "source_test_runner_control_hash": _optional_text(request.source_test_runner_control_hash),
        "source_test_runner_control_status": _optional_text(request.source_test_runner_control_status),
        "source_sandbox_envelope_id": _optional_text(request.source_sandbox_envelope_id),
        "source_sandbox_envelope_hash": _optional_text(request.source_sandbox_envelope_hash),
        "source_sandbox_envelope_status": _optional_text(request.source_sandbox_envelope_status),
        "source_policy_check_id": _optional_text(request.source_policy_check_id),
        "source_policy_check_hash": _optional_text(request.source_policy_check_hash),
        "source_execution_barrier_id": _optional_text(request.source_execution_barrier_id),
        "source_execution_barrier_hash": _optional_text(request.source_execution_barrier_hash),
        "source_execution_barrier_status": _optional_text(request.source_execution_barrier_status),
        "source_execution_barrier_passed": bool(request.source_execution_barrier_passed),
        "barrier_bound_command_hash": _optional_text(request.barrier_bound_command_hash),
        "barrier_bound_test_runner_control_hash": _optional_text(request.barrier_bound_test_runner_control_hash),
        "barrier_bound_sandbox_envelope_hash": _optional_text(request.barrier_bound_sandbox_envelope_hash),
        "barrier_bound_policy_check_hash": _optional_text(request.barrier_bound_policy_check_hash),
        "source_human_decision_id": _optional_text(request.source_human_decision_id),
        "source_human_decision_hash": _optional_text(request.source_human_decision_hash),
        "human_review_required": bool(request.human_review_required),
        "risk_flags": tuple(value.upper() for value in _text_tuple("risk_flags", request.risk_flags)),
    }


def _empty_request_data() -> dict[str, Any]:
    return {
        "schema_version": CONTROLLED_TEST_EXECUTION_SCHEMA_VERSION,
        "requested_command": "",
        "normalized_command": "",
        "command_hash": None,
        "command_kind": ControlledTestCommandKind.UNKNOWN.value,
        "repo_root": "",
        "timeout_seconds": _DEFAULT_TIMEOUT_SECONDS,
        "max_output_bytes": _DEFAULT_MAX_OUTPUT_BYTES,
        "source_trust": ControlledTestSourceTrust.UNKNOWN.value,
        "explicit_operator_execution_confirmed": False,
        "source_test_runner_control_id": None,
        "source_test_runner_control_hash": None,
        "source_test_runner_control_status": None,
        "source_sandbox_envelope_id": None,
        "source_sandbox_envelope_hash": None,
        "source_sandbox_envelope_status": None,
        "source_policy_check_id": None,
        "source_policy_check_hash": None,
        "source_execution_barrier_id": None,
        "source_execution_barrier_hash": None,
        "source_execution_barrier_status": None,
        "source_execution_barrier_passed": False,
        "barrier_bound_command_hash": None,
        "barrier_bound_test_runner_control_hash": None,
        "barrier_bound_sandbox_envelope_hash": None,
        "barrier_bound_policy_check_hash": None,
        "source_human_decision_id": None,
        "source_human_decision_hash": None,
        "human_review_required": True,
        "risk_flags": (),
    }


def _allowlisted_args(normalized_command: str) -> tuple[ControlledTestCommandKind, tuple[str, ...], set[ControlledTestExecutionFlag], tuple[str, ...]]:
    flags: set[ControlledTestExecutionFlag] = set()
    if _unsafe_command(normalized_command):
        return (
            ControlledTestCommandKind.UNKNOWN,
            (),
            {ControlledTestExecutionFlag.UNSAFE_COMMAND_BLOCKED},
            ("Unsafe command pattern was found before allowlist matching.",),
        )
    command = _strip_pythonpath_prefix(normalized_command)
    if command == "python -m unittest discover -s tests -v" or command == "python3 -m unittest discover -s tests -v":
        flags.add(ControlledTestExecutionFlag.ALLOWLISTED_UNITTEST_DISCOVER)
        return (
            ControlledTestCommandKind.UNITTEST_DISCOVER,
            (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"),
            flags,
            ("Allowlisted unittest discovery command.",),
        )
    if command == "python -m compileall runtime tests" or command == "python3 -m compileall runtime tests":
        flags.add(ControlledTestExecutionFlag.ALLOWLISTED_COMPILEALL)
        return (
            ControlledTestCommandKind.COMPILEALL,
            (sys.executable, "-m", "compileall", "runtime", "tests"),
            flags,
            ("Allowlisted compileall command.",),
        )
    prefix_options = ("python -m unittest ", "python3 -m unittest ")
    for prefix in prefix_options:
        if command.startswith(prefix) and command.endswith(" -v"):
            module_name = command[len(prefix) : -3].strip()
            if _safe_test_module(module_name):
                flags.add(ControlledTestExecutionFlag.ALLOWLISTED_UNITTEST_FOCUSED)
                return (
                    ControlledTestCommandKind.UNITTEST_FOCUSED,
                    (sys.executable, "-m", "unittest", module_name, "-v"),
                    flags,
                    ("Allowlisted focused unittest module command.",),
                )
    return (
        ControlledTestCommandKind.UNKNOWN,
        (),
        {ControlledTestExecutionFlag.UNSUPPORTED_COMMAND_BLOCKED},
        ("Command is outside the controlled test execution allowlist.",),
    )


def _strip_pythonpath_prefix(normalized_command: str) -> str:
    prefix = "pythonpath=runtime:. "
    if normalized_command.startswith(prefix):
        return normalized_command[len(prefix) :]
    return normalized_command


def _safe_test_module(module_name: str) -> bool:
    if not module_name.startswith("tests.test_"):
        return False
    tail = module_name[len("tests.test_") :]
    return bool(tail) and all(char.islower() or char.isdigit() or char == "_" for char in tail)


def _unsafe_command(normalized_command: str) -> bool:
    unsafe_patterns = (
        "shell" + "=true",
        "bash",
        "bash" + " -c",
        "sh" + " -c",
        "python -c",
        "eval",
        "exec",
        "os" + "." + "system",
        "sub" + "process",
        "po" + "pen",
        "curl",
        "wget",
        " nc ",
        "ssh",
        "scp",
        "sudo",
        "chmod",
        "chown",
        "rm -rf",
        "pip install",
        "npm install",
        "apt install",
        "g" + "it push",
        "g" + "it commit",
        "g" + "it checkout",
        "g" + "it reset",
        "$opena" + "i_" + "api" + "_key",
        "api" + "_key",
        "secret",
        "token",
        ".env",
        "~/.ssh",
        "|",
        ";",
        "&&",
        "||",
        ">",
        "<",
        "`",
        "$(",
    )
    return _contains_any(normalized_command, unsafe_patterns)


def _valid_test_controller_metadata(request_data: dict[str, Any]) -> bool:
    status = (request_data["source_test_runner_control_status"] or "").upper()
    return (
        bool(request_data["source_test_runner_control_id"])
        and _looks_like_sha256(request_data["source_test_runner_control_hash"])
        and status
        in {
            "TEST_RUN_PREVIEW_READY",
            "FOCUSED_TEST_REVIEW_REQUIRED",
            "FULL_SUITE_REVIEW_REQUIRED",
            "COMPILEALL_REVIEW_REQUIRED",
        }
    )


def _valid_sandbox_metadata(request_data: dict[str, Any]) -> bool:
    status = (request_data["source_sandbox_envelope_status"] or "").upper()
    return (
        bool(request_data["source_sandbox_envelope_id"])
        and _looks_like_sha256(request_data["source_sandbox_envelope_hash"])
        and status in {"SANDBOX_ENVELOPE_READY", "REVIEW_REQUIRED"}
    )


def _barrier_status(
    request_data: dict[str, Any],
) -> tuple[ControlledTestExecutionStatus | None, set[ControlledTestExecutionFlag], tuple[str, ...]]:
    flags: set[ControlledTestExecutionFlag] = set()
    notes: list[str] = []
    if not request_data["source_execution_barrier_id"] or not request_data["source_execution_barrier_hash"]:
        flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_MISSING)
        notes.append("Hash-bound human execution barrier metadata is required before controlled test execution.")
        return ControlledTestExecutionStatus.BLOCKED_MISSING_EXECUTION_BARRIER, flags, tuple(notes)

    flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_PRESENT)
    if not _looks_like_sha256(request_data["source_execution_barrier_hash"]):
        flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_HASH_MISMATCH)
        notes.append("Human execution barrier hash is malformed.")
        return ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_STALE_OR_INVALID, flags, tuple(notes)

    if not request_data["source_human_decision_id"] or not _looks_like_sha256(request_data["source_human_decision_hash"]):
        notes.append("Human decision metadata from the execution barrier is missing or malformed.")
        return ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_STALE_OR_INVALID, flags, tuple(notes)

    barrier_status = (request_data["source_execution_barrier_status"] or "").upper()
    if barrier_status != "EXECUTION_BARRIER_PASSED" or not request_data["source_execution_barrier_passed"]:
        flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_NOT_PASSED)
        notes.append("Human execution barrier did not pass for this controlled test execution.")
        return ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_NOT_PASSED, flags, tuple(notes)

    expected_pairs = (
        ("command", request_data["barrier_bound_command_hash"], request_data["command_hash"]),
        (
            "test-runner controller",
            request_data["barrier_bound_test_runner_control_hash"],
            request_data["source_test_runner_control_hash"],
        ),
        (
            "sandbox envelope",
            request_data["barrier_bound_sandbox_envelope_hash"],
            request_data["source_sandbox_envelope_hash"],
        ),
    )
    for label, barrier_hash, current_hash in expected_pairs:
        if barrier_hash != current_hash or not _looks_like_sha256(barrier_hash):
            flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_HASH_MISMATCH)
            notes.append(f"Human execution barrier {label} hash binding does not match this request.")
            return ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH, flags, tuple(notes)

    policy_hash = request_data["source_policy_check_hash"]
    if policy_hash and request_data["barrier_bound_policy_check_hash"] != policy_hash:
        flags.add(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_HASH_MISMATCH)
        notes.append("Human execution barrier local policy hash binding does not match this request.")
        return ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH, flags, tuple(notes)

    notes.append("Hash-bound human execution barrier verified for controlled test-runner metadata.")
    return None, flags, tuple(notes)


def _provider_untrusted(source_trust: str) -> bool:
    return source_trust in {
        ControlledTestSourceTrust.UNTRUSTED_PROVIDER_OUTPUT.value,
        ControlledTestSourceTrust.PROVIDER_UNTRUSTED.value,
        ControlledTestSourceTrust.MODEL_UNTRUSTED.value,
    }


def _normalize_command_kind(value: ControlledTestCommandKind | str) -> ControlledTestCommandKind:
    if isinstance(value, ControlledTestCommandKind):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "UNITTEST_FOCUSED": ControlledTestCommandKind.UNITTEST_FOCUSED,
        "UNITTEST_DISCOVER": ControlledTestCommandKind.UNITTEST_DISCOVER,
        "COMPILEALL": ControlledTestCommandKind.COMPILEALL,
    }
    return aliases.get(normalized, ControlledTestCommandKind.UNKNOWN)


def _normalize_source_trust(value: ControlledTestSourceTrust | str) -> ControlledTestSourceTrust:
    if isinstance(value, ControlledTestSourceTrust):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "USER": ControlledTestSourceTrust.USER_SUPPLIED,
        "USER_SUPPLIED": ControlledTestSourceTrust.USER_SUPPLIED,
        "SYSTEM_METADATA": ControlledTestSourceTrust.SYSTEM_METADATA,
        "CRITIC_METADATA": ControlledTestSourceTrust.CRITIC_METADATA,
        "UNTRUSTED": ControlledTestSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": ControlledTestSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": ControlledTestSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": ControlledTestSourceTrust.MODEL_UNTRUSTED,
    }
    return aliases.get(normalized, ControlledTestSourceTrust.UNKNOWN)


def _normalize_command(value: str) -> str:
    return " ".join(_text("requested_command", value).strip().split()).casefold()


def _safe_repo_root_text(value: str) -> str:
    text = _text("repo_root", value).strip()
    if not text:
        raise ValueError("repo_root cannot be empty")
    if "\x00" in text or ".." in text:
        raise ValueError("repo_root metadata is unsafe")
    return text


def _bound_output(value: str | None, max_output_bytes: int) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    if len(text.encode("utf-8")) <= max_output_bytes:
        return text, False
    encoded = text.encode("utf-8")[:max_output_bytes]
    bounded = encoded.decode("utf-8", errors="ignore")
    return _bounded_text(bounded, max_output_bytes), True


def _timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def _summary(
    status: ControlledTestExecutionStatus,
    command_kind: ControlledTestCommandKind,
    exit_code: int | None,
    timeout_expired: bool,
) -> str:
    exit_text = "timeout" if timeout_expired else f"exit_code={exit_code}"
    return _bounded_text(
        f"Controlled test execution result is {status.value} for {command_kind.value}; {exit_text}; no shell or arbitrary command authority granted.",
        420,
    )


def _contains_any(value: str, patterns: tuple[str, ...]) -> bool:
    lowered = value.casefold()
    return any(pattern.casefold() in lowered for pattern in patterns)


def _looks_like_sha256(value: str | None) -> bool:
    if value is None:
        return False
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _positive_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _hard_timeout_seconds(value: int) -> int:
    timeout = _positive_int("timeout_seconds", value)
    if timeout > _MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout_seconds exceeds the hard process limit")
    return timeout


def _text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if "\x00" in value:
        raise ValueError(f"{field_name} cannot contain null bytes")
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = _text("optional_text", value).strip()
    return text or None


def _text_tuple(field_name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list")
    return tuple(_text(field_name, value).strip() for value in values)


def _flag_tuple(values: tuple[ControlledTestExecutionFlag, ...]) -> tuple[ControlledTestExecutionFlag, ...]:
    if not isinstance(values, tuple):
        raise TypeError("flags must be a tuple")
    return tuple(ControlledTestExecutionFlag(value) for value in values)


def _hash_json(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _bounded_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."
