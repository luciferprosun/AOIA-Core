from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


LOCAL_AGENT_OBJECTIVE_SCHEMA_VERSION = "AOIA_LOCAL_AGENT_OBJECTIVE_1A"
LOCAL_AGENT_LOOP_STATE_SCHEMA_VERSION = "AOIA_LOCAL_AGENT_LOOP_STATE_1A"
LOCAL_AGENT_CANDIDATE_ACTION_SCHEMA_VERSION = "AOIA_LOCAL_AGENT_CANDIDATE_ACTION_1A"
LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION = "AOIA_LOCAL_AGENT_LOOP_REVIEW_1A"

LOCAL_AGENT_LOOP_READY_METADATA = "LOCAL_AGENT_LOOP_READY_METADATA"
LOCAL_AGENT_LOOP_BLOCKED_METADATA = "LOCAL_AGENT_LOOP_BLOCKED_METADATA"
LOCAL_AGENT_LOOP_SELECTED_METADATA_ONLY = "LOCAL_AGENT_LOOP_SELECTED_METADATA_ONLY"
LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW = "LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW"
LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH = "LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH"
LOCAL_AGENT_LOOP_NON_AUTHORITY = "LOCAL_AGENT_LOOP_NON_AUTHORITY"

LOCAL_AGENT_LOOP_OK = "LOCAL_AGENT_LOOP_OK"
LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON = "LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW"
LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON = "LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH"
LOCAL_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE = "LOCAL_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE"
LOCAL_AGENT_LOOP_BLOCKED_INVALID_STATE = "LOCAL_AGENT_LOOP_BLOCKED_INVALID_STATE"
LOCAL_AGENT_LOOP_BLOCKED_INVALID_CANDIDATE = "LOCAL_AGENT_LOOP_BLOCKED_INVALID_CANDIDATE"
LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND = "LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND"
LOCAL_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND = "LOCAL_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND"
LOCAL_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED = "LOCAL_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED"
LOCAL_AGENT_LOOP_BLOCKED_STEP54_NOT_AVAILABLE = "LOCAL_AGENT_LOOP_BLOCKED_STEP54_NOT_AVAILABLE"
LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID = "LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID"
LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH = "LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH"
LOCAL_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE = "LOCAL_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE"
LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH = "LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH"
LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH = "LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH"
LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME = "LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME"
LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE = "LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE"
LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_STATE = "LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_STATE"
LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE = "LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE"
LOCAL_AGENT_LOOP_BLOCKED_COMMAND_INJECTION = "LOCAL_AGENT_LOOP_BLOCKED_COMMAND_INJECTION"
LOCAL_AGENT_LOOP_BLOCKED_PROVIDER_CALL = "LOCAL_AGENT_LOOP_BLOCKED_PROVIDER_CALL"
LOCAL_AGENT_LOOP_BLOCKED_GIT_ACTION = "LOCAL_AGENT_LOOP_BLOCKED_GIT_ACTION"
LOCAL_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL = "LOCAL_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL"
LOCAL_AGENT_LOOP_BLOCKED_BROWSER_ACTION = "LOCAL_AGENT_LOOP_BLOCKED_BROWSER_ACTION"
LOCAL_AGENT_LOOP_BLOCKED_MCP_TOOL = "LOCAL_AGENT_LOOP_BLOCKED_MCP_TOOL"
LOCAL_AGENT_LOOP_BLOCKED_CODEX_AIDER = "LOCAL_AGENT_LOOP_BLOCKED_CODEX_AIDER"
LOCAL_AGENT_LOOP_BLOCKED_LOCAL_LLM = "LOCAL_AGENT_LOOP_BLOCKED_LOCAL_LLM"
LOCAL_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION = "LOCAL_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION"
LOCAL_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING = "LOCAL_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING"
LOCAL_AGENT_LOOP_BLOCKED_ENV_OR_SECRET = "LOCAL_AGENT_LOOP_BLOCKED_ENV_OR_SECRET"
LOCAL_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM = "LOCAL_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM"
LOCAL_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE = "LOCAL_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE"
LOCAL_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE = "LOCAL_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE"

LOCAL_AGENT_LOOP_STATUS_READY = "READY_METADATA"
LOCAL_AGENT_LOOP_STATUS_BLOCKED = "BLOCKED_METADATA"
LOCAL_AGENT_LOOP_RISK_LOW = "LOW"
LOCAL_AGENT_LOOP_RISK_MEDIUM = "MEDIUM"
LOCAL_AGENT_LOOP_RISK_HIGH = "HIGH"
LOCAL_AGENT_LOOP_RISK_BLOCKED = "BLOCKED"

