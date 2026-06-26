from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from runtime.patches.patch_preview import PATCH_PREVIEW_READY, PatchPreview, PatchPreviewResult


PATCH_POLICY_PASS = "PASS"
PATCH_POLICY_BLOCK = "BLOCK"
PATCH_POLICY_NEEDS_REVIEW = "NEEDS_REVIEW"

PATCH_POLICY_PROFILE_NAME = "AOIA_PATCH_LOCAL_POLICY"
PATCH_POLICY_PROFILE_VERSION = "1A"

PATCH_POLICY_BLOCKED_MISSING_PREVIEW = "PATCH_POLICY_BLOCKED_MISSING_PREVIEW"
PATCH_POLICY_BLOCKED_MALFORMED_PREVIEW = "PATCH_POLICY_BLOCKED_MALFORMED_PREVIEW"
PATCH_POLICY_BLOCKED_PREVIEW_NOT_READY = "PATCH_POLICY_BLOCKED_PREVIEW_NOT_READY"
PATCH_POLICY_BLOCKED_MISSING_PREVIEW_HASH = "PATCH_POLICY_BLOCKED_MISSING_PREVIEW_HASH"
PATCH_POLICY_BLOCKED_MISSING_TARGETS = "PATCH_POLICY_BLOCKED_MISSING_TARGETS"
PATCH_POLICY_BLOCKED_UNSAFE_TARGET = "PATCH_POLICY_BLOCKED_UNSAFE_TARGET"
PATCH_POLICY_BLOCKED_DUPLICATE_TARGET = "PATCH_POLICY_BLOCKED_DUPLICATE_TARGET"
PATCH_POLICY_BLOCKED_PREVIEW_AUTHORITY = "PATCH_POLICY_BLOCKED_PREVIEW_AUTHORITY"
PATCH_POLICY_BLOCKED_SECRET_TARGET = "PATCH_POLICY_BLOCKED_SECRET_TARGET"
PATCH_POLICY_BLOCKED_UNSUPPORTED_TARGET = "PATCH_POLICY_BLOCKED_UNSUPPORTED_TARGET"

PATCH_POLICY_FINDING_BOUNDARY_TARGET = "boundary_target_needs_review"
PATCH_POLICY_FINDING_RUNTIME_SCOPE = "runtime_scope"
PATCH_POLICY_FINDING_TEST_SCOPE = "test_scope"
PATCH_POLICY_FINDING_DOCS_SCOPE = "docs_scope"
PATCH_POLICY_FINDING_CONFIG_SCOPE = "config_scope"
PATCH_POLICY_FINDING_SCRIPT_SCOPE = "script_scope"
PATCH_POLICY_FINDING_HIDDEN_SCOPE = "hidden_scope"
PATCH_POLICY_FINDING_MULTI_FILE = "multi_file_patch"
PATCH_POLICY_FINDING_LARGE_PATCH = "large_patch"
PATCH_POLICY_FINDING_DIFF_TRUNCATED = "diff_truncated"
PATCH_POLICY_FINDING_CREATE_OPERATION = "create_operation"
PATCH_POLICY_FINDING_AUTHORITY_TEXT = "authority_language_detected"
PATCH_POLICY_FINDING_CAPABILITY_TEXT = "capability_text_detected"

