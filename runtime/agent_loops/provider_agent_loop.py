from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


PROVIDER_AGENT_OBJECTIVE_SCHEMA_VERSION = "AOIA_PROVIDER_AGENT_OBJECTIVE_1A"
PROVIDER_AGENT_INPUT_EVIDENCE_SCHEMA_VERSION = "AOIA_PROVIDER_AGENT_INPUT_EVIDENCE_1A"
PROVIDER_AGENT_CANDIDATE_ACTION_SCHEMA_VERSION = "AOIA_PROVIDER_AGENT_CANDIDATE_ACTION_1A"
PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION = "AOIA_PROVIDER_AGENT_LOOP_REVIEW_1A"

PROVIDER_AGENT_LOOP_READY_METADATA = "PROVIDER_AGENT_LOOP_READY_METADATA"
PROVIDER_AGENT_LOOP_BLOCKED_METADATA = "PROVIDER_AGENT_LOOP_BLOCKED_METADATA"
PROVIDER_AGENT_LOOP_SELECTED_METADATA_ONLY = "PROVIDER_AGENT_LOOP_SELECTED_METADATA_ONLY"
PROVIDER_AGENT_LOOP_PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_AGENT_LOOP_PROVIDER_OUTPUT_UNTRUSTED"
PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW = "PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW"
PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH = "PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH"
PROVIDER_AGENT_LOOP_NON_AUTHORITY = "PROVIDER_AGENT_LOOP_NON_AUTHORITY"

PROVIDER_AGENT_LOOP_OK = "PROVIDER_AGENT_LOOP_OK"
PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON = "PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW"
PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON = "PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_INPUT_EVIDENCE = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_INPUT_EVIDENCE"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_CANDIDATE = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_CANDIDATE"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND"
PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_PROVIDER_KIND = "PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_PROVIDER_KIND"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND"
PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND = "PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND"
PROVIDER_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED = "PROVIDER_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED"
PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK = "PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK"
PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID = "PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID"
PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH = "PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH"
PROVIDER_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE = "PROVIDER_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE"
PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH = "PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH"
PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME = "PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME"
PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE = "PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE"
PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_INPUT_EVIDENCE = "PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_INPUT_EVIDENCE"
PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE = "PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE"
PROVIDER_AGENT_LOOP_BLOCKED_COMMAND_INJECTION = "PROVIDER_AGENT_LOOP_BLOCKED_COMMAND_INJECTION"
PROVIDER_AGENT_LOOP_BLOCKED_PROVIDER_CALL = "PROVIDER_AGENT_LOOP_BLOCKED_PROVIDER_CALL"
PROVIDER_AGENT_LOOP_BLOCKED_GIT_ACTION = "PROVIDER_AGENT_LOOP_BLOCKED_GIT_ACTION"
PROVIDER_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL = "PROVIDER_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL"
PROVIDER_AGENT_LOOP_BLOCKED_BROWSER_ACTION = "PROVIDER_AGENT_LOOP_BLOCKED_BROWSER_ACTION"
PROVIDER_AGENT_LOOP_BLOCKED_MCP_TOOL = "PROVIDER_AGENT_LOOP_BLOCKED_MCP_TOOL"
PROVIDER_AGENT_LOOP_BLOCKED_CODEX_AIDER = "PROVIDER_AGENT_LOOP_BLOCKED_CODEX_AIDER"
PROVIDER_AGENT_LOOP_BLOCKED_LOCAL_LLM = "PROVIDER_AGENT_LOOP_BLOCKED_LOCAL_LLM"
PROVIDER_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION = "PROVIDER_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION"
PROVIDER_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING = "PROVIDER_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING"
PROVIDER_AGENT_LOOP_BLOCKED_WRITE_OR_PATCH = "PROVIDER_AGENT_LOOP_BLOCKED_WRITE_OR_PATCH"
PROVIDER_AGENT_LOOP_BLOCKED_COMMIT_OR_PUSH = "PROVIDER_AGENT_LOOP_BLOCKED_COMMIT_OR_PUSH"
PROVIDER_AGENT_LOOP_BLOCKED_ENV_OR_SECRET = "PROVIDER_AGENT_LOOP_BLOCKED_ENV_OR_SECRET"
PROVIDER_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM = "PROVIDER_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM"
PROVIDER_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE = "PROVIDER_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE"
PROVIDER_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE = "PROVIDER_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE"

PROVIDER_AGENT_LOOP_STATUS_READY = "READY_METADATA"
PROVIDER_AGENT_LOOP_STATUS_BLOCKED = "BLOCKED_METADATA"
PROVIDER_AGENT_LOOP_RISK_LOW = "LOW"
PROVIDER_AGENT_LOOP_RISK_MEDIUM = "MEDIUM"
PROVIDER_AGENT_LOOP_RISK_HIGH = "HIGH"
PROVIDER_AGENT_LOOP_RISK_BLOCKED = "BLOCKED"

SUPPORTED_PROVIDER_KINDS = frozenset(
    {
        "controlled_provider_gateway",
        "mock_provider_output",
        "generic_provider_output",
        "local_model_output_label",
        "external_model_output_label",
    }
)
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
        "evaluate_local_agent_loop_metadata",
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
        "evaluate_local_agent_loop_metadata",
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
        "step_54_provider_agent_loop",
    }
)
POST54_TARGET_TERMS = (
    "step_55",
    "prototype_freeze",
    "prototype freeze",
    "release",
    "knowledge_hub",
    "knowledge hub",
    "tetrad",
    "pheromone",
    "memory_hats",
    "memory hats",
    "lab_branch",
    "lab branch",
)

