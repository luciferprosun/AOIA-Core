from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


CODEX_LIVE_FLOW_REQUEST_SCHEMA_VERSION = "AOIA_CODEX_LIVE_FLOW_REQUEST_1A"
CODEX_LIVE_FLOW_HANDOFF_SCHEMA_VERSION = "AOIA_CODEX_LIVE_FLOW_HANDOFF_1A"
CODEX_EXTERNAL_RUN_OBSERVATION_SCHEMA_VERSION = "AOIA_CODEX_EXTERNAL_RUN_OBSERVATION_1A"
CODEX_RETURNED_OUTPUT_SCHEMA_VERSION = "AOIA_CODEX_RETURNED_OUTPUT_1A"
CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION = "AOIA_CODEX_LIVE_FLOW_REVIEW_1A"

CODEX_LIVE_FLOW_HUMAN_MEDIATED_ONLY = "CODEX_LIVE_FLOW_HUMAN_MEDIATED_ONLY"
CODEX_LIVE_FLOW_EXTERNAL_OUTPUT_UNTRUSTED = "CODEX_LIVE_FLOW_EXTERNAL_OUTPUT_UNTRUSTED"
CODEX_LIVE_FLOW_REQUIRES_BOUNDARY_REVIEW = "CODEX_LIVE_FLOW_REQUIRES_BOUNDARY_REVIEW"
CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW = "CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW"
CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH = "CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH"
CODEX_LIVE_FLOW_NON_AUTHORITY = "CODEX_LIVE_FLOW_NON_AUTHORITY"

CODEX_LIVE_FLOW_OK = "CODEX_LIVE_FLOW_OK"
CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW_REASON = "CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW"
CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH_REASON = "CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH"
CODEX_LIVE_FLOW_BLOCKED_INVALID_REQUEST = "CODEX_LIVE_FLOW_BLOCKED_INVALID_REQUEST"
CODEX_LIVE_FLOW_BLOCKED_INVALID_HANDOFF = "CODEX_LIVE_FLOW_BLOCKED_INVALID_HANDOFF"
CODEX_LIVE_FLOW_BLOCKED_INVALID_OBSERVATION = "CODEX_LIVE_FLOW_BLOCKED_INVALID_OBSERVATION"
CODEX_LIVE_FLOW_BLOCKED_INVALID_OUTPUT = "CODEX_LIVE_FLOW_BLOCKED_INVALID_OUTPUT"
CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH = "CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH"
CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH = "CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH"
CODEX_LIVE_FLOW_BLOCKED_FORBIDDEN_FILE = "CODEX_LIVE_FLOW_BLOCKED_FORBIDDEN_FILE"
CODEX_LIVE_FLOW_BLOCKED_CHANGED_FILE_OUT_OF_SCOPE = "CODEX_LIVE_FLOW_BLOCKED_CHANGED_FILE_OUT_OF_SCOPE"
CODEX_LIVE_FLOW_BLOCKED_INVALID_EXTERNAL_RUN_MODE = "CODEX_LIVE_FLOW_BLOCKED_INVALID_EXTERNAL_RUN_MODE"
CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME = "CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME"
CODEX_LIVE_FLOW_BLOCKED_EXPIRED_REQUEST = "CODEX_LIVE_FLOW_BLOCKED_EXPIRED_REQUEST"
CODEX_LIVE_FLOW_BLOCKED_EXPIRED_HANDOFF = "CODEX_LIVE_FLOW_BLOCKED_EXPIRED_HANDOFF"
CODEX_LIVE_FLOW_BLOCKED_EXPIRED_OUTPUT = "CODEX_LIVE_FLOW_BLOCKED_EXPIRED_OUTPUT"
CODEX_LIVE_FLOW_BLOCKED_HUMAN_OPERATOR_REQUIRED = "CODEX_LIVE_FLOW_BLOCKED_HUMAN_OPERATOR_REQUIRED"
CODEX_LIVE_FLOW_BLOCKED_AOIA_CODEX_INVOCATION = "CODEX_LIVE_FLOW_BLOCKED_AOIA_CODEX_INVOCATION"
CODEX_LIVE_FLOW_BLOCKED_CODEX_INVOCATION_SMUGGLING = "CODEX_LIVE_FLOW_BLOCKED_CODEX_INVOCATION_SMUGGLING"
CODEX_LIVE_FLOW_BLOCKED_AIDER_INVOCATION = "CODEX_LIVE_FLOW_BLOCKED_AIDER_INVOCATION"
CODEX_LIVE_FLOW_BLOCKED_PATCH_APPLICATION = "CODEX_LIVE_FLOW_BLOCKED_PATCH_APPLICATION"
CODEX_LIVE_FLOW_BLOCKED_WRITE_CLAIM = "CODEX_LIVE_FLOW_BLOCKED_WRITE_CLAIM"
CODEX_LIVE_FLOW_BLOCKED_TEST_EXECUTION = "CODEX_LIVE_FLOW_BLOCKED_TEST_EXECUTION"
CODEX_LIVE_FLOW_BLOCKED_COMMIT_OR_PUSH = "CODEX_LIVE_FLOW_BLOCKED_COMMIT_OR_PUSH"
CODEX_LIVE_FLOW_BLOCKED_COMMAND_INJECTION = "CODEX_LIVE_FLOW_BLOCKED_COMMAND_INJECTION"
CODEX_LIVE_FLOW_BLOCKED_PROVIDER_CALL = "CODEX_LIVE_FLOW_BLOCKED_PROVIDER_CALL"
CODEX_LIVE_FLOW_BLOCKED_GIT_ACTION = "CODEX_LIVE_FLOW_BLOCKED_GIT_ACTION"
CODEX_LIVE_FLOW_BLOCKED_PACKAGE_INSTALL = "CODEX_LIVE_FLOW_BLOCKED_PACKAGE_INSTALL"
CODEX_LIVE_FLOW_BLOCKED_BROWSER_ACTION = "CODEX_LIVE_FLOW_BLOCKED_BROWSER_ACTION"
CODEX_LIVE_FLOW_BLOCKED_MCP_TOOL = "CODEX_LIVE_FLOW_BLOCKED_MCP_TOOL"
CODEX_LIVE_FLOW_BLOCKED_AGENT_LOOP = "CODEX_LIVE_FLOW_BLOCKED_AGENT_LOOP"
CODEX_LIVE_FLOW_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING = "CODEX_LIVE_FLOW_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING"
CODEX_LIVE_FLOW_BLOCKED_ENV_OR_SECRET = "CODEX_LIVE_FLOW_BLOCKED_ENV_OR_SECRET"
CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM = "CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM"
CODEX_LIVE_FLOW_BLOCKED_NON_JSON_SERIALIZABLE = "CODEX_LIVE_FLOW_BLOCKED_NON_JSON_SERIALIZABLE"
CODEX_LIVE_FLOW_BLOCKED_AMBIGUOUS_EVIDENCE = "CODEX_LIVE_FLOW_BLOCKED_AMBIGUOUS_EVIDENCE"