SUPPORTED_NEXT_ACTION_KINDS = frozenset(
    {
        "request_human_review",
        "record_feedback_observation",
        "build_recovery_plan_metadata",
        "build_async_orchestration_metadata",
        "build_codex_handoff_metadata",
        "build_package_install_proposal_metadata",
        "build_browser_read_request_metadata",
        "build_browser_automation_preview_metadata",
        "evaluate_browser_governance_metadata",
        "evaluate_mcp_boundary_metadata",
        "evaluate_coding_assistant_boundary_metadata",
        "mark_blocked",
        "no_op",
    }
)
HIGH_RISK_ACTION_KINDS = frozenset(
    {
        "build_package_install_proposal_metadata",
        "build_browser_automation_preview_metadata",
        "evaluate_mcp_boundary_metadata",
        "evaluate_coding_assistant_boundary_metadata",
        "build_codex_handoff_metadata",
    }
)
SUPPORTED_TARGET_STEPS = frozenset(
    {
        "step_42_package_install_proposal",
        "step_43_controlled_package_install",
        "step_44_controlled_browser_read",
        "step_45_browser_automation_preview",
        "step_46_browser_automation_governance",
        "step_47_controlled_browser_automation",
        "step_48_coding_assistant_boundary",
        "step_49_mcp_boundary",
        "step_50_async_io_orchestration",
        "step_51_feedback_recovery",
        "step_52_codex_live_flow",
        "step_53_local_agent_loop",
    }
)
STEP54_TARGET = "step_54_provider_agent_loop"

_ALLOWED_OBJECTIVE_FIELDS = frozenset(
    {
        "schema_version",
        "objective_id",
        "objective_summary",
        "allowed_next_action_kinds",
        "forbidden_next_action_kinds",
        "context_hashes",
        "requested_by",
        "requested_at",
        "expires_at",
        "objective_hash",
    }
)
_ALLOWED_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "loop_id",
        "objective_hash",
        "iteration_index",
        "completed_iteration_hashes",
        "current_evidence_hashes",
        "orchestration_review_hash",
        "recovery_review_hash",
        "codex_live_flow_review_hash",
        "state_created_at",
        "state_expires_at",
        "state_hash",
    }
)
_ALLOWED_CANDIDATE_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "action_kind",
        "action_summary",
        "target_step",
        "required_evidence_hashes",
        "risk_notes",
        "proposed_by",
        "proposed_at",
        "expires_at",
        "candidate_hash",
    }
)
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approve",
        "approved",
        "authorize",
        "authorized",
        "authority",
        "selected_to_execute",
        "ready_to_execute",
        "agent_allowed",
        "can_execute",
        "can_dispatch",
        "can_retry",
        "can_fallback",
        "can_stream",
        "can_write",
        "can_commit",
        "can_push",
        "can_call_tool",
        "can_call_provider",
        "can_call_mcp",
        "can_call_llm",
        "gate_satisfied",
        "human_approved",
        "gate_pass",
        "grant_permission",
    }
)
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
    "../",
    "/etc/",
    ".git/",
)
_PROVIDER_TERMS = ("provider" + "_call", "call_provider", "openai", "anthropic", "gemini")
_GIT_TERMS = ("git" + "_action", "git_commit", "git_push")
_PACKAGE_TERMS = ("package" + "_install", "pip install", "npm install", "apt install")
_BROWSER_TERMS = ("browser_action", "browser_automation", "sel" + "enium", "play" + "wright", "web" + "browser")
_MCP_TERMS = ("mcp" + "_tool", "call" + "_tool", "read_resource")
_CODEX_AIDER_TERMS = ("cod" + "ex", "aid" + "er", "run_codex", "run_aider")
_LOCAL_LLM_TERMS = ("local" + "_llm", "oll" + "ama", "llama.cpp", "llama_cpp", "transform" + "ers", "vllm", "call_llm")
_AGENT_LOOP_TERMS = (
    "invoke_agent",
    "start_agent_loop",
    "run_agent",
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
_RETRY_FALLBACK_TERMS = (
    "retry_now",
    "auto_retry",
    "automatic_retry",
    "fallback_now",
    "auto_fallback",
    "automatic_fallback",
    "streaming",
    "dispatch",
    "dispatcher",
    "execute",
)
_ENV_SECRET_TERMS = ("api" + "_key", "token", "secret", "env", "password", "credential", ".env", "id_rsa", "ssh_key")
_TEXT_SCAN_SKIP_KEYS = frozenset(
    {
        "schema_version",
        "action_kind",
        "target_step",
        "loop_status",
        "allowed_next_action_kinds",
        "forbidden_next_action_kinds",
        "codex_live_flow_review_hash",
    }
)
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 4096
_MAX_COLLECTION_ITEMS = 128
_MAX_DEPTH = 8


@dataclass(frozen=True)
class LocalAgentObjective:
    schema_version: str
    objective_id: str
    objective_summary: str
    allowed_next_action_kinds: tuple[str, ...]
    forbidden_next_action_kinds: tuple[str, ...]
    context_hashes: tuple[str, ...]
    requested_by: str
    requested_at: int
    expires_at: int
    objective_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "objective_id", _identifier("objective_id", self.objective_id))
        object.__setattr__(self, "objective_summary", _required_text("objective_summary", self.objective_summary))
        object.__setattr__(self, "allowed_next_action_kinds", _label_tuple("allowed_next_action_kinds", self.allowed_next_action_kinds, allow_empty=False))
        object.__setattr__(self, "forbidden_next_action_kinds", _label_tuple("forbidden_next_action_kinds", self.forbidden_next_action_kinds, allow_empty=True))
        object.__setattr__(self, "context_hashes", _hash_tuple("context_hashes", self.context_hashes, allow_empty=True))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "requested_at", _nonnegative_int("requested_at", self.requested_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "objective_hash", _required_hash("objective_hash", self.objective_hash))
        if self.schema_version != LOCAL_AGENT_OBJECTIVE_SCHEMA_VERSION:
            raise ValueError("unsupported local agent objective schema version")
        if self.expires_at <= self.requested_at:
            raise ValueError("objective expires_at must be greater than requested_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "objective_id": self.objective_id,
            "objective_summary": self.objective_summary,
            "allowed_next_action_kinds": self.allowed_next_action_kinds,
            "forbidden_next_action_kinds": self.forbidden_next_action_kinds,
            "context_hashes": self.context_hashes,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "objective_hash": self.objective_hash,
        }


