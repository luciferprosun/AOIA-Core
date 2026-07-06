from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


FEEDBACK_OBSERVATION_SCHEMA_VERSION = "AOIA_FEEDBACK_OBSERVATION_1A"
RECOVERY_FAILURE_REPORT_SCHEMA_VERSION = "AOIA_RECOVERY_FAILURE_REPORT_1A"
RECOVERY_OPTION_SCHEMA_VERSION = "AOIA_RECOVERY_OPTION_1A"
RECOVERY_PLAN_SCHEMA_VERSION = "AOIA_RECOVERY_PLAN_1A"
RECOVERY_REVIEW_SCHEMA_VERSION = "AOIA_RECOVERY_REVIEW_1A"

FEEDBACK_RECOVERY_OBSERVED_OK = "FEEDBACK_RECOVERY_OBSERVED_OK"
FEEDBACK_RECOVERY_OBSERVED_BLOCKED = "FEEDBACK_RECOVERY_OBSERVED_BLOCKED"
FEEDBACK_RECOVERY_OBSERVED_FAILED = "FEEDBACK_RECOVERY_OBSERVED_FAILED"
FEEDBACK_RECOVERY_OPTION_MANUAL_REVIEW = "FEEDBACK_RECOVERY_OPTION_MANUAL_REVIEW"
FEEDBACK_RECOVERY_OPTION_NEW_EVIDENCE = "FEEDBACK_RECOVERY_OPTION_NEW_EVIDENCE"
FEEDBACK_RECOVERY_OPTION_REBUILD_PREVIEW = "FEEDBACK_RECOVERY_OPTION_REBUILD_PREVIEW"
FEEDBACK_RECOVERY_OPTION_RERUN_VALIDATION = "FEEDBACK_RECOVERY_OPTION_RERUN_VALIDATION"
FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW = "FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW"
FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH = "FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH"
FEEDBACK_RECOVERY_NON_AUTHORITY = "FEEDBACK_RECOVERY_NON_AUTHORITY"

FEEDBACK_RECOVERY_OK = "FEEDBACK_RECOVERY_OK"
FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW_REASON = "FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW"
FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH_REASON = "FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH"
FEEDBACK_RECOVERY_BLOCKED_INVALID_SOURCE_STEP = "FEEDBACK_RECOVERY_BLOCKED_INVALID_SOURCE_STEP"
FEEDBACK_RECOVERY_BLOCKED_INVALID_OBSERVED_STATUS = "FEEDBACK_RECOVERY_BLOCKED_INVALID_OBSERVED_STATUS"
FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH = "FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH"
FEEDBACK_RECOVERY_BLOCKED_INVALID_FAILURE_KIND = "FEEDBACK_RECOVERY_BLOCKED_INVALID_FAILURE_KIND"
FEEDBACK_RECOVERY_BLOCKED_INVALID_SEVERITY = "FEEDBACK_RECOVERY_BLOCKED_INVALID_SEVERITY"
FEEDBACK_RECOVERY_BLOCKED_INVALID_OPTION_KIND = "FEEDBACK_RECOVERY_BLOCKED_INVALID_OPTION_KIND"
FEEDBACK_RECOVERY_BLOCKED_EMPTY_OPTIONS = "FEEDBACK_RECOVERY_BLOCKED_EMPTY_OPTIONS"
FEEDBACK_RECOVERY_BLOCKED_DUPLICATE_OPTION_ID = "FEEDBACK_RECOVERY_BLOCKED_DUPLICATE_OPTION_ID"
FEEDBACK_RECOVERY_BLOCKED_SELECTED_OPTION_MISSING = "FEEDBACK_RECOVERY_BLOCKED_SELECTED_OPTION_MISSING"
FEEDBACK_RECOVERY_BLOCKED_RETRY_POLICY = "FEEDBACK_RECOVERY_BLOCKED_RETRY_POLICY"
FEEDBACK_RECOVERY_BLOCKED_FALLBACK_POLICY = "FEEDBACK_RECOVERY_BLOCKED_FALLBACK_POLICY"
FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME = "FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME"
FEEDBACK_RECOVERY_BLOCKED_EXPIRED_FAILURE = "FEEDBACK_RECOVERY_BLOCKED_EXPIRED_FAILURE"
FEEDBACK_RECOVERY_BLOCKED_EXPIRED_PLAN = "FEEDBACK_RECOVERY_BLOCKED_EXPIRED_PLAN"
FEEDBACK_RECOVERY_BLOCKED_OBSERVATION_HASH_MISMATCH = "FEEDBACK_RECOVERY_BLOCKED_OBSERVATION_HASH_MISMATCH"
FEEDBACK_RECOVERY_BLOCKED_FAILURE_HASH_MISMATCH = "FEEDBACK_RECOVERY_BLOCKED_FAILURE_HASH_MISMATCH"
FEEDBACK_RECOVERY_BLOCKED_COMMAND_INJECTION = "FEEDBACK_RECOVERY_BLOCKED_COMMAND_INJECTION"
FEEDBACK_RECOVERY_BLOCKED_PROVIDER_CALL = "FEEDBACK_RECOVERY_BLOCKED_PROVIDER_CALL"
FEEDBACK_RECOVERY_BLOCKED_GIT_ACTION = "FEEDBACK_RECOVERY_BLOCKED_GIT_ACTION"
FEEDBACK_RECOVERY_BLOCKED_PACKAGE_INSTALL = "FEEDBACK_RECOVERY_BLOCKED_PACKAGE_INSTALL"
FEEDBACK_RECOVERY_BLOCKED_BROWSER_ACTION = "FEEDBACK_RECOVERY_BLOCKED_BROWSER_ACTION"
FEEDBACK_RECOVERY_BLOCKED_MCP_TOOL = "FEEDBACK_RECOVERY_BLOCKED_MCP_TOOL"
FEEDBACK_RECOVERY_BLOCKED_CODEX_AIDER = "FEEDBACK_RECOVERY_BLOCKED_CODEX_AIDER"
FEEDBACK_RECOVERY_BLOCKED_AGENT_LOOP = "FEEDBACK_RECOVERY_BLOCKED_AGENT_LOOP"
FEEDBACK_RECOVERY_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING = "FEEDBACK_RECOVERY_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING"
FEEDBACK_RECOVERY_BLOCKED_ENV_OR_SECRET = "FEEDBACK_RECOVERY_BLOCKED_ENV_OR_SECRET"
FEEDBACK_RECOVERY_BLOCKED_AUTHORITY_CLAIM = "FEEDBACK_RECOVERY_BLOCKED_AUTHORITY_CLAIM"
FEEDBACK_RECOVERY_BLOCKED_NON_JSON_SERIALIZABLE = "FEEDBACK_RECOVERY_BLOCKED_NON_JSON_SERIALIZABLE"
FEEDBACK_RECOVERY_BLOCKED_AMBIGUOUS_EVIDENCE = "FEEDBACK_RECOVERY_BLOCKED_AMBIGUOUS_EVIDENCE"

