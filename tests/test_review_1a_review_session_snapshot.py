from __future__ import annotations

import ast
import io
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path

from runtime.review_session_snapshot import (
    ReviewSessionSnapshot,
    create_review_session_snapshot,
    snapshot_to_dict,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "review_session_snapshot.py"


class Review1AReviewSessionSnapshotTests(unittest.TestCase):
    def test_creates_deterministic_snapshot_from_same_inputs(self) -> None:
        first = self.make_snapshot()
        second = self.make_snapshot()

        self.assertEqual(first, second)
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_snapshot_hash_changes_when_meaningful_input_changes(self) -> None:
        baseline = self.make_snapshot()
        changed = self.make_snapshot(source_head="f" * 40)

        self.assertNotEqual(baseline.snapshot_hash, changed.snapshot_hash)

    def test_snapshot_contains_required_boundary_language(self) -> None:
        snapshot = self.make_snapshot(review_surface_text="operator review")

        self.assertIn("not an execution instruction", snapshot.review_surface_text)
        self.assertIn("no authority granted", snapshot.review_surface_text)

    def test_all_authority_flags_remain_false(self) -> None:
        snapshot = self.make_snapshot()

        self.assertFalse(snapshot.authority_granted)
        self.assertFalse(snapshot.execution_allowed)
        self.assertFalse(snapshot.dispatch_allowed)
        self.assertFalse(snapshot.provider_call_allowed)
        self.assertFalse(snapshot.artifact_write_allowed)
        self.assertFalse(snapshot.persistence_allowed)
        self.assertFalse(snapshot.decision_created)

    def test_malformed_or_empty_snapshot_id_fails_closed(self) -> None:
        for value in ("", "   ", None, 7):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_snapshot(snapshot_id=value)

    def test_malformed_or_empty_review_text_fails_closed(self) -> None:
        for value in ("", "   ", None, {}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_snapshot(review_surface_text=value)

    def test_summary_fields_are_copied_and_not_mutated_by_later_caller_changes(self) -> None:
        original = {"status": "REVIEWABLE", "reviewable": True}
        before = deepcopy(original)

        snapshot = self.make_snapshot(summary_fields=original)
        original["status"] = "CHANGED"
        original["added"] = "later"

        self.assertEqual(before, dict(snapshot.summary_fields))

    def test_summary_fields_are_read_only(self) -> None:
        snapshot = self.make_snapshot()

        with self.assertRaises(TypeError):
            snapshot.summary_fields["status"] = "CHANGED"

    def test_no_timestamp_or_random_generation_is_required_for_determinism(self) -> None:
        first = self.make_snapshot(created_at_utc="2026-06-21T10:00:00Z")
        second = self.make_snapshot(created_at_utc="2026-06-21T10:00:00Z")

        self.assertEqual(first.snapshot_hash, second.snapshot_hash)

    def test_snapshot_serialization_dict_output_is_stable(self) -> None:
        snapshot = self.make_snapshot()

        first = snapshot_to_dict(snapshot)
        second = snapshot.to_dict()

        self.assertEqual(first, second)
        self.assertEqual(first["summary_fields"], {"reviewable": True, "status": "REVIEWABLE"})
        self.assertIsNot(first["summary_fields"], second["summary_fields"])

    def test_snapshot_to_dict_fails_closed_for_unknown_input(self) -> None:
        for value in (None, {}, "bad", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    snapshot_to_dict(value)

    def test_summary_fields_validation_fails_closed(self) -> None:
        cases = (
            [],
            {"": "value"},
            {"status": ""},
            {"status": 1},
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_snapshot(summary_fields=value)

        with self.assertRaises(ValueError):
            create_review_session_snapshot(
                snapshot_id="review-1a-snapshot",
                created_at_utc="2026-06-21T10:00:00Z",
                source_milestone="AUTH-1G Operator Review Surface",
                source_head="2ebd2d0ab7af5c77dee36edee6c0a10a23f49968",
                review_surface_text="operator review",
                summary_fields=None,
            )

    def test_constructor_rejects_tampered_hash(self) -> None:
        valid = self.make_snapshot()

        with self.assertRaises(ValueError):
            ReviewSessionSnapshot(
                snapshot_id=valid.snapshot_id,
                created_at_utc=valid.created_at_utc,
                source_milestone=valid.source_milestone,
                source_head=valid.source_head,
                review_surface_text=valid.review_surface_text,
                summary_fields=valid.summary_fields,
                snapshot_hash="0" * 64,
            )

    def test_module_has_no_stdout_or_side_effects(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.make_snapshot()
        self.assertEqual("", buffer.getvalue())

    def test_static_boundary_no_forbidden_imports_or_calls(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "sqlite3",
            "selenium",
            "playwright",
        }
        imports = []
        called_names = set()
        called_attrs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_attrs.add(node.func.attr)

        for module_name in imports:
            self.assertFalse(
                any(
                    module_name == item or module_name.startswith(item + ".")
                    for item in forbidden_modules
                )
            )
            self.assertFalse(module_name.startswith("runtime.providers"))
            self.assertFalse(module_name.startswith("runtime.dispatch"))
            self.assertFalse(module_name.startswith("runtime.execution"))

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {"system", "write_text", "write_bytes", "write", "open"}:
            self.assertNotIn(attr, called_attrs)

    def test_module_does_not_import_or_call_dispatcher_executor_provider_or_artifact_writer(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        self.assertNotIn("runtime.dispatch", source)
        self.assertNotIn("runtime.executor", source)
        self.assertNotIn("runtime.providers", source)
        self.assertNotIn("artifact_writer", source)

    def test_unknown_or_malformed_input_never_becomes_authority_bearing_snapshot(self) -> None:
        for payload in (
            {"authority_granted": True},
            {"execution_allowed": True},
            {"dispatch_allowed": True},
            {"provider_call_allowed": True},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(TypeError):
                    ReviewSessionSnapshot(**payload)

    def make_snapshot(
        self,
        *,
        snapshot_id: object = "review-1a-snapshot",
        created_at_utc: object = "2026-06-21T10:00:00Z",
        source_milestone: object = "AUTH-1G Operator Review Surface",
        source_head: object = "2ebd2d0ab7af5c77dee36edee6c0a10a23f49968",
        review_surface_text: object = (
            "operator_review_surface: REVIEWABLE\n"
            "status: INERT_RECORD_REVIEW_READY\n"
            "note: not an execution instruction\n"
            "note: no authority granted"
        ),
        summary_fields: object = None,
    ) -> ReviewSessionSnapshot:
        return create_review_session_snapshot(
            snapshot_id=snapshot_id,
            created_at_utc=created_at_utc,
            source_milestone=source_milestone,
            source_head=source_head,
            review_surface_text=review_surface_text,
            summary_fields=(
                {"reviewable": True, "status": "REVIEWABLE"}
                if summary_fields is None
                else summary_fields
            ),
        )
