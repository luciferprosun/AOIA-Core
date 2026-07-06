from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


MCP_SERVER_DECLARATION_SCHEMA_VERSION = "AOIA_MCP_SERVER_DECLARATION_1A"
MCP_TOOL_DECLARATION_SCHEMA_VERSION = "AOIA_MCP_TOOL_DECLARATION_1A"
MCP_RESOURCE_DECLARATION_SCHEMA_VERSION = "AOIA_MCP_RESOURCE_DECLARATION_1A"
MCP_INTERACTION_PROPOSAL_SCHEMA_VERSION = "AOIA_MCP_INTERACTION_PROPOSAL_1A"
MCP_BOUNDARY_REVIEW_SCHEMA_VERSION = "AOIA_MCP_BOUNDARY_REVIEW_1A"

MCP_BOUNDARY_READY_METADATA_ONLY = "MCP_BOUNDARY_READY_METADATA_ONLY"
MCP_BOUNDARY_BLOCKED = "MCP_BOUNDARY_BLOCKED"

MCP_BOUNDARY_REASON_READY_METADATA_ONLY = "MCP_BOUNDARY_REASON_READY_METADATA_ONLY"
MCP_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE = "MCP_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE"
MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD = "MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD"
MCP_BOUNDARY_BLOCKED_UNSUPPORTED_KIND = "MCP_BOUNDARY_BLOCKED_UNSUPPORTED_KIND"
MCP_BOUNDARY_BLOCKED_UNSAFE_TRANSPORT = "MCP_BOUNDARY_BLOCKED_UNSAFE_TRANSPORT"
MCP_BOUNDARY_BLOCKED_POLICY_CAPABILITY = "MCP_BOUNDARY_BLOCKED_POLICY_CAPABILITY"
MCP_BOUNDARY_BLOCKED_UNSUPPORTED_CAPABILITY = "MCP_BOUNDARY_BLOCKED_UNSUPPORTED_CAPABILITY"
MCP_BOUNDARY_BLOCKED_UNSUPPORTED_INTERACTION = "MCP_BOUNDARY_BLOCKED_UNSUPPORTED_INTERACTION"
MCP_BOUNDARY_BLOCKED_HASH_MISMATCH = "MCP_BOUNDARY_BLOCKED_HASH_MISMATCH"
MCP_BOUNDARY_BLOCKED_STALE_EVIDENCE = "MCP_BOUNDARY_BLOCKED_STALE_EVIDENCE"
MCP_BOUNDARY_BLOCKED_AUTHORITY_CLAIM = "MCP_BOUNDARY_BLOCKED_AUTHORITY_CLAIM"
MCP_BOUNDARY_BLOCKED_EFFECT_EVIDENCE = "MCP_BOUNDARY_BLOCKED_EFFECT_EVIDENCE"
MCP_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE = "MCP_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE"
MCP_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE = "MCP_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE"
MCP_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE = "MCP_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE"

MCP_BOUNDARY_RISK_LOW = "LOW"
MCP_BOUNDARY_RISK_MEDIUM = "MEDIUM"
MCP_BOUNDARY_RISK_HIGH = "HIGH"
MCP_BOUNDARY_RISK_BLOCKED = "BLOCKED"

