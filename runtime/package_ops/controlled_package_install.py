from __future__ import annotations

import hashlib
import json
import subprocess
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runtime.package_ops.package_install_proposal import (
    PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY,
    PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
    PackageInstallProposal,
    compute_package_install_request_hash,
    propose_package_install,
)


CONTROLLED_PACKAGE_INSTALL_SCHEMA_VERSION = "AOIA_CONTROLLED_PACKAGE_INSTALL_1A"
PACKAGE_INSTALL_HUMAN_BARRIER_SCHEMA_VERSION = "AOIA_PACKAGE_INSTALL_HUMAN_BARRIER_1A"

CONTROLLED_PACKAGE_INSTALL_COMPLETED = "CONTROLLED_PACKAGE_INSTALL_COMPLETED"
CONTROLLED_PACKAGE_INSTALL_BLOCKED = "CONTROLLED_PACKAGE_INSTALL_BLOCKED"
CONTROLLED_PACKAGE_INSTALL_FAILED = "CONTROLLED_PACKAGE_INSTALL_FAILED"

CONTROLLED_PACKAGE_INSTALL_REASON_COMPLETED_OFFLINE_SANDBOX = "CONTROLLED_PACKAGE_INSTALL_REASON_COMPLETED_OFFLINE_SANDBOX"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_MALFORMED_EVIDENCE = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_MALFORMED_EVIDENCE"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_VALIDATION_NOT_READY = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_VALIDATION_NOT_READY"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_HASH_MISMATCH = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_HASH_MISMATCH"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_MISSING_HUMAN_BARRIER = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_MISSING_HUMAN_BARRIER"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_HASH_MISMATCH = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_HASH_MISMATCH"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_SCOPE_MISMATCH = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_SCOPE_MISMATCH"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_STALE = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_STALE"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_AUTHORITY_CLAIM"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_CURRENT_STATE_MISMATCH = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_CURRENT_STATE_MISMATCH"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_NON_OFFLINE = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_NON_OFFLINE"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_APT_UNSUPPORTED = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_APT_UNSUPPORTED"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSUPPORTED_ECOSYSTEM = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSUPPORTED_ECOSYSTEM"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_EXECUTION_FAILED = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_EXECUTION_FAILED"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_MISSING = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_MISSING"
CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_UNSAFE = "CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_UNSAFE"

_HEX = frozenset("0123456789abcdef")
_MAX_OUTPUT_CHARS = 4000
_DEFAULT_TIMEOUT_SECONDS = 60
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "authority",
        "authority_granted",
        "human_approved",
        "can_install",
        "can_execute",
        "can_write",
        "can_push",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "install_allowed",
        "execution_allowed",
    }
)
_AUTHORITY_FLAGS = (
    "can_install",
    "can_execute",
    "can_write",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "gate_satisfied",
    "human_barrier_satisfied",
    "future_install_authorized",
)
_MINIMAL_INSTALL_ENV = {
    "PYTHONNOUSERSITE": "1",
    "PIP_NO_INDEX": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PIP_NO_INPUT": "1",
    "NPM_CONFIG_OFFLINE": "true",
    "NPM_CONFIG_AUDIT": "false",
    "NPM_CONFIG_FUND": "false",
    "NPM_CONFIG_IGNORE_SCRIPTS": "true",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
}


@dataclass(frozen=True)
class PackageInstallCurrentState:
    current_tick: int
    dependency_context_hash: str
    target_environment_hash: str
    sandbox_root: str
    offline_artifact_root: str
    offline_mode: bool = True
    network_disabled: bool = True
    package_registry_access_disabled: bool = True


