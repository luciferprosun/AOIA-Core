"""Deterministic validation and evidence freeze for the UNIX Knowledge Unit.

This module is an explicit validation/build boundary.  It verifies existing
local artifacts, reproduces them only beneath caller-selected new roots, and
materializes evidence metadata.  It is not a service, dispatcher, approval
mechanism, controlled writer, or execution surface.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
import time
import tracemalloc
import types
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from runtime.knowledge.unix_corpus_ingestion import (
    AUTHORITY_FLAGS as CORPUS_AUTHORITY_FLAGS,
    NON_AUTHORITATIVE,
    read_unix_corpus_manifest,
    reconcile_unix_corpus,
)
from runtime.memory_hats.unix_hat import (
    EXECUTION_REQUEST_BLOCKED,
    NO_ROUTE,
    REVIEW_NEEDED,
    ROUTE_TO_UNIX_KNOWLEDGE,
    UnixHatDescriptor,
    actual_query_validation_payload,
    canonical_json_bytes as hat_canonical_json_bytes,
    create_unix_hat_descriptor,
    create_unix_route_request,
    propose_unix_route,
    routing_policy_manifest_payload,
    unix_hat_descriptor_from_payload,
)
from runtime.retrieval.unix_runtime_adapter import (
    UnixRetrievalFailure,
    UnixRetrievalResult,
    build_unix_retrieval_index,
    load_unix_retrieval_index,
    retrieve_loaded_unix_knowledge,
    retrieve_unix_knowledge,
    unix_retrieval_result_hash,
    verify_unix_retrieval_index,
)
from runtime.visible_unix_prototype import (
    ACTUAL_DEMO_QUERIES,
    EXPECTED_CORPUS_MANIFEST_HASH,
    EXPECTED_HAT_DESCRIPTOR_HASH,
    EXPECTED_INDEX_MANIFEST_HASH,
    EXPECTED_ROUTING_POLICY_VERSION,
    VisibleUnixPrototypeError,
    build_visible_unix_demo_payloads,
    build_visible_unix_review_model,
    materialize_visible_unix_demo,
    render_visible_unix_html,
    render_visible_unix_text,
    verify_visible_unix_demo,
    verify_visible_unix_review_model,
    verify_visible_unix_upstream,
    visible_unix_review_model_from_payload,
)


FREEZE_ID = "aoia-unix-unit-1a-r1"
FREEZE_SCHEMA_VERSION = "aoia-unix-full-validation-freeze-1a-r1"
SUPERSEDES_FREEZE_MANIFEST_HASH = (
    "59d058483d30ae60e290fa0a576920163eea0f7aef94ff28e4bf3671652dfa43"
)
FREEZE_VERIFICATION_SCHEMA_VERSION = "aoia-unix-freeze-verification-1a"
WORKTREE_SNAPSHOT_SCHEMA_VERSION = "aoia-unix-worktree-snapshot-1a"
VALIDATION_SUMMARY_SCHEMA_VERSION = "aoia-unix-validation-summary-1a"
DETERMINISM_REPORT_SCHEMA_VERSION = "aoia-unix-determinism-report-1a"
ADVERSARIAL_REPORT_SCHEMA_VERSION = "aoia-unix-adversarial-report-1a"
CAPABILITY_REPORT_SCHEMA_VERSION = "aoia-unix-capability-report-1a"
BENCHMARK_SCHEMA_VERSION = "aoia-unix-benchmark-1a"
LIMITATIONS_SCHEMA_VERSION = "aoia-unix-limitations-1a"
COMPONENT_HASHES_SCHEMA_VERSION = "aoia-unix-component-hashes-1a"
SPONSOR_MANIFEST_SCHEMA_VERSION = "aoia-unix-sponsor-bundle-1a"
SPONSOR_CHECKLIST_SCHEMA_VERSION = "aoia-unix-sponsor-checklist-1a"
EXPECTED_VISIBLE_DEMO_MANIFEST_HASH = (
    "515f6915043928c364bb0c573684a87db41e6e4f125478c3b0d9c2fd0433d59f"
)
REPOSITORY_RELATIVE_IDENTITY = "AOIA-Core"
APPROVED_SOURCE_PATH = "extracted/linux_master_library_v1.txt"
APPROVED_SOURCE_INVENTORY_SCHEMA_VERSION = "unix-approved-corpus-source-inventory-1b1"
DISCOVERY_INVENTORY_SCHEMA_VERSION = "unix-corpus-discovery-inventory-1b1"
APPROVED_SOURCE_SELECTION_POLICY_VERSION = "unix-approved-source-selection-policy-1b1"
MAX_EVIDENCE_FILE_BYTES = 32 * 1024 * 1024
MAX_EVIDENCE_TOTAL_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_FILES = 64
MAX_WORKTREE_FILES = 20_000
MAX_RELATIVE_PATH_BYTES = 512
_SAFE_OUTPUT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_HTML_EXTERNAL_ATTRIBUTE = re.compile(
    r"\s(?:src|href)\s*=|@import|url\s*\(",
    flags=re.IGNORECASE,
)
_INERT_FLAGS = {
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
    "gate_satisfied": False,
}

FIXED_BENCHMARK_QUERIES: tuple[str, ...] = (
    "UNIX file permissions",
    "path traversal",
    "shell injection",
    "process signals",
    "pipes",
    "sudo",
    "SSH authentication",
    "systemd",
    "Linux namespaces",
    "control groups",
    "containers",
    "package management",
    "network boundaries",
)

REQUIRED_LIMITATIONS: tuple[str, ...] = (
    "The corpus contains 13 canonical normalized records from one approved extracted local source.",
    "The corpus is not guaranteed to contain all UNIX knowledge.",
    "Retrieval is lexical, deterministic, and local.",
    "No remote embeddings or provider reasoning are used.",
    "Scoring is relevance metadata only and is not approval.",
    "Routing is deterministic metadata only and cannot dispatch.",
    "The UNIX Hat has zero capabilities.",
    "Execution requests are blocked and are not silently converted into actions.",
    "The system does not administer a real machine.",
    "No command or action is executed by the UNIX Knowledge Unit.",
    "Perfect correctness or perfect safety is not guaranteed.",
    "Human review remains required before consequential use.",
    "Freeze evidence is non-authoritative metadata.",
    "This local working-tree freeze is not a Git release, commit, or tag.",
)

REPRODUCIBILITY_COMMANDS = (
    "CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime:. "
    "python3 -m unittest tests.test_unix_full_validation_and_freeze_1a -v < /dev/null\n"
    "CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime:. "
    "python3 -m unittest tests.test_unix_unit_adversarial_suite_1a -v < /dev/null\n"
    "CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime:. "
    "python3 -m unittest discover -s tests -p 'test*.py' -q < /dev/null\n"
    "PYTHONPYCACHEPREFIX=/tmp/aoia-unix-freeze-pycache "
    "python3 -m compileall -q runtime tests\n"
)


class UnixFullValidationError(ValueError):
    """Fail-closed final validation error."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True, slots=True)
class UnixUnitPaths:
    repository_root: Path
    knowledge_root: Path
    approved_source_inventory_path: Path
    discovery_inventory_path: Path
    corpus_intake_root: Path
    corpus_manifest_path: Path
    corpus_records_path: Path
    retrieval_index_root: Path
    retrieval_index_manifest_path: Path
    hat_routing_root: Path
    hat_descriptor_path: Path
    routing_policy_path: Path
    route_validation_path: Path
    visible_demo_root: Path
    visible_demo_manifest_path: Path


@dataclass(frozen=True, slots=True)
class UnixUnitVerification:
    approved_source_inventory_hash: str
    discovery_inventory_hash: str
    corpus_manifest_hash: str
    corpus_record_count: int
    normalized_bytes: int
    retrieval_index_hash: str
    indexed_record_count: int
    unix_hat_descriptor_hash: str
    unix_hat_capability_count: int
    routing_policy_hash: str
    route_validation_hash: str
    visible_demo_manifest_hash: str
    visible_demo_file_count: int
    authority_status: str = NON_AUTHORITATIVE


@dataclass(frozen=True, slots=True)
class UnixUnitReplayReport:
    corpus_replay_match: bool
    retrieval_index_replay_match: bool
    hat_routing_replay_match: bool
    visible_demo_replay_match: bool
    corpus_manifest_hash: str
    retrieval_index_hash: str
    unix_hat_descriptor_hash: str
    visible_demo_manifest_hash: str
    authority_status: str
    report_hash: str


@dataclass(frozen=True, slots=True)
class UnixFreezeVerification:
    valid: bool
    status: str
    reason: str
    freeze_manifest_hash: str | None
    sponsor_manifest_hash: str | None
    worktree_snapshot_hash: str | None
    file_count: int
    total_bytes: int
    authority_status: str = NON_AUTHORITATIVE


def default_unix_unit_paths(repository_root: str | Path | None = None) -> UnixUnitPaths:
    root = (
        Path(repository_root).absolute()
        if repository_root is not None
        else Path(__file__).resolve().parents[1]
    )
    return UnixUnitPaths(
        repository_root=root,
        knowledge_root=root / "runtime/knowledge",
        approved_source_inventory_path=(
            root / "data/unix_corpus_ingestion_1b/approved_source_inventory.json"
        ),
        discovery_inventory_path=root / "data/unix_corpus_ingestion_1b/source_inventory.json",
        corpus_intake_root=root / "data/unix_corpus_ingestion_1b/intake",
        corpus_manifest_path=root / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json",
        corpus_records_path=root / "data/unix_corpus_ingestion_1b/intake/records",
        retrieval_index_root=root / "data/unix_retrieval_adapter_1a/index",
        retrieval_index_manifest_path=root / "data/unix_retrieval_adapter_1a/index/index_manifest.json",
        hat_routing_root=root / "data/unix_hat_routing_1a",
        hat_descriptor_path=root / "data/unix_hat_routing_1a/unix_hat_descriptor.json",
        routing_policy_path=root / "data/unix_hat_routing_1a/routing_policy_manifest.json",
        route_validation_path=root / "data/unix_hat_routing_1a/actual_query_validation.json",
        visible_demo_root=root / "data/visible_unix_prototype_1a",
        visible_demo_manifest_path=root / "data/visible_unix_prototype_1a/demo_manifest.json",
    )


