from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SAFE_EXECUTION_SANDBOX_SCHEMA_VERSION = "AOIA_SAFE_EXECUTION_SANDBOX_1A"
_MAX_SUMMARY_CHARS = 420


class SafeExecutionStatus(str, Enum):
    SANDBOX_ENVELOPE_READY = "SANDBOX_ENVELOPE_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED_UNSAFE_EXECUTION_REQUEST = "BLOCKED_UNSAFE_EXECUTION_REQUEST"
    BLOCKED_NETWORK_ACCESS = "BLOCKED_NETWORK_ACCESS"
    BLOCKED_ENV_ACCESS = "BLOCKED_ENV_ACCESS"
    BLOCKED_API_KEY_ACCESS = "BLOCKED_API_KEY_ACCESS"
    BLOCKED_BROWSER_ACCESS = "BLOCKED_BROWSER_ACCESS"
    BLOCKED_FILESYSTEM_WRITE = "BLOCKED_FILESYSTEM_WRITE"
    BLOCKED_UNSAFE_PATH = "BLOCKED_UNSAFE_PATH"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INCONSISTENT_METADATA = "INCONSISTENT_METADATA"


class SafeExecutionFlag(str, Enum):
    SANDBOX_ENVELOPE_METADATA_ONLY = "SANDBOX_ENVELOPE_METADATA_ONLY"
    NO_EXECUTION = "NO_EXECUTION"
    NO_SUBPROCESS = "NO_SUBPROCESS"
    NO_SHELL = "NO_SHELL"
    NO_COMMAND_EXECUTION = "NO_COMMAND_EXECUTION"
    NO_TEST_EXECUTION = "NO_TEST_EXECUTION"
    NO_BROWSER = "NO_BROWSER"
    NO_DOWNLOAD = "NO_DOWNLOAD"
    NO_FILE_READ = "NO_FILE_READ"
    NO_FILE_WRITE = "NO_FILE_WRITE"
    NO_DIRECTORY_CREATE = "NO_DIRECTORY_CREATE"
    NO_NETWORK = "NO_NETWORK"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    NO_PROVIDER_CALL = "NO_PROVIDER_CALL"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    TEST_RUN_ENVELOPE = "TEST_RUN_ENVELOPE"
    STATIC_CHECK_ENVELOPE = "STATIC_CHECK_ENVELOPE"
    COMPILE_CHECK_ENVELOPE = "COMPILE_CHECK_ENVELOPE"
    DOWNLOAD_ENVELOPE_BLOCKED = "DOWNLOAD_ENVELOPE_BLOCKED"
    BROWSER_ENVELOPE_BLOCKED = "BROWSER_ENVELOPE_BLOCKED"
    GITHUB_ENVELOPE_NOT_YET_GOVERNED = "GITHUB_ENVELOPE_NOT_YET_GOVERNED"
    SHELL_COMMAND_BLOCKED = "SHELL_COMMAND_BLOCKED"
    UNSAFE_COMMAND = "UNSAFE_COMMAND"
    UNSAFE_PATH = "UNSAFE_PATH"
    PATH_TRAVERSAL_BLOCKED = "PATH_TRAVERSAL_BLOCKED"
    ABSOLUTE_PATH_BLOCKED = "ABSOLUTE_PATH_BLOCKED"
    NETWORK_ACCESS_BLOCKED = "NETWORK_ACCESS_BLOCKED"
    ENV_ACCESS_BLOCKED = "ENV_ACCESS_BLOCKED"
    API_KEY_ACCESS_BLOCKED = "API_KEY_ACCESS_BLOCKED"
    FILESYSTEM_WRITE_BLOCKED = "FILESYSTEM_WRITE_BLOCKED"
    BROWSER_ACCESS_BLOCKED = "BROWSER_ACCESS_BLOCKED"
    PROVIDER_ACCESS_BLOCKED = "PROVIDER_ACCESS_BLOCKED"
    SUSPICIOUS_AUTHORITY_CLAIM = "SUSPICIOUS_AUTHORITY_CLAIM"
    SECRET_OR_TOKEN_PATTERN = "SECRET_OR_TOKEN_PATTERN"
    INCONSISTENT_HASH_METADATA = "INCONSISTENT_HASH_METADATA"
    ACTION_PROPOSAL_METADATA_ONLY = "ACTION_PROPOSAL_METADATA_ONLY"
    TOOL_CALL_PREVIEW_METADATA_ONLY = "TOOL_CALL_PREVIEW_METADATA_ONLY"
    TOOL_REGISTRY_METADATA_ONLY = "TOOL_REGISTRY_METADATA_ONLY"
    INTENT_ROUTE_METADATA_ONLY = "INTENT_ROUTE_METADATA_ONLY"
    LOCAL_POLICY_METADATA_ONLY = "LOCAL_POLICY_METADATA_ONLY"
    TEST_RUNNER_METADATA_ONLY = "TEST_RUNNER_METADATA_ONLY"
    DOWNLOAD_GOVERNANCE_METADATA_ONLY = "DOWNLOAD_GOVERNANCE_METADATA_ONLY"
    STATEMENT_GOVERNANCE_METADATA_ONLY = "STATEMENT_GOVERNANCE_METADATA_ONLY"
    BROWSER_GOVERNANCE_METADATA_ONLY = "BROWSER_GOVERNANCE_METADATA_ONLY"


class SafeExecutionKind(str, Enum):
    TEST_RUN = "TEST_RUN"
    STATIC_CHECK = "STATIC_CHECK"
    COMPILE_CHECK = "COMPILE_CHECK"
    DOWNLOAD = "DOWNLOAD"
    BROWSER_READ_ONLY = "BROWSER_READ_ONLY"
    GITHUB_READ_ONLY = "GITHUB_READ_ONLY"
    GITHUB_WRITE = "GITHUB_WRITE"
    SHELL_COMMAND = "SHELL_COMMAND"
    UNKNOWN = "UNKNOWN"


class SafeExecutionSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    CRITIC_METADATA = "CRITIC_METADATA"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SafeExecutionSandboxRequest:
    execution_kind: SafeExecutionKind | str
    requested_command: str
    workspace_root_metadata: str | None = None
    working_directory_metadata: str | None = None
    allowed_relative_paths: tuple[str, ...] | list[str] = ()
    blocked_path_patterns: tuple[str, ...] | list[str] = ("../", "/etc/passwd", "~/.ssh", ".env")
    timeout_seconds: int = 30
    max_output_bytes: int = 200000
    max_artifact_bytes: int = 1000000
    network_access: str = "BLOCKED"
    env_access: str = "BLOCKED"
    api_key_access: str = "BLOCKED"
    filesystem_write_mode: str = "BLOCKED"
    filesystem_read_mode: str = "METADATA_ONLY"
    browser_access: str = "BLOCKED"
    provider_access: str = "BLOCKED"
    source_trust: SafeExecutionSourceTrust | str = SafeExecutionSourceTrust.UNKNOWN
    source_action_proposal_id: str | None = None
    source_action_proposal_hash: str | None = None
    source_tool_call_preview_id: str | None = None
    source_tool_call_preview_hash: str | None = None
    source_intent_route_id: str | None = None
    source_intent_route_hash: str | None = None
    source_policy_check_id: str | None = None
    source_policy_check_hash: str | None = None
    source_test_runner_control_id: str | None = None
    source_test_runner_control_hash: str | None = None
    source_download_governance_id: str | None = None
    source_download_governance_hash: str | None = None
    source_statement_governance_id: str | None = None
    source_statement_governance_hash: str | None = None
    source_browser_governance_id: str | None = None
    source_browser_governance_hash: str | None = None
    source_statuses: tuple[str, ...] | list[str] = ()
    source_flags: tuple[str, ...] | list[str] = ()
    metadata: Mapping[str, Any] | None = None
    authority_claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SafeExecutionSandboxEnvelope:
    schema_version: str
    sandbox_envelope_id: str
    sandbox_envelope_hash: str
    status: SafeExecutionStatus
    execution_kind: SafeExecutionKind
    requested_command: str
    normalized_command: str
    command_hash: str
    workspace_root_metadata: str | None
    working_directory_metadata: str | None
    allowed_relative_paths: tuple[str, ...]
    blocked_path_patterns: tuple[str, ...]
    timeout_seconds: int
    max_output_bytes: int
    max_artifact_bytes: int
    network_access: str
    env_access: str
    api_key_access: str
    filesystem_write_mode: str
    filesystem_read_mode: str
    browser_access: str
    provider_access: str
    human_review_required: bool
    source_trust: SafeExecutionSourceTrust
    source_action_proposal_id: str | None
    source_action_proposal_hash: str | None
    source_tool_call_preview_id: str | None
    source_tool_call_preview_hash: str | None
    source_intent_route_id: str | None
    source_intent_route_hash: str | None
    source_policy_check_id: str | None
    source_policy_check_hash: str | None
    source_test_runner_control_id: str | None
    source_test_runner_control_hash: str | None
    source_download_governance_id: str | None
    source_download_governance_hash: str | None
    source_statement_governance_id: str | None
    source_statement_governance_hash: str | None
    source_browser_governance_id: str | None
    source_browser_governance_hash: str | None
    flags: tuple[SafeExecutionFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    execution_performed: bool = False
    subprocess_started: bool = False
    shell_invoked: bool = False
    command_executed: bool = False
    test_command_executed: bool = False
    browser_opened: bool = False
    download_performed: bool = False
    file_read: bool = False
    file_written: bool = False
    directory_created: bool = False
    network_called: bool = False
    env_read: bool = False
    api_key_loaded: bool = False
    provider_called: bool = False
    approval_created: bool = False
    gate_changed: bool = False
    tool_called: bool = False
    can_call_tool: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_change_approval_gate: bool = False
    can_change_policy: bool = False
    can_access_network: bool = False
    can_read_env: bool = False
    can_load_api_key: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text("schema_version", self.schema_version))
        object.__setattr__(self, "sandbox_envelope_id", _text("sandbox_envelope_id", self.sandbox_envelope_id))
        object.__setattr__(self, "sandbox_envelope_hash", _text("sandbox_envelope_hash", self.sandbox_envelope_hash))
        object.__setattr__(self, "status", SafeExecutionStatus(self.status))
        object.__setattr__(self, "execution_kind", SafeExecutionKind(self.execution_kind))
        object.__setattr__(self, "requested_command", _text("requested_command", self.requested_command))
        object.__setattr__(self, "normalized_command", _text("normalized_command", self.normalized_command))
        object.__setattr__(self, "command_hash", _text("command_hash", self.command_hash))
        object.__setattr__(self, "workspace_root_metadata", _optional_text(self.workspace_root_metadata))
        object.__setattr__(self, "working_directory_metadata", _optional_text(self.working_directory_metadata))
        object.__setattr__(self, "allowed_relative_paths", _text_tuple("allowed_relative_paths", self.allowed_relative_paths))
        object.__setattr__(self, "blocked_path_patterns", _text_tuple("blocked_path_patterns", self.blocked_path_patterns))
        object.__setattr__(self, "timeout_seconds", _nonnegative_int("timeout_seconds", self.timeout_seconds))
        object.__setattr__(self, "max_output_bytes", _nonnegative_int("max_output_bytes", self.max_output_bytes))
        object.__setattr__(self, "max_artifact_bytes", _nonnegative_int("max_artifact_bytes", self.max_artifact_bytes))
        object.__setattr__(self, "network_access", _access_text(self.network_access))
        object.__setattr__(self, "env_access", _access_text(self.env_access))
        object.__setattr__(self, "api_key_access", _access_text(self.api_key_access))
        object.__setattr__(self, "filesystem_write_mode", _access_text(self.filesystem_write_mode))
        object.__setattr__(self, "filesystem_read_mode", _access_text(self.filesystem_read_mode))
        object.__setattr__(self, "browser_access", _access_text(self.browser_access))
        object.__setattr__(self, "provider_access", _access_text(self.provider_access))
        object.__setattr__(self, "human_review_required", bool(self.human_review_required))
        object.__setattr__(self, "source_trust", SafeExecutionSourceTrust(self.source_trust))
        object.__setattr__(self, "source_action_proposal_id", _optional_text(self.source_action_proposal_id))
        object.__setattr__(self, "source_action_proposal_hash", _optional_text(self.source_action_proposal_hash))
        object.__setattr__(self, "source_tool_call_preview_id", _optional_text(self.source_tool_call_preview_id))
        object.__setattr__(self, "source_tool_call_preview_hash", _optional_text(self.source_tool_call_preview_hash))
        object.__setattr__(self, "source_intent_route_id", _optional_text(self.source_intent_route_id))
        object.__setattr__(self, "source_intent_route_hash", _optional_text(self.source_intent_route_hash))
        object.__setattr__(self, "source_policy_check_id", _optional_text(self.source_policy_check_id))
        object.__setattr__(self, "source_policy_check_hash", _optional_text(self.source_policy_check_hash))
        object.__setattr__(self, "source_test_runner_control_id", _optional_text(self.source_test_runner_control_id))
        object.__setattr__(self, "source_test_runner_control_hash", _optional_text(self.source_test_runner_control_hash))
        object.__setattr__(self, "source_download_governance_id", _optional_text(self.source_download_governance_id))
        object.__setattr__(self, "source_download_governance_hash", _optional_text(self.source_download_governance_hash))
        object.__setattr__(self, "source_statement_governance_id", _optional_text(self.source_statement_governance_id))
        object.__setattr__(self, "source_statement_governance_hash", _optional_text(self.source_statement_governance_hash))
        object.__setattr__(self, "source_browser_governance_id", _optional_text(self.source_browser_governance_id))
        object.__setattr__(self, "source_browser_governance_hash", _optional_text(self.source_browser_governance_hash))
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "display_summary", _bounded_text(_text("display_summary", self.display_summary)))
        for field_name in (
            "execution_performed",
            "subprocess_started",
            "shell_invoked",
            "command_executed",
            "test_command_executed",
            "browser_opened",
            "download_performed",
            "file_read",
            "file_written",
            "directory_created",
            "network_called",
            "env_read",
            "api_key_loaded",
            "provider_called",
            "approval_created",
            "gate_changed",
            "tool_called",
            "can_call_tool",
            "can_execute",
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
            "sandbox_envelope_id": self.sandbox_envelope_id,
            "sandbox_envelope_hash": self.sandbox_envelope_hash,
            "status": self.status.value,
            "execution_kind": self.execution_kind.value,
            "requested_command": self.requested_command,
            "normalized_command": self.normalized_command,
            "command_hash": self.command_hash,
            "workspace_root_metadata": self.workspace_root_metadata,
            "working_directory_metadata": self.working_directory_metadata,
            "allowed_relative_paths": list(self.allowed_relative_paths),
            "blocked_path_patterns": list(self.blocked_path_patterns),
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
            "max_artifact_bytes": self.max_artifact_bytes,
            "network_access": self.network_access,
            "env_access": self.env_access,
            "api_key_access": self.api_key_access,
            "filesystem_write_mode": self.filesystem_write_mode,
            "filesystem_read_mode": self.filesystem_read_mode,
            "browser_access": self.browser_access,
            "provider_access": self.provider_access,
            "human_review_required": self.human_review_required,
            "source_trust": self.source_trust.value,
            "source_action_proposal_id": self.source_action_proposal_id,
            "source_action_proposal_hash": self.source_action_proposal_hash,
            "source_tool_call_preview_id": self.source_tool_call_preview_id,
            "source_tool_call_preview_hash": self.source_tool_call_preview_hash,
            "source_intent_route_id": self.source_intent_route_id,
            "source_intent_route_hash": self.source_intent_route_hash,
            "source_policy_check_id": self.source_policy_check_id,
            "source_policy_check_hash": self.source_policy_check_hash,
            "source_test_runner_control_id": self.source_test_runner_control_id,
            "source_test_runner_control_hash": self.source_test_runner_control_hash,
            "source_download_governance_id": self.source_download_governance_id,
            "source_download_governance_hash": self.source_download_governance_hash,
            "source_statement_governance_id": self.source_statement_governance_id,
            "source_statement_governance_hash": self.source_statement_governance_hash,
            "source_browser_governance_id": self.source_browser_governance_id,
            "source_browser_governance_hash": self.source_browser_governance_hash,
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
            "file_read": self.file_read,
            "file_written": self.file_written,
            "directory_created": self.directory_created,
            "network_called": self.network_called,
            "env_read": self.env_read,
            "api_key_loaded": self.api_key_loaded,
            "provider_called": self.provider_called,
            "approval_created": self.approval_created,
            "gate_changed": self.gate_changed,
            "tool_called": self.tool_called,
            "can_call_tool": self.can_call_tool,
            "can_execute": self.can_execute,
            "can_write": self.can_write,
            "can_commit": self.can_commit,
            "can_change_approval_gate": self.can_change_approval_gate,
            "can_change_policy": self.can_change_policy,
            "can_access_network": self.can_access_network,
            "can_read_env": self.can_read_env,
            "can_load_api_key": self.can_load_api_key,
        }


