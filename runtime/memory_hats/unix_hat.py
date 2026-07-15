"""Immutable, non-authoritative UNIX Hat and route metadata.

This module is deliberately capability-free.  It validates already-loaded
corpus/index manifest data, classifies bounded text, and returns inert data.
It does not read or write files, invoke retrieval, dispatch callables, or
interpret metadata as approval.
"""

from __future__ import annotations

import hashlib
import json
import re
import types
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping


NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
UNIX_HAT_SCHEMA_VERSION = "unix-hat-descriptor-1a"
UNIX_HAT_ID = "unix-knowledge-hat-1a"
UNIX_ROUTE_REQUEST_SCHEMA_VERSION = "unix-route-request-1a"
UNIX_ROUTE_PROPOSAL_SCHEMA_VERSION = "unix-route-proposal-1a"
UNIX_RETRIEVAL_REQUEST_SCHEMA_VERSION = "unix-retrieval-request-metadata-1a"
UNIX_CONFIDENCE_SCHEMA_VERSION = "unix-route-confidence-1a"
ROUTING_POLICY_MANIFEST_SCHEMA_VERSION = "unix-routing-policy-manifest-1a"
ACTUAL_QUERY_VALIDATION_SCHEMA_VERSION = "unix-route-query-validation-1a"
ROUTING_POLICY_VERSION = "deterministic-unix-routing-policy-1a"

MAX_QUERY_CHARACTERS = 2_048
MAX_QUERY_TOKENS = 64
MAX_RESULT_LIMIT = 20
MAX_CONTEXT_FIELDS = 16
MAX_CONTEXT_BYTES = 4_096
MAX_CONTEXT_DEPTH = 4

ROUTE_TO_UNIX_KNOWLEDGE = "ROUTE_TO_UNIX_KNOWLEDGE"
EXECUTION_REQUEST_BLOCKED = "EXECUTION_REQUEST_BLOCKED"
NO_ROUTE = "NO_ROUTE"
REVIEW_NEEDED = "REVIEW_NEEDED"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FLAGS = {
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
    "gate_satisfied": False,
}
_CORPUS_MANIFEST_FIELDS = {
    "accepted_source_count",
    "authority_status",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_write",
    "corpus_id",
    "gate_satisfied",
    "manifest_hash",
    "quarantine_ids",
    "quarantined_source_count",
    "record_count",
    "record_ids",
    "schema_version",
    "source_count",
    "sources",
}
_INDEX_MANIFEST_FIELDS = {
    "authority_status",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_write",
    "corpus_id",
    "corpus_manifest_hash",
    "gate_satisfied",
    "index_files",
    "index_hash",
    "index_version",
    "indexed_record_ids",
    "posting_count",
    "record_count",
    "schema_version",
    "scoring_version",
    "tokenizer_version",
    "total_token_count",
    "unique_term_count",
}
_CONFIDENCE_FIELDS = {
    "ambiguity_score",
    "authority_status",
    "excluded_domain_score",
    "execution_risk_score",
    "final_confidence",
    "schema_version",
    "scope_match_score",
    "topic_match_score",
}
_RETRIEVAL_REQUEST_FIELDS = {
    "execution_allowed",
    "index_manifest_hash",
    "normalized_query",
    "query_hash",
    "requested_result_limit",
    "required_provenance_policy",
    "required_retrieval_adapter_version",
    "requires_explicit_caller",
    "schema_version",
}

SUPPORTED_TOPICS = (
    "ai-safety-boundaries",
    "bsd-macos-posix-differences",
    "containers",
    "control-groups",
    "debugging",
    "filesystem-concepts",
    "init-and-systemd",
    "linux",
    "namespaces",
    "network-boundaries",
    "observability",
    "package-management-concepts",
    "path-safety",
    "permissions-users-groups",
    "pipes-and-text-processing",
    "posix",
    "processes-and-signals",
    "shell-concepts-and-safety",
    "ssh-concepts",
    "unix",
)

EXCLUDED_TOPICS = (
    "actual-command-execution",
    "browser-automation",
    "controlled-write",
    "credential-handling",
    "filesystem-mutation",
    "financial-trading",
    "git-operation",
    "human-approval",
    "legal-authority",
    "live-shell-operation",
    "malware-execution",
    "medical-advice",
    "package-installation",
    "patch-application",
    "provider-api-operation",
    "real-system-administration",
    "unrelated-scientific-domains",
)

LIMITATIONS = (
    "Knowledge metadata only; never execution permission.",
    "Retrieval requires a separate explicit caller action.",
    "No provider, network, shell, Git, browser, writer, patch, or gate capability.",
    "Ambiguous requests require review and execution requests remain blocked.",
)