def build_approved_corpus_source_inventory(
    repository_root: str | Path,
) -> dict[str, Any]:
    """Build corpus identity from accepted source bytes, never discovery candidates."""

    paths = default_unix_unit_paths(repository_root)
    corpus = _read_canonical_object(paths.corpus_manifest_path, "CORPUS_INVALID")
    _assert_inert_payload(corpus, "CORPUS_INVALID")
    _verify_embedded_hash(corpus, "manifest_hash")
    sources = corpus.get("sources")
    if not isinstance(sources, list) or not sources:
        raise UnixFullValidationError("APPROVED_INVENTORY_INVALID", "accepted sources are missing")
    records: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict) or source.get("status") != "ACCEPTED":
            continue
        _assert_inert_payload(source, "APPROVED_INVENTORY_INVALID")
        relative = _safe_relative_path(source.get("source_path"), "APPROVED_INVENTORY_INVALID")
        path = _resolve_relative_regular_file(
            paths.knowledge_root,
            relative,
            "APPROVED_INVENTORY_INVALID",
        )
        source_hash = _hash_file(path)
        if source_hash != source.get("source_hash") or path.stat().st_size != source.get("size_bytes"):
            raise UnixFullValidationError(
                "APPROVED_INVENTORY_INVALID",
                "accepted source differs from the corpus manifest",
            )
        records.append(
            {
                "authority_status": NON_AUTHORITATIVE,
                **_INERT_FLAGS,
                "corpus_relative_path": relative,
                "media_type": source.get("media_type"),
                "repository_relative_path": f"runtime/knowledge/{relative}",
                "sha256": source_hash,
                "size_bytes": path.stat().st_size,
                "source_id": source.get("source_id"),
                "source_locator": f"repository:runtime/knowledge/{relative}",
                "source_type": "APPROVED_EXTRACTED_SOURCE",
            }
        )
    records.sort(key=lambda value: value["repository_relative_path"])
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "schema_version": APPROVED_SOURCE_INVENTORY_SCHEMA_VERSION,
        "selection_policy_version": APPROVED_SOURCE_SELECTION_POLICY_VERSION,
        "source_count": len(records),
        "sources": records,
        "total_source_bytes": sum(record["size_bytes"] for record in records),
    }
    if material["source_count"] != corpus.get("accepted_source_count"):
        raise UnixFullValidationError(
            "APPROVED_INVENTORY_INVALID",
            "accepted source count differs from the corpus manifest",
        )
    return {
        **material,
        "approved_inventory_hash": _sha256(_canonical_bytes(material)),
    }


def verify_approved_corpus_source_inventory(
    repository_root: str | Path,
    inventory: Mapping[str, Any],
) -> str:
    expected = build_approved_corpus_source_inventory(repository_root)
    if dict(inventory) != expected:
        raise UnixFullValidationError(
            "APPROVED_INVENTORY_INVALID",
            "approved source inventory differs from accepted corpus sources",
        )
    return expected["approved_inventory_hash"]


def build_corpus_discovery_inventory(
    *,
    candidate_roots: Sequence[Mapping[str, Any]],
    files: Sequence[Mapping[str, Any]],
    duplicate_groups: Sequence[Mapping[str, Any]] = (),
    archives: Sequence[Mapping[str, Any]] = (),
    expected_corpus_defined: bool,
    expected_corpus_matched: bool,
) -> dict[str, Any]:
    """Build discovery evidence that is explicitly separate from corpus identity."""

    if type(expected_corpus_defined) is not bool or type(expected_corpus_matched) is not bool:
        raise UnixFullValidationError("DISCOVERY_INVENTORY_INVALID", "expected-corpus flags are invalid")
    rows = [dict(row) for row in files]
    rows.sort(key=lambda row: str(row.get("path", "")))
    paths = [row.get("path") for row in rows]
    if (
        not rows
        or any(not isinstance(path, str) or not path for path in paths)
        or len(paths) != len(set(paths))
    ):
        raise UnixFullValidationError("DISCOVERY_INVENTORY_INVALID", "discovery file rows are invalid")
    for row in rows:
        _assert_inert_payload(row, "DISCOVERY_INVENTORY_INVALID")
        if type(row.get("selected")) is not bool or not isinstance(row.get("classification"), str):
            raise UnixFullValidationError("DISCOVERY_INVENTORY_INVALID", "discovery classification is invalid")
    material = {
        "archives": [dict(value) for value in archives],
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "candidate_roots": [dict(value) for value in candidate_roots],
        "duplicate_groups": [dict(value) for value in duplicate_groups],
        "expected_corpus_defined": expected_corpus_defined,
        "expected_corpus_matched": expected_corpus_matched,
        "files": rows,
        "schema_version": DISCOVERY_INVENTORY_SCHEMA_VERSION,
    }
    return {
        **material,
        "discovery_inventory_hash": _sha256(_canonical_bytes(material)),
    }


def verify_corpus_discovery_inventory(inventory: Mapping[str, Any]) -> str:
    if inventory.get("schema_version") != DISCOVERY_INVENTORY_SCHEMA_VERSION:
        raise UnixFullValidationError(
            "DISCOVERY_INVENTORY_INVALID",
            "legacy or unknown discovery inventory schema is forbidden",
        )
    expected = build_corpus_discovery_inventory(
        candidate_roots=inventory.get("candidate_roots", ()),
        files=inventory.get("files", ()),
        duplicate_groups=inventory.get("duplicate_groups", ()),
        archives=inventory.get("archives", ()),
        expected_corpus_defined=inventory.get("expected_corpus_defined"),
        expected_corpus_matched=inventory.get("expected_corpus_matched"),
    )
    if dict(inventory) != expected:
        raise UnixFullValidationError(
            "DISCOVERY_INVENTORY_INVALID",
            "discovery inventory hash or fields differ",
        )
    return expected["discovery_inventory_hash"]


def verify_unix_unit_upstream(
    repository_root: str | Path | None = None,
) -> UnixUnitVerification:
    paths = default_unix_unit_paths(repository_root)
    root = paths.repository_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise UnixFullValidationError("REPOSITORY_INVALID", "repository root is invalid")

    approved_inventory = _read_canonical_object(
        paths.approved_source_inventory_path,
        "APPROVED_INVENTORY_INVALID",
    )
    _assert_inert_payload(approved_inventory, "APPROVED_INVENTORY_INVALID")
    approved_inventory_hash = verify_approved_corpus_source_inventory(root, approved_inventory)

    discovery_inventory = _read_canonical_object(
        paths.discovery_inventory_path,
        "DISCOVERY_INVENTORY_INVALID",
    )
    _assert_inert_payload(discovery_inventory, "DISCOVERY_INVENTORY_INVALID")
    discovery_inventory_hash = verify_corpus_discovery_inventory(discovery_inventory)
    scanner_path = (
        "knowledge/languages/python/audits/duplicate_conflict_scan/"
        "scan_python_knowledge_duplicates.py"
    )
    scanner_rows = [
        row
        for row in discovery_inventory["files"]
        if row.get("path") == scanner_path
    ]
    if (
        len(scanner_rows) != 1
        or scanner_rows[0].get("classification") != "TOOLING"
        or scanner_rows[0].get("selected") is not False
    ):
        raise UnixFullValidationError(
            "DISCOVERY_INVENTORY_INVALID",
            "duplicate-conflict scanner must remain non-selected tooling",
        )
    approved_by_path = {
        source["repository_relative_path"]: source
        for source in approved_inventory["sources"]
    }
    selected_discovery = [row for row in discovery_inventory["files"] if row.get("selected") is True]
    if len(selected_discovery) != len(approved_by_path):
        raise UnixFullValidationError("DISCOVERY_INVENTORY_INVALID", "selected discovery set differs")
    for row in selected_discovery:
        approved = approved_by_path.get(row.get("path"))
        if (
            approved is None
            or row.get("sha256") != approved.get("sha256")
            or row.get("bytes") != approved.get("size_bytes")
        ):
            raise UnixFullValidationError(
                "DISCOVERY_INVENTORY_INVALID",
                "selected discovery source differs from approved inventory",
            )

    corpus_payload = _read_canonical_object(paths.corpus_manifest_path, "CORPUS_INVALID")
    _assert_inert_payload(corpus_payload, "CORPUS_INVALID")
    _verify_embedded_hash(corpus_payload, "manifest_hash")
    if corpus_payload.get("manifest_hash") != EXPECTED_CORPUS_MANIFEST_HASH:
        raise UnixFullValidationError("CORPUS_INVALID", "corpus manifest hash differs")
    corpus = read_unix_corpus_manifest(paths.corpus_intake_root)
    if corpus.record_count != 13 or corpus.quarantined_source_count != 0:
        raise UnixFullValidationError("CORPUS_INVALID", "corpus record or quarantine count differs")
    normalized_bytes = _verify_corpus_records(paths, corpus_payload)

    index_payload = _read_canonical_object(
        paths.retrieval_index_manifest_path,
        "INDEX_INVALID",
    )
    _assert_inert_payload(index_payload, "INDEX_INVALID")
    _verify_embedded_hash(index_payload, "index_hash")
    if index_payload.get("index_hash") != EXPECTED_INDEX_MANIFEST_HASH:
        raise UnixFullValidationError("INDEX_INVALID", "retrieval index hash differs")
    index_verification = verify_unix_retrieval_index(
        paths.retrieval_index_root,
        paths.corpus_manifest_path,
        paths.corpus_records_path,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
    )
    if not index_verification.valid or index_verification.manifest is None:
        raise UnixFullValidationError("INDEX_INVALID", index_verification.reason)
    _verify_index_files(paths, index_payload)

    descriptor_payload = _read_canonical_object(paths.hat_descriptor_path, "HAT_INVALID")
    descriptor = unix_hat_descriptor_from_payload(
        descriptor_payload,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        expected_index_manifest_hash=EXPECTED_INDEX_MANIFEST_HASH,
    )
    expected_descriptor = create_unix_hat_descriptor(
        corpus_payload,
        index_payload,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        expected_index_manifest_hash=EXPECTED_INDEX_MANIFEST_HASH,
    )
    if descriptor != expected_descriptor or descriptor.descriptor_hash != EXPECTED_HAT_DESCRIPTOR_HASH:
        raise UnixFullValidationError("HAT_INVALID", "UNIX Hat descriptor differs")
    if descriptor.capability_ids or descriptor.authority_status != NON_AUTHORITATIVE:
        raise UnixFullValidationError("HAT_INVALID", "UNIX Hat capability or authority differs")
    _assert_no_executable_values(descriptor, "HAT_INVALID")

    routing_policy = _read_canonical_object(paths.routing_policy_path, "ROUTING_INVALID")
    _assert_inert_payload(routing_policy, "ROUTING_INVALID")
    _verify_embedded_hash(routing_policy, "policy_hash")
    if routing_policy != routing_policy_manifest_payload(descriptor):
        raise UnixFullValidationError("ROUTING_INVALID", "routing policy differs")
    if routing_policy.get("routing_policy_version") != EXPECTED_ROUTING_POLICY_VERSION:
        raise UnixFullValidationError("ROUTING_INVALID", "routing policy version differs")

    route_validation = _read_canonical_object(paths.route_validation_path, "ROUTING_INVALID")
    _assert_inert_payload(route_validation, "ROUTING_INVALID")
    _verify_embedded_hash(route_validation, "validation_hash")
    rebuilt_validation = _rebuild_route_validation(route_validation, descriptor)
    if route_validation != rebuilt_validation:
        raise UnixFullValidationError("ROUTING_INVALID", "route validation replay differs")

    visible_verification = verify_visible_unix_demo(paths.visible_demo_root)
    if not visible_verification.valid:
        raise UnixFullValidationError("VISIBLE_DEMO_INVALID", visible_verification.reason)
    visible_manifest = _read_canonical_object(
        paths.visible_demo_manifest_path,
        "VISIBLE_DEMO_INVALID",
    )
    _assert_inert_payload(visible_manifest, "VISIBLE_DEMO_INVALID")
    _verify_embedded_hash(visible_manifest, "manifest_hash")
    if visible_manifest.get("manifest_hash") != EXPECTED_VISIBLE_DEMO_MANIFEST_HASH:
        raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible demo hash differs")
    _verify_visible_review_models_and_rendering(paths, visible_manifest)

    return UnixUnitVerification(
        approved_source_inventory_hash=approved_inventory_hash,
        discovery_inventory_hash=discovery_inventory_hash,
        corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        corpus_record_count=corpus.record_count,
        normalized_bytes=normalized_bytes,
        retrieval_index_hash=EXPECTED_INDEX_MANIFEST_HASH,
        indexed_record_count=index_verification.manifest.record_count,
        unix_hat_descriptor_hash=descriptor.descriptor_hash,
        unix_hat_capability_count=len(descriptor.capability_ids),
        routing_policy_hash=_required_hash(routing_policy, "policy_hash"),
        route_validation_hash=_required_hash(route_validation, "validation_hash"),
        visible_demo_manifest_hash=EXPECTED_VISIBLE_DEMO_MANIFEST_HASH,
        visible_demo_file_count=visible_verification.file_count,
    )


