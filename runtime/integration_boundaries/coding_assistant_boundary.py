from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


CODING_ASSISTANT_CAPABILITY_SCHEMA_VERSION = "AOIA_CODING_ASSISTANT_CAPABILITY_1A"
CODING_ASSISTANT_REQUEST_SCHEMA_VERSION = "AOIA_CODING_ASSISTANT_REQUEST_1A"
CODING_ASSISTANT_OUTPUT_SCHEMA_VERSION = "AOIA_CODING_ASSISTANT_OUTPUT_1A"
CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION = "AOIA_CODING_ASSISTANT_BOUNDARY_REVIEW_1A"

CODING_ASSISTANT_BOUNDARY_READY_METADATA_ONLY = "CODING_ASSISTANT_BOUNDARY_READY_METADATA_ONLY"
CODING_ASSISTANT_BOUNDARY_BLOCKED = "CODING_ASSISTANT_BOUNDARY_BLOCKED"

CODING_ASSISTANT_BOUNDARY_REASON_READY_METADATA_ONLY = "CODING_ASSISTANT_BOUNDARY_REASON_READY_METADATA_ONLY"
CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE = "CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE"
CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD = "CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD"
CODING_ASSISTANT_BOUNDARY_BLOCKED_UNSUPPORTED_ASSISTANT = "CODING_ASSISTANT_BOUNDARY_BLOCKED_UNSUPPORTED_ASSISTANT"
CODING_ASSISTANT_BOUNDARY_BLOCKED_UNSUPPORTED_CAPABILITY = "CODING_ASSISTANT_BOUNDARY_BLOCKED_UNSUPPORTED_CAPABILITY"
CODING_ASSISTANT_BOUNDARY_BLOCKED_POLICY_CAPABILITY = "CODING_ASSISTANT_BOUNDARY_BLOCKED_POLICY_CAPABILITY"
CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH = "CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH"
CODING_ASSISTANT_BOUNDARY_BLOCKED_STALE_EVIDENCE = "CODING_ASSISTANT_BOUNDARY_BLOCKED_STALE_EVIDENCE"
CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTHORITY_CLAIM = "CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTHORITY_CLAIM"
CODING_ASSISTANT_BOUNDARY_BLOCKED_EFFECT_EVIDENCE = "CODING_ASSISTANT_BOUNDARY_BLOCKED_EFFECT_EVIDENCE"
CODING_ASSISTANT_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE = "CODING_ASSISTANT_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE"
CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE = "CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE"
CODING_ASSISTANT_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE = "CODING_ASSISTANT_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE"

CODING_ASSISTANT_BOUNDARY_RISK_LOW = "LOW"
CODING_ASSISTANT_BOUNDARY_RISK_MEDIUM = "MEDIUM"
CODING_ASSISTANT_BOUNDARY_RISK_HIGH = "HIGH"
CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED = "BLOCKED"

