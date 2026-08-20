from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from runtime.safety.subprocess_env import build_subprocess_env
from runtime.safety.bounded_subprocess import run_bounded_subprocess

from runtime.patches.post_patch_verification_plan import (
    CHECK_KIND_COMPILE,
    CHECK_KIND_STATIC,
    CHECK_KIND_TEST,
    POST_PATCH_VERIFICATION_READY,
    PostPatchVerificationCheck,
    PostPatchVerificationPlanResult,
    compute_post_patch_verification_plan_hash,
)
from runtime.safety.workspace_guard import validate_workspace_root


CONTROLLED_VERIFICATION_PASS = "PASS"
CONTROLLED_VERIFICATION_FAIL = "FAIL"
CONTROLLED_VERIFICATION_BLOCKED = "BLOCKED"
CONTROLLED_VERIFICATION_PARTIAL = "PARTIAL"

CONTROLLED_VERIFICATION_CHECK_PASS = "PASS"
CONTROLLED_VERIFICATION_CHECK_FAIL = "FAIL"
CONTROLLED_VERIFICATION_CHECK_BLOCKED = "BLOCKED"
CONTROLLED_VERIFICATION_CHECK_TIMEOUT = "TIMEOUT"

CONTROLLED_VERIFICATION_BLOCKED_MISSING_PLAN = "CONTROLLED_VERIFICATION_BLOCKED_MISSING_PLAN"
CONTROLLED_VERIFICATION_BLOCKED_MALFORMED_PLAN = "CONTROLLED_VERIFICATION_BLOCKED_MALFORMED_PLAN"
CONTROLLED_VERIFICATION_BLOCKED_PLAN_NOT_READY = "CONTROLLED_VERIFICATION_BLOCKED_PLAN_NOT_READY"
CONTROLLED_VERIFICATION_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_VERIFICATION_BLOCKED_AUTHORITY_CLAIM"
CONTROLLED_VERIFICATION_BLOCKED_OPERATOR_APPROVAL = "CONTROLLED_VERIFICATION_BLOCKED_OPERATOR_APPROVAL"
CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_TARGET_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_TARGET_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN = "CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN"
CONTROLLED_VERIFICATION_BLOCKED_CHECK_METADATA_MISMATCH = "CONTROLLED_VERIFICATION_BLOCKED_CHECK_METADATA_MISMATCH"
CONTROLLED_VERIFICATION_BLOCKED_UNSUPPORTED_CHECK_KIND = "CONTROLLED_VERIFICATION_BLOCKED_UNSUPPORTED_CHECK_KIND"
CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND = "CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND"
CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_TEST_TARGET = "CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_TEST_TARGET"
CONTROLLED_VERIFICATION_BLOCKED_WORKSPACE_GUARD = "CONTROLLED_VERIFICATION_BLOCKED_WORKSPACE_GUARD"
CONTROLLED_VERIFICATION_BLOCKED_TIMEOUT_CONFIG = "CONTROLLED_VERIFICATION_BLOCKED_TIMEOUT_CONFIG"
CONTROLLED_VERIFICATION_TIMEOUT = "CONTROLLED_VERIFICATION_TIMEOUT"
CONTROLLED_VERIFICATION_CHECK_FAILED = "CONTROLLED_VERIFICATION_CHECK_FAILED"
CONTROLLED_VERIFICATION_CHECK_PASSED = "CONTROLLED_VERIFICATION_CHECK_PASSED"
CONTROLLED_VERIFICATION_INTERNAL_ERROR = "CONTROLLED_VERIFICATION_INTERNAL_ERROR"

COMMAND_KIND_COMPILEALL = "PYTHON_COMPILEALL_RUNTIME_TESTS"
COMMAND_KIND_UNITTEST_FOCUSED = "PYTHON_UNITTEST_FOCUSED"
COMMAND_KIND_UNITTEST_DISCOVER = "PYTHON_UNITTEST_DISCOVER"
COMMAND_KIND_UNSUPPORTED = "UNSUPPORTED"

