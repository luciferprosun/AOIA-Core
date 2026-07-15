from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence


INDEX_SCHEMA_VERSION = "unix-retrieval-index-manifest-1a"
INDEX_ENTRY_SCHEMA_VERSION = "unix-retrieval-index-entry-1a"
POSTINGS_SCHEMA_VERSION = "unix-retrieval-postings-1a"
QUERY_SCHEMA_VERSION = "unix-retrieval-query-1a"
RESULT_SCHEMA_VERSION = "unix-retrieval-result-1a"
PREVIEW_SCHEMA_VERSION = "unix-retrieval-preview-1a"
INDEX_VERSION = "unix-runtime-retrieval-1a"
TOKENIZER_VERSION = "unicode-nfkc-casefold-alnum-1a"
SCORING_VERSION = "deterministic-integer-lexical-1a"
CORPUS_SCHEMA_VERSION = "unix-corpus-ingestion-1a"
CORPUS_RECORD_SCHEMA_VERSION = "unix-corpus-record-1a"
CORPUS_SOURCE_SCHEMA_VERSION = "unix-corpus-source-1a"
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"

INDEX_MANIFEST_FILENAME = "index_manifest.json"
INDEX_ENTRIES_FILENAME = "entries.jsonl"
INDEX_POSTINGS_FILENAME = "postings.json"
INDEX_FILENAMES = (
    INDEX_ENTRIES_FILENAME,
    INDEX_MANIFEST_FILENAME,
    INDEX_POSTINGS_FILENAME,
)