def build_safe_execution_sandbox_envelope(request: SafeExecutionSandboxRequest) -> SafeExecutionSandboxEnvelope:
    if not isinstance(request, SafeExecutionSandboxRequest):
        return _build_envelope(
            request_data=_empty_request_data(),
            status=SafeExecutionStatus.MALFORMED_REQUEST,
            execution_kind=SafeExecutionKind.UNKNOWN,
            source_trust=SafeExecutionSourceTrust.UNKNOWN,
            flags={SafeExecutionFlag.HUMAN_REVIEW_REQUIRED, SafeExecutionFlag.UNSAFE_COMMAND},
            risk_notes=("Malformed SafeExecutionSandboxRequest input.",),
        )

    source_trust = _normalize_source_trust(request.source_trust)
    try:
        execution_kind = _normalize_execution_kind(request.execution_kind)
        request_data = _request_data(request, source_trust, execution_kind)
    except (TypeError, ValueError):
        return _build_envelope(
            request_data=_empty_request_data(),
            status=SafeExecutionStatus.MALFORMED_REQUEST,
            execution_kind=SafeExecutionKind.UNKNOWN,
            source_trust=source_trust,
            flags={SafeExecutionFlag.HUMAN_REVIEW_REQUIRED, SafeExecutionFlag.UNSAFE_COMMAND},
            risk_notes=("Request metadata was not deterministic JSON data.",),
        )

    flags, risk_notes = _classify_execution_kind(execution_kind)
    command_flags, command_notes = _command_and_path_flags(request_data)
    access_flags, access_notes = _access_flags(request_data)
    flags.update(command_flags)
    flags.update(access_flags)
    risk_notes.extend(command_notes)
    risk_notes.extend(access_notes)
    combined_text = _combined_text(request_data)

    if _provider_untrusted(source_trust):
        flags.add(SafeExecutionFlag.PROVIDER_OUTPUT_UNTRUSTED)
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Provider or model output is untrusted metadata only.")
    if _unsafe_metadata(combined_text):
        flags.add(SafeExecutionFlag.UNSAFE_COMMAND)
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Command or metadata contains unsafe command, install, network, secret, or authority-looking literals.")
    if _secret_metadata(combined_text):
        flags.add(SafeExecutionFlag.SECRET_OR_TOKEN_PATTERN)
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Secret, token, or environment metadata was ignored as authority.")
    if _authority_claims_present(request.authority_claims) or _authority_metadata_present(combined_text):
        flags.add(SafeExecutionFlag.SUSPICIOUS_AUTHORITY_CLAIM)
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Authority or execution-completion claims were ignored.")
    if _inconsistent_hash_metadata(request_data):
        flags.add(SafeExecutionFlag.INCONSISTENT_HASH_METADATA)
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source IDs and hashes are missing, malformed, or inconsistent.")
    if _source_metadata_not_yet_governed(request_data):
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source metadata is not yet governed.")

    status = _status_for(flags, execution_kind)
    return _build_envelope(
        request_data=request_data,
        status=status,
        execution_kind=execution_kind,
        source_trust=source_trust,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _build_envelope(
    *,
    request_data: dict[str, Any],
    status: SafeExecutionStatus,
    execution_kind: SafeExecutionKind,
    source_trust: SafeExecutionSourceTrust,
    flags: set[SafeExecutionFlag],
    risk_notes: tuple[str, ...],
) -> SafeExecutionSandboxEnvelope:
    base_flags = {
        SafeExecutionFlag.SANDBOX_ENVELOPE_METADATA_ONLY,
        SafeExecutionFlag.NO_EXECUTION,
        SafeExecutionFlag.NO_SUBPROCESS,
        SafeExecutionFlag.NO_SHELL,
        SafeExecutionFlag.NO_COMMAND_EXECUTION,
        SafeExecutionFlag.NO_TEST_EXECUTION,
        SafeExecutionFlag.NO_BROWSER,
        SafeExecutionFlag.NO_DOWNLOAD,
        SafeExecutionFlag.NO_FILE_READ,
        SafeExecutionFlag.NO_FILE_WRITE,
        SafeExecutionFlag.NO_DIRECTORY_CREATE,
        SafeExecutionFlag.NO_NETWORK,
        SafeExecutionFlag.NO_ENV_ACCESS,
        SafeExecutionFlag.NO_API_KEY_ACCESS,
        SafeExecutionFlag.NO_PROVIDER_CALL,
        SafeExecutionFlag.ACTION_PROPOSAL_METADATA_ONLY,
        SafeExecutionFlag.TOOL_CALL_PREVIEW_METADATA_ONLY,
        SafeExecutionFlag.TOOL_REGISTRY_METADATA_ONLY,
        SafeExecutionFlag.INTENT_ROUTE_METADATA_ONLY,
        SafeExecutionFlag.LOCAL_POLICY_METADATA_ONLY,
        SafeExecutionFlag.TEST_RUNNER_METADATA_ONLY,
        SafeExecutionFlag.DOWNLOAD_GOVERNANCE_METADATA_ONLY,
        SafeExecutionFlag.STATEMENT_GOVERNANCE_METADATA_ONLY,
        SafeExecutionFlag.BROWSER_GOVERNANCE_METADATA_ONLY,
    }
    all_flags = base_flags | set(flags)
    if status is not SafeExecutionStatus.SANDBOX_ENVELOPE_READY:
        all_flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    command_hash = _hash_json({"normalized_command": request_data["normalized_command"]})
    human_review_required = SafeExecutionFlag.HUMAN_REVIEW_REQUIRED in all_flags
    stable_payload = {
        "schema_version": SAFE_EXECUTION_SANDBOX_SCHEMA_VERSION,
        "status": status.value,
        "execution_kind": execution_kind.value,
        "requested_command": request_data["requested_command"],
        "normalized_command": request_data["normalized_command"],
        "command_hash": command_hash,
        "workspace_root_metadata": request_data["workspace_root_metadata"],
        "working_directory_metadata": request_data["working_directory_metadata"],
        "allowed_relative_paths": request_data["allowed_relative_paths"],
        "blocked_path_patterns": request_data["blocked_path_patterns"],
        "timeout_seconds": request_data["timeout_seconds"],
        "max_output_bytes": request_data["max_output_bytes"],
        "max_artifact_bytes": request_data["max_artifact_bytes"],
        "network_access": request_data["network_access"],
        "env_access": request_data["env_access"],
        "api_key_access": request_data["api_key_access"],
        "filesystem_write_mode": request_data["filesystem_write_mode"],
        "filesystem_read_mode": request_data["filesystem_read_mode"],
        "browser_access": request_data["browser_access"],
        "provider_access": request_data["provider_access"],
        "source_trust": source_trust.value,
        "source_action_proposal_id": request_data["source_action_proposal_id"],
        "source_action_proposal_hash": request_data["source_action_proposal_hash"],
        "source_tool_call_preview_id": request_data["source_tool_call_preview_id"],
        "source_tool_call_preview_hash": request_data["source_tool_call_preview_hash"],
        "source_intent_route_id": request_data["source_intent_route_id"],
        "source_intent_route_hash": request_data["source_intent_route_hash"],
        "source_policy_check_id": request_data["source_policy_check_id"],
        "source_policy_check_hash": request_data["source_policy_check_hash"],
        "source_test_runner_control_id": request_data["source_test_runner_control_id"],
        "source_test_runner_control_hash": request_data["source_test_runner_control_hash"],
        "source_download_governance_id": request_data["source_download_governance_id"],
        "source_download_governance_hash": request_data["source_download_governance_hash"],
        "source_statement_governance_id": request_data["source_statement_governance_id"],
        "source_statement_governance_hash": request_data["source_statement_governance_hash"],
        "source_browser_governance_id": request_data["source_browser_governance_id"],
        "source_browser_governance_hash": request_data["source_browser_governance_hash"],
        "source_statuses": request_data["source_statuses"],
        "source_flags": request_data["source_flags"],
        "metadata": request_data["metadata"],
        "flags": [flag.value for flag in ordered_flags],
        "risk_notes": list(ordered_notes),
        "human_review_required": human_review_required,
    }
    envelope_hash = _hash_json(stable_payload)
    return SafeExecutionSandboxEnvelope(
        schema_version=SAFE_EXECUTION_SANDBOX_SCHEMA_VERSION,
        sandbox_envelope_id=f"safe-exec-sandbox-{envelope_hash[:24]}",
        sandbox_envelope_hash=envelope_hash,
        status=status,
        execution_kind=execution_kind,
        requested_command=request_data["requested_command"],
        normalized_command=request_data["normalized_command"],
        command_hash=command_hash,
        workspace_root_metadata=request_data["workspace_root_metadata"],
        working_directory_metadata=request_data["working_directory_metadata"],
        allowed_relative_paths=request_data["allowed_relative_paths"],
        blocked_path_patterns=request_data["blocked_path_patterns"],
        timeout_seconds=request_data["timeout_seconds"],
        max_output_bytes=request_data["max_output_bytes"],
        max_artifact_bytes=request_data["max_artifact_bytes"],
        network_access=request_data["network_access"],
        env_access=request_data["env_access"],
        api_key_access=request_data["api_key_access"],
        filesystem_write_mode=request_data["filesystem_write_mode"],
        filesystem_read_mode=request_data["filesystem_read_mode"],
        browser_access=request_data["browser_access"],
        provider_access=request_data["provider_access"],
        human_review_required=human_review_required,
        source_trust=source_trust,
        source_action_proposal_id=request_data["source_action_proposal_id"],
        source_action_proposal_hash=request_data["source_action_proposal_hash"],
        source_tool_call_preview_id=request_data["source_tool_call_preview_id"],
        source_tool_call_preview_hash=request_data["source_tool_call_preview_hash"],
        source_intent_route_id=request_data["source_intent_route_id"],
        source_intent_route_hash=request_data["source_intent_route_hash"],
        source_policy_check_id=request_data["source_policy_check_id"],
        source_policy_check_hash=request_data["source_policy_check_hash"],
        source_test_runner_control_id=request_data["source_test_runner_control_id"],
        source_test_runner_control_hash=request_data["source_test_runner_control_hash"],
        source_download_governance_id=request_data["source_download_governance_id"],
        source_download_governance_hash=request_data["source_download_governance_hash"],
        source_statement_governance_id=request_data["source_statement_governance_id"],
        source_statement_governance_hash=request_data["source_statement_governance_hash"],
        source_browser_governance_id=request_data["source_browser_governance_id"],
        source_browser_governance_hash=request_data["source_browser_governance_hash"],
        flags=ordered_flags,
        risk_notes=ordered_notes,
        display_summary=_summary(status, execution_kind, human_review_required),
    )


def _request_data(
    request: SafeExecutionSandboxRequest,
    source_trust: SafeExecutionSourceTrust,
    execution_kind: SafeExecutionKind,
) -> dict[str, Any]:
    requested_command = _text("requested_command", request.requested_command)
    return {
        "execution_kind": execution_kind.value,
        "requested_command": requested_command,
        "normalized_command": _normalize_command(requested_command),
        "workspace_root_metadata": _optional_text(request.workspace_root_metadata),
        "working_directory_metadata": _optional_text(request.working_directory_metadata),
        "allowed_relative_paths": _normalized_path_tuple("allowed_relative_paths", request.allowed_relative_paths),
        "blocked_path_patterns": _text_tuple("blocked_path_patterns", request.blocked_path_patterns),
        "timeout_seconds": _nonnegative_int("timeout_seconds", request.timeout_seconds),
        "max_output_bytes": _nonnegative_int("max_output_bytes", request.max_output_bytes),
        "max_artifact_bytes": _nonnegative_int("max_artifact_bytes", request.max_artifact_bytes),
        "network_access": _access_text(request.network_access),
        "env_access": _access_text(request.env_access),
        "api_key_access": _access_text(request.api_key_access),
        "filesystem_write_mode": _access_text(request.filesystem_write_mode),
        "filesystem_read_mode": _access_text(request.filesystem_read_mode),
        "browser_access": _access_text(request.browser_access),
        "provider_access": _access_text(request.provider_access),
        "source_trust": source_trust.value,
        "source_action_proposal_id": _optional_text(request.source_action_proposal_id),
        "source_action_proposal_hash": _optional_text(request.source_action_proposal_hash),
        "source_tool_call_preview_id": _optional_text(request.source_tool_call_preview_id),
        "source_tool_call_preview_hash": _optional_text(request.source_tool_call_preview_hash),
        "source_intent_route_id": _optional_text(request.source_intent_route_id),
        "source_intent_route_hash": _optional_text(request.source_intent_route_hash),
        "source_policy_check_id": _optional_text(request.source_policy_check_id),
        "source_policy_check_hash": _optional_text(request.source_policy_check_hash),
        "source_test_runner_control_id": _optional_text(request.source_test_runner_control_id),
        "source_test_runner_control_hash": _optional_text(request.source_test_runner_control_hash),
        "source_download_governance_id": _optional_text(request.source_download_governance_id),
        "source_download_governance_hash": _optional_text(request.source_download_governance_hash),
        "source_statement_governance_id": _optional_text(request.source_statement_governance_id),
        "source_statement_governance_hash": _optional_text(request.source_statement_governance_hash),
        "source_browser_governance_id": _optional_text(request.source_browser_governance_id),
        "source_browser_governance_hash": _optional_text(request.source_browser_governance_hash),
        "source_statuses": tuple(value.upper() for value in _text_tuple("source_statuses", request.source_statuses)),
        "source_flags": tuple(value.upper() for value in _text_tuple("source_flags", request.source_flags)),
        "metadata": _stable_json_mapping(request.metadata),
    }


def _empty_request_data() -> dict[str, Any]:
    return {
        "execution_kind": SafeExecutionKind.UNKNOWN.value,
        "requested_command": "",
        "normalized_command": "",
        "workspace_root_metadata": None,
        "working_directory_metadata": None,
        "allowed_relative_paths": (),
        "blocked_path_patterns": ("../", "/etc/passwd", "~/.ssh", ".env"),
        "timeout_seconds": 30,
        "max_output_bytes": 200000,
        "max_artifact_bytes": 1000000,
        "network_access": "BLOCKED",
        "env_access": "BLOCKED",
        "api_key_access": "BLOCKED",
        "filesystem_write_mode": "BLOCKED",
        "filesystem_read_mode": "METADATA_ONLY",
        "browser_access": "BLOCKED",
        "provider_access": "BLOCKED",
        "source_trust": SafeExecutionSourceTrust.UNKNOWN.value,
        "source_action_proposal_id": None,
        "source_action_proposal_hash": None,
        "source_tool_call_preview_id": None,
        "source_tool_call_preview_hash": None,
        "source_intent_route_id": None,
        "source_intent_route_hash": None,
        "source_policy_check_id": None,
        "source_policy_check_hash": None,
        "source_test_runner_control_id": None,
        "source_test_runner_control_hash": None,
        "source_download_governance_id": None,
        "source_download_governance_hash": None,
        "source_statement_governance_id": None,
        "source_statement_governance_hash": None,
        "source_browser_governance_id": None,
        "source_browser_governance_hash": None,
        "source_statuses": (),
        "source_flags": (),
        "metadata": {},
    }


def _classify_execution_kind(execution_kind: SafeExecutionKind) -> tuple[set[SafeExecutionFlag], list[str]]:
    flags: set[SafeExecutionFlag] = {SafeExecutionFlag.HUMAN_REVIEW_REQUIRED}
    notes: list[str] = []
    if execution_kind is SafeExecutionKind.TEST_RUN:
        flags.add(SafeExecutionFlag.TEST_RUN_ENVELOPE)
        notes.append("Test-run envelope is metadata only and does not run tests.")
    elif execution_kind is SafeExecutionKind.STATIC_CHECK:
        flags.add(SafeExecutionFlag.STATIC_CHECK_ENVELOPE)
        notes.append("Static-check envelope is metadata only and does not call tools.")
    elif execution_kind is SafeExecutionKind.COMPILE_CHECK:
        flags.add(SafeExecutionFlag.COMPILE_CHECK_ENVELOPE)
        notes.append("Compile-check envelope is metadata only and does not compile.")
    elif execution_kind is SafeExecutionKind.DOWNLOAD:
        flags.add(SafeExecutionFlag.DOWNLOAD_ENVELOPE_BLOCKED)
        notes.append("Download execution is blocked in Safe Execution Sandbox 1A.")
    elif execution_kind is SafeExecutionKind.BROWSER_READ_ONLY:
        flags.add(SafeExecutionFlag.BROWSER_ENVELOPE_BLOCKED)
        notes.append("Browser execution is blocked in Safe Execution Sandbox 1A.")
    elif execution_kind in {SafeExecutionKind.GITHUB_READ_ONLY, SafeExecutionKind.GITHUB_WRITE}:
        flags.add(SafeExecutionFlag.GITHUB_ENVELOPE_NOT_YET_GOVERNED)
        notes.append("GitHub execution is not yet governed in this envelope.")
    elif execution_kind is SafeExecutionKind.SHELL_COMMAND:
        flags.add(SafeExecutionFlag.SHELL_COMMAND_BLOCKED)
        notes.append("Shell command execution is blocked in Safe Execution Sandbox 1A.")
    else:
        notes.append("Execution kind is unknown or not yet governed.")
    return flags, notes


def _command_and_path_flags(request_data: dict[str, Any]) -> tuple[set[SafeExecutionFlag], tuple[str, ...]]:
    flags: set[SafeExecutionFlag] = set()
    notes: list[str] = []
    normalized_command = request_data["normalized_command"]
    if not normalized_command:
        flags.add(SafeExecutionFlag.UNSAFE_COMMAND)
        notes.append("Requested command is empty or malformed.")
    if _unsafe_command(normalized_command):
        flags.add(SafeExecutionFlag.UNSAFE_COMMAND)
        notes.append("Requested command contains unsafe execution, install, network, or secret-like metadata.")
    path_text = " ".join(
        (
            normalized_command,
            request_data["workspace_root_metadata"] or "",
            request_data["working_directory_metadata"] or "",
            " ".join(request_data["allowed_relative_paths"]),
        )
    ).casefold()
    if _contains_any(path_text, ("../", "..\\", "/etc/passwd")):
        flags.update({SafeExecutionFlag.UNSAFE_PATH, SafeExecutionFlag.PATH_TRAVERSAL_BLOCKED})
        notes.append("Path traversal or restricted path metadata was blocked.")
    if _has_absolute_path_metadata(path_text):
        flags.update({SafeExecutionFlag.UNSAFE_PATH, SafeExecutionFlag.ABSOLUTE_PATH_BLOCKED})
        notes.append("Absolute path metadata was blocked.")
    if _contains_any(path_text, ("~/.ssh", ".env")):
        flags.update({SafeExecutionFlag.UNSAFE_PATH, SafeExecutionFlag.ENV_ACCESS_BLOCKED})
        notes.append("Secret-bearing path metadata was blocked.")
    if flags:
        flags.add(SafeExecutionFlag.HUMAN_REVIEW_REQUIRED)
    return flags, tuple(notes)


def _access_flags(request_data: dict[str, Any]) -> tuple[set[SafeExecutionFlag], tuple[str, ...]]:
    flags: set[SafeExecutionFlag] = {
        SafeExecutionFlag.NETWORK_ACCESS_BLOCKED,
        SafeExecutionFlag.ENV_ACCESS_BLOCKED,
        SafeExecutionFlag.API_KEY_ACCESS_BLOCKED,
        SafeExecutionFlag.FILESYSTEM_WRITE_BLOCKED,
        SafeExecutionFlag.BROWSER_ACCESS_BLOCKED,
        SafeExecutionFlag.PROVIDER_ACCESS_BLOCKED,
    }
    notes = ["Sandbox envelope defaults block network, environment, API-key, write, browser, and provider access."]
    if request_data["network_access"] != "BLOCKED":
        notes.append("Requested network access was reduced to blocked metadata.")
    if request_data["env_access"] != "BLOCKED":
        notes.append("Requested environment access was reduced to blocked metadata.")
    if request_data["api_key_access"] != "BLOCKED":
        notes.append("Requested API-key access was reduced to blocked metadata.")
    if request_data["filesystem_write_mode"] != "BLOCKED":
        notes.append("Requested filesystem write mode was reduced to blocked metadata.")
    if request_data["browser_access"] != "BLOCKED":
        notes.append("Requested browser access was reduced to blocked metadata.")
    if request_data["provider_access"] != "BLOCKED":
        notes.append("Requested provider access was reduced to blocked metadata.")
    return flags, tuple(notes)


def _status_for(flags: set[SafeExecutionFlag], execution_kind: SafeExecutionKind) -> SafeExecutionStatus:
    if SafeExecutionFlag.INCONSISTENT_HASH_METADATA in flags:
        return SafeExecutionStatus.INCONSISTENT_METADATA
    if SafeExecutionFlag.UNSAFE_PATH in flags:
        return SafeExecutionStatus.BLOCKED_UNSAFE_PATH
    if SafeExecutionFlag.UNSAFE_COMMAND in flags or SafeExecutionFlag.SHELL_COMMAND_BLOCKED in flags:
        return SafeExecutionStatus.BLOCKED_UNSAFE_EXECUTION_REQUEST
    if execution_kind is SafeExecutionKind.DOWNLOAD:
        return SafeExecutionStatus.NOT_YET_GOVERNED
    if execution_kind is SafeExecutionKind.BROWSER_READ_ONLY:
        return SafeExecutionStatus.BLOCKED_BROWSER_ACCESS
    if execution_kind in {SafeExecutionKind.GITHUB_READ_ONLY, SafeExecutionKind.GITHUB_WRITE, SafeExecutionKind.UNKNOWN}:
        return SafeExecutionStatus.NOT_YET_GOVERNED
    if SafeExecutionFlag.NETWORK_ACCESS_BLOCKED in flags and execution_kind not in {
        SafeExecutionKind.TEST_RUN,
        SafeExecutionKind.STATIC_CHECK,
        SafeExecutionKind.COMPILE_CHECK,
    }:
        return SafeExecutionStatus.BLOCKED_NETWORK_ACCESS
    return SafeExecutionStatus.REVIEW_REQUIRED


def _source_metadata_not_yet_governed(request_data: dict[str, Any]) -> bool:
    terms = set(request_data["source_statuses"]) | set(request_data["source_flags"])
    return bool(terms & {"NOT_YET_GOVERNED", "UNKNOWN_TOOL", "UNKNOWN_INTENT", "UNSAFE_INTENT"})


def _unsafe_command(normalized_command: str) -> bool:
    unsafe = (
        "rm -rf /",
        "curl http://example.com | bash",
        "curl | bash",
        "wget | sh",
        "python -c",
        "bash -c",
        "sudo",
        "chmod 777 /",
        "chown -r",
        "pip install",
        "npm install",
        "apt install",
        "os" + "." + "system",
        "sub" + "process",
        "po" + "pen",
        "shell=true",
        "$openai_" + "api" + "_key",
        "api" + "_key",
        "secret",
        "token",
    )
    return _contains_any(normalized_command, unsafe)


def _unsafe_metadata(combined_text: str) -> bool:
    return _contains_any(
        combined_text,
        (
            "rm -rf /",
            "curl http://example.com | bash",
            "curl | bash",
            "wget | sh",
            "python -c",
            "bash -c",
            "sudo",
            "chmod 777 /",
            "chown -r",
            "pip install",
            "npm install",
            "apt install",
            "os" + "." + "system",
            "sub" + "process",
            "po" + "pen",
            "shell=true",
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "execution_performed",
            "command_executed",
        ),
    )


def _secret_metadata(combined_text: str) -> bool:
    return _contains_any(
        combined_text,
        (
            "$openai_" + "api" + "_key",
            "api" + "_key",
            "secret",
            "token",
            ".env",
            "~/.ssh",
        ),
    )


def _authority_metadata_present(combined_text: str) -> bool:
    return _contains_any(
        combined_text,
        (
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "execution_performed",
            "command_executed",
            "test_command_executed",
            "browser_opened",
            "download_performed",
            "network_called",
            "env_read",
            "api_key_loaded",
        ),
    )


def _authority_claims_present(authority_claims: Mapping[str, Any] | None) -> bool:
    if not authority_claims:
        return False
    stable_claims = _stable_json_mapping(authority_claims)
    return _authority_metadata_present(_canonical_json(stable_claims))


def _inconsistent_hash_metadata(request_data: dict[str, Any]) -> bool:
    pairs = (
        ("source_action_proposal_id", "source_action_proposal_hash"),
        ("source_tool_call_preview_id", "source_tool_call_preview_hash"),
        ("source_intent_route_id", "source_intent_route_hash"),
        ("source_policy_check_id", "source_policy_check_hash"),
        ("source_test_runner_control_id", "source_test_runner_control_hash"),
        ("source_download_governance_id", "source_download_governance_hash"),
        ("source_statement_governance_id", "source_statement_governance_hash"),
        ("source_browser_governance_id", "source_browser_governance_hash"),
    )
    for id_key, hash_key in pairs:
        source_id = request_data[id_key]
        source_hash = request_data[hash_key]
        if bool(source_id) != bool(source_hash):
            return True
        if source_hash and not _looks_like_sha256(source_hash):
            return True
    return False


def _looks_like_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _normalize_execution_kind(value: SafeExecutionKind | str) -> SafeExecutionKind:
    if isinstance(value, SafeExecutionKind):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "UNITTEST": SafeExecutionKind.TEST_RUN,
        "TEST": SafeExecutionKind.TEST_RUN,
        "TESTS": SafeExecutionKind.TEST_RUN,
        "TEST_RUN": SafeExecutionKind.TEST_RUN,
        "STATIC": SafeExecutionKind.STATIC_CHECK,
        "STATIC_CHECK": SafeExecutionKind.STATIC_CHECK,
        "DIFF_CHECK": SafeExecutionKind.STATIC_CHECK,
        "COMPILE": SafeExecutionKind.COMPILE_CHECK,
        "COMPILEALL": SafeExecutionKind.COMPILE_CHECK,
        "COMPILE_CHECK": SafeExecutionKind.COMPILE_CHECK,
        "DOWNLOAD": SafeExecutionKind.DOWNLOAD,
        "BROWSER": SafeExecutionKind.BROWSER_READ_ONLY,
        "BROWSER_READ_ONLY": SafeExecutionKind.BROWSER_READ_ONLY,
        "GITHUB_READ_ONLY": SafeExecutionKind.GITHUB_READ_ONLY,
        "GITHUB_WRITE": SafeExecutionKind.GITHUB_WRITE,
        "SHELL": SafeExecutionKind.SHELL_COMMAND,
        "SHELL_COMMAND": SafeExecutionKind.SHELL_COMMAND,
    }
    return aliases.get(normalized, SafeExecutionKind.UNKNOWN)


