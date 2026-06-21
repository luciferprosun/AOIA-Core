from __future__ import annotations

import ast
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from runtime.human_review_decision import (
    ALLOWED_DECISION_STATUSES,
    APPROVE_FOR_NEXT_REVIEW_STEP,
    NEEDS_CHANGES,
    REJECT,
    HumanReviewDecision,
    create_human_review_decision,
    human_review_decision_to_dict,
)
from runtime.review_session_bundle import ReviewSessionBundle, create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "human_review_decision.py"
_DEFAULT_BUNDLE = object()


class Decision1AHumanReviewDecisionTests(unittest.TestCase):
    def test_creates_deterministic_decision_from_same_inputs(self) -> None:
        bundle = self.make_bundle()

        first = self.make_decision(bundle=bundle)
        second = self.make_decision(bundle=bundle)

        self.assertEqual(first, second)
        self.assertEqual(first.decision_hash, second.decision_hash)

    def test_decision_hash_changes_when_status_changes(self) -> None:
        first = self.make_decision(decision_status=REJECT)
        second = self.make_decision(decision_status=NEEDS_CHANGES)

        self.assertNotEqual(first.decision_hash, second.decision_hash)

    def test_decision_hash_changes_when_human_note_changes(self) -> None:
        first = self.make_decision(human_note="reason one")
        second = self.make_decision(human_note="reason two")

        self.assertNotEqual(first.decision_hash, second.decision_hash)

    def test_decision_hash_changes_when_bound_bundle_hash_changes(self) -> None:
        first = self.make_decision(bundle=self.make_bundle(snapshot_id="snapshot-a"))
        second = self.make_decision(bundle=self.make_bundle(snapshot_id="snapshot-b"))

        self.assertNotEqual(first.bundle_hash, second.bundle_hash)
        self.assertNotEqual(first.decision_hash, second.decision_hash)

    def test_rejects_empty_or_malformed_decision_id(self) -> None:
        for value in ("", "   ", None, 7):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_decision(decision_id=value)

    def test_rejects_empty_or_malformed_timestamp(self) -> None:
        for value in ("", "   ", None, {}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_decision(created_at_utc=value)

    def test_rejects_malformed_bundle_input(self) -> None:
        for value in (None, {}, "bundle", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    self.make_decision(bundle=value)

    def test_rejects_unknown_decision_status(self) -> None:
        for value in ("APPROVE", "EXECUTE", "", None, 1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_decision(decision_status=value)

    def test_accepts_only_strict_inert_decision_statuses(self) -> None:
        self.assertEqual(
            (APPROVE_FOR_NEXT_REVIEW_STEP, REJECT, NEEDS_CHANGES),
            ALLOWED_DECISION_STATUSES,
        )
        for status in ALLOWED_DECISION_STATUSES:
            with self.subTest(status=status):
                self.assertEqual(status, self.make_decision(decision_status=status).decision_status)

    def test_binds_to_bundle_hash_and_id(self) -> None:
        bundle = self.make_bundle()

        decision = self.make_decision(bundle=bundle)

        self.assertEqual(bundle.bundle_id, decision.bundle_id)
        self.assertEqual(bundle.bundle_hash, decision.bundle_hash)

    def test_includes_required_boundary_language(self) -> None:
        decision = self.make_decision()

        self.assertIn("not an execution instruction", decision.boundary_text)
        self.assertIn("no authority granted", decision.boundary_text)

    def test_all_authority_and_capability_flags_are_false(self) -> None:
        decision = self.make_decision()

        self.assertFalse(decision.authority_granted)
        self.assertFalse(decision.execution_allowed)
        self.assertFalse(decision.dispatch_allowed)
        self.assertFalse(decision.provider_call_allowed)
        self.assertFalse(decision.artifact_write_allowed)
        self.assertFalse(decision.persistence_allowed)
        self.assertFalse(decision.decision_executes_anything)

    def test_approve_for_next_review_step_grants_no_capability(self) -> None:
        decision = self.make_decision(decision_status=APPROVE_FOR_NEXT_REVIEW_STEP)

        self.assertEqual(APPROVE_FOR_NEXT_REVIEW_STEP, decision.decision_status)
        self.assertFalse(any((
            decision.authority_granted,
            decision.execution_allowed,
            decision.dispatch_allowed,
            decision.provider_call_allowed,
            decision.artifact_write_allowed,
            decision.persistence_allowed,
            decision.decision_executes_anything,
        )))

    def test_optional_human_note_defaults_to_empty_inert_text(self) -> None:
        decision = create_human_review_decision(
            decision_id="decision-a",
            created_at_utc="2026-06-21T12:00:00Z",
            bundle=self.make_bundle(),
            decision_status=REJECT,
        )

        self.assertEqual("", decision.human_note)

    def test_stable_dict_serialization(self) -> None:
        decision = self.make_decision()

        self.assertEqual(decision.to_dict(), human_review_decision_to_dict(decision))
        self.assertEqual(decision.to_dict(), decision.to_dict())

    def test_dict_projection_rejects_unknown_input(self) -> None:
        for value in (None, {}, "decision", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    human_review_decision_to_dict(value)

    def test_rejects_tampered_bundle(self) -> None:
        bundle = self.make_bundle()
        object.__setattr__(bundle, "bundle_hash", "0" * 64)

        with self.assertRaises(ValueError):
            self.make_decision(bundle=bundle)

    def test_rejects_authority_bearing_bundle(self) -> None:
        bundle = self.make_bundle()
        object.__setattr__(bundle, "authority_granted", True)

        with self.assertRaises(ValueError):
            self.make_decision(bundle=bundle)

    def test_constructor_rejects_tampered_decision_hash(self) -> None:
        valid = self.make_decision()

        with self.assertRaises(ValueError):
            HumanReviewDecision(
                decision_id=valid.decision_id,
                created_at_utc=valid.created_at_utc,
                bundle_id=valid.bundle_id,
                bundle_hash=valid.bundle_hash,
                decision_status=valid.decision_status,
                human_note=valid.human_note,
                boundary_text=valid.boundary_text,
                decision_hash="0" * 64,
            )

    def test_malformed_input_never_becomes_authority_bearing_decision(self) -> None:
        for payload in (
            {"authority_granted": True},
            {"execution_allowed": True},
            {"dispatch_allowed": True},
            {"provider_call_allowed": True},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(TypeError):
                    HumanReviewDecision(**payload)

    def test_has_no_stdout_side_effects(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            self.make_decision()

        self.assertEqual("", output.getvalue())

    def test_static_boundary_has_no_forbidden_imports_or_calls(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "subprocess", "socket", "requests", "urllib", "httpx", "aiohttp",
            "sqlite3", "selenium", "playwright",
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
            self.assertFalse(any(
                module_name == item or module_name.startswith(item + ".")
                for item in forbidden_modules
            ))
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

    def make_bundle(self, *, snapshot_id: str = "snapshot-a") -> ReviewSessionBundle:
        snapshot = create_review_session_snapshot(
            snapshot_id=snapshot_id,
            created_at_utc="2026-06-21T10:00:00Z",
            source_milestone="AUTH-1G Operator Review Surface",
            source_head="2ebd2d0ab7af5c77dee36edee6c0a10a23f49968",
            review_surface_text="operator review",
            summary_fields={"reviewable": True, "status": "REVIEWABLE"},
        )
        return create_review_session_bundle(
            bundle_id="bundle-a",
            created_at_utc="2026-06-21T11:00:00Z",
            snapshots=[snapshot],
        )

    def make_decision(
        self,
        *,
        decision_id: object = "decision-a",
        created_at_utc: object = "2026-06-21T12:00:00Z",
        bundle: object = _DEFAULT_BUNDLE,
        decision_status: object = APPROVE_FOR_NEXT_REVIEW_STEP,
        human_note: object = "reviewed by human",
    ) -> HumanReviewDecision:
        return create_human_review_decision(
            decision_id=decision_id,
            created_at_utc=created_at_utc,
            bundle=self.make_bundle() if bundle is _DEFAULT_BUNDLE else bundle,
            decision_status=decision_status,
            human_note=human_note,
        )