_TOPIC_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ai-safety-boundaries", ("ai safety", "safety boundary", "safety boundaries")),
    ("bsd-macos-posix-differences", ("bsd", "macos", "posix", "portable")),
    ("containers", ("container", "containers", "isolate processes")),
    ("control-groups", ("cgroup", "cgroups", "control group", "control groups")),
    ("debugging", ("debug", "debugging", "diagnose", "troubleshoot")),
    ("filesystem-concepts", ("file", "files", "filesystem", "mount")),
    ("init-and-systemd", ("init", "journalctl", "service", "systemctl", "systemd")),
    ("linux", ("linux", "rhel", "rhcsa")),
    ("namespaces", ("namespace", "namespaces")),
    ("network-boundaries", ("firewall", "network", "network boundary", "network boundaries")),
    ("observability", ("log", "logs", "observability", "telemetry")),
    ("package-management-concepts", ("apt", "dnf", "package", "packages", "rpm")),
    ("path-safety", ("path", "path traversal", "symlink", "traversal")),
    ("permissions-users-groups", ("chmod", "chown", "group", "groups", "permission", "permissions", "user", "users")),
    ("pipes-and-text-processing", ("awk", "grep", "pipe", "pipes", "sed", "text processing")),
    ("posix", ("posix",)),
    ("processes-and-signals", ("process", "processes", "signal", "signals")),
    ("shell-concepts-and-safety", ("bash", "command", "shell", "shell injection", "sudo")),
    ("ssh-concepts", ("ssh", "ssh authentication", "sshd")),
    ("unix", ("unix",)),
)

_EXECUTION_PHRASES = (
    "change permissions",
    "execute ",
    "install this package",
    "install curl",
    "open a shell",
    "run sudo",
)
_EXECUTION_FIRST_TOKENS = (
    "execute",
    "install",
    "launch",
    "run",
)
_AMBIGUOUS_PHRASES = (
    "do the safe thing with the server",
    "fix linux",
    "fix my system",
    "make linux work",
)
_EXCLUDED_DOMAIN_TERMS = (
    "capital of france",
    "legal advice",
    "medical advice",
    "romantic poem",
    "stellar nucleosynthesis",
    "trading strategy",
)

