from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.decision_implication_review import build_decision_implication_review_packet
from runtime.decision_review_handoff import (
    HANDOFF_BLOCKED,
    HANDOFF_INVALID,
    HANDOFF_READY,
    DecisionReviewHandoff,
    build_decision_review_handoff,
)
from runtime.human_review_decision import (
    APPROVE_FOR_NEXT_REVIEW_STEP,
    create_human_review_decision,
)
from runtime.human_review_decision_projection import project_human_review_decision
from runtime.prompt_packet_review import (
    PROMPT_PACKET_REVIEW_BLOCKED,
    PROMPT_PACKET_REVIEW_INVALID,
    PROMPT_PACKET_REVIEW_READY,
    PromptPacketReview,
    build_prompt_packet_review,
    prompt_packet_review_to_dict,
    render_prompt_packet_review,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.validated_decision_readiness import build_validated_decision_readiness_map


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "prompt_packet_review.py"


class PromptPackets1APromptPacketReviewTests(unittest.TestCase):
    def test_missing_input_returns_invalid(self) -> None:
        review = build_prompt_packet_review(None)

        self.assertEqual(PROMPT_PACKET_REVIEW_INVALID, review.state)
        self.assertEqual((), review.prompt_material)
        self.assertNotEqual((), review.blockers)

    def test_malformed_input_returns_invalid(self) -> None:
        malformed = self.make_handoff().to_dict()
        malformed.pop("decision_hash")

        review = build_prompt_packet_review(malformed)

        self.assertEqual(PROMPT_PACKET_REVIEW_INVALID, review.state)
        self.assertFalse(review.provider_request_created)

    def test_noncanonical_input_returns_invalid(self) -> None:
        malformed = self.make_handoff().to_dict()
        malformed["warnings"] = []

        review = build_prompt_packet_review(malformed)

        self.assertEqual(PROMPT_PACKET_REVIEW_INVALID, review.state)
        self.assertIn("canonical", review.blockers[0])

    def test_blocked_handoff_returns_blocked(self) -> None:
        blocked = self.make_failed_handoff(HANDOFF_BLOCKED)

        review = build_prompt_packet_review(blocked)

        self.assertEqual(PROMPT_PACKET_REVIEW_BLOCKED, review.state)
        self.assertEqual(blocked.blockers, review.blockers)

    def test_invalid_handoff_returns_invalid(self) -> None:
        invalid = self.make_failed_handoff(HANDOFF_INVALID)

        review = build_prompt_packet_review(invalid)

        self.assertEqual(PROMPT_PACKET_REVIEW_INVALID, review.state)
        self.assertEqual(invalid.blockers, review.blockers)

    def test_valid_handoff_returns_prompt_packet_review_ready(self) -> None:
        handoff = self.make_handoff()

        review = build_prompt_packet_review(handoff)

        self.assertEqual(PROMPT_PACKET_REVIEW_READY, review.state)
        self.assertEqual(HANDOFF_READY, review.source_handoff_state)
        self.assertTrue(review.is_review_only)

    def test_canonical_dictionary_is_accepted(self) -> None:
        handoff = self.make_handoff()

        review = build_prompt_packet_review(handoff.to_dict())

        self.assertEqual(PROMPT_PACKET_REVIEW_READY, review.state)
        self.assertEqual(handoff.decision_hash, review.decision_hash)

    def test_existing_blockers_are_preserved(self) -> None:
        blocked = self.make_failed_handoff(HANDOFF_BLOCKED)

        review = build_prompt_packet_review(blocked)

        self.assertEqual(blocked.blockers, review.blockers)

    def test_existing_warnings_are_preserved(self) -> None:
        handoff = self.make_handoff()

        review = build_prompt_packet_review(handoff)

        for warning in handoff.warnings:
            self.assertIn(warning, review.warnings)

    def test_review_context_and_constraints_are_deterministic(self) -> None:
        handoff = self.make_handoff()

        first = build_prompt_packet_review(handoff)
        second = build_prompt_packet_review(handoff)

        self.assertEqual(handoff.implication_reasons, first.review_context)
        self.assertEqual(handoff.review_next, first.review_next)
        self.assertEqual(first.constraints, second.constraints)

    def test_prompt_material_is_empty_bounded_and_immutable(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())

        self.assertEqual((), review.prompt_material)
        self.assertIsInstance(review.prompt_material, tuple)

    def test_oversized_source_context_fails_closed(self) -> None:
        handoff = self.make_handoff()
        object.__setattr__(handoff, "implication_reasons", ("x" * 513,))

        review = build_prompt_packet_review(handoff)

        self.assertEqual(PROMPT_PACKET_REVIEW_INVALID, review.state)
        self.assertEqual((), review.prompt_material)

    def test_output_includes_no_authority_warning(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())
        warnings = " ".join(review.warnings)

        self.assertIn("not a provider request", warnings)
        self.assertIn("not an execution instruction", review.boundary_text)
        self.assertIn("no authority granted", review.boundary_text)

    def test_output_includes_no_provider_secret_or_send_warning(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())
        warnings = " ".join(review.warnings)

        self.assertIn("not a provider request", warnings)
        self.assertIn("prompt sending", warnings)
        self.assertIn("secret or API key handling", warnings)
        self.assertIn("not a sendable prompt", review.boundary_text)

    def test_all_external_and_authority_flags_remain_false(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())

        self.assertFalse(review.authority_granted)
        self.assertFalse(review.execution_allowed)
        self.assertFalse(review.dispatch_allowed)
        self.assertFalse(review.provider_call_allowed)
        self.assertFalse(review.artifact_write_allowed)
        self.assertFalse(review.persistence_allowed)
        self.assertFalse(review.provider_request_created)
        self.assertFalse(review.prompt_sent)
        self.assertFalse(review.provider_config_accessed)
        self.assertFalse(review.secret_accessed)
        self.assertFalse(review.api_key_accessed)
        self.assertFalse(review.network_accessed)
        self.assertFalse(review.merge_authority_granted)
        self.assertFalse(review.review_executes_anything)

    def test_state_names_contain_no_dangerous_authority_language(self) -> None:
        dangerous = (
            "prompt_ready", "send_ready", "provider_ready", "execute_ready",
            "dispatch_ready", "approved", "authorized", "allowed",
            "permission_granted", "secret_ready", "api_key_ready", "merge_ready",
        )
        for state in (
            PROMPT_PACKET_REVIEW_READY,
            PROMPT_PACKET_REVIEW_BLOCKED,
            PROMPT_PACKET_REVIEW_INVALID,
        ):
            with self.subTest(state=state):
                self.assertFalse(any(term in state for term in dangerous))

    def test_same_input_produces_same_output(self) -> None:
        handoff = self.make_handoff()

        self.assertEqual(
            build_prompt_packet_review(handoff),
            build_prompt_packet_review(handoff),
        )

    def test_input_object_is_not_mutated(self) -> None:
        handoff = self.make_handoff()
        before = handoff.to_dict()

        build_prompt_packet_review(handoff)

        self.assertEqual(before, handoff.to_dict())

    def test_input_dictionary_is_not_mutated(self) -> None:
        mapping = self.make_handoff().to_dict()
        before = dict(mapping)

        build_prompt_packet_review(mapping)

        self.assertEqual(before, mapping)

    def test_review_is_immutable(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())

        with self.assertRaises(FrozenInstanceError):
            review.state = PROMPT_PACKET_REVIEW_BLOCKED
        self.assertIsInstance(review.constraints, tuple)

    def test_dict_serialization_is_stable(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())

        first = prompt_packet_review_to_dict(review)
        second = review.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["review_context"], second["review_context"])

    def test_render_is_stable_and_contains_no_send_boundary(self) -> None:
        review = build_prompt_packet_review(self.make_handoff())

        first = render_prompt_packet_review(review)
        second = render_prompt_packet_review(review)

        self.assertEqual(first, second)
        self.assertIn("prompt_material: empty", first)
        self.assertIn("not a sendable prompt", first)

    def test_helpers_reject_unknown_review_input(self) -> None:
        for value in (None, {}, "review", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    prompt_packet_review_to_dict(value)
                with self.assertRaises(ValueError):
                    render_prompt_packet_review(value)

    def test_fail_closed_constructor_forces_inert_state(self) -> None:
        review = PromptPacketReview(
            state=PROMPT_PACKET_REVIEW_INVALID,
            source_handoff_state="unsafe",
            source_implication_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            prompt_material=("send this",),
            blockers=("invalid source",),
            warnings=(),
            review_context=("unsafe",),
            review_next=(),
            constraints=(),
            boundary_text="unsafe",
            is_review_only=False,
            authority_granted=True,
            execution_allowed=True,
            dispatch_allowed=True,
            provider_call_allowed=True,
            artifact_write_allowed=True,
            persistence_allowed=True,
            provider_request_created=True,
            prompt_sent=True,
            provider_config_accessed=True,
            secret_accessed=True,
            api_key_accessed=True,
            network_accessed=True,
            merge_authority_granted=True,
            review_executes_anything=True,
        )

        self.assertEqual((), review.prompt_material)
        self.assertEqual("", review.decision_id)
        self.assertFalse(review.authority_granted)
        self.assertFalse(review.prompt_sent)
        self.assertFalse(review.secret_accessed)

    def test_module_performs_no_io_network_or_capability_calls(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "subprocess", "socket", "requests", "urllib", "httpx", "aiohttp",
            "sqlite3", "selenium", "playwright", "openai", "anthropic",
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
            self.assertNotIn("provider_config", module_name)

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {
            "system", "write_text", "write_bytes", "write", "open", "send",
            "post", "get", "request", "execute", "dispatch",
        }:
            self.assertNotIn(attr, called_attrs)

    def test_module_has_no_config_secret_or_prompt_generation_access(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "os.environ", "getenv", "load_dotenv", "provider_config.",
            "generate_prompt", "send_prompt", "api.openai", "api.anthropic",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_module_adds_no_ui_storage_or_retrieval_architecture(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "hat store", "tetrad", "evidence memory", "canonical promotion",
            "fts5", "zstd", "knowledge pack", "fastapi", "flask", "click.command",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def make_failed_handoff(self, state: str) -> DecisionReviewHandoff:
        return DecisionReviewHandoff(
            state=state,
            source_implication_state="",
            decision_id="",
            decision_hash="",
            decision_status="",
            bundle_id="",
            bundle_hash="",
            implication_reasons=(),
            blockers=("source review blocked",),
            blocked_surfaces=(),
            review_next=("Review the source blocker.",),
            warnings=("Source remains review-only.",),
            boundary_text="",
        )

    def make_handoff(self) -> DecisionReviewHandoff:
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
        implication = build_decision_implication_review_packet(readiness)
        return build_decision_review_handoff(implication)