SUPPORTED_CODING_ASSISTANT_KINDS = frozenset({"aider", "codex", "other"})
SUPPORTED_OUTPUT_KINDS = frozenset({"explanation", "patch_proposal_metadata", "review_notes", "test_plan_metadata"})
METADATA_ONLY_CAPABILITIES = frozenset(
    {
        "classify_risk",
        "emit_review_notes",
        "explain_code",
        "propose_patch_metadata",
        "propose_tests_metadata",
        "read_context_metadata",
        "summarize_findings",
    }
)
MEDIUM_RISK_CAPABILITIES = frozenset({"propose_patch_metadata", "propose_tests_metadata"})
FORBIDDEN_CODING_ASSISTANT_CAPABILITIES = frozenset(
    {
        "agent_loop",
        "aider_live_flow",
        "apply_patch",
        "browser_automation",
        "codex_live_flow",
        "dispatcher",
        "fallback",
        "git_operation",
        "invoke_aider",
        "invoke_codex",
        "invoke_coding_agent_cli",
        "mcp",
        "package_install",
        "provider_call",
        "repo_write",
        "retry",
        "shell",
        "streaming",
        "subprocess",
        "tool_call",
    }
)
_SUPPORTED_CAPABILITIES = METADATA_ONLY_CAPABILITIES | FORBIDDEN_CODING_ASSISTANT_CAPABILITIES
_REQUIRED_FUTURE_EVIDENCE = (
    "exact_request_hash",
    "exact_output_hash",
    "exact_capability_declaration_hash",
    "exact_boundary_review_hash",
    "explicit_hash_bound_human_approval",
    "separate_controlled_patch_or_execution_path",
)
_ALLOWED_DECLARATION_FIELDS = frozenset(
    {
        "schema_version",
        "assistant_kind",
        "requested_capabilities",
        "forbidden_capabilities",
        "declared_limitations",
        "declaration_hash",
    }
)
_ALLOWED_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "assistant_kind",
        "objective",
        "target_refs",
        "context_hashes",
        "capability_declaration_hash",
        "requested_by",
        "created_at_tick",
        "expires_at_tick",
        "metadata",
        "request_hash",
    }
)
_ALLOWED_OUTPUT_FIELDS = frozenset(
    {
        "schema_version",
        "output_id",
        "assistant_kind",
        "request_hash",
        "capability_declaration_hash",
        "output_kind",
        "output_text",
        "output_artifact_hash",
        "generated_at_tick",
        "expires_at_tick",
        "metadata",
        "output_hash",
    }
)
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "authority",
        "authority_granted",
        "human_approved",
        "agent_allowed",
        "boundary_passed",
        "can_apply",
        "can_commit",
        "can_execute",
        "can_push",
        "can_write",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "human_barrier_satisfied",
        "execution_allowed",
        "apply_allowed",
    }
)
_EFFECT_FIELD_NAMES = frozenset(
    {
        "codex_run",
        "aider_run",
        "coding_agent_cli_called",
        "process_started",
        "shell_called",
        "git_action_performed",
        "package_manager_called",
        "browser_automation_started",
        "browser_opened",
        "provider_called",
        "mcp_called",
        "tool_call_invoked",
        "patch_applied",
        "repo_file_written",
        "dispatcher_created",
        "agent_loop_started",
        "streaming_started",
        "retry_started",
        "fallback_started",
        "approval_created",
    }
)
_DANGEROUS_FIELD_NAMES = frozenset(
    {
        "command",
        "commands",
        "shell",
        "script",
        "javascript",
        "js",
        "subprocess",
        "process",
        "cli",
        "tool",
        "tools",
        "dispatcher",
        "agent_loop",
        "mcp",
        "provider",
        "network",
        "http",
        "url",
        "endpoint",
        "headers",
        "token",
        "secret",
        "env",
        "api" + "_key",
        "patch_file",
        "write_path",
        "commit",
        "push",
    }
)
_AUTONOMOUS_FIELD_NAMES = frozenset({"auto_apply", "auto_commit", "auto_push", "autonomous", "retry", "fallback", "loop"})
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 4096
_MAX_SHORT_TEXT = 1024
_MAX_COLLECTION_ITEMS = 64
_MAX_DEPTH = 6
_EXECUTABLE_TEXT_PATTERN = re.compile(
    r"(?i)(?:\b(?:codex|aider)\s+(?:run|apply|exec|edit|commit|push)\b|"
    r"\b(?:curl|wget|bash|sh|sudo|powershell|cmd\.exe)\b|"
    r"\b(?:python\s+-m|pip|npm|apt|git)\s+\w+\b|"
    r"\b(?:eval|exec|compile|importlib|os\.system|subprocess)\b|"
    r"(?:;|&&|\|\||`|\$\(|<\(|>\(|\n))"
)
_AUTHORITY_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"safe\s+to\s+(?:apply|execute|commit|push|write)|can\s+(?:apply|execute|commit|push|write)|"
    r"agent\s+allowed|gate\s+satisfied|authority\s+granted)\b"
)