@dataclass(frozen=True)
class PackageInstallHumanBarrier:
    schema_version: str
    proposal_hash: str
    validation_hash: str
    ecosystem: str
    package_name: str
    package_version: str
    source: str
    target: str
    dependency_context_hash: str
    target_environment_hash: str
    approved_by: str
    approval_reason: str
    approved_at: int
    expires_at: int
    barrier_hash: str
    can_install: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    future_install_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "proposal_hash", _required_hash("proposal_hash", self.proposal_hash))
        object.__setattr__(self, "validation_hash", _required_hash("validation_hash", self.validation_hash))
        object.__setattr__(self, "ecosystem", _required_text("ecosystem", self.ecosystem).casefold())
        object.__setattr__(self, "package_name", _required_text("package_name", self.package_name))
        object.__setattr__(self, "package_version", _required_text("package_version", self.package_version))
        object.__setattr__(self, "source", _required_text("source", self.source))
        object.__setattr__(self, "target", _required_text("target", self.target))
        object.__setattr__(self, "dependency_context_hash", _required_hash("dependency_context_hash", self.dependency_context_hash))
        object.__setattr__(self, "target_environment_hash", _required_hash("target_environment_hash", self.target_environment_hash))
        object.__setattr__(self, "approved_by", _required_text("approved_by", self.approved_by))
        object.__setattr__(self, "approval_reason", _required_text("approval_reason", self.approval_reason))
        object.__setattr__(self, "approved_at", _nonnegative_int("approved_at", self.approved_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "barrier_hash", _required_hash("barrier_hash", self.barrier_hash))
        for field_name in _AUTHORITY_FLAGS:
            object.__setattr__(self, field_name, False)
        if self.schema_version != PACKAGE_INSTALL_HUMAN_BARRIER_SCHEMA_VERSION:
            raise ValueError("unsupported package install human barrier schema version")
        if self.expires_at < self.approved_at:
            raise ValueError("package install human barrier TTL is inverted")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proposal_hash": self.proposal_hash,
            "validation_hash": self.validation_hash,
            "ecosystem": self.ecosystem,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "source": self.source,
            "target": self.target,
            "dependency_context_hash": self.dependency_context_hash,
            "target_environment_hash": self.target_environment_hash,
            "approved_by": self.approved_by,
            "approval_reason": self.approval_reason,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "barrier_hash": self.barrier_hash,
            "can_install": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
            "future_install_authorized": False,
        }


@dataclass(frozen=True)
class ControlledPackageInstallResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    ecosystem: str | None
    package_name: str | None
    package_version: str | None
    proposal_hash: str | None
    validation_hash: str | None
    barrier_hash: str | None
    source_artifact_hash: str | None
    target_path_hash: str | None
    dependency_context_hash: str | None
    target_environment_hash: str | None
    executed_args_preview: tuple[str, ...]
    exit_code: int | None
    stdout_preview: str
    stderr_preview: str
    result_hash: str
    sandbox_install_attempted: bool = False
    sandbox_install_completed: bool = False
    package_manager_called: bool = False
    subprocess_started: bool = False
    shell_invoked: bool = False
    network_called: bool = False
    package_registry_called: bool = False
    apt_executed: bool = False
    real_environment_modified: bool = False
    dependency_file_modified: bool = False
    provider_called: bool = False
    browser_opened: bool = False
    git_action_performed: bool = False
    approval_created: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_install: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    future_install_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", CONTROLLED_PACKAGE_INSTALL_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "executed_args_preview", tuple(self.executed_args_preview))
        if self.status not in {
            CONTROLLED_PACKAGE_INSTALL_COMPLETED,
            CONTROLLED_PACKAGE_INSTALL_BLOCKED,
            CONTROLLED_PACKAGE_INSTALL_FAILED,
        }:
            raise ValueError("unsupported controlled package install status")
        if not _sha256_like(self.result_hash):
            raise ValueError("result_hash must be a sha256 hex digest")
        attempted = self.status in {CONTROLLED_PACKAGE_INSTALL_COMPLETED, CONTROLLED_PACKAGE_INSTALL_FAILED}
        object.__setattr__(self, "sandbox_install_attempted", attempted)
        object.__setattr__(self, "sandbox_install_completed", self.status == CONTROLLED_PACKAGE_INSTALL_COMPLETED)
        object.__setattr__(self, "package_manager_called", attempted)
        object.__setattr__(self, "subprocess_started", attempted)
        for field_name in (
            "shell_invoked",
            "network_called",
            "package_registry_called",
            "apt_executed",
            "real_environment_modified",
            "dependency_file_modified",
            "provider_called",
            "browser_opened",
            "git_action_performed",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_install",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "future_install_authorized",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLED_PACKAGE_INSTALL_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "ecosystem": self.ecosystem,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "proposal_hash": self.proposal_hash,
            "validation_hash": self.validation_hash,
            "barrier_hash": self.barrier_hash,
            "source_artifact_hash": self.source_artifact_hash,
            "target_path_hash": self.target_path_hash,
            "dependency_context_hash": self.dependency_context_hash,
            "target_environment_hash": self.target_environment_hash,
            "executed_args_preview": self.executed_args_preview,
            "exit_code": self.exit_code,
            "stdout_preview": self.stdout_preview,
            "stderr_preview": self.stderr_preview,
            "result_hash": self.result_hash,
            "sandbox_install_attempted": self.sandbox_install_attempted,
            "sandbox_install_completed": self.sandbox_install_completed,
            "package_manager_called": self.package_manager_called,
            "subprocess_started": self.subprocess_started,
            "shell_invoked": False,
            "network_called": False,
            "package_registry_called": False,
            "apt_executed": False,
            "real_environment_modified": False,
            "dependency_file_modified": False,
            "provider_called": False,
            "browser_opened": False,
            "git_action_performed": False,
            "approval_created": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
            "can_install": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "future_install_authorized": False,
        }