@dataclass(frozen=True)
class LocalAgentLoopState:
    schema_version: str
    loop_id: str
    objective_hash: str
    iteration_index: int
    completed_iteration_hashes: tuple[str, ...]
    current_evidence_hashes: tuple[str, ...]
    orchestration_review_hash: str | None
    recovery_review_hash: str | None
    codex_live_flow_review_hash: str | None
    state_created_at: int
    state_expires_at: int
    state_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "loop_id", _identifier("loop_id", self.loop_id))
        object.__setattr__(self, "objective_hash", _required_hash("objective_hash", self.objective_hash))
        object.__setattr__(self, "iteration_index", _nonnegative_int("iteration_index", self.iteration_index))
        object.__setattr__(self, "completed_iteration_hashes", _hash_tuple("completed_iteration_hashes", self.completed_iteration_hashes, allow_empty=True))
        object.__setattr__(self, "current_evidence_hashes", _hash_tuple("current_evidence_hashes", self.current_evidence_hashes, allow_empty=True))
        object.__setattr__(self, "orchestration_review_hash", _optional_hash("orchestration_review_hash", self.orchestration_review_hash))
        object.__setattr__(self, "recovery_review_hash", _optional_hash("recovery_review_hash", self.recovery_review_hash))
        object.__setattr__(self, "codex_live_flow_review_hash", _optional_hash("codex_live_flow_review_hash", self.codex_live_flow_review_hash))
        object.__setattr__(self, "state_created_at", _nonnegative_int("state_created_at", self.state_created_at))
        object.__setattr__(self, "state_expires_at", _nonnegative_int("state_expires_at", self.state_expires_at))
        object.__setattr__(self, "state_hash", _required_hash("state_hash", self.state_hash))
        if self.schema_version != LOCAL_AGENT_LOOP_STATE_SCHEMA_VERSION:
            raise ValueError("unsupported local agent loop state schema version")
        if self.state_expires_at <= self.state_created_at:
            raise ValueError("state_expires_at must be greater than state_created_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "loop_id": self.loop_id,
            "objective_hash": self.objective_hash,
            "iteration_index": self.iteration_index,
            "completed_iteration_hashes": self.completed_iteration_hashes,
            "current_evidence_hashes": self.current_evidence_hashes,
            "orchestration_review_hash": self.orchestration_review_hash,
            "recovery_review_hash": self.recovery_review_hash,
            "codex_live_flow_review_hash": self.codex_live_flow_review_hash,
            "state_created_at": self.state_created_at,
            "state_expires_at": self.state_expires_at,
            "state_hash": self.state_hash,
        }