def _normalize_source_trust(value: SafeExecutionSourceTrust | str) -> SafeExecutionSourceTrust:
    if isinstance(value, SafeExecutionSourceTrust):
        return value
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "USER": SafeExecutionSourceTrust.USER_SUPPLIED,
        "USER_SUPPLIED": SafeExecutionSourceTrust.USER_SUPPLIED,
        "UNTRUSTED": SafeExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": SafeExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": SafeExecutionSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": SafeExecutionSourceTrust.MODEL_UNTRUSTED,
        "CRITIC_METADATA": SafeExecutionSourceTrust.CRITIC_METADATA,
        "SYSTEM_METADATA": SafeExecutionSourceTrust.SYSTEM_METADATA,
    }
    return aliases.get(normalized, SafeExecutionSourceTrust.UNKNOWN)


def _provider_untrusted(source_trust: SafeExecutionSourceTrust) -> bool:
    return source_trust in {
        SafeExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        SafeExecutionSourceTrust.PROVIDER_UNTRUSTED,
        SafeExecutionSourceTrust.MODEL_UNTRUSTED,
    }


def _normalize_command(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _normalized_path_tuple(field_name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(_normalize_path_metadata(value) for value in _text_tuple(field_name, values))


def _normalize_path_metadata(value: str) -> str:
    return "/".join(part for part in value.strip().replace("\\", "/").split("/") if part)


def _has_absolute_path_metadata(text: str) -> bool:
    return (
        text.startswith("/")
        or " /etc/" in text
        or "/etc/passwd" in text
        or text.startswith("~")
        or " ~/.ssh" in text
    )


def _combined_text(request_data: dict[str, Any]) -> str:
    return " ".join(
        (
            request_data["requested_command"],
            request_data["normalized_command"],
            request_data["workspace_root_metadata"] or "",
            request_data["working_directory_metadata"] or "",
            " ".join(request_data["allowed_relative_paths"]),
            " ".join(request_data["source_statuses"]),
            " ".join(request_data["source_flags"]),
            _canonical_json(request_data["metadata"]),
        )
    ).casefold()


def _contains_any(value: str, patterns: tuple[str, ...]) -> bool:
    lowered = value.casefold()
    return any(pattern.casefold() in lowered for pattern in patterns)


def _access_text(value: str) -> str:
    text = _text("access", value).strip().upper().replace("-", "_").replace(" ", "_")
    if not text:
        raise ValueError("access metadata cannot be empty")
    return text


def _nonnegative_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


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


def _flag_tuple(values: tuple[SafeExecutionFlag, ...]) -> tuple[SafeExecutionFlag, ...]:
    if not isinstance(values, tuple):
        raise TypeError("flags must be a tuple")
    return tuple(SafeExecutionFlag(value) for value in values)


def _stable_json_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    return json.loads(_canonical_json(dict(value)))


def _hash_json(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _bounded_text(value: str) -> str:
    if len(value) <= _MAX_SUMMARY_CHARS:
        return value
    return value[: _MAX_SUMMARY_CHARS - 3] + "..."


def _summary(status: SafeExecutionStatus, execution_kind: SafeExecutionKind, human_review_required: bool) -> str:
    review_text = "human review required" if human_review_required else "metadata ready"
    return _bounded_text(
        f"Safe execution sandbox envelope is {status.value} for {execution_kind.value}; {review_text}; no execution performed."
    )