CODEX_LIVE_FLOW_RISK_LOW = "LOW"
CODEX_LIVE_FLOW_RISK_MEDIUM = "MEDIUM"
CODEX_LIVE_FLOW_RISK_HIGH = "HIGH"
CODEX_LIVE_FLOW_RISK_BLOCKED = "BLOCKED"

SUPPORTED_STEP_IDS = frozenset({"step_52_minimal_codex_live_flow"})
SUPPORTED_EXTERNAL_RUN_MODES = frozenset(
    {
        "human_manual_copy_paste",
        "human_manual_codex_ui",
        "human_manual_codex_cli_outside_aoia",
    }
)

_ALLOWED_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "flow_id",
        "task_id",
        "step_id",
        "task_goal",
        "prepared_prompt_hash",
        "coding_assistant_request_hash",
        "coding_assistant_boundary_review_hash",
        "orchestration_plan_hash",
        "requested_by",
        "requested_at",
        "expires_at",
        "request_hash",
    }
)
_ALLOWED_HANDOFF_FIELDS = frozenset(
    {
        "schema_version",
        "flow_id",
        "request_hash",
        "task_id",
        "handoff_summary",
        "allowed_files",
        "forbidden_files",
        "required_tests",
        "forbidden_actions",
        "human_operator_required",
        "codex_invocation_allowed_by_aoia",
        "created_at",
        "expires_at",
        "handoff_hash",
    }
)
_ALLOWED_OBSERVATION_FIELDS = frozenset(
    {
        "schema_version",
        "flow_id",
        "request_hash",
        "handoff_hash",
        "human_operator",
        "external_run_mode",
        "external_run_started_at",
        "external_run_reported_at",
        "external_run_report_hash",
        "observation_hash",
    }
)
_ALLOWED_OUTPUT_FIELDS = frozenset(
    {
        "schema_version",
        "flow_id",
        "request_hash",
        "handoff_hash",
        "observation_hash",
        "output_summary",
        "changed_files_claimed",
        "tests_claimed",
        "commit_hash_claimed",
        "risk_notes",
        "authority_claims",
        "returned_at",
        "expires_at",
        "output_hash",
    }
)

_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approve",
        "approved",
        "authorize",
        "authorized",
        "authority",
        "codex_passed",
        "safe",
        "can_apply",
        "can_write",
        "can_execute",
        "can_dispatch",
        "can_retry",
        "can_fallback",
        "can_stream",
        "can_commit",
        "can_push",
        "tests_passed",
        "can_run_tests",
        "gate_satisfied",
        "human_approved",
        "gate_pass",
        "grant_permission",
    }
)
_CODEX_INVOCATION_TERMS = (
    "codex_allowed",
    "codex_can_run",
    "can_run_codex",
    "run_codex",
    "invoke_codex",
    "codex_cli",
    "codex api",
    "codex_sdk",
    "codex run",
    "codex exec",
)
_AIDER_TERMS = ("aider", "run_aider", "invoke_aider")
_PATCH_TERMS = ("apply_patch", "patch_apply")
_WRITE_TERMS = ("write_files", "can_write")
_TEST_TERMS = ("test_execution", "can_run_tests", "run tests", "tests_passed")
_COMMIT_PUSH_TERMS = ("can_commit", "can_push", "git_commit", "git_push", "git_fetch", "git_checkout", "git_reset", "git_merge", "git_rebase")
_COMMAND_INJECTION_TERMS = (
    "command",
    "commands",
    "script",
    "shell",
    "sub" + "process",
    "system",
    "os." + "system",
    "Po" + "pen",
    "bash",
    "sh -c",
    "curl",
    "wget",
    "http://",
    "https://",
)
_PROVIDER_TERMS = ("provider" + "_call", "call_provider")
_GIT_TERMS = ("git" + "_action",)
_PACKAGE_TERMS = ("package" + "_install", "pip install", "npm install", "apt install")
_BROWSER_TERMS = ("browser_action", "browser_automation", "sel" + "enium", "play" + "wright", "web" + "browser")
_MCP_TERMS = ("mcp" + "_tool", "call" + "_tool", "read_resource")
_AGENT_LOOP_TERMS = (
    "agent" + "_loop",
    "worker",
    "background",
    "thread" + "ing",
    "multi" + "processing",
    "async" + "io",
    "asyncio.run",
    "event" + "_loop",
    "create" + "_task",
    "gath" + "er",
    "sleep",
    "timer",
    "schedule",
    "scheduler",
)
_RETRY_FALLBACK_TERMS = ("retry_now", "auto_retry", "automatic_retry", "fallback_now", "auto_fallback", "automatic_fallback", "streaming", "dispatch", "dispatcher", "execute")
_ENV_SECRET_TERMS = ("api" + "_key", "token", "secret", "env", "password", "credential", ".env", "id_rsa", "ssh_key")
_TEXT_SCAN_SKIP_KEYS = frozenset(
    {
        "schema_version",
        "step_id",
        "external_run_mode",
        "commit_hash_claimed",
        "forbidden_actions",
        "authority_claims",
    }
)
_UNSAFE_PATH_TERMS = (".git", ".env", "/etc/", "id_rsa", "ssh_key", "secret", "credential")
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:+-]{0,255}$")
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 4096
_MAX_COLLECTION_ITEMS = 128
_MAX_DEPTH = 8