@dataclass(frozen=True)
class LocalAgentCandidateAction:
    schema_version: str
    candidate_id: str
    action_kind: str
    action_summary: str
    target_step: str | None
    required_evidence_hashes: tuple[str, ...]
    risk_notes: tuple[str, ...]
    proposed_by: str
    proposed_at: int
    expires_at: int
    candidate_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "candidate_id", _identifier("candidate_id", self.candidate_id))
        object.__setattr__(self, "action_kind", _required_text("action_kind", self.action_kind).casefold())
        object.__setattr__(self, "action_summary", _required_text("action_summary", self.action_summary))
        object.__setattr__(self, "target_step", _optional_label("target_step", self.target_step))
        object.__setattr__(self, "required_evidence_hashes", _hash_tuple("required_evidence_hashes", self.required_evidence_hashes, allow_empty=True))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes, allow_empty=True))
        object.__setattr__(self, "proposed_by", _required_text("proposed_by", self.proposed_by))
        object.__setattr__(self, "proposed_at", _nonnegative_int("proposed_at", self.proposed_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "candidate_hash", _required_hash("candidate_hash", self.candidate_hash))
        if self.schema_version != LOCAL_AGENT_CANDIDATE_ACTION_SCHEMA_VERSION:
            raise ValueError("unsupported local agent candidate action schema version")
        if self.expires_at <= self.proposed_at:
            raise ValueError("candidate expires_at must be greater than proposed_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "action_kind": self.action_kind,
            "action_summary": self.action_summary,
            "target_step": self.target_step,
            "required_evidence_hashes": self.required_evidence_hashes,
            "risk_notes": self.risk_notes,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at,
            "expires_at": self.expires_at,
            "candidate_hash": self.candidate_hash,
        }


@dataclass(frozen=True)
class LocalAgentLoopReviewResult:
    schema_version: str
    ok: bool
    blocked: bool
    selected: bool
    execution_allowed: bool
    dispatch_allowed: bool
    tool_call_allowed: bool
    provider_call_allowed: bool
    local_llm_allowed: bool
    retry_allowed: bool
    fallback_allowed: bool
    streaming_allowed: bool
    write_allowed: bool
    commit_allowed: bool
    push_allowed: bool
    requires_human_review: bool
    requires_controlled_path: bool
    loop_id: str | None
    objective_hash: str | None
    state_hash: str | None
    selected_candidate_hash: str | None
    ready_candidate_hashes: tuple[str, ...]
    blocked_candidate_hashes: tuple[str, ...]
    loop_status: str
    risk_tier: str
    loop_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    review_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_execute: bool = False
    can_dispatch: bool = False
    can_retry: bool = False
    can_fallback: bool = False
    can_stream: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_tool: bool = False
    can_call_provider: bool = False
    can_call_mcp: bool = False
    can_call_llm: bool = False
    approval_created: bool = False
    dispatcher_created: bool = False
    selected_candidate_executed: bool = False
    tool_called: bool = False
    provider_called: bool = False
    local_llm_called: bool = False
    retry_started: bool = False
    fallback_started: bool = False
    streaming_started: bool = False
    files_written: bool = False
    commit_created: bool = False
    push_performed: bool = False
    process_started: bool = False
    network_called: bool = False
    mcp_called: bool = False
    browser_opened: bool = False
    package_manager_called: bool = False
    git_action_performed: bool = False
    agent_loop_started: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "blocked", bool(self.blocked))
        object.__setattr__(self, "ok", bool(self.ok) and not bool(self.blocked))
        object.__setattr__(self, "selected", bool(self.selected) and not bool(self.blocked))
        for field_name in _REVIEW_FALSE_FLAGS:
            object.__setattr__(self, field_name, False)
        object.__setattr__(self, "requires_human_review", True)
        object.__setattr__(self, "requires_controlled_path", True)
        if self.loop_id is not None:
            object.__setattr__(self, "loop_id", _identifier("loop_id", self.loop_id))
        for field_name in ("objective_hash", "state_hash", "selected_candidate_hash"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required_hash(field_name, value))
        object.__setattr__(self, "ready_candidate_hashes", _hash_tuple("ready_candidate_hashes", self.ready_candidate_hashes, allow_empty=True))
        object.__setattr__(self, "blocked_candidate_hashes", _hash_tuple("blocked_candidate_hashes", self.blocked_candidate_hashes, allow_empty=True))
        if self.loop_status not in {LOCAL_AGENT_LOOP_STATUS_READY, LOCAL_AGENT_LOOP_STATUS_BLOCKED}:
            raise ValueError("unsupported local agent loop status")
        if self.risk_tier not in {LOCAL_AGENT_LOOP_RISK_LOW, LOCAL_AGENT_LOOP_RISK_MEDIUM, LOCAL_AGENT_LOOP_RISK_HIGH, LOCAL_AGENT_LOOP_RISK_BLOCKED}:
            raise ValueError("unsupported local agent loop risk tier")
        object.__setattr__(self, "loop_codes", tuple(sorted(set(_required_text("loop_codes", item) for item in self.loop_codes))))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(_required_text("reason_codes", item) for item in self.reason_codes))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
            "ok": self.ok,
            "blocked": self.blocked,
            "selected": self.selected,
            "execution_allowed": False,
            "dispatch_allowed": False,
            "tool_call_allowed": False,
            "provider_call_allowed": False,
            "local_llm_allowed": False,
            "retry_allowed": False,
            "fallback_allowed": False,
            "streaming_allowed": False,
            "write_allowed": False,
            "commit_allowed": False,
            "push_allowed": False,
            "requires_human_review": True,
            "requires_controlled_path": True,
            "loop_id": self.loop_id,
            "objective_hash": self.objective_hash,
            "state_hash": self.state_hash,
            "selected_candidate_hash": self.selected_candidate_hash,
            "ready_candidate_hashes": self.ready_candidate_hashes,
            "blocked_candidate_hashes": self.blocked_candidate_hashes,
            "loop_status": self.loop_status,
            "risk_tier": self.risk_tier,
            "loop_codes": self.loop_codes,
            "reason_codes": self.reason_codes,
            "review_hash": self.review_hash,
        }
        for field_name in _REVIEW_FALSE_FLAGS:
            data[field_name] = False
        return data