def replay_unix_unit_artifacts(
    repository_root: str | Path,
    output_root: str | Path,
) -> UnixUnitReplayReport:
    paths = default_unix_unit_paths(repository_root)
    upstream = verify_unix_unit_upstream(paths.repository_root)
    destination = _validated_new_root(output_root)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)

    corpus_replay = destination / "corpus_intake"
    corpus_result = reconcile_unix_corpus(
        paths.knowledge_root,
        corpus_replay,
        source_paths=(APPROVED_SOURCE_PATH,),
    )
    corpus_match = (
        corpus_result.manifest.manifest_hash == upstream.corpus_manifest_hash
        and _portable_file_map(corpus_replay) == _portable_file_map(paths.corpus_intake_root)
    )

    index_replay = destination / "retrieval_index"
    index_result = build_unix_retrieval_index(
        paths.corpus_manifest_path,
        paths.corpus_records_path,
        index_replay,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
    )
    index_match = (
        index_result.manifest.index_hash == upstream.retrieval_index_hash
        and _portable_file_map(index_replay) == _portable_file_map(paths.retrieval_index_root)
    )

    corpus_payload = _read_canonical_object(paths.corpus_manifest_path, "CORPUS_INVALID")
    index_payload = _read_canonical_object(paths.retrieval_index_manifest_path, "INDEX_INVALID")
    descriptor = create_unix_hat_descriptor(
        corpus_payload,
        index_payload,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        expected_index_manifest_hash=EXPECTED_INDEX_MANIFEST_HASH,
    )
    actual_validation = _read_canonical_object(paths.route_validation_path, "ROUTING_INVALID")
    hat_payloads = {
        "actual_query_validation.json": hat_canonical_json_bytes(
            _rebuild_route_validation(actual_validation, descriptor)
        ),
        "routing_policy_manifest.json": hat_canonical_json_bytes(
            routing_policy_manifest_payload(descriptor)
        ),
        "unix_hat_descriptor.json": hat_canonical_json_bytes(descriptor.to_dict()),
    }
    hat_root = destination / "hat_routing"
    hat_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    for relative, payload in sorted(hat_payloads.items()):
        _write_new_file(hat_root, relative, payload)
    hat_match = _portable_file_map(hat_root) == _portable_file_map(paths.hat_routing_root)

    visible_root = destination / "visible_demo"
    visible_result = materialize_visible_unix_demo(
        visible_root,
        allowed_parent=destination,
    )
    visible_match = (
        visible_result.valid
        and _portable_file_map(visible_root) == _portable_file_map(paths.visible_demo_root)
    )

    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "corpus_manifest_hash": upstream.corpus_manifest_hash,
        "corpus_replay_match": corpus_match,
        "hat_routing_replay_match": hat_match,
        "retrieval_index_hash": upstream.retrieval_index_hash,
        "retrieval_index_replay_match": index_match,
        "unix_hat_descriptor_hash": upstream.unix_hat_descriptor_hash,
        "visible_demo_manifest_hash": upstream.visible_demo_manifest_hash,
        "visible_demo_replay_match": visible_match,
    }
    report_hash = _sha256(_canonical_bytes(material))
    return UnixUnitReplayReport(
        corpus_replay_match=corpus_match,
        retrieval_index_replay_match=index_match,
        hat_routing_replay_match=hat_match,
        visible_demo_replay_match=visible_match,
        corpus_manifest_hash=upstream.corpus_manifest_hash,
        retrieval_index_hash=upstream.retrieval_index_hash,
        unix_hat_descriptor_hash=upstream.unix_hat_descriptor_hash,
        visible_demo_manifest_hash=upstream.visible_demo_manifest_hash,
        authority_status=NON_AUTHORITATIVE,
        report_hash=report_hash,
    )