RECOVERY_RISK_LOW = "LOW"
RECOVERY_RISK_MEDIUM = "MEDIUM"
RECOVERY_RISK_HIGH = "HIGH"
RECOVERY_RISK_BLOCKED = "BLOCKED"

SUPPORTED_SOURCE_STEPS = frozenset(
    {
        "step_42_" + "package" + "_install_proposal",
        "step_43_controlled_" + "package" + "_install",
        "step_44_controlled_browser_read",
        "step_45_browser_automation_preview",
        "step_46_browser_automation_governance",
        "step_47_controlled_browser_automation",
        "step_48_coding_assistant_boundary",
        "step_49_mcp_boundary",
        "step_50_async_io_orchestration",
    }
)
SUPPORTED_OBSERVED_STATUSES = frozenset(
    {
        "ok",
        "blocked",
        "failed",
        "expired",
        "mismatched_evidence",
        "unsafe_scope",
        "test_failure",
        "validation_failure",
        "human_rejected",
        "needs_review",
    }
)
SUPPORTED_FAILURE_KINDS = frozenset(
    {
        "validation_failure",
        "hash_mismatch",
        "expired_evidence",
        "missing_evidence",
        "scope_violation",
        "safety_boundary_violation",
        "test_failure",
        "blocked_by_policy",
        "human_rejection",
        "ambiguous_evidence",
    }
)
SUPPORTED_RECOVERY_OPTION_KINDS = frozenset(
    {
        "request_new_evidence",
        "rerun_validation_only",
        "rebuild_preview_only",
        "regenerate_proposal_only",
        "ask_human_review",
        "mark_blocked",
        "escalate_to_manual_review",
    }
)
SUPPORTED_POLICIES = frozenset({"none", "manual_review_required"})
SUPPORTED_SEVERITIES = frozenset({"info", "low", "medium", "high", "critical"})
HIGH_RISK_FAILURE_KINDS = frozenset({"scope_violation", "safety_boundary_violation", "hash_mismatch"})
HIGH_RISK_SOURCE_STEPS = frozenset(
    {
        "step_43_controlled_" + "package" + "_install",
        "step_47_controlled_browser_automation",
        "step_48_coding_assistant_boundary",
        "step_49_mcp_boundary",
    }
)

_ALLOWED_OBSERVATION_FIELDS = frozenset(
    {
        "schema_version",
        "observation_id",
        "source_step",
        "source_result_hash",
        "observed_status",
        "observed_codes",
        "observed_at",
        "observer",
        "observation_hash",
    }
)
_ALLOWED_FAILURE_FIELDS = frozenset(
    {
        "schema_version",
        "failure_id",
        "observation_hash",
        "failure_kind",
        "failed_operation_id",
        "failed_evidence_hashes",
        "failure_summary",
        "severity",
        "reported_at",
        "expires_at",
        "failure_hash",
    }
)
_ALLOWED_OPTION_FIELDS = frozenset(
    {
        "schema_version",
        "option_id",
        "option_kind",
        "target_operation_id",
        "required_new_evidence_hashes",
        "blocked_until_human_review",
        "recovery_summary",
        "option_hash",
    }
)
_ALLOWED_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "plan_id",
        "failure_hash",
        "recovery_options",
        "selected_option_id",
        "retry_policy",
        "fallback_policy",
        "created_at",
        "expires_at",
        "plan_hash",
    }
)
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approve",
        "approved",
        "authorize",
        "authorized",
        "authority",
        "recoverable_execute",
        "ready_to_retry",
        "ready_to_fallback",
        "can_recover",
        "can_execute",
        "can_dispatch",
        "can_retry",
        "can_fallback",
        "can_stream",
        "can_call_tool",
        "can_call_provider",
        "can_call_mcp",
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
_PROVIDER_TERMS = ("provider" + "_call", "call_provider")
_GIT_TERMS = ("git" + "_action", "git_commit", "git_push")
_PACKAGE_TERMS = ("package" + "_install", "pip install", "npm install", "apt install")
_BROWSER_TERMS = (
    "browser_action",
    "browser_automation",
    "sel" + "enium",
    "play" + "wright",
    "web" + "browser",
)
_MCP_TERMS = ("mcp" + "_tool", "call" + "_tool", "read_resource")
_CODEX_AIDER_TERMS = ("cod" + "ex", "aid" + "er")
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
_RETRY_FALLBACK_TERMS = (
    "retry_now",
    "auto_retry",
    "automatic_retry",
    "fallback_now",
    "auto_fallback",
    "automatic_fallback",
    "streaming",
    "tool_call",
    "dispatch",
    "dispatcher",
    "execute",
    "run",
)
_ENV_SECRET_TERMS = (
    "api" + "_key",
    "token",
    "secret",
    "env",
    "password",
    "credential",
    ".env",
    "id_rsa",
    "ssh_key",
)
_TEXT_SCAN_SKIP_KEYS = frozenset(
    {
        "schema_version",
        "source_step",
        "observed_status",
        "failure_kind",
        "severity",
        "option_kind",
        "retry_policy",
        "fallback_policy",
    }
)
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 2048
_MAX_COLLECTION_ITEMS = 128
_MAX_DEPTH = 8


