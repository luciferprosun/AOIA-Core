from __future__ import annotations

import ast
import unittest
from pathlib import Path

from runtime.review_session_bundle import (
    ReviewSessionBundle,
    create_review_session_bundle,
    review_session_bundle_to_dict,
)
from runtime.review_session_snapshot import (
    ReviewSessionSnapshot,
    create_review_session_snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "review_session_bundle.py"


class Review1BReviewSessionBundleTests(unittest.TestCase):
    def test_creates_deterministic_bundle_from_same_inputs(self) -> None:
        snapshots = [self.make_snapshot("snapshot-a"), self.make_snapshot("snapshot-b")]

        first = self.make_bundle(snapshots=snapshots)
        second = self.make_bundle(snapshots=snapshots)

        self.assertEqual(first, second)
        self.assertEqual(first.bundle_hash, second.bundle_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_bundle_hash_changes_when_snapshot_list_changes(self) -> None:
        first = self.make_bundle(snapshots=[self.make_snapshot("snapshot-a")])
        second = self.make_bundle(snapshots=[self.make_snapshot("snapshot-b")])

        self.assertNotEqual(first.bundle_hash, second.bundle_hash)

    def test_bundle_hash_changes_when_metadata_changes(self) -> None:
        baseline = self.make_bundle()

        self.assertNotEqual(baseline.bundle_hash, self.make_bundle(bundle_id="bundle-b").bundle_hash)
        self.assertNotEqual(
            baseline.bundle_hash,
            self.make_bundle(created_at_utc="2026-06-21T12:00:00Z").bundle_hash,
        )

    def test_rejects_empty_snapshot_list(self) -> None:
        with self.assertRaises(ValueError):
            self.make_bundle(snapshots=[])

    def test_rejects_malformed_or_empty_bundle_id(self) -> None:
        for value in ("", "   ", None, 7):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_bundle(bundle_id=value)

    def test_rejects_malformed_or_empty_timestamp(self) -> None:
        for value in ("", "   ", None, {}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_bundle(created_at_utc=value)

    def test_rejects_malformed_snapshot_like_input(self) -> None:
        for value in (None, {}, "snapshot", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    self.make_bundle(snapshots=[value])

    def test_copies_snapshot_hashes_from_caller_collection(self) -> None:
        snapshots = [self.make_snapshot("snapshot-a")]
        original_snapshot = snapshots[0]
        expected_hashes = (snapshots[0].snapshot_hash,)

        bundle = self.make_bundle(snapshots=snapshots)
        snapshots.append(self.make_snapshot("snapshot-b"))

        self.assertIs(original_snapshot, snapshots[0])
        self.assertEqual(expected_hashes, bundle.snapshot_hashes)
        self.assertEqual(1, bundle.snapshot_count)

    def test_preserves_snapshot_order_deterministically(self) -> None:
        first = self.make_snapshot("snapshot-a")
        second = self.make_snapshot("snapshot-b")

        bundle = self.make_bundle(snapshots=[second, first])

        self.assertEqual((second.snapshot_hash, first.snapshot_hash), bundle.snapshot_hashes)

    def test_includes_required_boundary_language(self) -> None:
        bundle = self.make_bundle()

        self.assertIn("not an execution instruction", bundle.boundary_text)
        self.assertIn("no authority granted", bundle.boundary_text)

    def test_all_authority_flags_are_false(self) -> None:
        bundle = self.make_bundle()

        self.assertFalse(bundle.authority_granted)
        self.assertFalse(bundle.execution_allowed)
        self.assertFalse(bundle.dispatch_allowed)
        self.assertFalse(bundle.provider_call_allowed)
        self.assertFalse(bundle.artifact_write_allowed)
        self.assertFalse(bundle.persistence_allowed)
        self.assertFalse(bundle.decision_created)

    def test_dict_serialization_is_stable_and_copied(self) -> None:
        bundle = self.make_bundle()

        first = review_session_bundle_to_dict(bundle)
        second = bundle.to_dict()

        self.assertEqual(first, second)
        self.assertEqual(list(bundle.snapshot_hashes), first["snapshot_hashes"])
        self.assertIsNot(first["snapshot_hashes"], second["snapshot_hashes"])

    def test_dict_projection_rejects_unknown_input(self) -> None:
        for value in (None, {}, "bad", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    review_session_bundle_to_dict(value)

    def test_constructor_rejects_tampered_hash(self) -> None:
        valid = self.make_bundle()

        with self.assertRaises(ValueError):
            ReviewSessionBundle(
                bundle_id=valid.bundle_id,
                created_at_utc=valid.created_at_utc,
                snapshot_count=valid.snapshot_count,
                snapshot_hashes=valid.snapshot_hashes,
                boundary_text=valid.boundary_text,
                bundle_hash="0" * 64,
            )

    def test_authority_bearing_snapshot_is_rejected(self) -> None:
        snapshot = self.make_snapshot("snapshot-a")
        object.__setattr__(snapshot, "authority_granted", True)

        with self.assertRaises(ValueError):
            self.make_bundle(snapshots=[snapshot])

    def test_snapshot_with_tampered_hash_is_rejected(self) -> None:
        snapshot = self.make_snapshot("snapshot-a")
        object.__setattr__(snapshot, "snapshot_hash", "0" * 64)

        with self.assertRaises(ValueError):
            self.make_bundle(snapshots=[snapshot])

    def test_malformed_input_never_creates_authority_bearing_bundle(self) -> None:
        for payload in (
            {"authority_granted": True},
            {"execution_allowed": True},
            {"dispatch_allowed": True},
            {"provider_call_allowed": True},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(TypeError):
                    ReviewSessionBundle(**payload)

    def test_static_boundary_has_no_forbidden_imports_or_calls(self) -> None:
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

    def test_module_does_not_reference_capability_components(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        self.assertNotIn("runtime.dispatch", source)
        self.assertNotIn("runtime.executor", source)
        self.assertNotIn("runtime.providers", source)
        self.assertNotIn("artifact_writer", source)

    def make_snapshot(self, snapshot_id: str) -> ReviewSessionSnapshot:
        return create_review_session_snapshot(
            snapshot_id=snapshot_id,
            created_at_utc="2026-06-21T10:00:00Z",
            source_milestone="AUTH-1G Operator Review Surface",
            source_head="2ebd2d0ab7af5c77dee36edee6c0a10a23f49968",
            review_surface_text="operator review",
            summary_fields={"reviewable": True, "status": "REVIEWABLE"},
        )

    def make_bundle(
        self,
        *,
        bundle_id: object = "bundle-a",
        created_at_utc: object = "2026-06-21T11:00:00Z",
        snapshots: object = None,
    ) -> ReviewSessionBundle:
        return create_review_session_bundle(
            bundle_id=bundle_id,
            created_at_utc=created_at_utc,
            snapshots=[self.make_snapshot("snapshot-a")] if snapshots is None else snapshots,
        )