SUPPORTED_MCP_SERVER_KINDS = frozenset({"local_metadata", "remote_metadata", "unknown_metadata"})
SUPPORTED_MCP_TOOL_KINDS = frozenset({"read_only_metadata", "write_proposal_metadata", "unknown_metadata"})
SUPPORTED_MCP_RESOURCE_KINDS = frozenset({"static_metadata", "dynamic_metadata", "unknown_metadata"})
SUPPORTED_MCP_INTERACTION_KINDS = frozenset({"propose_tool_call", "propose_resource_read"})
SAFE_MCP_TRANSPORT_KINDS = frozenset({"metadata_only", "none", "offline"})
FORBIDDEN_MCP_TRANSPORT_KINDS = frozenset({"http", "https", "sse", "stdio", "websocket", "socket"})
METADATA_ONLY_MCP_CAPABILITIES = frozenset(
    {
        "classify_risk",
        "declare_resource_metadata",
        "declare_tool_metadata",
        "describe_schema_metadata",
        "propose_resource_read_metadata",
        "propose_tool_call_metadata",
        "summarize_server_metadata",
    }
)
MEDIUM_RISK_MCP_CAPABILITIES = frozenset({"propose_resource_read_metadata", "propose_tool_call_metadata"})
FORBIDDEN_MCP_CAPABILITIES = frozenset(
    {
        "agent_loop",
        "async_io",
        "browser_execution",
        "call_tool",
        "codex_live_flow",
        "connect_server",
        "dispatcher",
        "git_operation",
        "http_transport",
        "package_install",
        "provider_call",
        "read_resource",
        "shell",
        "socket_transport",
        "sse_transport",
        "start_server",
        "stdio_transport",
        "subprocess",
        "tool_call",
        "websocket_transport",
    }
)
_SUPPORTED_CAPABILITIES = METADATA_ONLY_MCP_CAPABILITIES | FORBIDDEN_MCP_CAPABILITIES
_REQUIRED_FUTURE_EVIDENCE = (
    "exact_server_declaration_hash",
    "exact_tool_declaration_hashes",
    "exact_resource_declaration_hashes",
    "exact_interaction_proposal_hash",
    "exact_boundary_review_hash",
    "explicit_hash_bound_human_approval",
    "separate_controlled_mcp_runtime",
)
_ALLOWED_SERVER_FIELDS = frozenset(
    {
        "schema_version",
        "server_id",
        "server_kind",
        "transport_kind",
        "declared_tools",
        "declared_resources",
        "declared_capabilities",
        "declared_limitations",
        "declaration_hash",
    }
)
_ALLOWED_TOOL_FIELDS = frozenset(
    {
        "schema_version",
        "tool_id",
        "server_id",
        "tool_kind",
        "input_schema_hash",
        "declared_capabilities",
        "declared_limitations",
        "declaration_hash",
    }
)
_ALLOWED_RESOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "resource_id",
        "server_id",
        "resource_kind",
        "resource_uri_template",
        "declared_capabilities",
        "declared_limitations",
        "declaration_hash",
    }
)
_ALLOWED_PROPOSAL_FIELDS = frozenset(
    {
        "schema_version",
        "proposal_id",
        "server_declaration_hash",
        "tool_declaration_hashes",
        "resource_declaration_hashes",
        "interaction_kind",
        "target_id",
        "argument_hash",
        "reason",
        "requested_by",
        "created_at_tick",
        "expires_at_tick",
        "metadata",
        "proposal_hash",
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
        "mcp_allowed",
        "can_call_tool",
        "can_read_resource",
        "can_connect_server",
        "can_start_server",
        "can_execute",
        "can_write",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "human_barrier_satisfied",
        "execution_allowed",
    }
)
_EFFECT_FIELD_NAMES = frozenset(
    {
        "mcp_server_started",
        "mcp_server_connected",
        "mcp_tool_called",
        "mcp_resource_read",
        "stdio_opened",
        "http_called",
        "sse_connected",
        "websocket_connected",
        "socket_opened",
        "process_started",
        "shell_called",
        "provider_called",
        "browser_opened",
        "package_manager_called",
        "git_action_performed",
        "tool_call_invoked",
        "dispatcher_created",
        "async_io_started",
        "agent_loop_started",
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
        "stdio",
        "http",
        "https",
        "sse",
        "websocket",
        "socket",
        "subprocess",
        "process",
        "provider",
        "browser",
        "package",
        "git",
        "tool_call",
        "dispatcher",
        "async",
        "agent_loop",
        "token",
        "secret",
        "env",
        "api" + "_key",
    }
)
_AUTONOMOUS_FIELD_NAMES = frozenset({"auto_call", "auto_read", "autonomous", "retry", "fallback", "loop"})
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 1024
_MAX_COLLECTION_ITEMS = 64
_MAX_DEPTH = 6
_EXECUTABLE_TEXT_PATTERN = re.compile(
    r"(?i)(?:\b(?:mcp)\s+(?:run|serve|server|client|call|connect)\b|"
    r"\b(?:curl|wget|bash|sh|sudo|powershell|cmd\.exe)\b|"
    r"\b(?:python\s+-m|pip|npm|apt|git)\s+\w+\b|"
    r"\b(?:eval|exec|compile|importlib|os\.system|subprocess|socket|websocket)\b|"
    r"(?:;|&&|\|\||`|\$\(|<\(|>\(|\n))"
)
_AUTHORITY_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"safe\s+to\s+(?:call|read|execute|connect)|can\s+(?:call|read|execute|connect)|"
    r"mcp\s+allowed|gate\s+satisfied|authority\s+granted)\b"
)


