from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from runtime.memory.runtime_schemas import (
    MEMORY_RUNTIME_BLOCKED_AUTHORITY_CLAIM,
    MEMORY_RUNTIME_BLOCKED_AUTONOMY_SMUGGLING,
    MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_HASH,
    MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_ID,
    MEMORY_RUNTIME_BLOCKED_EMBEDDING_SMUGGLING,
    MEMORY_RUNTIME_BLOCKED_EXECUTION_SMUGGLING,
    MEMORY_RUNTIME_BLOCKED_EXPIRED_TAG,
    MEMORY_RUNTIME_BLOCKED_EXPIRED_TETRAD,
    MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH,
    MEMORY_RUNTIME_BLOCKED_INVALID_HASH,
    MEMORY_RUNTIME_BLOCKED_INVALID_TAG,
    MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD,
    MEMORY_RUNTIME_BLOCKED_INVALID_TIME,
    MEMORY_RUNTIME_BLOCKED_NON_JSON_SERIALIZABLE,
    MEMORY_RUNTIME_BLOCKED_PROVIDER_CALL,
    MEMORY_RUNTIME_BLOCKED_RETRIEVAL_SMUGGLING,
    MEMORY_RUNTIME_BLOCKED_STORAGE_SMUGGLING,
    MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND,
    MEMORY_RUNTIME_BLOCKED_UNKNOWN_TARGET,
    MEMORY_RUNTIME_NON_AUTHORITY,
    MEMORY_RUNTIME_OK,
    MEMORY_RUNTIME_PHEROMONE_TAG_METADATA_ONLY,
    MEMORY_RUNTIME_REQUIRES_CONTROLLED_PATH,
    MEMORY_RUNTIME_REQUIRES_HUMAN_REVIEW,
    MEMORY_RUNTIME_TETRAD_METADATA_ONLY,
    build_pheromone_memory_tag,
    build_tetrad_knowledge_object,
    canonical_memory_runtime_json,
    hash_memory_runtime_value,
    validate_memory_runtime_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "memory" / "runtime_schemas.py"


class MemoryRuntimeInertSchemas1ATests(unittest.TestCase):
    def test_tetrad_tag_and_validation_are_deterministic_hash_bound_and_inert(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)

        first = validate_memory_runtime_metadata(tetrad=tetrad, tags=(tag,), now=20)
        second = validate_memory_runtime_metadata(tetrad=self.tetrad(), tags=(self.tag(self.tetrad().object_hash),), now=20)

        self.assertEqual(tetrad.object_hash, self.tetrad().object_hash)
        self.assertEqual(tag.tag_hash, self.tag(tetrad.object_hash).tag_hash)
        self.assertEqual(first.validation_hash, second.validation_hash)
        self.assertTrue(first.ok)
        self.assertFalse(first.blocked)
        self.assertEqual(tetrad.object_hash, first.tetrad_hash)
        self.assertEqual((tag.tag_hash,), first.tag_hashes)
        self.assertIn(MEMORY_RUNTIME_OK, first.reason_codes)
        self.assertIn(MEMORY_RUNTIME_TETRAD_METADATA_ONLY, first.memory_codes)
        self.assertIn(MEMORY_RUNTIME_PHEROMONE_TAG_METADATA_ONLY, first.memory_codes)
        self.assertIn(MEMORY_RUNTIME_NON_AUTHORITY, first.memory_codes)
        self.assertIn(MEMORY_RUNTIME_REQUIRES_HUMAN_REVIEW, first.memory_codes)
        self.assertIn(MEMORY_RUNTIME_REQUIRES_CONTROLLED_PATH, first.memory_codes)
        self.assert_metadata_only(first.to_dict())

    def test_objects_are_frozen_and_expose_no_runtime_methods(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        result = validate_memory_runtime_metadata(tetrad=tetrad, tags=(tag,), now=20)

        with self.assertRaises(FrozenInstanceError):
            tetrad.summary = "changed"
        with self.assertRaises(FrozenInstanceError):
            tag.reason = "changed"
        with self.assertRaises(FrozenInstanceError):
            result.authority_allowed = True

        for item in (tetrad, tag, result):
            for forbidden in ("execute", "dispatch", "run", "write", "approve", "authorize", "call_provider"):
                self.assertFalse(hasattr(item, forbidden))

    def test_hashes_change_when_bound_evidence_changes(self):
        baseline = self.tetrad()
        changed_raw = self.tetrad(raw_evidence_hash=self.hash_value("raw-changed"))
        changed_summary = self.tetrad(summary="Different inert summary.")
        self.assertNotEqual(baseline.object_hash, changed_raw.object_hash)
        self.assertNotEqual(baseline.object_hash, changed_summary.object_hash)

        tag = self.tag(baseline.object_hash)
        changed_tag = self.tag(baseline.object_hash, tag_kind="operator_bookmarked")
        self.assertNotEqual(tag.tag_hash, changed_tag.tag_hash)

        first = validate_memory_runtime_metadata(tetrad=baseline, tags=(tag,), now=20)
        second = validate_memory_runtime_metadata(tetrad=baseline, tags=(), now=20)
        self.assertNotEqual(first.validation_hash, second.validation_hash)

    def test_canonical_json_is_deterministic_and_rejects_non_json_values(self):
        self.assertEqual(
            canonical_memory_runtime_json({"b": 1, "a": ("x",)}),
            canonical_memory_runtime_json({"a": ["x"], "b": 1}),
        )
        for value in ({"bad": object()}, {"bad": b"bytes"}, {"bad": {1, 2}}, {1: "bad"}, {"bad": float("nan")}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonical_memory_runtime_json(value)

    def test_hash_mismatch_and_invalid_hash_fail_closed(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        cases = (
            ({**tetrad.to_dict(), "object_hash": "9" * 64}, (tag,), MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH),
            ({**tetrad.to_dict(), "raw_evidence_hash": "bad"}, (tag,), MEMORY_RUNTIME_BLOCKED_INVALID_HASH),
            (tetrad, ({**tag.to_dict(), "tag_hash": "8" * 64},), MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH),
            (tetrad, ({**tag.to_dict(), "target_hash": "bad"},), MEMORY_RUNTIME_BLOCKED_INVALID_HASH),
        )
        for altered_tetrad, altered_tags, reason in cases:
            with self.subTest(reason=reason):
                result = validate_memory_runtime_metadata(tetrad=altered_tetrad, tags=altered_tags, now=20)
                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_schema_label_and_target_validation_fail_closed(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        cases = (
            ({**tetrad.to_dict(), "schema_version": "future"}, (tag,), MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD),
            ({**tetrad.to_dict(), "status_label": "canonical_ready"}, (tag,), MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD),
            (tetrad, ({**tag.to_dict(), "schema_version": "future"},), MEMORY_RUNTIME_BLOCKED_INVALID_TAG),
            (tetrad, ({**tag.to_dict(), "tag_kind": "auto_reinforce"},), MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND),
            (tetrad, ({**tag.to_dict(), "signal_label": "execute"},), MEMORY_RUNTIME_BLOCKED_INVALID_TAG),
            (tetrad, (self.tag("1" * 64),), MEMORY_RUNTIME_BLOCKED_UNKNOWN_TARGET),
        )
        for altered_tetrad, altered_tags, reason in cases:
            with self.subTest(reason=reason):
                result = validate_memory_runtime_metadata(tetrad=altered_tetrad, tags=altered_tags, now=20)
                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_time_validation_and_expiration_fail_closed(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        cases = (
            (tetrad, (tag,), None, MEMORY_RUNTIME_BLOCKED_INVALID_TIME),
            (tetrad, (tag,), -1, MEMORY_RUNTIME_BLOCKED_INVALID_TIME),
            (self.tetrad(created_at=30, expires_at=40), (tag,), 20, MEMORY_RUNTIME_BLOCKED_INVALID_TIME),
            (self.tetrad(created_at=1, expires_at=10), (tag,), 20, MEMORY_RUNTIME_BLOCKED_EXPIRED_TETRAD),
            (tetrad, (self.tag(tetrad.object_hash, created_at=30, expires_at=40),), 20, MEMORY_RUNTIME_BLOCKED_INVALID_TIME),
            (tetrad, (self.tag(tetrad.object_hash, created_at=1, expires_at=10),), 20, MEMORY_RUNTIME_BLOCKED_EXPIRED_TAG),
            ({**tetrad.to_dict(), "expires_at": 1}, (tag,), 20, MEMORY_RUNTIME_BLOCKED_INVALID_TIME),
            (tetrad, ({**tag.to_dict(), "expires_at": 1},), 20, MEMORY_RUNTIME_BLOCKED_INVALID_TIME),
        )
        for altered_tetrad, altered_tags, now, reason in cases:
            with self.subTest(reason=reason):
                result = validate_memory_runtime_metadata(tetrad=altered_tetrad, tags=altered_tags, now=now)
                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_duplicate_tags_fail_closed(self):
        tetrad = self.tetrad()
        first = self.tag(tetrad.object_hash, tag_id="tag-a")
        duplicate_id = self.tag(tetrad.object_hash, tag_id="tag-a", tag_kind="operator_bookmarked")
        duplicate_hash = {**self.tag(tetrad.object_hash, tag_id="tag-b").to_dict(), "tag_hash": first.tag_hash}

        result_id = validate_memory_runtime_metadata(tetrad=tetrad, tags=(first, duplicate_id), now=20)
        result_hash = validate_memory_runtime_metadata(tetrad=tetrad, tags=(first, duplicate_hash), now=20)

        self.assertIn(MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_ID, result_id.reason_codes)
        self.assertIn(MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_HASH, result_hash.reason_codes)
        self.assert_metadata_only(result_id.to_dict())
        self.assert_metadata_only(result_hash.to_dict())

    def test_smuggling_storage_retrieval_embeddings_autonomy_provider_execution_and_authority_fails_closed(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        cases = (
            ({**tetrad.to_dict(), "summary": "sqlite storage_write requested"}, MEMORY_RUNTIME_BLOCKED_STORAGE_SMUGGLING),
            ({**tetrad.to_dict(), "summary": "retrieval_ranking with bm25"}, MEMORY_RUNTIME_BLOCKED_RETRIEVAL_SMUGGLING),
            ({**tetrad.to_dict(), "summary": "embedding vector index"}, MEMORY_RUNTIME_BLOCKED_EMBEDDING_SMUGGLING),
            ({**tetrad.to_dict(), "summary": "autonomous agent_memory_autonomy"}, MEMORY_RUNTIME_BLOCKED_AUTONOMY_SMUGGLING),
            ({**tetrad.to_dict(), "summary": "provider_call with call_provider"}, MEMORY_RUNTIME_BLOCKED_PROVIDER_CALL),
            ({**tetrad.to_dict(), "summary": "dispatch tool_call shell command"}, MEMORY_RUNTIME_BLOCKED_EXECUTION_SMUGGLING),
            ({**tetrad.to_dict(), "summary": "approved authority gate_satisfied"}, MEMORY_RUNTIME_BLOCKED_AUTHORITY_CLAIM),
            ({**tetrad.to_dict(), "approved": True}, MEMORY_RUNTIME_BLOCKED_AUTHORITY_CLAIM),
        )
        for altered_tetrad, reason in cases:
            with self.subTest(reason=reason):
                result = validate_memory_runtime_metadata(tetrad=altered_tetrad, tags=(tag,), now=20)
                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_non_json_serializable_validation_fails_closed(self):
        tetrad = self.tetrad()
        result = validate_memory_runtime_metadata(tetrad={**tetrad.to_dict(), "bad": object()}, tags=(), now=20)

        self.assertTrue(result.blocked)
        self.assertIn(MEMORY_RUNTIME_BLOCKED_NON_JSON_SERIALIZABLE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_allowed_unsafe_for_execution_tag_remains_inert_not_authority(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash, tag_kind="unsafe_for_execution", reason="Human should not treat this evidence as executable.")

        result = validate_memory_runtime_metadata(tetrad=tetrad, tags=(tag,), now=20)

        self.assertTrue(result.ok)
        self.assert_metadata_only(result.to_dict())

    def test_hash_helper_is_sha256_and_non_secret(self):
        value_hash = hash_memory_runtime_value({"example": "memory"})

        self.assertEqual(64, len(value_hash))
        int(value_hash, 16)

    def test_module_has_no_forbidden_runtime_imports_or_calls(self):
        tree = ast.parse(RUNTIME_FILE.read_text(encoding="utf-8"))
        forbidden_imports = {
            "asyncio",
            "threading",
            "multiprocessing",
            "subprocess",
            "os",
            "socket",
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "sqlite3",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "google",
        }
        forbidden_calls = {"eval", "exec", "__import__", "open"}
        imports: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else ""
                calls.add(name)

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def assert_metadata_only(self, payload):
        for key in (
            "authority_allowed",
            "storage_allowed",
            "retrieval_allowed",
            "ranking_allowed",
            "embedding_allowed",
            "decay_allowed",
            "reinforcement_allowed",
            "provider_call_allowed",
            "execution_allowed",
            "dispatch_allowed",
            "autonomous_memory_allowed",
        ):
            self.assertFalse(payload[key])
        self.assertTrue(payload["requires_human_review"])
        self.assertTrue(payload["requires_controlled_path"])

    def tetrad(self, **overrides):
        values = {
            "object_id": "tetrad-1",
            "raw_evidence_hash": self.hash_value("raw"),
            "structured_claims_hash": self.hash_value("claims"),
            "semantic_view_hash": self.hash_value("semantic"),
            "audit_risk_hash": self.hash_value("audit"),
            "source_hashes": (self.hash_value("source"),),
            "status_label": "needs_review",
            "summary": "Four inert surfaces represent one reviewed evidence package.",
            "created_at": 10,
            "expires_at": 100,
        }
        values.update(overrides)
        return build_tetrad_knowledge_object(**values)

    def tag(self, target_hash, **overrides):
        values = {
            "tag_id": "tag-1",
            "target_hash": target_hash,
            "tag_kind": "needs_revalidation",
            "signal_label": "medium",
            "reason": "Operator should review freshness before reuse.",
            "created_at": 10,
            "expires_at": 100,
        }
        values.update(overrides)
        return build_pheromone_memory_tag(**values)

    def hash_value(self, text):
        return hash_memory_runtime_value({"fixture": text})


if __name__ == "__main__":
    unittest.main()