@dataclass(frozen=True)
class FeedbackObservation:
    schema_version: str
    observation_id: str
    source_step: str
    source_result_hash: str
    observed_status: str
    observed_codes: tuple[str, ...]
    observed_at: int
    observer: str
    observation_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "observation_id", _identifier("observation_id", self.observation_id))
        object.__setattr__(self, "source_step", _required_text("source_step", self.source_step).casefold())
        object.__setattr__(self, "source_result_hash", _required_hash("source_result_hash", self.source_result_hash))
        object.__setattr__(self, "observed_status", _required_text("observed_status", self.observed_status).casefold())
        object.__setattr__(self, "observed_codes", _text_tuple("observed_codes", self.observed_codes, allow_empty=True))
        object.__setattr__(self, "observed_at", _nonnegative_int("observed_at", self.observed_at))
        object.__setattr__(self, "observer", _required_text("observer", self.observer))
        object.__setattr__(self, "observation_hash", _required_hash("observation_hash", self.observation_hash))
        if self.schema_version != FEEDBACK_OBSERVATION_SCHEMA_VERSION:
            raise ValueError("unsupported feedback observation schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "source_step": self.source_step,
            "source_result_hash": self.source_result_hash,
            "observed_status": self.observed_status,
            "observed_codes": self.observed_codes,
            "observed_at": self.observed_at,
            "observer": self.observer,
            "observation_hash": self.observation_hash,
        }


@dataclass(frozen=True)
class RecoveryFailureReport:
    schema_version: str
    failure_id: str
    observation_hash: str
    failure_kind: str
    failed_operation_id: str | None
    failed_evidence_hashes: tuple[str, ...]
    failure_summary: str
    severity: str
    reported_at: int
    expires_at: int
    failure_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "failure_id", _identifier("failure_id", self.failure_id))
        object.__setattr__(self, "observation_hash", _required_hash("observation_hash", self.observation_hash))
        object.__setattr__(self, "failure_kind", _required_text("failure_kind", self.failure_kind).casefold())
        object.__setattr__(self, "failed_operation_id", _optional_identifier("failed_operation_id", self.failed_operation_id))
        object.__setattr__(self, "failed_evidence_hashes", _hash_tuple("failed_evidence_hashes", self.failed_evidence_hashes, allow_empty=True))
        object.__setattr__(self, "failure_summary", _required_text("failure_summary", self.failure_summary))
        object.__setattr__(self, "severity", _required_text("severity", self.severity).casefold())
        object.__setattr__(self, "reported_at", _nonnegative_int("reported_at", self.reported_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "failure_hash", _required_hash("failure_hash", self.failure_hash))
        if self.schema_version != RECOVERY_FAILURE_REPORT_SCHEMA_VERSION:
            raise ValueError("unsupported recovery failure report schema version")
        if self.expires_at <= self.reported_at:
            raise ValueError("failure expires_at must be greater than reported_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "failure_id": self.failure_id,
            "observation_hash": self.observation_hash,
            "failure_kind": self.failure_kind,
            "failed_operation_id": self.failed_operation_id,
            "failed_evidence_hashes": self.failed_evidence_hashes,
            "failure_summary": self.failure_summary,
            "severity": self.severity,
            "reported_at": self.reported_at,
            "expires_at": self.expires_at,
            "failure_hash": self.failure_hash,
        }


@dataclass(frozen=True)
class RecoveryOption:
    schema_version: str
    option_id: str
    option_kind: str
    target_operation_id: str | None
    required_new_evidence_hashes: tuple[str, ...]
    blocked_until_human_review: bool
    recovery_summary: str
    option_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "option_id", _identifier("option_id", self.option_id))
        object.__setattr__(self, "option_kind", _required_text("option_kind", self.option_kind).casefold())
        object.__setattr__(self, "target_operation_id", _optional_identifier("target_operation_id", self.target_operation_id))
        object.__setattr__(self, "required_new_evidence_hashes", _hash_tuple("required_new_evidence_hashes", self.required_new_evidence_hashes, allow_empty=True))
        if not isinstance(self.blocked_until_human_review, bool):
            raise TypeError("blocked_until_human_review must be boolean")
        object.__setattr__(self, "recovery_summary", _required_text("recovery_summary", self.recovery_summary))
        object.__setattr__(self, "option_hash", _required_hash("option_hash", self.option_hash))
        if self.schema_version != RECOVERY_OPTION_SCHEMA_VERSION:
            raise ValueError("unsupported recovery option schema version")
        object.__setattr__(self, "blocked_until_human_review", True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "option_id": self.option_id,
            "option_kind": self.option_kind,
            "target_operation_id": self.target_operation_id,
            "required_new_evidence_hashes": self.required_new_evidence_hashes,
            "blocked_until_human_review": True,
            "recovery_summary": self.recovery_summary,
            "option_hash": self.option_hash,
        }