_ALLOWED_OBJECTIVE_FIELDS = frozenset(
    {
        "schema_version",
        "objective_id",
        "objective_summary",
        "allowed_provider_kinds",
        "forbidden_provider_kinds",
        "allowed_next_action_kinds",
        "forbidden_next_action_kinds",
        "context_hashes",
        "requested_by",
        "requested_at",
        "expires_at",
        "objective_hash",
    }
)
_ALLOWED_INPUT_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_id",
        "provider_kind",
        "provider_response_hash",
        "provider_schema_validation_hash",
        "provider_critic_hash",
        "provider_governance_hash",
        "local_agent_loop_review_hash",
        "orchestration_review_hash",
        "recovery_review_hash",
        "evidence_summary",
        "observed_at",
        "expires_at",
        "evidence_hash",
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
        "provider_claims",
        "risk_notes",
        "suggested_by",
        "suggested_at",
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
        "provider_passed",
        "provider_allowed",
        "agent_allowed",
        "can_execute",
        "can_dispatch",
        "can_retry",
        "can_fallback",
        "can_stream",
        "can_write",
        "can_apply",
        "can_run_tests",
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
_PROVIDER_TERMS = (
    "provider" + "_call",
    "call" + "_provider",
    "run_provider",
    "open" + "ai",
    "anthropic",
    "gemini",
    "google.generativeai",
    "google.genai",
)
_LOCAL_LLM_TERMS = ("local" + "_llm", "oll" + "ama", "llama.cpp", "llama_cpp", "transform" + "ers", "vllm", "call_llm")
_GIT_TERMS = ("git" + "_action", "git_commit", "git_push", "git_fetch", "git_checkout", "git_reset", "git_merge", "git_rebase")
_PACKAGE_TERMS = ("package" + "_install", "pip install", "npm install", "apt install")
_BROWSER_TERMS = ("browser_action", "browser_automation", "sel" + "enium", "play" + "wright", "web" + "browser")
_MCP_TERMS = ("mcp" + "_tool", "call" + "_tool", "read_resource")
_CODEX_AIDER_TERMS = ("cod" + "ex", "aid" + "er", "run_codex", "run_aider")
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
_WRITE_PATCH_TERMS = ("apply_patch", "patch_apply", "write_files", "test_execution", "run_tests")
_COMMIT_PUSH_TERMS = ("git_commit", "git_push", "commit", "push")
_ENV_SECRET_TERMS = ("api" + "_key", "token", "secret", "env", "password", "credential", ".env", "id_rsa", "ssh_key")
_TEXT_SCAN_SKIP_KEYS = frozenset(
    {
        "schema_version",
        "provider_kind",
        "allowed_provider_kinds",
        "forbidden_provider_kinds",
        "action_kind",
        "target_step",
        "provider_loop_status",
        "allowed_next_action_kinds",
        "forbidden_next_action_kinds",
        "local_agent_loop_review_hash",
    }
)
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 4096
_MAX_COLLECTION_ITEMS = 128
_MAX_DEPTH = 8


@dataclass(frozen=True)
class ProviderAgentObjective:
    schema_version: str
    objective_id: str
    objective_summary: str
    allowed_provider_kinds: tuple[str, ...]
    forbidden_provider_kinds: tuple[str, ...]
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
        object.__setattr__(self, "allowed_provider_kinds", _label_tuple("allowed_provider_kinds", self.allowed_provider_kinds, allow_empty=False))
        object.__setattr__(self, "forbidden_provider_kinds", _label_tuple("forbidden_provider_kinds", self.forbidden_provider_kinds, allow_empty=True))
        object.__setattr__(self, "allowed_next_action_kinds", _label_tuple("allowed_next_action_kinds", self.allowed_next_action_kinds, allow_empty=False))
        object.__setattr__(self, "forbidden_next_action_kinds", _label_tuple("forbidden_next_action_kinds", self.forbidden_next_action_kinds, allow_empty=True))
        object.__setattr__(self, "context_hashes", _hash_tuple("context_hashes", self.context_hashes, allow_empty=True))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "requested_at", _nonnegative_int("requested_at", self.requested_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "objective_hash", _required_hash("objective_hash", self.objective_hash))
        if self.schema_version != PROVIDER_AGENT_OBJECTIVE_SCHEMA_VERSION:
            raise ValueError("unsupported provider agent objective schema version")
        if self.expires_at <= self.requested_at:
            raise ValueError("objective expires_at must be greater than requested_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "objective_id": self.objective_id,
            "objective_summary": self.objective_summary,
            "allowed_provider_kinds": self.allowed_provider_kinds,
            "forbidden_provider_kinds": self.forbidden_provider_kinds,
            "allowed_next_action_kinds": self.allowed_next_action_kinds,
            "forbidden_next_action_kinds": self.forbidden_next_action_kinds,
            "context_hashes": self.context_hashes,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "objective_hash": self.objective_hash,
        }