@dataclass(frozen=True)
class CodingAssistantCapabilityDeclaration:
    schema_version: str
    assistant_kind: str
    requested_capabilities: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]
    declared_limitations: tuple[str, ...]
    declaration_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "assistant_kind", _required_text("assistant_kind", self.assistant_kind).casefold())
        object.__setattr__(self, "requested_capabilities", _text_tuple("requested_capabilities", self.requested_capabilities))
        object.__setattr__(self, "forbidden_capabilities", _text_tuple("forbidden_capabilities", self.forbidden_capabilities))
        object.__setattr__(self, "declared_limitations", _raw_text_tuple("declared_limitations", self.declared_limitations))
        object.__setattr__(self, "declaration_hash", _required_hash("declaration_hash", self.declaration_hash))
        if self.schema_version != CODING_ASSISTANT_CAPABILITY_SCHEMA_VERSION:
            raise ValueError("unsupported coding assistant capability declaration schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assistant_kind": self.assistant_kind,
            "requested_capabilities": self.requested_capabilities,
            "forbidden_capabilities": self.forbidden_capabilities,
            "declared_limitations": self.declared_limitations,
            "declaration_hash": self.declaration_hash,
        }


@dataclass(frozen=True)
class CodingAssistantRequestEnvelope:
    schema_version: str
    request_id: str
    assistant_kind: str
    objective: str
    target_refs: tuple[str, ...]
    context_hashes: tuple[str, ...]
    capability_declaration_hash: str
    requested_by: str
    created_at_tick: int
    expires_at_tick: int
    metadata: Mapping[str, Any] | None
    request_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_apply: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    agent_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "request_id", _required_text("request_id", self.request_id))
        object.__setattr__(self, "assistant_kind", _required_text("assistant_kind", self.assistant_kind).casefold())
        object.__setattr__(self, "objective", _required_text("objective", self.objective))
        object.__setattr__(self, "target_refs", _raw_text_tuple("target_refs", self.target_refs))
        object.__setattr__(self, "context_hashes", _hash_tuple("context_hashes", self.context_hashes))
        object.__setattr__(self, "capability_declaration_hash", _required_hash("capability_declaration_hash", self.capability_declaration_hash))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "created_at_tick", _nonnegative_int("created_at_tick", self.created_at_tick))
        object.__setattr__(self, "expires_at_tick", _nonnegative_int("expires_at_tick", self.expires_at_tick))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        if self.schema_version != CODING_ASSISTANT_REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported coding assistant request envelope schema version")
        if self.expires_at_tick < self.created_at_tick:
            raise ValueError("coding assistant request TTL is inverted")
        for field_name in _REQUEST_AUTHORITY_FLAGS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "assistant_kind": self.assistant_kind,
            "objective": self.objective,
            "target_refs": self.target_refs,
            "context_hashes": self.context_hashes,
            "capability_declaration_hash": self.capability_declaration_hash,
            "requested_by": self.requested_by,
            "created_at_tick": self.created_at_tick,
            "expires_at_tick": self.expires_at_tick,
            "metadata": _json_fingerprint(self.metadata or {}),
            "request_hash": self.request_hash,
        }
        for field_name in _REQUEST_AUTHORITY_FLAGS:
            data[field_name] = False
        return data


