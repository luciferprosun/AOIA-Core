from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.decision_implication_review import (
    IMPLICATION_REVIEW_BLOCKED,
    IMPLICATION_REVIEW_INVALID,
    READY_FOR_IMPLICATION_REVIEW,
    DecisionImplicationReviewPacket,
    build_decision_implication_review_packet,
    decision_implication_review_packet_to_dict,
    render_decision_implication_review_packet,
)
from runtime.human_review_decision import (
    APPROVE_FOR_NEXT_REVIEW_STEP,
    create_human_review_decision,
)
from runtime.human_review_decision_projection import project_human_review_decision
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.validated_decision_readiness import (
    BLOCKED_SURFACES,
    build_validated_decision_readiness_map,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "decision_implication_review.py"


class Implications1ADecisionImplicationReviewTests(unittest.TestCase):
    def test_missing_readiness_returns_invalid(self) -> None:
        packet = build_decision_implication_review_packet(None)

        self.assertEqual(IMPLICATION_REVIEW_INVALID, packet.status)
        self.assertEqual("", packet.decision_id)
        self.assertNotEqual((), packet.blockers)

    def test_malformed_readiness_mapping_fails_closed(self) -> None:
        malformed = self.make_readiness().to_dict()
        malformed.pop("decision_hash")

        packet = build_decision_implication_review_packet(malformed)

        self.assertEqual(IMPLICATION_REVIEW_INVALID, packet.status)
        self.assertFalse(packet.authority_granted)

    def test_noncanonical_readiness_mapping_fails_closed(self) -> None:
        malformed = self.make_readiness().to_dict()
        malformed["blocked_surfaces"] = []

        packet = build_decision_implication_review_packet(malformed)

        self.assertEqual(IMPLICATION_REVIEW_INVALID, packet.status)
        self.assertIn("canonical", packet.blockers[0])

    def test_readiness_not_ready_for_review_is_blocked(self) -> None:
        failed_readiness = build_validated_decision_readiness_map(None)

        packet = build_decision_implication_review_packet(failed_readiness)

        self.assertEqual(IMPLICATION_REVIEW_BLOCKED, packet.status)
        self.assertEqual("", packet.decision_id)

    def test_valid_readiness_returns_ready_for_implication_review(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())

        self.assertEqual(READY_FOR_IMPLICATION_REVIEW, packet.status)
        self.assertTrue(packet.is_review_only)
        self.assertEqual("ready_for_review_continuation", packet.source_readiness_state)

    def test_canonical_readiness_dictionary_is_accepted(self) -> None:
        readiness = self.make_readiness()

        packet = build_decision_implication_review_packet(readiness.to_dict())

        self.assertEqual(READY_FOR_IMPLICATION_REVIEW, packet.status)
        self.assertEqual(readiness.decision_hash, packet.decision_hash)

    def test_existing_blocked_surfaces_are_preserved(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())

        self.assertEqual(BLOCKED_SURFACES, packet.blocked_surfaces)

    def test_failure_reasons_are_preserved_as_blockers(self) -> None:
        readiness = build_validated_decision_readiness_map(None)

        packet = build_decision_implication_review_packet(readiness)

        self.assertEqual(readiness.validation_failure_reasons, packet.blockers)

    def test_eligibility_reasons_are_deterministic(self) -> None:
        readiness = self.make_readiness()

        first = build_decision_implication_review_packet(readiness)
        second = build_decision_implication_review_packet(readiness)

        self.assertEqual(first, second)
        self.assertEqual(first.eligibility_reasons, second.eligibility_reasons)

    def test_packet_contains_human_review_questions(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())

        self.assertGreaterEqual(len(packet.review_questions), 4)
        self.assertTrue(all(question.endswith("?") for question in packet.review_questions))

    def test_boundary_warning_rejects_authority_meaning(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())
        warning_text = " ".join(packet.warnings)

        self.assertIn("not approval, permission, or execution readiness", warning_text)
        self.assertIn("grants no provider, dispatch", warning_text)
        self.assertIn("no authority granted", packet.boundary_text)

    def test_all_authority_fields_remain_false(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())

        self.assertFalse(packet.authority_granted)
        self.assertFalse(packet.execution_allowed)
        self.assertFalse(packet.dispatch_allowed)
        self.assertFalse(packet.provider_call_allowed)
        self.assertFalse(packet.artifact_write_allowed)
        self.assertFalse(packet.persistence_allowed)
        self.assertFalse(packet.packet_executes_anything)

    def test_status_names_contain_no_dangerous_authority_language(self) -> None:
        dangerous = (
            "approved", "authorized", "allowed", "execute_ready",
            "dispatch_ready", "provider_ready", "permission_granted",
        )

        for status in (
            READY_FOR_IMPLICATION_REVIEW,
            IMPLICATION_REVIEW_BLOCKED,
            IMPLICATION_REVIEW_INVALID,
        ):
            with self.subTest(status=status):
                self.assertFalse(any(term in status for term in dangerous))

    def test_source_readiness_is_not_mutated(self) -> None:
        readiness = self.make_readiness()
        before = readiness.to_dict()

        build_decision_implication_review_packet(readiness)

        self.assertEqual(before, readiness.to_dict())

    def test_source_mapping_is_not_mutated(self) -> None:
        mapping = self.make_readiness().to_dict()
        before = dict(mapping)

        build_decision_implication_review_packet(mapping)

        self.assertEqual(before, mapping)

    def test_packet_is_immutable(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())

        with self.assertRaises(FrozenInstanceError):
            packet.status = IMPLICATION_REVIEW_BLOCKED
        self.assertIsInstance(packet.review_questions, tuple)

    def test_dict_serialization_is_stable(self) -> None:
        packet = build_decision_implication_review_packet(self.make_readiness())

        first = decision_implication_review_packet_to_dict(packet)
        second = packet.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["review_questions"], second["review_questions"])

    def test_render_is_stable_and_contains_identity(self) -> None:
        readiness = self.make_readiness()
        packet = build_decision_implication_review_packet(readiness)

        first = render_decision_implication_review_packet(packet)
        second = render_decision_implication_review_packet(packet)

        self.assertEqual(first, second)
        self.assertIn(readiness.decision_id, first)
        self.assertIn(readiness.decision_hash, first)
        self.assertIn("not an execution instruction", first)

    def test_helpers_reject_unknown_packet_input(self) -> None:
        for value in (None, {}, "packet", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    decision_implication_review_packet_to_dict(value)
                with self.assertRaises(ValueError):
                    render_decision_implication_review_packet(value)

    def test_fail_closed_constructor_forces_inert_state(self) -> None:
        packet = DecisionImplicationReviewPacket(
            status=IMPLICATION_REVIEW_INVALID,
            source_readiness_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            eligibility_reasons=("unsafe",),
            blockers=("invalid source",),
            blocked_surfaces=(),
            review_questions=(),
            warnings=(),
            boundary_text="unsafe",
            is_review_only=False,
            authority_granted=True,
            execution_allowed=True,
            dispatch_allowed=True,
            provider_call_allowed=True,
            artifact_write_allowed=True,
            persistence_allowed=True,
            packet_executes_anything=True,
        )

        self.assertEqual("", packet.decision_id)
        self.assertEqual((), packet.eligibility_reasons)
        self.assertTrue(packet.is_review_only)
        self.assertFalse(packet.authority_granted)
        self.assertFalse(packet.packet_executes_anything)

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

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {"system", "write_text", "write_bytes", "write", "open"}:
            self.assertNotIn(attr, called_attrs)

    def test_module_adds_no_storage_or_retrieval_architecture(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "hat store", "tetrad", "evidence memory", "canonical promotion",
            "fts5", "zstd", "knowledge pack",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def make_readiness(self):
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
        return build_validated_decision_readiness_map(projection)