def build_worktree_snapshot(
    repository_root: str | Path,
    relative_paths: Iterable[str],
    *,
    branch: str,
    head: str,
) -> dict[str, Any]:
    root = Path(repository_root).resolve(strict=True)
    paths = tuple(sorted(set(relative_paths)))
    if not paths or len(paths) > MAX_WORKTREE_FILES:
        raise UnixFullValidationError("WORKTREE_SNAPSHOT_INVALID", "worktree path count is invalid")
    if not isinstance(branch, str) or not branch or not _is_git_object_id(head):
        raise UnixFullValidationError("WORKTREE_SNAPSHOT_INVALID", "branch or HEAD is invalid")
    records = []
    for relative in paths:
        path = _resolve_relative_regular_file(root, relative, "WORKTREE_SNAPSHOT_INVALID")
        records.append(
            {
                "path": relative,
                "sha256": _hash_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "branch": branch,
        "head": head,
        "repository_relative_identity": REPOSITORY_RELATIVE_IDENTITY,
        "schema_version": WORKTREE_SNAPSHOT_SCHEMA_VERSION,
        "files": records,
        "local_worktree_freeze_not_git_release": True,
    }
    return {**material, "snapshot_hash": _sha256(_canonical_bytes(material))}


def benchmark_unix_unit(
    repository_root: str | Path,
    output_root: str | Path,
    *,
    repetitions: int = 5,
) -> dict[str, Any]:
    if type(repetitions) is not int or repetitions < 3 or repetitions > 25:
        raise UnixFullValidationError("BENCHMARK_INVALID", "benchmark repetitions are invalid")
    paths = default_unix_unit_paths(repository_root)
    upstream = verify_unix_unit_upstream(paths.repository_root)
    destination = _validated_new_root(output_root)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)

    tracemalloc.start()
    ingestion_start = time.perf_counter_ns()
    ingestion = reconcile_unix_corpus(
        paths.knowledge_root,
        destination / "corpus_intake",
        source_paths=(APPROVED_SOURCE_PATH,),
    )
    ingestion_wall = time.perf_counter_ns() - ingestion_start
    _current, ingestion_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    index_start = time.perf_counter_ns()
    index = build_unix_retrieval_index(
        paths.corpus_manifest_path,
        paths.corpus_records_path,
        destination / "retrieval_index",
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
    )
    index_wall = time.perf_counter_ns() - index_start
    _current, index_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    cold_start = time.perf_counter_ns()
    cold = retrieve_unix_knowledge(
        paths.retrieval_index_root,
        paths.corpus_manifest_path,
        paths.corpus_records_path,
        FIXED_BENCHMARK_QUERIES[0],
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        evaluation_context="UNIX_FULL_VALIDATION_BENCHMARK",
    )
    cold_latency = time.perf_counter_ns() - cold_start
    if isinstance(cold, UnixRetrievalFailure):
        raise UnixFullValidationError("BENCHMARK_INVALID", cold.reason)

    loaded = load_unix_retrieval_index(
        paths.retrieval_index_root,
        paths.corpus_manifest_path,
        paths.corpus_records_path,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
    )
    query_latencies: list[int] = []
    query_hashes: dict[str, str] = {}
    result_counts: dict[str, int] = {}
    for _repeat in range(repetitions):
        for query in FIXED_BENCHMARK_QUERIES:
            started = time.perf_counter_ns()
            result = retrieve_loaded_unix_knowledge(
                loaded,
                query,
                evaluation_context="UNIX_FULL_VALIDATION_BENCHMARK",
            )
            query_latencies.append(time.perf_counter_ns() - started)
            result_hash = unix_retrieval_result_hash(result)
            existing = query_hashes.setdefault(query, result_hash)
            if existing != result_hash:
                raise UnixFullValidationError("BENCHMARK_INVALID", "query result is not deterministic")
            result_counts[query] = len(result.candidates)

    descriptor = verify_visible_unix_upstream().descriptor
    route_latencies: list[int] = []
    proposal_hashes: dict[str, str] = {}
    for _repeat in range(repetitions):
        for _slug, query, _expected in ACTUAL_DEMO_QUERIES:
            request = create_unix_route_request(query)
            started = time.perf_counter_ns()
            proposal = propose_unix_route(request, descriptor)
            route_latencies.append(time.perf_counter_ns() - started)
            existing = proposal_hashes.setdefault(query, proposal.proposal_hash)
            if existing != proposal.proposal_hash:
                raise UnixFullValidationError("BENCHMARK_INVALID", "route proposal is not deterministic")

    verified_visible = verify_visible_unix_upstream()
    model_latencies: list[int] = []
    text_latencies: list[int] = []
    html_latencies: list[int] = []
    model_hashes: dict[str, str] = {}
    for _repeat in range(repetitions):
        for _slug, query, _expected in ACTUAL_DEMO_QUERIES:
            started = time.perf_counter_ns()
            model = build_visible_unix_review_model(query, upstream=verified_visible)
            model_latencies.append(time.perf_counter_ns() - started)
            existing = model_hashes.setdefault(query, model.review_model_hash)
            if existing != model.review_model_hash:
                raise UnixFullValidationError("BENCHMARK_INVALID", "review model is not deterministic")
            started = time.perf_counter_ns()
            render_visible_unix_text(model)
            text_latencies.append(time.perf_counter_ns() - started)
            started = time.perf_counter_ns()
            render_visible_unix_html(model)
            html_latencies.append(time.perf_counter_ns() - started)

    demo_started = time.perf_counter_ns()
    demo_payloads = build_visible_unix_demo_payloads()
    demo_wall = time.perf_counter_ns() - demo_started
    index_manifest = _read_canonical_object(paths.retrieval_index_manifest_path, "INDEX_INVALID")
    source_size = sum(source.size_bytes for source in ingestion.manifest.sources)
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "benchmark_root_is_disposable_local_data": True,
        "corpus": {
            "canonical_record_count": ingestion.manifest.record_count,
            "ingestion_replay_peak_memory_bytes": ingestion_peak,
            "ingestion_replay_wall_time_ns": ingestion_wall,
            "normalized_bytes": upstream.normalized_bytes,
            "source_bytes": source_size,
            "source_count": ingestion.manifest.accepted_source_count,
        },
        "environment": {
            "cpu_identifier": platform.processor() or platform.machine() or "unknown",
            "logical_cpu_count": os.cpu_count() or 0,
            "platform": platform.platform(aliased=True, terse=True),
            "python_version": platform.python_version(),
            "repository_path": str(paths.repository_root),
            "total_memory_bytes": _total_memory_bytes(),
        },
        "hashes": {
            "corpus_manifest_hash": upstream.corpus_manifest_hash,
            "retrieval_index_hash": upstream.retrieval_index_hash,
            "unix_hat_descriptor_hash": upstream.unix_hat_descriptor_hash,
            "visible_demo_manifest_hash": upstream.visible_demo_manifest_hash,
        },
        "query_performance": {
            "cold_query_latency_ns": cold_latency,
            "deterministic_result_hashes": [
                [query, query_hashes[query]] for query in FIXED_BENCHMARK_QUERIES
            ],
            "maximum_latency_ns": max(query_latencies),
            "p50_latency_ns": _percentile(query_latencies, 50),
            "p95_latency_ns": _percentile(query_latencies, 95),
            "query_count": len(query_latencies),
            "result_counts": [[query, result_counts[query]] for query in FIXED_BENCHMARK_QUERIES],
            "warm_query_latency_ns": min(query_latencies),
        },
        "retrieval_index": {
            "index_build_peak_memory_bytes": index_peak,
            "index_build_wall_time_ns": index_wall,
            "index_bytes": index.total_index_bytes,
            "posting_count": index_manifest["posting_count"],
            "total_token_count": index_manifest["total_token_count"],
            "unique_term_count": index_manifest["unique_term_count"],
        },
        "routing": {
            "deterministic_proposal_hashes": [
                [query, proposal_hashes[query]] for _slug, query, _expected in ACTUAL_DEMO_QUERIES
            ],
            "maximum_latency_ns": max(route_latencies),
            "p50_latency_ns": _percentile(route_latencies, 50),
            "p95_latency_ns": _percentile(route_latencies, 95),
            "proposal_count": len(route_latencies),
        },
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "visible_review": {
            "complete_demo_build_time_ns": demo_wall,
            "demo_file_count": len(demo_payloads),
            "demo_total_bytes": sum(len(payload) for payload in demo_payloads.values()),
            "deterministic_review_model_hashes": [
                [query, model_hashes[query]] for _slug, query, _expected in ACTUAL_DEMO_QUERIES
            ],
            "html_render_p50_latency_ns": _percentile(html_latencies, 50),
            "review_model_p50_latency_ns": _percentile(model_latencies, 50),
            "text_render_p50_latency_ns": _percentile(text_latencies, 50),
        },
    }
    return {**material, "benchmark_hash": _sha256(_canonical_bytes(material))}


def build_validation_summary(test_summary: Mapping[str, Any]) -> dict[str, Any]:
    validated_tests = _validated_test_summary(test_summary)
    upstream = verify_unix_unit_upstream()
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "all_bindings_verified": True,
        "corpus_manifest_hash": upstream.corpus_manifest_hash,
        "retrieval_index_hash": upstream.retrieval_index_hash,
        "schema_version": VALIDATION_SUMMARY_SCHEMA_VERSION,
        "test_summary": validated_tests,
        "unix_hat_descriptor_hash": upstream.unix_hat_descriptor_hash,
        "visible_demo_manifest_hash": upstream.visible_demo_manifest_hash,
    }
    return {**material, "validation_summary_hash": _sha256(_canonical_bytes(material))}


def build_determinism_report(replay: UnixUnitReplayReport) -> dict[str, Any]:
    if type(replay) is not UnixUnitReplayReport or not all(
        (
            replay.corpus_replay_match,
            replay.retrieval_index_replay_match,
            replay.hat_routing_replay_match,
            replay.visible_demo_replay_match,
        )
    ):
        raise UnixFullValidationError("DETERMINISM_INVALID", "deterministic replay is incomplete")
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "corpus_replay_match": True,
        "hat_routing_replay_match": True,
        "replay_report_hash": replay.report_hash,
        "retrieval_index_replay_match": True,
        "schema_version": DETERMINISM_REPORT_SCHEMA_VERSION,
        "visible_demo_replay_match": True,
    }
    return {**material, "determinism_report_hash": _sha256(_canonical_bytes(material))}


def build_adversarial_report(case_counts: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "authority_attack_cases",
        "corpus_poisoning_cases",
        "hat_routing_forgery_cases",
        "index_tampering_cases",
        "path_symlink_cases",
        "resource_limit_cases",
        "visible_xss_tampering_cases",
    }
    if set(case_counts) != required or any(
        type(case_counts[name]) is not int or case_counts[name] < 1
        for name in required
    ):
        raise UnixFullValidationError("ADVERSARIAL_REPORT_INVALID", "adversarial counts are invalid")
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "case_counts": {name: case_counts[name] for name in sorted(required)},
        "final_authority_bypasses": [],
        "schema_version": ADVERSARIAL_REPORT_SCHEMA_VERSION,
        "status": "PASS",
    }
    return {**material, "adversarial_report_hash": _sha256(_canonical_bytes(material))}


def build_capability_boundary_report(
    protected_zone_counts: Mapping[str, Any],
) -> dict[str, Any]:
    if not protected_zone_counts or any(
        not isinstance(name, str)
        or type(count) is not int
        or count < 1
        for name, count in protected_zone_counts.items()
    ):
        raise UnixFullValidationError("CAPABILITY_REPORT_INVALID", "protected zone counts are invalid")
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "final_capability_violations": [],
        "protected_zone_counts": [
            [name, protected_zone_counts[name]] for name in sorted(protected_zone_counts)
        ],
        "schema_version": CAPABILITY_REPORT_SCHEMA_VERSION,
        "status": "PASS",
    }
    return {**material, "capability_report_hash": _sha256(_canonical_bytes(material))}


def materialize_unix_full_validation_freeze(
    output_root: str | Path,
    *,
    allowed_parent: str | Path,
    repository_root: str | Path,
    branch: str,
    head: str,
    worktree_snapshot: Mapping[str, Any],
    validation_summary: Mapping[str, Any],
    determinism_report: Mapping[str, Any],
    adversarial_report: Mapping[str, Any],
    capability_report: Mapping[str, Any],
    benchmark: Mapping[str, Any],
) -> UnixFreezeVerification:
    destination = _validated_new_child_root(output_root, allowed_parent)
    payloads = build_unix_full_validation_freeze_payloads(
        repository_root=repository_root,
        branch=branch,
        head=head,
        worktree_snapshot=worktree_snapshot,
        validation_summary=validation_summary,
        determinism_report=determinism_report,
        adversarial_report=adversarial_report,
        capability_report=capability_report,
        benchmark=benchmark,
    )
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    for relative, payload in sorted(payloads.items()):
        _write_new_file(destination, relative, payload)
    verification = verify_unix_full_validation_freeze(
        destination,
        repository_root=repository_root,
    )
    if not verification.valid:
        raise UnixFullValidationError(verification.status, verification.reason)
    return verification