@dataclass(frozen=True)
class CodingAssistantOutputEnvelope:
    schema_version: str
    output_id: str
    assistant_kind: str
    request_hash: str
    capability_declaration_hash: str
    output_kind: str
    output_text: str
    output_artifact_hash: str
    generated_at_tick: int
    expires_at_tick: int
    metadata: Mapping[str, Any] | None
    output_hash: str
    codex_run: bool = False
    aider_run: bool = False
    coding_agent_cli_called: bool = False
    process_started: bool = False
    shell_called: bool = False
    git_action_performed: bool = False
    package_manager_called: bool = False
    browser_automation_started: bool = False
    browser_opened: bool = False
    provider_called: bool = False
    mcp_called: bool = False
    tool_call_invoked: bool = False
    patch_applied: bool = False
    repo_file_written: bool = False
    dispatcher_created: bool = False
    agent_loop_started: bool = False
    streaming_started: bool = False
    retry_started: bool = False
    fallback_started: bool = False
    approval_created: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_apply: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    agent_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "output_id", _required_text("output_id", self.output_id))
        object.__setattr__(self, "assistant_kind", _required_text("assistant_kind", self.assistant_kind).casefold())
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        object.__setattr__(self, "capability_declaration_hash", _required_hash("capability_declaration_hash", self.capability_declaration_hash))
        object.__setattr__(self, "output_kind", _required_text("output_kind", self.output_kind).casefold())
        object.__setattr__(self, "output_text", _required_long_text("output_text", self.output_text))
        object.__setattr__(self, "output_artifact_hash", _required_hash("output_artifact_hash", self.output_artifact_hash))
        object.__setattr__(self, "generated_at_tick", _nonnegative_int("generated_at_tick", self.generated_at_tick))
        object.__setattr__(self, "expires_at_tick", _nonnegative_int("expires_at_tick", self.expires_at_tick))
        object.__setattr__(self, "output_hash", _required_hash("output_hash", self.output_hash))
        if self.schema_version != CODING_ASSISTANT_OUTPUT_SCHEMA_VERSION:
            raise ValueError("unsupported coding assistant output envelope schema version")
        if self.expires_at_tick < self.generated_at_tick:
            raise ValueError("coding assistant output TTL is inverted")
        for field_name in (*_EFFECT_FIELD_NAMES, *_REQUEST_AUTHORITY_FLAGS):
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "output_id": self.output_id,
            "assistant_kind": self.assistant_kind,
            "request_hash": self.request_hash,
            "capability_declaration_hash": self.capability_declaration_hash,
            "output_kind": self.output_kind,
            "output_text": self.output_text,
            "output_artifact_hash": self.output_artifact_hash,
            "generated_at_tick": self.generated_at_tick,
            "expires_at_tick": self.expires_at_tick,
            "metadata": _json_fingerprint(self.metadata or {}),
            "output_hash": self.output_hash,
        }
        for field_name in (*_EFFECT_FIELD_NAMES, *_REQUEST_AUTHORITY_FLAGS):
            data[field_name] = False
        return data


@dataclass(frozen=True)
class CodingAssistantBoundaryReviewResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    risk_tier: str
    assistant_kind: str | None
    request_hash: str | None
    output_hash: str | None
    declaration_hash: str | None
    requested_capabilities: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]
    required_future_evidence: tuple[str, ...]
    review_hash: str
    human_review_required: bool = True
    codex_run: bool = False
    aider_run: bool = False
    coding_agent_cli_called: bool = False
    process_started: bool = False
    shell_called: bool = False
    git_action_performed: bool = False
    package_manager_called: bool = False
    browser_automation_started: bool = False
    browser_opened: bool = False
    provider_called: bool = False
    mcp_called: bool = False
    tool_call_invoked: bool = False
    patch_applied: bool = False
    repo_file_written: bool = False
    dispatcher_created: bool = False
    agent_loop_started: bool = False
    streaming_started: bool = False
    retry_started: bool = False
    fallback_started: bool = False
    approval_created: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    boundary_passed: bool = False
    can_apply: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    agent_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "requested_capabilities", tuple(sorted(set(self.requested_capabilities))))
        object.__setattr__(self, "forbidden_capabilities", tuple(sorted(set(self.forbidden_capabilities))))
        object.__setattr__(self, "blocked_capabilities", tuple(sorted(set(self.blocked_capabilities))))
        object.__setattr__(self, "required_future_evidence", tuple(sorted(set(self.required_future_evidence))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))
        if self.status not in {CODING_ASSISTANT_BOUNDARY_READY_METADATA_ONLY, CODING_ASSISTANT_BOUNDARY_BLOCKED}:
            raise ValueError("unsupported coding assistant boundary review status")
        if self.risk_tier not in {
            CODING_ASSISTANT_BOUNDARY_RISK_LOW,
            CODING_ASSISTANT_BOUNDARY_RISK_MEDIUM,
            CODING_ASSISTANT_BOUNDARY_RISK_HIGH,
            CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED,
        }:
            raise ValueError("unsupported coding assistant boundary risk tier")
        object.__setattr__(self, "human_review_required", True)
        for field_name in (*_EFFECT_FIELD_NAMES, "boundary_passed", *_REQUEST_AUTHORITY_FLAGS):
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "risk_tier": self.risk_tier,
            "assistant_kind": self.assistant_kind,
            "request_hash": self.request_hash,
            "output_hash": self.output_hash,
            "declaration_hash": self.declaration_hash,
            "requested_capabilities": self.requested_capabilities,
            "forbidden_capabilities": self.forbidden_capabilities,
            "blocked_capabilities": self.blocked_capabilities,
            "required_future_evidence": self.required_future_evidence,
            "review_hash": self.review_hash,
            "human_review_required": True,
        }
        for field_name in (*_EFFECT_FIELD_NAMES, "boundary_passed", *_REQUEST_AUTHORITY_FLAGS):
            data[field_name] = False
        return data