@dataclass(frozen=True)
class CodexLiveFlowRequest:
    schema_version: str
    flow_id: str
    task_id: str
    step_id: str
    task_goal: str
    prepared_prompt_hash: str
    coding_assistant_request_hash: str
    coding_assistant_boundary_review_hash: str
    orchestration_plan_hash: str | None
    requested_by: str
    requested_at: int
    expires_at: int
    request_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "flow_id", _identifier("flow_id", self.flow_id))
        object.__setattr__(self, "task_id", _identifier("task_id", self.task_id))
        object.__setattr__(self, "step_id", _required_text("step_id", self.step_id).casefold())
        object.__setattr__(self, "task_goal", _required_text("task_goal", self.task_goal))
        object.__setattr__(self, "prepared_prompt_hash", _required_hash("prepared_prompt_hash", self.prepared_prompt_hash))
        object.__setattr__(self, "coding_assistant_request_hash", _required_hash("coding_assistant_request_hash", self.coding_assistant_request_hash))
        object.__setattr__(self, "coding_assistant_boundary_review_hash", _required_hash("coding_assistant_boundary_review_hash", self.coding_assistant_boundary_review_hash))
        object.__setattr__(self, "orchestration_plan_hash", _optional_hash("orchestration_plan_hash", self.orchestration_plan_hash))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "requested_at", _nonnegative_int("requested_at", self.requested_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        if self.schema_version != CODEX_LIVE_FLOW_REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported codex live-flow request schema version")
        if self.expires_at <= self.requested_at:
            raise ValueError("request expires_at must be greater than requested_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "flow_id": self.flow_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "task_goal": self.task_goal,
            "prepared_prompt_hash": self.prepared_prompt_hash,
            "coding_assistant_request_hash": self.coding_assistant_request_hash,
            "coding_assistant_boundary_review_hash": self.coding_assistant_boundary_review_hash,
            "orchestration_plan_hash": self.orchestration_plan_hash,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "request_hash": self.request_hash,
        }


@dataclass(frozen=True)
class CodexLiveFlowHandoffPacket:
    schema_version: str
    flow_id: str
    request_hash: str
    task_id: str
    handoff_summary: str
    allowed_files: tuple[str, ...]
    forbidden_files: tuple[str, ...]
    required_tests: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    human_operator_required: bool
    codex_invocation_allowed_by_aoia: bool
    created_at: int
    expires_at: int
    handoff_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "flow_id", _identifier("flow_id", self.flow_id))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        object.__setattr__(self, "task_id", _identifier("task_id", self.task_id))
        object.__setattr__(self, "handoff_summary", _required_text("handoff_summary", self.handoff_summary))
        object.__setattr__(self, "allowed_files", _path_tuple("allowed_files", self.allowed_files, allow_empty=False))
        object.__setattr__(self, "forbidden_files", _path_tuple("forbidden_files", self.forbidden_files, allow_empty=True))
        object.__setattr__(self, "required_tests", _text_tuple("required_tests", self.required_tests, allow_empty=True))
        object.__setattr__(self, "forbidden_actions", _text_tuple("forbidden_actions", self.forbidden_actions, allow_empty=True))
        if not isinstance(self.human_operator_required, bool):
            raise TypeError("human_operator_required must be boolean")
        if not isinstance(self.codex_invocation_allowed_by_aoia, bool):
            raise TypeError("codex_invocation_allowed_by_aoia must be boolean")
        object.__setattr__(self, "created_at", _nonnegative_int("created_at", self.created_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "handoff_hash", _required_hash("handoff_hash", self.handoff_hash))
        if self.schema_version != CODEX_LIVE_FLOW_HANDOFF_SCHEMA_VERSION:
            raise ValueError("unsupported codex live-flow handoff schema version")
        if self.expires_at <= self.created_at:
            raise ValueError("handoff expires_at must be greater than created_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "flow_id": self.flow_id,
            "request_hash": self.request_hash,
            "task_id": self.task_id,
            "handoff_summary": self.handoff_summary,
            "allowed_files": self.allowed_files,
            "forbidden_files": self.forbidden_files,
            "required_tests": self.required_tests,
            "forbidden_actions": self.forbidden_actions,
            "human_operator_required": self.human_operator_required,
            "codex_invocation_allowed_by_aoia": self.codex_invocation_allowed_by_aoia,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "handoff_hash": self.handoff_hash,
        }


@dataclass(frozen=True)
class CodexExternalRunObservation:
    schema_version: str
    flow_id: str
    request_hash: str
    handoff_hash: str
    human_operator: str
    external_run_mode: str
    external_run_started_at: int
    external_run_reported_at: int
    external_run_report_hash: str
    observation_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "flow_id", _identifier("flow_id", self.flow_id))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        object.__setattr__(self, "handoff_hash", _required_hash("handoff_hash", self.handoff_hash))
        object.__setattr__(self, "human_operator", _required_text("human_operator", self.human_operator))
        object.__setattr__(self, "external_run_mode", _required_text("external_run_mode", self.external_run_mode).casefold())
        object.__setattr__(self, "external_run_started_at", _nonnegative_int("external_run_started_at", self.external_run_started_at))
        object.__setattr__(self, "external_run_reported_at", _nonnegative_int("external_run_reported_at", self.external_run_reported_at))
        object.__setattr__(self, "external_run_report_hash", _required_hash("external_run_report_hash", self.external_run_report_hash))
        object.__setattr__(self, "observation_hash", _required_hash("observation_hash", self.observation_hash))
        if self.schema_version != CODEX_EXTERNAL_RUN_OBSERVATION_SCHEMA_VERSION:
            raise ValueError("unsupported codex external run observation schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "flow_id": self.flow_id,
            "request_hash": self.request_hash,
            "handoff_hash": self.handoff_hash,
            "human_operator": self.human_operator,
            "external_run_mode": self.external_run_mode,
            "external_run_started_at": self.external_run_started_at,
            "external_run_reported_at": self.external_run_reported_at,
            "external_run_report_hash": self.external_run_report_hash,
            "observation_hash": self.observation_hash,
        }