PATCH_POLICY_RISK_BLOCKED_TARGET = "blocked_target"
PATCH_POLICY_RISK_HIGH_RISK_BOUNDARY = "high_risk_boundary"
PATCH_POLICY_RISK_RUNTIME_CHANGE = "runtime_change"
PATCH_POLICY_RISK_TEST_CHANGE = "test_change"
PATCH_POLICY_RISK_DOCS_CHANGE = "docs_change"
PATCH_POLICY_RISK_CONFIG_CHANGE = "config_change"
PATCH_POLICY_RISK_SCRIPT_CHANGE = "script_change"
PATCH_POLICY_RISK_HIDDEN_CHANGE = "hidden_change"
PATCH_POLICY_RISK_MULTI_FILE = "multi_file"
PATCH_POLICY_RISK_LARGE_PATCH = "large_patch"
PATCH_POLICY_RISK_DIFF_TRUNCATED = "diff_truncated"
PATCH_POLICY_RISK_CREATE_OPERATION = "create_operation"
PATCH_POLICY_RISK_AUTHORITY_LANGUAGE = "authority_language"
PATCH_POLICY_RISK_CAPABILITY_TEXT = "capability_text"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_LARGE_PATCH_BYTES = 100_000
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
_HIGH_RISK_BOUNDARY_TARGETS = frozenset(
    {
        "runtime/control_write.py",
        "runtime/human_decision_gated_artifact_write.py",
        "runtime/safety/sandbox_artifact_runner.py",
        "runtime/safety/write_kill_switch.py",
        "runtime/safety/workspace_guard.py",
        "runtime/providers/gateway.py",
        "runtime/audit/durable_log.py",
        "runtime/bridges/proposal_preview_gate_binding.py",
    }
)
_SECRET_TARGET_MARKERS = (
    ".env",
    "private_key",
    "id_rsa",
    "credentials",
    "credential",
    "secrets",
    "secret",
)
_LOCKFILE_TARGETS = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "pipfile.lock",
        "cargo.lock",
    }
)
_BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".bin",
        ".exe",
    }
)
_AUTHORITY_TEXT_PATTERNS = (
    "can_write=True",
    "can_execute=True",
    "provider_output_trusted=True",
    "metadata_authority=True",
    "write_authority_granted=True",
    "execution_authority_granted=True",
)
_CAPABILITY_TEXT_PATTERNS = (
    "subprocess",
    "os.system",
    "Popen",
    "socket",
    "webbrowser",
    "requests",
    "httpx",
    "git" + " push",
    "git" + " commit",
    "pip install",
    "npm install",
    "eval(",
    "exec(",
)


@dataclass(frozen=True)
class PatchPolicyProfile:
    name: str = PATCH_POLICY_PROFILE_NAME
    version: str = PATCH_POLICY_PROFILE_VERSION
    large_patch_bytes: int = _LARGE_PATCH_BYTES


@dataclass(frozen=True)
class PatchPolicyFinding:
    code: str
    severity: str
    target_path: str | None
    scope: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "target_path": self.target_path,
            "scope": self.scope,
            "message": self.message,
        }


@dataclass(frozen=True)
class PatchPolicyCheckResult:
    status: str
    policy_profile_name: str
    policy_profile_version: str
    policy_hash: str
    patch_preview_hash: str | None
    target_paths: tuple[str, ...]
    file_count: int
    scope_classification: str
    findings: tuple[PatchPolicyFinding, ...]
    risk_flags: tuple[str, ...]
    reason_codes: tuple[str, ...]
    reason: str
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
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "policy_profile_name": self.policy_profile_name,
            "policy_profile_version": self.policy_profile_version,
            "policy_hash": self.policy_hash,
            "patch_preview_hash": self.patch_preview_hash,
            "target_paths": list(self.target_paths),
            "file_count": self.file_count,
            "scope_classification": self.scope_classification,
            "findings": [item.to_dict() for item in self.findings],
            "risk_flags": list(self.risk_flags),
            "reason_codes": list(self.reason_codes),
            "reason": self.reason,
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


def canonical_patch_policy_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_patch_policy_hash(value: Any) -> str:
    return hashlib.sha256(canonical_patch_policy_json(value).encode("utf-8")).hexdigest()


