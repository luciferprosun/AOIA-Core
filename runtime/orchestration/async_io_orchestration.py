from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


ASYNC_IO_OPERATION_SCHEMA_VERSION = "AOIA_ASYNC_IO_OPERATION_1A"
ASYNC_IO_ORCHESTRATION_PLAN_SCHEMA_VERSION = "AOIA_ASYNC_IO_ORCHESTRATION_PLAN_1A"
ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION = "AOIA_ASYNC_IO_ORCHESTRATION_REVIEW_1A"

ASYNC_IO_ORCHESTRATION_READY_METADATA = "ASYNC_IO_ORCHESTRATION_READY_METADATA"
ASYNC_IO_ORCHESTRATION_BLOCKED_BY_DEPENDENCY = "ASYNC_IO_ORCHESTRATION_BLOCKED_BY_DEPENDENCY"
ASYNC_IO_ORCHESTRATION_DEPENDENCY_ORDERED = "ASYNC_IO_ORCHESTRATION_DEPENDENCY_ORDERED"
ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW = "ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW"
ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH = "ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH"
ASYNC_IO_ORCHESTRATION_NON_AUTHORITY = "ASYNC_IO_ORCHESTRATION_NON_AUTHORITY"

ASYNC_IO_ORCHESTRATION_OK = "ASYNC_IO_ORCHESTRATION_OK"
ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION = "ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION"
ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION_KIND = "ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION_KIND"
ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH = "ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH"
ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_OPERATION_ID = "ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_OPERATION_ID"
ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_DEPENDENCY_ID = "ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_DEPENDENCY_ID"
ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_COMPLETED_ID = "ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_COMPLETED_ID"
ASYNC_IO_ORCHESTRATION_BLOCKED_UNKNOWN_COMPLETED_ID = "ASYNC_IO_ORCHESTRATION_BLOCKED_UNKNOWN_COMPLETED_ID"
ASYNC_IO_ORCHESTRATION_BLOCKED_MISSING_DEPENDENCY = "ASYNC_IO_ORCHESTRATION_BLOCKED_MISSING_DEPENDENCY"
ASYNC_IO_ORCHESTRATION_BLOCKED_DEPENDENCY_CYCLE = "ASYNC_IO_ORCHESTRATION_BLOCKED_DEPENDENCY_CYCLE"
ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_OPERATIONS = "ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_OPERATIONS"
ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_READY_OPERATIONS = "ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_READY_OPERATIONS"
ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_ORDERING_POLICY = "ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_ORDERING_POLICY"
ASYNC_IO_ORCHESTRATION_BLOCKED_RETRY_POLICY = "ASYNC_IO_ORCHESTRATION_BLOCKED_RETRY_POLICY"
ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME = "ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME"
ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_OPERATION = "ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_OPERATION"
ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_PLAN = "ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_PLAN"
ASYNC_IO_ORCHESTRATION_BLOCKED_COMMAND_INJECTION = "ASYNC_IO_ORCHESTRATION_BLOCKED_COMMAND_INJECTION"
ASYNC_IO_ORCHESTRATION_BLOCKED_PROVIDER_CALL = "ASYNC_IO_ORCHESTRATION_BLOCKED_PROVIDER_CALL"
ASYNC_IO_ORCHESTRATION_BLOCKED_GIT_ACTION = "ASYNC_IO_ORCHESTRATION_BLOCKED_GIT_ACTION"
ASYNC_IO_ORCHESTRATION_BLOCKED_PACKAGE_INSTALL = "ASYNC_IO_ORCHESTRATION_BLOCKED_PACKAGE_INSTALL"
ASYNC_IO_ORCHESTRATION_BLOCKED_BROWSER_ACTION = "ASYNC_IO_ORCHESTRATION_BLOCKED_BROWSER_ACTION"
ASYNC_IO_ORCHESTRATION_BLOCKED_MCP_TOOL = "ASYNC_IO_ORCHESTRATION_BLOCKED_MCP_TOOL"
ASYNC_IO_ORCHESTRATION_BLOCKED_CODEX_AIDER = "ASYNC_IO_ORCHESTRATION_BLOCKED_CODEX_AIDER"
ASYNC_IO_ORCHESTRATION_BLOCKED_AGENT_LOOP = "ASYNC_IO_ORCHESTRATION_BLOCKED_AGENT_LOOP"
ASYNC_IO_ORCHESTRATION_BLOCKED_ENV_OR_SECRET = "ASYNC_IO_ORCHESTRATION_BLOCKED_ENV_OR_SECRET"
ASYNC_IO_ORCHESTRATION_BLOCKED_AUTHORITY_CLAIM = "ASYNC_IO_ORCHESTRATION_BLOCKED_AUTHORITY_CLAIM"
ASYNC_IO_ORCHESTRATION_BLOCKED_NON_JSON_SERIALIZABLE = "ASYNC_IO_ORCHESTRATION_BLOCKED_NON_JSON_SERIALIZABLE"
ASYNC_IO_ORCHESTRATION_BLOCKED_AMBIGUOUS_EVIDENCE = "ASYNC_IO_ORCHESTRATION_BLOCKED_AMBIGUOUS_EVIDENCE"
ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW_REASON = "ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW"
ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH_REASON = "ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH"