@dataclass(frozen=True)
class MCPServerDeclaration:
    schema_version: str
    server_id: str
    server_kind: str
    transport_kind: str
    declared_tools: tuple[str, ...]
    declared_resources: tuple[str, ...]
    declared_capabilities: tuple[str, ...]
    declared_limitations: tuple[str, ...]
    declaration_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "server_id", _required_text("server_id", self.server_id))
        object.__setattr__(self, "server_kind", _required_text("server_kind", self.server_kind).casefold())
        object.__setattr__(self, "transport_kind", _required_text("transport_kind", self.transport_kind).casefold())
        object.__setattr__(self, "declared_tools", _text_tuple("declared_tools", self.declared_tools))
        object.__setattr__(self, "declared_resources", _text_tuple("declared_resources", self.declared_resources))
        object.__setattr__(self, "declared_capabilities", _text_tuple("declared_capabilities", self.declared_capabilities))
        object.__setattr__(self, "declared_limitations", _raw_text_tuple("declared_limitations", self.declared_limitations))
        object.__setattr__(self, "declaration_hash", _required_hash("declaration_hash", self.declaration_hash))
        if self.schema_version != MCP_SERVER_DECLARATION_SCHEMA_VERSION:
            raise ValueError("unsupported MCP server declaration schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "server_id": self.server_id,
            "server_kind": self.server_kind,
            "transport_kind": self.transport_kind,
            "declared_tools": self.declared_tools,
            "declared_resources": self.declared_resources,
            "declared_capabilities": self.declared_capabilities,
            "declared_limitations": self.declared_limitations,
            "declaration_hash": self.declaration_hash,
        }


@dataclass(frozen=True)
class MCPToolDeclaration:
    schema_version: str
    tool_id: str
    server_id: str
    tool_kind: str
    input_schema_hash: str
    declared_capabilities: tuple[str, ...]
    declared_limitations: tuple[str, ...]
    declaration_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "tool_id", _required_text("tool_id", self.tool_id))
        object.__setattr__(self, "server_id", _required_text("server_id", self.server_id))
        object.__setattr__(self, "tool_kind", _required_text("tool_kind", self.tool_kind).casefold())
        object.__setattr__(self, "input_schema_hash", _required_hash("input_schema_hash", self.input_schema_hash))
        object.__setattr__(self, "declared_capabilities", _text_tuple("declared_capabilities", self.declared_capabilities))
        object.__setattr__(self, "declared_limitations", _raw_text_tuple("declared_limitations", self.declared_limitations))
        object.__setattr__(self, "declaration_hash", _required_hash("declaration_hash", self.declaration_hash))
        if self.schema_version != MCP_TOOL_DECLARATION_SCHEMA_VERSION:
            raise ValueError("unsupported MCP tool declaration schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_id": self.tool_id,
            "server_id": self.server_id,
            "tool_kind": self.tool_kind,
            "input_schema_hash": self.input_schema_hash,
            "declared_capabilities": self.declared_capabilities,
            "declared_limitations": self.declared_limitations,
            "declaration_hash": self.declaration_hash,
        }


@dataclass(frozen=True)
class MCPResourceDeclaration:
    schema_version: str
    resource_id: str
    server_id: str
    resource_kind: str
    resource_uri_template: str
    declared_capabilities: tuple[str, ...]
    declared_limitations: tuple[str, ...]
    declaration_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "resource_id", _required_text("resource_id", self.resource_id))
        object.__setattr__(self, "server_id", _required_text("server_id", self.server_id))
        object.__setattr__(self, "resource_kind", _required_text("resource_kind", self.resource_kind).casefold())
        object.__setattr__(self, "resource_uri_template", _required_text("resource_uri_template", self.resource_uri_template))
        object.__setattr__(self, "declared_capabilities", _text_tuple("declared_capabilities", self.declared_capabilities))
        object.__setattr__(self, "declared_limitations", _raw_text_tuple("declared_limitations", self.declared_limitations))
        object.__setattr__(self, "declaration_hash", _required_hash("declaration_hash", self.declaration_hash))
        if self.schema_version != MCP_RESOURCE_DECLARATION_SCHEMA_VERSION:
            raise ValueError("unsupported MCP resource declaration schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "resource_id": self.resource_id,
            "server_id": self.server_id,
            "resource_kind": self.resource_kind,
            "resource_uri_template": self.resource_uri_template,
            "declared_capabilities": self.declared_capabilities,
            "declared_limitations": self.declared_limitations,
            "declaration_hash": self.declaration_hash,
        }