@dataclass(frozen=True)
class RecoveryPlan:
    schema_version: str
    plan_id: str
    failure_hash: str
    recovery_options: tuple[RecoveryOption, ...]
    selected_option_id: str | None
    retry_policy: str
    fallback_policy: str
    created_at: int
    expires_at: int
    plan_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "plan_id", _identifier("plan_id", self.plan_id))
        object.__setattr__(self, "failure_hash", _required_hash("failure_hash", self.failure_hash))
        object.__setattr__(self, "recovery_options", _option_tuple(self.recovery_options, allow_empty=True))
        object.__setattr__(self, "selected_option_id", _optional_identifier("selected_option_id", self.selected_option_id))
        object.__setattr__(self, "retry_policy", _required_text("retry_policy", self.retry_policy).casefold())
        object.__setattr__(self, "fallback_policy", _required_text("fallback_policy", self.fallback_policy).casefold())
        object.__setattr__(self, "created_at", _nonnegative_int("created_at", self.created_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "plan_hash", _required_hash("plan_hash", self.plan_hash))
        if self.schema_version != RECOVERY_PLAN_SCHEMA_VERSION:
            raise ValueError("unsupported recovery plan schema version")
        if self.expires_at <= self.created_at:
            raise ValueError("plan expires_at must be greater than created_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "failure_hash": self.failure_hash,
            "recovery_options": tuple(option.to_dict() for option in self.recovery_options),
            "selected_option_id": self.selected_option_id,
            "retry_policy": self.retry_policy,
            "fallback_policy": self.fallback_policy,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True)
class RecoveryReviewResult:
    schema_version: str
    ok: bool
    blocked: bool
    recovery_allowed: bool
    retry_allowed: bool
    fallback_allowed: bool
    execution_allowed: bool
    dispatch_allowed: bool
    requires_human_review: bool
    requires_controlled_path: bool
    observation_hash: str | None
    failure_hash: str | None
    plan_hash: str | None
    selected_option_hash: str | None
    recovery_risk_tier: str
    recovery_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    review_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_recover: bool = False
    can_execute: bool = False
    can_dispatch: bool = False
    can_retry: bool = False
    can_fallback: bool = False
    can_stream: bool = False
    can_call_tool: bool = False
    can_call_provider: bool = False
    can_call_mcp: bool = False
    approval_created: bool = False
    dispatcher_created: bool = False
    recovery_executed: bool = False
    selected_option_executed: bool = False
    retry_started: bool = False
    fallback_started: bool = False
    streaming_started: bool = False
    process_started: bool = False
    network_called: bool = False
    provider_called: bool = False
    mcp_called: bool = False
    browser_opened: bool = False
    package_manager_called: bool = False
    git_action_performed: bool = False
    agent_loop_started: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", RECOVERY_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "ok", bool(self.ok) and not bool(self.blocked))
        object.__setattr__(self, "blocked", bool(self.blocked))
        object.__setattr__(self, "recovery_allowed", False)
        object.__setattr__(self, "retry_allowed", False)
        object.__setattr__(self, "fallback_allowed", False)
        object.__setattr__(self, "execution_allowed", False)
        object.__setattr__(self, "dispatch_allowed", False)
        object.__setattr__(self, "requires_human_review", True)
        object.__setattr__(self, "requires_controlled_path", True)
        for field_name in ("observation_hash", "failure_hash", "plan_hash", "selected_option_hash"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required_hash(field_name, value))
        if self.recovery_risk_tier not in {RECOVERY_RISK_LOW, RECOVERY_RISK_MEDIUM, RECOVERY_RISK_HIGH, RECOVERY_RISK_BLOCKED}:
            raise ValueError("unsupported recovery risk tier")
        object.__setattr__(self, "recovery_codes", tuple(sorted(set(_required_text("recovery_codes", item) for item in self.recovery_codes))))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(_required_text("reason_codes", item) for item in self.reason_codes))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))
        for field_name in _REVIEW_FALSE_FLAGS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": RECOVERY_REVIEW_SCHEMA_VERSION,
            "ok": self.ok,
            "blocked": self.blocked,
            "recovery_allowed": False,
            "retry_allowed": False,
            "fallback_allowed": False,
            "execution_allowed": False,
            "dispatch_allowed": False,
            "requires_human_review": True,
            "requires_controlled_path": True,
            "observation_hash": self.observation_hash,
            "failure_hash": self.failure_hash,
            "plan_hash": self.plan_hash,
            "selected_option_hash": self.selected_option_hash,
            "recovery_risk_tier": self.recovery_risk_tier,
            "recovery_codes": self.recovery_codes,
            "reason_codes": self.reason_codes,
            "review_hash": self.review_hash,
        }
        for field_name in _REVIEW_FALSE_FLAGS:
            data[field_name] = False
        return data