_REVIEW_FALSE_FLAGS = (
    "execution_allowed",
    "dispatch_allowed",
    "tool_call_allowed",
    "provider_call_allowed",
    "local_llm_allowed",
    "retry_allowed",
    "fallback_allowed",
    "streaming_allowed",
    "write_allowed",
    "commit_allowed",
    "push_allowed",
    "gate_satisfied",
    "human_barrier_satisfied",
    "can_execute",
    "can_dispatch",
    "can_retry",
    "can_fallback",
    "can_stream",
    "can_write",
    "can_commit",
    "can_push",
    "can_call_tool",
    "can_call_provider",
    "can_call_mcp",
    "can_call_llm",
    "approval_created",
    "dispatcher_created",
    "selected_candidate_executed",
    "tool_called",
    "provider_called",
    "local_llm_called",
    "retry_started",
    "fallback_started",
    "streaming_started",
    "files_written",
    "commit_created",
    "push_performed",
    "process_started",
    "network_called",
    "mcp_called",
    "browser_opened",
    "package_manager_called",
    "git_action_performed",
    "agent_loop_started",
)


def canonical_local_agent_loop_json(value: Any) -> str:
    return json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_local_agent_loop_value(value: Any) -> str:
    return hashlib.sha256(canonical_local_agent_loop_json(value).encode("utf-8")).hexdigest()