@dataclass(frozen=True)
class MCPInteractionProposal:
    schema_version: str
    proposal_id: str
    server_declaration_hash: str
    tool_declaration_hashes: tuple[str, ...]
    resource_declaration_hashes: tuple[str, ...]
    interaction_kind: str
    target_id: str
    argument_hash: str
    reason: str
    requested_by: str
    created_at_tick: int
    expires_at_tick: int
    metadata: Mapping[str, Any] | None
    proposal_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    mcp_allowed: bool = False
    can_call_tool: bool = False
    can_read_resource: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "proposal_id", _required_text("proposal_id", self.proposal_id))
        object.__setattr__(self, "server_declaration_hash", _required_hash("server_declaration_hash", self.server_declaration_hash))
        object.__setattr__(self, "tool_declaration_hashes", _hash_tuple("tool_declaration_hashes", self.tool_declaration_hashes))
        object.__setattr__(self, "resource_declaration_hashes", _hash_tuple("resource_declaration_hashes", self.resource_declaration_hashes))
        object.__setattr__(self, "interaction_kind", _required_text("interaction_kind", self.interaction_kind).casefold())
        object.__setattr__(self, "target_id", _required_text("target_id", self.target_id))
        object.__setattr__(self, "argument_hash", _required_hash("argument_hash", self.argument_hash))
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "created_at_tick", _nonnegative_int("created_at_tick", self.created_at_tick))
        object.__setattr__(self, "expires_at_tick", _nonnegative_int("expires_at_tick", self.expires_at_tick))
        object.__setattr__(self, "proposal_hash", _required_hash("proposal_hash", self.proposal_hash))
        if self.schema_version != MCP_INTERACTION_PROPOSAL_SCHEMA_VERSION:
            raise ValueError("unsupported MCP interaction proposal schema version")
        if self.expires_at_tick < self.created_at_tick:
            raise ValueError("MCP interaction proposal TTL is inverted")
        for field_name in _AUTHORITY_FLAGS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "server_declaration_hash": self.server_declaration_hash,
            "tool_declaration_hashes": self.tool_declaration_hashes,
            "resource_declaration_hashes": self.resource_declaration_hashes,
            "interaction_kind": self.interaction_kind,
            "target_id": self.target_id,
            "argument_hash": self.argument_hash,
            "reason": self.reason,
            "requested_by": self.requested_by,
            "created_at_tick": self.created_at_tick,
            "expires_at_tick": self.expires_at_tick,
            "metadata": _json_fingerprint(self.metadata or {}),
            "proposal_hash": self.proposal_hash,
        }
        for field_name in _AUTHORITY_FLAGS:
            data[field_name] = False
        return data


@dataclass(frozen=True)
class MCPBoundaryReviewResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    risk_tier: str
    server_id: str | None
    server_declaration_hash: str | None
    tool_declaration_hashes: tuple[str, ...]
    resource_declaration_hashes: tuple[str, ...]
    proposal_hash: str | None
    interaction_kind: str | None
    target_id: str | None
    declared_capabilities: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]
    required_future_evidence: tuple[str, ...]
    review_hash: str
    human_review_required: bool = True
    mcp_server_started: bool = False
    mcp_server_connected: bool = False
    mcp_tool_called: bool = False
    mcp_resource_read: bool = False
    stdio_opened: bool = False
    http_called: bool = False
    sse_connected: bool = False
    websocket_connected: bool = False
    socket_opened: bool = False
    process_started: bool = False
    shell_called: bool = False
    provider_called: bool = False
    browser_opened: bool = False
    package_manager_called: bool = False
    git_action_performed: bool = False
    tool_call_invoked: bool = False
    dispatcher_created: bool = False
    async_io_started: bool = False
    agent_loop_started: bool = False
    approval_created: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    mcp_allowed: bool = False
    can_call_tool: bool = False
    can_read_resource: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", MCP_BOUNDARY_REVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "tool_declaration_hashes", tuple(self.tool_declaration_hashes))
        object.__setattr__(self, "resource_declaration_hashes", tuple(self.resource_declaration_hashes))
        object.__setattr__(self, "declared_capabilities", tuple(sorted(set(self.declared_capabilities))))
        object.__setattr__(self, "blocked_capabilities", tuple(sorted(set(self.blocked_capabilities))))
        object.__setattr__(self, "required_future_evidence", tuple(sorted(set(self.required_future_evidence))))
        object.__setattr__(self, "review_hash", _required_hash("review_hash", self.review_hash))
        if self.status not in {MCP_BOUNDARY_READY_METADATA_ONLY, MCP_BOUNDARY_BLOCKED}:
            raise ValueError("unsupported MCP boundary review status")
        if self.risk_tier not in {MCP_BOUNDARY_RISK_LOW, MCP_BOUNDARY_RISK_MEDIUM, MCP_BOUNDARY_RISK_HIGH, MCP_BOUNDARY_RISK_BLOCKED}:
            raise ValueError("unsupported MCP boundary risk tier")
        object.__setattr__(self, "human_review_required", True)
        for field_name in (*_EFFECT_FIELD_NAMES, *_AUTHORITY_FLAGS):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": MCP_BOUNDARY_REVIEW_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "risk_tier": self.risk_tier,
            "server_id": self.server_id,
            "server_declaration_hash": self.server_declaration_hash,
            "tool_declaration_hashes": self.tool_declaration_hashes,
            "resource_declaration_hashes": self.resource_declaration_hashes,
            "proposal_hash": self.proposal_hash,
            "interaction_kind": self.interaction_kind,
            "target_id": self.target_id,
            "declared_capabilities": self.declared_capabilities,
            "blocked_capabilities": self.blocked_capabilities,
            "required_future_evidence": self.required_future_evidence,
            "review_hash": self.review_hash,
            "human_review_required": True,
        }
        for field_name in (*_EFFECT_FIELD_NAMES, *_AUTHORITY_FLAGS):
            data[field_name] = False
        return data