@dataclass(frozen=True)
class _RunnerResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timeout_expired: bool = False


class _SubprocessPackageRunner:
    def run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_seconds: int,
    ) -> _RunnerResult:
        try:
            completed = subprocess.run(
                list(argv),
                cwd=str(cwd),
                env=dict(env),
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return _RunnerResult(None, _text_output(exc.stdout), _text_output(exc.stderr), timeout_expired=True)
        except (OSError, ValueError) as exc:
            return _RunnerResult(1, "", str(exc))
        return _RunnerResult(completed.returncode, _text_output(completed.stdout), _text_output(completed.stderr))


class _VenvEnvironmentBuilder:
    def create(self, target_path: Path) -> None:
        venv.EnvBuilder(with_pip=True, clear=False).create(str(target_path))


class _SandboxInterpreterBlocked(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def create_package_install_human_barrier(
    *,
    proposal_hash: str,
    validation_hash: str,
    ecosystem: str,
    package_name: str,
    package_version: str,
    source: str,
    target: str,
    dependency_context_hash: str,
    target_environment_hash: str,
    approved_by: str,
    approval_reason: str,
    approved_at: int,
    expires_at: int,
) -> PackageInstallHumanBarrier:
    material = {
        "schema_version": PACKAGE_INSTALL_HUMAN_BARRIER_SCHEMA_VERSION,
        "proposal_hash": _required_hash("proposal_hash", proposal_hash),
        "validation_hash": _required_hash("validation_hash", validation_hash),
        "ecosystem": _required_text("ecosystem", ecosystem).casefold(),
        "package_name": _required_text("package_name", package_name),
        "package_version": _required_text("package_version", package_version),
        "source": _required_text("source", source),
        "target": _required_text("target", target),
        "dependency_context_hash": _required_hash("dependency_context_hash", dependency_context_hash),
        "target_environment_hash": _required_hash("target_environment_hash", target_environment_hash),
        "approved_by": _required_text("approved_by", approved_by),
        "approval_reason": _required_text("approval_reason", approval_reason),
        "approved_at": _nonnegative_int("approved_at", approved_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return PackageInstallHumanBarrier(
        **material,
        barrier_hash=compute_package_install_barrier_hash(material),
    )


def execute_controlled_package_install(
    *,
    proposal: object,
    validation_result: object,
    human_barrier: object,
    current_state: object,
    source_artifact_path: str,
    target_path: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    runner: Any = None,
    environment_builder: Any = None,
) -> ControlledPackageInstallResult:
    try:
        state = _coerce_current_state(current_state)
        tick = state.current_tick
        timeout = _positive_int("timeout_seconds", timeout_seconds)
        proposal_hash = compute_package_install_request_hash(proposal)
        validation = _coerce_validation_result(validation_result)
        barrier = _coerce_barrier(human_barrier)
        source_path, source_error = _safe_source_path(source_artifact_path, state.offline_artifact_root)
        target, target_error = _safe_target_path(target_path, state.sandbox_root)
    except (TypeError, ValueError):
        return _result(
            status=CONTROLLED_PACKAGE_INSTALL_BLOCKED,
            reason_codes=(CONTROLLED_PACKAGE_INSTALL_BLOCKED_MALFORMED_EVIDENCE,),
        )

    reason_codes: list[str] = []
    if validation.status != PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY:
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_VALIDATION_NOT_READY)
    revalidated = propose_package_install(proposal, now_tick=tick)
    if (
        revalidated.status != PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY
        or revalidated.proposal_hash != validation.proposal_hash
        or proposal_hash != validation.request_hash
    ):
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_HASH_MISMATCH)
    if _authority_claim_present(validation_result) or _authority_claim_present(human_barrier):
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_AUTHORITY_CLAIM)
    if source_error is not None:
        reason_codes.append(source_error)
    if target_error is not None:
        reason_codes.append(target_error)
    if not state.offline_mode or not state.network_disabled or not state.package_registry_access_disabled:
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_NON_OFFLINE)
    if state.dependency_context_hash != barrier.dependency_context_hash or state.target_environment_hash != barrier.target_environment_hash:
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_CURRENT_STATE_MISMATCH)

    barrier_codes = _barrier_reason_codes(
        barrier=barrier,
        proposal_hash=proposal_hash,
        validation_hash=validation.proposal_hash,
        ecosystem=validation.ecosystem,
        package_name=validation.package_name,
        package_version=validation.version,
        source=source_artifact_path,
        target=target_path,
        dependency_context_hash=state.dependency_context_hash,
        target_environment_hash=state.target_environment_hash,
        current_tick=tick,
    )
    reason_codes.extend(barrier_codes)

    source_hash = _hash_file(source_path) if source_path is not None and source_path.is_file() else None
    target_hash = _stable_hash(str(target)) if target is not None else None
    if validation.ecosystem == "apt":
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_APT_UNSUPPORTED)
    elif validation.ecosystem not in {"pip", "npm"}:
        reason_codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSUPPORTED_ECOSYSTEM)

    if reason_codes:
        return _result(
            status=CONTROLLED_PACKAGE_INSTALL_BLOCKED,
            reason_codes=tuple(reason_codes),
            ecosystem=validation.ecosystem,
            package_name=validation.package_name,
            package_version=validation.version,
            proposal_hash=proposal_hash,
            validation_hash=validation.proposal_hash,
            barrier_hash=barrier.barrier_hash,
            source_artifact_hash=source_hash,
            target_path_hash=target_hash,
            dependency_context_hash=state.dependency_context_hash,
            target_environment_hash=state.target_environment_hash,
        )

    assert source_path is not None
    assert target is not None
    active_runner = runner or _SubprocessPackageRunner()
    try:
        if validation.ecosystem == "pip":
            argv, cwd = _prepare_pip_install(
                source_path=source_path,
                target_path=target,
                environment_builder=environment_builder or _VenvEnvironmentBuilder(),
            )
        else:
            argv, cwd = _prepare_npm_install(source_path=source_path, target_path=target)
        completed = active_runner.run(
            argv,
            cwd=cwd,
            env=_MINIMAL_INSTALL_ENV,
            timeout_seconds=timeout,
        )
    except (OSError, ValueError) as exc:
        return _result(
            status=CONTROLLED_PACKAGE_INSTALL_FAILED,
            reason_codes=(CONTROLLED_PACKAGE_INSTALL_BLOCKED_EXECUTION_FAILED,),
            ecosystem=validation.ecosystem,
            package_name=validation.package_name,
            package_version=validation.version,
            proposal_hash=proposal_hash,
            validation_hash=validation.proposal_hash,
            barrier_hash=barrier.barrier_hash,
            source_artifact_hash=source_hash,
            target_path_hash=target_hash,
            dependency_context_hash=state.dependency_context_hash,
            target_environment_hash=state.target_environment_hash,
            stderr_preview=type(exc).__name__,
        )
    except _SandboxInterpreterBlocked as exc:
        return _result(
            status=CONTROLLED_PACKAGE_INSTALL_BLOCKED,
            reason_codes=(exc.reason_code,),
            ecosystem=validation.ecosystem,
            package_name=validation.package_name,
            package_version=validation.version,
            proposal_hash=proposal_hash,
            validation_hash=validation.proposal_hash,
            barrier_hash=barrier.barrier_hash,
            source_artifact_hash=source_hash,
            target_path_hash=target_hash,
            dependency_context_hash=state.dependency_context_hash,
            target_environment_hash=state.target_environment_hash,
        )

    status = CONTROLLED_PACKAGE_INSTALL_COMPLETED if completed.exit_code == 0 and not completed.timeout_expired else CONTROLLED_PACKAGE_INSTALL_FAILED
    reason = (
        CONTROLLED_PACKAGE_INSTALL_REASON_COMPLETED_OFFLINE_SANDBOX
        if status == CONTROLLED_PACKAGE_INSTALL_COMPLETED
        else CONTROLLED_PACKAGE_INSTALL_BLOCKED_EXECUTION_FAILED
    )
    return _result(
        status=status,
        reason_codes=(reason,),
        ecosystem=validation.ecosystem,
        package_name=validation.package_name,
        package_version=validation.version,
        proposal_hash=proposal_hash,
        validation_hash=validation.proposal_hash,
        barrier_hash=barrier.barrier_hash,
        source_artifact_hash=source_hash,
        target_path_hash=target_hash,
        dependency_context_hash=state.dependency_context_hash,
        target_environment_hash=state.target_environment_hash,
        executed_args_preview=argv,
        exit_code=completed.exit_code,
        stdout_preview=_bound_text(completed.stdout),
        stderr_preview=_bound_text(completed.stderr),
    )