_SCHEMA_VERSION = "AOIA_CONTROLLED_POST_PATCH_VERIFICATION_1A"
_DEFAULT_TIMEOUT_SECONDS = 60
_DEFAULT_MAX_OUTPUT_BYTES = 20_000
_MIN_TIMEOUT_SECONDS = 1
_MAX_TIMEOUT_SECONDS = 300
_MIN_OUTPUT_BYTES = 1
_MAX_OUTPUT_BYTES = 50_000
_MINIMAL_ENV = {
    "PYTHONPATH": "runtime:.",
    "PYTHONNOUSERSITE": "1",
}
_AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "write_authority_granted",
    "execution_authority_granted",
    "provider_authority_granted",
)
_SHA256_HEX = frozenset("0123456789abcdef")
_BLOCKED_COMMAND_TERMS = (
    ";",
    "&&",
    "||",
    "|",
    "`",
    "$(",
    ">",
    "<",
    " git ",
    "git ",
    " git",
    "bash",
    "sh -c",
    "shell" + "=true",
    "pip install",
    "npm install",
    "apt install",
    "curl",
    "wget",
    "socket",
    "requests",
    "httpx",
    "urllib",
    "webbrowser",
    "selenium",
    "playwright",
    "openai",
    "anthropic",
    "provider",
    "api_key",
    "secret",
    "token",
    ".env",
    "os.environ",
    "getenv",
)


@dataclass(frozen=True)
class ControlledVerificationRunRequest:
    verification_plan: PostPatchVerificationPlanResult | None
    workspace_root: str
    requested_check_ids: tuple[str, ...] | list[str]
    expected_plan_hash: str
    expected_apply_hash: str
    expected_patch_preview_hash: str
    expected_patch_policy_hash: str
    expected_patch_barrier_hash: str
    operator_approved: bool
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    max_output_bytes: int = _DEFAULT_MAX_OUTPUT_BYTES


@dataclass(frozen=True)
class ControlledVerificationCheckResult:
    check_id: str
    status: str
    reason_code: str
    reason: str
    command_kind: str
    test_target: str | None
    exit_code: int | None
    timeout_expired: bool
    stdout_preview: str
    stderr_preview: str
    stdout_truncated: bool
    stderr_truncated: bool
    execution_attempted: bool = False
    subprocess_started: bool = False
    shell_invoked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "shell_invoked", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "command_kind": self.command_kind,
            "test_target": self.test_target,
            "exit_code": self.exit_code,
            "timeout_expired": self.timeout_expired,
            "stdout_preview": self.stdout_preview,
            "stderr_preview": self.stderr_preview,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "execution_attempted": self.execution_attempted,
            "subprocess_started": self.subprocess_started,
            "shell_invoked": self.shell_invoked,
        }


@dataclass(frozen=True)
class ControlledVerificationRunResult:
    status: str
    run_hash: str
    plan_hash: str | None
    apply_hash: str | None
    patch_preview_hash: str | None
    patch_policy_hash: str | None
    patch_barrier_hash: str | None
    target_paths: tuple[str, ...]
    check_ids: tuple[str, ...]
    check_results: tuple[ControlledVerificationCheckResult, ...]
    reason_codes: tuple[str, ...]
    reason: str
    partial: bool = False
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_paths", tuple(self.target_paths))
        object.__setattr__(self, "check_ids", tuple(self.check_ids))
        object.__setattr__(self, "check_results", tuple(self.check_results))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "partial", self.status == CONTROLLED_VERIFICATION_PARTIAL)
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "run_hash": self.run_hash,
            "plan_hash": self.plan_hash,
            "apply_hash": self.apply_hash,
            "patch_preview_hash": self.patch_preview_hash,
            "patch_policy_hash": self.patch_policy_hash,
            "patch_barrier_hash": self.patch_barrier_hash,
            "target_paths": list(self.target_paths),
            "check_ids": list(self.check_ids),
            "check_results": [item.to_dict() for item in self.check_results],
            "reason_codes": list(self.reason_codes),
            "reason": self.reason,
            "partial": self.partial,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "write_authority_granted": self.write_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
        }


def canonical_controlled_verification_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_controlled_verification_hash(value: Any) -> str:
    return hashlib.sha256(canonical_controlled_verification_json(value).encode("utf-8")).hexdigest()