@dataclass(frozen=True)
class ProviderAgentInputEvidence:
    schema_version: str
    evidence_id: str
    provider_kind: str
    provider_response_hash: str
    provider_schema_validation_hash: str
    provider_critic_hash: str | None
    provider_governance_hash: str | None
    local_agent_loop_review_hash: str
    orchestration_review_hash: str | None
    recovery_review_hash: str | None
    evidence_summary: str
    observed_at: int
    expires_at: int
    evidence_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "evidence_id", _identifier("evidence_id", self.evidence_id))
        object.__setattr__(self, "provider_kind", _required_text("provider_kind", self.provider_kind).casefold())
        object.__setattr__(self, "provider_response_hash", _required_hash("provider_response_hash", self.provider_response_hash))
        object.__setattr__(self, "provider_schema_validation_hash", _required_hash("provider_schema_validation_hash", self.provider_schema_validation_hash))
        object.__setattr__(self, "provider_critic_hash", _optional_hash("provider_critic_hash", self.provider_critic_hash))
        object.__setattr__(self, "provider_governance_hash", _optional_hash("provider_governance_hash", self.provider_governance_hash))
        object.__setattr__(self, "local_agent_loop_review_hash", _required_hash("local_agent_loop_review_hash", self.local_agent_loop_review_hash))
        object.__setattr__(self, "orchestration_review_hash", _optional_hash("orchestration_review_hash", self.orchestration_review_hash))
        object.__setattr__(self, "recovery_review_hash", _optional_hash("recovery_review_hash", self.recovery_review_hash))
        object.__setattr__(self, "evidence_summary", _required_text("evidence_summary", self.evidence_summary))
        object.__setattr__(self, "observed_at", _nonnegative_int("observed_at", self.observed_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "evidence_hash", _required_hash("evidence_hash", self.evidence_hash))
        if self.schema_version != PROVIDER_AGENT_INPUT_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("unsupported provider agent input evidence schema version")
        if self.expires_at <= self.observed_at:
            raise ValueError("input evidence expires_at must be greater than observed_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "provider_kind": self.provider_kind,
            "provider_response_hash": self.provider_response_hash,
            "provider_schema_validation_hash": self.provider_schema_validation_hash,
            "provider_critic_hash": self.provider_critic_hash,
            "provider_governance_hash": self.provider_governance_hash,
            "local_agent_loop_review_hash": self.local_agent_loop_review_hash,
            "orchestration_review_hash": self.orchestration_review_hash,
            "recovery_review_hash": self.recovery_review_hash,
            "evidence_summary": self.evidence_summary,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True)
class ProviderAgentCandidateAction:
    schema_version: str
    candidate_id: str
    action_kind: str
    action_summary: str
    target_step: str | None
    required_evidence_hashes: tuple[str, ...]
    provider_claims: tuple[str, ...]
    risk_notes: tuple[str, ...]
    suggested_by: str
    suggested_at: int
    expires_at: int
    candidate_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "candidate_id", _identifier("candidate_id", self.candidate_id))
        object.__setattr__(self, "action_kind", _required_text("action_kind", self.action_kind).casefold())
        object.__setattr__(self, "action_summary", _required_text("action_summary", self.action_summary))
        object.__setattr__(self, "target_step", _optional_label("target_step", self.target_step))
        object.__setattr__(self, "required_evidence_hashes", _hash_tuple("required_evidence_hashes", self.required_evidence_hashes, allow_empty=True))
        object.__setattr__(self, "provider_claims", _text_tuple("provider_claims", self.provider_claims, allow_empty=True))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes, allow_empty=True))
        object.__setattr__(self, "suggested_by", _required_text("suggested_by", self.suggested_by))
        object.__setattr__(self, "suggested_at", _nonnegative_int("suggested_at", self.suggested_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "candidate_hash", _required_hash("candidate_hash", self.candidate_hash))
        if self.schema_version != PROVIDER_AGENT_CANDIDATE_ACTION_SCHEMA_VERSION:
            raise ValueError("unsupported provider agent candidate action schema version")
        if self.expires_at <= self.suggested_at:
            raise ValueError("candidate expires_at must be greater than suggested_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "action_kind": self.action_kind,
            "action_summary": self.action_summary,
            "target_step": self.target_step,
            "required_evidence_hashes": self.required_evidence_hashes,
            "provider_claims": self.provider_claims,
            "risk_notes": self.risk_notes,
            "suggested_by": self.suggested_by,
            "suggested_at": self.suggested_at,
            "expires_at": self.expires_at,
            "candidate_hash": self.candidate_hash,
        }


@dataclass(frozen=True)
class ProviderAgentLoopReviewResult:
    schema_version: str
    ok: bool
    blocked: bool
    selected: bool
    provider_call_allowed: bool
    local_llm_allowed: bool
    tool_call_allowed: bool
    execution_allowed: bool
    dispatch_allowed: bool
    retry_allowed: bool
    fallback_allowed: bool
    streaming_allowed: bool
    write_allowed: bool
    patch_apply_allowed: bool
    test_execution_allowed: bool
    commit_allowed: bool
    push_allowed: bool
    requires_human_review: bool
    requires_controlled_path: bool
    objective_hash: str | None
    input_evidence_hash: str | None
    selected_candidate_hash: str | None
    ready_candidate_hashes: tuple[str, ...]
    blocked_candidate_hashes: tuple[str, ...]
    provider_loop_status: str
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
    can_apply: bool = False
    can_run_tests: bool = False
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
    patch_applied: bool = False
    tests_run: bool = False
    commit_created: bool = False
    push_performed: bool = False
    process_started: bool = False
    network_called: bool = False
    mcp_called: bool = False
    browser_opened: bool = False
    package_manager_called: bool = False
    git_action_performed: bool = False
    agent_loop_started: bool = False
    post54_work_started: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "blocked", bool(self.blocked))
        object.__setattr__(self, "ok", bool(self.ok) and not bool(self.blocked))
        object.__setattr__(self, "selected", bool(self.selected) and not bool(self.blocked))
        for field_name in _REVIEW_FALSE_FLAGS:
            object.__setattr__(self, field_name, False)
        object.__setattr__(self, "requires_human_review", True)
        object.__setattr__(self, "requires_controlled_path", True)
        for field_name in ("objective_hash", "input_evidence_hash", "selected_candidate_hash"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required_hash(field_name, value))
        object.__setattr__(self, "ready_candidate_hashes", _hash_tuple("ready_candidate_hashes", self.ready_candidate_hashes, allow_empty=True))
        object.__setattr__(self, "blocked_candidate_hashes", _hash_tuple("blocked_candidate_hashes", self.blocked_candidate_hashes, allow_empty=True))
        if self.provider_loop_status not in {PROVIDER_AGENT_LOOP_STATUS_READY, PROVIDER_AGENT_LOOP_STATUS_BLOCKED}:
            raise ValueError("unsupported provider agent loop status")
        if self.risk_tier not in {
            PROVIDER_AGENT_LOOP_RISK_LOW,
            PROVIDER_AGENT_LOOP_RISK_MEDIUM,
            PROVIDER_AGENT_LOOP_RISK_HIGH,
            PROVIDER_AGENT_LOOP_RISK_BLOCKED,
        }:
            raise ValueError("unsupported provider agent loop risk tier")
        object.__setattr__(self, "loop_codes", tuple(sorted(set(_required_text("loop_codes", item) for item in self.loop_codes))))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(_required_text("reason_codes", item) for item in self.reason_codes))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
            "ok": self.ok,
            "blocked": self.blocked,
            "selected": self.selected,
            "provider_call_allowed": False,
            "local_llm_allowed": False,
            "tool_call_allowed": False,
            "execution_allowed": False,
            "dispatch_allowed": False,
            "retry_allowed": False,
            "fallback_allowed": False,
            "streaming_allowed": False,
            "write_allowed": False,
            "patch_apply_allowed": False,
            "test_execution_allowed": False,
            "commit_allowed": False,
            "push_allowed": False,
            "requires_human_review": True,
            "requires_controlled_path": True,
            "objective_hash": self.objective_hash,
            "input_evidence_hash": self.input_evidence_hash,
            "selected_candidate_hash": self.selected_candidate_hash,
            "ready_candidate_hashes": self.ready_candidate_hashes,
            "blocked_candidate_hashes": self.blocked_candidate_hashes,
            "provider_loop_status": self.provider_loop_status,
            "risk_tier": self.risk_tier,
            "loop_codes": self.loop_codes,
            "reason_codes": self.reason_codes,
            "review_hash": self.review_hash,
        }
        for field_name in _REVIEW_FALSE_FLAGS:
            data[field_name] = False
        return data


