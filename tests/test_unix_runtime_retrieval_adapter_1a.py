from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import types
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from unittest import mock

from human_decision_gate_integration import validate_canonical_human_gate_authority
from retrieval.unix_runtime_adapter import (
    CORPUS_RECORD_SCHEMA_VERSION,
    CORPUS_SCHEMA_VERSION,
    CORPUS_SOURCE_SCHEMA_VERSION,
    INDEX_ENTRIES_FILENAME,
    INDEX_MANIFEST_FILENAME,
    INDEX_SCHEMA_VERSION,
    NON_AUTHORITATIVE,
    PHEROMONE_MAX_ADJUSTMENT,
    DecaySnapshot,
    LoadedUnixRetrievalIndex,
    UnixRetrievalError,
    UnixRetrievalFailure,
    UnixRetrievalPreview,
    UnixRetrievalResult,
    build_unix_retrieval_index,
    load_unix_retrieval_index,
    normalize_unix_retrieval_query,
    preview_unix_retrieval,
    retrieve_loaded_unix_knowledge,
    retrieve_unix_knowledge,
    unix_retrieval_result_hash,
    unix_retrieval_result_payload,
    verify_unix_retrieval_index,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTUAL_CORPUS_ROOT = REPO_ROOT / "data" / "unix_corpus_ingestion_1b" / "intake"
ACTUAL_MANIFEST = ACTUAL_CORPUS_ROOT / "corpus_manifest.json"
ACTUAL_RECORDS = ACTUAL_CORPUS_ROOT / "records"
EXPECTED_CORPUS_MANIFEST_HASH = (
    "e7241f0d043d90bf79a3f1a9f2691691a1d87b719d39cc533c9a765d97a61768"
)
AUTHORITY_FLAGS = {
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
    "gate_satisfied": False,
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _write_canonical(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _fixture_corpus(
    root: Path,
    contents: tuple[str, ...] | None = None,
) -> tuple[Path, Path, str]:
    record_contents = contents or (
        "File permissions\nUNIX file permissions use chmod, chown, ACLs, and umask safely.",
        "Process signals\nSIGTERM requests orderly process shutdown while SIGKILL is immediate.",
        "Network boundaries\nSSH, sockets, firewall rules, and network namespaces form boundaries.",
    )
    records_root = root / "records"
    records_root.mkdir(parents=True)
    source_bytes = "\n\n".join(record_contents).encode("utf-8")
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    source_id = f"unix-source-{source_hash[:24]}"
    source_path = "extracted/fixture.txt"
    records: list[dict[str, object]] = []
    ordinal_record_ids: list[str] = []
    for ordinal, content in enumerate(record_contents, start=1):
        material: dict[str, object] = {
            "authority_status": NON_AUTHORITATIVE,
            **AUTHORITY_FLAGS,
            "content": content,
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "locator": f"lines:{ordinal * 10}-{ordinal * 10 + 9}",
            "media_type": "text/plain",
            "ordinal": ordinal,
            "schema_version": CORPUS_RECORD_SCHEMA_VERSION,
            "source_hash": source_hash,
            "source_id": source_id,
            "source_path": source_path,
        }
        record_id = hashlib.sha256(_canonical_bytes(material)).hexdigest()
        record = {**material, "record_id": record_id}
        records.append(record)
        ordinal_record_ids.append(record_id)
        _write_canonical(records_root / f"{record_id}.json", record)

    sorted_record_ids = sorted(ordinal_record_ids)
    source = {
        "authority_status": NON_AUTHORITATIVE,
        **AUTHORITY_FLAGS,
        "media_type": "text/plain",
        "quarantine_id": None,
        "record_ids": ordinal_record_ids,
        "schema_version": CORPUS_SOURCE_SCHEMA_VERSION,
        "size_bytes": len(source_bytes),
        "source_hash": source_hash,
        "source_id": source_id,
        "source_path": source_path,
        "status": "ACCEPTED",
    }
    semantic = {
        "accepted_source_count": 1,
        "authority_status": NON_AUTHORITATIVE,
        **AUTHORITY_FLAGS,
        "quarantine_ids": [],
        "quarantined_source_count": 0,
        "record_count": len(records),
        "record_ids": sorted_record_ids,
        "schema_version": CORPUS_SCHEMA_VERSION,
        "source_count": 1,
        "sources": [source],
    }
    corpus_digest = hashlib.sha256(_canonical_bytes(semantic)).hexdigest()
    corpus_id = f"unix-corpus-{corpus_digest[:24]}"
    hash_material = {**semantic, "corpus_id": corpus_id}
    manifest_hash = hashlib.sha256(_canonical_bytes(hash_material)).hexdigest()
    manifest = {**hash_material, "manifest_hash": manifest_hash}
    manifest_path = root / "corpus_manifest.json"
    _write_canonical(manifest_path, manifest)
    return manifest_path, records_root, manifest_hash


def _assert_no_callable_or_module(test: unittest.TestCase, value: object) -> None:
    seen: set[int] = set()

    def visit(item: object) -> None:
        identity = id(item)
        if identity in seen:
            return
        seen.add(identity)
        test.assertFalse(callable(item))
        test.assertNotIsInstance(item, types.ModuleType)
        if is_dataclass(item) and not isinstance(item, type):
            for field in fields(item):
                visit(getattr(item, field.name))
        elif isinstance(item, dict):
            for key, nested in item.items():
                visit(key)
                visit(nested)
        elif isinstance(item, (tuple, list, set, frozenset)):
            for nested in item:
                visit(nested)

    visit(value)


class UnixRuntimeRetrievalFixtureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest, self.records, self.manifest_hash = _fixture_corpus(
            self.root / "corpus"
        )
        self.index_root = self.root / "index"
        self.build = build_unix_retrieval_index(
            self.manifest,
            self.records,
            self.index_root,
            expected_corpus_manifest_hash=self.manifest_hash,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()


class CorpusIndexBindingTests(UnixRuntimeRetrievalFixtureTestCase):
    def test_valid_corpus_builds_and_index_verifies(self) -> None:
        verification = verify_unix_retrieval_index(
            self.index_root,
            self.manifest,
            self.records,
            expected_corpus_manifest_hash=self.manifest_hash,
        )
        self.assertTrue(verification.valid)
        self.assertEqual("VALID", verification.status)
        self.assertEqual(3, verification.manifest.record_count)
        self.assertEqual(NON_AUTHORITATIVE, verification.manifest.authority_status)

    def test_index_binds_exact_corpus_manifest_hash_and_records(self) -> None:
        loaded = load_unix_retrieval_index(
            self.index_root,
            self.manifest,
            self.records,
        )
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_hash"], loaded.manifest.corpus_manifest_hash)
        self.assertEqual(tuple(manifest["record_ids"]), loaded.manifest.indexed_record_ids)

    def test_changed_corpus_invalidates_existing_index(self) -> None:
        changed_manifest, changed_records, _changed_hash = _fixture_corpus(
            self.root / "changed",
            contents=(
                "File permissions\nChanged canonical content.",
                "Process signals\nSIGTERM information.",
                "Network boundaries\nSSH boundary information.",
            ),
        )
        result = verify_unix_retrieval_index(
            self.index_root,
            changed_manifest,
            changed_records,
        )
        self.assertFalse(result.valid)
        self.assertIn(result.status, {"CORPUS_MANIFEST_MISMATCH", "STALE_INDEX"})

    def test_missing_manifested_record_fails_closed(self) -> None:
        record_id = json.loads(self.manifest.read_text(encoding="utf-8"))["record_ids"][0]
        (self.records / f"{record_id}.json").unlink()
        result = verify_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertFalse(result.valid)
        self.assertEqual("MISSING_RECORD", result.status)

    def test_changed_record_content_hash_fails_closed(self) -> None:
        record_id = json.loads(self.manifest.read_text(encoding="utf-8"))["record_ids"][0]
        path = self.records / f"{record_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["content"] += " forged"
        _write_canonical(path, payload)
        result = verify_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertFalse(result.valid)
        self.assertEqual("RECORD_HASH_MISMATCH", result.status)

    def test_extra_unmanifested_record_does_not_enter_index(self) -> None:
        extra_id = "f" * 64
        _write_canonical(self.records / f"{extra_id}.json", {"ignored": True})
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertNotIn(extra_id, loaded.manifest.indexed_record_ids)
        self.assertEqual(3, loaded.manifest.record_count)

    def test_wrong_independently_retained_manifest_hash_is_rejected(self) -> None:
        result = verify_unix_retrieval_index(
            self.index_root,
            self.manifest,
            self.records,
            expected_corpus_manifest_hash="0" * 64,
        )
        self.assertFalse(result.valid)
        self.assertEqual("CORPUS_MANIFEST_MISMATCH", result.status)

    def test_index_hash_independently_recalculates(self) -> None:
        payload = json.loads(
            (self.index_root / INDEX_MANIFEST_FILENAME).read_text(encoding="utf-8")
        )
        recorded = payload.pop("index_hash")
        self.assertEqual(hashlib.sha256(_canonical_bytes(payload)).hexdigest(), recorded)

    def test_deterministic_index_replay_is_byte_identical(self) -> None:
        replay = self.root / "replay"
        replay_build = build_unix_retrieval_index(
            self.manifest,
            self.records,
            replay,
            expected_corpus_manifest_hash=self.manifest_hash,
        )
        self.assertEqual(self.build.manifest.index_hash, replay_build.manifest.index_hash)
        for name in sorted(path.name for path in self.index_root.iterdir()):
            self.assertEqual(
                (self.index_root / name).read_bytes(),
                (replay / name).read_bytes(),
            )

    def test_output_root_is_explicit_and_not_rewritten(self) -> None:
        original = {
            path.name: path.read_bytes()
            for path in self.index_root.iterdir()
        }
        with self.assertRaises(UnixRetrievalError) as caught:
            build_unix_retrieval_index(
                self.manifest,
                self.records,
                self.index_root,
            )
        self.assertEqual("OUTPUT_EXISTS", caught.exception.status)
        self.assertEqual(
            original,
            {path.name: path.read_bytes() for path in self.index_root.iterdir()},
        )

    def test_output_root_cannot_overlap_canonical_record_input(self) -> None:
        nested_output = self.records / "nested-index-output"
        with self.assertRaises(UnixRetrievalError) as caught:
            build_unix_retrieval_index(
                self.manifest,
                self.records,
                nested_output,
            )
        self.assertEqual("INVALID_OUTPUT_ROOT", caught.exception.status)
        self.assertFalse(nested_output.exists())

    def test_unknown_index_schema_fails_closed(self) -> None:
        path = self.index_root / INDEX_MANIFEST_FILENAME
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["schema_version"] = "future-index"
        _write_canonical(path, payload)
        result = verify_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertFalse(result.valid)
        self.assertEqual("UNKNOWN_SCHEMA", result.status)

    def test_malformed_index_json_fails_closed(self) -> None:
        (self.index_root / INDEX_MANIFEST_FILENAME).write_bytes(b"{not-json}\n")
        result = verify_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertFalse(result.valid)
        self.assertEqual("MALFORMED_INDEX", result.status)

    def test_corrupted_index_file_is_rejected_without_rebuild(self) -> None:
        entries = self.index_root / INDEX_ENTRIES_FILENAME
        entries.write_bytes(entries.read_bytes() + b"{}\n")
        before = entries.read_bytes()
        result = retrieve_unix_knowledge(
            self.index_root,
            self.manifest,
            self.records,
            "file permissions",
        )
        self.assertIsInstance(result, UnixRetrievalFailure)
        self.assertEqual("INDEX_HASH_MISMATCH", result.status)
        self.assertEqual(before, entries.read_bytes())

    def test_missing_index_returns_structured_failure(self) -> None:
        result = retrieve_unix_knowledge(
            self.root / "missing-index",
            self.manifest,
            self.records,
            "file permissions",
        )
        self.assertIsInstance(result, UnixRetrievalFailure)
        self.assertEqual("MISSING_INDEX", result.status)
        self.assertFalse(result.command_or_action_executed)


class QueryNormalizationAndRankingTests(UnixRuntimeRetrievalFixtureTestCase):
    def test_query_normalization_is_unicode_case_and_whitespace_deterministic(self) -> None:
        first = normalize_unix_retrieval_query(
            "  UNIX\u00a0FILE  Permissions  ",
            evaluation_context="fixed-evaluation",
        )
        second = normalize_unix_retrieval_query(
            "  UNIX\u00a0FILE  Permissions  ",
            evaluation_context="fixed-evaluation",
        )
        self.assertEqual("unix file permissions", first.normalized_query)
        self.assertEqual(first, second)
        self.assertEqual(first.query_hash, second.query_hash)

    def test_empty_and_whitespace_queries_are_rejected(self) -> None:
        for value in ("", " \t\n "):
            with self.subTest(value=value):
                with self.assertRaises(UnixRetrievalError) as caught:
                    normalize_unix_retrieval_query(value)
                self.assertEqual("EMPTY_QUERY", caught.exception.status)

    def test_oversized_and_over_tokenized_queries_are_rejected(self) -> None:
        with self.assertRaises(UnixRetrievalError) as caught:
            normalize_unix_retrieval_query("x" * 2049)
        self.assertEqual("QUERY_TOO_LONG", caught.exception.status)
        with self.assertRaises(UnixRetrievalError) as caught:
            normalize_unix_retrieval_query(" ".join(f"t{value}" for value in range(65)))
        self.assertEqual("TOO_MANY_TOKENS", caught.exception.status)

    def test_invalid_limits_are_rejected_without_querying(self) -> None:
        for value in (True, 0, 21):
            with self.subTest(value=value):
                with self.assertRaises(UnixRetrievalError) as caught:
                    normalize_unix_retrieval_query("permissions", requested_limit=value)
                self.assertEqual("INVALID_LIMIT", caught.exception.status)

    def test_same_query_and_index_have_identical_order_and_hash(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        first = retrieve_loaded_unix_knowledge(
            loaded,
            "UNIX file permissions",
            evaluation_context="fixed",
        )
        second = retrieve_loaded_unix_knowledge(
            loaded,
            "UNIX file permissions",
            evaluation_context="fixed",
        )
        self.assertEqual(first, second)
        self.assertEqual(unix_retrieval_result_hash(first), unix_retrieval_result_hash(second))

    def test_exact_phrase_and_title_components_are_visible(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        result = retrieve_loaded_unix_knowledge(loaded, "file permissions")
        top = result.candidates[0]
        self.assertGreater(top.score_breakdown.exact_phrase_score, 0)
        self.assertGreater(top.score_breakdown.title_score, 0)
        self.assertEqual(top.final_score, top.score_breakdown.final_score)

    def test_all_score_components_are_bounded_integers(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        result = retrieve_loaded_unix_knowledge(loaded, "permissions chmod")
        for candidate in result.candidates:
            for field in fields(candidate.score_breakdown):
                self.assertIs(type(getattr(candidate.score_breakdown, field.name)), int)
            self.assertGreaterEqual(candidate.final_score, 0)

    def test_stable_tie_breaking_uses_record_id(self) -> None:
        manifest, records, manifest_hash = _fixture_corpus(
            self.root / "ties",
            contents=(
                "Alpha record\nshared token only",
                "Beta record\nshared token only",
            ),
        )
        index = self.root / "tie-index"
        build_unix_retrieval_index(
            manifest,
            records,
            index,
            expected_corpus_manifest_hash=manifest_hash,
        )
        result = retrieve_unix_knowledge(index, manifest, records, "shared token")
        self.assertIsInstance(result, UnixRetrievalResult)
        ids = [candidate.record_id for candidate in result.candidates]
        self.assertEqual(sorted(ids), ids)

    def test_unrelated_query_returns_no_confident_result(self) -> None:
        result = retrieve_unix_knowledge(
            self.index_root,
            self.manifest,
            self.records,
            "zzzxylophone astronomy",
        )
        self.assertIsInstance(result, UnixRetrievalResult)
        self.assertEqual("NO_CONFIDENT_RESULT", result.status)
        self.assertEqual((), result.candidates)

    def test_command_url_and_path_looking_queries_remain_inert_text(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        with mock.patch("pathlib.Path.write_text", side_effect=AssertionError("write")), mock.patch(
            "pathlib.Path.write_bytes", side_effect=AssertionError("write")
        ):
            result = retrieve_loaded_unix_knowledge(
                loaded,
                "sudo rm -rf / and https://example.invalid chmod",
            )
        self.assertFalse(result.command_or_action_executed)
        self.assertIn("COMMAND_LOOKING_QUERY_TREATED_AS_INERT_TEXT", result.warnings)

    def test_runtime_loaded_query_performs_no_filesystem_access(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        with mock.patch.object(Path, "open", side_effect=AssertionError("filesystem access")), mock.patch.object(
            Path, "read_bytes", side_effect=AssertionError("filesystem access")
        ):
            result = retrieve_loaded_unix_knowledge(loaded, "process signals")
        self.assertEqual("OK", result.status)

    def test_missing_dates_produce_deterministic_unknown_decay(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        first = retrieve_loaded_unix_knowledge(
            loaded,
            "process signals",
            evaluation_context="2026-07-14T10:00:00Z",
        )
        second = retrieve_loaded_unix_knowledge(
            loaded,
            "process signals",
            evaluation_context="2026-07-14T10:00:00Z",
        )
        self.assertIsInstance(first.decay_snapshot, DecaySnapshot)
        self.assertEqual("STALENESS_UNKNOWN", first.decay_snapshot.status)
        self.assertEqual(first.decay_snapshot, second.decay_snapshot)
        self.assertEqual(0, first.decay_snapshot.staleness_adjustment)

    def test_pheromone_input_is_fail_closed_until_governed_schema_exists(self) -> None:
        result = retrieve_unix_knowledge(
            self.index_root,
            self.manifest,
            self.records,
            "file permissions",
            pheromone_metadata={"tag": "boost", "value": 999999},
        )
        self.assertIsInstance(result, UnixRetrievalFailure)
        self.assertEqual("INVALID_PHEROMONE_DATA", result.status)
        self.assertEqual(0, PHEROMONE_MAX_ADJUSTMENT)

    def test_preview_contains_complete_non_authoritative_metadata(self) -> None:
        preview = preview_unix_retrieval(
            self.index_root,
            self.manifest,
            self.records,
            "SSH network boundaries",
            evaluation_context="fixed",
        )
        self.assertIsInstance(preview, UnixRetrievalPreview)
        self.assertEqual(NON_AUTHORITATIVE, preview.authority_status)
        self.assertEqual("NO_COMMAND_OR_ACTION_EXECUTED", preview.action_statement)
        self.assertEqual(len(preview.candidates), preview.candidate_count)
        self.assertEqual(self.build.manifest.index_hash, preview.index_hash)
        self.assertEqual(self.manifest_hash, preview.corpus_manifest_hash)
        _assert_no_callable_or_module(self, preview)

    def test_result_objects_are_frozen(self) -> None:
        result = retrieve_unix_knowledge(
            self.index_root,
            self.manifest,
            self.records,
            "file permissions",
        )
        self.assertIsInstance(result, UnixRetrievalResult)
        with self.assertRaises(FrozenInstanceError):
            result.status = "APPROVED"

    def test_result_cannot_be_canonical_human_gate_authority(self) -> None:
        result = retrieve_unix_knowledge(
            self.index_root,
            self.manifest,
            self.records,
            "file permissions",
        )
        reason = validate_canonical_human_gate_authority(
            result,
            expected_artifact_hash="0" * 64,
            expected_approval_decision_id="decision",
            expected_audit_event_id="audit",
            expected_contract_audit_event_id="contract",
        )
        self.assertEqual("artifact write requires exact canonical human gate evidence", reason)

    def test_html_and_command_excerpts_are_plain_source_text(self) -> None:
        manifest, records, manifest_hash = _fixture_corpus(
            self.root / "html-corpus",
            contents=(
                "HTML example\n<script>execute()</script> sudo apt install package",
            ),
        )
        index = self.root / "html-index"
        build_unix_retrieval_index(
            manifest,
            records,
            index,
            expected_corpus_manifest_hash=manifest_hash,
        )
        result = retrieve_unix_knowledge(index, manifest, records, "sudo apt install")
        self.assertIsInstance(result, UnixRetrievalResult)
        self.assertIn("sudo apt install", result.candidates[0].excerpt)
        self.assertFalse(result.command_or_action_executed)


class FailureAndInertnessTests(UnixRuntimeRetrievalFixtureTestCase):
    def test_no_legacy_or_provider_fallback_on_invalid_index(self) -> None:
        (self.index_root / INDEX_MANIFEST_FILENAME).write_bytes(b"broken\n")
        with mock.patch(
            "retrieval.linux.retrieval_engine.LinuxRetrievalEngine.retrieve",
            side_effect=AssertionError("legacy fallback"),
        ):
            result = retrieve_unix_knowledge(
                self.index_root,
                self.manifest,
                self.records,
                "permissions",
            )
        self.assertIsInstance(result, UnixRetrievalFailure)
        self.assertEqual((), tuple(self.index_root.glob("*.repaired")))

    def test_adapter_source_has_no_execution_network_routing_or_gate_imports(self) -> None:
        path = REPO_ROOT / "runtime" / "retrieval" / "unix_runtime_adapter.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        forbidden = {
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "webbrowser",
            "runtime.orchestrator.knowledge_router",
            "runtime.providers.gateway",
            "runtime.human_decision_gate_integration",
            "runtime.human_decision_gated_artifact_write",
            "runtime.patches.controlled_patch_apply",
        }
        self.assertFalse(imports.intersection(forbidden))

    def test_loaded_index_and_result_contain_no_callable(self) -> None:
        loaded = load_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertIsInstance(loaded, LoadedUnixRetrievalIndex)
        _assert_no_callable_or_module(self, loaded)
        result = retrieve_loaded_unix_knowledge(loaded, "permissions")
        _assert_no_callable_or_module(self, result)

    def test_result_hash_is_canonical_and_stable(self) -> None:
        result = retrieve_unix_knowledge(
            self.index_root,
            self.manifest,
            self.records,
            "file permissions",
            evaluation_context="fixed",
        )
        payload = unix_retrieval_result_payload(result)
        expected = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        self.assertEqual(expected, unix_retrieval_result_hash(result))

    def test_forged_provenance_is_rejected(self) -> None:
        entries = self.index_root / INDEX_ENTRIES_FILENAME
        rows = entries.read_text(encoding="utf-8").splitlines()
        payload = json.loads(rows[0])
        payload["provenance"]["source_hash"] = "0" * 64
        rows[0] = _canonical_bytes(payload).decode("utf-8")
        entries.write_text("\n".join(rows) + "\n", encoding="utf-8")
        result = verify_unix_retrieval_index(self.index_root, self.manifest, self.records)
        self.assertFalse(result.valid)
        self.assertEqual("INDEX_HASH_MISMATCH", result.status)


class ActualCanonicalCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.index_root = Path(cls.temporary.name) / "actual-index"
        cls.build = build_unix_retrieval_index(
            ACTUAL_MANIFEST,
            ACTUAL_RECORDS,
            cls.index_root,
            expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_actual_manifest_and_all_thirteen_records_verify(self) -> None:
        verification = verify_unix_retrieval_index(
            self.index_root,
            ACTUAL_MANIFEST,
            ACTUAL_RECORDS,
            expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        )
        self.assertTrue(verification.valid)
        self.assertEqual(13, verification.manifest.record_count)
        self.assertEqual(EXPECTED_CORPUS_MANIFEST_HASH, verification.manifest.corpus_manifest_hash)

    def test_actual_index_replay_matches_portable_files(self) -> None:
        replay = Path(self.temporary.name) / f"replay-{self.id().split('.')[-1]}"
        replay_build = build_unix_retrieval_index(
            ACTUAL_MANIFEST,
            ACTUAL_RECORDS,
            replay,
            expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        )
        self.assertEqual(self.build.manifest.index_hash, replay_build.manifest.index_hash)
        for source_file in sorted(self.index_root.iterdir()):
            self.assertEqual(source_file.read_bytes(), (replay / source_file.name).read_bytes())

    def test_fixed_actual_query_set_has_deterministic_result_hashes(self) -> None:
        queries = (
            "UNIX file permissions",
            "path traversal",
            "shell injection",
            "process signals",
            "pipes",
            "sudo",
            "SSH",
            "systemd",
            "Linux namespaces",
            "control groups",
            "containers",
            "package management",
            "network boundaries",
        )
        loaded = load_unix_retrieval_index(
            self.index_root,
            ACTUAL_MANIFEST,
            ACTUAL_RECORDS,
            expected_corpus_manifest_hash=EXPECTED_CORPUS_MANIFEST_HASH,
        )
        first = [
            unix_retrieval_result_hash(
                retrieve_loaded_unix_knowledge(
                    loaded,
                    query,
                    evaluation_context="2026-07-14T11:41:00+02:00",
                )
            )
            for query in queries
        ]
        second = [
            unix_retrieval_result_hash(
                retrieve_loaded_unix_knowledge(
                    loaded,
                    query,
                    evaluation_context="2026-07-14T11:41:00+02:00",
                )
            )
            for query in queries
        ]
        self.assertEqual(first, second)
        self.assertEqual(len(queries), len(first))
        self.assertTrue(all(len(value) == 64 for value in first))

    def test_actual_command_and_authority_queries_execute_nothing(self) -> None:
        for query in (
            "Explain sudo rm -rf safely",
            "approved human_approved authority execute write provider",
        ):
            with self.subTest(query=query):
                preview = preview_unix_retrieval(
                    self.index_root,
                    ACTUAL_MANIFEST,
                    ACTUAL_RECORDS,
                    query,
                    evaluation_context="fixed",
                )
                self.assertIsInstance(preview, UnixRetrievalPreview)
                self.assertEqual("NO_COMMAND_OR_ACTION_EXECUTED", preview.action_statement)
                self.assertEqual(NON_AUTHORITATIVE, preview.authority_status)


if __name__ == "__main__":
    unittest.main()
