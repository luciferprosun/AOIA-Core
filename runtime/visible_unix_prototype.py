"""Offline, read-only UNIX Knowledge Unit review prototype.

Runtime query functions in this module read verified local artifacts and return
immutable presentation metadata. They do not write, dispatch, execute, call a
provider, use the network, or connect to an approval boundary. Demo persistence
is an explicit, separate build operation restricted to a caller-supplied root.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
import types
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from runtime.memory_hats.unix_hat import (
    EXECUTION_REQUEST_BLOCKED,
    NO_ROUTE,
    NON_AUTHORITATIVE,
    REVIEW_NEEDED,
    ROUTE_TO_UNIX_KNOWLEDGE,
    UnixHatDescriptor,
    UnixHatRoutingError,
    UnixRouteProposal,
    create_unix_hat_descriptor,
    create_unix_route_request,
    propose_unix_route,
    routing_policy_manifest_payload,
    unix_hat_descriptor_from_payload,
)
from runtime.retrieval.unix_runtime_adapter import (
    UnixRetrievalFailure,
    UnixRetrievalResult,
    retrieve_unix_knowledge,
    unix_retrieval_result_hash,
    verify_unix_retrieval_index,
)


PROTOTYPE_SCHEMA_VERSION = "visible-unix-review-model-1a"
DEMO_MANIFEST_SCHEMA_VERSION = "visible-unix-demo-manifest-1a"
DEMO_VERIFICATION_SCHEMA_VERSION = "visible-unix-demo-verification-1a"
EXECUTION_STATUS = "NO_COMMAND_OR_ACTION_EXECUTED"
SPONSOR_EXPLANATION = (
    "AOIA-Core UNIX Knowledge Unit is a local-first, deterministic, "
    "human-controlled knowledge and review layer. It can classify UNIX "
    "knowledge questions, select an inert UNIX Hat, retrieve locally indexed "
    "evidence and explain provenance and scoring. It does not execute "
    "commands and does not grant authority."
)
EXPECTED_CORPUS_MANIFEST_HASH = (
    "e7241f0d043d90bf79a3f1a9f2691691a1d87b719d39cc533c9a765d97a61768"
)
EXPECTED_INDEX_MANIFEST_HASH = (
    "3703dce3476b9c482515c3454f41a563c19f0f9ad21723fc61945434e79f7745"
)
EXPECTED_HAT_DESCRIPTOR_HASH = (
    "24850bfb838488d8b7839a518cd2a8d702b8b266397edbbcb0fc5f7a4ba78a0c"
)
EXPECTED_ROUTING_POLICY_VERSION = "deterministic-unix-routing-policy-1a"
MAX_UPSTREAM_JSON_BYTES = 16 * 1024 * 1024
MAX_DEMO_FILE_BYTES = 32 * 1024 * 1024
_SAFE_OUTPUT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_AUTHORITY_FLAGS = {
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
    "gate_satisfied": False,
}

ACTUAL_DEMO_QUERIES: tuple[tuple[str, str, str], ...] = (
    (
        "unix_file_permissions",
        "How do UNIX file permissions work?",
        ROUTE_TO_UNIX_KNOWLEDGE,
    ),
    (
        "path_traversal",
        "Explain path traversal.",
        ROUTE_TO_UNIX_KNOWLEDGE,
    ),
    (
        "process_signals",
        "How do process signals work?",
        ROUTE_TO_UNIX_KNOWLEDGE,
    ),
    (
        "execution_blocked",
        "Run sudo apt install curl.",
        EXECUTION_REQUEST_BLOCKED,
    ),
    (
        "no_route",
        "Explain stellar nucleosynthesis.",
        NO_ROUTE,
    ),
    (
        "review_needed",
        "Fix my system.",
        REVIEW_NEEDED,
    ),
)


class VisibleUnixPrototypeError(ValueError):
    """Controlled fail-closed error for visible prototype validation."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True, slots=True)
class VisibleUnixUpstreamPaths:
    corpus_manifest_path: Path
    records_path: Path
    index_root: Path
    hat_descriptor_path: Path
    routing_policy_path: Path
    benchmark_path: Path


@dataclass(frozen=True, slots=True)
class VisibleUnixBenchmarkSummary:
    corpus_record_count: int
    index_total_bytes: int
    index_build_wall_time_ns: int
    index_build_peak_memory_bytes: int
    query_p50_latency_ns: int
    query_p95_latency_ns: int
    query_max_latency_ns: int
    authority_status: str


@dataclass(frozen=True, slots=True)
class VerifiedVisibleUnixUpstream:
    paths: VisibleUnixUpstreamPaths
    descriptor: UnixHatDescriptor
    corpus_record_count: int
    routing_policy_hash: str
    benchmark_summary: VisibleUnixBenchmarkSummary


@dataclass(frozen=True, slots=True)
class VisibleUnixRouteConfidence:
    topic_match_score: int
    scope_match_score: int
    execution_risk_score: int
    excluded_domain_score: int
    ambiguity_score: int
    final_confidence: int
    authority_status: str


@dataclass(frozen=True, slots=True)
class VisibleUnixHatSummary:
    hat_id: str
    display_name: str
    description: str
    supported_topics: tuple[str, ...]
    excluded_topics: tuple[str, ...]
    corpus_manifest_hash: str
    retrieval_index_hash: str
    capability_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    descriptor_hash: str
    authority_status: str


@dataclass(frozen=True, slots=True)
class VisibleUnixRetrievalRequestSummary:
    normalized_query: str
    query_hash: str
    index_manifest_hash: str
    requested_result_limit: int
    provenance_policy: str
    retrieval_adapter_version: str
    routing_invoked_retrieval: bool
    requires_explicit_caller: bool
    execution_allowed: bool


@dataclass(frozen=True, slots=True)
class VisibleUnixScoreExplanation:
    rank: int
    record_id: str
    exact_phrase_score: int
    title_score: int
    heading_score: int
    token_overlap_score: int
    term_frequency_score: int
    source_quality_score: int
    provenance_score: int
    risk_adjustment: int
    staleness_adjustment: int
    pheromone_adjustment: int
    final_score: int


@dataclass(frozen=True, slots=True)
class VisibleUnixProvenanceSummary:
    rank: int
    record_id: str
    source_id: str
    source_locator: str
    source_hash: str
    record_content_hash: str
    corpus_manifest_hash: str
    index_manifest_hash: str
    record_ordinal: int
    ingestion_schema_version: str
    normalization_version: str


@dataclass(frozen=True, slots=True)
class VisibleUnixCandidate:
    rank: int
    title: str
    excerpt: str
    excerpt_truncated: bool
    record_id: str
    source_id: str
    source_locator: str
    final_score: int
    score_breakdown: VisibleUnixScoreExplanation
    provenance: VisibleUnixProvenanceSummary
    warnings: tuple[str, ...]
    authority_status: str


@dataclass(frozen=True, slots=True)
class VisibleUnixRiskSummary:
    status: str
    execution_request_blocked: bool
    excluded_signals: tuple[str, ...]
    command_looking_text_is_inert: bool
    provider_calls: str
    network_calls: str
    filesystem_mutations_during_query: str
    authority_status: str


@dataclass(frozen=True, slots=True)
class VisibleUnixStalenessSummary:
    status: str
    reason: str
    staleness_adjustment: int
    evaluation_context: str
    authority_status: str


@dataclass(frozen=True, slots=True)
class VisibleUnixReviewModel:
    schema_version: str
    request_id: str
    raw_query: str
    normalized_query: str
    query_hash: str
    route_status: str
    selected_hat_id: str | None
    route_rationale: str
    route_proposal_hash: str
    route_confidence: VisibleUnixRouteConfidence
    unix_hat_summary: VisibleUnixHatSummary
    retrieval_request_summary: VisibleUnixRetrievalRequestSummary | None
    retrieval_status: str
    retrieval_result_hash: str | None
    retrieval_candidates: tuple[VisibleUnixCandidate, ...]
    score_explanations: tuple[VisibleUnixScoreExplanation, ...]
    provenance_summary: tuple[VisibleUnixProvenanceSummary, ...]
    risk_summary: VisibleUnixRiskSummary
    staleness_summary: VisibleUnixStalenessSummary
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    benchmark_summary: VisibleUnixBenchmarkSummary
    corpus_record_count: int
    execution_status: str
    authority_status: str
    corpus_manifest_hash: str
    index_manifest_hash: str
    unix_hat_descriptor_hash: str
    routing_policy_version: str
    review_model_hash: str