def build_unix_full_validation_freeze_payloads(
    *,
    repository_root: str | Path,
    branch: str,
    head: str,
    worktree_snapshot: Mapping[str, Any],
    validation_summary: Mapping[str, Any],
    determinism_report: Mapping[str, Any],
    adversarial_report: Mapping[str, Any],
    capability_report: Mapping[str, Any],
    benchmark: Mapping[str, Any],
) -> dict[str, bytes]:
    paths = default_unix_unit_paths(repository_root)
    upstream = verify_unix_unit_upstream(paths.repository_root)
    if not isinstance(branch, str) or not branch or not _is_git_object_id(head):
        raise UnixFullValidationError("FREEZE_INPUT_INVALID", "branch or HEAD is invalid")
    worktree = _validated_hashed_report(
        worktree_snapshot,
        schema_version=WORKTREE_SNAPSHOT_SCHEMA_VERSION,
        hash_field="snapshot_hash",
    )
    validation = _validated_hashed_report(
        validation_summary,
        schema_version=VALIDATION_SUMMARY_SCHEMA_VERSION,
        hash_field="validation_summary_hash",
    )
    determinism = _validated_hashed_report(
        determinism_report,
        schema_version=DETERMINISM_REPORT_SCHEMA_VERSION,
        hash_field="determinism_report_hash",
    )
    adversarial = _validated_hashed_report(
        adversarial_report,
        schema_version=ADVERSARIAL_REPORT_SCHEMA_VERSION,
        hash_field="adversarial_report_hash",
    )
    capability = _validated_hashed_report(
        capability_report,
        schema_version=CAPABILITY_REPORT_SCHEMA_VERSION,
        hash_field="capability_report_hash",
    )
    benchmark_payload = _validated_hashed_report(
        benchmark,
        schema_version=BENCHMARK_SCHEMA_VERSION,
        hash_field="benchmark_hash",
    )
    if worktree.get("branch") != branch or worktree.get("head") != head:
        raise UnixFullValidationError("FREEZE_INPUT_INVALID", "worktree branch or HEAD differs")
    if validation.get("test_summary") != _validated_test_summary(validation.get("test_summary", {})):
        raise UnixFullValidationError("FREEZE_INPUT_INVALID", "test summary differs")
    if not all(
        determinism.get(field) is True
        for field in (
            "corpus_replay_match",
            "retrieval_index_replay_match",
            "hat_routing_replay_match",
            "visible_demo_replay_match",
        )
    ):
        raise UnixFullValidationError("FREEZE_INPUT_INVALID", "determinism report is incomplete")
    if adversarial.get("status") != "PASS" or adversarial.get("final_authority_bypasses") != []:
        raise UnixFullValidationError("FREEZE_INPUT_INVALID", "adversarial report is not clean")
    if capability.get("status") != "PASS" or capability.get("final_capability_violations") != []:
        raise UnixFullValidationError("FREEZE_INPUT_INVALID", "capability report is not clean")

    component_material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "components": {
            "approved_source_inventory": {
                "path": "data/unix_corpus_ingestion_1b/approved_source_inventory.json",
                "sha256": upstream.approved_source_inventory_hash,
            },
            "corpus_manifest": {
                "path": "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json",
                "sha256": upstream.corpus_manifest_hash,
            },
            "retrieval_index_manifest": {
                "path": "data/unix_retrieval_adapter_1a/index/index_manifest.json",
                "sha256": upstream.retrieval_index_hash,
            },
            "routing_policy": {
                "path": "data/unix_hat_routing_1a/routing_policy_manifest.json",
                "sha256": upstream.routing_policy_hash,
            },
            "unix_hat_descriptor": {
                "path": "data/unix_hat_routing_1a/unix_hat_descriptor.json",
                "sha256": upstream.unix_hat_descriptor_hash,
            },
            "visible_demo_manifest": {
                "path": "data/visible_unix_prototype_1a/demo_manifest.json",
                "sha256": upstream.visible_demo_manifest_hash,
            },
            "discovery_inventory": {
                "path": "data/unix_corpus_ingestion_1b/source_inventory.json",
                "sha256": upstream.discovery_inventory_hash,
            },
        },
        "schema_version": COMPONENT_HASHES_SCHEMA_VERSION,
    }
    component_hashes = {
        **component_material,
        "component_hashes_hash": _sha256(_canonical_bytes(component_material)),
    }
    limitations_material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "limitations": list(REQUIRED_LIMITATIONS),
        "schema_version": LIMITATIONS_SCHEMA_VERSION,
    }
    limitations = {
        **limitations_material,
        "limitations_hash": _sha256(_canonical_bytes(limitations_material)),
    }
    sponsor_checklist_material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "checks": [
            ["offline_static_bundle", True],
            ["external_resources_absent", True],
            ["execution_controls_absent", True],
            ["unsupported_claims_absent", True],
            ["limitations_visible", True],
            ["authority_status_visible", True],
        ],
        "schema_version": SPONSOR_CHECKLIST_SCHEMA_VERSION,
    }
    sponsor_checklist = {
        **sponsor_checklist_material,
        "checklist_hash": _sha256(_canonical_bytes(sponsor_checklist_material)),
    }
    verification_material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "freeze_id": FREEZE_ID,
        "repair_attempted": False,
        "schema_version": FREEZE_VERIFICATION_SCHEMA_VERSION,
        "status": "READY_FOR_INDEPENDENT_VERIFICATION",
        "supersedes_freeze_manifest_hash": SUPERSEDES_FREEZE_MANIFEST_HASH,
    }
    verification = {
        **verification_material,
        "verification_hash": _sha256(_canonical_bytes(verification_material)),
    }

    root_payloads: dict[str, bytes] = {
        "adversarial_report.json": _canonical_bytes(adversarial) + b"\n",
        "benchmark.json": _canonical_bytes(benchmark_payload) + b"\n",
        "capability_boundary_report.json": _canonical_bytes(capability) + b"\n",
        "component_hashes.json": _canonical_bytes(component_hashes) + b"\n",
        "determinism_report.json": _canonical_bytes(determinism) + b"\n",
        "limitations.json": _canonical_bytes(limitations) + b"\n",
        "reproducibility_commands.txt": REPRODUCIBILITY_COMMANDS.encode("utf-8"),
        "sponsor_demo_checklist.json": _canonical_bytes(sponsor_checklist) + b"\n",
        "validation_summary.json": _canonical_bytes(validation) + b"\n",
        "verification.json": _canonical_bytes(verification) + b"\n",
        "worktree_snapshot.json": _canonical_bytes(worktree) + b"\n",
    }
    sponsor_payloads = _build_sponsor_payloads(
        paths=paths,
        validation=validation,
        benchmark=benchmark_payload,
        limitations=limitations,
        checklist=sponsor_checklist,
    )
    base = {
        **root_payloads,
        **{f"sponsor_demo/{name}": payload for name, payload in sponsor_payloads.items()},
    }
    if len(base) + 1 > MAX_EVIDENCE_FILES or sum(len(value) for value in base.values()) > MAX_EVIDENCE_TOTAL_BYTES:
        raise UnixFullValidationError("FREEZE_SIZE_LIMIT", "freeze evidence exceeds hard limits")
    file_records = [
        {"path": path, "sha256": _sha256(payload), "size_bytes": len(payload)}
        for path, payload in sorted(base.items())
    ]
    sponsor_manifest = json.loads(sponsor_payloads["bundle_manifest.json"].decode("utf-8"))
    manifest_material = {
        "adversarial_report_hash": adversarial["adversarial_report_hash"],
        "artifact_files": file_records,
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "benchmark_hash": benchmark_payload["benchmark_hash"],
        "branch": branch,
        "corpus_manifest_hash": upstream.corpus_manifest_hash,
        "freeze_id": FREEZE_ID,
        "head": head,
        "limitations_hash": limitations["limitations_hash"],
        "local_worktree_freeze_not_git_release": True,
        "repository_relative_identity": REPOSITORY_RELATIVE_IDENTITY,
        "retrieval_index_hash": upstream.retrieval_index_hash,
        "routing_policy_hash": upstream.routing_policy_hash,
        "schema_version": FREEZE_SCHEMA_VERSION,
        "sponsor_demo_manifest_hash": sponsor_manifest["manifest_hash"],
        "supersedes_freeze_manifest_hash": SUPERSEDES_FREEZE_MANIFEST_HASH,
        "test_summary": validation["test_summary"],
        "unix_hat_descriptor_hash": upstream.unix_hat_descriptor_hash,
        "validation_summary_hash": validation["validation_summary_hash"],
        "visible_demo_manifest_hash": upstream.visible_demo_manifest_hash,
        "worktree_snapshot_hash": worktree["snapshot_hash"],
    }
    freeze_manifest = {
        **manifest_material,
        "freeze_manifest_hash": _sha256(_canonical_bytes(manifest_material)),
    }
    return {
        **base,
        "freeze_manifest.json": _canonical_bytes(freeze_manifest) + b"\n",
    }


