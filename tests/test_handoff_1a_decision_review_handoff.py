from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.decision_implication_review import (
    READY_FOR_IMPLICATION_REVIEW,
    build_decision_implication_review_packet,
)
from runtime.decision_review_handoff import (
    HANDOFF_BLOCKED,
    HANDOFF_INVALID,
    HANDOFF_READY,
    DecisionReviewHandoff,
    build_decision_review_handoff,
    decision_review_handoff_to_dict,
    render_decision_review_handoff,
)
from runtime.human_review_decision import (
    APPROVE_FOR_NEXT_REVIEW_STEP,
    create_human_review_decision,
)
from runtime.human_review_decision_projection import project_human_review_decision
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.validated_decision_readiness import build_validated_decision_readiness_map


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "decision_review_handoff.py"


class Handoff1ADecisionReviewHandoffTests(unittest.TestCase):
    def test_missing_input_returns_invalid(self) -> None:
        handoff = build_decision_review_handoff(None)

        self.assertEqual(HANDOFF_INVALID, handoff.state)
        self.assertEqual("", handoff.decision_id)
        self.assertNotEqual((), handoff.blockers)

    def test_malformed_input_returns_invalid(self) -> None:
        malformed = self.make_implication().to_dict()
        malformed.pop("decision_hash")

        handoff = build_decision_review_handoff(malformed)

        self.assertEqual(HANDOFF_INVALID, handoff.state)
        self.assertFalse(handoff.authority_granted)

    def test_noncanonical_input_returns_invalid(self) -> None:
        malformed = self.make_implication().to_dict()
        malformed["warnings"] = []

        handoff = build_decision_review_handoff(malformed)

        self.assertEqual(HANDOFF_INVALID, handoff.state)
        self.assertIn("canonical", handoff.blockers[0])

    def test_blocked_implication_input_returns_blocked(self) -> None:
        implication = build_decision_implication_review_packet(
            build_validated_decision_readiness_map(None)
        )

        handoff = build_decision_review_handoff(implication)

        self.assertEqual(HANDOFF_BLOCKED, handoff.state)
        self.assertEqual("", handoff.decision_id)

    def test_valid_implication_input_returns_handoff_ready(self) -> None:
        implication = self.make_implication()

        handoff = build_decision_review_handoff(implication)

        self.assertEqual(HANDOFF_READY, handoff.state)
        self.assertEqual(READY_FOR_IMPLICATION_REVIEW, handoff.source_implication_state)
        self.assertTrue(handoff.is_review_only)

    def test_canonical_dictionary_is_accepted(self) -> None:
        implication = self.make_implication()

        handoff = build_decision_review_handoff(implication.to_dict())

        self.assertEqual(HANDOFF_READY, handoff.state)
        self.assertEqual(implication.decision_hash, handoff.decision_hash)

    def test_existing_blockers_are_preserved(self) -> None:
        implication = build_decision_implication_review_packet(
            build_validated_decision_readiness_map(None)
        )

        handoff = build_decision_review_handoff(implication)

        self.assertEqual(implication.blockers, handoff.blockers)

    def test_existing_warnings_are_preserved(self) -> None:
        implication = self.make_implication()

        handoff = build_decision_review_handoff(implication)

        for warning in implication.warnings:
            self.assertIn(warning, handoff.warnings)

    def test_review_items_are_carried_forward_deterministically(self) -> None:
        implication = self.make_implication()

        first = build_decision_review_handoff(implication)
        second = build_decision_review_handoff(implication)

        self.assertEqual(implication.review_questions, first.review_next)
        self.assertEqual(first.review_next, second.review_next)

    def test_decision_and_bundle_identity_are_preserved(self) -> None:
        implication = self.make_implication()
        handoff = build_decision_review_handoff(implication)

        self.assertEqual(implication.decision_id, handoff.decision_id)
        self.assertEqual(implication.decision_hash, handoff.decision_hash)
        self.assertEqual(implication.decision_status, handoff.decision_status)
        self.assertEqual(implication.bundle_id, handoff.bundle_id)
        self.assertEqual(implication.bundle_hash, handoff.bundle_hash)

    def test_output_includes_explicit_boundary_warning(self) -> None:
        handoff = build_decision_review_handoff(self.make_implication())
        warnings = " ".join(handoff.warnings)

        self.assertIn(
            "not approval, permission, execution, dispatch, provider access, prompt generation, provider config, or secret handling",
            warnings,
        )
        self.assertIn("no authority granted", handoff.boundary_text)

    def test_no_authority_or_external_access_is_enabled(self) -> None:
        handoff = build_decision_review_handoff(self.make_implication())

        self.assertFalse(handoff.authority_granted)
        self.assertFalse(handoff.execution_allowed)
        self.assertFalse(handoff.dispatch_allowed)
        self.assertFalse(handoff.provider_call_allowed)
        self.assertFalse(handoff.artifact_write_allowed)
        self.assertFalse(handoff.persistence_allowed)
        self.assertFalse(handoff.prompt_packet_generated)
        self.assertFalse(handoff.provider_config_mutated)
        self.assertFalse(handoff.secret_accessed)
        self.assertFalse(handoff.api_key_accessed)
        self.assertFalse(handoff.handoff_executes_anything)

    def test_state_names_contain_no_dangerous_authority_language(self) -> None:
        dangerous = (
            "approved", "authorized", "allowed", "execute_ready", "dispatch_ready",
            "provider_ready", "permission_granted", "prompt_ready", "secret_ready",
            "api_key_ready",
        )
        for state in (HANDOFF_READY, HANDOFF_BLOCKED, HANDOFF_INVALID):
            with self.subTest(state=state):
                self.assertFalse(any(term in state for term in dangerous))

    def test_same_input_produces_same_output(self) -> None:
        implication = self.make_implication()

        first = build_decision_review_handoff(implication)
        second = build_decision_review_handoff(implication)

        self.assertEqual(first, second)

    def test_input_object_is_not_mutated(self) -> None:
        implication = self.make_implication()
        before = implication.to_dict()

        build_decision_review_handoff(implication)

        self.assertEqual(before, implication.to_dict())

    def test_input_dictionary_is_not_mutated(self) -> None:
        mapping = self.make_implication().to_dict()
        before = dict(mapping)

        build_decision_review_handoff(mapping)

        self.assertEqual(before, mapping)

    def test_handoff_is_immutable(self) -> None:
        handoff = build_decision_review_handoff(self.make_implication())

        with self.assertRaises(FrozenInstanceError):
            handoff.state = HANDOFF_BLOCKED
        self.assertIsInstance(handoff.review_next, tuple)

    def test_dict_serialization_is_stable(self) -> None:
        handoff = build_decision_review_handoff(self.make_implication())

        first = decision_review_handoff_to_dict(handoff)
        second = handoff.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["review_next"], second["review_next"])

    def test_render_is_stable_and_review_only(self) -> None:
        implication = self.make_implication()
        handoff = build_decision_review_handoff(implication)

        first = render_decision_review_handoff(handoff)
        second = render_decision_review_handoff(handoff)

        self.assertEqual(first, second)
        self.assertIn(implication.decision_id, first)
        self.assertIn("not an execution instruction", first)

    def test_helpers_reject_unknown_handoff_input(self) -> None:
        for value in (None, {}, "handoff", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    decision_review_handoff_to_dict(value)
                with self.assertRaises(ValueError):
                    render_decision_review_handoff(value)

    def test_fail_closed_constructor_forces_all_safety_flags_false(self) -> None:
        handoff = DecisionReviewHandoff(
            state=HANDOFF_INVALID,
            source_implication_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            implication_reasons=("unsafe",),
            blockers=("invalid source",),
            blocked_surfaces=(),
            review_next=(),
            warnings=(),
            boundary_text="unsafe",
            is_review_only=False,
            authority_granted=True,
            execution_allowed=True,
            dispatch_allowed=True,
            provider_call_allowed=True,
            artifact_write_allowed=True,
            persistence_allowed=True,
            prompt_packet_generated=True,
            provider_config_mutated=True,
            secret_accessed=True,
            api_key_accessed=True,
            handoff_executes_anything=True,
        )

        self.assertEqual("", handoff.decision_id)
        self.assertEqual((), handoff.implication_reasons)
        self.assertTrue(handoff.is_review_only)
        self.assertFalse(handoff.authority_granted)
        self.assertFalse(handoff.prompt_packet_generated)
        self.assertFalse(handoff.secret_accessed)

    def test_module_performs_no_io_or_capability_calls(self) -> None:
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
            self.assertNotIn("prompt", module_name)

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {"system", "write_text", "write_bytes", "write", "open"}:
            self.assertNotIn(attr, called_attrs)

    def test_module_has_no_provider_config_or_secret_access(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "os.environ", "getenv", "secret store", "provider_config.",
            "generate_prompt", "prompt_packet_builder",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_module_adds_no_storage_or_retrieval_architecture(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "hat store", "tetrad", "evidence memory", "canonical promotion",
            "fts5", "zstd", "knowledge pack",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def make_implication(self):
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
        decision = create_human_review_decision(
            decision_id="decision-a",
            created_at_utc="2026-06-21T12:00:00Z",
            bundle=bundle,
            decision_status=APPROVE_FOR_NEXT_REVIEW_STEP,
            human_note="reviewed by human",
        )
        projection = project_human_review_decision(decision)
        readiness = build_validated_decision_readiness_map(projection)
        return build_decision_implication_review_packet(readiness)