def check_patch_local_policy(
    patch_preview: PatchPreview | PatchPreviewResult | None,
    *,
    profile: PatchPolicyProfile | None = None,
) -> PatchPolicyCheckResult:
    policy_profile = profile or PatchPolicyProfile()
    preview, intake_error = _coerce_preview(patch_preview)
    if intake_error is not None:
        return _result(
            status=PATCH_POLICY_BLOCK,
            profile=policy_profile,
            patch_preview_hash=None,
            target_paths=(),
            file_count=0,
            scope_classification="unknown",
            findings=(
                PatchPolicyFinding(
                    code=intake_error,
                    severity="block",
                    target_path=None,
                    scope="unknown",
                    message="patch preview is missing, malformed, or not ready",
                ),
            ),
            risk_flags=(PATCH_POLICY_RISK_BLOCKED_TARGET,),
            reason_codes=(intake_error,),
            reason="patch policy blocked before reviewable preview metadata",
        )

    assert preview is not None
    structural_error = _structural_error(preview)
    if structural_error is not None:
        return _result(
            status=PATCH_POLICY_BLOCK,
            profile=policy_profile,
            patch_preview_hash=preview.preview_hash,
            target_paths=tuple(preview.target_paths),
            file_count=preview.total_file_count,
            scope_classification=_scope_classification(tuple(preview.target_paths)),
            findings=(
                PatchPolicyFinding(
                    code=structural_error,
                    severity="block",
                    target_path=None,
                    scope="unknown",
                    message="patch preview metadata failed local policy structural checks",
                ),
            ),
            risk_flags=(PATCH_POLICY_RISK_BLOCKED_TARGET,),
            reason_codes=(structural_error,),
            reason="patch policy blocked malformed preview metadata",
        )

    findings: list[PatchPolicyFinding] = []
    risk_flags: set[str] = set()
    for file_preview in preview.files:
        path = file_preview.target_path
        scope = _path_scope(path)
        _add_scope_risks(scope, risk_flags)

        if path in _HIGH_RISK_BOUNDARY_TARGETS or _boundary_like_path(path):
            findings.append(
                PatchPolicyFinding(
                    code=PATCH_POLICY_FINDING_BOUNDARY_TARGET,
                    severity="review",
                    target_path=path,
                    scope=scope,
                    message="patch targets an authority, provider, gate, write, or audit boundary module",
                )
            )
            risk_flags.add(PATCH_POLICY_RISK_HIGH_RISK_BOUNDARY)
        if file_preview.operation == "create":
            findings.append(
                PatchPolicyFinding(
                    code=PATCH_POLICY_FINDING_CREATE_OPERATION,
                    severity="review",
                    target_path=path,
                    scope=scope,
                    message="patch creates a file",
                )
            )
            risk_flags.add(PATCH_POLICY_RISK_CREATE_OPERATION)
        if file_preview.diff_truncated:
            findings.append(
                PatchPolicyFinding(
                    code=PATCH_POLICY_FINDING_DIFF_TRUNCATED,
                    severity="review",
                    target_path=path,
                    scope=scope,
                    message="patch diff was truncated in preview metadata",
                )
            )
            risk_flags.add(PATCH_POLICY_RISK_DIFF_TRUNCATED)
        text = file_preview.diff_preview or ""
        if _contains_any(text, _AUTHORITY_TEXT_PATTERNS):
            findings.append(
                PatchPolicyFinding(
                    code=PATCH_POLICY_FINDING_AUTHORITY_TEXT,
                    severity="review",
                    target_path=path,
                    scope=scope,
                    message="patch preview text contains authority-like language",
                )
            )
            risk_flags.add(PATCH_POLICY_RISK_AUTHORITY_LANGUAGE)
        if _contains_any(text, _CAPABILITY_TEXT_PATTERNS):
            findings.append(
                PatchPolicyFinding(
                    code=PATCH_POLICY_FINDING_CAPABILITY_TEXT,
                    severity="review",
                    target_path=path,
                    scope=scope,
                    message="patch preview text contains risky capability language",
                )
            )
            risk_flags.add(PATCH_POLICY_RISK_CAPABILITY_TEXT)

    if preview.total_file_count > 1:
        findings.append(
            PatchPolicyFinding(
                code=PATCH_POLICY_FINDING_MULTI_FILE,
                severity="review",
                target_path=None,
                scope=_scope_classification(preview.target_paths),
                message="patch changes multiple files",
            )
        )
        risk_flags.add(PATCH_POLICY_RISK_MULTI_FILE)
    if preview.total_proposed_size_bytes > policy_profile.large_patch_bytes:
        findings.append(
            PatchPolicyFinding(
                code=PATCH_POLICY_FINDING_LARGE_PATCH,
                severity="review",
                target_path=None,
                scope=_scope_classification(preview.target_paths),
                message="patch proposed content exceeds local large-patch threshold",
            )
        )
        risk_flags.add(PATCH_POLICY_RISK_LARGE_PATCH)

    reason_codes = tuple(sorted({finding.code for finding in findings}))
    status = PATCH_POLICY_PASS if not findings else PATCH_POLICY_NEEDS_REVIEW
    return _result(
        status=status,
        profile=policy_profile,
        patch_preview_hash=preview.preview_hash,
        target_paths=tuple(preview.target_paths),
        file_count=preview.total_file_count,
        scope_classification=_scope_classification(preview.target_paths),
        findings=tuple(sorted(findings, key=lambda item: (item.severity, item.code, item.target_path or ""))),
        risk_flags=tuple(sorted(risk_flags)),
        reason_codes=reason_codes,
        reason="patch policy passed with review metadata only" if status == PATCH_POLICY_PASS else "patch policy requires human review metadata",
    )