_AUTHORITY_FLAGS = (
    "gate_satisfied",
    "human_barrier_satisfied",
    "mcp_allowed",
    "can_call_tool",
    "can_read_resource",
    "can_execute",
    "can_write",
    "can_call_provider",
    "can_change_gate",
)


def create_mcp_server_declaration(
    *,
    server_id: str,
    server_kind: str,
    transport_kind: str,
    declared_tools: tuple[str, ...],
    declared_resources: tuple[str, ...],
    declared_capabilities: tuple[str, ...],
    declared_limitations: tuple[str, ...] = ("metadata_only", "no_mcp_client", "no_mcp_server", "no_transport"),
) -> MCPServerDeclaration:
    material = {
        "schema_version": MCP_SERVER_DECLARATION_SCHEMA_VERSION,
        "server_id": _required_text("server_id", server_id),
        "server_kind": _required_text("server_kind", server_kind).casefold(),
        "transport_kind": _required_text("transport_kind", transport_kind).casefold(),
        "declared_tools": _text_tuple("declared_tools", declared_tools),
        "declared_resources": _text_tuple("declared_resources", declared_resources),
        "declared_capabilities": _text_tuple("declared_capabilities", declared_capabilities),
        "declared_limitations": _raw_text_tuple("declared_limitations", declared_limitations),
    }
    return MCPServerDeclaration(**material, declaration_hash=compute_mcp_server_declaration_hash(material))


def create_mcp_tool_declaration(
    *,
    tool_id: str,
    server_id: str,
    tool_kind: str,
    input_schema_hash: str,
    declared_capabilities: tuple[str, ...],
    declared_limitations: tuple[str, ...] = ("metadata_only", "no_tool_call"),
) -> MCPToolDeclaration:
    material = {
        "schema_version": MCP_TOOL_DECLARATION_SCHEMA_VERSION,
        "tool_id": _required_text("tool_id", tool_id),
        "server_id": _required_text("server_id", server_id),
        "tool_kind": _required_text("tool_kind", tool_kind).casefold(),
        "input_schema_hash": _required_hash("input_schema_hash", input_schema_hash),
        "declared_capabilities": _text_tuple("declared_capabilities", declared_capabilities),
        "declared_limitations": _raw_text_tuple("declared_limitations", declared_limitations),
    }
    return MCPToolDeclaration(**material, declaration_hash=compute_mcp_tool_declaration_hash(material))


def create_mcp_resource_declaration(
    *,
    resource_id: str,
    server_id: str,
    resource_kind: str,
    resource_uri_template: str,
    declared_capabilities: tuple[str, ...],
    declared_limitations: tuple[str, ...] = ("metadata_only", "no_resource_read"),
) -> MCPResourceDeclaration:
    material = {
        "schema_version": MCP_RESOURCE_DECLARATION_SCHEMA_VERSION,
        "resource_id": _required_text("resource_id", resource_id),
        "server_id": _required_text("server_id", server_id),
        "resource_kind": _required_text("resource_kind", resource_kind).casefold(),
        "resource_uri_template": _required_text("resource_uri_template", resource_uri_template),
        "declared_capabilities": _text_tuple("declared_capabilities", declared_capabilities),
        "declared_limitations": _raw_text_tuple("declared_limitations", declared_limitations),
    }
    return MCPResourceDeclaration(**material, declaration_hash=compute_mcp_resource_declaration_hash(material))