@dataclass(frozen=True)
class CodexReturnedOutputEvidence:
    schema_version: str
    flow_id: str
    request_hash: str
    handoff_hash: str
    observation_hash: str
    output_summary: str
    changed_files_claimed: tuple[str, ...]
    tests_claimed: tuple[str, ...]
    commit_hash_claimed: str | None
    risk_notes: tuple[str, ...]
    authority_claims: tuple[str, ...]
    returned_at: int
    expires_at: int
    output_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "flow_id", _identifier("flow_id", self.flow_id))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        object.__setattr__(self, "handoff_hash", _required_hash("handoff_hash", self.handoff_hash))
        object.__setattr__(self, "observation_hash", _required_hash("observation_hash", self.observation_hash))
        object.__setattr__(self, "output_summary", _required_text("output_summary", self.output_summary))
        object.__setattr__(self, "changed_files_claimed", _path_tuple("changed_files_claimed", self.changed_files_claimed, allow_empty=True))
        object.__setattr__(self, "tests_claimed", _text_tuple("tests_claimed", self.tests_claimed, allow_empty=True))
        object.__setattr__(self, "commit_hash_claimed", _optional_hash("commit_hash_claimed", self.commit_hash_claimed))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes, allow_empty=True))
        object.__setattr__(self, "authority_claims", _text_tuple("authority_claims", self.authority_claims, allow_empty=True))
        object.__setattr__(self, "returned_at", _nonnegative_int("returned_at", self.returned_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "output_hash", _required_hash("output_hash", self.output_hash))
        if self.schema_version != CODEX_RETURNED_OUTPUT_SCHEMA_VERSION:
            raise ValueError("unsupported codex returned output schema version")
        if self.expires_at <= self.returned_at:
            raise ValueError("output expires_at must be greater than returned_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "flow_id": self.flow_id,
            "request_hash": self.request_hash,
            "handoff_hash": self.handoff_hash,
            "observation_hash": self.observation_hash,
            "output_summary": self.output_summary,
            "changed_files_claimed": self.changed_files_claimed,
            "tests_claimed": self.tests_claimed,
            "commit_hash_claimed": self.commit_hash_claimed,
            "risk_notes": self.risk_notes,
            "authority_claims": self.authority_claims,
            "returned_at": self.returned_at,
            "expires_at": self.expires_at,
            "output_hash": self.output_hash,
        }


@dataclass(frozen=True)
class CodexLiveFlowReviewResult:
    schema_version: str
    ok: bool
    blocked: bool
    codex_invocation_allowed: bool
    execution_allowed: bool
    write_allowed: bool
    patch_apply_allowed: bool
    test_execution_allowed: bool
    commit_allowed: bool
    push_allowed: bool
    dispatch_allowed: bool
    retry_allowed: bool
    fallback_allowed: bool
    streaming_allowed: bool
    requires_human_review: bool
    requires_controlled_path: bool
    flow_id: str | None
    task_id: str | None
    request_hash: str | None
    handoff_hash: str | None
    observation_hash: str | None
    output_hash: str | None
    claimed_changed_files: tuple[str, ...]
    claimed_tests: tuple[str, ...]
    claimed_commit_hash: str | None
    risk_tier: str
    live_flow_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    review_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_run_codex: bool = False
    can_apply: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_dispatch: bool = False
    can_retry: bool = False
    can_fallback: bool = False
    can_stream: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_run_tests: bool = False
    approval_created: bool = False
    dispatcher_created: bool = False
    patch_applied: bool = False
    files_written: bool = False
    tests_executed: bool = False
    process_started: bool = False
    network_called: bool = False
    provider_called: bool = False
    mcp_called: bool = False
    browser_opened: bool = False
    package_manager_called: bool = False
    git_action_performed: bool = False
    agent_loop_started: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "ok", bool(self.ok) and not bool(self.blocked))
        object.__setattr__(self, "blocked", bool(self.blocked))
        for field_name in _REVIEW_FALSE_FLAGS:
            object.__setattr__(self, field_name, False)
        object.__setattr__(self, "requires_human_review", True)
        object.__setattr__(self, "requires_controlled_path", True)
        for field_name in ("request_hash", "handoff_hash", "observation_hash", "output_hash", "claimed_commit_hash"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required_hash(field_name, value))
        if self.flow_id is not None:
            object.__setattr__(self, "flow_id", _identifier("flow_id", self.flow_id))
        if self.task_id is not None:
            object.__setattr__(self, "task_id", _identifier("task_id", self.task_id))
        object.__setattr__(self, "claimed_changed_files", _path_tuple("claimed_changed_files", self.claimed_changed_files, allow_empty=True))
        object.__setattr__(self, "claimed_tests", _text_tuple("claimed_tests", self.claimed_tests, allow_empty=True))
        if self.risk_tier not in {CODEX_LIVE_FLOW_RISK_LOW, CODEX_LIVE_FLOW_RISK_MEDIUM, CODEX_LIVE_FLOW_RISK_HIGH, CODEX_LIVE_FLOW_RISK_BLOCKED}:
            raise ValueError("unsupported codex live-flow risk tier")
        object.__setattr__(self, "live_flow_codes", tuple(sorted(set(_required_text("live_flow_codes", item) for item in self.live_flow_codes))))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(_required_text("reason_codes", item) for item in self.reason_codes))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION,
            "ok": self.ok,
            "blocked": self.blocked,
            "codex_invocation_allowed": False,
            "execution_allowed": False,
            "write_allowed": False,
            "patch_apply_allowed": False,
            "test_execution_allowed": False,
            "commit_allowed": False,
            "push_allowed": False,
            "dispatch_allowed": False,
            "retry_allowed": False,
            "fallback_allowed": False,
            "streaming_allowed": False,
            "requires_human_review": True,
            "requires_controlled_path": True,
            "flow_id": self.flow_id,
            "task_id": self.task_id,
            "request_hash": self.request_hash,
            "handoff_hash": self.handoff_hash,
            "observation_hash": self.observation_hash,
            "output_hash": self.output_hash,
            "claimed_changed_files": self.claimed_changed_files,
            "claimed_tests": self.claimed_tests,
            "claimed_commit_hash": self.claimed_commit_hash,
            "risk_tier": self.risk_tier,
            "live_flow_codes": self.live_flow_codes,
            "reason_codes": self.reason_codes,
            "review_hash": self.review_hash,
        }
        for field_name in _REVIEW_FALSE_FLAGS:
            data[field_name] = False
        return data


_REVIEW_FALSE_FLAGS = (
    "codex_invocation_allowed",
    "execution_allowed",
    "write_allowed",
    "patch_apply_allowed",
    "test_execution_allowed",
    "commit_allowed",
    "push_allowed",
    "dispatch_allowed",
    "retry_allowed",
    "fallback_allowed",
    "streaming_allowed",
    "gate_satisfied",
    "human_barrier_satisfied",
    "can_run_codex",
    "can_apply",
    "can_write",
    "can_execute",
    "can_dispatch",
    "can_retry",
    "can_fallback",
    "can_stream",
    "can_commit",
    "can_push",
    "can_run_tests",
    "approval_created",
    "dispatcher_created",
    "patch_applied",
    "files_written",
    "tests_executed",
    "process_started",
    "network_called",
    "provider_called",
    "mcp_called",
    "browser_opened",
    "package_manager_called",
    "git_action_performed",
    "agent_loop_started",
)


