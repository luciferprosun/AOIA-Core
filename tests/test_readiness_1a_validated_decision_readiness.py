from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.human_review_decision import (
    APPROVE_FOR_NEXT_REVIEW_STEP,
    create_human_review_decision,
)
from runtime.human_review_decision_projection import (
    HumanReviewDecisionProjection,
    project_human_review_decision,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.validated_decision_readiness import (
    BLOCKED_SURFACES,
    FORBIDDEN_TRANSITIONS,
    REQUIRED_BOUNDARIES,
    ValidatedDecisionReadinessMap,
    build_validated_decision_readiness_map,
    render_validated_decision_readiness_map,
    validated_decision_readiness_map_to_dict,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "validated_decision_readiness.py"


class Readiness1AValidatedDecisionReadinessTests(unittest.TestCase):
    def test_valid_projection_builds_readiness_map(self) -> None:
        projection = self.make_projection()

        readiness = build_validated_decision_readiness_map(projection)

        self.assertTrue(readiness.source_projection_is_validated)
        self.assertTrue(readiness.is_ready_for_review_continuation)
        self.assertTrue(readiness.is_review_only)

    def test_unvalidated_projection_fails_closed(self) -> None:
        projection = self.make_projection()
        object.__setattr__(projection, "is_validated", False)

        readiness = build_validated_decision_readiness_map(projection)

        self.assertFalse(readiness.source_projection_is_validated)
        self.assertFalse(readiness.is_ready_for_review_continuation)
        self.assertEqual("", readiness.decision_id)

    def test_projection_validation_is_required(self) -> None:
        decision = self.make_decision()

        readiness = build_validated_decision_readiness_map(decision)

        self.assertFalse(readiness.source_projection_is_validated)
        self.assertIn("projection", readiness.validation_failure_reasons[0])

    def test_projection_reporting_failure_fails_closed_and_preserves_reason(self) -> None:
        decision = self.make_decision()
        object.__setattr__(decision, "authority_granted", True)
        projection = project_human_review_decision(decision)

        readiness = build_validated_decision_readiness_map(projection)

        self.assertFalse(readiness.source_projection_is_validated)
        self.assertEqual(
            projection.validation_failure_reasons,
            readiness.validation_failure_reasons,
        )

    def test_inconsistent_projection_preserves_its_failure_reason(self) -> None:
        projection = self.make_projection()
        object.__setattr__(projection, "validation_failure_reasons", ("reported failure",))

        readiness = build_validated_decision_readiness_map(projection)

        self.assertFalse(readiness.source_projection_is_validated)
        self.assertEqual(("reported failure",), readiness.validation_failure_reasons)

    def test_output_is_deterministic_for_same_input(self) -> None:
        projection = self.make_projection()

        first = build_validated_decision_readiness_map(projection)
        second = build_validated_decision_readiness_map(projection)

        self.assertEqual(first, second)

    def test_dict_serialization_is_stable(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        first = validated_decision_readiness_map_to_dict(readiness)
        second = readiness.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["blocked_surfaces"], second["blocked_surfaces"])

    def test_render_output_is_stable(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertEqual(
            render_validated_decision_readiness_map(readiness),
            render_validated_decision_readiness_map(readiness),
        )

    def test_render_includes_boundary_language(self) -> None:
        rendered = render_validated_decision_readiness_map(
            build_validated_decision_readiness_map(self.make_projection())
        )

        self.assertIn("not an execution instruction", rendered)
        self.assertIn("no authority granted", rendered)

    def test_render_includes_decision_and_bundle_identity(self) -> None:
        projection = self.make_projection()
        rendered = render_validated_decision_readiness_map(
            build_validated_decision_readiness_map(projection)
        )

        for value in (
            projection.decision_id,
            projection.decision_hash,
            projection.decision_status,
            projection.bundle_id,
            projection.bundle_hash,
        ):
            with self.subTest(value=value):
                self.assertIn(value, rendered)

    def test_map_is_review_only(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertTrue(readiness.is_review_only)
        self.assertIn("review continuation only", readiness.readiness_summary)

    def test_runtime_surfaces_are_not_ready(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertFalse(readiness.execution_allowed)
        self.assertFalse(readiness.provider_call_allowed)
        self.assertFalse(readiness.artifact_write_allowed)
        self.assertFalse(readiness.persistence_allowed)

    def test_blocked_surfaces_cover_every_required_boundary(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertEqual(BLOCKED_SURFACES, readiness.blocked_surfaces)
        for label in (
            "execution blocked",
            "provider calls blocked",
            "persistence blocked",
            "artifact writes blocked",
            "dispatcher/router blocked",
            "shell/browser/network blocked",
            "approval gate modification blocked",
        ):
            with self.subTest(label=label):
                self.assertIn(label, readiness.blocked_surfaces)

    def test_required_boundaries_cover_future_review_constraints(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertEqual(REQUIRED_BOUNDARIES, readiness.required_boundaries)
        self.assertIn("human review required", readiness.required_boundaries)
        self.assertIn("validation required", readiness.required_boundaries)
        self.assertIn("projection required", readiness.required_boundaries)
        self.assertIn(
            "audit review required before any future controlled handoff",
            readiness.required_boundaries,
        )

    def test_forbidden_transitions_prevent_semantic_escalation(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertEqual(FORBIDDEN_TRANSITIONS, readiness.forbidden_transitions)
        self.assertIn(
            "validated decision must not become permission",
            readiness.forbidden_transitions,
        )
        self.assertIn(
            "readiness map must not become instruction",
            readiness.forbidden_transitions,
        )
        self.assertIn(
            "review information must not become execution authority",
            readiness.forbidden_transitions,
        )

    def test_all_authority_fields_remain_false(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        self.assertFalse(readiness.authority_granted)
        self.assertFalse(readiness.execution_allowed)
        self.assertFalse(readiness.dispatch_allowed)
        self.assertFalse(readiness.provider_call_allowed)
        self.assertFalse(readiness.artifact_write_allowed)
        self.assertFalse(readiness.persistence_allowed)
        self.assertFalse(readiness.readiness_map_executes_anything)

    def test_readiness_map_is_immutable(self) -> None:
        readiness = build_validated_decision_readiness_map(self.make_projection())

        with self.assertRaises(FrozenInstanceError):
            readiness.is_review_only = False
        self.assertIsInstance(readiness.blocked_surfaces, tuple)
        self.assertIsInstance(readiness.required_boundaries, tuple)

    def test_source_projection_is_not_mutated(self) -> None:
        projection = self.make_projection()
        before = projection.to_dict()

        build_validated_decision_readiness_map(projection)

        self.assertEqual(before, projection.to_dict())

    def test_malformed_input_fails_closed(self) -> None:
        for value in (None, {}, "projection", object()):
            with self.subTest(value=type(value).__name__):
                readiness = build_validated_decision_readiness_map(value)
                self.assertFalse(readiness.source_projection_is_validated)
                self.assertFalse(readiness.is_ready_for_review_continuation)

    def test_failed_readiness_reason_is_deterministic_and_rendered(self) -> None:
        first = build_validated_decision_readiness_map(None)
        second = build_validated_decision_readiness_map(None)

        self.assertEqual(first.validation_failure_reasons, second.validation_failure_reasons)
        self.assertIn(
            first.validation_failure_reasons[0],
            render_validated_decision_readiness_map(first),
        )

    def test_helpers_reject_unknown_readiness_input(self) -> None:
        for value in (None, {}, "readiness", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    validated_decision_readiness_map_to_dict(value)
                with self.assertRaises(ValueError):
                    render_validated_decision_readiness_map(value)

    def test_constructor_forces_fail_closed_static_state(self) -> None:
        readiness = ValidatedDecisionReadinessMap(
            is_ready_for_review_continuation=True,
            is_review_only=False,
            source_projection_is_validated=False,
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            validated_surfaces=("unsafe",),
            blocked_surfaces=(),
            required_boundaries=(),
            forbidden_transitions=(),
            readiness_summary="unsafe",
            boundary_text="unsafe",
            validation_failure_reasons=("rejected",),
            authority_granted=True,
            execution_allowed=True,
            dispatch_allowed=True,
            provider_call_allowed=True,
            artifact_write_allowed=True,
            persistence_allowed=True,
            readiness_map_executes_anything=True,
        )

        self.assertFalse(readiness.is_ready_for_review_continuation)
        self.assertTrue(readiness.is_review_only)
        self.assertEqual("", readiness.decision_id)
        self.assertEqual((), readiness.validated_surfaces)
        self.assertFalse(readiness.authority_granted)

    def test_public_names_respect_language_boundary(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        banned_terms = (
            "Dispatcher", "Instruction", "Execution", "Action", "Capability",
            "Intent", "Plan", "Queue", "Route", "Router", "Task", "Step",
            "Provider", "Permission", "Executor", "Runner", "Workflow",
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

    def test_module_has_no_io_or_capability_imports_or_calls(self) -> None:
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

    def test_module_has_no_forbidden_deferred_semantics(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in ("lineage", "intent", "queue", "state machine", "capability catalog"):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def make_projection(self) -> HumanReviewDecisionProjection:
        return project_human_review_decision(self.make_decision())

    def make_decision(self):
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