_REVIEW_FALSE_FLAGS = (
    "gate_satisfied",
    "human_barrier_satisfied",
    "can_recover",
    "can_execute",
    "can_dispatch",
    "can_retry",
    "can_fallback",
    "can_stream",
    "can_call_tool",
    "can_call_provider",
    "can_call_mcp",
    "approval_created",
    "dispatcher_created",
    "recovery_executed",
    "selected_option_executed",
    "retry_started",
    "fallback_started",
    "streaming_started",
    "process_started",
    "network_called",
    "provider_called",
    "mcp_called",
    "browser_opened",
    "package_manager_called",
    "git_action_performed",
    "agent_loop_started",
)


def canonical_feedback_recovery_json(value: Any) -> str:
    return json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_feedback_recovery_value(value: Any) -> str:
    return hashlib.sha256(canonical_feedback_recovery_json(value).encode("utf-8")).hexdigest()


def build_feedback_observation(
    *,
    observation_id: str,
    source_step: str,
    source_result_hash: str,
    observed_status: str,
    observed_codes: tuple[str, ...],
    observed_at: int,
    observer: str,
) -> FeedbackObservation:
    material = {
        "schema_version": FEEDBACK_OBSERVATION_SCHEMA_VERSION,
        "observation_id": _identifier("observation_id", observation_id),
        "source_step": _required_text("source_step", source_step).casefold(),
        "source_result_hash": _required_hash("source_result_hash", source_result_hash),
        "observed_status": _required_text("observed_status", observed_status).casefold(),
        "observed_codes": _text_tuple("observed_codes", observed_codes, allow_empty=True),
        "observed_at": _nonnegative_int("observed_at", observed_at),
        "observer": _required_text("observer", observer),
    }
    return FeedbackObservation(**material, observation_hash=_hash_material(material))