def canonical_codex_live_flow_json(value: Any) -> str:
    return json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_codex_live_flow_value(value: Any) -> str:
    return hashlib.sha256(canonical_codex_live_flow_json(value).encode("utf-8")).hexdigest()


def build_codex_live_flow_request(
    *,
    flow_id: str,
    task_id: str,
    step_id: str,
    task_goal: str,
    prepared_prompt_hash: str,
    coding_assistant_request_hash: str,
    coding_assistant_boundary_review_hash: str,
    orchestration_plan_hash: str | None,
    requested_by: str,
    requested_at: int,
    expires_at: int,
) -> CodexLiveFlowRequest:
    material = {
        "schema_version": CODEX_LIVE_FLOW_REQUEST_SCHEMA_VERSION,
        "flow_id": _identifier("flow_id", flow_id),
        "task_id": _identifier("task_id", task_id),
        "step_id": _required_text("step_id", step_id).casefold(),
        "task_goal": _required_text("task_goal", task_goal),
        "prepared_prompt_hash": _required_hash("prepared_prompt_hash", prepared_prompt_hash),
        "coding_assistant_request_hash": _required_hash("coding_assistant_request_hash", coding_assistant_request_hash),
        "coding_assistant_boundary_review_hash": _required_hash("coding_assistant_boundary_review_hash", coding_assistant_boundary_review_hash),
        "orchestration_plan_hash": _optional_hash("orchestration_plan_hash", orchestration_plan_hash),
        "requested_by": _required_text("requested_by", requested_by),
        "requested_at": _nonnegative_int("requested_at", requested_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return CodexLiveFlowRequest(**material, request_hash=_hash_material(material))


def build_codex_live_flow_handoff_packet(
    *,
    flow_id: str,
    request_hash: str,
    task_id: str,
    handoff_summary: str,
    allowed_files: tuple[str, ...],
    forbidden_files: tuple[str, ...],
    required_tests: tuple[str, ...],
    forbidden_actions: tuple[str, ...],
    human_operator_required: bool = True,
    codex_invocation_allowed_by_aoia: bool = False,
    created_at: int,
    expires_at: int,
) -> CodexLiveFlowHandoffPacket:
    if not isinstance(human_operator_required, bool):
        raise TypeError("human_operator_required must be boolean")
    if not isinstance(codex_invocation_allowed_by_aoia, bool):
        raise TypeError("codex_invocation_allowed_by_aoia must be boolean")
    material = {
        "schema_version": CODEX_LIVE_FLOW_HANDOFF_SCHEMA_VERSION,
        "flow_id": _identifier("flow_id", flow_id),
        "request_hash": _required_hash("request_hash", request_hash),
        "task_id": _identifier("task_id", task_id),
        "handoff_summary": _required_text("handoff_summary", handoff_summary),
        "allowed_files": _path_tuple("allowed_files", allowed_files, allow_empty=False),
        "forbidden_files": _path_tuple("forbidden_files", forbidden_files, allow_empty=True),
        "required_tests": _text_tuple("required_tests", required_tests, allow_empty=True),
        "forbidden_actions": _text_tuple("forbidden_actions", forbidden_actions, allow_empty=True),
        "human_operator_required": human_operator_required,
        "codex_invocation_allowed_by_aoia": codex_invocation_allowed_by_aoia,
        "created_at": _nonnegative_int("created_at", created_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return CodexLiveFlowHandoffPacket(**material, handoff_hash=_hash_material(material))


def build_codex_external_run_observation(
    *,
    flow_id: str,
    request_hash: str,
    handoff_hash: str,
    human_operator: str,
    external_run_mode: str,
    external_run_started_at: int,
    external_run_reported_at: int,
    external_run_report_hash: str,
) -> CodexExternalRunObservation:
    material = {
        "schema_version": CODEX_EXTERNAL_RUN_OBSERVATION_SCHEMA_VERSION,
        "flow_id": _identifier("flow_id", flow_id),
        "request_hash": _required_hash("request_hash", request_hash),
        "handoff_hash": _required_hash("handoff_hash", handoff_hash),
        "human_operator": _required_text("human_operator", human_operator),
        "external_run_mode": _required_text("external_run_mode", external_run_mode).casefold(),
        "external_run_started_at": _nonnegative_int("external_run_started_at", external_run_started_at),
        "external_run_reported_at": _nonnegative_int("external_run_reported_at", external_run_reported_at),
        "external_run_report_hash": _required_hash("external_run_report_hash", external_run_report_hash),
    }
    return CodexExternalRunObservation(**material, observation_hash=_hash_material(material))


def build_codex_returned_output_evidence(
    *,
    flow_id: str,
    request_hash: str,
    handoff_hash: str,
    observation_hash: str,
    output_summary: str,
    changed_files_claimed: tuple[str, ...],
    tests_claimed: tuple[str, ...],
    commit_hash_claimed: str | None,
    risk_notes: tuple[str, ...],
    authority_claims: tuple[str, ...],
    returned_at: int,
    expires_at: int,
) -> CodexReturnedOutputEvidence:
    material = {
        "schema_version": CODEX_RETURNED_OUTPUT_SCHEMA_VERSION,
        "flow_id": _identifier("flow_id", flow_id),
        "request_hash": _required_hash("request_hash", request_hash),
        "handoff_hash": _required_hash("handoff_hash", handoff_hash),
        "observation_hash": _required_hash("observation_hash", observation_hash),
        "output_summary": _required_text("output_summary", output_summary),
        "changed_files_claimed": _path_tuple("changed_files_claimed", changed_files_claimed, allow_empty=True),
        "tests_claimed": _text_tuple("tests_claimed", tests_claimed, allow_empty=True),
        "commit_hash_claimed": _optional_hash("commit_hash_claimed", commit_hash_claimed),
        "risk_notes": _text_tuple("risk_notes", risk_notes, allow_empty=True),
        "authority_claims": _text_tuple("authority_claims", authority_claims, allow_empty=True),
        "returned_at": _nonnegative_int("returned_at", returned_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return CodexReturnedOutputEvidence(**material, output_hash=_hash_material(material))


def evaluate_codex_live_flow(
    *,
    request: CodexLiveFlowRequest,
    handoff: CodexLiveFlowHandoffPacket,
    observation: CodexExternalRunObservation,
    output: CodexReturnedOutputEvidence,
    now: int,
) -> CodexLiveFlowReviewResult:
    reason_codes: list[str] = []
    try:
        now_value = _nonnegative_int("now", now)
    except (TypeError, ValueError):
        return _blocked((CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME,))

    try:
        request_data = _coerce_mapping(request)
        handoff_data = _coerce_mapping(handoff)
        observation_data = _coerce_mapping(observation)
        output_data = _coerce_mapping(output)
        evidence_fingerprint = _json_fingerprint(
            {
                "request": request_data,
                "handoff": handoff_data,
                "observation": observation_data,
                "output": output_data,
            }
        )
    except TypeError:
        return _blocked((CODEX_LIVE_FLOW_BLOCKED_NON_JSON_SERIALIZABLE,))

    reason_codes.extend(_danger_reason_codes((request_data, handoff_data, observation_data, output_data)))
    if _contains_unknown_fields(request_data, handoff_data, observation_data, output_data):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_AMBIGUOUS_EVIDENCE)
    if _invalid_hash_evidence_present(request_data, handoff_data, observation_data, output_data):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)
    if _invalid_time_evidence_present(request_data, handoff_data, observation_data, output_data):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME)
    if _invalid_raw_paths_present(handoff_data, output_data):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH)

    try:
        live_request = _coerce_request(request_data)
        live_handoff = _coerce_handoff(handoff_data)
        live_observation = _coerce_observation(observation_data)
        live_output = _coerce_output(output_data)
    except (TypeError, ValueError):
        return _blocked(tuple(reason_codes or (CODEX_LIVE_FLOW_BLOCKED_AMBIGUOUS_EVIDENCE,)), input_fingerprint=evidence_fingerprint)

    if live_request.step_id not in SUPPORTED_STEP_IDS:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_REQUEST)
    if live_observation.external_run_mode not in SUPPORTED_EXTERNAL_RUN_MODES:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_EXTERNAL_RUN_MODE)

    if live_handoff.request_hash != live_request.request_hash or live_handoff.flow_id != live_request.flow_id or live_handoff.task_id != live_request.task_id:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)
    if live_observation.request_hash != live_request.request_hash or live_observation.handoff_hash != live_handoff.handoff_hash or live_observation.flow_id != live_request.flow_id:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)
    if (
        live_output.request_hash != live_request.request_hash
        or live_output.handoff_hash != live_handoff.handoff_hash
        or live_output.observation_hash != live_observation.observation_hash
        or live_output.flow_id != live_request.flow_id
    ):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)

    if _invalid_paths_present(live_handoff.allowed_files, live_handoff.forbidden_files, live_output.changed_files_claimed):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH)
    if any(path in set(live_handoff.forbidden_files) for path in live_output.changed_files_claimed):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_FORBIDDEN_FILE)
    if any(path not in set(live_handoff.allowed_files) for path in live_output.changed_files_claimed):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_CHANGED_FILE_OUT_OF_SCOPE)

    if not live_handoff.human_operator_required:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HUMAN_OPERATOR_REQUIRED)
    if live_handoff.codex_invocation_allowed_by_aoia:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_AOIA_CODEX_INVOCATION)
    if live_output.authority_claims:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM)

    if now_value < live_request.requested_at or now_value < live_handoff.created_at or now_value < live_observation.external_run_reported_at or now_value < live_output.returned_at:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME)
    if live_observation.external_run_reported_at < live_observation.external_run_started_at:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME)
    if now_value > live_request.expires_at:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_EXPIRED_REQUEST)
    if now_value > live_handoff.expires_at:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_EXPIRED_HANDOFF)
    if now_value > live_output.expires_at:
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_EXPIRED_OUTPUT)

    if live_request.request_hash != _hash_material(_request_hash_material(live_request)):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)
    if live_handoff.handoff_hash != _hash_material(_handoff_hash_material(live_handoff)):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)
    if live_observation.observation_hash != _hash_material(_observation_hash_material(live_observation)):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)
    if live_output.output_hash != _hash_material(_output_hash_material(live_output)):
        reason_codes.append(CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH)

    blocked = bool(set(reason_codes) - {CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW_REASON, CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH_REASON})
    if blocked:
        reason_codes = sorted(set(reason_codes))
    else:
        reason_codes = sorted(
            {
                CODEX_LIVE_FLOW_OK,
                CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW_REASON,
                CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH_REASON,
            }
        )

    live_flow_codes = (
        CODEX_LIVE_FLOW_EXTERNAL_OUTPUT_UNTRUSTED,
        CODEX_LIVE_FLOW_HUMAN_MEDIATED_ONLY,
        CODEX_LIVE_FLOW_NON_AUTHORITY,
        CODEX_LIVE_FLOW_REQUIRES_BOUNDARY_REVIEW,
        CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH,
        CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW,
    )
    risk_tier = _risk_tier(blocked, live_output)
    material = {
        "schema_version": CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION,
        "ok": not blocked,
        "blocked": blocked,
        "codex_invocation_allowed": False,
        "execution_allowed": False,
        "write_allowed": False,
        "patch_apply_allowed": False,
        "test_execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "dispatch_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "flow_id": live_request.flow_id,
        "task_id": live_request.task_id,
        "request_hash": live_request.request_hash,
        "handoff_hash": live_handoff.handoff_hash,
        "observation_hash": live_observation.observation_hash,
        "output_hash": live_output.output_hash,
        "claimed_changed_files": live_output.changed_files_claimed,
        "claimed_tests": live_output.tests_claimed,
        "claimed_commit_hash": live_output.commit_hash_claimed,
        "risk_tier": risk_tier,
        "live_flow_codes": live_flow_codes,
        "reason_codes": tuple(reason_codes),
    }
    return CodexLiveFlowReviewResult(
        schema_version=CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION,
        ok=not blocked,
        blocked=blocked,
        codex_invocation_allowed=False,
        execution_allowed=False,
        write_allowed=False,
        patch_apply_allowed=False,
        test_execution_allowed=False,
        commit_allowed=False,
        push_allowed=False,
        dispatch_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        flow_id=live_request.flow_id,
        task_id=live_request.task_id,
        request_hash=live_request.request_hash,
        handoff_hash=live_handoff.handoff_hash,
        observation_hash=live_observation.observation_hash,
        output_hash=live_output.output_hash,
        claimed_changed_files=live_output.changed_files_claimed,
        claimed_tests=live_output.tests_claimed,
        claimed_commit_hash=live_output.commit_hash_claimed,
        risk_tier=risk_tier,
        live_flow_codes=live_flow_codes,
        reason_codes=tuple(reason_codes),
        review_hash=hash_codex_live_flow_value(material),
    )