def verify_unix_full_validation_freeze(
    freeze_root: str | Path,
    *,
    repository_root: str | Path,
) -> UnixFreezeVerification:
    try:
        root = _existing_safe_directory(freeze_root, "FREEZE_INVALID")
        paths = default_unix_unit_paths(repository_root)
        manifest = _read_canonical_object(root / "freeze_manifest.json", "FREEZE_INVALID")
        _assert_inert_payload(manifest, "FREEZE_INVALID")
        _verify_embedded_hash(manifest, "freeze_manifest_hash")
        if manifest.get("schema_version") != FREEZE_SCHEMA_VERSION or manifest.get("freeze_id") != FREEZE_ID:
            raise UnixFullValidationError("FREEZE_INVALID", "freeze manifest identity differs")
        upstream = verify_unix_unit_upstream(paths.repository_root)
        expected_bindings = {
            "corpus_manifest_hash": upstream.corpus_manifest_hash,
            "retrieval_index_hash": upstream.retrieval_index_hash,
            "routing_policy_hash": upstream.routing_policy_hash,
            "unix_hat_descriptor_hash": upstream.unix_hat_descriptor_hash,
            "visible_demo_manifest_hash": upstream.visible_demo_manifest_hash,
        }
        if any(manifest.get(name) != value for name, value in expected_bindings.items()):
            raise UnixFullValidationError("FREEZE_BINDING_MISMATCH", "freeze component binding differs")
        records = manifest.get("artifact_files")
        if not isinstance(records, list) or not records or len(records) > MAX_EVIDENCE_FILES:
            raise UnixFullValidationError("FREEZE_INVALID", "freeze file records are invalid")
        expected_paths: set[str] = {"freeze_manifest.json"}
        total = (root / "freeze_manifest.json").stat().st_size
        for record in records:
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "size_bytes"}:
                raise UnixFullValidationError("FREEZE_INVALID", "freeze file record is malformed")
            relative = _safe_relative_path(record["path"], "FREEZE_INVALID")
            if relative in expected_paths or not _is_sha256(record["sha256"]) or type(record["size_bytes"]) is not int:
                raise UnixFullValidationError("FREEZE_INVALID", "freeze file record differs")
            expected_paths.add(relative)
            path = _resolve_relative_regular_file(root, relative, "FREEZE_INVALID")
            if path.stat().st_size != record["size_bytes"] or _hash_file(path) != record["sha256"]:
                raise UnixFullValidationError("FREEZE_HASH_MISMATCH", f"freeze file differs: {relative}")
            if path.stat().st_size > MAX_EVIDENCE_FILE_BYTES:
                raise UnixFullValidationError("FREEZE_SIZE_LIMIT", "freeze file exceeds hard limit")
            total += path.stat().st_size
        discovered = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        if any(path.is_symlink() for path in root.rglob("*")) or discovered != expected_paths:
            raise UnixFullValidationError("FREEZE_FILE_SET_MISMATCH", "freeze file set differs")
        if total > MAX_EVIDENCE_TOTAL_BYTES:
            raise UnixFullValidationError("FREEZE_SIZE_LIMIT", "freeze total size exceeds hard limit")

        report_specs = (
            ("component_hashes.json", COMPONENT_HASHES_SCHEMA_VERSION, "component_hashes_hash"),
            ("worktree_snapshot.json", WORKTREE_SNAPSHOT_SCHEMA_VERSION, "snapshot_hash"),
            ("validation_summary.json", VALIDATION_SUMMARY_SCHEMA_VERSION, "validation_summary_hash"),
            ("determinism_report.json", DETERMINISM_REPORT_SCHEMA_VERSION, "determinism_report_hash"),
            ("adversarial_report.json", ADVERSARIAL_REPORT_SCHEMA_VERSION, "adversarial_report_hash"),
            ("capability_boundary_report.json", CAPABILITY_REPORT_SCHEMA_VERSION, "capability_report_hash"),
            ("benchmark.json", BENCHMARK_SCHEMA_VERSION, "benchmark_hash"),
            ("limitations.json", LIMITATIONS_SCHEMA_VERSION, "limitations_hash"),
            ("verification.json", FREEZE_VERIFICATION_SCHEMA_VERSION, "verification_hash"),
            ("sponsor_demo_checklist.json", SPONSOR_CHECKLIST_SCHEMA_VERSION, "checklist_hash"),
        )
        reports = {
            name: _validated_hashed_report(
                _read_canonical_object(root / name, "FREEZE_INVALID"),
                schema_version=schema,
                hash_field=hash_field,
            )
            for name, schema, hash_field in report_specs
        }
        if reports["validation_summary.json"].get("test_summary") != manifest.get("test_summary"):
            raise UnixFullValidationError("FREEZE_TEST_SUMMARY_MISMATCH", "freeze test totals differ")
        expected_components = {
            "approved_source_inventory": {
                "path": "data/unix_corpus_ingestion_1b/approved_source_inventory.json",
                "sha256": upstream.approved_source_inventory_hash,
            },
            "corpus_manifest": {
                "path": "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json",
                "sha256": upstream.corpus_manifest_hash,
            },
            "retrieval_index_manifest": {
                "path": "data/unix_retrieval_adapter_1a/index/index_manifest.json",
                "sha256": upstream.retrieval_index_hash,
            },
            "routing_policy": {
                "path": "data/unix_hat_routing_1a/routing_policy_manifest.json",
                "sha256": upstream.routing_policy_hash,
            },
            "unix_hat_descriptor": {
                "path": "data/unix_hat_routing_1a/unix_hat_descriptor.json",
                "sha256": upstream.unix_hat_descriptor_hash,
            },
            "visible_demo_manifest": {
                "path": "data/visible_unix_prototype_1a/demo_manifest.json",
                "sha256": upstream.visible_demo_manifest_hash,
            },
            "discovery_inventory": {
                "path": "data/unix_corpus_ingestion_1b/source_inventory.json",
                "sha256": upstream.discovery_inventory_hash,
            },
        }
        if reports["component_hashes.json"].get("components") != expected_components:
            raise UnixFullValidationError("FREEZE_BINDING_MISMATCH", "component hash record differs")
        _validated_test_summary(manifest.get("test_summary", {}))
        if reports["adversarial_report.json"].get("status") != "PASS" or reports["adversarial_report.json"].get("final_authority_bypasses") != []:
            raise UnixFullValidationError("FREEZE_INVALID", "adversarial status differs")
        if reports["capability_boundary_report.json"].get("status") != "PASS" or reports["capability_boundary_report.json"].get("final_capability_violations") != []:
            raise UnixFullValidationError("FREEZE_INVALID", "capability status differs")
        if reports["limitations.json"].get("limitations") != list(REQUIRED_LIMITATIONS):
            raise UnixFullValidationError("FREEZE_LIMITATIONS_MISMATCH", "required limitations differ")
        if reports["worktree_snapshot.json"].get("snapshot_hash") != manifest.get("worktree_snapshot_hash"):
            raise UnixFullValidationError("FREEZE_WORKTREE_MISMATCH", "worktree snapshot differs")
        if (
            manifest.get("supersedes_freeze_manifest_hash") != SUPERSEDES_FREEZE_MANIFEST_HASH
            or reports["verification.json"].get("supersedes_freeze_manifest_hash")
            != SUPERSEDES_FREEZE_MANIFEST_HASH
        ):
            raise UnixFullValidationError("FREEZE_REVISION_INVALID", "freeze supersession differs")
        if reports["benchmark.json"].get("benchmark_hash") != manifest.get("benchmark_hash"):
            raise UnixFullValidationError("FREEZE_BENCHMARK_MISMATCH", "benchmark binding differs")
        sponsor_hash = _verify_sponsor_bundle(root / "sponsor_demo")
        if sponsor_hash != manifest.get("sponsor_demo_manifest_hash"):
            raise UnixFullValidationError("SPONSOR_BUNDLE_MISMATCH", "sponsor bundle binding differs")
        return UnixFreezeVerification(
            valid=True,
            status="VALID",
            reason="deterministic local freeze evidence verified",
            freeze_manifest_hash=manifest["freeze_manifest_hash"],
            sponsor_manifest_hash=sponsor_hash,
            worktree_snapshot_hash=manifest["worktree_snapshot_hash"],
            file_count=len(expected_paths),
            total_bytes=total,
        )
    except (UnixFullValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        return UnixFreezeVerification(
            valid=False,
            status=getattr(exc, "status", "FREEZE_INVALID"),
            reason=getattr(exc, "reason", f"freeze verification failed: {exc.__class__.__name__}"),
            freeze_manifest_hash=None,
            sponsor_manifest_hash=None,
            worktree_snapshot_hash=None,
            file_count=0,
            total_bytes=0,
        )


def _build_sponsor_payloads(
    *,
    paths: UnixUnitPaths,
    validation: Mapping[str, Any],
    benchmark: Mapping[str, Any],
    limitations: Mapping[str, Any],
    checklist: Mapping[str, Any],
) -> dict[str, bytes]:
    architecture = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "description": (
            "AOIA-Core UNIX Knowledge Unit is a deterministic local knowledge and review layer. "
            "It ingests approved local evidence, indexes and retrieves it, proposes an inert UNIX "
            "Hat route, and renders an offline review. It never executes commands or grants authority."
        ),
        "flow": [
            "approved local source",
            "canonical records and provenance",
            "deterministic local index",
            "read-only retrieval",
            "inert UNIX Hat and route proposal",
            "offline visible review",
            "non-authoritative freeze evidence",
        ],
        "schema_version": "aoia-unix-sponsor-architecture-1a",
    }
    boundary = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "execution_controls": [],
        "external_resources": [],
        "human_review_required": True,
        "network_required": False,
        "provider_required": False,
        "schema_version": "aoia-unix-sponsor-authority-boundary-1a",
        "unix_hat_capabilities": [],
    }
    summary = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "benchmark_hash": benchmark["benchmark_hash"],
        "schema_version": "aoia-unix-sponsor-summary-1a",
        "test_summary": validation["test_summary"],
        "validation_summary_hash": validation["validation_summary_hash"],
    }
    base = {
        "architecture_summary.json": _canonical_bytes(architecture) + b"\n",
        "authority_boundary.json": _canonical_bytes(boundary) + b"\n",
        "benchmark_summary.json": _canonical_bytes(summary) + b"\n",
        "demo.txt": (paths.visible_demo_root / "demo.txt").read_bytes(),
        "index.html": (paths.visible_demo_root / "index.html").read_bytes(),
        "limitations.json": _canonical_bytes(limitations) + b"\n",
        "reproduction.txt": REPRODUCIBILITY_COMMANDS.encode("utf-8"),
        "sponsor_demo_checklist.json": _canonical_bytes(checklist) + b"\n",
        "visible_demo_manifest.json": paths.visible_demo_manifest_path.read_bytes(),
        "visible_demo_verification.json": (paths.visible_demo_root / "verification.json").read_bytes(),
    }
    file_records = [
        {"path": name, "sha256": _sha256(payload), "size_bytes": len(payload)}
        for name, payload in sorted(base.items())
    ]
    material = {
        "authority_status": NON_AUTHORITATIVE,
        **_INERT_FLAGS,
        "files": file_records,
        "offline": True,
        "schema_version": SPONSOR_MANIFEST_SCHEMA_VERSION,
    }
    manifest = {**material, "manifest_hash": _sha256(_canonical_bytes(material))}
    return {**base, "bundle_manifest.json": _canonical_bytes(manifest) + b"\n"}