def create_mcp_interaction_proposal(
    *,
    proposal_id: str,
    server_declaration_hash: str,
    tool_declaration_hashes: tuple[str, ...],
    resource_declaration_hashes: tuple[str, ...],
    interaction_kind: str,
    target_id: str,
    arguments: Mapping[str, Any] | None,
    reason: str,
    requested_by: str,
    created_at_tick: int,
    expires_at_tick: int,
    metadata: Mapping[str, Any] | None = None,
) -> MCPInteractionProposal:
    material = {
        "schema_version": MCP_INTERACTION_PROPOSAL_SCHEMA_VERSION,
        "proposal_id": _required_text("proposal_id", proposal_id),
        "server_declaration_hash": _required_hash("server_declaration_hash", server_declaration_hash),
        "tool_declaration_hashes": _hash_tuple("tool_declaration_hashes", tool_declaration_hashes),
        "resource_declaration_hashes": _hash_tuple("resource_declaration_hashes", resource_declaration_hashes),
        "interaction_kind": _required_text("interaction_kind", interaction_kind).casefold(),
        "target_id": _required_text("target_id", target_id),
        "argument_hash": compute_mcp_argument_hash(arguments or {}),
        "reason": _required_text("reason", reason),
        "requested_by": _required_text("requested_by", requested_by),
        "created_at_tick": _nonnegative_int("created_at_tick", created_at_tick),
        "expires_at_tick": _nonnegative_int("expires_at_tick", expires_at_tick),
        "metadata": _json_fingerprint(metadata or {}),
    }
    return MCPInteractionProposal(**material, proposal_hash=compute_mcp_interaction_proposal_hash(material))