class UnixHatRoutingError(ValueError):
    """Fail-closed error carrying a stable routing or binding status."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True, slots=True)
class UnixHatDescriptor:
    schema_version: str
    hat_id: str
    display_name: str
    description: str
    knowledge_domain: str
    supported_topics: tuple[str, ...]
    excluded_topics: tuple[str, ...]
    corpus_id: str
    corpus_manifest_hash: str
    retrieval_index_hash: str
    retrieval_adapter_version: str
    tokenizer_version: str
    scoring_version: str
    routing_policy_version: str
    capability_ids: tuple[str, ...]
    authority_status: str
    limitations: tuple[str, ...]
    descriptor_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_status": self.authority_status,
            "capability_ids": list(self.capability_ids),
            "corpus_id": self.corpus_id,
            "corpus_manifest_hash": self.corpus_manifest_hash,
            "description": self.description,
            "descriptor_hash": self.descriptor_hash,
            "display_name": self.display_name,
            "excluded_topics": list(self.excluded_topics),
            "hat_id": self.hat_id,
            "knowledge_domain": self.knowledge_domain,
            "limitations": list(self.limitations),
            "retrieval_adapter_version": self.retrieval_adapter_version,
            "retrieval_index_hash": self.retrieval_index_hash,
            "routing_policy_version": self.routing_policy_version,
            "schema_version": self.schema_version,
            "scoring_version": self.scoring_version,
            "supported_topics": list(self.supported_topics),
            "tokenizer_version": self.tokenizer_version,
        }


@dataclass(frozen=True, slots=True)
class UnixRouteRequest:
    schema_version: str
    request_id: str
    raw_query: str
    normalized_query: str
    query_hash: str
    requested_limit: int
    context_metadata: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "context_metadata": [list(item) for item in self.context_metadata],
            "normalized_query": self.normalized_query,
            "query_hash": self.query_hash,
            "raw_query": self.raw_query,
            "request_id": self.request_id,
            "requested_limit": self.requested_limit,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class UnixRouteConfidenceMetadata:
    schema_version: str
    topic_match_score: int
    scope_match_score: int
    execution_risk_score: int
    excluded_domain_score: int
    ambiguity_score: int
    final_confidence: int
    authority_status: str = NON_AUTHORITATIVE

    def to_dict(self) -> dict[str, object]:
        return {
            "ambiguity_score": self.ambiguity_score,
            "authority_status": self.authority_status,
            "excluded_domain_score": self.excluded_domain_score,
            "execution_risk_score": self.execution_risk_score,
            "final_confidence": self.final_confidence,
            "schema_version": self.schema_version,
            "scope_match_score": self.scope_match_score,
            "topic_match_score": self.topic_match_score,
        }


@dataclass(frozen=True, slots=True)
class UnixRetrievalRequestMetadata:
    schema_version: str
    normalized_query: str
    query_hash: str
    index_manifest_hash: str
    requested_result_limit: int
    required_provenance_policy: str
    required_retrieval_adapter_version: str
    execution_allowed: bool
    requires_explicit_caller: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "execution_allowed": self.execution_allowed,
            "index_manifest_hash": self.index_manifest_hash,
            "normalized_query": self.normalized_query,
            "query_hash": self.query_hash,
            "requested_result_limit": self.requested_result_limit,
            "required_provenance_policy": self.required_provenance_policy,
            "required_retrieval_adapter_version": self.required_retrieval_adapter_version,
            "requires_explicit_caller": self.requires_explicit_caller,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class UnixRouteProposal:
    schema_version: str
    request_id: str
    query_hash: str
    route_status: str
    selected_hat_id: str | None
    hat_descriptor_hash: str
    corpus_manifest_hash: str
    retrieval_index_hash: str
    retrieval_adapter_version: str
    route_rationale: str
    matched_topics: tuple[str, ...]
    excluded_signals: tuple[str, ...]
    confidence_metadata: UnixRouteConfidenceMetadata
    retrieval_request: UnixRetrievalRequestMetadata | None
    warnings: tuple[str, ...]
    authority_status: str
    proposal_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_status": self.authority_status,
            "confidence_metadata": self.confidence_metadata.to_dict(),
            "corpus_manifest_hash": self.corpus_manifest_hash,
            "excluded_signals": list(self.excluded_signals),
            "hat_descriptor_hash": self.hat_descriptor_hash,
            "matched_topics": list(self.matched_topics),
            "proposal_hash": self.proposal_hash,
            "query_hash": self.query_hash,
            "request_id": self.request_id,
            "retrieval_adapter_version": self.retrieval_adapter_version,
            "retrieval_index_hash": self.retrieval_index_hash,
            "retrieval_request": (
                self.retrieval_request.to_dict()
                if self.retrieval_request is not None
                else None
            ),
            "route_rationale": self.route_rationale,
            "route_status": self.route_status,
            "schema_version": self.schema_version,
            "selected_hat_id": self.selected_hat_id,
            "warnings": list(self.warnings),
        }


def create_unix_hat_descriptor(
    corpus_manifest: Mapping[str, Any],
    index_manifest: Mapping[str, Any],
    *,
    expected_corpus_manifest_hash: str,
    expected_index_manifest_hash: str,
) -> UnixHatDescriptor:
    """Create a descriptor from already-loaded, independently verified data."""

    _verify_corpus_manifest(corpus_manifest, expected_corpus_manifest_hash)
    _verify_index_manifest(
        index_manifest,
        expected_index_manifest_hash,
        corpus_manifest,
    )
    material = {
        "authority_status": NON_AUTHORITATIVE,
        "capability_ids": [],
        "corpus_id": corpus_manifest["corpus_id"],
        "corpus_manifest_hash": corpus_manifest["manifest_hash"],
        "description": "Read-only UNIX knowledge classification and retrieval-request metadata.",
        "display_name": "UNIX Knowledge Hat 1A",
        "excluded_topics": list(EXCLUDED_TOPICS),
        "hat_id": UNIX_HAT_ID,
        "knowledge_domain": "unix-linux-posix-knowledge",
        "limitations": list(LIMITATIONS),
        "retrieval_adapter_version": index_manifest["index_version"],
        "retrieval_index_hash": index_manifest["index_hash"],
        "routing_policy_version": ROUTING_POLICY_VERSION,
        "schema_version": UNIX_HAT_SCHEMA_VERSION,
        "scoring_version": index_manifest["scoring_version"],
        "supported_topics": list(SUPPORTED_TOPICS),
        "tokenizer_version": index_manifest["tokenizer_version"],
    }
    descriptor = _descriptor_from_material(
        {**material, "descriptor_hash": _sha256(_canonical_bytes(material))}
    )
    validate_unix_hat_descriptor(
        descriptor,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
        expected_index_manifest_hash=expected_index_manifest_hash,
    )
    return descriptor


def unix_hat_descriptor_from_payload(
    payload: Mapping[str, Any],
    *,
    expected_corpus_manifest_hash: str | None = None,
    expected_index_manifest_hash: str | None = None,
) -> UnixHatDescriptor:
    expected_fields = set(UnixHatDescriptor.__dataclass_fields__)
    _require_exact_fields(payload, expected_fields, "UNKNOWN_HAT_VERSION")
    descriptor = _descriptor_from_material(payload)
    validate_unix_hat_descriptor(
        descriptor,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
        expected_index_manifest_hash=expected_index_manifest_hash,
    )
    return descriptor


def validate_unix_hat_descriptor(
    descriptor: UnixHatDescriptor,
    *,
    expected_corpus_manifest_hash: str | None = None,
    expected_index_manifest_hash: str | None = None,
) -> None:
    if type(descriptor) is not UnixHatDescriptor:
        raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "descriptor type is invalid")
    if descriptor.schema_version != UNIX_HAT_SCHEMA_VERSION:
        raise UnixHatRoutingError("UNKNOWN_HAT_VERSION", "descriptor schema is unsupported")
    if descriptor.hat_id != UNIX_HAT_ID:
        raise UnixHatRoutingError("UNKNOWN_HAT_VERSION", "Hat ID is unsupported")
    if descriptor.routing_policy_version != ROUTING_POLICY_VERSION:
        raise UnixHatRoutingError("ROUTING_POLICY_MISMATCH", "routing policy version differs")
    if descriptor.authority_status != NON_AUTHORITATIVE:
        raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "descriptor authority status is invalid")
    if descriptor.capability_ids:
        raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "descriptor capability set must be empty")
    for value in _iter_values(descriptor):
        if callable(value) or isinstance(value, types.ModuleType):
            raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "descriptor contains executable data")
    payload = descriptor.to_dict()
    supplied_hash = payload.pop("descriptor_hash")
    if not _is_sha256(supplied_hash) or supplied_hash != _sha256(_canonical_bytes(payload)):
        raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "descriptor hash does not verify")
    if expected_corpus_manifest_hash is not None and descriptor.corpus_manifest_hash != expected_corpus_manifest_hash:
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "descriptor corpus binding differs")
    if expected_index_manifest_hash is not None and descriptor.retrieval_index_hash != expected_index_manifest_hash:
        raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "descriptor index binding differs")


def create_unix_route_request(
    raw_query: str,
    *,
    requested_limit: int = 5,
    context_metadata: Mapping[str, Any] | None = None,
) -> UnixRouteRequest:
    if not isinstance(raw_query, str):
        raise UnixHatRoutingError("INVALID_REQUEST", "query must be a string")
    if len(raw_query) > MAX_QUERY_CHARACTERS:
        raise UnixHatRoutingError("INVALID_REQUEST", "query exceeds character limit")
    normalized = _normalize_query(raw_query)
    if not normalized:
        raise UnixHatRoutingError("INVALID_REQUEST", "query must contain text")
    if len(normalized.split()) > MAX_QUERY_TOKENS:
        raise UnixHatRoutingError("INVALID_REQUEST", "query exceeds token limit")
    if type(requested_limit) is not int or not 1 <= requested_limit <= MAX_RESULT_LIMIT:
        raise UnixHatRoutingError("INVALID_REQUEST", "requested limit is invalid")
    frozen_context = _freeze_context(context_metadata)
    material = {
        "context_metadata": [list(item) for item in frozen_context],
        "normalized_query": normalized,
        "raw_query": raw_query,
        "requested_limit": requested_limit,
        "schema_version": UNIX_ROUTE_REQUEST_SCHEMA_VERSION,
    }
    query_hash = _sha256(_canonical_bytes(material))
    return UnixRouteRequest(
        schema_version=UNIX_ROUTE_REQUEST_SCHEMA_VERSION,
        request_id=f"unix-route-{query_hash[:24]}",
        raw_query=raw_query,
        normalized_query=normalized,
        query_hash=query_hash,
        requested_limit=requested_limit,
        context_metadata=frozen_context,
    )


def unix_route_request_from_payload(payload: Mapping[str, Any]) -> UnixRouteRequest:
    expected_fields = set(UnixRouteRequest.__dataclass_fields__)
    _require_exact_fields(payload, expected_fields, "INVALID_REQUEST")
    context_value = payload["context_metadata"]
    if not isinstance(context_value, list):
        raise UnixHatRoutingError("INVALID_REQUEST", "context metadata encoding is invalid")
    context: dict[str, Any] = {}
    for item in context_value:
        if not isinstance(item, list) or len(item) != 2 or not all(isinstance(part, str) for part in item):
            raise UnixHatRoutingError("INVALID_REQUEST", "context metadata entry is invalid")
        key, encoded = item
        if key in context:
            raise UnixHatRoutingError("INVALID_REQUEST", "context metadata contains a duplicate key")
        try:
            context[key] = json.loads(encoded)
        except (json.JSONDecodeError, TypeError) as exc:
            raise UnixHatRoutingError("INVALID_REQUEST", "context metadata is malformed") from exc
    rebuilt = create_unix_route_request(
        payload["raw_query"],
        requested_limit=payload["requested_limit"],
        context_metadata=context,
    )
    if rebuilt.to_dict() != dict(payload):
        raise UnixHatRoutingError("INVALID_REQUEST", "request hash or normalized fields differ")
    return rebuilt


def propose_unix_route(
    request: UnixRouteRequest,
    descriptor: UnixHatDescriptor,
) -> UnixRouteProposal:
    validate_unix_hat_descriptor(descriptor)
    _validate_route_request(request)
    normalized = request.normalized_query
    matched_topics = _match_topics(normalized)
    execution_signals = _match_execution_signals(normalized)
    excluded_signals = tuple(
        term for term in _EXCLUDED_DOMAIN_TERMS if term in normalized
    )
    ambiguous = any(phrase in normalized for phrase in _AMBIGUOUS_PHRASES)

    if execution_signals and (matched_topics or _looks_like_system_operation(normalized)):
        status = EXECUTION_REQUEST_BLOCKED
        selected_hat_id = None
        rationale = "execution_request_blocked_before_inert_knowledge_routing"
    elif ambiguous:
        status = REVIEW_NEEDED
        selected_hat_id = None
        rationale = "ambiguous_system_request_requires_separate_human_review"
    elif excluded_signals or not matched_topics:
        status = NO_ROUTE
        selected_hat_id = None
        rationale = "query_is_outside_the_unix_knowledge_scope"
    else:
        status = ROUTE_TO_UNIX_KNOWLEDGE
        selected_hat_id = descriptor.hat_id
        rationale = "deterministic_unix_knowledge_topic_match"

    confidence = _confidence_metadata(
        status,
        matched_topics,
        execution_signals,
        excluded_signals,
        ambiguous,
    )
    retrieval_request = None
    if status == ROUTE_TO_UNIX_KNOWLEDGE:
        retrieval_request = UnixRetrievalRequestMetadata(
            schema_version=UNIX_RETRIEVAL_REQUEST_SCHEMA_VERSION,
            normalized_query=normalized,
            query_hash=request.query_hash,
            index_manifest_hash=descriptor.retrieval_index_hash,
            requested_result_limit=request.requested_limit,
            required_provenance_policy="exact-corpus-record-and-source-hash-1a",
            required_retrieval_adapter_version=descriptor.retrieval_adapter_version,
            execution_allowed=False,
            requires_explicit_caller=True,
        )
    warnings = (
        "NO_COMMAND_OR_ACTION_EXECUTED",
        "ROUTE_METADATA_IS_NOT_AUTHORITY",
        "CALLER_CONTEXT_DID_NOT_GRANT_ROUTE_OR_APPROVAL",
    )
    material = {
        "authority_status": NON_AUTHORITATIVE,
        "confidence_metadata": confidence.to_dict(),
        "corpus_manifest_hash": descriptor.corpus_manifest_hash,
        "excluded_signals": list(sorted(set(excluded_signals + execution_signals))),
        "hat_descriptor_hash": descriptor.descriptor_hash,
        "matched_topics": list(matched_topics),
        "query_hash": request.query_hash,
        "request_id": request.request_id,
        "retrieval_adapter_version": descriptor.retrieval_adapter_version,
        "retrieval_index_hash": descriptor.retrieval_index_hash,
        "retrieval_request": retrieval_request.to_dict() if retrieval_request else None,
        "route_rationale": rationale,
        "route_status": status,
        "schema_version": UNIX_ROUTE_PROPOSAL_SCHEMA_VERSION,
        "selected_hat_id": selected_hat_id,
        "warnings": list(warnings),
    }
    proposal = _proposal_from_material(
        {**material, "proposal_hash": _sha256(_canonical_bytes(material))}
    )
    validate_unix_route_proposal(proposal, descriptor)
    return proposal


def unix_route_proposal_from_payload(
    payload: Mapping[str, Any],
    descriptor: UnixHatDescriptor,
) -> UnixRouteProposal:
    expected_fields = set(UnixRouteProposal.__dataclass_fields__)
    _require_exact_fields(payload, expected_fields, "FORGED_ROUTE_PROPOSAL")
    proposal = _proposal_from_material(payload)
    validate_unix_route_proposal(proposal, descriptor)
    return proposal


def validate_unix_route_proposal(
    proposal: UnixRouteProposal,
    descriptor: UnixHatDescriptor,
) -> None:
    validate_unix_hat_descriptor(descriptor)
    if type(proposal) is not UnixRouteProposal:
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "proposal type is invalid")
    if proposal.schema_version != UNIX_ROUTE_PROPOSAL_SCHEMA_VERSION:
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "proposal schema is unsupported")
    if proposal.authority_status != NON_AUTHORITATIVE:
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "proposal authority status is invalid")
    confidence = proposal.confidence_metadata
    if confidence.schema_version != UNIX_CONFIDENCE_SCHEMA_VERSION:
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "confidence schema is unsupported")
    if confidence.authority_status != NON_AUTHORITATIVE:
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "confidence authority status is invalid")
    if any(
        type(score) is not int or not 0 <= score <= 10_000
        for score in (
            confidence.topic_match_score,
            confidence.scope_match_score,
            confidence.execution_risk_score,
            confidence.excluded_domain_score,
            confidence.ambiguity_score,
            confidence.final_confidence,
        )
    ):
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "confidence score is out of range")
    if proposal.hat_descriptor_hash != descriptor.descriptor_hash:
        raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "proposal Hat binding differs")
    if proposal.corpus_manifest_hash != descriptor.corpus_manifest_hash:
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "proposal corpus binding differs")
    if proposal.retrieval_index_hash != descriptor.retrieval_index_hash:
        raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "proposal index binding differs")
    if proposal.retrieval_adapter_version != descriptor.retrieval_adapter_version:
        raise UnixHatRoutingError("RETRIEVAL_ADAPTER_MISMATCH", "proposal adapter version differs")
    if proposal.retrieval_request is not None:
        if proposal.route_status != ROUTE_TO_UNIX_KNOWLEDGE:
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "non-route proposal has retrieval metadata")
        if proposal.retrieval_request.execution_allowed:
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "retrieval metadata permits execution")
        if not proposal.retrieval_request.requires_explicit_caller:
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "retrieval is not caller-separated")
        if proposal.retrieval_request.schema_version != UNIX_RETRIEVAL_REQUEST_SCHEMA_VERSION:
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "retrieval request schema differs")
        if proposal.retrieval_request.query_hash != proposal.query_hash:
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "retrieval query binding differs")
        if proposal.retrieval_request.index_manifest_hash != descriptor.retrieval_index_hash:
            raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "retrieval index binding differs")
        if proposal.retrieval_request.required_retrieval_adapter_version != descriptor.retrieval_adapter_version:
            raise UnixHatRoutingError("RETRIEVAL_ADAPTER_MISMATCH", "retrieval adapter binding differs")
    for value in _iter_values(proposal):
        if callable(value) or isinstance(value, types.ModuleType):
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "proposal contains executable data")
    payload = proposal.to_dict()
    supplied_hash = payload.pop("proposal_hash")
    if not _is_sha256(supplied_hash) or supplied_hash != _sha256(_canonical_bytes(payload)):
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "proposal hash does not verify")


def routing_policy_manifest_payload(descriptor: UnixHatDescriptor) -> dict[str, object]:
    validate_unix_hat_descriptor(descriptor)
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "corpus_manifest_hash": descriptor.corpus_manifest_hash,
        "execution_indicators": list(_EXECUTION_PHRASES),
        "excluded_domain_indicators": list(_EXCLUDED_DOMAIN_TERMS),
        "hat_descriptor_hash": descriptor.descriptor_hash,
        "index_manifest_hash": descriptor.retrieval_index_hash,
        "routing_policy_version": ROUTING_POLICY_VERSION,
        "schema_version": ROUTING_POLICY_MANIFEST_SCHEMA_VERSION,
        "status_values": [
            EXECUTION_REQUEST_BLOCKED,
            NO_ROUTE,
            REVIEW_NEEDED,
            ROUTE_TO_UNIX_KNOWLEDGE,
        ],
        "topic_vocabulary": [
            [topic, list(terms)] for topic, terms in _TOPIC_TERMS
        ],
    }
    return {**material, "policy_hash": _sha256(_canonical_bytes(material))}


def actual_query_validation_payload(
    query_proposals: tuple[tuple[str, UnixRouteProposal], ...],
) -> dict[str, object]:
    for query, proposal in query_proposals:
        if not isinstance(query, str) or type(proposal) is not UnixRouteProposal:
            raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "validation input is invalid")
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "command_or_action_executed": False,
        "proposals": [
            {
                "normalized_query": _normalize_query(query),
                "proposal_hash": proposal.proposal_hash,
                "query": query,
                "query_hash": proposal.query_hash,
                "request_id": proposal.request_id,
                "route_status": proposal.route_status,
            }
            for query, proposal in query_proposals
        ],
        "schema_version": ACTUAL_QUERY_VALIDATION_SCHEMA_VERSION,
    }
    return {**material, "validation_hash": _sha256(_canonical_bytes(material))}


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the only portable artifact encoding used by this boundary."""

    return _canonical_bytes(payload) + b"\n"