def _coerce_preview(value: PatchPreview | PatchPreviewResult | None) -> tuple[PatchPreview | None, str | None]:
    if value is None:
        return None, PATCH_POLICY_BLOCKED_MISSING_PREVIEW
    if isinstance(value, PatchPreviewResult):
        if value.patch_preview is None:
            return None, PATCH_POLICY_BLOCKED_MISSING_PREVIEW
        if value.preview_ready is not True or value.status != PATCH_PREVIEW_READY:
            return None, PATCH_POLICY_BLOCKED_PREVIEW_NOT_READY
        return value.patch_preview, None
    if isinstance(value, PatchPreview):
        return value, None
    return None, PATCH_POLICY_BLOCKED_MALFORMED_PREVIEW


def _structural_error(preview: PatchPreview) -> str | None:
    if preview.status != PATCH_PREVIEW_READY:
        return PATCH_POLICY_BLOCKED_PREVIEW_NOT_READY
    if not _full_hash(preview.preview_hash):
        return PATCH_POLICY_BLOCKED_MISSING_PREVIEW_HASH
    if not preview.target_paths or not preview.files:
        return PATCH_POLICY_BLOCKED_MISSING_TARGETS
    if _has_authority_flag(preview):
        return PATCH_POLICY_BLOCKED_PREVIEW_AUTHORITY
    seen: set[str] = set()
    file_targets = tuple(item.target_path for item in preview.files)
    if tuple(preview.target_paths) != file_targets:
        return PATCH_POLICY_BLOCKED_MALFORMED_PREVIEW
    for path in preview.target_paths:
        normalized, path_error = _safe_target(path)
        if path_error is not None:
            return path_error
        if normalized in seen:
            return PATCH_POLICY_BLOCKED_DUPLICATE_TARGET
        seen.add(normalized)
        if _secret_like_target(normalized):
            return PATCH_POLICY_BLOCKED_SECRET_TARGET
        if _unsupported_target(normalized):
            return PATCH_POLICY_BLOCKED_UNSUPPORTED_TARGET
    return None