@dataclass(frozen=True, slots=True)
class VisibleUnixDemoVerification:
    valid: bool
    status: str
    reason: str
    file_count: int
    total_bytes: int
    demo_manifest_hash: str | None
    authority_status: str = NON_AUTHORITATIVE


def default_visible_unix_upstream_paths() -> VisibleUnixUpstreamPaths:
    root = Path(__file__).resolve().parents[1]
    return VisibleUnixUpstreamPaths(
        corpus_manifest_path=(
            root / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json"
        ),
        records_path=root / "data/unix_corpus_ingestion_1b/intake/records",
        index_root=root / "data/unix_retrieval_adapter_1a/index",
        hat_descriptor_path=(
            root / "data/unix_hat_routing_1a/unix_hat_descriptor.json"
        ),
        routing_policy_path=(
            root / "data/unix_hat_routing_1a/routing_policy_manifest.json"
        ),
        benchmark_path=root / "data/unix_retrieval_adapter_1a/benchmark.json",
    )


def verify_visible_unix_upstream(
    paths: VisibleUnixUpstreamPaths | None = None,
) -> VerifiedVisibleUnixUpstream:
    selected = paths or default_visible_unix_upstream_paths()
    if type(selected) is not VisibleUnixUpstreamPaths:
        raise VisibleUnixPrototypeError(
            "UPSTREAM_INVALID",
            "upstream paths object is invalid",
        )
    corpus = _read_canonical_object(
        selected.corpus_manifest_path,
        "CORPUS_MANIFEST_INVALID",
    )
    index = _read_canonical_object(
        selected.index_root / "index_manifest.json",
        "INDEX_MANIFEST_INVALID",
    )
    descriptor_payload = _read_canonical_object(
        selected.hat_descriptor_path,
        "UNIX_HAT_DESCRIPTOR_INVALID",
    )
    policy = _read_canonical_object(
        selected.routing_policy_path,
        "ROUTING_POLICY_INVALID",
    )
    benchmark = _read_canonical_object(
        selected.benchmark_path,
        "BENCHMARK_INVALID",
    )

    if corpus.get("manifest_hash") != EXPECTED_CORPUS_MANIFEST_HASH:
        raise VisibleUnixPrototypeError(
            "CORPUS_MANIFEST_INVALID",
            "corpus manifest hash differs",
        )
    if index.get("index_hash") != EXPECTED_INDEX_MANIFEST_HASH:
        raise VisibleUnixPrototypeError(
            "INDEX_MANIFEST_INVALID",
            "index manifest hash differs",
        )
    verification = verify_unix_retrieval_index(
        selected.index_root,
        selected.corpus_manifest_path,
        selected.records_path,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
    )
    if not verification.valid or verification.manifest is None:
        raise VisibleUnixPrototypeError(
            "INDEX_MANIFEST_INVALID",
            verification.reason,
        )
    descriptor = unix_hat_descriptor_from_payload(
        descriptor_payload,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        expected_index_manifest_hash=EXPECTED_INDEX_MANIFEST_HASH,
    )
    expected_descriptor = create_unix_hat_descriptor(
        corpus,
        index,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        expected_index_manifest_hash=EXPECTED_INDEX_MANIFEST_HASH,
    )
    if descriptor != expected_descriptor:
        raise VisibleUnixPrototypeError(
            "UNIX_HAT_DESCRIPTOR_INVALID",
            "descriptor does not match verified manifests",
        )
    if descriptor.descriptor_hash != EXPECTED_HAT_DESCRIPTOR_HASH:
        raise VisibleUnixPrototypeError(
            "UNIX_HAT_DESCRIPTOR_INVALID",
            "descriptor hash differs",
        )
    if policy != routing_policy_manifest_payload(descriptor):
        raise VisibleUnixPrototypeError(
            "ROUTING_POLICY_INVALID",
            "routing policy does not match descriptor and canonical policy",
        )
    if descriptor.routing_policy_version != EXPECTED_ROUTING_POLICY_VERSION:
        raise VisibleUnixPrototypeError(
            "ROUTING_POLICY_INVALID",
            "routing policy version differs",
        )
    benchmark_summary = _benchmark_summary(benchmark)
    if benchmark.get("corpus_manifest_hash") != EXPECTED_CORPUS_MANIFEST_HASH:
        raise VisibleUnixPrototypeError(
            "BENCHMARK_INVALID",
            "benchmark corpus binding differs",
        )
    if benchmark.get("index_hash") != EXPECTED_INDEX_MANIFEST_HASH:
        raise VisibleUnixPrototypeError(
            "BENCHMARK_INVALID",
            "benchmark index binding differs",
        )
    if benchmark_summary.corpus_record_count != corpus.get("record_count"):
        raise VisibleUnixPrototypeError(
            "BENCHMARK_INVALID",
            "benchmark record count differs",
        )
    return VerifiedVisibleUnixUpstream(
        paths=selected,
        descriptor=descriptor,
        corpus_record_count=_strict_int(corpus, "record_count"),
        routing_policy_hash=_strict_text(policy, "policy_hash"),
        benchmark_summary=benchmark_summary,
    )


def build_visible_unix_review_model(
    raw_query: str,
    *,
    requested_limit: int = 5,
    upstream: VerifiedVisibleUnixUpstream | None = None,
) -> VisibleUnixReviewModel:
    verified = upstream or verify_visible_unix_upstream()
    request = create_unix_route_request(
        raw_query,
        requested_limit=requested_limit,
    )
    proposal = propose_unix_route(request, verified.descriptor)

    retrieval_result: UnixRetrievalResult | UnixRetrievalFailure | None = None
    if proposal.route_status == ROUTE_TO_UNIX_KNOWLEDGE:
        retrieval_request = proposal.retrieval_request
        if retrieval_request is None:
            raise VisibleUnixPrototypeError(
                "ROUTE_RETRIEVAL_MISMATCH",
                "knowledge route lacks inert retrieval request metadata",
            )
        retrieval_result = retrieve_unix_knowledge(
            verified.paths.index_root,
            verified.paths.corpus_manifest_path,
            verified.paths.records_path,
            retrieval_request.normalized_query,
            requested_limit=retrieval_request.requested_result_limit,
            evaluation_context="VISIBLE_UNIX_PROTOTYPE_1A",
            expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        )

    return _assemble_review_model(
        request=request,
        proposal=proposal,
        descriptor=verified.descriptor,
        retrieval_result=retrieval_result,
        benchmark=verified.benchmark_summary,
        corpus_record_count=verified.corpus_record_count,
    )


def run_visible_unix_query(
    raw_query: str,
    *,
    requested_limit: int = 5,
    paths: VisibleUnixUpstreamPaths | None = None,
) -> VisibleUnixReviewModel:
    """Run the verified, offline, read-only review flow entirely in memory."""

    return build_visible_unix_review_model(
        raw_query,
        requested_limit=requested_limit,
        upstream=verify_visible_unix_upstream(paths),
    )