def _hash_material(value: Mapping[str, Any]) -> str:
    data = dict(value)
    for field_name in ("request_hash", "handoff_hash", "observation_hash", "output_hash", "review_hash"):
        data.pop(field_name, None)
    return hash_codex_live_flow_value(_json_fingerprint(data))


def _request_hash_material(value: CodexLiveFlowRequest) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("request_hash", None)
    return data


def _handoff_hash_material(value: CodexLiveFlowHandoffPacket) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("handoff_hash", None)
    return data


def _observation_hash_material(value: CodexExternalRunObservation) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("observation_hash", None)
    return data


def _output_hash_material(value: CodexReturnedOutputEvidence) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("output_hash", None)
    return data


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> CodexLiveFlowReviewResult:
    codes = tuple(sorted(set(reason_codes)))
    material = {
        "schema_version": CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION,
        "ok": False,
        "blocked": True,
        "codex_invocation_allowed": False,
        "execution_allowed": False,
        "write_allowed": False,
        "patch_apply_allowed": False,
        "test_execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "dispatch_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "flow_id": None,
        "task_id": None,
        "request_hash": None,
        "handoff_hash": None,
        "observation_hash": None,
        "output_hash": None,
        "claimed_changed_files": (),
        "claimed_tests": (),
        "claimed_commit_hash": None,
        "risk_tier": CODEX_LIVE_FLOW_RISK_BLOCKED,
        "live_flow_codes": _base_live_flow_codes(),
        "reason_codes": codes,
        "input_fingerprint": input_fingerprint,
    }
    return CodexLiveFlowReviewResult(
        schema_version=CODEX_LIVE_FLOW_REVIEW_SCHEMA_VERSION,
        ok=False,
        blocked=True,
        codex_invocation_allowed=False,
        execution_allowed=False,
        write_allowed=False,
        patch_apply_allowed=False,
        test_execution_allowed=False,
        commit_allowed=False,
        push_allowed=False,
        dispatch_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        flow_id=None,
        task_id=None,
        request_hash=None,
        handoff_hash=None,
        observation_hash=None,
        output_hash=None,
        claimed_changed_files=(),
        claimed_tests=(),
        claimed_commit_hash=None,
        risk_tier=CODEX_LIVE_FLOW_RISK_BLOCKED,
        live_flow_codes=_base_live_flow_codes(),
        reason_codes=codes,
        review_hash=hash_codex_live_flow_value(material),
    )