SUPPORTED_ASYNC_IO_OPERATION_KINDS = frozenset(
    {
        "package" + "_install_proposal",
        "controlled_" + "package" + "_install",
        "controlled_browser_read",
        "browser_automation_preview",
        "browser_automation_governance",
        "controlled_browser_automation",
        "coding_assistant_boundary",
        "mcp_boundary",
        "human_review_checkpoint",
        "audit_ledger_append",
    }
)
HIGH_RISK_OPERATION_KINDS = frozenset(
    {
        "controlled_" + "package" + "_install",
        "controlled_browser_automation",
        "mcp_boundary",
        "coding_assistant_boundary",
    }
)
SUPPORTED_ORDERING_POLICIES = frozenset({"dependency_topological", "declaration_order", "blocked_only_review"})
SUPPORTED_RETRY_POLICIES = frozenset({"none"})

_ALLOWED_OPERATION_FIELDS = frozenset(
    {
        "schema_version",
        "operation_id",
        "operation_kind",
        "input_hashes",
        "dependency_operation_ids",
        "expected_output_hash",
        "requested_by",
        "requested_at",
        "expires_at",
        "operation_hash",
    }
)
_ALLOWED_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "plan_id",
        "operations",
        "ordering_policy",
        "max_operations",
        "max_ready_operations",
        "retry_policy",
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
        "ready_to_" + "execute",
        "can_" + "execute",
        "can_" + "dispatch",
        "can_" + "retry",
        "can_" + "fallback",
        "can_" + "stream",
        "can_" + "call_tool",
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
_CONTROL_TERMS = ("retry", "fallback", "streaming", "dispatch", "dispatcher", "execute", "run")
_TEXT_SCAN_SKIP_KEYS = frozenset({"schema_version", "operation_kind", "ordering_policy", "retry_policy"})
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 1024
_MAX_COLLECTION_ITEMS = 128
_MAX_DEPTH = 8


@dataclass(frozen=True)
class AsyncIOOperationEnvelope:
    schema_version: str
    operation_id: str
    operation_kind: str
    input_hashes: tuple[str, ...]
    dependency_operation_ids: tuple[str, ...]
    expected_output_hash: str | None
    requested_by: str
    requested_at: int
    expires_at: int
    operation_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "operation_id", _identifier("operation_id", self.operation_id))
        object.__setattr__(self, "operation_kind", _required_text("operation_kind", self.operation_kind).casefold())
        object.__setattr__(self, "input_hashes", _hash_tuple("input_hashes", self.input_hashes, allow_empty=True))
        object.__setattr__(
            self,
            "dependency_operation_ids",
            _identifier_tuple("dependency_operation_ids", self.dependency_operation_ids, allow_empty=True),
        )
        object.__setattr__(self, "expected_output_hash", _optional_hash("expected_output_hash", self.expected_output_hash))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "requested_at", _nonnegative_int("requested_at", self.requested_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "operation_hash", _required_hash("operation_hash", self.operation_hash))
        if self.schema_version != ASYNC_IO_OPERATION_SCHEMA_VERSION:
            raise ValueError("unsupported async I/O operation schema version")
        if self.expires_at <= self.requested_at:
            raise ValueError("operation expires_at must be greater than requested_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation_id": self.operation_id,
            "operation_kind": self.operation_kind,
            "input_hashes": self.input_hashes,
            "dependency_operation_ids": self.dependency_operation_ids,
            "expected_output_hash": self.expected_output_hash,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "operation_hash": self.operation_hash,
        }