def verify_visible_unix_review_model(
    model: VisibleUnixReviewModel,
) -> None:
    if type(model) is not VisibleUnixReviewModel:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model type is invalid",
        )
    _validate_review_model_types(model)
    if model.schema_version != PROTOTYPE_SCHEMA_VERSION:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model schema is unsupported",
        )
    if model.authority_status != NON_AUTHORITATIVE:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model authority status is invalid",
        )
    if model.execution_status != EXECUTION_STATUS:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model execution status is invalid",
        )
    if (
        model.corpus_manifest_hash != EXPECTED_CORPUS_MANIFEST_HASH
        or model.index_manifest_hash != EXPECTED_INDEX_MANIFEST_HASH
        or model.unix_hat_descriptor_hash != EXPECTED_HAT_DESCRIPTOR_HASH
        or model.routing_policy_version != EXPECTED_ROUTING_POLICY_VERSION
    ):
        raise VisibleUnixPrototypeError(
            "UPSTREAM_BINDING_MISMATCH",
            "review model upstream binding differs",
        )
    if model.unix_hat_summary.capability_ids:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "UNIX Hat capability set is not empty",
        )
    for value in _iter_values(model):
        if callable(value) or isinstance(value, types.ModuleType):
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "review model contains executable data",
            )
    if model.route_status == ROUTE_TO_UNIX_KNOWLEDGE:
        if model.retrieval_request_summary is None:
            raise VisibleUnixPrototypeError(
                "ROUTE_RETRIEVAL_MISMATCH",
                "knowledge route lacks retrieval request summary",
            )
        if model.retrieval_status not in {"OK", "NO_CONFIDENT_RESULT"}:
            raise VisibleUnixPrototypeError(
                "ROUTE_RETRIEVAL_MISMATCH",
                "knowledge route retrieval status is invalid",
            )
        request = model.retrieval_request_summary
        if (
            request.routing_invoked_retrieval
            or not request.requires_explicit_caller
            or request.execution_allowed
            or request.index_manifest_hash != model.index_manifest_hash
        ):
            raise VisibleUnixPrototypeError(
                "ROUTE_RETRIEVAL_MISMATCH",
                "retrieval request summary violates separation",
            )
    else:
        if (
            model.retrieval_request_summary is not None
            or model.retrieval_status != "NOT_PERFORMED"
            or model.retrieval_result_hash is not None
            or model.retrieval_candidates
        ):
            raise VisibleUnixPrototypeError(
                "ROUTE_RETRIEVAL_MISMATCH",
                "non-route model contains retrieval output",
            )
    if model.route_status == EXECUTION_REQUEST_BLOCKED:
        if not model.risk_summary.execution_request_blocked:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "execution block is not visible in risk summary",
            )
    elif model.risk_summary.execution_request_blocked:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "risk summary falsely marks execution blocked",
        )
    if len(model.retrieval_candidates) != len(model.score_explanations):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "candidate and score counts differ",
        )
    if len(model.retrieval_candidates) != len(model.provenance_summary):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "candidate and provenance counts differ",
        )
    for expected_rank, candidate in enumerate(model.retrieval_candidates, start=1):
        if candidate.rank != expected_rank:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate ranks are not contiguous",
            )
        if candidate.authority_status != NON_AUTHORITATIVE:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate authority status is invalid",
            )
        if candidate.score_breakdown != model.score_explanations[expected_rank - 1]:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate score summary differs",
            )
        if candidate.provenance != model.provenance_summary[expected_rank - 1]:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate provenance summary differs",
            )
        if (
            candidate.provenance.corpus_manifest_hash
            != model.corpus_manifest_hash
            or candidate.provenance.index_manifest_hash
            != model.index_manifest_hash
            or candidate.provenance.record_id != candidate.record_id
            or candidate.provenance.source_id != candidate.source_id
            or candidate.provenance.source_locator != candidate.source_locator
            or candidate.score_breakdown.final_score != candidate.final_score
        ):
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate binding differs",
            )
    payload = visible_unix_review_model_payload(model)
    supplied_hash = payload.pop("review_model_hash")
    if not _is_sha256(supplied_hash):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_HASH_MISMATCH",
            "review model hash is malformed",
        )
    if supplied_hash != _sha256(_canonical_bytes(payload)):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_HASH_MISMATCH",
            "review model hash does not verify",
        )


def visible_unix_review_model_payload(
    model: VisibleUnixReviewModel,
) -> dict[str, Any]:
    if type(model) is not VisibleUnixReviewModel:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model type is invalid",
        )
    return _to_data(model)


def visible_unix_review_model_from_payload(
    payload: Mapping[str, Any],
) -> VisibleUnixReviewModel:
    _require_exact_fields(payload, VisibleUnixReviewModel, "REVIEW_MODEL_INVALID")
    try:
        confidence = _simple_from_payload(
            VisibleUnixRouteConfidence,
            payload["route_confidence"],
        )
        hat = _simple_from_payload(
            VisibleUnixHatSummary,
            payload["unix_hat_summary"],
            tuple_fields=("supported_topics", "excluded_topics", "capability_ids", "limitations"),
        )
        retrieval_request_payload = payload["retrieval_request_summary"]
        retrieval_request = None
        if retrieval_request_payload is not None:
            retrieval_request = _simple_from_payload(
                VisibleUnixRetrievalRequestSummary,
                retrieval_request_payload,
            )
        candidates = []
        for item in _required_list(payload, "retrieval_candidates"):
            _require_mapping(item, "retrieval candidate")
            score = _simple_from_payload(
                VisibleUnixScoreExplanation,
                item["score_breakdown"],
            )
            provenance = _simple_from_payload(
                VisibleUnixProvenanceSummary,
                item["provenance"],
            )
            candidate_payload = dict(item)
            candidate_payload["score_breakdown"] = score
            candidate_payload["provenance"] = provenance
            candidate_payload["warnings"] = tuple(candidate_payload["warnings"])
            _require_exact_fields(
                candidate_payload,
                VisibleUnixCandidate,
                "REVIEW_MODEL_INVALID",
            )
            candidates.append(VisibleUnixCandidate(**candidate_payload))
        scores = tuple(
            _simple_from_payload(VisibleUnixScoreExplanation, item)
            for item in _required_list(payload, "score_explanations")
        )
        provenance = tuple(
            _simple_from_payload(VisibleUnixProvenanceSummary, item)
            for item in _required_list(payload, "provenance_summary")
        )
        risk = _simple_from_payload(
            VisibleUnixRiskSummary,
            payload["risk_summary"],
            tuple_fields=("excluded_signals",),
        )
        staleness = _simple_from_payload(
            VisibleUnixStalenessSummary,
            payload["staleness_summary"],
        )
        benchmark = _simple_from_payload(
            VisibleUnixBenchmarkSummary,
            payload["benchmark_summary"],
        )
        values = dict(payload)
        values.update(
            {
                "benchmark_summary": benchmark,
                "limitations": tuple(values["limitations"]),
                "provenance_summary": provenance,
                "retrieval_candidates": tuple(candidates),
                "retrieval_request_summary": retrieval_request,
                "risk_summary": risk,
                "route_confidence": confidence,
                "score_explanations": scores,
                "staleness_summary": staleness,
                "unix_hat_summary": hat,
                "warnings": tuple(values["warnings"]),
            }
        )
        model = VisibleUnixReviewModel(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model fields are malformed",
        ) from exc
    verify_visible_unix_review_model(model)
    return model