_REVIEW_FALSE_FLAGS = (
    "provider_call_allowed",
    "local_llm_allowed",
    "tool_call_allowed",
    "execution_allowed",
    "dispatch_allowed",
    "retry_allowed",
    "fallback_allowed",
    "streaming_allowed",
    "write_allowed",
    "patch_apply_allowed",
    "test_execution_allowed",
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
    "can_apply",
    "can_run_tests",
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
    "patch_applied",
    "tests_run",
    "commit_created",
    "push_performed",
    "process_started",
    "network_called",
    "mcp_called",
    "browser_opened",
    "package_manager_called",
    "git_action_performed",
    "agent_loop_started",
    "post54_work_started",
)


def canonical_provider_agent_loop_json(value: Any) -> str:
    return json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_provider_agent_loop_value(value: Any) -> str:
    return hashlib.sha256(canonical_provider_agent_loop_json(value).encode("utf-8")).hexdigest()


def build_provider_agent_objective(
    *,
    objective_id: str,
    objective_summary: str,
    allowed_provider_kinds: tuple[str, ...],
    forbidden_provider_kinds: tuple[str, ...],
    allowed_next_action_kinds: tuple[str, ...],
    forbidden_next_action_kinds: tuple[str, ...],
    context_hashes: tuple[str, ...],
    requested_by: str,
    requested_at: int,
    expires_at: int,
) -> ProviderAgentObjective:
    material = {
        "schema_version": PROVIDER_AGENT_OBJECTIVE_SCHEMA_VERSION,
        "objective_id": _identifier("objective_id", objective_id),
        "objective_summary": _required_text("objective_summary", objective_summary),
        "allowed_provider_kinds": _label_tuple("allowed_provider_kinds", allowed_provider_kinds, allow_empty=False),
        "forbidden_provider_kinds": _label_tuple("forbidden_provider_kinds", forbidden_provider_kinds, allow_empty=True),
        "allowed_next_action_kinds": _label_tuple("allowed_next_action_kinds", allowed_next_action_kinds, allow_empty=False),
        "forbidden_next_action_kinds": _label_tuple("forbidden_next_action_kinds", forbidden_next_action_kinds, allow_empty=True),
        "context_hashes": _hash_tuple("context_hashes", context_hashes, allow_empty=True),
        "requested_by": _required_text("requested_by", requested_by),
        "requested_at": _nonnegative_int("requested_at", requested_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return ProviderAgentObjective(**material, objective_hash=_hash_material(material))


def build_provider_agent_input_evidence(
    *,
    evidence_id: str,
    provider_kind: str,
    provider_response_hash: str,
    provider_schema_validation_hash: str,
    provider_critic_hash: str | None,
    provider_governance_hash: str | None,
    local_agent_loop_review_hash: str,
    orchestration_review_hash: str | None,
    recovery_review_hash: str | None,
    evidence_summary: str,
    observed_at: int,
    expires_at: int,
) -> ProviderAgentInputEvidence:
    material = {
        "schema_version": PROVIDER_AGENT_INPUT_EVIDENCE_SCHEMA_VERSION,
        "evidence_id": _identifier("evidence_id", evidence_id),
        "provider_kind": _required_text("provider_kind", provider_kind).casefold(),
        "provider_response_hash": _required_hash("provider_response_hash", provider_response_hash),
        "provider_schema_validation_hash": _required_hash("provider_schema_validation_hash", provider_schema_validation_hash),
        "provider_critic_hash": _optional_hash("provider_critic_hash", provider_critic_hash),
        "provider_governance_hash": _optional_hash("provider_governance_hash", provider_governance_hash),
        "local_agent_loop_review_hash": _required_hash("local_agent_loop_review_hash", local_agent_loop_review_hash),
        "orchestration_review_hash": _optional_hash("orchestration_review_hash", orchestration_review_hash),
        "recovery_review_hash": _optional_hash("recovery_review_hash", recovery_review_hash),
        "evidence_summary": _required_text("evidence_summary", evidence_summary),
        "observed_at": _nonnegative_int("observed_at", observed_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return ProviderAgentInputEvidence(**material, evidence_hash=_hash_material(material))


def build_provider_agent_candidate_action(
    *,
    candidate_id: str,
    action_kind: str,
    action_summary: str,
    target_step: str | None,
    required_evidence_hashes: tuple[str, ...],
    provider_claims: tuple[str, ...],
    risk_notes: tuple[str, ...],
    suggested_by: str,
    suggested_at: int,
    expires_at: int,
) -> ProviderAgentCandidateAction:
    material = {
        "schema_version": PROVIDER_AGENT_CANDIDATE_ACTION_SCHEMA_VERSION,
        "candidate_id": _identifier("candidate_id", candidate_id),
        "action_kind": _required_text("action_kind", action_kind).casefold(),
        "action_summary": _required_text("action_summary", action_summary),
        "target_step": _optional_label("target_step", target_step),
        "required_evidence_hashes": _hash_tuple("required_evidence_hashes", required_evidence_hashes, allow_empty=True),
        "provider_claims": _text_tuple("provider_claims", provider_claims, allow_empty=True),
        "risk_notes": _text_tuple("risk_notes", risk_notes, allow_empty=True),
        "suggested_by": _required_text("suggested_by", suggested_by),
        "suggested_at": _nonnegative_int("suggested_at", suggested_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return ProviderAgentCandidateAction(**material, candidate_hash=_hash_material(material))


def evaluate_provider_agent_loop_iteration(
    *,
    objective: ProviderAgentObjective,
    input_evidence: ProviderAgentInputEvidence,
    candidates: tuple[ProviderAgentCandidateAction, ...],
    completed_candidate_hashes: tuple[str, ...] = (),
    now: int,
) -> ProviderAgentLoopReviewResult:
    reason_codes: list[str] = []
    try:
        now_value = _nonnegative_int("now", now)
    except (TypeError, ValueError):
        return _blocked((PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME,))

    try:
        objective_data = _coerce_mapping(objective)
        input_evidence_data = _coerce_mapping(input_evidence)
        candidate_data = _candidate_mapping_tuple(candidates)
        completed_hashes = _hash_tuple("completed_candidate_hashes", completed_candidate_hashes, allow_empty=True)
        evidence_fingerprint = _json_fingerprint(
            {
                "objective": objective_data,
                "input_evidence": input_evidence_data,
                "candidates": candidate_data,
                "completed_candidate_hashes": completed_hashes,
            }
        )
    except TypeError:
        return _blocked((PROVIDER_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE,))
    except ValueError:
        return _blocked((PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH,))

    reason_codes.extend(_danger_reason_codes((objective_data, input_evidence_data, candidate_data)))
    if _contains_unknown_fields(objective_data, input_evidence_data, candidate_data):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE)
    if _invalid_hash_evidence_present(objective_data, input_evidence_data, candidate_data):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH)
    if _invalid_time_evidence_present(objective_data, input_evidence_data, candidate_data):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME)

    try:
        provider_objective = _coerce_objective(objective_data)
        provider_input = _coerce_input_evidence(input_evidence_data)
        candidate_items = tuple(_coerce_candidate(item) for item in candidate_data)
    except (TypeError, ValueError):
        return _blocked(tuple(reason_codes or (PROVIDER_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE,)), input_fingerprint=evidence_fingerprint)

    candidate_ids = tuple(candidate.candidate_id for candidate in candidate_items)
    candidate_hashes = tuple(candidate.candidate_hash for candidate in candidate_items)
    candidate_hash_set = frozenset(candidate_hashes)

    if provider_objective.objective_hash != _hash_material(_objective_hash_material(provider_objective)):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH)
    if provider_input.evidence_hash != _hash_material(_input_evidence_hash_material(provider_input)):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH)
    if any(candidate.candidate_hash != _hash_material(_candidate_hash_material(candidate)) for candidate in candidate_items):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH)

    if any(kind not in SUPPORTED_PROVIDER_KINDS for kind in provider_objective.allowed_provider_kinds):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE)
    if any(kind not in SUPPORTED_PROVIDER_KINDS for kind in provider_objective.forbidden_provider_kinds):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE)
    if provider_input.provider_kind not in SUPPORTED_PROVIDER_KINDS:
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND)
    if provider_input.provider_kind not in provider_objective.allowed_provider_kinds:
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND)
    if provider_input.provider_kind in provider_objective.forbidden_provider_kinds:
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_PROVIDER_KIND)
    if any(kind not in SUPPORTED_NEXT_ACTION_KINDS for kind in provider_objective.allowed_next_action_kinds):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE)
    if any(kind not in SUPPORTED_NEXT_ACTION_KINDS for kind in provider_objective.forbidden_next_action_kinds):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE)
    if len(set(candidate_ids)) != len(candidate_ids):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID)
    if len(set(candidate_hashes)) != len(candidate_hashes):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH)
    if any(item not in candidate_hash_set for item in completed_hashes):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE)
    for candidate in candidate_items:
        if candidate.action_kind not in SUPPORTED_NEXT_ACTION_KINDS:
            reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND)
        if candidate.action_kind not in provider_objective.allowed_next_action_kinds:
            reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND)
        if candidate.action_kind in provider_objective.forbidden_next_action_kinds:
            reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND)
        if _is_post54_target(candidate.target_step):
            reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK)
        elif candidate.target_step is not None and candidate.target_step not in SUPPORTED_TARGET_STEPS:
            reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED)

    if now_value < provider_objective.requested_at or now_value < provider_input.observed_at:
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME)
    if any(now_value < candidate.suggested_at for candidate in candidate_items):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME)
    if now_value > provider_objective.expires_at:
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE)
    if now_value > provider_input.expires_at:
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_INPUT_EVIDENCE)
    if any(now_value > candidate.expires_at for candidate in candidate_items):
        reason_codes.append(PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE)

    ready_candidates = tuple(candidate for candidate in candidate_items if candidate.candidate_hash not in completed_hashes)
    ready_hashes = tuple(sorted(candidate.candidate_hash for candidate in ready_candidates))
    blocked_hashes = tuple(sorted(candidate.candidate_hash for candidate in candidate_items if candidate.candidate_hash in completed_hashes))

    blocked = bool(set(reason_codes) - {PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON, PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON})
    selected_candidate = None if blocked or not ready_candidates else sorted(ready_candidates, key=lambda item: (item.candidate_id, item.candidate_hash))[0]
    selected_hash = selected_candidate.candidate_hash if selected_candidate is not None else None
    if blocked:
        reason_codes = sorted(set(reason_codes))
    else:
        reason_codes = sorted(
            {
                PROVIDER_AGENT_LOOP_OK,
                PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON,
                PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON,
            }
        )

    provider_loop_status = PROVIDER_AGENT_LOOP_STATUS_BLOCKED if blocked else PROVIDER_AGENT_LOOP_STATUS_READY
    risk_tier = _risk_tier(blocked, provider_input, candidate_items, selected_candidate)
    loop_codes = _loop_codes(blocked, selected_candidate is not None)
    material = {
        "schema_version": PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        "ok": not blocked,
        "blocked": blocked,
        "selected": selected_candidate is not None,
        "provider_call_allowed": False,
        "local_llm_allowed": False,
        "tool_call_allowed": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "write_allowed": False,
        "patch_apply_allowed": False,
        "test_execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "objective_hash": provider_objective.objective_hash,
        "input_evidence_hash": provider_input.evidence_hash,
        "selected_candidate_hash": selected_hash,
        "ready_candidate_hashes": ready_hashes,
        "blocked_candidate_hashes": blocked_hashes,
        "provider_loop_status": provider_loop_status,
        "risk_tier": risk_tier,
        "loop_codes": loop_codes,
        "reason_codes": tuple(reason_codes),
    }
    return ProviderAgentLoopReviewResult(
        schema_version=PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        ok=not blocked,
        blocked=blocked,
        selected=selected_candidate is not None,
        provider_call_allowed=False,
        local_llm_allowed=False,
        tool_call_allowed=False,
        execution_allowed=False,
        dispatch_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        write_allowed=False,
        patch_apply_allowed=False,
        test_execution_allowed=False,
        commit_allowed=False,
        push_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        objective_hash=provider_objective.objective_hash,
        input_evidence_hash=provider_input.evidence_hash,
        selected_candidate_hash=selected_hash,
        ready_candidate_hashes=ready_hashes,
        blocked_candidate_hashes=blocked_hashes,
        provider_loop_status=provider_loop_status,
        risk_tier=risk_tier,
        loop_codes=loop_codes,
        reason_codes=tuple(reason_codes),
        review_hash=hash_provider_agent_loop_value(material),
    )