def review_mcp_boundary(
    *,
    server_declaration: object,
    tool_declarations: object,
    resource_declarations: object,
    interaction_proposal: object,
    now_tick: object,
) -> MCPBoundaryReviewResult:
    reason_codes: list[str] = []
    try:
        tick = _nonnegative_int("now_tick", now_tick)
    except (TypeError, ValueError):
        return _blocked((MCP_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE,))
    try:
        server_data = _coerce_mapping(server_declaration)
        tool_data = _coerce_mapping_sequence(tool_declarations)
        resource_data = _coerce_mapping_sequence(resource_declarations)
        proposal_data = _coerce_mapping(interaction_proposal)
        input_fingerprint = _json_fingerprint(
            {
                "server_declaration": server_data,
                "tool_declarations": tool_data,
                "resource_declarations": resource_data,
                "interaction_proposal": proposal_data,
            }
        )
    except TypeError:
        return _blocked((MCP_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE,))

    if any(field not in _ALLOWED_SERVER_FIELDS for field in server_data):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD)
    if any(field not in _ALLOWED_TOOL_FIELDS for item in tool_data for field in item):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD)
    if any(field not in _ALLOWED_RESOURCE_FIELDS for item in resource_data for field in item):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD)
    if any(field not in _ALLOWED_PROPOSAL_FIELDS and field not in _AUTHORITY_FLAGS and field not in _EFFECT_FIELD_NAMES for field in proposal_data):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD)

    try:
        server = _coerce_server(server_data)
        tools = tuple(_coerce_tool(item) for item in tool_data)
        resources = tuple(_coerce_resource(item) for item in resource_data)
        proposal = _coerce_proposal(proposal_data)
    except (TypeError, ValueError):
        return _blocked(tuple(reason_codes or (MCP_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE,)), input_fingerprint=input_fingerprint)

    tool_ids = tuple(tool.tool_id for tool in tools)
    resource_ids = tuple(resource.resource_id for resource in resources)
    tool_hashes = tuple(tool.declaration_hash for tool in tools)
    resource_hashes = tuple(resource.declaration_hash for resource in resources)
    all_capabilities = tuple(
        sorted(
            set(
                (
                    *server.declared_capabilities,
                    *(capability for tool in tools for capability in tool.declared_capabilities),
                    *(capability for resource in resources for capability in resource.declared_capabilities),
                )
            )
        )
    )
    unsupported_capabilities = tuple(item for item in all_capabilities if item not in _SUPPORTED_CAPABILITIES)
    blocked_capabilities = tuple(item for item in all_capabilities if item in FORBIDDEN_MCP_CAPABILITIES)

    if server.server_kind not in SUPPORTED_MCP_SERVER_KINDS:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNSUPPORTED_KIND)
    if any(tool.tool_kind not in SUPPORTED_MCP_TOOL_KINDS for tool in tools):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNSUPPORTED_KIND)
    if any(resource.resource_kind not in SUPPORTED_MCP_RESOURCE_KINDS for resource in resources):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNSUPPORTED_KIND)
    if server.transport_kind not in SAFE_MCP_TRANSPORT_KINDS or server.transport_kind in FORBIDDEN_MCP_TRANSPORT_KINDS:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNSAFE_TRANSPORT)
    if proposal.interaction_kind not in SUPPORTED_MCP_INTERACTION_KINDS:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNSUPPORTED_INTERACTION)
    if tick < proposal.created_at_tick or tick > proposal.expires_at_tick:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_STALE_EVIDENCE)
    if unsupported_capabilities:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_UNSUPPORTED_CAPABILITY)
    if blocked_capabilities:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_POLICY_CAPABILITY)

    if server.declaration_hash != compute_mcp_server_declaration_hash(_server_hash_material(server)):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if any(tool.declaration_hash != compute_mcp_tool_declaration_hash(_tool_hash_material(tool)) for tool in tools):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if any(resource.declaration_hash != compute_mcp_resource_declaration_hash(_resource_hash_material(resource)) for resource in resources):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if proposal.proposal_hash != compute_mcp_interaction_proposal_hash(_proposal_hash_material(proposal)):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if proposal.server_declaration_hash != server.declaration_hash:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if proposal.tool_declaration_hashes != tool_hashes or proposal.resource_declaration_hashes != resource_hashes:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if tuple(server.declared_tools) != tuple(sorted(tool_ids)) or tuple(server.declared_resources) != tuple(sorted(resource_ids)):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if any(tool.server_id != server.server_id for tool in tools) or any(resource.server_id != server.server_id for resource in resources):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if proposal.interaction_kind == "propose_tool_call" and proposal.target_id not in tool_ids:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)
    if proposal.interaction_kind == "propose_resource_read" and proposal.target_id not in resource_ids:
        reason_codes.append(MCP_BOUNDARY_BLOCKED_HASH_MISMATCH)

    all_evidence = (server_data, *tool_data, *resource_data, proposal_data)
    if any(_authority_claim_present(item) for item in all_evidence):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_AUTHORITY_CLAIM)
    if _effect_claim_present(proposal_data):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_EFFECT_EVIDENCE)
    if any(_has_key(item, _DANGEROUS_FIELD_NAMES) for item in all_evidence):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE)
    if _has_executable_text(proposal_data):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE)
    if any(_has_key(item, _AUTONOMOUS_FIELD_NAMES) for item in all_evidence):
        reason_codes.append(MCP_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE)

    if not reason_codes:
        reason_codes = [MCP_BOUNDARY_REASON_READY_METADATA_ONLY]
    status = MCP_BOUNDARY_READY_METADATA_ONLY
    if reason_codes != [MCP_BOUNDARY_REASON_READY_METADATA_ONLY]:
        status = MCP_BOUNDARY_BLOCKED
    risk_tier = _risk_tier(all_capabilities, tuple((*blocked_capabilities, *unsupported_capabilities)))
    material = {
        "schema_version": MCP_BOUNDARY_REVIEW_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_tier": risk_tier,
        "server_id": server.server_id,
        "server_declaration_hash": server.declaration_hash,
        "tool_declaration_hashes": tool_hashes,
        "resource_declaration_hashes": resource_hashes,
        "proposal_hash": proposal.proposal_hash,
        "interaction_kind": proposal.interaction_kind,
        "target_id": proposal.target_id,
        "declared_capabilities": all_capabilities,
        "blocked_capabilities": tuple(sorted(set((*blocked_capabilities, *unsupported_capabilities)))),
        "required_future_evidence": _REQUIRED_FUTURE_EVIDENCE,
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
    }
    return MCPBoundaryReviewResult(
        schema_version=MCP_BOUNDARY_REVIEW_SCHEMA_VERSION,
        status=status,
        reason_codes=tuple(reason_codes),
        risk_tier=risk_tier,
        server_id=server.server_id,
        server_declaration_hash=server.declaration_hash,
        tool_declaration_hashes=tool_hashes,
        resource_declaration_hashes=resource_hashes,
        proposal_hash=proposal.proposal_hash,
        interaction_kind=proposal.interaction_kind,
        target_id=proposal.target_id,
        declared_capabilities=all_capabilities,
        blocked_capabilities=tuple((*blocked_capabilities, *unsupported_capabilities)),
        required_future_evidence=_REQUIRED_FUTURE_EVIDENCE,
        review_hash=_stable_hash(material),
    )