def render_visible_unix_text(model: VisibleUnixReviewModel) -> str:
    verify_visible_unix_review_model(model)
    lines = [
        "AOIA-Core Visible UNIX Prototype 1A",
        SPONSOR_EXPLANATION,
        "",
        "Authority status: NON_AUTHORITATIVE",
        "Execution status: NO_COMMAND_OR_ACTION_EXECUTED",
        "UNIX Hat capabilities: none",
        "Provider calls: none",
        "Network calls: none",
        "Filesystem mutations during query: none",
        "",
        "Stage 1 — Query",
        f"Raw query: {model.raw_query}",
        f"Normalized query: {model.normalized_query}",
        f"Query hash: {model.query_hash}",
        f"Request ID: {model.request_id}",
        "",
        "Stage 2 — Route classification",
        f"Route status: {model.route_status}",
        f"Selected Hat ID: {model.selected_hat_id or 'none'}",
        f"Route rationale: {model.route_rationale}",
        f"Route proposal hash: {model.route_proposal_hash}",
        f"Excluded/risk signals: {_joined(model.risk_summary.excluded_signals)}",
        "Confidence breakdown:",
    ]
    for name, value in _confidence_rows(model.route_confidence):
        lines.append(f"  {name}: {value}")
    hat = model.unix_hat_summary
    lines.extend(
        (
            "",
            "Stage 3 — UNIX Hat",
            f"Hat ID: {hat.hat_id}",
            f"Display name: {hat.display_name}",
            f"Description: {hat.description}",
            f"Supported scope: {_joined(hat.supported_topics)}",
            f"Excluded scope: {_joined(hat.excluded_topics)}",
            f"Corpus binding: {hat.corpus_manifest_hash}",
            f"Index binding: {hat.retrieval_index_hash}",
            "Capability IDs: none",
            f"Descriptor hash: {hat.descriptor_hash}",
            f"Limitations: {_joined(hat.limitations)}",
            "",
            "Stage 4 — Retrieval request",
        )
    )
    if model.retrieval_request_summary is None:
        lines.append("Retrieval request: none; retrieval was not performed.")
    else:
        request = model.retrieval_request_summary
        lines.extend(
            (
                f"Normalized query: {request.normalized_query}",
                f"Index hash: {request.index_manifest_hash}",
                f"Requested limit: {request.requested_result_limit}",
                f"Provenance policy: {request.provenance_policy}",
                f"Retrieval adapter version: {request.retrieval_adapter_version}",
                "Routing invoked retrieval: no",
                "Retrieval required a separate explicit caller: yes",
            )
        )
    lines.extend(("", "Stage 5 — Retrieval results"))
    lines.append(f"Retrieval status: {model.retrieval_status}")
    if not model.retrieval_candidates:
        lines.append("Candidates: none")
    for candidate in model.retrieval_candidates:
        lines.extend(
            (
                f"Result {candidate.rank}",
                f"  Title: {candidate.title}",
                f"  Excerpt: {candidate.excerpt}",
                f"  Record ID: {candidate.record_id}",
                f"  Source ID: {candidate.source_id}",
                f"  Source locator: {candidate.source_locator}",
                f"  Source hash: {candidate.provenance.source_hash}",
                f"  Record content hash: {candidate.provenance.record_content_hash}",
                f"  Corpus manifest hash: {candidate.provenance.corpus_manifest_hash}",
                f"  Index manifest hash: {candidate.provenance.index_manifest_hash}",
                f"  Final score: {candidate.final_score}",
                f"  Score breakdown: {_score_text(candidate.score_breakdown)}",
                f"  Staleness: {model.staleness_summary.status} — {model.staleness_summary.reason}",
                f"  Warnings: {_joined(candidate.warnings)}",
                "  Authority status: NON_AUTHORITATIVE",
            )
        )
    lines.extend(
        (
            "",
            "Sponsor review metadata",
            f"Corpus record count: {model.corpus_record_count}",
            f"Corpus manifest hash: {model.corpus_manifest_hash}",
            f"Retrieval index hash: {model.index_manifest_hash}",
            f"UNIX Hat descriptor hash: {model.unix_hat_descriptor_hash}",
            f"Routing policy version: {model.routing_policy_version}",
            "Test baseline reference: 3146 passed, 4 skipped before this step",
            f"Measured benchmark: {_benchmark_text(model.benchmark_summary)}",
            f"Warnings: {_joined(model.warnings)}",
            f"Limitations: {_joined(model.limitations)}",
            "",
            "Stage 6 — Safety conclusion",
            "NO COMMAND OR ACTION WAS EXECUTED",
            "THIS OUTPUT IS KNOWLEDGE AND REVIEW METADATA ONLY",
            f"Route safety status: {model.route_status}",
            "Authority status: NON_AUTHORITATIVE",
            "Execution status: NO_COMMAND_OR_ACTION_EXECUTED",
            "UNIX Hat capabilities: none",
            "Provider calls: none",
            "Network calls: none",
            "Filesystem mutations during query: none",
        )
    )
    if model.route_status == EXECUTION_REQUEST_BLOCKED:
        lines.append("EXECUTION REQUEST BLOCKED")
    return "\n".join(lines) + "\n"


def render_visible_unix_html(model: VisibleUnixReviewModel) -> str:
    verify_visible_unix_review_model(model)
    body = _model_html_sections(model)
    return _html_document(
        title="AOIA-Core Visible UNIX Prototype 1A",
        body=body,
    )


def build_visible_unix_demo_payloads(
    paths: VisibleUnixUpstreamPaths | None = None,
) -> dict[str, bytes]:
    upstream = verify_visible_unix_upstream(paths)
    models = tuple(
        (
            slug,
            expected_status,
            build_visible_unix_review_model(query, upstream=upstream),
        )
        for slug, query, expected_status in ACTUAL_DEMO_QUERIES
    )
    for _slug, expected_status, model in models:
        if model.route_status != expected_status:
            raise VisibleUnixPrototypeError(
                "DEMO_ROUTE_MISMATCH",
                "actual demo route status differs",
            )

    base: dict[str, bytes] = {
        "demo.txt": "\n".join(
            render_visible_unix_text(model).rstrip("\n")
            for _slug, _status, model in models
        ).encode("utf-8") + b"\n",
        "index.html": _render_demo_index(models).encode("utf-8"),
    }
    for slug, _status, model in models:
        base[f"queries/{slug}.html"] = render_visible_unix_html(model).encode("utf-8")
        base[f"review_models/{slug}.json"] = (
            _canonical_bytes(visible_unix_review_model_payload(model)) + b"\n"
        )
    file_records = [
        {
            "path": path,
            "sha256": _sha256(payload),
            "size_bytes": len(payload),
        }
        for path, payload in sorted(base.items())
    ]
    manifest_material = {
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "command_or_action_executed": False,
        "corpus_manifest_hash": EXPECTED_CORPUS_MANIFEST_HASH,
        "files": file_records,
        "index_manifest_hash": EXPECTED_INDEX_MANIFEST_HASH,
        "models": [
            {
                "query": query,
                "retrieval_result_hash": model.retrieval_result_hash,
                "review_model_hash": model.review_model_hash,
                "route_status": model.route_status,
                "slug": slug,
            }
            for (slug, query, _expected), (_model_slug, _status, model)
            in zip(ACTUAL_DEMO_QUERIES, models, strict=True)
        ],
        "routing_policy_version": EXPECTED_ROUTING_POLICY_VERSION,
        "schema_version": DEMO_MANIFEST_SCHEMA_VERSION,
        "unix_hat_descriptor_hash": EXPECTED_HAT_DESCRIPTOR_HASH,
    }
    manifest = {
        **manifest_material,
        "manifest_hash": _sha256(_canonical_bytes(manifest_material)),
    }
    manifest_bytes = _canonical_bytes(manifest) + b"\n"
    verification = {
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "command_or_action_executed": False,
        "demo_manifest_hash": manifest["manifest_hash"],
        "expected_file_count": len(base) + 2,
        "schema_version": DEMO_VERIFICATION_SCHEMA_VERSION,
        "status": "VERIFIED_DETERMINISTIC_OFFLINE_REVIEW_ARTIFACT",
    }
    return {
        **base,
        "demo_manifest.json": manifest_bytes,
        "verification.json": _canonical_bytes(verification) + b"\n",
    }


def materialize_visible_unix_demo(
    output_root: str | Path,
    *,
    allowed_parent: str | Path,
    paths: VisibleUnixUpstreamPaths | None = None,
) -> VisibleUnixDemoVerification:
    """Explicitly create a new demo root; runtime query functions never call it."""

    destination = _validated_new_demo_root(output_root, allowed_parent)
    payloads = build_visible_unix_demo_payloads(paths)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    for relative, payload in sorted(payloads.items()):
        _write_new_demo_file(destination, relative, payload)
    verification = verify_visible_unix_demo(destination, paths=paths)
    if not verification.valid:
        raise VisibleUnixPrototypeError(
            verification.status,
            verification.reason,
        )
    return verification