def _result(
    *,
    status: str,
    profile: PatchPolicyProfile,
    patch_preview_hash: str | None,
    target_paths: tuple[str, ...],
    file_count: int,
    scope_classification: str,
    findings: tuple[PatchPolicyFinding, ...],
    risk_flags: tuple[str, ...],
    reason_codes: tuple[str, ...],
    reason: str,
) -> PatchPolicyCheckResult:
    material = {
        "schema_version": "AOIA_PATCH_POLICY_1A",
        "status": status,
        "policy_profile_name": profile.name,
        "policy_profile_version": profile.version,
        "patch_preview_hash": patch_preview_hash,
        "target_paths": list(target_paths),
        "file_count": file_count,
        "scope_classification": scope_classification,
        "findings": [item.to_dict() for item in findings],
        "risk_flags": list(risk_flags),
        "reason_codes": list(reason_codes),
    }
    policy_hash = compute_patch_policy_hash(material)
    return PatchPolicyCheckResult(
        status=status,
        policy_profile_name=profile.name,
        policy_profile_version=profile.version,
        policy_hash=policy_hash,
        patch_preview_hash=patch_preview_hash,
        target_paths=target_paths,
        file_count=file_count,
        scope_classification=scope_classification,
        findings=findings,
        risk_flags=risk_flags,
        reason_codes=reason_codes,
        reason=reason,
    )


def _safe_target(value: object) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    candidate = value.strip()
    if not candidate or "\x00" in candidate:
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    if "\\" in candidate:
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    path = PurePosixPath(candidate)
    if ".." in path.parts:
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    if ".git" in path.parts:
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    normalized = path.as_posix()
    if normalized in ("", "."):
        return "", PATCH_POLICY_BLOCKED_UNSAFE_TARGET
    return normalized, None


def _path_scope(path: str) -> str:
    parts = PurePosixPath(path).parts
    if any(part.startswith(".") for part in parts):
        return "hidden"
    if path.startswith("runtime/"):
        return "runtime"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("docs/") or path.endswith(".md"):
        return "docs"
    if path.startswith("scripts/") or path.endswith(".sh"):
        return "scripts"
    if PurePosixPath(path).name in _LOCKFILE_TARGETS or path.endswith((".toml", ".yaml", ".yml", ".ini", ".cfg", ".json")):
        return "config"
    return "unknown"


def _scope_classification(target_paths: tuple[str, ...]) -> str:
    scopes = {_path_scope(path) for path in target_paths}
    if not scopes:
        return "unknown"
    if len(scopes) == 1:
        return next(iter(scopes))
    return "mixed"


def _add_scope_risks(scope: str, risk_flags: set[str]) -> None:
    if scope == "runtime":
        risk_flags.add(PATCH_POLICY_RISK_RUNTIME_CHANGE)
    elif scope == "tests":
        risk_flags.add(PATCH_POLICY_RISK_TEST_CHANGE)
    elif scope == "docs":
        risk_flags.add(PATCH_POLICY_RISK_DOCS_CHANGE)
    elif scope == "config":
        risk_flags.add(PATCH_POLICY_RISK_CONFIG_CHANGE)
    elif scope == "scripts":
        risk_flags.add(PATCH_POLICY_RISK_SCRIPT_CHANGE)
    elif scope == "hidden":
        risk_flags.add(PATCH_POLICY_RISK_HIDDEN_CHANGE)


def _secret_like_target(path: str) -> bool:
    lowered = PurePosixPath(path).name.casefold()
    return any(marker in lowered for marker in _SECRET_TARGET_MARKERS)


def _unsupported_target(path: str) -> bool:
    lowered = PurePosixPath(path).suffix.casefold()
    return lowered in _BINARY_EXTENSIONS or PurePosixPath(path).name.casefold() in _LOCKFILE_TARGETS


def _boundary_like_path(path: str) -> bool:
    lowered = path.casefold()
    return any(marker in lowered for marker in ("authority", "gate", "control_write", "sandbox", "provider", "ledger"))


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(pattern.casefold() in lowered for pattern in patterns)


def _has_authority_flag(value: PatchPreview) -> bool:
    return any(getattr(value, field_name, False) is not False for field_name in _AUTHORITY_FIELDS)


def _full_hash(value: Any) -> str | None:
    if isinstance(value, str) and _SHA256_HEX.fullmatch(value):
        return value
    return None


def _stable_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