_REQUEST_AUTHORITY_FLAGS = (
    "gate_satisfied",
    "human_barrier_satisfied",
    "can_apply",
    "can_execute",
    "can_commit",
    "can_push",
    "can_write",
    "can_call_provider",
    "can_change_gate",
    "agent_allowed",
)


def create_coding_assistant_capability_declaration(
    *,
    assistant_kind: str,
    requested_capabilities: tuple[str, ...],
    forbidden_capabilities: tuple[str, ...] = tuple(sorted(FORBIDDEN_CODING_ASSISTANT_CAPABILITIES)),
    declared_limitations: tuple[str, ...] = (
        "metadata_only",
        "no_cli_invocation",
        "no_patch_application",
        "no_repo_write",
        "no_dispatch",
    ),
) -> CodingAssistantCapabilityDeclaration:
    material = {
        "schema_version": CODING_ASSISTANT_CAPABILITY_SCHEMA_VERSION,
        "assistant_kind": _required_text("assistant_kind", assistant_kind).casefold(),
        "requested_capabilities": _text_tuple("requested_capabilities", requested_capabilities),
        "forbidden_capabilities": _text_tuple("forbidden_capabilities", forbidden_capabilities),
        "declared_limitations": _raw_text_tuple("declared_limitations", declared_limitations),
    }
    return CodingAssistantCapabilityDeclaration(**material, declaration_hash=compute_coding_assistant_declaration_hash(material))


def create_coding_assistant_request_envelope(
    *,
    request_id: str,
    assistant_kind: str,
    objective: str,
    target_refs: tuple[str, ...],
    context_hashes: tuple[str, ...],
    capability_declaration_hash: str,
    requested_by: str,
    created_at_tick: int,
    expires_at_tick: int,
    metadata: Mapping[str, Any] | None = None,
) -> CodingAssistantRequestEnvelope:
    material = {
        "schema_version": CODING_ASSISTANT_REQUEST_SCHEMA_VERSION,
        "request_id": _required_text("request_id", request_id),
        "assistant_kind": _required_text("assistant_kind", assistant_kind).casefold(),
        "objective": _required_text("objective", objective),
        "target_refs": _raw_text_tuple("target_refs", target_refs),
        "context_hashes": _hash_tuple("context_hashes", context_hashes),
        "capability_declaration_hash": _required_hash("capability_declaration_hash", capability_declaration_hash),
        "requested_by": _required_text("requested_by", requested_by),
        "created_at_tick": _nonnegative_int("created_at_tick", created_at_tick),
        "expires_at_tick": _nonnegative_int("expires_at_tick", expires_at_tick),
        "metadata": _json_fingerprint(metadata or {}),
    }
    return CodingAssistantRequestEnvelope(**material, request_hash=compute_coding_assistant_request_hash(material))