def verify_visible_unix_demo(
    demo_root: str | Path,
    *,
    paths: VisibleUnixUpstreamPaths | None = None,
) -> VisibleUnixDemoVerification:
    try:
        root = _existing_demo_root(demo_root)
        expected = build_visible_unix_demo_payloads(paths)
        discovered = tuple(root.rglob("*"))
        if any(path.is_symlink() for path in discovered):
            raise VisibleUnixPrototypeError(
                "DEMO_FILE_SET_MISMATCH",
                "demo contains a symbolic-link entry",
            )
        actual_paths = tuple(
            sorted(
                path.relative_to(root).as_posix()
                for path in discovered
                if path.is_file()
            )
        )
        if tuple(sorted(expected)) != actual_paths:
            raise VisibleUnixPrototypeError(
                "DEMO_FILE_SET_MISMATCH",
                "demo file set differs",
            )
        total = 0
        for relative, expected_bytes in sorted(expected.items()):
            path = root / PurePosixPath(relative)
            if path.is_symlink() or not path.is_file():
                raise VisibleUnixPrototypeError(
                    "DEMO_FILE_SET_MISMATCH",
                    "demo contains a missing or symbolic-link file",
                )
            actual = path.read_bytes()
            if len(actual) > MAX_DEMO_FILE_BYTES or actual != expected_bytes:
                raise VisibleUnixPrototypeError(
                    "DEMO_HASH_MISMATCH",
                    f"demo file differs: {relative}",
                )
            total += len(actual)
        manifest = json.loads(expected["demo_manifest.json"].decode("utf-8"))
        return VisibleUnixDemoVerification(
            valid=True,
            status="VALID",
            reason="all deterministic offline demo files verified",
            file_count=len(expected),
            total_bytes=total,
            demo_manifest_hash=manifest["manifest_hash"],
        )
    except (VisibleUnixPrototypeError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        status = getattr(exc, "status", "DEMO_INVALID")
        reason = getattr(exc, "reason", f"demo verification failed: {exc.__class__.__name__}")
        return VisibleUnixDemoVerification(
            valid=False,
            status=status,
            reason=reason,
            file_count=0,
            total_bytes=0,
            demo_manifest_hash=None,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline read-only UNIX Knowledge Unit review prototype.",
        allow_abbrev=False,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    query = commands.add_parser("query", help="render one read-only query")
    query.add_argument("--query", required=True)
    query.add_argument("--limit", type=int, default=5)
    query.add_argument("--format", choices=("text", "html", "json"), default="text")
    demo = commands.add_parser("render-demo", help="explicitly build a static demo")
    demo.add_argument("--output-root", required=True)
    verify = commands.add_parser("verify-demo", help="verify a static demo")
    verify.add_argument("--demo-root", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        if arguments.command == "query":
            model = run_visible_unix_query(
                arguments.query,
                requested_limit=arguments.limit,
            )
            if arguments.format == "html":
                print(render_visible_unix_html(model), end="")
            elif arguments.format == "json":
                print(
                    json.dumps(
                        visible_unix_review_model_payload(model),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
            else:
                print(render_visible_unix_text(model), end="")
            return 0
        if arguments.command == "render-demo":
            data_root = Path(__file__).resolve().parents[1] / "data"
            result = materialize_visible_unix_demo(
                arguments.output_root,
                allowed_parent=data_root,
            )
            print(json.dumps(_to_data(result), sort_keys=True, separators=(",", ":")))
            return 0
        result = verify_visible_unix_demo(arguments.demo_root)
        print(json.dumps(_to_data(result), sort_keys=True, separators=(",", ":")))
        return 0 if result.valid else 2
    except (VisibleUnixPrototypeError, UnixHatRoutingError, OSError, ValueError) as exc:
        payload = {
            "authority_status": NON_AUTHORITATIVE,
            "execution_status": EXECUTION_STATUS,
            "reason": getattr(exc, "reason", "invalid input"),
            "status": getattr(exc, "status", "INVALID_REQUEST"),
        }
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return 2


def _assemble_review_model(
    *,
    request: Any,
    proposal: UnixRouteProposal,
    descriptor: UnixHatDescriptor,
    retrieval_result: UnixRetrievalResult | UnixRetrievalFailure | None,
    benchmark: VisibleUnixBenchmarkSummary,
    corpus_record_count: int,
) -> VisibleUnixReviewModel:
    confidence = VisibleUnixRouteConfidence(
        topic_match_score=proposal.confidence_metadata.topic_match_score,
        scope_match_score=proposal.confidence_metadata.scope_match_score,
        execution_risk_score=proposal.confidence_metadata.execution_risk_score,
        excluded_domain_score=proposal.confidence_metadata.excluded_domain_score,
        ambiguity_score=proposal.confidence_metadata.ambiguity_score,
        final_confidence=proposal.confidence_metadata.final_confidence,
        authority_status=NON_AUTHORITATIVE,
    )
    hat = VisibleUnixHatSummary(
        hat_id=descriptor.hat_id,
        display_name=descriptor.display_name,
        description=descriptor.description,
        supported_topics=descriptor.supported_topics,
        excluded_topics=descriptor.excluded_topics,
        corpus_manifest_hash=descriptor.corpus_manifest_hash,
        retrieval_index_hash=descriptor.retrieval_index_hash,
        capability_ids=descriptor.capability_ids,
        limitations=descriptor.limitations,
        descriptor_hash=descriptor.descriptor_hash,
        authority_status=NON_AUTHORITATIVE,
    )
    request_summary = None
    if proposal.retrieval_request is not None:
        source = proposal.retrieval_request
        request_summary = VisibleUnixRetrievalRequestSummary(
            normalized_query=source.normalized_query,
            query_hash=source.query_hash,
            index_manifest_hash=source.index_manifest_hash,
            requested_result_limit=source.requested_result_limit,
            provenance_policy=source.required_provenance_policy,
            retrieval_adapter_version=source.required_retrieval_adapter_version,
            routing_invoked_retrieval=False,
            requires_explicit_caller=source.requires_explicit_caller,
            execution_allowed=source.execution_allowed,
        )

    candidates: list[VisibleUnixCandidate] = []
    retrieval_status = "NOT_PERFORMED"
    retrieval_hash = None
    staleness = VisibleUnixStalenessSummary(
        status="NOT_EVALUATED",
        reason="retrieval was not performed for this route status",
        staleness_adjustment=0,
        evaluation_context="VISIBLE_UNIX_PROTOTYPE_1A",
        authority_status=NON_AUTHORITATIVE,
    )
    retrieval_warnings: tuple[str, ...] = ()
    if isinstance(retrieval_result, UnixRetrievalFailure):
        retrieval_status = retrieval_result.status
        retrieval_hash = unix_retrieval_result_hash(retrieval_result)
        retrieval_warnings = (retrieval_result.reason,)
    elif isinstance(retrieval_result, UnixRetrievalResult):
        if (
            retrieval_result.authority_status != NON_AUTHORITATIVE
            or retrieval_result.command_or_action_executed
            or retrieval_result.corpus_manifest_hash != descriptor.corpus_manifest_hash
            or retrieval_result.index_hash != descriptor.retrieval_index_hash
        ):
            raise VisibleUnixPrototypeError(
                "RETRIEVAL_BINDING_MISMATCH",
                "retrieval result violates the visible review boundary",
            )
        retrieval_status = retrieval_result.status
        retrieval_hash = unix_retrieval_result_hash(retrieval_result)
        retrieval_warnings = retrieval_result.warnings
        staleness = VisibleUnixStalenessSummary(
            status=retrieval_result.decay_snapshot.status,
            reason=retrieval_result.decay_snapshot.reason,
            staleness_adjustment=(
                retrieval_result.decay_snapshot.staleness_adjustment
            ),
            evaluation_context=retrieval_result.decay_snapshot.evaluation_context,
            authority_status=NON_AUTHORITATIVE,
        )
        for rank, candidate in enumerate(retrieval_result.candidates, start=1):
            score = VisibleUnixScoreExplanation(
                rank=rank,
                record_id=candidate.record_id,
                exact_phrase_score=candidate.score_breakdown.exact_phrase_score,
                title_score=candidate.score_breakdown.title_score,
                heading_score=candidate.score_breakdown.heading_score,
                token_overlap_score=candidate.score_breakdown.token_overlap_score,
                term_frequency_score=candidate.score_breakdown.term_frequency_score,
                source_quality_score=candidate.score_breakdown.source_quality_score,
                provenance_score=candidate.score_breakdown.provenance_score,
                risk_adjustment=candidate.score_breakdown.risk_adjustment,
                staleness_adjustment=candidate.score_breakdown.staleness_adjustment,
                pheromone_adjustment=candidate.score_breakdown.pheromone_adjustment,
                final_score=candidate.score_breakdown.final_score,
            )
            source = candidate.provenance
            provenance = VisibleUnixProvenanceSummary(
                rank=rank,
                record_id=source.record_id,
                source_id=source.source_id,
                source_locator=source.source_locator,
                source_hash=source.source_hash,
                record_content_hash=source.record_content_hash,
                corpus_manifest_hash=source.corpus_manifest_hash,
                index_manifest_hash=retrieval_result.index_hash,
                record_ordinal=source.record_ordinal,
                ingestion_schema_version=source.ingestion_schema_version,
                normalization_version=source.normalization_version,
            )
            candidates.append(
                VisibleUnixCandidate(
                    rank=rank,
                    title=candidate.title,
                    excerpt=candidate.excerpt,
                    excerpt_truncated=candidate.excerpt_truncated,
                    record_id=candidate.record_id,
                    source_id=candidate.source_id,
                    source_locator=candidate.source_locator,
                    final_score=candidate.final_score,
                    score_breakdown=score,
                    provenance=provenance,
                    warnings=candidate.warnings,
                    authority_status=NON_AUTHORITATIVE,
                )
            )

    risk = VisibleUnixRiskSummary(
        status=(
            EXECUTION_REQUEST_BLOCKED
            if proposal.route_status == EXECUTION_REQUEST_BLOCKED
            else "INERT_QUERY_TEXT"
        ),
        execution_request_blocked=(
            proposal.route_status == EXECUTION_REQUEST_BLOCKED
        ),
        excluded_signals=proposal.excluded_signals,
        command_looking_text_is_inert=True,
        provider_calls="none",
        network_calls="none",
        filesystem_mutations_during_query="none",
        authority_status=NON_AUTHORITATIVE,
    )
    warnings = _stable_unique(
        (
            *proposal.warnings,
            *retrieval_warnings,
            (
                "RETRIEVAL_WAS_NOT_PERFORMED_FOR_ROUTE_STATUS"
                if retrieval_result is None
                else "ROUTING_DID_NOT_INVOKE_RETRIEVAL"
            ),
        )
    )
    limitations = _stable_unique(
        (
            *descriptor.limitations,
            "Offline lexical evidence review only; no correctness guarantee.",
            "The visible result is not permission, approval, or an execution instruction.",
            "No fallback answer is generated for no-route or review-needed requests.",
        )
    )
    material = {
        "authority_status": NON_AUTHORITATIVE,
        "benchmark_summary": _to_data(benchmark),
        "corpus_manifest_hash": descriptor.corpus_manifest_hash,
        "corpus_record_count": corpus_record_count,
        "execution_status": EXECUTION_STATUS,
        "index_manifest_hash": descriptor.retrieval_index_hash,
        "limitations": list(limitations),
        "normalized_query": request.normalized_query,
        "provenance_summary": [
            _to_data(item.provenance) for item in candidates
        ],
        "query_hash": request.query_hash,
        "raw_query": request.raw_query,
        "request_id": request.request_id,
        "retrieval_candidates": [_to_data(item) for item in candidates],
        "retrieval_request_summary": (
            _to_data(request_summary) if request_summary is not None else None
        ),
        "retrieval_result_hash": retrieval_hash,
        "retrieval_status": retrieval_status,
        "risk_summary": _to_data(risk),
        "route_confidence": _to_data(confidence),
        "route_proposal_hash": proposal.proposal_hash,
        "route_rationale": proposal.route_rationale,
        "route_status": proposal.route_status,
        "routing_policy_version": descriptor.routing_policy_version,
        "schema_version": PROTOTYPE_SCHEMA_VERSION,
        "score_explanations": [
            _to_data(item.score_breakdown) for item in candidates
        ],
        "selected_hat_id": proposal.selected_hat_id,
        "staleness_summary": _to_data(staleness),
        "unix_hat_descriptor_hash": descriptor.descriptor_hash,
        "unix_hat_summary": _to_data(hat),
        "warnings": list(warnings),
    }
    model = visible_unix_review_model_from_payload(
        {
            **material,
            "review_model_hash": _sha256(_canonical_bytes(material)),
        }
    )
    return model


def _model_html_sections(model: VisibleUnixReviewModel) -> str:
    e = lambda value: html_lib.escape(str(value), quote=True)
    confidence_rows = "".join(
        f"<tr><th scope=\"row\">{e(name)}</th><td>{e(value)}</td></tr>"
        for name, value in _confidence_rows(model.route_confidence)
    )
    if model.retrieval_request_summary is None:
        retrieval_request = "<p>None. Retrieval was not performed.</p>"
    else:
        request = model.retrieval_request_summary
        retrieval_request = (
            "<dl>"
            f"<dt>Normalized query</dt><dd>{e(request.normalized_query)}</dd>"
            f"<dt>Index hash</dt><dd>{e(request.index_manifest_hash)}</dd>"
            f"<dt>Requested limit</dt><dd>{e(request.requested_result_limit)}</dd>"
            f"<dt>Provenance policy</dt><dd>{e(request.provenance_policy)}</dd>"
            f"<dt>Adapter version</dt><dd>{e(request.retrieval_adapter_version)}</dd>"
            "<dt>Routing invoked retrieval</dt><dd>no</dd>"
            "<dt>Separate explicit caller required</dt><dd>yes</dd>"
            "</dl>"
        )
    candidate_rows = []
    for candidate in model.retrieval_candidates:
        candidate_rows.append(
            "<tr>"
            f"<td>{e(candidate.rank)}</td>"
            f"<td>{e(candidate.title)}</td>"
            f"<td>{e(candidate.excerpt)}</td>"
            f"<td>{e(candidate.record_id)}</td>"
            f"<td>{e(candidate.source_id)}</td>"
            f"<td>{e(candidate.source_locator)}</td>"
            f"<td>{e(candidate.provenance.source_hash)}</td>"
            f"<td>{e(candidate.provenance.record_content_hash)}</td>"
            f"<td>{e(candidate.final_score)}</td>"
            f"<td>{e(_score_text(candidate.score_breakdown))}</td>"
            f"<td>{e(model.staleness_summary.status)}: {e(model.staleness_summary.reason)}</td>"
            f"<td>{e(_joined(candidate.warnings))}</td>"
            "<td>NON_AUTHORITATIVE</td>"
            "</tr>"
        )
    if not candidate_rows:
        candidate_rows.append(
            "<tr><td colspan=\"13\">No retrieval candidates for this route status.</td></tr>"
        )
    blocked = (
        "<p class=\"blocked\"><strong>EXECUTION REQUEST BLOCKED</strong></p>"
        if model.route_status == EXECUTION_REQUEST_BLOCKED
        else ""
    )
    hat = model.unix_hat_summary
    return (
        "<section aria-labelledby=\"summary\">"
        "<h1 id=\"summary\">AOIA-Core Visible UNIX Prototype 1A</h1>"
        f"<p>{e(SPONSOR_EXPLANATION)}</p>"
        "<div class=\"boundary\" aria-label=\"Visible safety boundary\">"
        "<strong>Authority status: NON_AUTHORITATIVE</strong><br>"
        "Execution status: NO_COMMAND_OR_ACTION_EXECUTED<br>"
        "UNIX Hat capabilities: none<br>Provider calls: none<br>"
        "Network calls: none<br>Filesystem mutations during query: none"
        "</div></section>"
        "<section><h2>Stage 1 — Query</h2><dl>"
        f"<dt>Raw query</dt><dd>{e(model.raw_query)}</dd>"
        f"<dt>Normalized query</dt><dd>{e(model.normalized_query)}</dd>"
        f"<dt>Query hash</dt><dd>{e(model.query_hash)}</dd>"
        f"<dt>Request ID</dt><dd>{e(model.request_id)}</dd>"
        "</dl></section>"
        "<section><h2>Stage 2 — Route classification</h2><dl>"
        f"<dt>Route status</dt><dd>{e(model.route_status)}</dd>"
        f"<dt>Selected Hat ID</dt><dd>{e(model.selected_hat_id or 'none')}</dd>"
        f"<dt>Rationale</dt><dd>{e(model.route_rationale)}</dd>"
        f"<dt>Proposal hash</dt><dd>{e(model.route_proposal_hash)}</dd>"
        f"<dt>Excluded/risk signals</dt><dd>{e(_joined(model.risk_summary.excluded_signals))}</dd>"
        "</dl><table><caption>Confidence breakdown</caption><tbody>"
        f"{confidence_rows}</tbody></table>{blocked}</section>"
        "<section><h2>Stage 3 — UNIX Hat</h2><dl>"
        f"<dt>Hat ID</dt><dd>{e(hat.hat_id)}</dd>"
        f"<dt>Display name</dt><dd>{e(hat.display_name)}</dd>"
        f"<dt>Description</dt><dd>{e(hat.description)}</dd>"
        f"<dt>Supported scope</dt><dd>{e(_joined(hat.supported_topics))}</dd>"
        f"<dt>Excluded scope</dt><dd>{e(_joined(hat.excluded_topics))}</dd>"
        f"<dt>Corpus binding</dt><dd>{e(hat.corpus_manifest_hash)}</dd>"
        f"<dt>Index binding</dt><dd>{e(hat.retrieval_index_hash)}</dd>"
        "<dt>Capability IDs</dt><dd>none</dd>"
        f"<dt>Descriptor hash</dt><dd>{e(hat.descriptor_hash)}</dd>"
        f"<dt>Limitations</dt><dd>{e(_joined(hat.limitations))}</dd>"
        "</dl></section>"
        "<section><h2>Stage 4 — Retrieval request</h2>"
        f"{retrieval_request}</section>"
        "<section><h2>Stage 5 — Retrieval results</h2>"
        f"<p>Retrieval status: <strong>{e(model.retrieval_status)}</strong></p>"
        "<div class=\"table-wrap\"><table><caption>Canonical local evidence</caption>"
        "<thead><tr><th scope=\"col\">Rank</th><th scope=\"col\">Title</th>"
        "<th scope=\"col\">Excerpt</th><th scope=\"col\">Record ID</th>"
        "<th scope=\"col\">Source ID</th><th scope=\"col\">Locator</th>"
        "<th scope=\"col\">Source hash</th><th scope=\"col\">Content hash</th>"
        "<th scope=\"col\">Final score</th><th scope=\"col\">Score breakdown</th>"
        "<th scope=\"col\">Staleness</th><th scope=\"col\">Warnings</th>"
        "<th scope=\"col\">Authority</th></tr></thead><tbody>"
        f"{''.join(candidate_rows)}</tbody></table></div></section>"
        "<section><h2>Sponsor review metadata</h2><dl>"
        f"<dt>Corpus record count</dt><dd>{e(model.corpus_record_count)}</dd>"
        f"<dt>Corpus manifest hash</dt><dd>{e(model.corpus_manifest_hash)}</dd>"
        f"<dt>Index hash</dt><dd>{e(model.index_manifest_hash)}</dd>"
        f"<dt>Hat descriptor hash</dt><dd>{e(model.unix_hat_descriptor_hash)}</dd>"
        f"<dt>Routing policy</dt><dd>{e(model.routing_policy_version)}</dd>"
        "<dt>Test baseline</dt><dd>3146 passed, 4 skipped before this step</dd>"
        f"<dt>Measured benchmark</dt><dd>{e(_benchmark_text(model.benchmark_summary))}</dd>"
        f"<dt>Warnings</dt><dd>{e(_joined(model.warnings))}</dd>"
        f"<dt>Limitations</dt><dd>{e(_joined(model.limitations))}</dd>"
        "</dl></section>"
        "<section class=\"boundary\"><h2>Stage 6 — Safety conclusion</h2>"
        "<p><strong>NO COMMAND OR ACTION WAS EXECUTED</strong></p>"
        "<p><strong>THIS OUTPUT IS KNOWLEDGE AND REVIEW METADATA ONLY</strong></p>"
        f"<p>Route safety status: {e(model.route_status)}</p>{blocked}"
        "<p>Authority status: NON_AUTHORITATIVE<br>"
        "Execution status: NO_COMMAND_OR_ACTION_EXECUTED<br>"
        "UNIX Hat capabilities: none<br>Provider calls: none<br>"
        "Network calls: none<br>Filesystem mutations during query: none</p>"
        "</section>"
    )


def _html_document(*, title: str, body: str) -> str:
    safe_title = html_lib.escape(title, quote=True)
    return (
        "<!doctype html>\n"
        "<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{safe_title}</title>"
        "<style>"
        ":root{color-scheme:light dark;font-family:system-ui,sans-serif;}"
        "body{margin:0 auto;max-width:76rem;padding:1rem;line-height:1.55;}"
        "section{margin-block:1.5rem;padding:1rem;border:1px solid #777;border-radius:.4rem;}"
        ".boundary{border-width:3px;background:Canvas;}"
        ".blocked{border:3px solid #b00020;padding:.75rem;font-weight:700;}"
        "dt{font-weight:700;margin-top:.5rem;}dd{overflow-wrap:anywhere;}"
        ".table-wrap{overflow-x:auto;}table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #777;padding:.5rem;text-align:left;vertical-align:top;}"
        "th{font-weight:700;}*:focus-visible{outline:3px solid #1769aa;outline-offset:2px;}"
        "@media(max-width:44rem){body{padding:.5rem}section{padding:.65rem}}"
        "@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}"
        "</style></head><body>"
        f"{body}</body></html>\n"
    )


def _render_demo_index(
    models: tuple[tuple[str, str, VisibleUnixReviewModel], ...],
) -> str:
    body = [
        "<header><h1>AOIA-Core UNIX Knowledge Unit — Offline Sponsor Review</h1>",
        f"<p>{html_lib.escape(SPONSOR_EXPLANATION, quote=True)}</p>",
        "<p><strong>Local static artifact. No server, provider, network, command, or action is used.</strong></p>",
        "</header>",
    ]
    for slug, expected_status, model in models:
        body.append(
            f"<article aria-labelledby=\"demo-{html_lib.escape(slug, quote=True)}\">"
            f"<h2 id=\"demo-{html_lib.escape(slug, quote=True)}\">"
            f"Demo query: {html_lib.escape(model.raw_query, quote=True)}</h2>"
            f"<p>Expected route class: {html_lib.escape(expected_status, quote=True)}</p>"
            f"{_model_html_sections(model)}</article>"
        )
    return _html_document(
        title="AOIA-Core UNIX Knowledge Unit Offline Sponsor Review",
        body="".join(body),
    )


def _benchmark_summary(payload: Mapping[str, Any]) -> VisibleUnixBenchmarkSummary:
    if payload.get("authority_status") != NON_AUTHORITATIVE:
        raise VisibleUnixPrototypeError(
            "BENCHMARK_INVALID",
            "benchmark authority status is invalid",
        )
    if any(payload.get(key) is not value for key, value in _AUTHORITY_FLAGS.items()):
        raise VisibleUnixPrototypeError(
            "BENCHMARK_INVALID",
            "benchmark authority flags are invalid",
        )
    return VisibleUnixBenchmarkSummary(
        corpus_record_count=_strict_int(payload, "record_count"),
        index_total_bytes=_strict_int(payload, "index_total_bytes"),
        index_build_wall_time_ns=_strict_int(payload, "index_build_wall_time_ns"),
        index_build_peak_memory_bytes=_strict_int(payload, "index_build_peak_memory_bytes"),
        query_p50_latency_ns=_strict_int(payload, "query_p50_latency_ns"),
        query_p95_latency_ns=_strict_int(payload, "query_p95_latency_ns"),
        query_max_latency_ns=_strict_int(payload, "query_max_latency_ns"),
        authority_status=NON_AUTHORITATIVE,
    )


def _validate_review_model_types(model: VisibleUnixReviewModel) -> None:
    string_values = (
        model.schema_version,
        model.request_id,
        model.raw_query,
        model.normalized_query,
        model.query_hash,
        model.route_status,
        model.route_rationale,
        model.route_proposal_hash,
        model.retrieval_status,
        model.execution_status,
        model.authority_status,
        model.corpus_manifest_hash,
        model.index_manifest_hash,
        model.unix_hat_descriptor_hash,
        model.routing_policy_version,
        model.review_model_hash,
    )
    if not all(isinstance(value, str) for value in string_values):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model text field is invalid",
        )
    if model.selected_hat_id is not None and not isinstance(model.selected_hat_id, str):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "selected Hat ID is invalid",
        )
    if model.retrieval_result_hash is not None and not _is_sha256(model.retrieval_result_hash):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "retrieval result hash is invalid",
        )
    if type(model.corpus_record_count) is not int or model.corpus_record_count < 1:
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "corpus record count is invalid",
        )
    tuple_text_fields = (
        model.warnings,
        model.limitations,
        model.unix_hat_summary.supported_topics,
        model.unix_hat_summary.excluded_topics,
        model.unix_hat_summary.capability_ids,
        model.unix_hat_summary.limitations,
        model.risk_summary.excluded_signals,
    )
    if not all(
        isinstance(value, tuple) and all(isinstance(item, str) for item in value)
        for value in tuple_text_fields
    ):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model tuple field is invalid",
        )
    integer_values = (
        model.route_confidence.topic_match_score,
        model.route_confidence.scope_match_score,
        model.route_confidence.execution_risk_score,
        model.route_confidence.excluded_domain_score,
        model.route_confidence.ambiguity_score,
        model.route_confidence.final_confidence,
        model.staleness_summary.staleness_adjustment,
        model.benchmark_summary.corpus_record_count,
        model.benchmark_summary.index_total_bytes,
        model.benchmark_summary.index_build_wall_time_ns,
        model.benchmark_summary.index_build_peak_memory_bytes,
        model.benchmark_summary.query_p50_latency_ns,
        model.benchmark_summary.query_p95_latency_ns,
        model.benchmark_summary.query_max_latency_ns,
    )
    if not all(type(value) is int for value in integer_values):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            "review model integer field is invalid",
        )
    for candidate in model.retrieval_candidates:
        if type(candidate.rank) is not int or type(candidate.final_score) is not int:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate numeric field is invalid",
            )
        if type(candidate.excerpt_truncated) is not bool:
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "candidate truncation field is invalid",
            )
        if not all(type(value) is int for value in _score_values(candidate.score_breakdown)):
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                "score field is invalid",
            )