def _base_live_flow_codes() -> tuple[str, ...]:
    return (
        CODEX_LIVE_FLOW_EXTERNAL_OUTPUT_UNTRUSTED,
        CODEX_LIVE_FLOW_HUMAN_MEDIATED_ONLY,
        CODEX_LIVE_FLOW_NON_AUTHORITY,
        CODEX_LIVE_FLOW_REQUIRES_BOUNDARY_REVIEW,
        CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH,
        CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW,
    )


def _coerce_request(value: object) -> CodexLiveFlowRequest:
    if isinstance(value, CodexLiveFlowRequest):
        return value
    if isinstance(value, Mapping):
        return CodexLiveFlowRequest(**_sanitize_mapping(value, _ALLOWED_REQUEST_FIELDS))
    raise TypeError("codex live-flow request is required")


def _coerce_handoff(value: object) -> CodexLiveFlowHandoffPacket:
    if isinstance(value, CodexLiveFlowHandoffPacket):
        return value
    if isinstance(value, Mapping):
        return CodexLiveFlowHandoffPacket(**_sanitize_mapping(value, _ALLOWED_HANDOFF_FIELDS))
    raise TypeError("codex live-flow handoff is required")


def _coerce_observation(value: object) -> CodexExternalRunObservation:
    if isinstance(value, CodexExternalRunObservation):
        return value
    if isinstance(value, Mapping):
        return CodexExternalRunObservation(**_sanitize_mapping(value, _ALLOWED_OBSERVATION_FIELDS))
    raise TypeError("codex external run observation is required")