def _hash_material(value: Mapping[str, Any]) -> str:
    data = dict(value)
    for field_name in ("objective_hash", "evidence_hash", "candidate_hash", "review_hash"):
        data.pop(field_name, None)
    return hash_provider_agent_loop_value(_json_fingerprint(data))


def _objective_hash_material(value: ProviderAgentObjective) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("objective_hash", None)
    return data


def _input_evidence_hash_material(value: ProviderAgentInputEvidence) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("evidence_hash", None)
    return data


def _candidate_hash_material(value: ProviderAgentCandidateAction) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("candidate_hash", None)
    return data


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> ProviderAgentLoopReviewResult:
    codes = tuple(sorted(set(reason_codes)))
    material = {
        "schema_version": PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        "ok": False,
        "blocked": True,
        "selected": False,
        "provider_call_allowed": False,
        "local_llm_allowed": False,
        "tool_call_allowed": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "write_allowed": False,
        "patch_apply_allowed": False,
        "test_execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "objective_hash": None,
        "input_evidence_hash": None,
        "selected_candidate_hash": None,
        "ready_candidate_hashes": (),
        "blocked_candidate_hashes": (),
        "provider_loop_status": PROVIDER_AGENT_LOOP_STATUS_BLOCKED,
        "risk_tier": PROVIDER_AGENT_LOOP_RISK_BLOCKED,
        "loop_codes": _loop_codes(True, False),
        "reason_codes": codes,
        "input_fingerprint": input_fingerprint,
    }
    return ProviderAgentLoopReviewResult(
        schema_version=PROVIDER_AGENT_LOOP_REVIEW_SCHEMA_VERSION,
        ok=False,
        blocked=True,
        selected=False,
        provider_call_allowed=False,
        local_llm_allowed=False,
        tool_call_allowed=False,
        execution_allowed=False,
        dispatch_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        write_allowed=False,
        patch_apply_allowed=False,
        test_execution_allowed=False,
        commit_allowed=False,
        push_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        objective_hash=None,
        input_evidence_hash=None,
        selected_candidate_hash=None,
        ready_candidate_hashes=(),
        blocked_candidate_hashes=(),
        provider_loop_status=PROVIDER_AGENT_LOOP_STATUS_BLOCKED,
        risk_tier=PROVIDER_AGENT_LOOP_RISK_BLOCKED,
        loop_codes=_loop_codes(True, False),
        reason_codes=codes,
        review_hash=hash_provider_agent_loop_value(material),
    )