def build_recovery_failure_report(
    *,
    failure_id: str,
    observation_hash: str,
    failure_kind: str,
    failed_operation_id: str | None,
    failed_evidence_hashes: tuple[str, ...],
    failure_summary: str,
    severity: str,
    reported_at: int,
    expires_at: int,
) -> RecoveryFailureReport:
    material = {
        "schema_version": RECOVERY_FAILURE_REPORT_SCHEMA_VERSION,
        "failure_id": _identifier("failure_id", failure_id),
        "observation_hash": _required_hash("observation_hash", observation_hash),
        "failure_kind": _required_text("failure_kind", failure_kind).casefold(),
        "failed_operation_id": _optional_identifier("failed_operation_id", failed_operation_id),
        "failed_evidence_hashes": _hash_tuple("failed_evidence_hashes", failed_evidence_hashes, allow_empty=True),
        "failure_summary": _required_text("failure_summary", failure_summary),
        "severity": _required_text("severity", severity).casefold(),
        "reported_at": _nonnegative_int("reported_at", reported_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return RecoveryFailureReport(**material, failure_hash=_hash_material(material))


def build_recovery_option(
    *,
    option_id: str,
    option_kind: str,
    target_operation_id: str | None,
    required_new_evidence_hashes: tuple[str, ...],
    blocked_until_human_review: bool,
    recovery_summary: str,
) -> RecoveryOption:
    material = {
        "schema_version": RECOVERY_OPTION_SCHEMA_VERSION,
        "option_id": _identifier("option_id", option_id),
        "option_kind": _required_text("option_kind", option_kind).casefold(),
        "target_operation_id": _optional_identifier("target_operation_id", target_operation_id),
        "required_new_evidence_hashes": _hash_tuple("required_new_evidence_hashes", required_new_evidence_hashes, allow_empty=True),
        "blocked_until_human_review": bool(blocked_until_human_review),
        "recovery_summary": _required_text("recovery_summary", recovery_summary),
    }
    material["blocked_until_human_review"] = True
    return RecoveryOption(**material, option_hash=_hash_material(material))


def build_recovery_plan(
    *,
    plan_id: str,
    failure_hash: str,
    recovery_options: tuple[RecoveryOption, ...],
    selected_option_id: str | None,
    retry_policy: str,
    fallback_policy: str,
    created_at: int,
    expires_at: int,
) -> RecoveryPlan:
    options = _option_tuple(recovery_options, allow_empty=True)
    material = {
        "schema_version": RECOVERY_PLAN_SCHEMA_VERSION,
        "plan_id": _identifier("plan_id", plan_id),
        "failure_hash": _required_hash("failure_hash", failure_hash),
        "recovery_options": tuple(option.option_hash for option in options),
        "selected_option_id": _optional_identifier("selected_option_id", selected_option_id),
        "retry_policy": _required_text("retry_policy", retry_policy).casefold(),
        "fallback_policy": _required_text("fallback_policy", fallback_policy).casefold(),
        "created_at": _nonnegative_int("created_at", created_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return RecoveryPlan(
        schema_version=RECOVERY_PLAN_SCHEMA_VERSION,
        plan_id=material["plan_id"],
        failure_hash=material["failure_hash"],
        recovery_options=options,
        selected_option_id=material["selected_option_id"],
        retry_policy=material["retry_policy"],
        fallback_policy=material["fallback_policy"],
        created_at=material["created_at"],
        expires_at=material["expires_at"],
        plan_hash=_hash_material(material),
    )


def evaluate_recovery_plan(
    *,
    observation: FeedbackObservation,
    failure: RecoveryFailureReport,
    plan: RecoveryPlan,
    now: int,
) -> RecoveryReviewResult:
    reason_codes: list[str] = []
    try:
        now_value = _nonnegative_int("now", now)
    except (TypeError, ValueError):
        return _blocked((FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME,))

    try:
        observation_data = _coerce_mapping(observation)
        failure_data = _coerce_mapping(failure)
        plan_data = _coerce_mapping(plan)
        evidence_fingerprint = _json_fingerprint({"observation": observation_data, "failure": failure_data, "plan": plan_data})
    except TypeError:
        return _blocked((FEEDBACK_RECOVERY_BLOCKED_NON_JSON_SERIALIZABLE,))

    reason_codes.extend(_danger_reason_codes((observation_data, failure_data, plan_data)))
    if _contains_unknown_fields(observation_data, failure_data, plan_data):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_AMBIGUOUS_EVIDENCE)
    if _invalid_hash_evidence_present(observation_data, failure_data, plan_data):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH)
    if _invalid_time_evidence_present(observation_data, failure_data, plan_data):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME)

    try:
        observed = _coerce_observation(observation_data)
        reported = _coerce_failure(failure_data)
        recovery_plan = _coerce_plan(plan_data)
    except (TypeError, ValueError):
        return _blocked(
            tuple(reason_codes or (FEEDBACK_RECOVERY_BLOCKED_AMBIGUOUS_EVIDENCE,)),
            input_fingerprint=evidence_fingerprint,
        )

    options = recovery_plan.recovery_options
    option_ids = tuple(option.option_id for option in options)
    option_by_id = {option.option_id: option for option in options}
    selected_option = option_by_id.get(recovery_plan.selected_option_id) if recovery_plan.selected_option_id is not None else None

    if observed.source_step not in SUPPORTED_SOURCE_STEPS:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_SOURCE_STEP)
    if observed.observed_status not in SUPPORTED_OBSERVED_STATUSES:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_OBSERVED_STATUS)
    if reported.failure_kind not in SUPPORTED_FAILURE_KINDS:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_FAILURE_KIND)
    if reported.severity not in SUPPORTED_SEVERITIES:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_SEVERITY)
    if not options:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_EMPTY_OPTIONS)
    if len(set(option_ids)) != len(option_ids):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_DUPLICATE_OPTION_ID)
    if any(option.option_kind not in SUPPORTED_RECOVERY_OPTION_KINDS for option in options):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_OPTION_KIND)
    if recovery_plan.selected_option_id is not None and recovery_plan.selected_option_id not in option_by_id:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_SELECTED_OPTION_MISSING)
    if recovery_plan.retry_policy not in SUPPORTED_POLICIES:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_RETRY_POLICY)
    if recovery_plan.fallback_policy not in SUPPORTED_POLICIES:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_FALLBACK_POLICY)
    if now_value < observed.observed_at or now_value < reported.reported_at or now_value < recovery_plan.created_at:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME)
    if now_value > reported.expires_at:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_EXPIRED_FAILURE)
    if now_value > recovery_plan.expires_at:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_EXPIRED_PLAN)

    if observed.observation_hash != _hash_material(_observation_hash_material(observed)):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH)
    if reported.failure_hash != _hash_material(_failure_hash_material(reported)):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH)
    if any(option.option_hash != _hash_material(_option_hash_material(option)) for option in options):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH)
    if recovery_plan.plan_hash != _hash_material(_plan_hash_material(recovery_plan)):
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH)
    if reported.observation_hash != observed.observation_hash:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_OBSERVATION_HASH_MISMATCH)
    if recovery_plan.failure_hash != reported.failure_hash:
        reason_codes.append(FEEDBACK_RECOVERY_BLOCKED_FAILURE_HASH_MISMATCH)

    blocked = bool(set(reason_codes) - {FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW_REASON, FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH_REASON})
    if blocked:
        reason_codes = sorted(set(reason_codes))
    else:
        reason_codes = sorted(
            {
                FEEDBACK_RECOVERY_OK,
                FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW_REASON,
                FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH_REASON,
            }
        )

    recovery_codes = _recovery_codes(observed, options)
    risk_tier = _risk_tier(blocked, observed, reported, selected_option)
    selected_hash = selected_option.option_hash if selected_option is not None else None
    material = {
        "schema_version": RECOVERY_REVIEW_SCHEMA_VERSION,
        "ok": not blocked,
        "blocked": blocked,
        "recovery_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "observation_hash": observed.observation_hash,
        "failure_hash": reported.failure_hash,
        "plan_hash": recovery_plan.plan_hash,
        "selected_option_hash": selected_hash,
        "recovery_risk_tier": risk_tier,
        "recovery_codes": recovery_codes,
        "reason_codes": tuple(reason_codes),
        "evidence_fingerprint": evidence_fingerprint,
    }
    return RecoveryReviewResult(
        schema_version=RECOVERY_REVIEW_SCHEMA_VERSION,
        ok=not blocked,
        blocked=blocked,
        recovery_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        execution_allowed=False,
        dispatch_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        observation_hash=observed.observation_hash,
        failure_hash=reported.failure_hash,
        plan_hash=recovery_plan.plan_hash,
        selected_option_hash=selected_hash,
        recovery_risk_tier=risk_tier,
        recovery_codes=recovery_codes,
        reason_codes=tuple(reason_codes),
        review_hash=hash_feedback_recovery_value(material),
    )