def run_controlled_post_patch_verification(
    request: ControlledVerificationRunRequest | Mapping[str, Any] | None,
) -> ControlledVerificationRunResult:
    if not isinstance(request, ControlledVerificationRunRequest):
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_MALFORMED_PLAN, "controlled verification requires a typed request")
    plan = request.verification_plan
    if not isinstance(plan, PostPatchVerificationPlanResult):
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_MISSING_PLAN, "post-patch verification plan is required")
    if _has_authority_claim(plan) or (plan.plan is not None and _has_authority_claim(plan.plan)):
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_AUTHORITY_CLAIM, "verification plan contains authority-like claims", plan=plan)
    if plan.status != POST_PATCH_VERIFICATION_READY or not plan.plan_ready or plan.plan is None:
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_PLAN_NOT_READY, "verification plan must be READY", plan=plan)
    if not request.operator_approved:
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_OPERATOR_APPROVAL, "explicit operator approval is required to run verification", plan=plan)

    evidence_error = _evidence_error(request, plan)
    if evidence_error is not None:
        return _blocked(evidence_error, "verification plan hash binding failed", plan=plan)

    workspace_error = _workspace_error(request.workspace_root, plan.target_paths)
    if workspace_error is not None:
        return _blocked(workspace_error, "workspace root or plan target path is unsafe", plan=plan)

    requested_ids, requested_error = _requested_check_ids(request.requested_check_ids)
    if requested_error is not None:
        return _blocked(requested_error, "requested check ids are malformed", plan=plan)
    plan_checks = {check.check_id: check for check in plan.checks}
    missing = [check_id for check_id in requested_ids if check_id not in plan_checks]
    if missing:
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN, "requested check id is not present in the verification plan", plan=plan, check_ids=requested_ids)

    timeout_seconds = _bounded_int(request.timeout_seconds, _MIN_TIMEOUT_SECONDS, _MAX_TIMEOUT_SECONDS, _DEFAULT_TIMEOUT_SECONDS)
    max_output_bytes = _bounded_int(request.max_output_bytes, _MIN_OUTPUT_BYTES, _MAX_OUTPUT_BYTES, _DEFAULT_MAX_OUTPUT_BYTES)
    if timeout_seconds != request.timeout_seconds or max_output_bytes != request.max_output_bytes:
        return _blocked(CONTROLLED_VERIFICATION_BLOCKED_TIMEOUT_CONFIG, "timeout/output bounds are outside controlled limits", plan=plan, check_ids=requested_ids)

    check_results: list[ControlledVerificationCheckResult] = []
    for check_id in requested_ids:
        check = plan_checks[check_id]
        allowed = _allowlisted_check(check)
        if allowed.reason_code is not None:
            check_results.append(_blocked_check(check, allowed.reason_code, allowed.reason, allowed.command_kind))
            return _run_result(
                status=CONTROLLED_VERIFICATION_BLOCKED,
                reason_code=allowed.reason_code,
                reason=allowed.reason,
                plan=plan,
                check_ids=requested_ids,
                check_results=tuple(check_results),
            )
        try:
            completed = run_bounded_subprocess(
                allowed.args,
                cwd=request.workspace_root,
                env=build_subprocess_env(inherit_names=(), fixed=_MINIMAL_ENV),
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_preview, stdout_truncated = _bound_output(_timeout_output(exc.stdout), max_output_bytes)
            stderr_preview, stderr_truncated = _bound_output(_timeout_output(exc.stderr), max_output_bytes)
            check_results.append(
                ControlledVerificationCheckResult(
                    check_id=check.check_id,
                    status=CONTROLLED_VERIFICATION_CHECK_TIMEOUT,
                    reason_code=CONTROLLED_VERIFICATION_TIMEOUT,
                    reason="controlled verification check timed out",
                    command_kind=allowed.command_kind,
                    test_target=check.test_target,
                    exit_code=None,
                    timeout_expired=True,
                    stdout_preview=stdout_preview,
                    stderr_preview=stderr_preview,
                    stdout_truncated=stdout_truncated,
                    stderr_truncated=stderr_truncated,
                    execution_attempted=True,
                    subprocess_started=True,
                )
            )
            continue
        except Exception as exc:
            stderr_preview, stderr_truncated = _bound_output(type(exc).__name__, max_output_bytes)
            check_results.append(
                ControlledVerificationCheckResult(
                    check_id=check.check_id,
                    status=CONTROLLED_VERIFICATION_CHECK_FAIL,
                    reason_code=CONTROLLED_VERIFICATION_INTERNAL_ERROR,
                    reason="controlled verification caught an internal execution error",
                    command_kind=allowed.command_kind,
                    test_target=check.test_target,
                    exit_code=None,
                    timeout_expired=False,
                    stdout_preview="",
                    stderr_preview=stderr_preview,
                    stdout_truncated=False,
                    stderr_truncated=stderr_truncated,
                    execution_attempted=True,
                    subprocess_started=True,
                )
            )
            continue

        stdout_preview, stdout_truncated = _bound_output(completed.stdout, max_output_bytes)
        stderr_preview, stderr_truncated = _bound_output(completed.stderr, max_output_bytes)
        passed = completed.returncode == 0
        check_results.append(
            ControlledVerificationCheckResult(
                check_id=check.check_id,
                status=CONTROLLED_VERIFICATION_CHECK_PASS if passed else CONTROLLED_VERIFICATION_CHECK_FAIL,
                reason_code=CONTROLLED_VERIFICATION_CHECK_PASSED if passed else CONTROLLED_VERIFICATION_CHECK_FAILED,
                reason="controlled verification check passed" if passed else "controlled verification check failed",
                command_kind=allowed.command_kind,
                test_target=check.test_target,
                exit_code=completed.returncode,
                timeout_expired=False,
                stdout_preview=stdout_preview,
                stderr_preview=stderr_preview,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
                execution_attempted=True,
                subprocess_started=True,
            )
        )

    if all(item.status == CONTROLLED_VERIFICATION_CHECK_PASS for item in check_results):
        return _run_result(
            status=CONTROLLED_VERIFICATION_PASS,
            reason_code=CONTROLLED_VERIFICATION_PASS,
            reason="all controlled post-patch verification checks passed",
            plan=plan,
            check_ids=requested_ids,
            check_results=tuple(check_results),
        )
    if any(item.status in (CONTROLLED_VERIFICATION_CHECK_PASS, CONTROLLED_VERIFICATION_CHECK_FAIL, CONTROLLED_VERIFICATION_CHECK_TIMEOUT) for item in check_results):
        status = CONTROLLED_VERIFICATION_FAIL
        if any(item.status == CONTROLLED_VERIFICATION_CHECK_PASS for item in check_results) and any(
            item.status != CONTROLLED_VERIFICATION_CHECK_PASS for item in check_results
        ):
            status = CONTROLLED_VERIFICATION_PARTIAL
        return _run_result(
            status=status,
            reason_code=CONTROLLED_VERIFICATION_CHECK_FAILED,
            reason="one or more controlled post-patch verification checks failed",
            plan=plan,
            check_ids=requested_ids,
            check_results=tuple(check_results),
        )
    return _run_result(
        status=CONTROLLED_VERIFICATION_BLOCKED,
        reason_code=CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN,
        reason="no controlled verification checks were executed",
        plan=plan,
        check_ids=requested_ids,
        check_results=tuple(check_results),
    )


@dataclass(frozen=True)
class _AllowedCheck:
    command_kind: str
    args: tuple[str, ...]
    reason_code: str | None = None
    reason: str = ""


def _allowlisted_check(check: PostPatchVerificationCheck) -> _AllowedCheck:
    command = _normalized_command(check.command)
    if _unsafe_command(command):
        return _AllowedCheck(COMMAND_KIND_UNSUPPORTED, (), CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND, "check command contains blocked shell, git, provider, network, package, browser, env, or secret pattern")
    if check.check_kind == CHECK_KIND_COMPILE:
        if check.check_id == "compileall-runtime-tests" and command == "python3 -m compileall runtime tests":
            return _AllowedCheck(COMMAND_KIND_COMPILEALL, (sys.executable, "-m", "compileall", "runtime", "tests"))
        return _AllowedCheck(COMMAND_KIND_UNSUPPORTED, (), CONTROLLED_VERIFICATION_BLOCKED_UNSUPPORTED_CHECK_KIND, "compile check is not in the controlled allowlist")
    if check.check_kind in (CHECK_KIND_TEST, CHECK_KIND_STATIC):
        if check.test_target == "tests" and _is_full_discovery_command(command):
            return _AllowedCheck(COMMAND_KIND_UNITTEST_DISCOVER, (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-v"))
        if _safe_test_module(check.test_target):
            expected = f"PYTHONPATH=runtime:. python3 -m unittest {check.test_target} -v"
            if command == _normalized_command(expected):
                return _AllowedCheck(COMMAND_KIND_UNITTEST_FOCUSED, (sys.executable, "-m", "unittest", check.test_target or "", "-v"))
            return _AllowedCheck(COMMAND_KIND_UNSUPPORTED, (), CONTROLLED_VERIFICATION_BLOCKED_CHECK_METADATA_MISMATCH, "focused unittest check metadata does not match the structured test target")
        return _AllowedCheck(COMMAND_KIND_UNSUPPORTED, (), CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_TEST_TARGET, "test target is outside the controlled tests.* allowlist")
    return _AllowedCheck(COMMAND_KIND_UNSUPPORTED, (), CONTROLLED_VERIFICATION_BLOCKED_UNSUPPORTED_CHECK_KIND, "check kind is metadata-only or unsupported for Step 26 execution")


def _evidence_error(request: ControlledVerificationRunRequest, plan: PostPatchVerificationPlanResult) -> str | None:
    if not _full_hash(request.expected_plan_hash) or request.expected_plan_hash != plan.plan_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH
    if plan.plan.plan_hash != plan.plan_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH
    if _expected_plan_hash(plan) != plan.plan_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH
    if tuple(check.to_dict() for check in plan.checks) != tuple(check.to_dict() for check in plan.plan.checks):
        return CONTROLLED_VERIFICATION_BLOCKED_CHECK_METADATA_MISMATCH
    if not _full_hash(request.expected_apply_hash) or request.expected_apply_hash != plan.apply_hash or plan.plan.apply_hash != plan.apply_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH
    if not _full_hash(request.expected_patch_preview_hash) or request.expected_patch_preview_hash != plan.patch_preview_hash or plan.plan.patch_preview_hash != plan.patch_preview_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH
    if not _full_hash(request.expected_patch_policy_hash) or request.expected_patch_policy_hash != plan.patch_policy_hash or plan.plan.patch_policy_hash != plan.patch_policy_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH
    if not _full_hash(request.expected_patch_barrier_hash) or request.expected_patch_barrier_hash != plan.patch_barrier_hash or plan.plan.patch_barrier_hash != plan.patch_barrier_hash:
        return CONTROLLED_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH
    if tuple(plan.target_paths) != tuple(plan.plan.target_paths):
        return CONTROLLED_VERIFICATION_BLOCKED_TARGET_MISMATCH
    return None


def _expected_plan_hash(plan: PostPatchVerificationPlanResult) -> str:
    material = {
        "schema_version": "AOIA_POST_PATCH_VERIFICATION_PLAN_1A",
        "status": plan.plan.status,
        "apply_hash": plan.plan.apply_hash,
        "patch_preview_hash": plan.plan.patch_preview_hash,
        "patch_policy_hash": plan.plan.patch_policy_hash,
        "patch_barrier_hash": plan.plan.patch_barrier_hash,
        "target_paths": list(plan.plan.target_paths),
        "applied_content_hashes": [list(item) for item in plan.plan.applied_content_hashes],
        "policy_status": plan.plan.policy_status,
        "apply_status": plan.plan.apply_status,
        "scope_classification": plan.plan.scope_classification,
        "checks": [item.to_dict() for item in plan.plan.checks],
        "reason_codes": list(plan.plan.reason_codes),
        "risk_flags": list(plan.plan.risk_flags),
    }
    return compute_post_patch_verification_plan_hash(material)


def _workspace_error(workspace_root: str, target_paths: tuple[str, ...]) -> str | None:
    root = validate_workspace_root(workspace_root)
    if not root.allowed:
        return CONTROLLED_VERIFICATION_BLOCKED_WORKSPACE_GUARD
    for target_path in target_paths:
        if not _safe_plan_target(root.workspace_root or "", target_path):
            return CONTROLLED_VERIFICATION_BLOCKED_WORKSPACE_GUARD
    return None


def _safe_plan_target(workspace_root: str, target_path: str) -> bool:
    if not isinstance(target_path, str):
        return False
    candidate_text = target_path.strip()
    if not candidate_text or "\x00" in candidate_text or "\\" in candidate_text:
        return False
    path = PurePosixPath(candidate_text)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
        return False
    root = Path(workspace_root)
    candidate = root / candidate_text
    current = root
    for part in path.parts[:-1]:
        current = current / part
        if current.is_symlink():
            return False
    if candidate.is_symlink() or (candidate.exists() and candidate.is_dir()):
        return False
    try:
        resolved = candidate.resolve(strict=False)
        root_resolved = root.resolve(strict=True)
    except OSError:
        return False
    return root_resolved == resolved or root_resolved in resolved.parents


def _requested_check_ids(value: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], str | None]:
    if not isinstance(value, (tuple, list)) or not value:
        return (), CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return (), CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN
        text = item.strip()
        if text in normalized:
            return (), CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN
        normalized.append(text)
    return tuple(sorted(normalized)), None


def _is_full_discovery_command(command: str) -> bool:
    return command in {
        'PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v',
        "PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p 'test*.py' -v",
        "PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p test*.py -v",
    }


def _safe_test_module(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    if not value.startswith("tests.") or value.startswith("/") or "\\" in value or "/" in value:
        return False
    if ".." in value or value.endswith(".") or ".-" in value:
        return False
    return all(part and part.replace("_", "").isalnum() for part in value.split("."))


def _unsafe_command(command: str) -> bool:
    if not isinstance(command, str) or not command:
        return True
    check = command.replace('"test*.py"', "").replace("'test*.py'", "").replace(" test*.py ", " ")
    if "*" in check:
        return True
    lowered = f" {check.casefold()} "
    return any(term in lowered for term in _BLOCKED_COMMAND_TERMS)


def _normalized_command(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _blocked_check(
    check: PostPatchVerificationCheck,
    reason_code: str,
    reason: str,
    command_kind: str = COMMAND_KIND_UNSUPPORTED,
) -> ControlledVerificationCheckResult:
    return ControlledVerificationCheckResult(
        check_id=check.check_id,
        status=CONTROLLED_VERIFICATION_CHECK_BLOCKED,
        reason_code=reason_code,
        reason=reason,
        command_kind=command_kind,
        test_target=check.test_target,
        exit_code=None,
        timeout_expired=False,
        stdout_preview="",
        stderr_preview="",
        stdout_truncated=False,
        stderr_truncated=False,
        execution_attempted=False,
        subprocess_started=False,
    )


def _blocked(
    reason_code: str,
    reason: str,
    *,
    plan: PostPatchVerificationPlanResult | None = None,
    check_ids: tuple[str, ...] = (),
) -> ControlledVerificationRunResult:
    return _run_result(
        status=CONTROLLED_VERIFICATION_BLOCKED,
        reason_code=reason_code,
        reason=reason,
        plan=plan,
        check_ids=check_ids,
        check_results=(),
    )


def _run_result(
    *,
    status: str,
    reason_code: str,
    reason: str,
    plan: PostPatchVerificationPlanResult | None,
    check_ids: tuple[str, ...],
    check_results: tuple[ControlledVerificationCheckResult, ...],
) -> ControlledVerificationRunResult:
    material = {
        "schema_version": _SCHEMA_VERSION,
        "status": status,
        "plan_hash": plan.plan_hash if plan is not None else None,
        "apply_hash": plan.apply_hash if plan is not None else None,
        "patch_preview_hash": plan.patch_preview_hash if plan is not None else None,
        "patch_policy_hash": plan.patch_policy_hash if plan is not None else None,
        "patch_barrier_hash": plan.patch_barrier_hash if plan is not None else None,
        "target_paths": list(plan.target_paths) if plan is not None else [],
        "check_ids": list(check_ids),
        "check_results": [item.to_dict() for item in check_results],
        "reason_codes": [reason_code],
    }
    return ControlledVerificationRunResult(
        status=status,
        run_hash=compute_controlled_verification_hash(material),
        plan_hash=plan.plan_hash if plan is not None else None,
        apply_hash=plan.apply_hash if plan is not None else None,
        patch_preview_hash=plan.patch_preview_hash if plan is not None else None,
        patch_policy_hash=plan.patch_policy_hash if plan is not None else None,
        patch_barrier_hash=plan.patch_barrier_hash if plan is not None else None,
        target_paths=plan.target_paths if plan is not None else (),
        check_ids=check_ids,
        check_results=check_results,
        reason_codes=(reason_code,),
        reason=reason,
    )


def _bound_output(value: Any, max_bytes: int) -> tuple[str, bool]:
    if value is None:
        return "", False
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    return encoded[:max_bytes].decode("utf-8", errors="replace"), True


def _timeout_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _bounded_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    if isinstance(value, bool):
        return default
    if not isinstance(value, int):
        return default
    if value < minimum or value > maximum:
        return default
    return value


def _has_authority_claim(value: Any) -> bool:
    return any(getattr(value, field_name, False) is not False for field_name in _AUTHORITY_FIELDS)


def _full_hash(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip().lower()
        if len(text) == 64 and all(character in _SHA256_HEX for character in text):
            return text
    return None


def _stable_json_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _stable_json_value(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _stable_json_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, tuple | list):
        return [_stable_json_value(item) for item in value]
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