def _read_canonical_object(path: Path, status: str) -> dict[str, Any]:
    _assert_no_symlink_components(path)
    if not path.is_file() or path.is_symlink():
        raise VisibleUnixPrototypeError(status, "required upstream file is missing")
    data = path.read_bytes()
    if not data or len(data) > MAX_UPSTREAM_JSON_BYTES:
        raise VisibleUnixPrototypeError(status, "upstream file size is invalid")
    try:
        payload = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_constant=_reject_non_finite,
        )
    except (UnicodeError, json.JSONDecodeError, VisibleUnixPrototypeError) as exc:
        raise VisibleUnixPrototypeError(status, "upstream JSON is malformed") from exc
    if not isinstance(payload, dict):
        raise VisibleUnixPrototypeError(status, "upstream JSON must be an object")
    if data != _canonical_bytes(payload) + b"\n":
        raise VisibleUnixPrototypeError(status, "upstream JSON is not canonical")
    return payload


def _validated_new_demo_root(value: str | Path, allowed_parent: str | Path) -> Path:
    parent = Path(allowed_parent).absolute()
    candidate = Path(value).absolute()
    _assert_no_symlink_components(parent)
    if not parent.is_dir() or parent.is_symlink():
        raise VisibleUnixPrototypeError(
            "INVALID_OUTPUT_ROOT",
            "allowed output parent is invalid",
        )
    if candidate.exists() or candidate.is_symlink():
        raise VisibleUnixPrototypeError(
            "INVALID_OUTPUT_ROOT",
            "demo output root must not already exist",
        )
    if candidate.parent != parent or not _SAFE_OUTPUT_NAME.fullmatch(candidate.name):
        raise VisibleUnixPrototypeError(
            "INVALID_OUTPUT_ROOT",
            "demo output root must be a safe direct child of the allowed parent",
        )
    if candidate.resolve(strict=False).parent != parent.resolve(strict=True):
        raise VisibleUnixPrototypeError(
            "INVALID_OUTPUT_ROOT",
            "demo output root escapes the allowed parent",
        )
    return candidate