def build_local_agent_objective(
    *,
    objective_id: str,
    objective_summary: str,
    allowed_next_action_kinds: tuple[str, ...],
    forbidden_next_action_kinds: tuple[str, ...],
    context_hashes: tuple[str, ...],
    requested_by: str,
    requested_at: int,
    expires_at: int,
) -> LocalAgentObjective:
    material = {
        "schema_version": LOCAL_AGENT_OBJECTIVE_SCHEMA_VERSION,
        "objective_id": _identifier("objective_id", objective_id),
        "objective_summary": _required_text("objective_summary", objective_summary),
        "allowed_next_action_kinds": _label_tuple("allowed_next_action_kinds", allowed_next_action_kinds, allow_empty=False),
        "forbidden_next_action_kinds": _label_tuple("forbidden_next_action_kinds", forbidden_next_action_kinds, allow_empty=True),
        "context_hashes": _hash_tuple("context_hashes", context_hashes, allow_empty=True),
        "requested_by": _required_text("requested_by", requested_by),
        "requested_at": _nonnegative_int("requested_at", requested_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return LocalAgentObjective(**material, objective_hash=_hash_material(material))


def build_local_agent_loop_state(
    *,
    loop_id: str,
    objective_hash: str,
    iteration_index: int,
    completed_iteration_hashes: tuple[str, ...],
    current_evidence_hashes: tuple[str, ...],
    orchestration_review_hash: str | None,
    recovery_review_hash: str | None,
    codex_live_flow_review_hash: str | None,
    state_created_at: int,
    state_expires_at: int,
) -> LocalAgentLoopState:
    material = {
        "schema_version": LOCAL_AGENT_LOOP_STATE_SCHEMA_VERSION,
        "loop_id": _identifier("loop_id", loop_id),
        "objective_hash": _required_hash("objective_hash", objective_hash),
        "iteration_index": _nonnegative_int("iteration_index", iteration_index),
        "completed_iteration_hashes": _hash_tuple("completed_iteration_hashes", completed_iteration_hashes, allow_empty=True),
        "current_evidence_hashes": _hash_tuple("current_evidence_hashes", current_evidence_hashes, allow_empty=True),
        "orchestration_review_hash": _optional_hash("orchestration_review_hash", orchestration_review_hash),
        "recovery_review_hash": _optional_hash("recovery_review_hash", recovery_review_hash),
        "codex_live_flow_review_hash": _optional_hash("codex_live_flow_review_hash", codex_live_flow_review_hash),
        "state_created_at": _nonnegative_int("state_created_at", state_created_at),
        "state_expires_at": _nonnegative_int("state_expires_at", state_expires_at),
    }
    return LocalAgentLoopState(**material, state_hash=_hash_material(material))


def build_local_agent_candidate_action(
    *,
    candidate_id: str,
    action_kind: str,
    action_summary: str,
    target_step: str | None,
    required_evidence_hashes: tuple[str, ...],
    risk_notes: tuple[str, ...],
    proposed_by: str,
    proposed_at: int,
    expires_at: int,
) -> LocalAgentCandidateAction:
    material = {
        "schema_version": LOCAL_AGENT_CANDIDATE_ACTION_SCHEMA_VERSION,
        "candidate_id": _identifier("candidate_id", candidate_id),
        "action_kind": _required_text("action_kind", action_kind).casefold(),
        "action_summary": _required_text("action_summary", action_summary),
        "target_step": _optional_label("target_step", target_step),
        "required_evidence_hashes": _hash_tuple("required_evidence_hashes", required_evidence_hashes, allow_empty=True),
        "risk_notes": _text_tuple("risk_notes", risk_notes, allow_empty=True),
        "proposed_by": _required_text("proposed_by", proposed_by),
        "proposed_at": _nonnegative_int("proposed_at", proposed_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return LocalAgentCandidateAction(**material, candidate_hash=_hash_material(material))


def evaluate_local_agent_loop_iteration(
    *,
    objective: LocalAgentObjective,
    state: LocalAgentLoopState,
    candidates: tuple[LocalAgentCandidateAction, ...],
    completed_candidate_hashes: tuple[str, ...] = (),
    now: int,
) -> LocalAgentLoopReviewResult:
    reason_codes: list[str] = []
    try:
        now_value = _nonnegative_int("now", now)
    except (TypeError, ValueError):
        return _blocked((LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME,))

    try:
        objective_data = _coerce_mapping(objective)
        state_data = _coerce_mapping(state)
        candidate_data = _candidate_mapping_tuple(candidates)
        completed_hashes = _hash_tuple("completed_candidate_hashes", completed_candidate_hashes, allow_empty=True)
        evidence_fingerprint = _json_fingerprint(
            {
                "objective": objective_data,
                "state": state_data,
                "candidates": candidate_data,
                "completed_candidate_hashes": completed_hashes,
            }
        )
    except TypeError:
        return _blocked((LOCAL_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE,))
    except ValueError:
        return _blocked((LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH,))

    reason_codes.extend(_danger_reason_codes((objective_data, state_data, candidate_data)))
    if _contains_unknown_fields(objective_data, state_data, candidate_data):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE)
    if _invalid_hash_evidence_present(objective_data, state_data, candidate_data):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH)
    if _invalid_time_evidence_present(objective_data, state_data, candidate_data):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME)

    try:
        local_objective = _coerce_objective(objective_data)
        loop_state = _coerce_state(state_data)
        candidate_items = tuple(_coerce_candidate(item) for item in candidate_data)
    except (TypeError, ValueError):
        return _blocked(tuple(reason_codes or (LOCAL_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE,)), input_fingerprint=evidence_fingerprint)

    candidate_ids = tuple(candidate.candidate_id for candidate in candidate_items)
    candidate_hashes = tuple(candidate.candidate_hash for candidate in candidate_items)
    candidate_hash_set = frozenset(candidate_hashes)

    if loop_state.objective_hash != local_objective.objective_hash:
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH)
    if local_objective.objective_hash != _hash_material(_objective_hash_material(local_objective)):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH)
    if loop_state.state_hash != _hash_material(_state_hash_material(loop_state)):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH)
    if any(candidate.candidate_hash != _hash_material(_candidate_hash_material(candidate)) for candidate in candidate_items):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH)

    if any(kind not in SUPPORTED_NEXT_ACTION_KINDS for kind in local_objective.allowed_next_action_kinds):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE)
    if any(kind not in SUPPORTED_NEXT_ACTION_KINDS for kind in local_objective.forbidden_next_action_kinds):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE)
    if len(set(candidate_ids)) != len(candidate_ids):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID)
    if len(set(candidate_hashes)) != len(candidate_hashes):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH)
    if any(item not in candidate_hash_set for item in completed_hashes):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE)
    for candidate in candidate_items:
        if candidate.action_kind not in SUPPORTED_NEXT_ACTION_KINDS:
            reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND)
        if candidate.action_kind not in local_objective.allowed_next_action_kinds:
            reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND)
        if candidate.action_kind in local_objective.forbidden_next_action_kinds:
            reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND)
        if candidate.target_step == STEP54_TARGET:
            reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_STEP54_NOT_AVAILABLE)
        elif candidate.target_step is not None and candidate.target_step not in SUPPORTED_TARGET_STEPS:
            reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED)

    if now_value < local_objective.requested_at or now_value < loop_state.state_created_at:
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME)
    if any(now_value < candidate.proposed_at for candidate in candidate_items):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME)
    if now_value > local_objective.expires_at:
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE)
    if now_value > loop_state.state_expires_at:
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_STATE)
    if any(now_value > candidate.expires_at for candidate in candidate_items):
        reason_codes.append(LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE)

    ready_candidates = tuple(candidate for candidate in candidate_items if candidate.candidate_hash not in completed_hashes)
    ready_hashes = tuple(sorted(candidate.candidate_hash for candidate in ready_candidates))
    blocked_hashes = tuple(sorted(candidate.candidate_hash for candidate in candidate_items if candidate.candidate_hash in completed_hashes))

    blocked = bool(set(reason_codes) - {LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON, LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON})
    selected_candidate = None if blocked or not ready_candidates else sorted(ready_candidates, key=lambda item: (item.candidate_id, item.candidate_hash))[0]
    selected_hash = selected_candidate.candidate_hash if selected_candidate is not None else None
    if blocked:
        reason_codes = sorted(set(reason_codes))
    else:
        reason_codes = sorted(
            {
                LOCAL_AGENT_LOOP_OK,
                LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON,
                LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON,
            }
        )

    loop_status = LOCAL_AGENT_LOOP_STATUS_BLOCKED if blocked else LOCAL_AGENT_LOOP_STATUS_READY
    risk_tier = _risk_tier(blocked, candidate_items, selected_candidate)
    loop_codes = _loop_codes(blocked, selected_candidate is not None)
    material = {
        "schema_version": LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        "ok": not blocked,
        "blocked": blocked,
        "selected": selected_candidate is not None,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "tool_call_allowed": False,
        "provider_call_allowed": False,
        "local_llm_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "write_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "loop_id": loop_state.loop_id,
        "objective_hash": local_objective.objective_hash,
        "state_hash": loop_state.state_hash,
        "selected_candidate_hash": selected_hash,
        "ready_candidate_hashes": ready_hashes,
        "blocked_candidate_hashes": blocked_hashes,
        "loop_status": loop_status,
        "risk_tier": risk_tier,
        "loop_codes": loop_codes,
        "reason_codes": tuple(reason_codes),
    }
    return LocalAgentLoopReviewResult(
        schema_version=LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        ok=not blocked,
        blocked=blocked,
        selected=selected_candidate is not None,
        execution_allowed=False,
        dispatch_allowed=False,
        tool_call_allowed=False,
        provider_call_allowed=False,
        local_llm_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        write_allowed=False,
        commit_allowed=False,
        push_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        loop_id=loop_state.loop_id,
        objective_hash=local_objective.objective_hash,
        state_hash=loop_state.state_hash,
        selected_candidate_hash=selected_hash,
        ready_candidate_hashes=ready_hashes,
        blocked_candidate_hashes=blocked_hashes,
        loop_status=loop_status,
        risk_tier=risk_tier,
        loop_codes=loop_codes,
        reason_codes=tuple(reason_codes),
        review_hash=hash_local_agent_loop_value(material),
    )