@dataclass(frozen=True)
class AsyncIOOrchestrationPlan:
    schema_version: str
    plan_id: str
    operations: tuple[AsyncIOOperationEnvelope, ...]
    ordering_policy: str
    max_operations: int
    max_ready_operations: int
    retry_policy: str
    created_at: int
    expires_at: int
    plan_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "plan_id", _identifier("plan_id", self.plan_id))
        object.__setattr__(self, "operations", _operation_tuple(self.operations))
        object.__setattr__(self, "ordering_policy", _required_text("ordering_policy", self.ordering_policy).casefold())
        object.__setattr__(self, "max_operations", _positive_int("max_operations", self.max_operations))
        object.__setattr__(self, "max_ready_operations", _positive_int("max_ready_operations", self.max_ready_operations))
        object.__setattr__(self, "retry_policy", _required_text("retry_policy", self.retry_policy).casefold())
        object.__setattr__(self, "created_at", _nonnegative_int("created_at", self.created_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "plan_hash", _required_hash("plan_hash", self.plan_hash))
        if self.schema_version != ASYNC_IO_ORCHESTRATION_PLAN_SCHEMA_VERSION:
            raise ValueError("unsupported async I/O orchestration plan schema version")
        if self.expires_at <= self.created_at:
            raise ValueError("plan expires_at must be greater than created_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "operations": tuple(operation.to_dict() for operation in self.operations),
            "ordering_policy": self.ordering_policy,
            "max_operations": self.max_operations,
            "max_ready_operations": self.max_ready_operations,
            "retry_policy": self.retry_policy,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True)
class AsyncIOOrchestrationReviewResult:
    schema_version: str
    ok: bool
    blocked: bool
    execution_allowed: bool
    dispatch_allowed: bool
    retry_allowed: bool
    fallback_allowed: bool
    streaming_allowed: bool
    requires_human_review: bool
    requires_controlled_path: bool
    plan_hash: str | None
    completed_operation_ids: tuple[str, ...]
    ready_operation_ids: tuple[str, ...]
    blocked_operation_ids: tuple[str, ...]
    ordered_operation_ids: tuple[str, ...]
    dependency_edges: tuple[tuple[str, str], ...]
    orchestration_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    review_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
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
    operation_executed: bool = False
    tool_call_invoked: bool = False
    provider_called: bool = False
    mcp_called: bool = False
    process_started: bool = False
    network_called: bool = False
    browser_opened: bool = False
    package_manager_called: bool = False
    git_action_performed: bool = False
    retry_started: bool = False
    fallback_started: bool = False
    streaming_started: bool = False
    agent_loop_started: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "ok", bool(self.ok) and not bool(self.blocked))
        object.__setattr__(self, "blocked", bool(self.blocked))
        object.__setattr__(self, "execution_allowed", False)
        object.__setattr__(self, "dispatch_allowed", False)
        object.__setattr__(self, "retry_allowed", False)
        object.__setattr__(self, "fallback_allowed", False)
        object.__setattr__(self, "streaming_allowed", False)
        object.__setattr__(self, "requires_human_review", True)
        object.__setattr__(self, "requires_controlled_path", True)
        if self.plan_hash is not None:
            object.__setattr__(self, "plan_hash", _required_hash("plan_hash", self.plan_hash))
        object.__setattr__(self, "completed_operation_ids", _identifier_tuple("completed_operation_ids", self.completed_operation_ids, allow_empty=True))
        object.__setattr__(self, "ready_operation_ids", _identifier_tuple("ready_operation_ids", self.ready_operation_ids, allow_empty=True))
        object.__setattr__(self, "blocked_operation_ids", _identifier_tuple("blocked_operation_ids", self.blocked_operation_ids, allow_empty=True))
        object.__setattr__(self, "ordered_operation_ids", _identifier_tuple("ordered_operation_ids", self.ordered_operation_ids, allow_empty=True))
        object.__setattr__(self, "dependency_edges", tuple((str(dep), str(op)) for dep, op in self.dependency_edges))
        object.__setattr__(self, "orchestration_codes", tuple(sorted(set(_required_text("orchestration_codes", item) for item in self.orchestration_codes))))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(_required_text("reason_codes", item) for item in self.reason_codes))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))
        for field_name in _REVIEW_FALSE_FLAGS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION,
            "ok": self.ok,
            "blocked": self.blocked,
            "execution_allowed": False,
            "dispatch_allowed": False,
            "retry_allowed": False,
            "fallback_allowed": False,
            "streaming_allowed": False,
            "requires_human_review": True,
            "requires_controlled_path": True,
            "plan_hash": self.plan_hash,
            "completed_operation_ids": self.completed_operation_ids,
            "ready_operation_ids": self.ready_operation_ids,
            "blocked_operation_ids": self.blocked_operation_ids,
            "ordered_operation_ids": self.ordered_operation_ids,
            "dependency_edges": self.dependency_edges,
            "orchestration_codes": self.orchestration_codes,
            "reason_codes": self.reason_codes,
            "review_hash": self.review_hash,
        }
        for field_name in _REVIEW_FALSE_FLAGS:
            data[field_name] = False
        return data


