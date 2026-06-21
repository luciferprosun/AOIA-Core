from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from runtime.human_review_decision import (
    APPROVE_FOR_NEXT_REVIEW_STEP,
    HumanReviewDecision,
    create_human_review_decision,
)
from runtime.human_review_decision_projection import (
    HumanReviewDecisionProjection,
    human_review_decision_projection_to_dict,
    project_human_review_decision,
    render_human_review_decision_projection,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "human_review_decision_projection.py"


class Decision1CHumanReviewDecisionProjectionTests(unittest.TestCase):
    def test_valid_decision_projects_after_validation(self) -> None:
        projection = project_human_review_decision(self.make_decision())

        self.assertTrue(projection.is_projected)
        self.assertTrue(projection.is_validated)
        self.assertEqual((), projection.validation_failure_reasons)

    def test_invalid_decision_fails_closed_without_normal_projection(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "authority_granted", True)

        projection = project_human_review_decision(decision)

        self.assertFalse(projection.is_projected)
        self.assertFalse(projection.is_validated)
        self.assertEqual("", projection.decision_id)
        self.assertNotEqual((), projection.validation_failure_reasons)

    def test_validator_is_a_required_precondition(self) -> None:
        with patch(
            "runtime.human_review_decision_projection.validate_human_review_decision",
            side_effect=ValueError("validator rejected decision"),
        ) as validator:
            projection = project_human_review_decision(self.make_decision())

        validator.assert_called_once()
        self.assertFalse(projection.is_projected)
        self.assertEqual(("validator rejected decision",), projection.validation_failure_reasons)

    def test_projection_is_deterministic_for_same_input(self) -> None:
        decision = self.make_decision()

        first = project_human_review_decision(decision)
        second = project_human_review_decision(decision)

        self.assertEqual(first, second)

    def test_projection_dict_serialization_is_stable(self) -> None:
        projection = project_human_review_decision(self.make_decision())

        first = human_review_decision_projection_to_dict(projection)
        second = projection.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["validation_failure_reasons"], second["validation_failure_reasons"])

    def test_render_output_is_stable(self) -> None:
        projection = project_human_review_decision(self.make_decision())

        self.assertEqual(
            render_human_review_decision_projection(projection),
            render_human_review_decision_projection(projection),
        )

    def test_render_includes_required_boundary_phrases(self) -> None:
        rendered = render_human_review_decision_projection(
            project_human_review_decision(self.make_decision())
        )

        self.assertIn("not an execution instruction", rendered)
        self.assertIn("no authority granted", rendered)

    def test_render_includes_decision_and_bundle_identity(self) -> None:
        decision = self.make_decision()
        rendered = render_human_review_decision_projection(
            project_human_review_decision(decision)
        )

        for value in (
            decision.decision_id,
            decision.decision_hash,
            decision.decision_status,
            decision.bundle_id,
            decision.bundle_hash,
        ):
            with self.subTest(value=value):
                self.assertIn(value, rendered)

    def test_approve_status_is_rendered_as_review_only(self) -> None:
        rendered = render_human_review_decision_projection(
            project_human_review_decision(self.make_decision())
        )

        self.assertIn(APPROVE_FOR_NEXT_REVIEW_STEP, rendered)
        self.assertIn("Review information only", rendered)
        self.assertIn("does not execute, dispatch, persist, call providers, or write artifacts", rendered)
        self.assertIn("grants no runtime authority", rendered)

    def test_all_authority_and_capability_flags_remain_false(self) -> None:
        projection = project_human_review_decision(self.make_decision())

        self.assertFalse(projection.authority_granted)
        self.assertFalse(projection.execution_allowed)
        self.assertFalse(projection.dispatch_allowed)
        self.assertFalse(projection.provider_call_allowed)
        self.assertFalse(projection.artifact_write_allowed)
        self.assertFalse(projection.persistence_allowed)
        self.assertFalse(projection.projection_executes_anything)

    def test_projection_object_is_immutable(self) -> None:
        projection = project_human_review_decision(self.make_decision())

        with self.assertRaises(FrozenInstanceError):
            projection.decision_status = "REJECT"

    def test_source_decision_is_not_mutated(self) -> None:
        decision = self.make_decision()
        before = decision.to_dict()

        project_human_review_decision(decision)

        self.assertEqual(before, decision.to_dict())

    def test_malformed_decision_input_fails_closed(self) -> None:
        for value in (None, {}, "decision", object()):
            with self.subTest(value=type(value).__name__):
                projection = project_human_review_decision(value)
                self.assertFalse(projection.is_projected)
                self.assertFalse(projection.is_validated)

    def test_validation_failure_reasons_are_preserved_and_rendered(self) -> None:
        with patch(
            "runtime.human_review_decision_projection.validate_human_review_decision",
            side_effect=ValueError("inert validation failure"),
        ):
            projection = project_human_review_decision(self.make_decision())

        self.assertEqual(("inert validation failure",), projection.validation_failure_reasons)
        self.assertIn(
            "inert validation failure",
            render_human_review_decision_projection(projection),
        )

    def test_projection_and_render_helpers_reject_unknown_projection_input(self) -> None:
        for value in (None, {}, "projection", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    human_review_decision_projection_to_dict(value)
                with self.assertRaises(ValueError):
                    render_human_review_decision_projection(value)

    def test_failed_projection_forces_all_safety_flags_false(self) -> None:
        projection = HumanReviewDecisionProjection(
            is_projected=False,
            is_validated=False,
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            operator_summary="unsafe",
            boundary_text="unsafe",
            validation_failure_reasons=("rejected",),
            authority_granted=True,
            execution_allowed=True,
            dispatch_allowed=True,
            provider_call_allowed=True,
            artifact_write_allowed=True,
            persistence_allowed=True,
            projection_executes_anything=True,
        )

        self.assertEqual("", projection.decision_id)
        self.assertFalse(any((
            projection.authority_granted,
            projection.execution_allowed,
            projection.dispatch_allowed,
            projection.provider_call_allowed,
            projection.artifact_write_allowed,
            projection.persistence_allowed,
            projection.projection_executes_anything,
        )))

    def test_public_names_respect_language_boundary(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        banned_terms = (
            "Dispatcher", "Instruction", "Execution", "Action", "Capability",
            "Intent", "Plan", "Queue", "Route", "Router", "Task", "Step",
            "Provider", "Permission",
        )
        public_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and not node.name.startswith("_")
        ]

        for name in public_names:
            with self.subTest(name=name):
                self.assertFalse(any(term.casefold() in name.casefold() for term in banned_terms))

    def test_module_has_no_forbidden_imports_or_calls(self) -> None:
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
            self.assertNotIn("artifact", module_name)

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {"system", "write_text", "write_bytes", "write", "open"}:
            self.assertNotIn(attr, called_attrs)

    def test_module_has_no_deferred_semantics(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in ("lineage", "intent", "queue", "state machine", "capability catalog"):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def make_decision(self) -> HumanReviewDecision:
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
            decision_status=APPROVE_FOR_NEXT_REVIEW_STEP,
            human_note="reviewed by human",
        )