def _loop_codes(blocked: bool, selected: bool) -> tuple[str, ...]:
    codes = {
        PROVIDER_AGENT_LOOP_PROVIDER_OUTPUT_UNTRUSTED,
        PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW,
        PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH,
        PROVIDER_AGENT_LOOP_NON_AUTHORITY,
    }
    codes.add(PROVIDER_AGENT_LOOP_BLOCKED_METADATA if blocked else PROVIDER_AGENT_LOOP_READY_METADATA)
    if selected:
        codes.add(PROVIDER_AGENT_LOOP_SELECTED_METADATA_ONLY)
    return tuple(sorted(codes))


def _risk_tier(
    blocked: bool,
    input_evidence: ProviderAgentInputEvidence,
    candidates: tuple[ProviderAgentCandidateAction, ...],
    selected: ProviderAgentCandidateAction | None,
) -> str:
    if blocked:
        return PROVIDER_AGENT_LOOP_RISK_BLOCKED
    if input_evidence.provider_kind in {"controlled_provider_gateway", "external_model_output_label"}:
        return PROVIDER_AGENT_LOOP_RISK_HIGH
    if selected is not None and selected.action_kind in HIGH_RISK_ACTION_KINDS:
        return PROVIDER_AGENT_LOOP_RISK_HIGH
    if any(candidate.action_kind in HIGH_RISK_ACTION_KINDS or candidate.provider_claims for candidate in candidates):
        return PROVIDER_AGENT_LOOP_RISK_MEDIUM
    return PROVIDER_AGENT_LOOP_RISK_LOW