def compute_package_install_barrier_hash(value: Mapping[str, Any]) -> str:
    return _stable_hash(_fingerprint(value))


def _prepare_pip_install(
    *,
    source_path: Path,
    target_path: Path,
    environment_builder: Any,
) -> tuple[tuple[str, ...], Path]:
    target_path.mkdir(parents=True, exist_ok=True)
    environment_builder.create(target_path)
    python_bin = _sandbox_python_bin(target_path)
    return (
        str(python_bin),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        "--disable-pip-version-check",
        str(source_path),
    ), target_path


def _sandbox_python_bin(target_path: Path) -> Path:
    try:
        target_root = target_path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise _SandboxInterpreterBlocked(CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_UNSAFE) from exc
    for candidate in (
        target_path / "bin" / "python",
        target_path / "Scripts" / "python.exe",
    ):
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            continue
        if not resolved.is_file():
            continue
        if not _is_relative_to(resolved, target_root):
            raise _SandboxInterpreterBlocked(CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_UNSAFE)
        return resolved
    raise _SandboxInterpreterBlocked(CONTROLLED_PACKAGE_INSTALL_BLOCKED_SANDBOX_INTERPRETER_MISSING)


def _prepare_npm_install(*, source_path: Path, target_path: Path) -> tuple[tuple[str, ...], Path]:
    target_path.mkdir(parents=True, exist_ok=True)
    package_json = target_path / "package.json"
    if not package_json.exists():
        package_json.write_text('{"private":true,"name":"aoia-step43-sandbox","version":"0.0.0"}\n', encoding="utf-8")
    return (
        "npm",
        "install",
        "--offline",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        "--no-save",
        "--package-lock=false",
        str(source_path),
    ), target_path