def create_coding_assistant_output_envelope(
    *,
    output_id: str,
    assistant_kind: str,
    request_hash: str,
    capability_declaration_hash: str,
    output_kind: str,
    output_text: str,
    generated_at_tick: int,
    expires_at_tick: int,
    metadata: Mapping[str, Any] | None = None,
) -> CodingAssistantOutputEnvelope:
    material = {
        "schema_version": CODING_ASSISTANT_OUTPUT_SCHEMA_VERSION,
        "output_id": _required_text("output_id", output_id),
        "assistant_kind": _required_text("assistant_kind", assistant_kind).casefold(),
        "request_hash": _required_hash("request_hash", request_hash),
        "capability_declaration_hash": _required_hash("capability_declaration_hash", capability_declaration_hash),
        "output_kind": _required_text("output_kind", output_kind).casefold(),
        "output_text": _required_long_text("output_text", output_text),
        "output_artifact_hash": compute_coding_assistant_output_artifact_hash(output_text),
        "generated_at_tick": _nonnegative_int("generated_at_tick", generated_at_tick),
        "expires_at_tick": _nonnegative_int("expires_at_tick", expires_at_tick),
        "metadata": _json_fingerprint(metadata or {}),
    }
    return CodingAssistantOutputEnvelope(**material, output_hash=compute_coding_assistant_output_hash(material))


def review_coding_assistant_boundary(
    *,
    capability_declaration: object,
    request_envelope: object,
    output_envelope: object,
    now_tick: object,
) -> CodingAssistantBoundaryReviewResult:
    reason_codes: list[str] = []
    try:
        tick = _nonnegative_int("now_tick", now_tick)
    except (TypeError, ValueError):
        return _blocked((CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE,))

    try:
        declaration_data = _coerce_mapping(capability_declaration)
        request_data = _coerce_mapping(request_envelope)
        output_data = _coerce_mapping(output_envelope)
        input_fingerprint = _json_fingerprint(
            {
                "capability_declaration": declaration_data,
                "request_envelope": request_data,
                "output_envelope": output_data,
            }
        )
    except TypeError:
        return _blocked((CODING_ASSISTANT_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE,))

    if any(field not in _ALLOWED_DECLARATION_FIELDS for field in declaration_data):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD)
    if any(field not in _ALLOWED_REQUEST_FIELDS and field not in _REQUEST_AUTHORITY_FLAGS for field in request_data):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD)
    if any(field not in _ALLOWED_OUTPUT_FIELDS and field not in _REQUEST_AUTHORITY_FLAGS and field not in _EFFECT_FIELD_NAMES for field in output_data):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD)

    try:
        declaration = _coerce_declaration(declaration_data)
        request = _coerce_request(request_data)
        output = _coerce_output(output_data)
    except (TypeError, ValueError):
        return _blocked(
            tuple(reason_codes or (CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE,)),
            input_fingerprint=input_fingerprint,
        )

    if declaration.assistant_kind not in SUPPORTED_CODING_ASSISTANT_KINDS:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_UNSUPPORTED_ASSISTANT)
    if request.assistant_kind != declaration.assistant_kind or output.assistant_kind != declaration.assistant_kind:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if output.output_kind not in SUPPORTED_OUTPUT_KINDS:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE)
    if tick < request.created_at_tick or tick > request.expires_at_tick:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_STALE_EVIDENCE)
    if tick < output.generated_at_tick or tick > output.expires_at_tick:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_STALE_EVIDENCE)

    if declaration.declaration_hash != compute_coding_assistant_declaration_hash(_declaration_hash_material(declaration)):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if request.request_hash != compute_coding_assistant_request_hash(_request_hash_material(request)):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if output.output_hash != compute_coding_assistant_output_hash(_output_hash_material(output)):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if output.output_artifact_hash != compute_coding_assistant_output_artifact_hash(output.output_text):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if request.capability_declaration_hash != declaration.declaration_hash:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if output.capability_declaration_hash != declaration.declaration_hash or output.request_hash != request.request_hash:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH)

    unsupported_capabilities = tuple(item for item in declaration.requested_capabilities if item not in _SUPPORTED_CAPABILITIES)
    blocked_capabilities = tuple(item for item in declaration.requested_capabilities if item in FORBIDDEN_CODING_ASSISTANT_CAPABILITIES)
    missing_forbidden = tuple(item for item in FORBIDDEN_CODING_ASSISTANT_CAPABILITIES if item not in declaration.forbidden_capabilities)
    if unsupported_capabilities:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_UNSUPPORTED_CAPABILITY)
    if blocked_capabilities or missing_forbidden:
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_POLICY_CAPABILITY)
    if _authority_claim_present(declaration_data) or _authority_claim_present(request_data) or _authority_claim_present(output_data):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTHORITY_CLAIM)
    if _effect_claim_present(output_data):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_EFFECT_EVIDENCE)
    if _has_key(declaration_data, _DANGEROUS_FIELD_NAMES) or _has_key(request_data, _DANGEROUS_FIELD_NAMES) or _has_key(output_data, _DANGEROUS_FIELD_NAMES):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE)
    if _has_executable_text(request_data) or _has_executable_text(output_data):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE)
    if _has_key(declaration_data, _AUTONOMOUS_FIELD_NAMES) or _has_key(request_data, _AUTONOMOUS_FIELD_NAMES) or _has_key(output_data, _AUTONOMOUS_FIELD_NAMES):
        reason_codes.append(CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE)

    if not reason_codes:
        reason_codes = [CODING_ASSISTANT_BOUNDARY_REASON_READY_METADATA_ONLY]
    status = CODING_ASSISTANT_BOUNDARY_READY_METADATA_ONLY
    if reason_codes != [CODING_ASSISTANT_BOUNDARY_REASON_READY_METADATA_ONLY]:
        status = CODING_ASSISTANT_BOUNDARY_BLOCKED
    risk_tier = _risk_tier(declaration.requested_capabilities, tuple((*blocked_capabilities, *unsupported_capabilities, *missing_forbidden)))
    material = {
        "schema_version": CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_tier": risk_tier,
        "assistant_kind": declaration.assistant_kind,
        "request_hash": request.request_hash,
        "output_hash": output.output_hash,
        "declaration_hash": declaration.declaration_hash,
        "requested_capabilities": declaration.requested_capabilities,
        "forbidden_capabilities": declaration.forbidden_capabilities,
        "blocked_capabilities": tuple(sorted(set((*blocked_capabilities, *unsupported_capabilities, *missing_forbidden)))),
        "required_future_evidence": _REQUIRED_FUTURE_EVIDENCE,
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
    }
    return CodingAssistantBoundaryReviewResult(
        schema_version=CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION,
        status=status,
        reason_codes=tuple(reason_codes),
        risk_tier=risk_tier,
        assistant_kind=declaration.assistant_kind,
        request_hash=request.request_hash,
        output_hash=output.output_hash,
        declaration_hash=declaration.declaration_hash,
        requested_capabilities=declaration.requested_capabilities,
        forbidden_capabilities=declaration.forbidden_capabilities,
        blocked_capabilities=tuple((*blocked_capabilities, *unsupported_capabilities, *missing_forbidden)),
        required_future_evidence=_REQUIRED_FUTURE_EVIDENCE,
        review_hash=_stable_hash(material),
    )