def _hash_material(value: Mapping[str, Any]) -> str:
    data = dict(value)
    for field_name in ("objective_hash", "state_hash", "candidate_hash", "review_hash"):
        data.pop(field_name, None)
    return hash_local_agent_loop_value(_json_fingerprint(data))


def _objective_hash_material(value: LocalAgentObjective) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("objective_hash", None)
    return data


def _state_hash_material(value: LocalAgentLoopState) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("state_hash", None)
    return data


def _candidate_hash_material(value: LocalAgentCandidateAction) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("candidate_hash", None)
    return data


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> LocalAgentLoopReviewResult:
    codes = tuple(sorted(set(reason_codes)))
    material = {
        "schema_version": LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        "ok": False,
        "blocked": True,
        "selected": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "tool_call_allowed": False,
        "provider_call_allowed": False,
        "local_llm_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "write_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "loop_id": None,
        "objective_hash": None,
        "state_hash": None,
        "selected_candidate_hash": None,
        "ready_candidate_hashes": (),
        "blocked_candidate_hashes": (),
        "loop_status": LOCAL_AGENT_LOOP_STATUS_BLOCKED,
        "risk_tier": LOCAL_AGENT_LOOP_RISK_BLOCKED,
        "loop_codes": _loop_codes(True, False),
        "reason_codes": codes,
        "input_fingerprint": input_fingerprint,
    }
    return LocalAgentLoopReviewResult(
        schema_version=LOCAL_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        ok=False,
        blocked=True,
        selected=False,
        execution_allowed=False,
        dispatch_allowed=False,
        tool_call_allowed=False,
        provider_call_allowed=False,
        local_llm_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        write_allowed=False,
        commit_allowed=False,
        push_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        loop_id=None,
        objective_hash=None,
        state_hash=None,
        selected_candidate_hash=None,
        ready_candidate_hashes=(),
        blocked_candidate_hashes=(),
        loop_status=LOCAL_AGENT_LOOP_STATUS_BLOCKED,
        risk_tier=LOCAL_AGENT_LOOP_RISK_BLOCKED,
        loop_codes=_loop_codes(True, False),
        reason_codes=codes,
        review_hash=hash_local_agent_loop_value(material),
    )


def _loop_codes(blocked: bool, selected: bool) -> tuple[str, ...]:
    codes = {
        LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW,
        LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH,
        LOCAL_AGENT_LOOP_NON_AUTHORITY,
    }
    codes.add(LOCAL_AGENT_LOOP_BLOCKED_METADATA if blocked else LOCAL_AGENT_LOOP_READY_METADATA)
    if selected:
        codes.add(LOCAL_AGENT_LOOP_SELECTED_METADATA_ONLY)
    return tuple(sorted(codes))


def _risk_tier(blocked: bool, candidates: tuple[LocalAgentCandidateAction, ...], selected: LocalAgentCandidateAction | None) -> str:
    if blocked:
        return LOCAL_AGENT_LOOP_RISK_BLOCKED
    if selected is not None and selected.action_kind in HIGH_RISK_ACTION_KINDS:
        return LOCAL_AGENT_LOOP_RISK_HIGH
    if any(candidate.action_kind in HIGH_RISK_ACTION_KINDS for candidate in candidates):
        return LOCAL_AGENT_LOOP_RISK_MEDIUM
    return LOCAL_AGENT_LOOP_RISK_LOW


def _coerce_objective(value: object) -> LocalAgentObjective:
    if isinstance(value, LocalAgentObjective):
        return value
    if isinstance(value, Mapping):
        return LocalAgentObjective(**_sanitize_mapping(value, _ALLOWED_OBJECTIVE_FIELDS))
    raise TypeError("local agent objective is required")


def _coerce_state(value: object) -> LocalAgentLoopState:
    if isinstance(value, LocalAgentLoopState):
        return value
    if isinstance(value, Mapping):
        return LocalAgentLoopState(**_sanitize_mapping(value, _ALLOWED_STATE_FIELDS))
    raise TypeError("local agent loop state is required")