def _coerce_output(value: object) -> CodexReturnedOutputEvidence:
    if isinstance(value, CodexReturnedOutputEvidence):
        return value
    if isinstance(value, Mapping):
        return CodexReturnedOutputEvidence(**_sanitize_mapping(value, _ALLOWED_OUTPUT_FIELDS))
    raise TypeError("codex returned output evidence is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("codex live-flow evidence must be mapping evidence")


def _sanitize_mapping(value: Mapping[str, Any], allowed_fields: frozenset[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key in allowed_fields}


def _contains_unknown_fields(request: Mapping[str, Any], handoff: Mapping[str, Any], observation: Mapping[str, Any], output: Mapping[str, Any]) -> bool:
    return (
        any(key not in _ALLOWED_REQUEST_FIELDS for key in request)
        or any(key not in _ALLOWED_HANDOFF_FIELDS for key in handoff)
        or any(key not in _ALLOWED_OBSERVATION_FIELDS for key in observation)
        or any(key not in _ALLOWED_OUTPUT_FIELDS for key in output)
    )


def _invalid_hash_evidence_present(request: Mapping[str, Any], handoff: Mapping[str, Any], observation: Mapping[str, Any], output: Mapping[str, Any]) -> bool:
    for data, fields in (
        (request, ("prepared_prompt_hash", "coding_assistant_request_hash", "coding_assistant_boundary_review_hash", "request_hash")),
        (handoff, ("request_hash", "handoff_hash")),
        (observation, ("request_hash", "handoff_hash", "external_run_report_hash", "observation_hash")),
        (output, ("request_hash", "handoff_hash", "observation_hash", "output_hash")),
    ):
        for field_name in fields:
            if field_name in data and not _sha256_like(data[field_name]):
                return True
    if request.get("orchestration_plan_hash") is not None and not _sha256_like(request.get("orchestration_plan_hash")):
        return True
    if output.get("commit_hash_claimed") is not None and not _sha256_like(output.get("commit_hash_claimed")):
        return True
    return False


def _invalid_time_evidence_present(request: Mapping[str, Any], handoff: Mapping[str, Any], observation: Mapping[str, Any], output: Mapping[str, Any]) -> bool:
    request_times = (request.get("requested_at"), request.get("expires_at"))
    handoff_times = (handoff.get("created_at"), handoff.get("expires_at"))
    observation_times = (observation.get("external_run_started_at"), observation.get("external_run_reported_at"))
    output_times = (output.get("returned_at"), output.get("expires_at"))
    if not all(_valid_nonnegative_int(item) for item in (*request_times, *handoff_times, *observation_times, *output_times)):
        return True
    if request_times[1] <= request_times[0] or handoff_times[1] <= handoff_times[0] or output_times[1] <= output_times[0]:
        return True
    if observation_times[1] < observation_times[0]:
        return True
    return False


def _invalid_paths_present(*path_groups: tuple[str, ...]) -> bool:
    for path_group in path_groups:
        for path in path_group:
            if not _safe_path(path):
                return True
    return False


def _invalid_raw_paths_present(handoff: Mapping[str, Any], output: Mapping[str, Any]) -> bool:
    for value in (
        handoff.get("allowed_files"),
        handoff.get("forbidden_files"),
        output.get("changed_files_claimed"),
    ):
        if not isinstance(value, (tuple, list)):
            return True
        if any(not _safe_path(item) for item in value):
            return True
    return False


def _safe_path(path: object) -> bool:
    if not isinstance(path, str) or not path.strip():
        return False
    text = path.strip()
    lowered = text.casefold()
    if text.startswith(("/", "~")) or "\\" in text or ".." in text.split("/"):
        return False
    if any(term in lowered for term in _UNSAFE_PATH_TERMS):
        return False
    return bool(_SAFE_PATH_PATTERN.fullmatch(text))


def _danger_reason_codes(value: object) -> list[str]:
    codes: set[str] = set()
    for key, text in _scanned_text_items(value):
        normalized = text.casefold()
        normalized_key = key.casefold()
        if normalized_key in _AUTHORITY_FIELD_NAMES or any(term in normalized for term in _AUTHORITY_FIELD_NAMES):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM)
        if any(term in normalized for term in _CODEX_INVOCATION_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_CODEX_INVOCATION_SMUGGLING)
        if any(term in normalized for term in _AIDER_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_AIDER_INVOCATION)
        if any(term in normalized for term in _PATCH_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_PATCH_APPLICATION)
        if any(term in normalized for term in _WRITE_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_WRITE_CLAIM)
        if any(term in normalized for term in _TEST_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_TEST_EXECUTION)
        if any(term in normalized for term in _COMMIT_PUSH_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_COMMIT_OR_PUSH)
        if any(term.casefold() in normalized for term in _COMMAND_INJECTION_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_COMMAND_INJECTION)
        if any(term in normalized for term in _PROVIDER_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_PROVIDER_CALL)
        if any(term in normalized for term in _GIT_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_GIT_ACTION)
        if any(term in normalized for term in _PACKAGE_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_PACKAGE_INSTALL)
        if any(term in normalized for term in _BROWSER_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_BROWSER_ACTION)
        if any(term in normalized for term in _MCP_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_MCP_TOOL)
        if any(term in normalized for term in _AGENT_LOOP_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_AGENT_LOOP)
        if any(term in normalized for term in _RETRY_FALLBACK_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING)
        if any(term in normalized for term in _ENV_SECRET_TERMS):
            codes.add(CODEX_LIVE_FLOW_BLOCKED_ENV_OR_SECRET)
    return sorted(codes)


def _scanned_text_items(value: object, *, parent_key: str = "") -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            if key not in _TEXT_SCAN_SKIP_KEYS:
                items.append((key, key))
                items.extend(_scanned_text_items(item, parent_key=key))
        return tuple(items)
    if isinstance(value, (tuple, list)):
        items = []
        for item in value:
            items.extend(_scanned_text_items(item, parent_key=parent_key))
        return tuple(items)
    if isinstance(value, str):
        return ((parent_key, value),)
    return ()


def _risk_tier(blocked: bool, output: CodexReturnedOutputEvidence) -> str:
    if blocked:
        return CODEX_LIVE_FLOW_RISK_BLOCKED
    if output.authority_claims or output.commit_hash_claimed is not None:
        return CODEX_LIVE_FLOW_RISK_HIGH
    if output.changed_files_claimed:
        return CODEX_LIVE_FLOW_RISK_MEDIUM
    return CODEX_LIVE_FLOW_RISK_LOW


def _identifier(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError(f"{name} must be a stable identifier")
    return text


def _required_hash(name: str, value: object) -> str:
    text = _required_text(name, value).casefold()
    if not _sha256_like(text):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return text


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_hash(name, value)


def _path_tuple(name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    items = _text_tuple(name, value, allow_empty=allow_empty)
    for item in items:
        if not _safe_path(item):
            raise ValueError(f"{name} contains unsafe path metadata")
    return items


def _text_tuple(name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    if not value and not allow_empty:
        raise TypeError(f"{name} must not be empty")
    return tuple(_required_text(name, item) for item in value)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    text = value.strip()
    if len(text) > _MAX_TEXT:
        raise ValueError(f"{name} is too long")
    return text


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _valid_nonnegative_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.casefold())


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("codex live-flow evidence is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 1_000_000_000:
            raise TypeError("integer evidence is excessive")
        return value
    if isinstance(value, float):
        raise TypeError("floating point evidence is ambiguous")
    if isinstance(value, str):
        if len(value) > _MAX_TEXT:
            raise TypeError("text evidence is excessive")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("mapping evidence is excessive")
        normalized: dict[str, Any] = {}
        for key in value:
            if not isinstance(key, str) or not key.strip():
                raise TypeError("mapping evidence keys must be non-empty text")
        for key in sorted(value):
            normalized[key.strip()] = _json_fingerprint(value[key], depth=depth + 1)
        return normalized
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("sequence evidence is excessive")
        return tuple(_json_fingerprint(item, depth=depth + 1) for item in value)
    raise TypeError("codex live-flow evidence must be JSON serializable")