def _verify_sponsor_bundle(root: Path) -> str:
    sponsor_root = _existing_safe_directory(root, "SPONSOR_BUNDLE_INVALID")
    manifest = _read_canonical_object(sponsor_root / "bundle_manifest.json", "SPONSOR_BUNDLE_INVALID")
    _assert_inert_payload(manifest, "SPONSOR_BUNDLE_INVALID")
    _verify_embedded_hash(manifest, "manifest_hash")
    if manifest.get("schema_version") != SPONSOR_MANIFEST_SCHEMA_VERSION or manifest.get("offline") is not True:
        raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor manifest differs")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor file records are invalid")
    expected = {"bundle_manifest.json"}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size_bytes"}:
            raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor record is malformed")
        relative = _safe_relative_path(record["path"], "SPONSOR_BUNDLE_INVALID")
        path = _resolve_relative_regular_file(sponsor_root, relative, "SPONSOR_BUNDLE_INVALID")
        if relative in expected or path.stat().st_size != record["size_bytes"] or _hash_file(path) != record["sha256"]:
            raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor file differs")
        expected.add(relative)
    discovered = {
        path.relative_to(sponsor_root).as_posix()
        for path in sponsor_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if any(path.is_symlink() for path in sponsor_root.rglob("*")) or discovered != expected:
        raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor file set differs")
    html = (sponsor_root / "index.html").read_text(encoding="utf-8")
    lowered = html.casefold()
    if (
        "<script" in lowered
        or "<iframe" in lowered
        or "<button" in lowered
        or "<form" in lowered
        or _HTML_EXTERNAL_ATTRIBUTE.search(html)
    ):
        raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor HTML is not static and inert")
    limitations = _read_canonical_object(sponsor_root / "limitations.json", "SPONSOR_BUNDLE_INVALID")
    if limitations.get("limitations") != list(REQUIRED_LIMITATIONS):
        raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor limitations differ")
    boundary = _read_canonical_object(sponsor_root / "authority_boundary.json", "SPONSOR_BUNDLE_INVALID")
    _assert_inert_payload(boundary, "SPONSOR_BUNDLE_INVALID")
    if boundary.get("execution_controls") != [] or boundary.get("external_resources") != []:
        raise UnixFullValidationError("SPONSOR_BUNDLE_INVALID", "sponsor authority boundary differs")
    return manifest["manifest_hash"]


def _verify_corpus_records(paths: UnixUnitPaths, manifest: Mapping[str, Any]) -> int:
    record_ids = manifest.get("record_ids")
    sources = manifest.get("sources")
    if not isinstance(record_ids, list) or len(record_ids) != 13 or len(set(record_ids)) != 13:
        raise UnixFullValidationError("CORPUS_INVALID", "manifest record IDs are invalid")
    if not isinstance(sources, list) or len(sources) != 1:
        raise UnixFullValidationError("CORPUS_INVALID", "manifest sources are invalid")
    source = sources[0]
    _assert_inert_payload(source, "CORPUS_INVALID")
    source_path = _resolve_relative_regular_file(
        paths.knowledge_root,
        source.get("source_path"),
        "CORPUS_INVALID",
    )
    source_hash = _hash_file(source_path)
    if source_hash != source.get("source_hash") or source_path.stat().st_size != source.get("size_bytes"):
        raise UnixFullValidationError("CORPUS_INVALID", "manifest source binding differs")
    line_count = len(source_path.read_text(encoding="utf-8").splitlines())
    physical = sorted(paths.corpus_records_path.glob("*.json"))
    if {path.stem for path in physical} != set(record_ids):
        raise UnixFullValidationError("CORPUS_INVALID", "physical record set differs")
    total = 0
    for path in physical:
        record = _read_canonical_object(path, "CORPUS_INVALID")
        _assert_inert_payload(record, "CORPUS_INVALID")
        material = dict(record)
        record_id = material.pop("record_id", None)
        content = record.get("content")
        if not isinstance(content, str) or record_id != path.stem:
            raise UnixFullValidationError("CORPUS_INVALID", "record identity differs")
        if _sha256(_canonical_bytes(material)) != record_id:
            raise UnixFullValidationError("CORPUS_INVALID", "record hash differs")
        if _sha256(content.encode("utf-8")) != record.get("content_hash"):
            raise UnixFullValidationError("CORPUS_INVALID", "record content hash differs")
        if (
            record.get("source_hash") != source_hash
            or record.get("source_id") != source.get("source_id")
            or record.get("source_path") != source.get("source_path")
        ):
            raise UnixFullValidationError("CORPUS_INVALID", "record provenance differs")
        match = re.fullmatch(r"lines:(\d+)-(\d+)(?:;.*)?", str(record.get("locator")))
        if match is None or not (1 <= int(match.group(1)) <= int(match.group(2)) <= line_count):
            raise UnixFullValidationError("CORPUS_INVALID", "record locator differs")
        total += len(content.encode("utf-8"))
    if total != 797_008:
        raise UnixFullValidationError("CORPUS_INVALID", "normalized byte count differs")
    quarantine = tuple((paths.corpus_intake_root / "quarantine").glob("*"))
    if quarantine or manifest.get("quarantine_ids") != []:
        raise UnixFullValidationError("CORPUS_INVALID", "unexpected quarantine records exist")
    return total


def _verify_index_files(paths: UnixUnitPaths, manifest: Mapping[str, Any]) -> None:
    records = manifest.get("index_files")
    if not isinstance(records, list) or len(records) != 2:
        raise UnixFullValidationError("INDEX_INVALID", "index file manifest differs")
    expected = {"index_manifest.json"}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size_bytes"}:
            raise UnixFullValidationError("INDEX_INVALID", "index file record differs")
        relative = _safe_relative_path(record["path"], "INDEX_INVALID")
        path = _resolve_relative_regular_file(paths.retrieval_index_root, relative, "INDEX_INVALID")
        if _hash_file(path) != record["sha256"] or path.stat().st_size != record["size_bytes"]:
            raise UnixFullValidationError("INDEX_INVALID", "index file hash differs")
        expected.add(relative)
    actual = {path.name for path in paths.retrieval_index_root.iterdir() if path.is_file()}
    if actual != expected:
        raise UnixFullValidationError("INDEX_INVALID", "index file set differs")
    loaded = load_unix_retrieval_index(
        paths.retrieval_index_root,
        paths.corpus_manifest_path,
        paths.corpus_records_path,
        expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
    )
    if len(loaded.entries) != manifest.get("record_count"):
        raise UnixFullValidationError("INDEX_INVALID", "loaded entry count differs")
    for entry in loaded.entries:
        _assert_no_executable_values(entry, "INDEX_INVALID")


def _rebuild_route_validation(
    validation: Mapping[str, Any],
    descriptor: UnixHatDescriptor,
) -> dict[str, object]:
    proposals = validation.get("proposals")
    if not isinstance(proposals, list) or not proposals:
        raise UnixFullValidationError("ROUTING_INVALID", "route validation proposals are invalid")
    rebuilt = []
    for row in proposals:
        if not isinstance(row, dict) or not isinstance(row.get("query"), str):
            raise UnixFullValidationError("ROUTING_INVALID", "route validation row is invalid")
        request = create_unix_route_request(row["query"])
        proposal = propose_unix_route(request, descriptor)
        if proposal.route_status != row.get("route_status") or proposal.proposal_hash != row.get("proposal_hash"):
            raise UnixFullValidationError("ROUTING_INVALID", "route proposal replay differs")
        rebuilt.append((row["query"], proposal))
    return actual_query_validation_payload(tuple(rebuilt))


def _verify_visible_review_models_and_rendering(
    paths: UnixUnitPaths,
    manifest: Mapping[str, Any],
) -> None:
    models = manifest.get("models")
    if not isinstance(models, list) or len(models) != len(ACTUAL_DEMO_QUERIES):
        raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible model records differ")
    by_slug = {row.get("slug"): row for row in models if isinstance(row, dict)}
    for slug, _query, expected_status in ACTUAL_DEMO_QUERIES:
        row = by_slug.get(slug)
        if row is None:
            raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible model slug is missing")
        payload = _read_canonical_object(
            paths.visible_demo_root / f"review_models/{slug}.json",
            "VISIBLE_DEMO_INVALID",
        )
        try:
            model = visible_unix_review_model_from_payload(payload)
        except VisibleUnixPrototypeError as exc:
            raise UnixFullValidationError("VISIBLE_DEMO_INVALID", exc.reason) from exc
        verify_visible_unix_review_model(model)
        if (
            model.review_model_hash != row.get("review_model_hash")
            or model.route_status != expected_status
            or model.authority_status != NON_AUTHORITATIVE
            or model.execution_status != "NO_COMMAND_OR_ACTION_EXECUTED"
        ):
            raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible review binding differs")
        rendered = (paths.visible_demo_root / f"queries/{slug}.html").read_text(encoding="utf-8")
        if rendered != render_visible_unix_html(model):
            raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible HTML replay differs")
        lowered = rendered.casefold()
        if (
            "<script" in lowered
            or "<iframe" in lowered
            or "<button" in lowered
            or "<form" in lowered
            or _HTML_EXTERNAL_ATTRIBUTE.search(rendered)
        ):
            raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible HTML is not inert")
    demo_text = (paths.visible_demo_root / "demo.txt").read_text(encoding="utf-8")
    if "NON_AUTHORITATIVE" not in demo_text or "NO COMMAND OR ACTION WAS EXECUTED" not in demo_text:
        raise UnixFullValidationError("VISIBLE_DEMO_INVALID", "visible safety status is missing")


def _validated_test_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "adversarial_tests",
        "errors",
        "failures",
        "final_validation_tests",
        "full_suite_total",
        "non_interactive",
        "skipped",
        "static_capability_tests",
        "step12_regressions",
        "step13_ledger_tests",
        "upstream_unix_regressions",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise UnixFullValidationError("TEST_SUMMARY_INVALID", "test summary fields differ")
    result = dict(value)
    for name in required - {"non_interactive"}:
        if type(result[name]) is not int or result[name] < 0:
            raise UnixFullValidationError("TEST_SUMMARY_INVALID", "test summary count differs")
    if (
        result["non_interactive"] is not True
        or result["failures"] != 0
        or result["errors"] != 0
        or result["skipped"] > 4
        or result["full_suite_total"] < 3_174
        or result["final_validation_tests"] < 1
        or result["adversarial_tests"] < 1
    ):
        raise UnixFullValidationError("TEST_SUMMARY_INVALID", "test summary is not clean")
    return result


def _validated_hashed_report(
    value: Mapping[str, Any],
    *,
    schema_version: str,
    hash_field: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise UnixFullValidationError("REPORT_INVALID", "evidence report must be an object")
    payload = dict(value)
    supplied = payload.pop(hash_field, None)
    if payload.get("schema_version") != schema_version or not _is_sha256(supplied):
        raise UnixFullValidationError("REPORT_INVALID", "evidence report identity differs")
    _assert_inert_payload(payload, "REPORT_INVALID")
    if _sha256(_canonical_bytes(payload)) != supplied:
        raise UnixFullValidationError("REPORT_HASH_MISMATCH", "evidence report hash differs")
    return {**payload, hash_field: supplied}


def _verify_embedded_hash(
    value: Mapping[str, Any],
    hash_field: str,
    *,
    include_newline: bool = False,
) -> None:
    material = dict(value)
    supplied = material.pop(hash_field, None)
    encoded = _canonical_bytes(material) + (b"\n" if include_newline else b"")
    if not _is_sha256(supplied) or _sha256(encoded) != supplied:
        raise UnixFullValidationError("HASH_MISMATCH", f"{hash_field} does not verify")


def _assert_inert_payload(value: Mapping[str, Any], status: str) -> None:
    if value.get("authority_status") != NON_AUTHORITATIVE:
        raise UnixFullValidationError(status, "authority status differs")
    for name, expected in _INERT_FLAGS.items():
        if name in value and value.get(name) is not expected:
            raise UnixFullValidationError(status, f"authority flag differs: {name}")
    _assert_no_executable_values(value, status)


def _assert_no_executable_values(value: Any, status: str) -> None:
    seen: set[int] = set()

    def visit(item: Any) -> None:
        identity = id(item)
        if identity in seen:
            return
        seen.add(identity)
        if callable(item) or isinstance(item, types.ModuleType):
            raise UnixFullValidationError(status, "executable value is forbidden")
        if is_dataclass(item) and not isinstance(item, type):
            for field in fields(item):
                visit(getattr(item, field.name))
        elif isinstance(item, Mapping):
            for key, nested in item.items():
                visit(key)
                visit(nested)
        elif isinstance(item, (tuple, list, set, frozenset)):
            for nested in item:
                visit(nested)

    visit(value)


def _read_canonical_object(path: Path, status: str) -> dict[str, Any]:
    _assert_no_symlink_components(path)
    if not path.is_file() or path.is_symlink():
        raise UnixFullValidationError(status, "required canonical file is missing")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_EVIDENCE_FILE_BYTES:
        raise UnixFullValidationError(status, "canonical file size is invalid")
    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, UnixFullValidationError) as exc:
        raise UnixFullValidationError(status, "canonical JSON is malformed") from exc
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload) + b"\n":
        raise UnixFullValidationError(status, "JSON is not a canonical object")
    return payload