_REVIEW_FALSE_FLAGS = (
    "gate_satisfied",
    "human_barrier_satisfied",
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
    "operation_executed",
    "tool_call_invoked",
    "provider_called",
    "mcp_called",
    "process_started",
    "network_called",
    "browser_opened",
    "package_manager_called",
    "git_action_performed",
    "retry_started",
    "fallback_started",
    "streaming_started",
    "agent_loop_started",
)


def canonical_async_io_orchestration_json(value: Any) -> str:
    return json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_async_io_orchestration_value(value: Any) -> str:
    return hashlib.sha256(canonical_async_io_orchestration_json(value).encode("utf-8")).hexdigest()


def build_async_io_operation_envelope(
    *,
    operation_id: str,
    operation_kind: str,
    input_hashes: tuple[str, ...],
    dependency_operation_ids: tuple[str, ...],
    expected_output_hash: str | None,
    requested_by: str,
    requested_at: int,
    expires_at: int,
) -> AsyncIOOperationEnvelope:
    material = {
        "schema_version": ASYNC_IO_OPERATION_SCHEMA_VERSION,
        "operation_id": _identifier("operation_id", operation_id),
        "operation_kind": _required_text("operation_kind", operation_kind).casefold(),
        "input_hashes": _hash_tuple("input_hashes", input_hashes, allow_empty=True),
        "dependency_operation_ids": _identifier_tuple("dependency_operation_ids", dependency_operation_ids, allow_empty=True),
        "expected_output_hash": _optional_hash("expected_output_hash", expected_output_hash),
        "requested_by": _required_text("requested_by", requested_by),
        "requested_at": _nonnegative_int("requested_at", requested_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return AsyncIOOperationEnvelope(**material, operation_hash=_operation_hash(material))


def build_async_io_orchestration_plan(
    *,
    plan_id: str,
    operations: tuple[AsyncIOOperationEnvelope, ...],
    ordering_policy: str = "dependency_topological",
    max_operations: int = 50,
    max_ready_operations: int = 10,
    retry_policy: str = "none",
    created_at: int,
    expires_at: int,
) -> AsyncIOOrchestrationPlan:
    operation_tuple = _operation_tuple(operations)
    material = {
        "schema_version": ASYNC_IO_ORCHESTRATION_PLAN_SCHEMA_VERSION,
        "plan_id": _identifier("plan_id", plan_id),
        "operations": tuple(operation.operation_hash for operation in operation_tuple),
        "ordering_policy": _required_text("ordering_policy", ordering_policy).casefold(),
        "max_operations": _positive_int("max_operations", max_operations),
        "max_ready_operations": _positive_int("max_ready_operations", max_ready_operations),
        "retry_policy": _required_text("retry_policy", retry_policy).casefold(),
        "created_at": _nonnegative_int("created_at", created_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return AsyncIOOrchestrationPlan(
        schema_version=ASYNC_IO_ORCHESTRATION_PLAN_SCHEMA_VERSION,
        plan_id=material["plan_id"],
        operations=operation_tuple,
        ordering_policy=material["ordering_policy"],
        max_operations=material["max_operations"],
        max_ready_operations=material["max_ready_operations"],
        retry_policy=material["retry_policy"],
        created_at=material["created_at"],
        expires_at=material["expires_at"],
        plan_hash=_plan_hash(material),
    )


def evaluate_async_io_orchestration(
    *,
    plan: AsyncIOOrchestrationPlan,
    completed_operation_ids: tuple[str, ...] = (),
    now: int,
) -> AsyncIOOrchestrationReviewResult:
    reason_codes: list[str] = []
    try:
        now_value = _nonnegative_int("now", now)
    except (TypeError, ValueError):
        return _blocked((ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME,))

    try:
        raw_plan = _coerce_mapping(plan)
        input_fingerprint = _json_fingerprint(raw_plan)
    except TypeError:
        return _blocked((ASYNC_IO_ORCHESTRATION_BLOCKED_NON_JSON_SERIALIZABLE,))

    reason_codes.extend(_danger_reason_codes(raw_plan))
    if _contains_unknown_fields(raw_plan):
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_AMBIGUOUS_EVIDENCE)
    if _invalid_hash_evidence_present(raw_plan):
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH)
    if _invalid_time_evidence_present(raw_plan):
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME)

    try:
        completed_ids = _identifier_tuple("completed_operation_ids", completed_operation_ids, allow_empty=True)
    except (TypeError, ValueError):
        return _blocked((ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION,))
    if len(set(completed_ids)) != len(completed_ids):
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_COMPLETED_ID)
    completed_set = frozenset(completed_ids)

    try:
        coerced_plan = _coerce_plan(raw_plan)
    except (TypeError, ValueError):
        return _blocked(
            tuple(reason_codes or (ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION,)),
            input_fingerprint=input_fingerprint,
        )

    operations = coerced_plan.operations
    operation_ids = tuple(operation.operation_id for operation in operations)
    operation_id_set = frozenset(operation_ids)
    operation_by_id = {operation.operation_id: operation for operation in operations}

    if len(operation_id_set) != len(operation_ids):
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_OPERATION_ID)
    if len(operations) > coerced_plan.max_operations:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_OPERATIONS)
    if coerced_plan.ordering_policy not in SUPPORTED_ORDERING_POLICIES:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_ORDERING_POLICY)
    if coerced_plan.retry_policy not in SUPPORTED_RETRY_POLICIES:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_RETRY_POLICY)
    if now_value < coerced_plan.created_at:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME)
    if now_value > coerced_plan.expires_at:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_PLAN)

    expected_plan_hash = _plan_hash(_plan_hash_material(coerced_plan))
    if coerced_plan.plan_hash != expected_plan_hash:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH)

    for operation in operations:
        if operation.operation_kind not in SUPPORTED_ASYNC_IO_OPERATION_KINDS:
            reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION_KIND)
        if len(set(operation.dependency_operation_ids)) != len(operation.dependency_operation_ids):
            reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_DEPENDENCY_ID)
        if any(dependency_id not in operation_id_set for dependency_id in operation.dependency_operation_ids):
            reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_MISSING_DEPENDENCY)
        if now_value < operation.requested_at:
            reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME)
        if now_value > operation.expires_at:
            reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_OPERATION)
        if operation.operation_hash != _operation_hash(_operation_hash_material(operation)):
            reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH)

    if any(completed_id not in operation_id_set for completed_id in completed_ids):
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_UNKNOWN_COMPLETED_ID)

    dependency_edges = tuple(
        sorted(
            (dependency_id, operation.operation_id)
            for operation in operations
            for dependency_id in operation.dependency_operation_ids
        )
    )
    cycle_detected, topological_order = _topological_order(operations)
    if cycle_detected:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_DEPENDENCY_CYCLE)

    ready_ids = tuple(
        sorted(
            operation.operation_id
            for operation in operations
            if operation.operation_id not in completed_set
            and all(dependency_id in completed_set for dependency_id in operation.dependency_operation_ids)
        )
    )
    blocked_ids = tuple(
        sorted(
            operation.operation_id
            for operation in operations
            if operation.operation_id not in completed_set
            and any(dependency_id not in completed_set for dependency_id in operation.dependency_operation_ids)
        )
    )
    if len(ready_ids) > coerced_plan.max_ready_operations:
        reason_codes.append(ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_READY_OPERATIONS)

    ordered_ids = _ordered_operation_ids(coerced_plan.ordering_policy, operations, topological_order, blocked_ids)
    orchestration_codes = _orchestration_codes(ready_ids=ready_ids, blocked_ids=blocked_ids, ordered_ids=ordered_ids)
    blocked = bool(set(reason_codes) - {ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW_REASON, ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH_REASON})
    if blocked:
        reason_codes = sorted(set(reason_codes))
    else:
        reason_codes = sorted(
            {
                ASYNC_IO_ORCHESTRATION_OK,
                ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW_REASON,
                ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH_REASON,
            }
        )

    material = {
        "schema_version": ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION,
        "ok": not blocked,
        "blocked": blocked,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "plan_hash": coerced_plan.plan_hash,
        "completed_operation_ids": tuple(sorted(completed_ids)),
        "ready_operation_ids": ready_ids,
        "blocked_operation_ids": blocked_ids,
        "ordered_operation_ids": ordered_ids,
        "dependency_edges": dependency_edges,
        "orchestration_codes": tuple(sorted(set(orchestration_codes))),
        "reason_codes": tuple(reason_codes),
        "input_fingerprint": input_fingerprint,
    }
    return AsyncIOOrchestrationReviewResult(
        schema_version=ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION,
        ok=not blocked,
        blocked=blocked,
        execution_allowed=False,
        dispatch_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        plan_hash=coerced_plan.plan_hash,
        completed_operation_ids=tuple(sorted(completed_ids)),
        ready_operation_ids=ready_ids,
        blocked_operation_ids=blocked_ids,
        ordered_operation_ids=ordered_ids,
        dependency_edges=dependency_edges,
        orchestration_codes=tuple(orchestration_codes),
        reason_codes=tuple(reason_codes),
        review_hash=hash_async_io_orchestration_value(material),
    )


