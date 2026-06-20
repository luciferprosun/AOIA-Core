from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
import unittest

from runtime.knowledge.tetrad import EVIDENCE, TetradFace, TetradRecord
from runtime.knowledge.tetrad_index import (
    DuplicateTetradIndexKeyError,
    InvalidTetradIndexKeyError,
    TetradExactKeyIndex,
    TetradIndexKeyNotFoundError,
    TetradIndexSnapshot,
    build_tetrad_exact_key_index,
    lookup_tetrad_record,
    snapshot_tetrad_index,
)
from runtime.safety.approval_artifact_gate import (
    evaluate_pre_artifact_approval_gate,
)
from runtime.schemas.approval_decision import approval_decision_to_dict


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_RUNTIME = REPO_ROOT / "runtime" / "knowledge" / "tetrad_index.py"
AUTHORITY_RUNTIME_PATHS = (
    REPO_ROOT / "runtime" / "schemas" / "approval_decision.py",
    REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_policy.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py",
    REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
    REPO_ROOT / "runtime" / "provider_registry.py",
    REPO_ROOT / "runtime" / "model_router.py",
)


class TetradDExactKeyIndexTests(unittest.TestCase):
    def test_build_is_deterministic_and_does_not_mutate_inputs(self):
        first = self.make_record("First")
        second = self.make_record("Second")
        records = [second, first]
        before = [record.to_dict() for record in records]

        index_a = build_tetrad_exact_key_index(records)
        index_b = build_tetrad_exact_key_index((first, second))

        self.assertEqual(before, [record.to_dict() for record in records])
        self.assertEqual(index_a.index_id, index_b.index_id)
        self.assertEqual(index_a.index_hash, index_b.index_hash)
        self.assertEqual(tuple(sorted((first.tetrad_id, second.tetrad_id))), index_a.keys)
        self.assertTrue(index_a.read_only)
        self.assertTrue(index_a.display_only)
        self.assertTrue(index_a.non_authoritative)

    def test_exact_key_lookup_returns_expected_immutable_record(self):
        first = self.make_record("First")
        second = self.make_record("Second")
        index = build_tetrad_exact_key_index((first, second))

        result = lookup_tetrad_record(index, second.tetrad_id)

        self.assertIs(second, result)
        self.assertEqual(second.tetrad_id, result.tetrad_id)
        with self.assertRaises(FrozenInstanceError):
            result.read_only = False

    def test_missing_exact_key_fails_closed(self):
        record = self.make_record("Present")
        index = build_tetrad_exact_key_index((record,))
        missing = "0" * 64 if record.tetrad_id != "0" * 64 else "1" * 64

        with self.assertRaises(TetradIndexKeyNotFoundError):
            lookup_tetrad_record(index, missing)

    def test_duplicate_key_fails_closed(self):
        record = self.make_record("Duplicate")

        with self.assertRaises(DuplicateTetradIndexKeyError):
            build_tetrad_exact_key_index((record, record))

    def test_missing_and_invalid_keys_fail_closed(self):
        record = self.make_record("Valid")
        index = build_tetrad_exact_key_index((record,))
        invalid = (None, "", " ", "a" * 63, "A" * 64, record.tetrad_id + "0")

        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(InvalidTetradIndexKeyError):
                    lookup_tetrad_record(index, value)

    def test_invalid_records_and_mismatched_entries_fail_closed(self):
        record = self.make_record("Valid")

        for values in (None, "not-records", [object()]):
            with self.subTest(values=values):
                with self.assertRaises(TypeError):
                    build_tetrad_exact_key_index(values)
        with self.assertRaises(ValueError):
            TetradExactKeyIndex(entries=(("0" * 64, record),))

    def test_index_and_snapshot_are_immutable_and_snapshot_is_deterministic(self):
        first = self.make_record("First")
        second = self.make_record("Second")
        index = build_tetrad_exact_key_index((first, second))

        snapshot_a = snapshot_tetrad_index(index)
        snapshot_b = snapshot_tetrad_index(index)
        payload = snapshot_a.to_dict()
        payload["keys"].append("0" * 64)

        self.assertEqual(snapshot_a, snapshot_b)
        self.assertEqual(index.keys, snapshot_a.keys)
        self.assertEqual(2, snapshot_a.record_count)
        self.assertTrue(snapshot_a.read_only)
        self.assertTrue(snapshot_a.display_only)
        self.assertTrue(snapshot_a.non_authoritative)
        self.assertNotEqual(tuple(payload["keys"]), snapshot_a.keys)
        with self.assertRaises(FrozenInstanceError):
            index.entries = ()
        with self.assertRaises(FrozenInstanceError):
            snapshot_a.keys = ()

    def test_snapshot_and_index_expose_no_authority_fields(self):
        forbidden = {
            "approved",
            "approval",
            "gate_passed",
            "write_allowed",
            "execution_ready",
            "provider_enabled",
            "live_call_allowed",
            "canonical_by_tetrad",
            "trusted",
        }
        index_fields = {item.name for item in fields(TetradExactKeyIndex)}
        snapshot_fields = {item.name for item in fields(TetradIndexSnapshot)}
        snapshot_keys = set(
            snapshot_tetrad_index(
                build_tetrad_exact_key_index((self.make_record("One"),))
            ).to_dict()
        )

        self.assertTrue(index_fields.isdisjoint(forbidden))
        self.assertTrue(snapshot_fields.isdisjoint(forbidden))
        self.assertTrue(snapshot_keys.isdisjoint(forbidden))

    def test_index_is_rejected_as_approval_decision_and_denied_by_gate(self):
        index = build_tetrad_exact_key_index((self.make_record("One"),))

        with self.assertRaises(TypeError):
            approval_decision_to_dict(index)
        result = evaluate_pre_artifact_approval_gate(
            approval_decision=index,
            approval_audit_handoff_result=object(),
        )

        self.assertFalse(result.allowed)
        self.assertIsNone(result.approval_decision_id)

    def test_authority_provider_and_write_modules_do_not_import_index(self):
        for path in AUTHORITY_RUNTIME_PATHS:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("knowledge.tetrad_index", source)
                self.assertNotIn("import tetrad_index", source)

    def test_module_has_no_forbidden_capabilities_or_expansion_terms(self):
        source = INDEX_RUNTIME.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_import_roots = {
            "anthropic",
            "httpx",
            "openai",
            "pexpect",
            "playwright",
            "pty",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        forbidden_calls = (
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
            "open(",
            "write_text(",
            "write_bytes(",
        )
        forbidden_terms = (
            "embedding",
            "vector",
            "semantic_search",
            "fuzzy",
            "directed_acyclic_graph",
            "provider_registry",
            "provider_clients",
            "approval_artifact_gate",
            "gated_durable_artifact_flow",
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            self.assertTrue(roots.isdisjoint(forbidden_import_roots))
        for value in forbidden_calls:
            self.assertNotIn(value, source)
        lowered = source.lower()
        for value in forbidden_terms:
            self.assertNotIn(value, lowered)

    def make_record(self, content: str) -> TetradRecord:
        return TetradRecord(
            evidence=TetradFace(
                face_type=EVIDENCE,
                content=(content,),
                source_refs=("tetrad-d-test",),
            ),
        )


if __name__ == "__main__":
    unittest.main()