def compute_coding_assistant_declaration_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("declaration_hash", None)
    return _stable_hash(_json_fingerprint(data))


def compute_coding_assistant_request_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("request_hash", None)
    for field_name in _REQUEST_AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return _stable_hash(_json_fingerprint(data))


def compute_coding_assistant_output_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("output_hash", None)
    for field_name in (*_REQUEST_AUTHORITY_FLAGS, *_EFFECT_FIELD_NAMES):
        data.pop(field_name, None)
    return _stable_hash(_json_fingerprint(data))


def compute_coding_assistant_output_artifact_hash(output_text: str) -> str:
    return _stable_hash(_required_long_text("output_text", output_text))


def canonical_coding_assistant_boundary_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _declaration_hash_material(declaration: CodingAssistantCapabilityDeclaration) -> dict[str, Any]:
    data = declaration.to_dict()
    data.pop("declaration_hash", None)
    return data


def _request_hash_material(request: CodingAssistantRequestEnvelope) -> dict[str, Any]:
    data = request.to_dict()
    data.pop("request_hash", None)
    for field_name in _REQUEST_AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return data


def _output_hash_material(output: CodingAssistantOutputEnvelope) -> dict[str, Any]:
    data = output.to_dict()
    data.pop("output_hash", None)
    for field_name in (*_REQUEST_AUTHORITY_FLAGS, *_EFFECT_FIELD_NAMES):
        data.pop(field_name, None)
    return data