def _operation_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("operation_hash", None)
    return hash_async_io_orchestration_value(_json_fingerprint(data))


def _plan_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("plan_hash", None)
    return hash_async_io_orchestration_value(_json_fingerprint(data))


def _operation_hash_material(operation: AsyncIOOperationEnvelope) -> dict[str, Any]:
    data = operation.to_dict()
    data.pop("operation_hash", None)
    return data


def _plan_hash_material(plan: AsyncIOOrchestrationPlan) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "plan_id": plan.plan_id,
        "operations": tuple(operation.operation_hash for operation in plan.operations),
        "ordering_policy": plan.ordering_policy,
        "max_operations": plan.max_operations,
        "max_ready_operations": plan.max_ready_operations,
        "retry_policy": plan.retry_policy,
        "created_at": plan.created_at,
        "expires_at": plan.expires_at,
    }


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> AsyncIOOrchestrationReviewResult:
    codes = tuple(sorted(set(reason_codes)))
    material = {
        "schema_version": ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION,
        "ok": False,
        "blocked": True,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "retry_allowed": False,
        "fallback_allowed": False,
        "streaming_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "plan_hash": None,
        "completed_operation_ids": (),
        "ready_operation_ids": (),
        "blocked_operation_ids": (),
        "ordered_operation_ids": (),
        "dependency_edges": (),
        "orchestration_codes": (
            ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW,
            ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH,
            ASYNC_IO_ORCHESTRATION_NON_AUTHORITY,
        ),
        "reason_codes": codes,
        "input_fingerprint": input_fingerprint,
    }
    return AsyncIOOrchestrationReviewResult(
        schema_version=ASYNC_IO_ORCHESTRATION_REVIEW_SCHEMA_VERSION,
        ok=False,
        blocked=True,
        execution_allowed=False,
        dispatch_allowed=False,
        retry_allowed=False,
        fallback_allowed=False,
        streaming_allowed=False,
        requires_human_review=True,
        requires_controlled_path=True,
        plan_hash=None,
        completed_operation_ids=(),
        ready_operation_ids=(),
        blocked_operation_ids=(),
        ordered_operation_ids=(),
        dependency_edges=(),
        orchestration_codes=material["orchestration_codes"],
        reason_codes=codes,
        review_hash=hash_async_io_orchestration_value(material),
    )