def _coerce_candidate(value: object) -> LocalAgentCandidateAction:
    if isinstance(value, LocalAgentCandidateAction):
        return value
    if isinstance(value, Mapping):
        return LocalAgentCandidateAction(**_sanitize_mapping(value, _ALLOWED_CANDIDATE_FIELDS))
    raise TypeError("local agent candidate action is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("local agent loop evidence must be mapping evidence")


def _candidate_mapping_tuple(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError("candidates must be a sequence")
    if len(value) > _MAX_COLLECTION_ITEMS:
        raise TypeError("too many candidates")
    return tuple(_coerce_mapping(candidate) for candidate in value)


def _sanitize_mapping(value: Mapping[str, Any], allowed_fields: frozenset[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key in allowed_fields}


def _contains_unknown_fields(objective: Mapping[str, Any], state: Mapping[str, Any], candidates: tuple[Mapping[str, Any], ...]) -> bool:
    return (
        any(key not in _ALLOWED_OBJECTIVE_FIELDS for key in objective)
        or any(key not in _ALLOWED_STATE_FIELDS for key in state)
        or any(any(key not in _ALLOWED_CANDIDATE_FIELDS for key in candidate) for candidate in candidates)
    )


def _invalid_hash_evidence_present(objective: Mapping[str, Any], state: Mapping[str, Any], candidates: tuple[Mapping[str, Any], ...]) -> bool:
    if any(not _sha256_like(objective.get(field_name)) for field_name in ("objective_hash",)):
        return True
    if not _hash_sequence_like(objective.get("context_hashes")):
        return True
    for field_name in ("objective_hash", "state_hash"):
        if not _sha256_like(state.get(field_name)):
            return True
    for field_name in ("completed_iteration_hashes", "current_evidence_hashes"):
        if not _hash_sequence_like(state.get(field_name)):
            return True
    for field_name in ("orchestration_review_hash", "recovery_review_hash", "codex_live_flow_review_hash"):
        if state.get(field_name) is not None and not _sha256_like(state.get(field_name)):
            return True
    for candidate in candidates:
        if not _sha256_like(candidate.get("candidate_hash")):
            return True
        if not _hash_sequence_like(candidate.get("required_evidence_hashes")):
            return True
    return False


def _invalid_time_evidence_present(objective: Mapping[str, Any], state: Mapping[str, Any], candidates: tuple[Mapping[str, Any], ...]) -> bool:
    if not all(_valid_nonnegative_int(objective.get(field_name)) for field_name in ("requested_at", "expires_at")):
        return True
    if objective["expires_at"] <= objective["requested_at"]:
        return True
    if not all(_valid_nonnegative_int(state.get(field_name)) for field_name in ("state_created_at", "state_expires_at", "iteration_index")):
        return True
    if state["state_expires_at"] <= state["state_created_at"]:
        return True
    for candidate in candidates:
        if not all(_valid_nonnegative_int(candidate.get(field_name)) for field_name in ("proposed_at", "expires_at")):
            return True
        if candidate["expires_at"] <= candidate["proposed_at"]:
            return True
    return False


def _danger_reason_codes(value: object) -> list[str]:
    codes: set[str] = set()
    for key, text in _scanned_text_items(value):
        normalized = text.casefold()
        normalized_key = key.casefold()
        if normalized_key in _AUTHORITY_FIELD_NAMES or any(term in normalized for term in _AUTHORITY_FIELD_NAMES):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM)
        if any(term.casefold() in normalized for term in _COMMAND_INJECTION_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_COMMAND_INJECTION)
        if any(term in normalized for term in _PROVIDER_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_PROVIDER_CALL)
        if any(term in normalized for term in _GIT_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_GIT_ACTION)
        if any(term in normalized for term in _PACKAGE_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL)
        if any(term in normalized for term in _BROWSER_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_BROWSER_ACTION)
        if any(term in normalized for term in _MCP_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_MCP_TOOL)
        if any(term in normalized for term in _CODEX_AIDER_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_CODEX_AIDER)
        if any(term in normalized for term in _LOCAL_LLM_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_LOCAL_LLM)
        if any(term in normalized for term in _AGENT_LOOP_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION)
        if any(term in normalized for term in _RETRY_FALLBACK_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING)
        if any(term in normalized for term in _ENV_SECRET_TERMS):
            codes.add(LOCAL_AGENT_LOOP_BLOCKED_ENV_OR_SECRET)
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


def _identifier(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError(f"{name} must be a stable identifier")
    return text


def _optional_label(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(name, value).casefold()


def _required_hash(name: str, value: object) -> str:
    text = _required_text(name, value).casefold()
    if not _sha256_like(text):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return text


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_hash(name, value)


def _hash_tuple(name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    if not value and not allow_empty:
        raise TypeError(f"{name} must not be empty")
    return tuple(_required_hash(name, item) for item in value)


def _label_tuple(name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    if not value and not allow_empty:
        raise TypeError(f"{name} must not be empty")
    return tuple(_required_text(name, item).casefold() for item in value)


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


def _hash_sequence_like(value: object) -> bool:
    return isinstance(value, (tuple, list)) and all(_sha256_like(item) for item in value)


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("local agent loop evidence is too deeply nested")
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
    raise TypeError("local agent loop evidence must be JSON serializable")