def _barrier_reason_codes(
    *,
    barrier: PackageInstallHumanBarrier,
    proposal_hash: str,
    validation_hash: str,
    ecosystem: str | None,
    package_name: str | None,
    package_version: str | None,
    source: str,
    target: str,
    dependency_context_hash: str,
    target_environment_hash: str,
    current_tick: int,
) -> tuple[str, ...]:
    codes: list[str] = []
    if barrier is None:
        return (CONTROLLED_PACKAGE_INSTALL_BLOCKED_MISSING_HUMAN_BARRIER,)
    try:
        if barrier.barrier_hash != compute_package_install_barrier_hash(_barrier_hash_material(barrier)):
            codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_HASH_MISMATCH)
    except (TypeError, ValueError):
        codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_HASH_MISMATCH)
    if current_tick < barrier.approved_at or current_tick > barrier.expires_at:
        codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_STALE)
    if (
        barrier.proposal_hash != proposal_hash
        or barrier.validation_hash != validation_hash
        or barrier.ecosystem != ecosystem
        or barrier.package_name != package_name
        or barrier.package_version != package_version
        or barrier.source != source
        or barrier.target != target
        or barrier.dependency_context_hash != dependency_context_hash
        or barrier.target_environment_hash != target_environment_hash
    ):
        codes.append(CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_SCOPE_MISMATCH)
    return tuple(codes)


def _coerce_validation_result(value: object) -> PackageInstallProposal:
    if isinstance(value, PackageInstallProposal):
        return value
    if isinstance(value, Mapping):
        return PackageInstallProposal(**dict(value))
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        if isinstance(mapped, Mapping):
            return PackageInstallProposal(**dict(mapped))
    raise TypeError("valid Step 42 package install proposal validation result is required")


def _coerce_barrier(value: object) -> PackageInstallHumanBarrier:
    if isinstance(value, PackageInstallHumanBarrier):
        return value
    if isinstance(value, Mapping):
        return PackageInstallHumanBarrier(**dict(value))
    raise TypeError("package install human barrier is required")