def _verify_corpus_manifest(payload: Mapping[str, Any], expected_hash: str) -> None:
    _require_exact_fields(payload, _CORPUS_MANIFEST_FIELDS, "CORPUS_MANIFEST_MISMATCH")
    _verify_non_authority_flags(payload, "CORPUS_MANIFEST_MISMATCH")
    supplied_hash = payload["manifest_hash"]
    if not _is_sha256(expected_hash) or supplied_hash != expected_hash:
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "corpus hash differs")
    material = dict(payload)
    material.pop("manifest_hash")
    if supplied_hash != _sha256(_canonical_bytes(material)):
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "corpus hash does not verify")
    record_ids = payload["record_ids"]
    if not isinstance(record_ids, list) or not record_ids or payload["record_count"] != len(record_ids):
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "corpus record inventory differs")


def _verify_index_manifest(
    payload: Mapping[str, Any],
    expected_hash: str,
    corpus_manifest: Mapping[str, Any],
) -> None:
    _require_exact_fields(payload, _INDEX_MANIFEST_FIELDS, "INDEX_MANIFEST_MISMATCH")
    _verify_non_authority_flags(payload, "INDEX_MANIFEST_MISMATCH")
    supplied_hash = payload["index_hash"]
    if not _is_sha256(expected_hash) or supplied_hash != expected_hash:
        raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "index hash differs")
    material = dict(payload)
    material.pop("index_hash")
    if supplied_hash != _sha256(_canonical_bytes(material)):
        raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "index hash does not verify")
    if payload["corpus_manifest_hash"] != corpus_manifest["manifest_hash"]:
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "index corpus hash differs")
    if payload["corpus_id"] != corpus_manifest["corpus_id"]:
        raise UnixHatRoutingError("CORPUS_MANIFEST_MISMATCH", "index corpus ID differs")
    if payload["indexed_record_ids"] != sorted(corpus_manifest["record_ids"]):
        raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "indexed record IDs differ")
    if payload["record_count"] != corpus_manifest["record_count"]:
        raise UnixHatRoutingError("INDEX_MANIFEST_MISMATCH", "index record count differs")


