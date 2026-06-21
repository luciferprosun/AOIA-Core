from __future__ import annotations

import ast
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from runtime.human_review_decision import (
    ALLOWED_DECISION_STATUSES,
    APPROVE_FOR_NEXT_REVIEW_STEP,
    HumanReviewDecision,
    create_human_review_decision,
)
from runtime.human_review_decision_validator import (
    FORBIDDEN_DECISION_LANGUAGE,
    validate_decision_language,
    validate_human_review_decision,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "human_review_decision_validator.py"


class Decision1BHumanReviewDecisionValidatorTests(unittest.TestCase):
    def test_accepts_valid_inert_decision(self) -> None:
        decision = self.make_decision()

        self.assertIsNone(validate_human_review_decision(decision))

    def test_validation_is_deterministic_and_does_not_mutate_decision(self) -> None:
        decision = self.make_decision()
        before = decision.to_dict()

        self.assertIsNone(validate_human_review_decision(decision))
        self.assertIsNone(validate_human_review_decision(decision))

        self.assertEqual(before, decision.to_dict())

    def test_accepts_all_strict_inert_decision_statuses(self) -> None:
        for status in ALLOWED_DECISION_STATUSES:
            with self.subTest(status=status):
                self.assertIsNone(validate_human_review_decision(self.make_decision(status=status)))

    def test_approve_for_next_review_step_remains_inert(self) -> None:
        decision = self.make_decision(status=APPROVE_FOR_NEXT_REVIEW_STEP)

        self.assertIsNone(validate_human_review_decision(decision))
        self.assertFalse(decision.authority_granted)
        self.assertFalse(decision.execution_allowed)
        self.assertFalse(decision.decision_executes_anything)

    def test_rejects_malformed_decision_input(self) -> None:
        for value in (None, {}, "decision", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    validate_human_review_decision(value)

    def test_rejects_authority_or_capability_bearing_decision(self) -> None:
        for flag_name in (
            "authority_granted",
            "execution_allowed",
            "dispatch_allowed",
            "provider_call_allowed",
            "artifact_write_allowed",
            "persistence_allowed",
            "decision_executes_anything",
        ):
            decision = self.make_decision()
            object.__setattr__(decision, flag_name, True)
            with self.subTest(flag_name=flag_name):
                with self.assertRaises(ValueError):
                    validate_human_review_decision(decision)

    def test_rejects_tampered_decision_hash(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "decision_hash", "0" * 64)

        with self.assertRaises(ValueError):
            validate_human_review_decision(decision)

    def test_rejects_tampered_decision_identity(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "decision_id", "changed-decision")

        with self.assertRaises(ValueError):
            validate_human_review_decision(decision)

    def test_rejects_tampered_bundle_binding(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "bundle_hash", "0" * 64)

        with self.assertRaises(ValueError):
            validate_human_review_decision(decision)

    def test_rejects_tampered_boundary_text(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "boundary_text", "authority granted")

        with self.assertRaises(ValueError):
            validate_human_review_decision(decision)

    def test_required_boundary_language_is_preserved(self) -> None:
        decision = self.make_decision()

        validate_human_review_decision(decision)

        self.assertIn("not an execution instruction", decision.boundary_text)
        self.assertIn("no authority granted", decision.boundary_text)

    def test_language_guard_accepts_inert_review_language(self) -> None:
        for note in (
            "",
            "reviewed by human",
            "needs design clarification",
            "may proceed to the next review step",
        ):
            with self.subTest(note=note):
                self.assertIsNone(validate_decision_language(note))

    def test_language_guard_rejects_every_forbidden_phrase(self) -> None:
        for phrase in FORBIDDEN_DECISION_LANGUAGE:
            with self.subTest(phrase=phrase):
                with self.assertRaises(ValueError):
                    validate_decision_language(f"Human says: {phrase}.")

    def test_language_guard_is_case_and_whitespace_insensitive(self) -> None:
        with self.assertRaises(ValueError):
            validate_decision_language("EXECUTE   THIS immediately")

    def test_language_guard_rejects_non_string_input(self) -> None:
        for value in (None, {}, 1, []):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    validate_decision_language(value)

    def test_decision_with_forbidden_human_note_is_rejected(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "human_note", "execute this immediately")

        with self.assertRaises(ValueError):
            validate_human_review_decision(decision)

    def test_validator_creates_no_projection_lineage_intent_or_plan(self) -> None:
        result = validate_human_review_decision(self.make_decision())

        self.assertIsNone(result)
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()
        self.assertNotIn("projection", source)
        self.assertNotIn("lineage", source)
        self.assertNotIn("intent", source)
        self.assertNotIn("plan", source)

    def test_has_no_stdout_side_effects(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            validate_human_review_decision(self.make_decision())

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

    def make_decision(
        self,
        *,
        status: str = APPROVE_FOR_NEXT_REVIEW_STEP,
    ) -> HumanReviewDecision:
        snapshot = create_review_session_snapshot(
            snapshot_id="snapshot-a",
            created_at_utc="2026-06-21T10:00:00Z",
            source_milestone="AUTH-1G Operator Review Surface",
            source_head="2ebd2d0ab7af5c77dee36edee6c0a10a23f49968",
            review_surface_text="operator review",
            summary_fields={"reviewable": True, "status": "REVIEWABLE"},
        )
        bundle = create_review_session_bundle(
            bundle_id="bundle-a",
            created_at_utc="2026-06-21T11:00:00Z",
            snapshots=[snapshot],
        )
        return create_human_review_decision(
            decision_id="decision-a",
            created_at_utc="2026-06-21T12:00:00Z",
            bundle=bundle,
            decision_status=status,
            human_note="reviewed by human",
        )