def _coerce_current_state(value: object) -> PackageInstallCurrentState:
    if isinstance(value, PackageInstallCurrentState):
        return value
    if isinstance(value, Mapping):
        return PackageInstallCurrentState(**dict(value))
    raise TypeError("package install current state is required")


def _safe_source_path(source: str, offline_artifact_root: str) -> tuple[Path | None, str | None]:
    if "://" in source:
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE
    try:
        root = Path(offline_artifact_root).resolve(strict=True)
        path = Path(source).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE
    if not _is_relative_to(path, root):
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE
    if not (path.is_file() or path.is_dir()):
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE
    return path, None


def _safe_target_path(target: str, sandbox_root: str) -> tuple[Path | None, str | None]:
    if "://" in target:
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET
    try:
        root = Path(sandbox_root).resolve(strict=True)
        path = Path(target).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET
    if path == root or not _is_relative_to(path, root):
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET
    parts = {part.casefold() for part in path.parts}
    if {".git", ".venv", "venv", "node_modules"} & parts:
        return None, CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET
    return path, None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _hash_file(path: Path) -> str:
    if path.is_dir():
        return _stable_hash(tuple(sorted(str(item.relative_to(path)) for item in path.rglob("*") if item.is_file())))
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _barrier_hash_material(barrier: PackageInstallHumanBarrier) -> dict[str, Any]:
    data = barrier.to_dict()
    data.pop("barrier_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return data


def _authority_claim_present(value: object) -> bool:
    if isinstance(value, PackageInstallHumanBarrier):
        value = value.to_dict()
    elif isinstance(value, PackageInstallProposal):
        value = value.to_dict()
    elif hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in _AUTHORITY_FIELD_NAMES and item is not False:
                return True
            if _authority_claim_present(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_authority_claim_present(item) for item in value)
    return False


def _result(
    *,
    status: str,
    reason_codes: tuple[str, ...],
    ecosystem: str | None = None,
    package_name: str | None = None,
    package_version: str | None = None,
    proposal_hash: str | None = None,
    validation_hash: str | None = None,
    barrier_hash: str | None = None,
    source_artifact_hash: str | None = None,
    target_path_hash: str | None = None,
    dependency_context_hash: str | None = None,
    target_environment_hash: str | None = None,
    executed_args_preview: tuple[str, ...] = (),
    exit_code: int | None = None,
    stdout_preview: str = "",
    stderr_preview: str = "",
) -> ControlledPackageInstallResult:
    material = {
        "schema_version": CONTROLLED_PACKAGE_INSTALL_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "ecosystem": ecosystem,
        "package_name": package_name,
        "package_version": package_version,
        "proposal_hash": proposal_hash,
        "validation_hash": validation_hash,
        "barrier_hash": barrier_hash,
        "source_artifact_hash": source_artifact_hash,
        "target_path_hash": target_path_hash,
        "dependency_context_hash": dependency_context_hash,
        "target_environment_hash": target_environment_hash,
        "executed_args_preview": executed_args_preview,
        "exit_code": exit_code,
        "stdout_preview": stdout_preview,
        "stderr_preview": stderr_preview,
    }
    return ControlledPackageInstallResult(
        schema_version=CONTROLLED_PACKAGE_INSTALL_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        ecosystem=ecosystem,
        package_name=package_name,
        package_version=package_version,
        proposal_hash=proposal_hash,
        validation_hash=validation_hash,
        barrier_hash=barrier_hash,
        source_artifact_hash=source_artifact_hash,
        target_path_hash=target_path_hash,
        dependency_context_hash=dependency_context_hash,
        target_environment_hash=target_environment_hash,
        executed_args_preview=executed_args_preview,
        exit_code=exit_code,
        stdout_preview=stdout_preview,
        stderr_preview=stderr_preview,
        result_hash=_stable_hash(material),
    )


def _fingerprint(value: object) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        raise TypeError("floating point evidence is ambiguous")
    if isinstance(value, Mapping):
        return {
            str(key): _fingerprint(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return tuple(_fingerprint(item) for item in value)
    return {"unsupported_type": type(value).__name__}


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: object) -> str:
    material = json.dumps(_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _bound_text(value: object) -> str:
    text = _text_output(value)
    return text[:_MAX_OUTPUT_CHARS]


def _text_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