def _existing_demo_root(value: str | Path) -> Path:
    root = Path(value).absolute()
    _assert_no_symlink_components(root)
    if not root.is_dir() or root.is_symlink():
        raise VisibleUnixPrototypeError(
            "DEMO_INVALID",
            "demo root is missing or symbolic",
        )
    return root


def _write_new_demo_file(root: Path, relative: str, payload: bytes) -> None:
    path_value = PurePosixPath(relative)
    if path_value.is_absolute() or ".." in path_value.parts or not path_value.parts:
        raise VisibleUnixPrototypeError(
            "INVALID_OUTPUT_ROOT",
            "demo artifact path is unsafe",
        )
    if len(payload) > MAX_DEMO_FILE_BYTES:
        raise VisibleUnixPrototypeError(
            "DEMO_SIZE_LIMIT",
            "demo artifact exceeds the size limit",
        )
    target = root.joinpath(*path_value.parts)
    if target.parent != root:
        target.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise VisibleUnixPrototypeError(
            "DEMO_FILE_SET_MISMATCH",
            "demo artifact already exists",
        )
    with target.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def _assert_no_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if component.exists() and component.is_symlink():
            raise VisibleUnixPrototypeError(
                "SYMLINK_PATH_REJECTED",
                "symbolic-link path component is forbidden",
            )