def _coerce_plan(value: object) -> AsyncIOOrchestrationPlan:
    if isinstance(value, AsyncIOOrchestrationPlan):
        return value
    if isinstance(value, Mapping):
        data = _sanitize_mapping(value, _ALLOWED_PLAN_FIELDS)
        operations = data.get("operations")
        if not isinstance(operations, (tuple, list)) or not operations:
            raise TypeError("operations must be a non-empty sequence")
        data["operations"] = tuple(_coerce_operation(item) for item in operations)
        return AsyncIOOrchestrationPlan(**data)
    raise TypeError("async I/O orchestration plan is required")


def _coerce_operation(value: object) -> AsyncIOOperationEnvelope:
    if isinstance(value, AsyncIOOperationEnvelope):
        return value
    if isinstance(value, Mapping):
        return AsyncIOOperationEnvelope(**_sanitize_mapping(value, _ALLOWED_OPERATION_FIELDS))
    raise TypeError("async I/O operation envelope is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("async I/O orchestration evidence must be mapping evidence")


def _sanitize_mapping(value: Mapping[str, Any], allowed_fields: frozenset[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key in allowed_fields}


def _operation_tuple(value: object) -> tuple[AsyncIOOperationEnvelope, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError("operations must be a non-empty sequence")
    return tuple(_coerce_operation(item) for item in value)


def _contains_unknown_fields(raw_plan: Mapping[str, Any]) -> bool:
    if any(key not in _ALLOWED_PLAN_FIELDS for key in raw_plan):
        return True
    operations = raw_plan.get("operations")
    if isinstance(operations, (tuple, list)):
        return any(isinstance(operation, Mapping) and any(key not in _ALLOWED_OPERATION_FIELDS for key in operation) for operation in operations)
    return False


def _danger_reason_codes(value: object) -> list[str]:
    codes: set[str] = set()
    for key, text in _scanned_text_items(value):
        normalized = text.casefold()
        normalized_key = key.casefold()
        if normalized_key in _AUTHORITY_FIELD_NAMES or any(term in normalized for term in _AUTHORITY_FIELD_NAMES):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_AUTHORITY_CLAIM)
        if any(term.casefold() in normalized for term in _COMMAND_INJECTION_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_COMMAND_INJECTION)
        if any(term in normalized for term in _PROVIDER_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_PROVIDER_CALL)
        if any(term in normalized for term in _GIT_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_GIT_ACTION)
        if any(term in normalized for term in _PACKAGE_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_PACKAGE_INSTALL)
        if any(term in normalized for term in _BROWSER_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_BROWSER_ACTION)
        if any(term in normalized for term in _MCP_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_MCP_TOOL)
        if any(term in normalized for term in _CODEX_AIDER_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_CODEX_AIDER)
        if any(term in normalized for term in _AGENT_LOOP_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_AGENT_LOOP)
        if any(term in normalized for term in _ENV_SECRET_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_ENV_OR_SECRET)
        if any(term in normalized for term in _CONTROL_TERMS):
            codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_AUTHORITY_CLAIM)
    return sorted(codes)


def _scanned_text_items(value: object, *, parent_key: str = "") -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            if key not in _TEXT_SCAN_SKIP_KEYS:
                items.append((key, key))
            if key not in _TEXT_SCAN_SKIP_KEYS:
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


def _invalid_hash_evidence_present(value: Mapping[str, Any]) -> bool:
    if "plan_hash" in value and not _sha256_like(value["plan_hash"]):
        return True
    operations = value.get("operations")
    if not isinstance(operations, (tuple, list)):
        return True
    for operation in operations:
        operation_data = _coerce_mapping_if_possible(operation)
        if operation_data is None:
            return True
        for field_name in ("operation_hash",):
            if field_name in operation_data and not _sha256_like(operation_data[field_name]):
                return True
        input_hashes = operation_data.get("input_hashes")
        if not isinstance(input_hashes, (tuple, list)):
            return True
        if any(not _sha256_like(item) for item in input_hashes):
            return True
        expected = operation_data.get("expected_output_hash")
        if expected is not None and not _sha256_like(expected):
            return True
    return False


def _invalid_time_evidence_present(value: Mapping[str, Any]) -> bool:
    created_at = value.get("created_at")
    expires_at = value.get("expires_at")
    if not _valid_nonnegative_int(created_at) or not _valid_nonnegative_int(expires_at):
        return True
    if expires_at <= created_at:
        return True
    operations = value.get("operations")
    if not isinstance(operations, (tuple, list)):
        return True
    for operation in operations:
        operation_data = _coerce_mapping_if_possible(operation)
        if operation_data is None:
            return True
        requested_at = operation_data.get("requested_at")
        operation_expires_at = operation_data.get("expires_at")
        if not _valid_nonnegative_int(requested_at) or not _valid_nonnegative_int(operation_expires_at):
            return True
        if operation_expires_at <= requested_at:
            return True
    return False


def _coerce_mapping_if_possible(value: object) -> dict[str, Any] | None:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    return None


def _topological_order(operations: tuple[AsyncIOOperationEnvelope, ...]) -> tuple[bool, tuple[str, ...]]:
    operation_ids = frozenset(operation.operation_id for operation in operations)
    incoming = {operation.operation_id: set(operation.dependency_operation_ids) & operation_ids for operation in operations}
    outgoing: dict[str, set[str]] = {operation.operation_id: set() for operation in operations}
    for operation in operations:
        for dependency_id in operation.dependency_operation_ids:
            if dependency_id in outgoing:
                outgoing[dependency_id].add(operation.operation_id)

    ready = sorted(operation_id for operation_id, dependencies in incoming.items() if not dependencies)
    ordered: list[str] = []
    while ready:
        operation_id = ready.pop(0)
        ordered.append(operation_id)
        for dependent_id in sorted(outgoing[operation_id]):
            incoming[dependent_id].discard(operation_id)
            if not incoming[dependent_id] and dependent_id not in ordered and dependent_id not in ready:
                ready.append(dependent_id)
        ready.sort()
    return len(ordered) != len(operation_ids), tuple(ordered)


def _ordered_operation_ids(
    ordering_policy: str,
    operations: tuple[AsyncIOOperationEnvelope, ...],
    topological_order: tuple[str, ...],
    blocked_ids: tuple[str, ...],
) -> tuple[str, ...]:
    if ordering_policy == "dependency_topological":
        return topological_order
    if ordering_policy == "declaration_order":
        return tuple(operation.operation_id for operation in operations)
    if ordering_policy == "blocked_only_review":
        return blocked_ids
    return ()


def _orchestration_codes(*, ready_ids: tuple[str, ...], blocked_ids: tuple[str, ...], ordered_ids: tuple[str, ...]) -> tuple[str, ...]:
    codes = {
        ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW,
        ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH,
        ASYNC_IO_ORCHESTRATION_NON_AUTHORITY,
    }
    if ready_ids:
        codes.add(ASYNC_IO_ORCHESTRATION_READY_METADATA)
    if blocked_ids:
        codes.add(ASYNC_IO_ORCHESTRATION_BLOCKED_BY_DEPENDENCY)
    if ordered_ids:
        codes.add(ASYNC_IO_ORCHESTRATION_DEPENDENCY_ORDERED)
    return tuple(sorted(codes))


def _identifier(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError(f"{name} must be a stable identifier")
    return text


def _identifier_tuple(name: str, value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    if not value and not allow_empty:
        raise TypeError(f"{name} must not be empty")
    return tuple(_identifier(name, item) for item in value)


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


def _positive_int(name: str, value: object) -> int:
    integer = _nonnegative_int(name, value)
    if integer <= 0:
        raise ValueError(f"{name} must be positive")
    return integer


def _valid_nonnegative_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.casefold())


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("async I/O orchestration evidence is too deeply nested")
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
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
            if not isinstance(key, str) or not key.strip():
                raise TypeError("mapping evidence keys must be non-empty text")
            normalized[key.strip()] = _json_fingerprint(item, depth=depth + 1)
        return normalized
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("sequence evidence is excessive")
        return tuple(_json_fingerprint(item, depth=depth + 1) for item in value)
    raise TypeError("async I/O orchestration evidence must be JSON serializable")