def _hash_material(value: Mapping[str, Any]) -> str:
    data = dict(value)
    for field_name in ("observation_hash", "failure_hash", "option_hash", "plan_hash", "review_hash"):
        data.pop(field_name, None)
    return hash_feedback_recovery_value(_json_fingerprint(data))


def _observation_hash_material(value: FeedbackObservation) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("observation_hash", None)
    return data


def _failure_hash_material(value: RecoveryFailureReport) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("failure_hash", None)
    return data


def _option_hash_material(value: RecoveryOption) -> dict[str, Any]:
    data = value.to_dict()
    data.pop("option_hash", None)
    return data


def _plan_hash_material(value: RecoveryPlan) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "plan_id": value.plan_id,
        "failure_hash": value.failure_hash,
        "recovery_options": tuple(option.option_hash for option in value.recovery_options),
        "selected_option_id": value.selected_option_id,
        "retry_policy": value.retry_policy,
        "fallback_policy": value.fallback_policy,
        "created_at": value.created_at,
        "expires_at": value.expires_at,
    }


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> RecoveryReviewResult:
    codes = tuple(sorted(set(reason_codes)))
    material = {
        "schema_version": RECOVERY_REVIEW_SCHEMA_VERSION,
        "ok": False,
        "blocked": True,
        "recovery_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "observation_hash": None,
        "failure_hash": None,
        "plan_hash": None,
        "selected_option_hash": None,
        "recovery_risk_tier": RECOVERY_RISK_BLOCKED,
        "recovery_codes": (
            FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW,
            FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH,
            FEEDBACK_RECOVERY_NON_AUTHORITY,
        ),
        "reason_codes": codes,
        "input_fingerprint": input_fingerprint,
    }
    return RecoveryReviewResult(
        schema_version=RECOVERY_REVIEW_SCHEMA_VERSION,
        ok=False,
        blocked=True,
        recovery_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        execution_allowed=False,
        dispatch_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        observation_hash=None,
        failure_hash=None,
        plan_hash=None,
        selected_option_hash=None,
        recovery_risk_tier=RECOVERY_RISK_BLOCKED,
        recovery_codes=material["recovery_codes"],
        reason_codes=codes,
        review_hash=hash_feedback_recovery_value(material),
    )


def _coerce_observation(value: object) -> FeedbackObservation:
    if isinstance(value, FeedbackObservation):
        return value
    if isinstance(value, Mapping):
        return FeedbackObservation(**_sanitize_mapping(value, _ALLOWED_OBSERVATION_FIELDS))
    raise TypeError("feedback observation is required")


def _coerce_failure(value: object) -> RecoveryFailureReport:
    if isinstance(value, RecoveryFailureReport):
        return value
    if isinstance(value, Mapping):
        return RecoveryFailureReport(**_sanitize_mapping(value, _ALLOWED_FAILURE_FIELDS))
    raise TypeError("recovery failure report is required")


def _coerce_option(value: object) -> RecoveryOption:
    if isinstance(value, RecoveryOption):
        return value
    if isinstance(value, Mapping):
        return RecoveryOption(**_sanitize_mapping(value, _ALLOWED_OPTION_FIELDS))
    raise TypeError("recovery option is required")