def _simple_from_payload(
    class_type: type,
    payload: Any,
    *,
    tuple_fields: tuple[str, ...] = (),
):
    _require_mapping(payload, class_type.__name__)
    _require_exact_fields(payload, class_type, "REVIEW_MODEL_INVALID")
    values = dict(payload)
    for name in tuple_fields:
        if not isinstance(values[name], list):
            raise VisibleUnixPrototypeError(
                "REVIEW_MODEL_INVALID",
                f"{class_type.__name__}.{name} must be a list",
            )
        values[name] = tuple(values[name])
    return class_type(**values)


def _require_exact_fields(payload: Mapping[str, Any], class_type: type, status: str) -> None:
    if not isinstance(payload, Mapping) or set(payload) != {
        field.name for field in fields(class_type)
    }:
        raise VisibleUnixPrototypeError(status, "object fields do not match schema")


def _require_mapping(value: Any, label: str) -> None:
    if not isinstance(value, Mapping):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            f"{label} must be an object",
        )


def _required_list(payload: Mapping[str, Any], name: str) -> list[Any]:
    value = payload[name]
    if not isinstance(value, list):
        raise VisibleUnixPrototypeError(
            "REVIEW_MODEL_INVALID",
            f"{name} must be a list",
        )
    return value


def _strict_text(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise VisibleUnixPrototypeError(
            "UPSTREAM_INVALID",
            f"{name} must be non-empty text",
        )
    return value


def _strict_int(payload: Mapping[str, Any], name: str) -> int:
    value = payload.get(name)
    if type(value) is not int or value < 0:
        raise VisibleUnixPrototypeError(
            "UPSTREAM_INVALID",
            f"{name} must be a non-negative integer",
        )
    return value


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VisibleUnixPrototypeError(
                "MALFORMED_JSON",
                "duplicate JSON object key",
            )
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise VisibleUnixPrototypeError(
        "MALFORMED_JSON",
        f"non-finite JSON number is forbidden: {value}",
    )


def _to_data(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _to_data(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_to_data(item) for item in value]
    if isinstance(value, list):
        return [_to_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_data(item) for key, item in value.items()}
    if value is None or type(value) in (bool, int, str):
        return value
    raise VisibleUnixPrototypeError(
        "UNSUPPORTED_OBJECT",
        "object is not inert canonical data",
    )


def _iter_values(value: Any):
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _iter_values(getattr(value, field.name))
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


def _score_values(value: VisibleUnixScoreExplanation) -> tuple[int, ...]:
    return (
        value.rank,
        value.exact_phrase_score,
        value.title_score,
        value.heading_score,
        value.token_overlap_score,
        value.term_frequency_score,
        value.source_quality_score,
        value.provenance_score,
        value.risk_adjustment,
        value.staleness_adjustment,
        value.pheromone_adjustment,
        value.final_score,
    )


def _confidence_rows(
    value: VisibleUnixRouteConfidence,
) -> tuple[tuple[str, int], ...]:
    return (
        ("topic_match_score", value.topic_match_score),
        ("scope_match_score", value.scope_match_score),
        ("execution_risk_score", value.execution_risk_score),
        ("excluded_domain_score", value.excluded_domain_score),
        ("ambiguity_score", value.ambiguity_score),
        ("final_confidence", value.final_confidence),
    )


def _score_text(value: VisibleUnixScoreExplanation) -> str:
    return ", ".join(
        (
            f"exact_phrase={value.exact_phrase_score}",
            f"title={value.title_score}",
            f"heading={value.heading_score}",
            f"token_overlap={value.token_overlap_score}",
            f"term_frequency={value.term_frequency_score}",
            f"source_quality={value.source_quality_score}",
            f"provenance={value.provenance_score}",
            f"risk_adjustment={value.risk_adjustment}",
            f"staleness_adjustment={value.staleness_adjustment}",
            f"pheromone_adjustment={value.pheromone_adjustment}",
            f"final={value.final_score}",
        )
    )


def _benchmark_text(value: VisibleUnixBenchmarkSummary) -> str:
    return (
        f"index_bytes={value.index_total_bytes}, "
        f"build_ns={value.index_build_wall_time_ns}, "
        f"peak_memory_bytes={value.index_build_peak_memory_bytes}, "
        f"query_p50_ns={value.query_p50_latency_ns}, "
        f"query_p95_ns={value.query_p95_latency_ns}, "
        f"query_max_ns={value.query_max_latency_ns}"
    )


def _stable_unique(values: Sequence[str]) -> tuple[str, ...]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)


def _joined(values: Sequence[str]) -> str:
    return "; ".join(values) if values else "none"


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


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


if __name__ == "__main__":
    raise SystemExit(main())