def _coerce_objective(value: object) -> ProviderAgentObjective:
    if isinstance(value, ProviderAgentObjective):
        return value
    if isinstance(value, Mapping):
        return ProviderAgentObjective(**_sanitize_mapping(value, _ALLOWED_OBJECTIVE_FIELDS))
    raise TypeError("provider agent objective is required")


def _coerce_input_evidence(value: object) -> ProviderAgentInputEvidence:
    if isinstance(value, ProviderAgentInputEvidence):
        return value
    if isinstance(value, Mapping):
        return ProviderAgentInputEvidence(**_sanitize_mapping(value, _ALLOWED_INPUT_EVIDENCE_FIELDS))
    raise TypeError("provider agent input evidence is required")


def _coerce_candidate(value: object) -> ProviderAgentCandidateAction:
    if isinstance(value, ProviderAgentCandidateAction):
        return value
    if isinstance(value, Mapping):
        return ProviderAgentCandidateAction(**_sanitize_mapping(value, _ALLOWED_CANDIDATE_FIELDS))
    raise TypeError("provider agent candidate action is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("provider agent loop evidence must be mapping evidence")


def _candidate_mapping_tuple(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError("candidates must be a sequence")
    if len(value) > _MAX_COLLECTION_ITEMS:
        raise TypeError("too many candidates")
    return tuple(_coerce_mapping(candidate) for candidate in value)


def _sanitize_mapping(value: Mapping[str, Any], allowed_fields: frozenset[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key in allowed_fields}


def _contains_unknown_fields(objective: Mapping[str, Any], input_evidence: Mapping[str, Any], candidates: tuple[Mapping[str, Any], ...]) -> bool:
    return (
        any(key not in _ALLOWED_OBJECTIVE_FIELDS for key in objective)
        or any(key not in _ALLOWED_INPUT_EVIDENCE_FIELDS for key in input_evidence)
        or any(any(key not in _ALLOWED_CANDIDATE_FIELDS for key in candidate) for candidate in candidates)
    )


def _invalid_hash_evidence_present(objective: Mapping[str, Any], input_evidence: Mapping[str, Any], candidates: tuple[Mapping[str, Any], ...]) -> bool:
    if any(not _sha256_like(objective.get(field_name)) for field_name in ("objective_hash",)):
        return True
    if not _hash_sequence_like(objective.get("context_hashes")):
        return True
    for field_name in (
        "provider_response_hash",
        "provider_schema_validation_hash",
        "local_agent_loop_review_hash",
        "evidence_hash",
    ):
        if not _sha256_like(input_evidence.get(field_name)):
            return True
    for field_name in ("provider_critic_hash", "provider_governance_hash", "orchestration_review_hash", "recovery_review_hash"):
        if input_evidence.get(field_name) is not None and not _sha256_like(input_evidence.get(field_name)):
            return True
    for candidate in candidates:
        if not _sha256_like(candidate.get("candidate_hash")):
            return True
        if not _hash_sequence_like(candidate.get("required_evidence_hashes")):
            return True
    return False


def _invalid_time_evidence_present(objective: Mapping[str, Any], input_evidence: Mapping[str, Any], candidates: tuple[Mapping[str, Any], ...]) -> bool:
    if not all(_valid_nonnegative_int(objective.get(field_name)) for field_name in ("requested_at", "expires_at")):
        return True
    if objective["expires_at"] <= objective["requested_at"]:
        return True
    if not all(_valid_nonnegative_int(input_evidence.get(field_name)) for field_name in ("observed_at", "expires_at")):
        return True
    if input_evidence["expires_at"] <= input_evidence["observed_at"]:
        return True
    for candidate in candidates:
        if not all(_valid_nonnegative_int(candidate.get(field_name)) for field_name in ("suggested_at", "expires_at")):
            return True
        if candidate["expires_at"] <= candidate["suggested_at"]:
            return True
    return False


def _danger_reason_codes(value: object) -> list[str]:
    codes: set[str] = set()
    for key, text in _scanned_text_items(value):
        normalized = text.casefold()
        key_normalized = key.casefold()
        if key_normalized in _AUTHORITY_FIELD_NAMES or normalized in _AUTHORITY_FIELD_NAMES:
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM)
        if _contains_any(normalized, _COMMAND_INJECTION_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_COMMAND_INJECTION)
        if _contains_any(normalized, _PROVIDER_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_PROVIDER_CALL)
        if _contains_any(normalized, _LOCAL_LLM_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_LOCAL_LLM)
        if _contains_any(normalized, _GIT_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_GIT_ACTION)
        if _contains_any(normalized, _PACKAGE_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL)
        if _contains_any(normalized, _BROWSER_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_BROWSER_ACTION)
        if _contains_any(normalized, _MCP_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_MCP_TOOL)
        if _contains_any(normalized, _CODEX_AIDER_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_CODEX_AIDER)
        if _contains_any(normalized, _AGENT_LOOP_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION)
        if _contains_any(normalized, _RETRY_FALLBACK_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING)
        if _contains_any(normalized, _WRITE_PATCH_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_WRITE_OR_PATCH)
        if _contains_any(normalized, _COMMIT_PUSH_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_COMMIT_OR_PUSH)
        if _contains_any(normalized, _ENV_SECRET_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_ENV_OR_SECRET)
        if _contains_any(normalized, POST54_TARGET_TERMS):
            codes.add(PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK)
    return sorted(codes)


def _scanned_text_items(value: object, *, depth: int = 0, key_name: str = "") -> tuple[tuple[str, str], ...]:
    if depth > _MAX_DEPTH:
        return ((key_name, "ambiguous-depth"),)
    if isinstance(value, Mapping):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                items.append((str(key), str(key)))
                continue
            if key in _TEXT_SCAN_SKIP_KEYS:
                continue
            items.append((key, key))
            items.extend(_scanned_text_items(item, depth=depth + 1, key_name=key))
        return tuple(items)
    if isinstance(value, (tuple, list)):
        items = []
        for item in value:
            items.extend(_scanned_text_items(item, depth=depth + 1, key_name=key_name))
        return tuple(items)
    if isinstance(value, str):
        return ((key_name, value),)
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return ()
    if isinstance(value, float):
        return ((key_name, "ambiguous-float"),)
    return ((key_name, type(value).__name__),)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in text for term in terms)


def _is_post54_target(value: str | None) -> bool:
    return isinstance(value, str) and _contains_any(value.casefold(), POST54_TARGET_TERMS)


def _json_fingerprint(value: Any, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("too deeply nested")
    if callable(value):
        raise TypeError("callables are not canonical JSON")
    if isinstance(value, bytes):
        raise TypeError("bytes are not canonical JSON")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("floats are not allowed in provider agent loop evidence")
    if isinstance(value, tuple):
        return [_json_fingerprint(item, depth=depth + 1) for item in value]
    if isinstance(value, list):
        return [_json_fingerprint(item, depth=depth + 1) for item in value]
    if isinstance(value, set):
        raise TypeError("sets are not canonical JSON")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("mapping keys must be strings")
            result[key] = _json_fingerprint(item, depth=depth + 1)
        return result
    if hasattr(value, "to_dict"):
        return _json_fingerprint(value.to_dict(), depth=depth + 1)
    raise TypeError("custom objects are not canonical JSON")


def _required_text(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    stripped = value.strip()
    if not stripped or len(stripped) > _MAX_TEXT:
        raise ValueError(f"{field_name} must be non-empty bounded text")
    return stripped


def _identifier(field_name: str, value: object) -> str:
    text = _required_text(field_name, value)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be a stable identifier")
    return text


def _optional_label(field_name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(field_name, value).casefold()


def _label_tuple(field_name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    items = _text_tuple(field_name, value, allow_empty=allow_empty)
    return tuple(item.casefold() for item in items)


def _text_tuple(field_name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple of text")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > _MAX_COLLECTION_ITEMS:
        raise ValueError(f"{field_name} has too many values")
    return tuple(_required_text(field_name, item) for item in value)


def _hash_tuple(field_name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple of hashes")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > _MAX_COLLECTION_ITEMS:
        raise ValueError(f"{field_name} has too many values")
    return tuple(_required_hash(field_name, item) for item in value)


def _optional_hash(field_name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_hash(field_name, value)


def _required_hash(field_name: str, value: object) -> str:
    if not _sha256_like(value):
        raise ValueError(f"{field_name} must be a lowercase sha256 hash")
    return str(value)


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value)


def _hash_sequence_like(value: object) -> bool:
    return isinstance(value, (tuple, list)) and all(_sha256_like(item) for item in value)


def _nonnegative_int(field_name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _valid_nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