def compute_mcp_server_declaration_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("declaration_hash", None)
    return _stable_hash(_json_fingerprint(data))


def compute_mcp_tool_declaration_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("declaration_hash", None)
    return _stable_hash(_json_fingerprint(data))


def compute_mcp_resource_declaration_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("declaration_hash", None)
    return _stable_hash(_json_fingerprint(data))


def compute_mcp_interaction_proposal_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("proposal_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return _stable_hash(_json_fingerprint(data))


def compute_mcp_argument_hash(value: Mapping[str, Any]) -> str:
    return _stable_hash(_json_fingerprint(value))


def canonical_mcp_boundary_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _server_hash_material(server: MCPServerDeclaration) -> dict[str, Any]:
    data = server.to_dict()
    data.pop("declaration_hash", None)
    return data


def _tool_hash_material(tool: MCPToolDeclaration) -> dict[str, Any]:
    data = tool.to_dict()
    data.pop("declaration_hash", None)
    return data


def _resource_hash_material(resource: MCPResourceDeclaration) -> dict[str, Any]:
    data = resource.to_dict()
    data.pop("declaration_hash", None)
    return data


def _proposal_hash_material(proposal: MCPInteractionProposal) -> dict[str, Any]:
    data = proposal.to_dict()
    data.pop("proposal_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return data


def _risk_tier(capabilities: tuple[str, ...], blocked: tuple[str, ...]) -> str:
    if blocked:
        return MCP_BOUNDARY_RISK_BLOCKED
    if any(item in FORBIDDEN_MCP_CAPABILITIES for item in capabilities):
        return MCP_BOUNDARY_RISK_HIGH
    if any(item in MEDIUM_RISK_MCP_CAPABILITIES for item in capabilities):
        return MCP_BOUNDARY_RISK_MEDIUM
    return MCP_BOUNDARY_RISK_LOW


def _blocked(reason_codes: tuple[str, ...], *, input_fingerprint: Any | None = None) -> MCPBoundaryReviewResult:
    material = {
        "schema_version": MCP_BOUNDARY_REVIEW_SCHEMA_VERSION,
        "status": MCP_BOUNDARY_BLOCKED,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_tier": MCP_BOUNDARY_RISK_BLOCKED,
        "required_future_evidence": _REQUIRED_FUTURE_EVIDENCE,
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
    }
    return MCPBoundaryReviewResult(
        schema_version=MCP_BOUNDARY_REVIEW_SCHEMA_VERSION,
        status=MCP_BOUNDARY_BLOCKED,
        reason_codes=reason_codes,
        risk_tier=MCP_BOUNDARY_RISK_BLOCKED,
        server_id=None,
        server_declaration_hash=None,
        tool_declaration_hashes=(),
        resource_declaration_hashes=(),
        proposal_hash=None,
        interaction_kind=None,
        target_id=None,
        declared_capabilities=(),
        blocked_capabilities=(),
        required_future_evidence=_REQUIRED_FUTURE_EVIDENCE,
        review_hash=_stable_hash(material),
    )


def _coerce_server(value: object) -> MCPServerDeclaration:
    if isinstance(value, MCPServerDeclaration):
        return value
    if isinstance(value, Mapping):
        return MCPServerDeclaration(**dict(value))
    raise TypeError("MCP server declaration is required")


def _coerce_tool(value: object) -> MCPToolDeclaration:
    if isinstance(value, MCPToolDeclaration):
        return value
    if isinstance(value, Mapping):
        return MCPToolDeclaration(**dict(value))
    raise TypeError("MCP tool declaration is required")


def _coerce_resource(value: object) -> MCPResourceDeclaration:
    if isinstance(value, MCPResourceDeclaration):
        return value
    if isinstance(value, Mapping):
        return MCPResourceDeclaration(**dict(value))
    raise TypeError("MCP resource declaration is required")


def _coerce_proposal(value: object) -> MCPInteractionProposal:
    if isinstance(value, MCPInteractionProposal):
        return value
    if isinstance(value, Mapping):
        data = dict(value)
        for field_name in _EFFECT_FIELD_NAMES:
            data.pop(field_name, None)
        return MCPInteractionProposal(**data)
    raise TypeError("MCP interaction proposal is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("MCP boundary evidence must be mapping evidence")


def _coerce_mapping_sequence(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError("MCP boundary requires non-empty declaration sequences")
    return tuple(_coerce_mapping(item) for item in value)


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
        raise TypeError("MCP boundary evidence is too deeply nested")
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
    raise TypeError("MCP boundary evidence must be JSON serializable")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