MAX_QUERY_CHARACTERS = 2048
MAX_QUERY_TOKENS = 64
MAX_RESULT_LIMIT = 20
MAX_EXCERPT_CHARACTERS = 480
MAX_INDEX_RECORDS = 100_000
MAX_RECORD_CHARACTERS = 4_000_000
MAX_INDEX_FILE_BYTES = 256 * 1024 * 1024
MIN_CONFIDENT_SCORE = 1_000
MAX_BASE_RELEVANCE_SCORE = 12_000
PHEROMONE_MAX_ADJUSTMENT = 0

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
_CORPUS_SOURCE_FIELDS = {
    "authority_status",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_write",
    "gate_satisfied",
    "media_type",
    "quarantine_id",
    "record_ids",
    "schema_version",
    "size_bytes",
    "source_hash",
    "source_id",
    "source_path",
    "status",
}
_CORPUS_RECORD_FIELDS = {
    "authority_status",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_write",
    "content",
    "content_hash",
    "gate_satisfied",
    "locator",
    "media_type",
    "ordinal",
    "record_id",
    "schema_version",
    "source_hash",
    "source_id",
    "source_path",
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
_INDEX_ENTRY_FIELDS = {
    "authority_status",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_write",
    "content",
    "gate_satisfied",
    "heading",
    "provenance",
    "schema_version",
    "term_frequencies",
    "title",
}
_PROVENANCE_FIELDS = {
    "corpus_id",
    "corpus_manifest_hash",
    "ingestion_schema_version",
    "normalization_version",
    "record_content_hash",
    "record_id",
    "record_ordinal",
    "source_hash",
    "source_id",
    "source_locator",
    "source_path",
}
_INDEX_FILE_FIELDS = {"path", "sha256", "size_bytes"}
_POSTINGS_FIELDS = {"postings", "schema_version"}
_RISK_TOKENS = {
    "apt",
    "chmod",
    "chown",
    "curl",
    "dd",
    "execute",
    "git",
    "install",
    "mkfs",
    "rm",
    "sudo",
    "system",
    "wget",
    "write",
}


class UnixRetrievalError(ValueError):
    """Controlled fail-closed error for index build, load, or query validation."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True, order=True)
class UnixRetrievalIndexFile:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class UnixRetrievalIndexManifest:
    schema_version: str
    index_version: str
    corpus_id: str
    corpus_manifest_hash: str
    record_count: int
    indexed_record_ids: tuple[str, ...]
    tokenizer_version: str
    scoring_version: str
    index_files: tuple[UnixRetrievalIndexFile, ...]
    total_token_count: int
    unique_term_count: int
    posting_count: int
    index_hash: str
    authority_status: str


@dataclass(frozen=True)
class UnixRetrievalProvenance:
    corpus_id: str
    corpus_manifest_hash: str
    record_id: str
    record_content_hash: str
    source_id: str
    source_hash: str
    source_path: str
    source_locator: str
    record_ordinal: int
    ingestion_schema_version: str
    normalization_version: str


@dataclass(frozen=True)
class UnixRetrievalIndexEntry:
    schema_version: str
    title: str
    heading: str
    content: str
    term_frequencies: tuple[tuple[str, int], ...]
    provenance: UnixRetrievalProvenance
    authority_status: str


@dataclass(frozen=True)
class UnixRetrievalQuery:
    schema_version: str
    raw_query: str
    normalized_query: str
    query_hash: str
    requested_limit: int
    evaluation_context: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class DecaySnapshot:
    status: str
    evaluation_context: str
    staleness_adjustment: int
    reason: str
    authority_status: str = NON_AUTHORITATIVE


@dataclass(frozen=True)
class PheromoneAdjustmentPreview:
    supported: bool
    status: str
    adjustment: int
    maximum_absolute_adjustment: int
    reason: str
    authority_status: str = NON_AUTHORITATIVE


@dataclass(frozen=True)
class UnixRetrievalScoreBreakdown:
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


@dataclass(frozen=True)
class UnixRetrievalCandidate:
    record_id: str
    source_id: str
    source_locator: str
    title: str
    excerpt: str
    excerpt_truncated: bool
    record_content_hash: str
    provenance: UnixRetrievalProvenance
    score_breakdown: UnixRetrievalScoreBreakdown
    final_score: int
    warnings: tuple[str, ...]
    authority_status: str = NON_AUTHORITATIVE


@dataclass(frozen=True)
class UnixRetrievalFailure:
    status: str
    reason: str
    authority_status: str = NON_AUTHORITATIVE
    command_or_action_executed: bool = False


@dataclass(frozen=True)
class UnixRetrievalResult:
    schema_version: str
    status: str
    query: UnixRetrievalQuery
    index_hash: str
    corpus_manifest_hash: str
    candidates: tuple[UnixRetrievalCandidate, ...]
    rejected_candidate_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    decay_snapshot: DecaySnapshot
    pheromone_adjustment_preview: PheromoneAdjustmentPreview
    authority_status: str = NON_AUTHORITATIVE
    command_or_action_executed: bool = False


@dataclass(frozen=True)
class UnixRetrievalPreview:
    schema_version: str
    normalized_query: str
    query_hash: str
    index_hash: str
    corpus_manifest_hash: str
    requested_limit: int
    candidate_count: int
    candidates: tuple[UnixRetrievalCandidate, ...]
    rejected_candidate_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    decay_snapshot: DecaySnapshot
    pheromone_adjustment_preview: PheromoneAdjustmentPreview
    authority_status: str
    action_statement: str


@dataclass(frozen=True)
class UnixRetrievalVerificationResult:
    valid: bool
    status: str
    reason: str
    manifest: UnixRetrievalIndexManifest | None


@dataclass(frozen=True)
class UnixRetrievalBuildResult:
    status: str
    output_root: str
    manifest: UnixRetrievalIndexManifest
    total_index_bytes: int
    authority_status: str = NON_AUTHORITATIVE


@dataclass(frozen=True)
class LoadedUnixRetrievalIndex:
    manifest: UnixRetrievalIndexManifest
    entries: tuple[UnixRetrievalIndexEntry, ...]
    postings: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class _VerifiedCorpus:
    manifest_payload: Mapping[str, Any]
    records: tuple[Mapping[str, Any], ...]


def normalize_unix_retrieval_query(
    raw_query: str,
    *,
    requested_limit: int = 5,
    evaluation_context: str = "UNSPECIFIED",
) -> UnixRetrievalQuery:
    if not isinstance(raw_query, str):
        raise UnixRetrievalError("EMPTY_QUERY", "query must be a string")
    if len(raw_query) > MAX_QUERY_CHARACTERS:
        raise UnixRetrievalError("QUERY_TOO_LONG", "query exceeds the character limit")
    normalized = _normalize_text(raw_query)
    if not normalized:
        raise UnixRetrievalError("EMPTY_QUERY", "query must contain searchable text")
    tokens = tuple(normalized.split())
    if len(tokens) > MAX_QUERY_TOKENS:
        raise UnixRetrievalError("TOO_MANY_TOKENS", "query exceeds the token limit")
    if type(requested_limit) is not int or not 1 <= requested_limit <= MAX_RESULT_LIMIT:
        raise UnixRetrievalError("INVALID_LIMIT", "requested limit is outside the allowed range")
    if not isinstance(evaluation_context, str) or not evaluation_context.strip():
        raise UnixRetrievalError(
            "INVALID_EVALUATION_CONTEXT",
            "evaluation context must be explicit non-empty text",
        )
    if len(evaluation_context) > 256:
        raise UnixRetrievalError(
            "INVALID_EVALUATION_CONTEXT",
            "evaluation context exceeds the length limit",
        )
    material = {
        "evaluation_context": evaluation_context,
        "normalized_query": normalized,
        "raw_query": raw_query,
        "requested_limit": requested_limit,
        "schema_version": QUERY_SCHEMA_VERSION,
    }
    return UnixRetrievalQuery(
        schema_version=QUERY_SCHEMA_VERSION,
        raw_query=raw_query,
        normalized_query=normalized,
        query_hash=_sha256(_canonical_bytes(material)),
        requested_limit=requested_limit,
        evaluation_context=evaluation_context,
        tokens=tokens,
    )


def build_unix_retrieval_index(
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    output_root: str | Path,
    *,
    expected_corpus_manifest_hash: str | None = None,
) -> UnixRetrievalBuildResult:
    corpus = _load_verified_corpus(
        corpus_manifest_path,
        records_path,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
    )
    destination = _validated_new_output_root(
        output_root,
        input_paths=(corpus_manifest_path, records_path),
    )
    entries = tuple(
        _index_entry(corpus.manifest_payload, record)
        for record in sorted(corpus.records, key=lambda item: item["record_id"])
    )
    postings = _build_postings(entries)
    entries_bytes = b"".join(
        _canonical_bytes(_index_entry_payload(entry)) + b"\n"
        for entry in entries
    )
    postings_payload = {
        "postings": {token: list(record_ids) for token, record_ids in postings.items()},
        "schema_version": POSTINGS_SCHEMA_VERSION,
    }
    postings_bytes = _canonical_bytes(postings_payload) + b"\n"
    file_payloads = {
        INDEX_ENTRIES_FILENAME: entries_bytes,
        INDEX_POSTINGS_FILENAME: postings_bytes,
    }
    index_files = tuple(
        UnixRetrievalIndexFile(
            path=name,
            sha256=_sha256(payload),
            size_bytes=len(payload),
        )
        for name, payload in sorted(file_payloads.items())
    )
    total_tokens = sum(
        count
        for entry in entries
        for _token, count in entry.term_frequencies
    )
    posting_count = sum(len(record_ids) for record_ids in postings.values())
    manifest_material = {
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "corpus_id": corpus.manifest_payload["corpus_id"],
        "corpus_manifest_hash": corpus.manifest_payload["manifest_hash"],
        "index_files": [_index_file_payload(item) for item in index_files],
        "index_version": INDEX_VERSION,
        "indexed_record_ids": [entry.provenance.record_id for entry in entries],
        "posting_count": posting_count,
        "record_count": len(entries),
        "schema_version": INDEX_SCHEMA_VERSION,
        "scoring_version": SCORING_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
        "total_token_count": total_tokens,
        "unique_term_count": len(postings),
    }
    index_hash = _sha256(_canonical_bytes(manifest_material))
    manifest_payload = {**manifest_material, "index_hash": index_hash}
    manifest_bytes = _canonical_bytes(manifest_payload) + b"\n"

    destination.mkdir(parents=True, exist_ok=False)
    for name, payload in sorted(file_payloads.items()):
        _write_once(destination / name, payload)
    _write_once(destination / INDEX_MANIFEST_FILENAME, manifest_bytes)

    loaded = _load_verified_index(
        destination,
        corpus_manifest_path,
        records_path,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
    )
    total_bytes = sum(path.stat().st_size for path in destination.iterdir())
    return UnixRetrievalBuildResult(
        status="CREATED",
        output_root=str(destination),
        manifest=loaded.manifest,
        total_index_bytes=total_bytes,
    )


def verify_unix_retrieval_index(
    index_root: str | Path,
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    *,
    expected_corpus_manifest_hash: str | None = None,
) -> UnixRetrievalVerificationResult:
    try:
        loaded = _load_verified_index(
            index_root,
            corpus_manifest_path,
            records_path,
            expected_corpus_manifest_hash=expected_corpus_manifest_hash,
        )
    except UnixRetrievalError as exc:
        return UnixRetrievalVerificationResult(
            valid=False,
            status=exc.status,
            reason=exc.reason,
            manifest=None,
        )
    except OSError as exc:
        return UnixRetrievalVerificationResult(
            valid=False,
            status="MALFORMED_INDEX",
            reason=f"index could not be read: {exc.__class__.__name__}",
            manifest=None,
        )
    return UnixRetrievalVerificationResult(
        valid=True,
        status="VALID",
        reason="index and corpus binding verified",
        manifest=loaded.manifest,
    )


def load_unix_retrieval_index(
    index_root: str | Path,
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    *,
    expected_corpus_manifest_hash: str | None = None,
) -> LoadedUnixRetrievalIndex:
    return _load_verified_index(
        index_root,
        corpus_manifest_path,
        records_path,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
    )


def retrieve_unix_knowledge(
    index_root: str | Path,
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    raw_query: str,
    *,
    requested_limit: int = 5,
    evaluation_context: str = "UNSPECIFIED",
    pheromone_metadata: object | None = None,
    expected_corpus_manifest_hash: str | None = None,
) -> UnixRetrievalResult | UnixRetrievalFailure:
    try:
        loaded = load_unix_retrieval_index(
            index_root,
            corpus_manifest_path,
            records_path,
            expected_corpus_manifest_hash=expected_corpus_manifest_hash,
        )
        return retrieve_loaded_unix_knowledge(
            loaded,
            raw_query,
            requested_limit=requested_limit,
            evaluation_context=evaluation_context,
            pheromone_metadata=pheromone_metadata,
        )
    except UnixRetrievalError as exc:
        return UnixRetrievalFailure(status=exc.status, reason=exc.reason)
    except OSError as exc:
        return UnixRetrievalFailure(
            status="MALFORMED_INDEX",
            reason=f"index could not be read: {exc.__class__.__name__}",
        )


def retrieve_loaded_unix_knowledge(
    loaded_index: LoadedUnixRetrievalIndex,
    raw_query: str,
    *,
    requested_limit: int = 5,
    evaluation_context: str = "UNSPECIFIED",
    pheromone_metadata: object | None = None,
) -> UnixRetrievalResult:
    if not isinstance(loaded_index, LoadedUnixRetrievalIndex):
        raise UnixRetrievalError("MALFORMED_INDEX", "loaded index type is invalid")
    if pheromone_metadata is not None:
        raise UnixRetrievalError(
            "INVALID_PHEROMONE_DATA",
            "pheromone adjustment is not enabled without a canonical governed schema",
        )
    query = normalize_unix_retrieval_query(
        raw_query,
        requested_limit=requested_limit,
        evaluation_context=evaluation_context,
    )
    entries_by_id = {
        entry.provenance.record_id: entry
        for entry in loaded_index.entries
    }
    candidate_ids = sorted(
        {
            record_id
            for token in set(query.tokens)
            for record_id in loaded_index.postings.get(token, ())
        }
    )
    decay = DecaySnapshot(
        status="STALENESS_UNKNOWN",
        evaluation_context=evaluation_context,
        staleness_adjustment=0,
        reason="canonical records contain no verified publication or review date",
    )
    pheromone = PheromoneAdjustmentPreview(
        supported=False,
        status="NOT_SUPPORTED",
        adjustment=0,
        maximum_absolute_adjustment=PHEROMONE_MAX_ADJUSTMENT,
        reason="no canonical governed pheromone schema is bound to this index",
    )
    candidates = [
        _score_candidate(entries_by_id[record_id], query, decay, pheromone)
        for record_id in candidate_ids
    ]
    ranked = tuple(
        candidate
        for candidate in sorted(
            candidates,
            key=lambda item: (
                -item.final_score,
                item.record_id,
                item.source_locator,
            ),
        )
        if candidate.final_score >= MIN_CONFIDENT_SCORE
    )[:requested_limit]
    status = "OK" if ranked else "NO_CONFIDENT_RESULT"
    warnings = ["RETRIEVAL_RESULT_IS_NON_AUTHORITATIVE"]
    if _RISK_TOKENS.intersection(query.tokens):
        warnings.append("COMMAND_LOOKING_QUERY_TREATED_AS_INERT_TEXT")
    return UnixRetrievalResult(
        schema_version=RESULT_SCHEMA_VERSION,
        status=status,
        query=query,
        index_hash=loaded_index.manifest.index_hash,
        corpus_manifest_hash=loaded_index.manifest.corpus_manifest_hash,
        candidates=ranked,
        rejected_candidate_reasons=(),
        warnings=tuple(warnings),
        decay_snapshot=decay,
        pheromone_adjustment_preview=pheromone,
    )


def preview_unix_retrieval(
    index_root: str | Path,
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    raw_query: str,
    *,
    requested_limit: int = 5,
    evaluation_context: str = "UNSPECIFIED",
    pheromone_metadata: object | None = None,
    expected_corpus_manifest_hash: str | None = None,
) -> UnixRetrievalPreview | UnixRetrievalFailure:
    result = retrieve_unix_knowledge(
        index_root,
        corpus_manifest_path,
        records_path,
        raw_query,
        requested_limit=requested_limit,
        evaluation_context=evaluation_context,
        pheromone_metadata=pheromone_metadata,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
    )
    if isinstance(result, UnixRetrievalFailure):
        return result
    return UnixRetrievalPreview(
        schema_version=PREVIEW_SCHEMA_VERSION,
        normalized_query=result.query.normalized_query,
        query_hash=result.query.query_hash,
        index_hash=result.index_hash,
        corpus_manifest_hash=result.corpus_manifest_hash,
        requested_limit=result.query.requested_limit,
        candidate_count=len(result.candidates),
        candidates=result.candidates,
        rejected_candidate_reasons=result.rejected_candidate_reasons,
        warnings=result.warnings,
        decay_snapshot=result.decay_snapshot,
        pheromone_adjustment_preview=result.pheromone_adjustment_preview,
        authority_status=NON_AUTHORITATIVE,
        action_statement="NO_COMMAND_OR_ACTION_EXECUTED",
    )


def unix_retrieval_result_hash(
    value: UnixRetrievalResult | UnixRetrievalPreview | UnixRetrievalFailure,
) -> str:
    return _sha256(_canonical_bytes(unix_retrieval_result_payload(value)))


def unix_retrieval_result_payload(
    value: UnixRetrievalResult | UnixRetrievalPreview | UnixRetrievalFailure,
) -> dict[str, Any]:
    if isinstance(value, UnixRetrievalFailure):
        return {
            "authority_status": value.authority_status,
            "command_or_action_executed": value.command_or_action_executed,
            "reason": value.reason,
            "status": value.status,
        }
    if isinstance(value, UnixRetrievalPreview):
        return {
            "action_statement": value.action_statement,
            "authority_status": value.authority_status,
            "candidate_count": value.candidate_count,
            "candidates": [_candidate_payload(item) for item in value.candidates],
            "corpus_manifest_hash": value.corpus_manifest_hash,
            "decay_snapshot": _decay_payload(value.decay_snapshot),
            "index_hash": value.index_hash,
            "normalized_query": value.normalized_query,
            "pheromone_adjustment_preview": _pheromone_payload(
                value.pheromone_adjustment_preview
            ),
            "query_hash": value.query_hash,
            "rejected_candidate_reasons": list(value.rejected_candidate_reasons),
            "requested_limit": value.requested_limit,
            "schema_version": value.schema_version,
            "warnings": list(value.warnings),
        }
    if isinstance(value, UnixRetrievalResult):
        return {
            "authority_status": value.authority_status,
            "candidates": [_candidate_payload(item) for item in value.candidates],
            "command_or_action_executed": value.command_or_action_executed,
            "corpus_manifest_hash": value.corpus_manifest_hash,
            "decay_snapshot": _decay_payload(value.decay_snapshot),
            "index_hash": value.index_hash,
            "pheromone_adjustment_preview": _pheromone_payload(
                value.pheromone_adjustment_preview
            ),
            "query": _query_payload(value.query),
            "rejected_candidate_reasons": list(value.rejected_candidate_reasons),
            "schema_version": value.schema_version,
            "status": value.status,
            "warnings": list(value.warnings),
        }
    raise TypeError("unsupported retrieval result type")


def _load_verified_corpus(
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    *,
    expected_corpus_manifest_hash: str | None,
) -> _VerifiedCorpus:
    manifest_path = _existing_regular_path(
        corpus_manifest_path,
        "CORPUS_MANIFEST_MISMATCH",
        "corpus manifest",
    )
    record_root = _existing_directory(
        records_path,
        "MISSING_RECORD",
        "corpus records directory",
    )
    manifest = _read_canonical_object(
        manifest_path,
        "CORPUS_MANIFEST_MISMATCH",
        "corpus manifest",
    )
    _expect_fields(manifest, _CORPUS_MANIFEST_FIELDS, "CORPUS_MANIFEST_MISMATCH", "corpus manifest")
    if manifest.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise UnixRetrievalError("UNKNOWN_SCHEMA", "corpus manifest schema is unsupported")
    _assert_non_authoritative(manifest, "CORPUS_MANIFEST_MISMATCH", "corpus manifest")
    manifest_hash = _expect_sha256(
        manifest.get("manifest_hash"),
        "CORPUS_MANIFEST_MISMATCH",
        "corpus manifest hash",
    )
    material = dict(manifest)
    material.pop("manifest_hash")
    if _sha256(_canonical_bytes(material)) != manifest_hash:
        raise UnixRetrievalError("CORPUS_MANIFEST_MISMATCH", "corpus manifest hash mismatch")
    if expected_corpus_manifest_hash is not None:
        expected = _expect_sha256(
            expected_corpus_manifest_hash,
            "CORPUS_MANIFEST_MISMATCH",
            "expected corpus manifest hash",
        )
        if manifest_hash != expected:
            raise UnixRetrievalError(
                "CORPUS_MANIFEST_MISMATCH",
                "corpus manifest does not match the independently retained expected hash",
            )

    record_ids = _expect_hash_list(
        manifest.get("record_ids"),
        "CORPUS_MANIFEST_MISMATCH",
        "corpus record IDs",
    )
    if len(record_ids) > MAX_INDEX_RECORDS:
        raise UnixRetrievalError("CORPUS_MANIFEST_MISMATCH", "corpus record limit exceeded")
    if type(manifest.get("record_count")) is not int or manifest["record_count"] != len(record_ids):
        raise UnixRetrievalError("CORPUS_MANIFEST_MISMATCH", "corpus record count mismatch")
    if manifest.get("quarantine_ids"):
        raise UnixRetrievalError("CORPUS_MANIFEST_MISMATCH", "quarantined corpus is not indexable")

    sources_payload = manifest.get("sources")
    if not isinstance(sources_payload, list) or not sources_payload:
        raise UnixRetrievalError("PROVENANCE_INVALID", "corpus sources are missing")
    sources: dict[str, Mapping[str, Any]] = {}
    bound_record_ids: set[str] = set()
    for source in sources_payload:
        if not isinstance(source, dict):
            raise UnixRetrievalError("PROVENANCE_INVALID", "corpus source entry is invalid")
        _expect_fields(source, _CORPUS_SOURCE_FIELDS, "PROVENANCE_INVALID", "corpus source")
        if source.get("schema_version") != CORPUS_SOURCE_SCHEMA_VERSION:
            raise UnixRetrievalError("UNKNOWN_SCHEMA", "corpus source schema is unsupported")
        _assert_non_authoritative(source, "PROVENANCE_INVALID", "corpus source")
        source_id = _expect_nonempty_string(source.get("source_id"), "PROVENANCE_INVALID", "source ID")
        if source_id in sources:
            raise UnixRetrievalError("PROVENANCE_INVALID", "duplicate corpus source ID")
        _expect_sha256(source.get("source_hash"), "PROVENANCE_INVALID", "source hash")
        _expect_safe_relative_path(source.get("source_path"), "PROVENANCE_INVALID", "source path")
        if source.get("status") != "ACCEPTED" or source.get("quarantine_id") is not None:
            raise UnixRetrievalError("PROVENANCE_INVALID", "only accepted sources may be indexed")
        source_record_ids = _expect_hash_list(
            source.get("record_ids"),
            "PROVENANCE_INVALID",
            "source record IDs",
            require_sorted=False,
        )
        if bound_record_ids.intersection(source_record_ids):
            raise UnixRetrievalError("PROVENANCE_INVALID", "record is bound to multiple sources")
        bound_record_ids.update(source_record_ids)
        sources[source_id] = source
    if bound_record_ids != set(record_ids):
        raise UnixRetrievalError("PROVENANCE_INVALID", "source-to-record bindings are incomplete")

    records: list[Mapping[str, Any]] = []
    for record_id in record_ids:
        path = record_root / f"{record_id}.json"
        if not path.is_file() or path.is_symlink():
            raise UnixRetrievalError("MISSING_RECORD", f"corpus record is missing: {record_id}")
        record = _read_canonical_object(path, "RECORD_HASH_MISMATCH", "corpus record")
        _expect_fields(record, _CORPUS_RECORD_FIELDS, "PROVENANCE_INVALID", "corpus record")
        if record.get("schema_version") != CORPUS_RECORD_SCHEMA_VERSION:
            raise UnixRetrievalError("UNKNOWN_SCHEMA", "corpus record schema is unsupported")
        _assert_non_authoritative(record, "PROVENANCE_INVALID", "corpus record")
        if record.get("record_id") != record_id:
            raise UnixRetrievalError("RECORD_HASH_MISMATCH", "record filename and ID differ")
        content = _expect_nonempty_string(record.get("content"), "RECORD_HASH_MISMATCH", "record content")
        if len(content) > MAX_RECORD_CHARACTERS:
            raise UnixRetrievalError("RECORD_HASH_MISMATCH", "record content exceeds the size limit")
        content_hash = _expect_sha256(
            record.get("content_hash"),
            "RECORD_HASH_MISMATCH",
            "record content hash",
        )
        if _sha256(content.encode("utf-8")) != content_hash:
            raise UnixRetrievalError("RECORD_HASH_MISMATCH", "record content hash mismatch")
        record_material = dict(record)
        record_material.pop("record_id")
        if _sha256(_canonical_bytes(record_material)) != record_id:
            raise UnixRetrievalError("RECORD_HASH_MISMATCH", "record identifier mismatch")
        source_id = _expect_nonempty_string(record.get("source_id"), "PROVENANCE_INVALID", "record source ID")
        source = sources.get(source_id)
        if source is None:
            raise UnixRetrievalError("PROVENANCE_INVALID", "record source is not in the corpus manifest")
        if (
            record.get("source_hash") != source.get("source_hash")
            or record.get("source_path") != source.get("source_path")
            or record_id not in source.get("record_ids", [])
        ):
            raise UnixRetrievalError("PROVENANCE_INVALID", "record provenance does not match its source")
        _expect_locator(record.get("locator"))
        if type(record.get("ordinal")) is not int or record["ordinal"] <= 0:
            raise UnixRetrievalError("PROVENANCE_INVALID", "record ordinal is invalid")
        records.append(record)
    return _VerifiedCorpus(
        manifest_payload=MappingProxyType(dict(manifest)),
        records=tuple(MappingProxyType(dict(record)) for record in records),
    )


def _load_verified_index(
    index_root: str | Path,
    corpus_manifest_path: str | Path,
    records_path: str | Path,
    *,
    expected_corpus_manifest_hash: str | None,
) -> LoadedUnixRetrievalIndex:
    root = _existing_directory(index_root, "MISSING_INDEX", "retrieval index")
    actual_names = tuple(sorted(path.name for path in root.iterdir()))
    if actual_names != INDEX_FILENAMES:
        raise UnixRetrievalError("MALFORMED_INDEX", "index contains missing or unexpected files")
    corpus = _load_verified_corpus(
        corpus_manifest_path,
        records_path,
        expected_corpus_manifest_hash=expected_corpus_manifest_hash,
    )
    manifest_payload = _read_canonical_object(
        root / INDEX_MANIFEST_FILENAME,
        "MALFORMED_INDEX",
        "index manifest",
    )
    manifest = _parse_index_manifest(manifest_payload)
    if manifest.corpus_id != corpus.manifest_payload["corpus_id"]:
        raise UnixRetrievalError("CORPUS_MANIFEST_MISMATCH", "index corpus ID mismatch")
    if manifest.corpus_manifest_hash != corpus.manifest_payload["manifest_hash"]:
        raise UnixRetrievalError("STALE_INDEX", "index is bound to a different corpus manifest")
    if manifest.indexed_record_ids != tuple(corpus.manifest_payload["record_ids"]):
        raise UnixRetrievalError("STALE_INDEX", "index record set differs from the corpus manifest")

    for file_record in manifest.index_files:
        path = root / file_record.path
        if not path.is_file() or path.is_symlink():
            raise UnixRetrievalError("MISSING_INDEX", f"index file is missing: {file_record.path}")
        size = path.stat().st_size
        if size != file_record.size_bytes or size > MAX_INDEX_FILE_BYTES:
            raise UnixRetrievalError("INDEX_HASH_MISMATCH", f"index file size mismatch: {file_record.path}")
        if _hash_file(path) != file_record.sha256:
            raise UnixRetrievalError("INDEX_HASH_MISMATCH", f"index file hash mismatch: {file_record.path}")

    entry_payloads = _read_canonical_jsonl(
        root / INDEX_ENTRIES_FILENAME,
        "MALFORMED_INDEX",
        "index entries",
    )
    if len(entry_payloads) != manifest.record_count:
        raise UnixRetrievalError("MALFORMED_INDEX", "index entry count mismatch")
    corpus_records = {record["record_id"]: record for record in corpus.records}
    entries = tuple(
        _parse_index_entry(payload, corpus_records, manifest)
        for payload in entry_payloads
    )
    entry_ids = tuple(entry.provenance.record_id for entry in entries)
    if entry_ids != tuple(sorted(entry_ids)) or entry_ids != manifest.indexed_record_ids:
        raise UnixRetrievalError("NON_DETERMINISTIC_INDEX", "index entries are not in canonical record order")

    postings_payload = _read_canonical_object(
        root / INDEX_POSTINGS_FILENAME,
        "MALFORMED_INDEX",
        "index postings",
    )
    _expect_fields(postings_payload, _POSTINGS_FIELDS, "MALFORMED_INDEX", "index postings")
    if postings_payload.get("schema_version") != POSTINGS_SCHEMA_VERSION:
        raise UnixRetrievalError("UNKNOWN_SCHEMA", "postings schema is unsupported")
    postings_raw = postings_payload.get("postings")
    if not isinstance(postings_raw, dict):
        raise UnixRetrievalError("MALFORMED_INDEX", "postings must be an object")
    postings: dict[str, tuple[str, ...]] = {}
    valid_ids = set(entry_ids)
    for token, values in postings_raw.items():
        if not isinstance(token, str) or not token or _normalize_text(token) != token or " " in token:
            raise UnixRetrievalError("MALFORMED_INDEX", "posting token is invalid")
        record_ids = _expect_hash_list(values, "MALFORMED_INDEX", "posting record IDs")
        if not set(record_ids).issubset(valid_ids):
            raise UnixRetrievalError("MALFORMED_INDEX", "posting references an unknown record")
        postings[token] = record_ids
    expected_postings = _build_postings(entries)
    if postings != expected_postings:
        raise UnixRetrievalError("INDEX_HASH_MISMATCH", "postings do not match indexed content")
    total_tokens = sum(
        count
        for entry in entries
        for _token, count in entry.term_frequencies
    )
    posting_count = sum(len(values) for values in postings.values())
    if (
        manifest.total_token_count != total_tokens
        or manifest.unique_term_count != len(postings)
        or manifest.posting_count != posting_count
    ):
        raise UnixRetrievalError("INDEX_HASH_MISMATCH", "index statistics do not match content")
    return LoadedUnixRetrievalIndex(
        manifest=manifest,
        entries=entries,
        postings=MappingProxyType(dict(sorted(postings.items()))),
    )


def _parse_index_manifest(payload: Mapping[str, Any]) -> UnixRetrievalIndexManifest:
    _expect_fields(payload, _INDEX_MANIFEST_FIELDS, "MALFORMED_INDEX", "index manifest")
    if payload.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise UnixRetrievalError("UNKNOWN_SCHEMA", "index manifest schema is unsupported")
    if payload.get("index_version") != INDEX_VERSION:
        raise UnixRetrievalError("STALE_INDEX", "index version is unsupported")
    if payload.get("tokenizer_version") != TOKENIZER_VERSION:
        raise UnixRetrievalError("STALE_INDEX", "tokenizer version is unsupported")
    if payload.get("scoring_version") != SCORING_VERSION:
        raise UnixRetrievalError("STALE_INDEX", "scoring version is unsupported")
    _assert_non_authoritative(payload, "MALFORMED_INDEX", "index manifest")
    index_hash = _expect_sha256(payload.get("index_hash"), "INDEX_HASH_MISMATCH", "index hash")
    material = dict(payload)
    material.pop("index_hash")
    if _sha256(_canonical_bytes(material)) != index_hash:
        raise UnixRetrievalError("INDEX_HASH_MISMATCH", "index manifest hash mismatch")
    indexed_ids = _expect_hash_list(
        payload.get("indexed_record_ids"),
        "MALFORMED_INDEX",
        "indexed record IDs",
    )
    if type(payload.get("record_count")) is not int or payload["record_count"] != len(indexed_ids):
        raise UnixRetrievalError("MALFORMED_INDEX", "index record count mismatch")
    file_values = payload.get("index_files")
    if not isinstance(file_values, list):
        raise UnixRetrievalError("MALFORMED_INDEX", "index files must be a list")
    index_files: list[UnixRetrievalIndexFile] = []
    for item in file_values:
        if not isinstance(item, dict):
            raise UnixRetrievalError("MALFORMED_INDEX", "index file entry is invalid")
        _expect_fields(item, _INDEX_FILE_FIELDS, "MALFORMED_INDEX", "index file")
        path = _expect_nonempty_string(item.get("path"), "MALFORMED_INDEX", "index file path")
        if path not in {INDEX_ENTRIES_FILENAME, INDEX_POSTINGS_FILENAME}:
            raise UnixRetrievalError("MALFORMED_INDEX", "index manifest contains an unexpected file")
        sha256 = _expect_sha256(item.get("sha256"), "MALFORMED_INDEX", "index file hash")
        size = item.get("size_bytes")
        if type(size) is not int or not 0 < size <= MAX_INDEX_FILE_BYTES:
            raise UnixRetrievalError("MALFORMED_INDEX", "index file size is invalid")
        index_files.append(UnixRetrievalIndexFile(path=path, sha256=sha256, size_bytes=size))
    index_files_tuple = tuple(sorted(index_files))
    if tuple(item.path for item in index_files_tuple) != (
        INDEX_ENTRIES_FILENAME,
        INDEX_POSTINGS_FILENAME,
    ):
        raise UnixRetrievalError("MALFORMED_INDEX", "index file set is incomplete")
    counts: list[int] = []
    for name in ("total_token_count", "unique_term_count", "posting_count"):
        value = payload.get(name)
        if type(value) is not int or value < 0:
            raise UnixRetrievalError("MALFORMED_INDEX", f"index {name} is invalid")
        counts.append(value)
    return UnixRetrievalIndexManifest(
        schema_version=payload["schema_version"],
        index_version=payload["index_version"],
        corpus_id=_expect_nonempty_string(payload.get("corpus_id"), "MALFORMED_INDEX", "corpus ID"),
        corpus_manifest_hash=_expect_sha256(
            payload.get("corpus_manifest_hash"),
            "MALFORMED_INDEX",
            "corpus manifest hash",
        ),
        record_count=payload["record_count"],
        indexed_record_ids=indexed_ids,
        tokenizer_version=payload["tokenizer_version"],
        scoring_version=payload["scoring_version"],
        index_files=index_files_tuple,
        total_token_count=counts[0],
        unique_term_count=counts[1],
        posting_count=counts[2],
        index_hash=index_hash,
        authority_status=payload["authority_status"],
    )


def _parse_index_entry(
    payload: Mapping[str, Any],
    corpus_records: Mapping[str, Mapping[str, Any]],
    manifest: UnixRetrievalIndexManifest,
) -> UnixRetrievalIndexEntry:
    _expect_fields(payload, _INDEX_ENTRY_FIELDS, "MALFORMED_INDEX", "index entry")
    if payload.get("schema_version") != INDEX_ENTRY_SCHEMA_VERSION:
        raise UnixRetrievalError("UNKNOWN_SCHEMA", "index entry schema is unsupported")
    _assert_non_authoritative(payload, "MALFORMED_INDEX", "index entry")
    provenance_payload = payload.get("provenance")
    if not isinstance(provenance_payload, dict):
        raise UnixRetrievalError("PROVENANCE_INVALID", "index entry provenance is invalid")
    _expect_fields(provenance_payload, _PROVENANCE_FIELDS, "PROVENANCE_INVALID", "index provenance")
    provenance = UnixRetrievalProvenance(
        corpus_id=_expect_nonempty_string(provenance_payload.get("corpus_id"), "PROVENANCE_INVALID", "corpus ID"),
        corpus_manifest_hash=_expect_sha256(
            provenance_payload.get("corpus_manifest_hash"),
            "PROVENANCE_INVALID",
            "corpus manifest hash",
        ),
        record_id=_expect_sha256(provenance_payload.get("record_id"), "PROVENANCE_INVALID", "record ID"),
        record_content_hash=_expect_sha256(
            provenance_payload.get("record_content_hash"),
            "PROVENANCE_INVALID",
            "record content hash",
        ),
        source_id=_expect_nonempty_string(provenance_payload.get("source_id"), "PROVENANCE_INVALID", "source ID"),
        source_hash=_expect_sha256(provenance_payload.get("source_hash"), "PROVENANCE_INVALID", "source hash"),
        source_path=_expect_safe_relative_path(
            provenance_payload.get("source_path"),
            "PROVENANCE_INVALID",
            "source path",
        ),
        source_locator=_expect_locator(provenance_payload.get("source_locator")),
        record_ordinal=_expect_positive_int(
            provenance_payload.get("record_ordinal"),
            "PROVENANCE_INVALID",
            "record ordinal",
        ),
        ingestion_schema_version=_expect_nonempty_string(
            provenance_payload.get("ingestion_schema_version"),
            "PROVENANCE_INVALID",
            "ingestion schema version",
        ),
        normalization_version=_expect_nonempty_string(
            provenance_payload.get("normalization_version"),
            "PROVENANCE_INVALID",
            "normalization version",
        ),
    )
    record = corpus_records.get(provenance.record_id)
    if record is None:
        raise UnixRetrievalError("MISSING_RECORD", "index entry references a missing corpus record")
    expected_provenance = _provenance(manifest.corpus_id, manifest.corpus_manifest_hash, record)
    if provenance != expected_provenance:
        raise UnixRetrievalError("PROVENANCE_INVALID", "index provenance differs from the corpus record")
    content = _expect_nonempty_string(payload.get("content"), "RECORD_HASH_MISMATCH", "index content")
    if content != record["content"] or _sha256(content.encode("utf-8")) != provenance.record_content_hash:
        raise UnixRetrievalError("RECORD_HASH_MISMATCH", "index content differs from the corpus record")
    title = _expect_nonempty_string(payload.get("title"), "MALFORMED_INDEX", "index title")
    heading = payload.get("heading")
    if not isinstance(heading, str):
        raise UnixRetrievalError("MALFORMED_INDEX", "index heading must be text")
    frequencies_raw = payload.get("term_frequencies")
    if not isinstance(frequencies_raw, dict):
        raise UnixRetrievalError("MALFORMED_INDEX", "term frequencies must be an object")
    frequencies: list[tuple[str, int]] = []
    for token, count in frequencies_raw.items():
        if not isinstance(token, str) or not token or _normalize_text(token) != token or " " in token:
            raise UnixRetrievalError("MALFORMED_INDEX", "term-frequency token is invalid")
        if type(count) is not int or count <= 0:
            raise UnixRetrievalError("MALFORMED_INDEX", "term-frequency count is invalid")
        frequencies.append((token, count))
    frequencies_tuple = tuple(sorted(frequencies))
    expected = tuple(sorted(Counter(_tokenize(content)).items()))
    if frequencies_tuple != expected:
        raise UnixRetrievalError("INDEX_HASH_MISMATCH", "term frequencies differ from indexed content")
    return UnixRetrievalIndexEntry(
        schema_version=payload["schema_version"],
        title=title,
        heading=heading,
        content=content,
        term_frequencies=frequencies_tuple,
        provenance=provenance,
        authority_status=payload["authority_status"],
    )


def _index_entry(
    manifest: Mapping[str, Any],
    record: Mapping[str, Any],
) -> UnixRetrievalIndexEntry:
    content = record["content"]
    frequencies = tuple(sorted(Counter(_tokenize(content)).items()))
    return UnixRetrievalIndexEntry(
        schema_version=INDEX_ENTRY_SCHEMA_VERSION,
        title=_derive_title(content),
        heading=_derive_heading(content),
        content=content,
        term_frequencies=frequencies,
        provenance=_provenance(
            manifest["corpus_id"],
            manifest["manifest_hash"],
            record,
        ),
        authority_status=NON_AUTHORITATIVE,
    )


def _provenance(
    corpus_id: str,
    corpus_manifest_hash: str,
    record: Mapping[str, Any],
) -> UnixRetrievalProvenance:
    return UnixRetrievalProvenance(
        corpus_id=corpus_id,
        corpus_manifest_hash=corpus_manifest_hash,
        record_id=record["record_id"],
        record_content_hash=record["content_hash"],
        source_id=record["source_id"],
        source_hash=record["source_hash"],
        source_path=record["source_path"],
        source_locator=record["locator"],
        record_ordinal=record["ordinal"],
        ingestion_schema_version=CORPUS_SCHEMA_VERSION,
        normalization_version=record["schema_version"],
    )


def _build_postings(
    entries: Sequence[UnixRetrievalIndexEntry],
) -> dict[str, tuple[str, ...]]:
    postings: dict[str, list[str]] = {}
    for entry in entries:
        record_id = entry.provenance.record_id
        for token, _count in entry.term_frequencies:
            postings.setdefault(token, []).append(record_id)
    return {
        token: tuple(sorted(record_ids))
        for token, record_ids in sorted(postings.items())
    }


def _score_candidate(
    entry: UnixRetrievalIndexEntry,
    query: UnixRetrievalQuery,
    decay: DecaySnapshot,
    pheromone: PheromoneAdjustmentPreview,
) -> UnixRetrievalCandidate:
    query_terms = set(query.tokens)
    frequencies = dict(entry.term_frequencies)
    matched_terms = query_terms.intersection(frequencies)
    normalized_content = _normalize_text(entry.content)
    title_terms = set(_tokenize(entry.title))
    heading_terms = set(_tokenize(entry.heading))
    denominator = max(len(query_terms), 1)
    exact_phrase_score = 4_000 if query.normalized_query in normalized_content else 0
    title_score = (2_000 * len(query_terms.intersection(title_terms))) // denominator
    heading_score = (1_000 * len(query_terms.intersection(heading_terms))) // denominator
    token_overlap_score = (2_500 * len(matched_terms)) // denominator
    term_frequency_score = min(
        1_000,
        sum(min(frequencies[token], 10) * 50 for token in matched_terms),
    )
    source_quality_score = 500
    provenance_score = 500
    risk_adjustment = -250 if _RISK_TOKENS.intersection(query_terms) else 0
    final_score = max(
        0,
        exact_phrase_score
        + title_score
        + heading_score
        + token_overlap_score
        + term_frequency_score
        + source_quality_score
        + provenance_score
        + risk_adjustment
        + decay.staleness_adjustment
        + pheromone.adjustment,
    )
    if final_score > MAX_BASE_RELEVANCE_SCORE:
        raise UnixRetrievalError("NON_DETERMINISTIC_INDEX", "score exceeded the declared bound")
    breakdown = UnixRetrievalScoreBreakdown(
        exact_phrase_score=exact_phrase_score,
        title_score=title_score,
        heading_score=heading_score,
        token_overlap_score=token_overlap_score,
        term_frequency_score=term_frequency_score,
        source_quality_score=source_quality_score,
        provenance_score=provenance_score,
        risk_adjustment=risk_adjustment,
        staleness_adjustment=decay.staleness_adjustment,
        pheromone_adjustment=pheromone.adjustment,
        final_score=final_score,
    )
    excerpt, truncated = _excerpt(entry.content, query.tokens)
    warnings = ["STALENESS_UNKNOWN"]
    if risk_adjustment:
        warnings.append("COMMAND_TEXT_IS_INERT_EVIDENCE")
    return UnixRetrievalCandidate(
        record_id=entry.provenance.record_id,
        source_id=entry.provenance.source_id,
        source_locator=entry.provenance.source_locator,
        title=entry.title,
        excerpt=excerpt,
        excerpt_truncated=truncated,
        record_content_hash=entry.provenance.record_content_hash,
        provenance=entry.provenance,
        score_breakdown=breakdown,
        final_score=final_score,
        warnings=tuple(warnings),
    )


def _derive_title(content: str) -> str:
    for line in content.splitlines():
        title = " ".join(line.split())
        if title:
            return title[:160]
    raise UnixRetrievalError("RECORD_HASH_MISMATCH", "record content has no title text")


def _derive_heading(content: str) -> str:
    heading_pattern = re.compile(r"^(?:chapter\s+)?\d+(?:\.\d+)*\s+\S", re.IGNORECASE)
    for line in content.splitlines()[:80]:
        heading = " ".join(line.split())
        if heading and len(heading) <= 200 and heading_pattern.match(heading):
            return heading
    return ""


def _excerpt(content: str, query_tokens: Sequence[str]) -> tuple[str, bool]:
    folded = unicodedata.normalize("NFKC", content).casefold()
    position = -1
    for token in query_tokens:
        position = folded.find(token)
        if position >= 0:
            break
    if position < 0:
        position = 0
    start = max(0, position - 120)
    end = min(len(content), start + MAX_EXCERPT_CHARACTERS)
    excerpt = " ".join(content[start:end].split())
    return excerpt, start > 0 or end < len(content)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    characters = [character if character.isalnum() else " " for character in normalized]
    return " ".join("".join(characters).split())


def _tokenize(value: str) -> tuple[str, ...]:
    normalized = _normalize_text(value)
    return tuple(normalized.split()) if normalized else ()


def _query_payload(value: UnixRetrievalQuery) -> dict[str, Any]:
    return {
        "evaluation_context": value.evaluation_context,
        "normalized_query": value.normalized_query,
        "query_hash": value.query_hash,
        "raw_query": value.raw_query,
        "requested_limit": value.requested_limit,
        "schema_version": value.schema_version,
        "tokens": list(value.tokens),
    }


def _candidate_payload(value: UnixRetrievalCandidate) -> dict[str, Any]:
    return {
        "authority_status": value.authority_status,
        "excerpt": value.excerpt,
        "excerpt_truncated": value.excerpt_truncated,
        "final_score": value.final_score,
        "provenance": _provenance_payload(value.provenance),
        "record_content_hash": value.record_content_hash,
        "record_id": value.record_id,
        "score_breakdown": {
            "exact_phrase_score": value.score_breakdown.exact_phrase_score,
            "final_score": value.score_breakdown.final_score,
            "heading_score": value.score_breakdown.heading_score,
            "pheromone_adjustment": value.score_breakdown.pheromone_adjustment,
            "provenance_score": value.score_breakdown.provenance_score,
            "risk_adjustment": value.score_breakdown.risk_adjustment,
            "source_quality_score": value.score_breakdown.source_quality_score,
            "staleness_adjustment": value.score_breakdown.staleness_adjustment,
            "term_frequency_score": value.score_breakdown.term_frequency_score,
            "title_score": value.score_breakdown.title_score,
            "token_overlap_score": value.score_breakdown.token_overlap_score,
        },
        "source_id": value.source_id,
        "source_locator": value.source_locator,
        "title": value.title,
        "warnings": list(value.warnings),
    }


def _decay_payload(value: DecaySnapshot) -> dict[str, Any]:
    return {
        "authority_status": value.authority_status,
        "evaluation_context": value.evaluation_context,
        "reason": value.reason,
        "staleness_adjustment": value.staleness_adjustment,
        "status": value.status,
    }


def _pheromone_payload(value: PheromoneAdjustmentPreview) -> dict[str, Any]:
    return {
        "adjustment": value.adjustment,
        "authority_status": value.authority_status,
        "maximum_absolute_adjustment": value.maximum_absolute_adjustment,
        "reason": value.reason,
        "status": value.status,
        "supported": value.supported,
    }


def _index_entry_payload(value: UnixRetrievalIndexEntry) -> dict[str, Any]:
    return {
        "authority_status": value.authority_status,
        **_AUTHORITY_FLAGS,
        "content": value.content,
        "heading": value.heading,
        "provenance": _provenance_payload(value.provenance),
        "schema_version": value.schema_version,
        "term_frequencies": dict(value.term_frequencies),
        "title": value.title,
    }


def _provenance_payload(value: UnixRetrievalProvenance) -> dict[str, Any]:
    return {
        "corpus_id": value.corpus_id,
        "corpus_manifest_hash": value.corpus_manifest_hash,
        "ingestion_schema_version": value.ingestion_schema_version,
        "normalization_version": value.normalization_version,
        "record_content_hash": value.record_content_hash,
        "record_id": value.record_id,
        "record_ordinal": value.record_ordinal,
        "source_hash": value.source_hash,
        "source_id": value.source_id,
        "source_locator": value.source_locator,
        "source_path": value.source_path,
    }


def _index_file_payload(value: UnixRetrievalIndexFile) -> dict[str, Any]:
    return {
        "path": value.path,
        "sha256": value.sha256,
        "size_bytes": value.size_bytes,
    }


def _validated_new_output_root(
    value: str | Path,
    *,
    input_paths: tuple[str | Path, ...] = (),
) -> Path:
    path = _path_value(value, "INVALID_OUTPUT_ROOT", "index output root")
    _assert_no_symlink_components(path)
    resolved = path.resolve(strict=False)
    if resolved.exists():
        raise UnixRetrievalError("OUTPUT_EXISTS", "index output root must not already exist")
    for input_value in input_paths:
        input_path = _path_value(input_value, "INVALID_OUTPUT_ROOT", "index input path")
        _assert_no_symlink_components(input_path)
        try:
            resolved_input = input_path.resolve(strict=True)
        except OSError as exc:
            raise UnixRetrievalError(
                "INVALID_OUTPUT_ROOT",
                "index input path does not exist",
            ) from exc
        if (
            resolved == resolved_input
            or resolved_input in resolved.parents
            or resolved in resolved_input.parents
        ):
            raise UnixRetrievalError(
                "INVALID_OUTPUT_ROOT",
                "index output root must not overlap corpus inputs",
            )
    return resolved


def _existing_regular_path(value: str | Path, status: str, label: str) -> Path:
    path = _path_value(value, status, label)
    _assert_no_symlink_components(path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise UnixRetrievalError(status, f"{label} does not exist") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise UnixRetrievalError(status, f"{label} must be a regular non-symlink file")
    return resolved


def _existing_directory(value: str | Path, status: str, label: str) -> Path:
    path = _path_value(value, status, label)
    _assert_no_symlink_components(path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise UnixRetrievalError(status, f"{label} does not exist") from exc
    if not resolved.is_dir() or resolved.is_symlink():
        raise UnixRetrievalError(status, f"{label} must be a non-symlink directory")
    return resolved


def _path_value(value: str | Path, status: str, label: str) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    raise UnixRetrievalError(status, f"{label} must be a path")


def _assert_no_symlink_components(path: Path) -> None:
    current = path if path.is_absolute() else Path.cwd() / path
    while True:
        if current.exists() and current.is_symlink():
            raise UnixRetrievalError("PATH_ESCAPE", "path contains a symbolic link")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _write_once(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise UnixRetrievalError("INDEX_WRITE_FAILED", "index materialization failed") from exc


def _read_canonical_object(path: Path, status: str, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise UnixRetrievalError(status, f"{label} could not be read") from exc
    if len(raw) > MAX_INDEX_FILE_BYTES:
        raise UnixRetrievalError(status, f"{label} exceeds the size limit")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise UnixRetrievalError(status, f"{label} is not newline-terminated canonical JSON")
    try:
        text = raw[:-1].decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise UnixRetrievalError(status, f"{label} is not valid UTF-8") from exc
    try:
        payload = _strict_json_loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise UnixRetrievalError(status, f"{label} is malformed JSON") from exc
    if not isinstance(payload, dict):
        raise UnixRetrievalError(status, f"{label} must contain one JSON object")
    if raw != _canonical_bytes(payload) + b"\n":
        raise UnixRetrievalError(status, f"{label} is not canonical JSON")
    return payload


def _read_canonical_jsonl(path: Path, status: str, label: str) -> tuple[dict[str, Any], ...]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise UnixRetrievalError(status, f"{label} could not be read") from exc
    if not raw or len(raw) > MAX_INDEX_FILE_BYTES or not raw.endswith(b"\n"):
        raise UnixRetrievalError(status, f"{label} is incomplete or exceeds the size limit")
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(keepends=True), start=1):
        if not raw_line.endswith(b"\n") or raw_line == b"\n":
            raise UnixRetrievalError(status, f"{label} contains an invalid line {line_number}")
        try:
            text = raw_line[:-1].decode("utf-8", errors="strict")
            payload = _strict_json_loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise UnixRetrievalError(status, f"{label} line {line_number} is malformed") from exc
        if not isinstance(payload, dict) or raw_line != _canonical_bytes(payload) + b"\n":
            raise UnixRetrievalError(status, f"{label} line {line_number} is not canonical")
        rows.append(payload)
    return tuple(rows)


def _strict_json_loads(text: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"unsupported JSON constant: {value}")

    return json.loads(
        text,
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _expect_fields(
    payload: Mapping[str, Any],
    expected: set[str],
    status: str,
    label: str,
) -> None:
    if set(payload) != expected:
        raise UnixRetrievalError(status, f"{label} has an invalid field set")


def _assert_non_authoritative(payload: Mapping[str, Any], status: str, label: str) -> None:
    if payload.get("authority_status") != NON_AUTHORITATIVE:
        raise UnixRetrievalError(status, f"{label} authority status is invalid")
    if any(payload.get(name) is not False for name in _AUTHORITY_FLAGS):
        raise UnixRetrievalError(status, f"{label} contains authority-bearing state")


def _expect_nonempty_string(value: Any, status: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnixRetrievalError(status, f"{label} must be non-empty text")
    return value


def _expect_sha256(value: Any, status: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise UnixRetrievalError(status, f"{label} is not a lowercase SHA-256 digest")
    return value


def _expect_hash_list(
    value: Any,
    status: str,
    label: str,
    *,
    require_sorted: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise UnixRetrievalError(status, f"{label} must be a list")
    values = tuple(_expect_sha256(item, status, label) for item in value)
    if len(values) != len(set(values)):
        raise UnixRetrievalError(status, f"{label} contains duplicates")
    if require_sorted and values != tuple(sorted(values)):
        raise UnixRetrievalError(status, f"{label} must be sorted")
    return values


def _expect_safe_relative_path(value: Any, status: str, label: str) -> str:
    text = _expect_nonempty_string(value, status, label)
    path = Path(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise UnixRetrievalError(status, f"{label} must be a safe relative path")
    return path.as_posix()


def _expect_locator(value: Any) -> str:
    locator = _expect_nonempty_string(value, "PROVENANCE_INVALID", "source locator")
    match = re.fullmatch(r"lines:(\d+)-(\d+)", locator)
    if match is None or int(match.group(1)) <= 0 or int(match.group(2)) < int(match.group(1)):
        raise UnixRetrievalError("PROVENANCE_INVALID", "source locator is invalid")
    return locator


def _expect_positive_int(value: Any, status: str, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise UnixRetrievalError(status, f"{label} must be a positive integer")
    return value


__all__ = [
    "DecaySnapshot",
    "INDEX_SCHEMA_VERSION",
    "INDEX_VERSION",
    "LoadedUnixRetrievalIndex",
    "NON_AUTHORITATIVE",
    "PHEROMONE_MAX_ADJUSTMENT",
    "PheromoneAdjustmentPreview",
    "SCORING_VERSION",
    "TOKENIZER_VERSION",
    "UnixRetrievalBuildResult",
    "UnixRetrievalCandidate",
    "UnixRetrievalError",
    "UnixRetrievalFailure",
    "UnixRetrievalIndexEntry",
    "UnixRetrievalIndexManifest",
    "UnixRetrievalPreview",
    "UnixRetrievalProvenance",
    "UnixRetrievalQuery",
    "UnixRetrievalResult",
    "UnixRetrievalScoreBreakdown",
    "UnixRetrievalVerificationResult",
    "build_unix_retrieval_index",
    "load_unix_retrieval_index",
    "normalize_unix_retrieval_query",
    "preview_unix_retrieval",
    "retrieve_loaded_unix_knowledge",
    "retrieve_unix_knowledge",
    "unix_retrieval_result_hash",
    "unix_retrieval_result_payload",
    "verify_unix_retrieval_index",
]