def _portable_file_map(root: Path) -> dict[str, bytes]:
    _assert_no_symlink_components(root)
    if not root.is_dir() or root.is_symlink():
        raise UnixFullValidationError("REPLAY_INVALID", "replay directory is invalid")
    entries = tuple(root.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise UnixFullValidationError("REPLAY_INVALID", "replay contains a symbolic link")
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in entries
        if path.is_file()
    }


def _validated_new_root(value: str | Path) -> Path:
    path = Path(value).absolute()
    _assert_no_symlink_components(path.parent)
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise UnixFullValidationError("OUTPUT_ROOT_INVALID", "output root must be a new path")
    if not _SAFE_OUTPUT_NAME.fullmatch(path.name):
        raise UnixFullValidationError("OUTPUT_ROOT_INVALID", "output root name is unsafe")
    if path.resolve(strict=False).parent != path.parent.resolve(strict=True):
        raise UnixFullValidationError("OUTPUT_ROOT_INVALID", "output root escapes its parent")
    return path


def _validated_new_child_root(value: str | Path, allowed_parent: str | Path) -> Path:
    parent = Path(allowed_parent).absolute()
    _assert_no_symlink_components(parent)
    if not parent.is_dir() or parent.is_symlink():
        raise UnixFullValidationError("OUTPUT_ROOT_INVALID", "allowed parent is invalid")
    path = _validated_new_root(value)
    if path.parent != parent or path.resolve(strict=False).parent != parent.resolve(strict=True):
        raise UnixFullValidationError("OUTPUT_ROOT_INVALID", "output root is not an exact child")
    return path


def _existing_safe_directory(value: str | Path, status: str) -> Path:
    path = Path(value).absolute()
    _assert_no_symlink_components(path)
    if not path.is_dir() or path.is_symlink():
        raise UnixFullValidationError(status, "required directory is invalid")
    return path


def _resolve_relative_regular_file(root: Path, value: Any, status: str) -> Path:
    relative = _safe_relative_path(value, status)
    base = root.resolve(strict=True)
    path = base.joinpath(*PurePosixPath(relative).parts)
    _assert_no_symlink_components(path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise UnixFullValidationError(status, "required file is missing") from exc
    if resolved.parent != base and base not in resolved.parents:
        raise UnixFullValidationError(status, "relative file escapes its root")
    if not resolved.is_file() or resolved.is_symlink() or path.is_symlink():
        raise UnixFullValidationError(status, "relative path is not a regular file")
    return resolved


def _safe_relative_path(value: Any, status: str) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > MAX_RELATIVE_PATH_BYTES:
        raise UnixFullValidationError(status, "relative path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise UnixFullValidationError(status, "relative path is unsafe")
    return path.as_posix()


def _write_new_file(root: Path, relative: str, payload: bytes) -> None:
    safe = _safe_relative_path(relative, "OUTPUT_ROOT_INVALID")
    if len(payload) > MAX_EVIDENCE_FILE_BYTES:
        raise UnixFullValidationError("FREEZE_SIZE_LIMIT", "evidence file exceeds hard limit")
    path = root.joinpath(*PurePosixPath(safe).parts)
    if path.parent != root:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise UnixFullValidationError("OUTPUT_EXISTS", "evidence file already exists")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def _assert_no_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if component.exists() and component.is_symlink():
            raise UnixFullValidationError("SYMLINK_PATH_REJECTED", "symbolic-link path is forbidden")


def _required_hash(value: Mapping[str, Any], name: str) -> str:
    result = value.get(name)
    if not _is_sha256(result):
        raise UnixFullValidationError("HASH_INVALID", f"{name} is invalid")
    return result


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _is_git_object_id(value: Any) -> bool:
    return isinstance(value, str) and _GIT_OBJECT_ID.fullmatch(value) is not None


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise UnixFullValidationError("DUPLICATE_JSON_KEY", "duplicate JSON key is forbidden")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise UnixFullValidationError("NONFINITE_JSON", f"non-finite JSON value is forbidden: {value}")


def _percentile(values: Sequence[int], percentile: int) -> int:
    if not values or percentile < 0 or percentile > 100:
        raise UnixFullValidationError("BENCHMARK_INVALID", "latency sample is invalid")
    ordered = sorted(values)
    index = max(0, ((len(ordered) * percentile + 99) // 100) - 1)
    return ordered[min(index, len(ordered) - 1)]


def _total_memory_bytes() -> int:
    path = Path("/proc/meminfo")
    try:
        first = path.read_text(encoding="ascii").splitlines()[0]
        match = re.fullmatch(r"MemTotal:\s+(\d+)\s+kB", first)
        return int(match.group(1)) * 1024 if match else 0
    except (OSError, UnicodeError, IndexError, ValueError):
        return 0


__all__ = [
    "APPROVED_SOURCE_INVENTORY_SCHEMA_VERSION",
    "APPROVED_SOURCE_SELECTION_POLICY_VERSION",
    "ADVERSARIAL_REPORT_SCHEMA_VERSION",
    "BENCHMARK_SCHEMA_VERSION",
    "CAPABILITY_REPORT_SCHEMA_VERSION",
    "DETERMINISM_REPORT_SCHEMA_VERSION",
    "DISCOVERY_INVENTORY_SCHEMA_VERSION",
    "EXPECTED_VISIBLE_DEMO_MANIFEST_HASH",
    "FIXED_BENCHMARK_QUERIES",
    "FREEZE_ID",
    "FREEZE_SCHEMA_VERSION",
    "NON_AUTHORITATIVE",
    "REQUIRED_LIMITATIONS",
    "SUPERSEDES_FREEZE_MANIFEST_HASH",
    "UnixFreezeVerification",
    "UnixFullValidationError",
    "UnixUnitReplayReport",
    "UnixUnitVerification",
    "benchmark_unix_unit",
    "build_adversarial_report",
    "build_approved_corpus_source_inventory",
    "build_capability_boundary_report",
    "build_determinism_report",
    "build_corpus_discovery_inventory",
    "build_unix_full_validation_freeze_payloads",
    "build_validation_summary",
    "build_worktree_snapshot",
    "default_unix_unit_paths",
    "materialize_unix_full_validation_freeze",
    "replay_unix_unit_artifacts",
    "verify_unix_full_validation_freeze",
    "verify_approved_corpus_source_inventory",
    "verify_corpus_discovery_inventory",
    "verify_unix_unit_upstream",
]