def _coerce_plan(value: object) -> RecoveryPlan:
    if isinstance(value, RecoveryPlan):
        return value
    if isinstance(value, Mapping):
        data = _sanitize_mapping(value, _ALLOWED_PLAN_FIELDS)
        options = data.get("recovery_options")
        if not isinstance(options, (tuple, list)):
            raise TypeError("recovery_options must be a sequence")
        data["recovery_options"] = tuple(_coerce_option(option) for option in options)
        return RecoveryPlan(**data)
    raise TypeError("recovery plan is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("feedback recovery evidence must be mapping evidence")


def _sanitize_mapping(value: Mapping[str, Any], allowed_fields: frozenset[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key in allowed_fields}


def _option_tuple(value: object, *, allow_empty: bool) -> tuple[RecoveryOption, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError("recovery_options must be a sequence")
    if not value and not allow_empty:
        raise TypeError("recovery_options must not be empty")
    return tuple(_coerce_option(item) for item in value)


def _contains_unknown_fields(observation: Mapping[str, Any], failure: Mapping[str, Any], plan: Mapping[str, Any]) -> bool:
    if any(key not in _ALLOWED_OBSERVATION_FIELDS for key in observation):
        return True
    if any(key not in _ALLOWED_FAILURE_FIELDS for key in failure):
        return True
    if any(key not in _ALLOWED_PLAN_FIELDS for key in plan):
        return True
    options = plan.get("recovery_options")
    if isinstance(options, (tuple, list)):
        return any(isinstance(option, Mapping) and any(key not in _ALLOWED_OPTION_FIELDS for key in option) for option in options)
    return False


def _invalid_hash_evidence_present(observation: Mapping[str, Any], failure: Mapping[str, Any], plan: Mapping[str, Any]) -> bool:
    for data, fields in (
        (observation, ("source_result_hash", "observation_hash")),
        (failure, ("observation_hash", "failure_hash")),
        (plan, ("failure_hash", "plan_hash")),
    ):
        for field_name in fields:
            if field_name in data and not _sha256_like(data[field_name]):
                return True
    failed_hashes = failure.get("failed_evidence_hashes")
    if not isinstance(failed_hashes, (tuple, list)) or any(not _sha256_like(item) for item in failed_hashes):
        return True
    options = plan.get("recovery_options")
    if not isinstance(options, (tuple, list)):
        return True
    for option in options:
        option_data = _coerce_mapping_if_possible(option)
        if option_data is None:
            return True
        if "option_hash" in option_data and not _sha256_like(option_data["option_hash"]):
            return True
        required_hashes = option_data.get("required_new_evidence_hashes")
        if not isinstance(required_hashes, (tuple, list)) or any(not _sha256_like(item) for item in required_hashes):
            return True
    return False


def _invalid_time_evidence_present(observation: Mapping[str, Any], failure: Mapping[str, Any], plan: Mapping[str, Any]) -> bool:
    if not _valid_nonnegative_int(observation.get("observed_at")):
        return True
    reported_at = failure.get("reported_at")
    failure_expires_at = failure.get("expires_at")
    created_at = plan.get("created_at")
    plan_expires_at = plan.get("expires_at")
    if not all(_valid_nonnegative_int(item) for item in (reported_at, failure_expires_at, created_at, plan_expires_at)):
        return True
    if failure_expires_at <= reported_at or plan_expires_at <= created_at:
        return True
    return False


def _danger_reason_codes(value: object) -> list[str]:
    codes: set[str] = set()
    for key, text in _scanned_text_items(value):
        normalized = text.casefold()
        normalized_key = key.casefold()
        if normalized_key in _AUTHORITY_FIELD_NAMES or any(term in normalized for term in _AUTHORITY_FIELD_NAMES):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_AUTHORITY_CLAIM)
        if any(term.casefold() in normalized for term in _COMMAND_INJECTION_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_COMMAND_INJECTION)
        if any(term in normalized for term in _PROVIDER_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_PROVIDER_CALL)
        if any(term in normalized for term in _GIT_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_GIT_ACTION)
        if any(term in normalized for term in _PACKAGE_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_PACKAGE_INSTALL)
        if any(term in normalized for term in _BROWSER_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_BROWSER_ACTION)
        if any(term in normalized for term in _MCP_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_MCP_TOOL)
        if any(term in normalized for term in _CODEX_AIDER_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_CODEX_AIDER)
        if any(term in normalized for term in _AGENT_LOOP_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_AGENT_LOOP)
        if any(term in normalized for term in _RETRY_FALLBACK_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING)
        if any(term in normalized for term in _ENV_SECRET_TERMS):
            codes.add(FEEDBACK_RECOVERY_BLOCKED_ENV_OR_SECRET)
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


def _recovery_codes(observation: FeedbackObservation, options: tuple[RecoveryOption, ...]) -> tuple[str, ...]:
    codes = {
        FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW,
        FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH,
        FEEDBACK_RECOVERY_NON_AUTHORITY,
    }
    if observation.observed_status == "ok":
        codes.add(FEEDBACK_RECOVERY_OBSERVED_OK)
    elif observation.observed_status == "blocked":
        codes.add(FEEDBACK_RECOVERY_OBSERVED_BLOCKED)
    else:
        codes.add(FEEDBACK_RECOVERY_OBSERVED_FAILED)
    option_kinds = frozenset(option.option_kind for option in options)
    if option_kinds & {"ask_human_review", "mark_blocked", "escalate_to_manual_review"}:
        codes.add(FEEDBACK_RECOVERY_OPTION_MANUAL_REVIEW)
    if "request_new_evidence" in option_kinds:
        codes.add(FEEDBACK_RECOVERY_OPTION_NEW_EVIDENCE)
    if "rebuild_preview_only" in option_kinds:
        codes.add(FEEDBACK_RECOVERY_OPTION_REBUILD_PREVIEW)
    if "rerun_validation_only" in option_kinds:
        codes.add(FEEDBACK_RECOVERY_OPTION_RERUN_VALIDATION)
    return tuple(sorted(codes))


def _risk_tier(blocked: bool, observation: FeedbackObservation, failure: RecoveryFailureReport, option: RecoveryOption | None) -> str:
    if blocked:
        return RECOVERY_RISK_BLOCKED
    if failure.severity in {"high", "critical"} or failure.failure_kind in HIGH_RISK_FAILURE_KINDS or observation.source_step in HIGH_RISK_SOURCE_STEPS:
        return RECOVERY_RISK_HIGH
    if option is not None and option.option_kind in {"ask_human_review", "mark_blocked", "escalate_to_manual_review"}:
        return RECOVERY_RISK_MEDIUM
    if failure.severity == "medium":
        return RECOVERY_RISK_MEDIUM
    return RECOVERY_RISK_LOW


def _coerce_mapping_if_possible(value: object) -> dict[str, Any] | None:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    return None


def _identifier(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError(f"{name} must be a stable identifier")
    return text


def _optional_identifier(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _identifier(name, value)


def _required_hash(name: str, value: object) -> str:
    text = _required_text(name, value).casefold()
    if not _sha256_like(text):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return text


def _hash_tuple(name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    if not value and not allow_empty:
        raise TypeError(f"{name} must not be empty")
    return tuple(_required_hash(name, item) for item in value)


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
        raise TypeError("feedback recovery evidence is too deeply nested")
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
    raise TypeError("feedback recovery evidence must be JSON serializable")