def _risk_tier(capabilities: tuple[str, ...], blocked: tuple[str, ...]) -> str:
    if blocked:
        return CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED
    if any(item in FORBIDDEN_CODING_ASSISTANT_CAPABILITIES for item in capabilities):
        return CODING_ASSISTANT_BOUNDARY_RISK_HIGH
    if any(item in MEDIUM_RISK_CAPABILITIES for item in capabilities):
        return CODING_ASSISTANT_BOUNDARY_RISK_MEDIUM
    return CODING_ASSISTANT_BOUNDARY_RISK_LOW


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> CodingAssistantBoundaryReviewResult:
    material = {
        "schema_version": CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION,
        "status": CODING_ASSISTANT_BOUNDARY_BLOCKED,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_tier": CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED,
        "required_future_evidence": _REQUIRED_FUTURE_EVIDENCE,
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
    }
    return CodingAssistantBoundaryReviewResult(
        schema_version=CODING_ASSISTANT_BOUNDARY_REVIEW_SCHEMA_VERSION,
        status=CODING_ASSISTANT_BOUNDARY_BLOCKED,
        reason_codes=reason_codes,
        risk_tier=CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED,
        assistant_kind=None,
        request_hash=None,
        output_hash=None,
        declaration_hash=None,
        requested_capabilities=(),
        forbidden_capabilities=(),
        blocked_capabilities=(),
        required_future_evidence=_REQUIRED_FUTURE_EVIDENCE,
        review_hash=_stable_hash(material),
    )


def _coerce_declaration(value: object) -> CodingAssistantCapabilityDeclaration:
    if isinstance(value, CodingAssistantCapabilityDeclaration):
        return value
    if isinstance(value, Mapping):
        return CodingAssistantCapabilityDeclaration(**dict(value))
    raise TypeError("coding assistant capability declaration is required")


def _coerce_request(value: object) -> CodingAssistantRequestEnvelope:
    if isinstance(value, CodingAssistantRequestEnvelope):
        return value
    if isinstance(value, Mapping):
        return CodingAssistantRequestEnvelope(**dict(value))
    raise TypeError("coding assistant request envelope is required")


def _coerce_output(value: object) -> CodingAssistantOutputEnvelope:
    if isinstance(value, CodingAssistantOutputEnvelope):
        return value
    if isinstance(value, Mapping):
        return CodingAssistantOutputEnvelope(**dict(value))
    raise TypeError("coding assistant output envelope is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("coding assistant boundary evidence must be mapping evidence")


def _authority_claim_present(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in _AUTHORITY_FIELD_NAMES and item is not False:
                return True
            if _authority_claim_present(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_authority_claim_present(item) for item in value)
    return False


def _effect_claim_present(value: Mapping[str, Any]) -> bool:
    return any(value.get(field_name) is True for field_name in _EFFECT_FIELD_NAMES)


def _has_key(value: object, names: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in names:
                return True
            if _has_key(item, names):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_has_key(item, names) for item in value)
    return False


def _has_executable_text(value: object) -> bool:
    return any(_EXECUTABLE_TEXT_PATTERN.search(item) for item in _text_values(value))


def _text_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_text_values(item))
        return tuple(values)
    if isinstance(value, (tuple, list)):
        values = []
        for item in value:
            values.extend(_text_values(item))
        return tuple(values)
    return ()


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _hash_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError(f"{name} must be a non-empty sequence")
    return tuple(_required_hash(name, item) for item in value)


def _text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError(f"{name} must be a non-empty sequence")
    return tuple(sorted(set(_required_text(name, item).casefold() for item in value)))


def _raw_text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError(f"{name} must be a non-empty sequence")
    return tuple(_required_text(name, item) for item in value)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(value.strip()) > _MAX_SHORT_TEXT:
        raise ValueError(f"{name} is too long")
    return value.strip()


def _required_long_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(value.strip()) > _MAX_TEXT:
        raise ValueError(f"{name} is too long")
    return value.strip()


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: object) -> str:
    material = json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("coding assistant boundary evidence is too deeply nested")
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
    raise TypeError("coding assistant boundary evidence must be JSON serializable")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