def _descriptor_from_material(payload: Mapping[str, Any]) -> UnixHatDescriptor:
    try:
        return UnixHatDescriptor(
            schema_version=_required_str(payload, "schema_version"),
            hat_id=_required_str(payload, "hat_id"),
            display_name=_required_str(payload, "display_name"),
            description=_required_str(payload, "description"),
            knowledge_domain=_required_str(payload, "knowledge_domain"),
            supported_topics=_required_string_tuple(payload, "supported_topics"),
            excluded_topics=_required_string_tuple(payload, "excluded_topics"),
            corpus_id=_required_str(payload, "corpus_id"),
            corpus_manifest_hash=_required_str(payload, "corpus_manifest_hash"),
            retrieval_index_hash=_required_str(payload, "retrieval_index_hash"),
            retrieval_adapter_version=_required_str(payload, "retrieval_adapter_version"),
            tokenizer_version=_required_str(payload, "tokenizer_version"),
            scoring_version=_required_str(payload, "scoring_version"),
            routing_policy_version=_required_str(payload, "routing_policy_version"),
            capability_ids=_required_string_tuple(payload, "capability_ids"),
            authority_status=_required_str(payload, "authority_status"),
            limitations=_required_string_tuple(payload, "limitations"),
            descriptor_hash=_required_str(payload, "descriptor_hash"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise UnixHatRoutingError("STALE_HAT_DESCRIPTOR", "descriptor fields are malformed") from exc


def _proposal_from_material(payload: Mapping[str, Any]) -> UnixRouteProposal:
    try:
        confidence_payload = payload["confidence_metadata"]
        if not isinstance(confidence_payload, Mapping):
            raise TypeError("confidence metadata must be a mapping")
        _require_exact_fields(
            confidence_payload,
            _CONFIDENCE_FIELDS,
            "FORGED_ROUTE_PROPOSAL",
        )
        confidence = UnixRouteConfidenceMetadata(
            schema_version=_required_str(confidence_payload, "schema_version"),
            topic_match_score=_required_int(confidence_payload, "topic_match_score"),
            scope_match_score=_required_int(confidence_payload, "scope_match_score"),
            execution_risk_score=_required_int(confidence_payload, "execution_risk_score"),
            excluded_domain_score=_required_int(confidence_payload, "excluded_domain_score"),
            ambiguity_score=_required_int(confidence_payload, "ambiguity_score"),
            final_confidence=_required_int(confidence_payload, "final_confidence"),
            authority_status=_required_str(confidence_payload, "authority_status"),
        )
        retrieval_payload = payload["retrieval_request"]
        retrieval_request = None
        if retrieval_payload is not None:
            if not isinstance(retrieval_payload, Mapping):
                raise TypeError("retrieval request must be a mapping")
            _require_exact_fields(
                retrieval_payload,
                _RETRIEVAL_REQUEST_FIELDS,
                "FORGED_ROUTE_PROPOSAL",
            )
            retrieval_request = UnixRetrievalRequestMetadata(
                schema_version=_required_str(retrieval_payload, "schema_version"),
                normalized_query=_required_str(retrieval_payload, "normalized_query"),
                query_hash=_required_str(retrieval_payload, "query_hash"),
                index_manifest_hash=_required_str(retrieval_payload, "index_manifest_hash"),
                requested_result_limit=_required_int(retrieval_payload, "requested_result_limit"),
                required_provenance_policy=_required_str(retrieval_payload, "required_provenance_policy"),
                required_retrieval_adapter_version=_required_str(retrieval_payload, "required_retrieval_adapter_version"),
                execution_allowed=_required_bool(retrieval_payload, "execution_allowed"),
                requires_explicit_caller=_required_bool(retrieval_payload, "requires_explicit_caller"),
            )
        selected = payload["selected_hat_id"]
        if selected is not None and not isinstance(selected, str):
            raise TypeError("selected Hat ID must be text or null")
        return UnixRouteProposal(
            schema_version=_required_str(payload, "schema_version"),
            request_id=_required_str(payload, "request_id"),
            query_hash=_required_str(payload, "query_hash"),
            route_status=_required_str(payload, "route_status"),
            selected_hat_id=selected,
            hat_descriptor_hash=_required_str(payload, "hat_descriptor_hash"),
            corpus_manifest_hash=_required_str(payload, "corpus_manifest_hash"),
            retrieval_index_hash=_required_str(payload, "retrieval_index_hash"),
            retrieval_adapter_version=_required_str(payload, "retrieval_adapter_version"),
            route_rationale=_required_str(payload, "route_rationale"),
            matched_topics=_required_string_tuple(payload, "matched_topics"),
            excluded_signals=_required_string_tuple(payload, "excluded_signals"),
            confidence_metadata=confidence,
            retrieval_request=retrieval_request,
            warnings=_required_string_tuple(payload, "warnings"),
            authority_status=_required_str(payload, "authority_status"),
            proposal_hash=_required_str(payload, "proposal_hash"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise UnixHatRoutingError("FORGED_ROUTE_PROPOSAL", "proposal fields are malformed") from exc


def _validate_route_request(request: UnixRouteRequest) -> None:
    if type(request) is not UnixRouteRequest:
        raise UnixHatRoutingError("INVALID_REQUEST", "request type is invalid")
    rebuilt = create_unix_route_request(
        request.raw_query,
        requested_limit=request.requested_limit,
        context_metadata={key: json.loads(value) for key, value in request.context_metadata},
    )
    if rebuilt != request:
        raise UnixHatRoutingError("INVALID_REQUEST", "request hash or fields do not verify")


def _confidence_metadata(
    status: str,
    matched_topics: tuple[str, ...],
    execution_signals: tuple[str, ...],
    excluded_signals: tuple[str, ...],
    ambiguous: bool,
) -> UnixRouteConfidenceMetadata:
    topic_score = min(6_000, len(matched_topics) * 1_200)
    scope_score = 2_000 if matched_topics else 0
    execution_score = 10_000 if execution_signals else 0
    excluded_score = min(10_000, len(excluded_signals) * 5_000)
    ambiguity_score = 8_000 if ambiguous else 0
    if status == ROUTE_TO_UNIX_KNOWLEDGE:
        final = min(10_000, topic_score + scope_score)
    elif status == EXECUTION_REQUEST_BLOCKED:
        final = execution_score
    elif status == REVIEW_NEEDED:
        final = ambiguity_score
    else:
        final = max(excluded_score, 0)
    return UnixRouteConfidenceMetadata(
        schema_version=UNIX_CONFIDENCE_SCHEMA_VERSION,
        topic_match_score=topic_score,
        scope_match_score=scope_score,
        execution_risk_score=execution_score,
        excluded_domain_score=excluded_score,
        ambiguity_score=ambiguity_score,
        final_confidence=final,
    )


def _match_topics(normalized: str) -> tuple[str, ...]:
    padded = f" {normalized} "
    matched = []
    for topic, terms in _TOPIC_TERMS:
        if any(f" {term} " in padded for term in terms):
            matched.append(topic)
    return tuple(sorted(matched))


def _match_execution_signals(normalized: str) -> tuple[str, ...]:
    tokens = normalized.split()
    signals = [phrase.strip() for phrase in _EXECUTION_PHRASES if phrase in normalized]
    if tokens and tokens[0] in _EXECUTION_FIRST_TOKENS:
        signals.append(f"imperative:{tokens[0]}")
    if {"git", "push"}.issubset(tokens):
        signals.append("version-control-publish-operation")
    return tuple(sorted(set(signals)))


def _looks_like_system_operation(normalized: str) -> bool:
    operation_terms = ("apt", "chmod", "curl", "git", "linux", "package", "rm", "server", "shell", "sudo", "system")
    padded = f" {normalized} "
    return any(f" {term} " in padded for term in operation_terms)


def _normalize_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    characters = [
        character if character.isalnum() else " "
        for character in normalized
    ]
    return " ".join("".join(characters).split())


def _freeze_context(context: Mapping[str, Any] | None) -> tuple[tuple[str, str], ...]:
    if context is None:
        return ()
    if not isinstance(context, Mapping):
        raise UnixHatRoutingError("INVALID_REQUEST", "context metadata must be a mapping")
    if len(context) > MAX_CONTEXT_FIELDS:
        raise UnixHatRoutingError("INVALID_REQUEST", "context metadata has too many fields")
    frozen = []
    for key in sorted(context):
        if not isinstance(key, str) or not key or len(key) > 128:
            raise UnixHatRoutingError("INVALID_REQUEST", "context metadata key is invalid")
        _validate_inert_json_value(context[key], depth=0)
        encoded = json.dumps(
            context[key],
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        frozen.append((key, encoded))
    result = tuple(frozen)
    if len(_canonical_bytes([list(item) for item in result])) > MAX_CONTEXT_BYTES:
        raise UnixHatRoutingError("INVALID_REQUEST", "context metadata is too large")
    return result


def _validate_inert_json_value(value: Any, *, depth: int) -> None:
    if depth > MAX_CONTEXT_DEPTH:
        raise UnixHatRoutingError("INVALID_REQUEST", "context metadata is too deeply nested")
    if callable(value) or isinstance(value, types.ModuleType):
        raise UnixHatRoutingError("INVALID_REQUEST", "context metadata contains executable data")
    if value is None or type(value) in (bool, int, float, str):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise UnixHatRoutingError("INVALID_REQUEST", "context metadata contains non-finite data")
        return
    if isinstance(value, list):
        for item in value:
            _validate_inert_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise UnixHatRoutingError("INVALID_REQUEST", "context object keys must be text")
        for key in sorted(value):
            _validate_inert_json_value(value[key], depth=depth + 1)
        return
    raise UnixHatRoutingError("INVALID_REQUEST", "context metadata is not inert JSON data")


def _iter_values(value: Any):
    if hasattr(value, "__dataclass_fields__") and not isinstance(value, type):
        for name in value.__dataclass_fields__:
            yield from _iter_values(getattr(value, name))
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _iter_values(key)
            yield from _iter_values(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from _iter_values(item)
        return
    yield value


def _verify_non_authority_flags(payload: Mapping[str, Any], status: str) -> None:
    if payload.get("authority_status") != NON_AUTHORITATIVE:
        raise UnixHatRoutingError(status, "authority status is invalid")
    if any(payload.get(name) is not expected for name, expected in _AUTHORITY_FLAGS.items()):
        raise UnixHatRoutingError(status, "authority flags are invalid")


def _require_exact_fields(payload: Mapping[str, Any], fields: set[str], status: str) -> None:
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise UnixHatRoutingError(status, "object fields do not match the schema")


def _required_str(payload: Mapping[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str):
        raise TypeError(field)
    return value


def _required_int(payload: Mapping[str, Any], field: str) -> int:
    value = payload[field]
    if type(value) is not int:
        raise TypeError(field)
    return value


def _required_bool(payload: Mapping[str, Any], field: str) -> bool:
    value = payload[field]
    if type(value) is not bool:
        raise TypeError(field)
    return value


def _required_string_tuple(payload: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = payload[field]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(field)
    return tuple(value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
