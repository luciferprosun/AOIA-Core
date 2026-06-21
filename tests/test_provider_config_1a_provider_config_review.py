from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.decision_implication_review import build_decision_implication_review_packet
from runtime.decision_review_handoff import build_decision_review_handoff
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
)
from runtime.provider_config_review import (
    PROVIDER_CONFIG_REVIEW_BLOCKED,
    PROVIDER_CONFIG_REVIEW_INVALID,
    PROVIDER_CONFIG_REVIEW_READY,
    PROVIDER_POLICY_MATERIAL,
    ProviderConfigReview,
    build_provider_config_review,
    provider_config_review_to_dict,
    render_provider_config_review,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.validated_decision_readiness import build_validated_decision_readiness_map


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "provider_config_review.py"


class ProviderConfig1AProviderConfigReviewTests(unittest.TestCase):
    def test_missing_input_returns_invalid(self) -> None:
        review = build_provider_config_review(None)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertNotEqual((), review.blockers)

    def test_malformed_input_returns_invalid(self) -> None:
        malformed = self.make_prompt_review().to_dict()
        malformed.pop("decision_hash")

        review = build_provider_config_review(malformed)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertFalse(review.real_provider_config_created)

    def test_noncanonical_input_returns_invalid(self) -> None:
        malformed = self.make_prompt_review().to_dict()
        malformed["provider_config_accessed"] = True

        review = build_provider_config_review(malformed)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertIn("canonical", review.blockers[0])

    def test_blocked_prompt_review_returns_blocked(self) -> None:
        source = self.make_failed_prompt_review(PROMPT_PACKET_REVIEW_BLOCKED)

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_BLOCKED, review.state)
        self.assertEqual(source.blockers, review.blockers)

    def test_invalid_prompt_review_returns_invalid(self) -> None:
        source = self.make_failed_prompt_review(PROMPT_PACKET_REVIEW_INVALID)

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertEqual(source.blockers, review.blockers)

    def test_valid_prompt_review_returns_provider_config_review_ready(self) -> None:
        source = self.make_prompt_review()

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_READY, review.state)
        self.assertEqual(PROMPT_PACKET_REVIEW_READY, review.source_prompt_packet_state)
        self.assertTrue(review.is_review_only)

    def test_canonical_dictionary_is_accepted(self) -> None:
        source = self.make_prompt_review()

        review = build_provider_config_review(source.to_dict())

        self.assertEqual(PROVIDER_CONFIG_REVIEW_READY, review.state)
        self.assertEqual(source.decision_hash, review.decision_hash)

    def test_existing_blockers_are_preserved(self) -> None:
        source = self.make_failed_prompt_review(PROMPT_PACKET_REVIEW_BLOCKED)

        review = build_provider_config_review(source)

        self.assertEqual(source.blockers, review.blockers)

    def test_existing_warnings_are_preserved(self) -> None:
        source = self.make_prompt_review()

        review = build_provider_config_review(source)

        for warning in source.warnings:
            self.assertIn(warning, review.warnings)

    def test_review_context_and_constraints_are_deterministic(self) -> None:
        source = self.make_prompt_review()

        first = build_provider_config_review(source)
        second = build_provider_config_review(source)

        self.assertEqual(source.review_context, first.review_context)
        self.assertEqual(source.review_next, first.review_next)
        self.assertEqual(first.constraints, second.constraints)

    def test_policy_material_is_static_bounded_and_review_only(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())

        self.assertEqual(PROVIDER_POLICY_MATERIAL, review.provider_policy_material)
        self.assertLessEqual(len(review.provider_policy_material), 40)
        self.assertTrue(review.is_review_only)

    def test_policy_material_contains_only_abstract_constraints(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())
        joined = " ".join(review.provider_policy_material).lower()

        self.assertIn("blocked_by_default", review.provider_policy_material)
        self.assertIn("no_live_calls", review.provider_policy_material)
        for forbidden in ("http://", "https://", "token=", "secret=", "api_key="):
            self.assertNotIn(forbidden, joined)

    def test_constructor_strips_secret_endpoint_and_live_material(self) -> None:
        review = ProviderConfigReview(
            state=PROVIDER_CONFIG_REVIEW_INVALID,
            source_prompt_packet_state="unsafe",
            source_handoff_state="unsafe",
            source_implication_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            provider_policy_material=("api_key=secret", "https://provider.example"),
            blockers=("invalid source",),
            warnings=(),
            review_context=(),
            review_next=(),
            constraints=(),
            boundary_text="unsafe",
        )

        self.assertEqual(PROVIDER_POLICY_MATERIAL, review.provider_policy_material)
        self.assertNotIn("api_key=secret", review.provider_policy_material)
        self.assertNotIn("https://provider.example", review.provider_policy_material)

    def test_inherited_secret_like_context_fails_closed(self) -> None:
        source = self.make_prompt_review()
        object.__setattr__(source, "review_context", ("api_key=secret",))

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertIn("forbidden", review.blockers[0])

    def test_inherited_endpoint_context_fails_closed(self) -> None:
        source = self.make_prompt_review()
        object.__setattr__(source, "review_context", ("https://provider.example",))

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertIn("forbidden", review.blockers[0])

    def test_inherited_secret_like_constraint_fails_closed_without_echo(self) -> None:
        source = self.make_prompt_review()
        object.__setattr__(source, "constraints", ("token=do-not-echo",))

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertNotIn("do-not-echo", str(review.to_dict()))

    def test_inherited_endpoint_warning_fails_closed_without_echo(self) -> None:
        source = self.make_prompt_review()
        object.__setattr__(source, "warnings", ("https://provider.example",))

        review = build_provider_config_review(source)

        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.state)
        self.assertNotIn("provider.example", str(review.to_dict()))

    def test_inherited_live_provider_or_model_context_fails_closed(self) -> None:
        for value in ("openai", "anthropic", "gemini", "gpt-live", "claude-live"):
            source = self.make_prompt_review()
            object.__setattr__(source, "review_context", (value,))
            with self.subTest(value=value):
                self.assertEqual(
                    PROVIDER_CONFIG_REVIEW_INVALID,
                    build_provider_config_review(source).state,
                )

    def test_output_includes_no_authority_warning(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())
        warnings = " ".join(review.warnings)

        self.assertIn("not real provider configuration", warnings)
        self.assertIn("no authority granted", review.boundary_text)

    def test_output_includes_no_live_secret_send_or_network_warning(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())
        warnings = " ".join(review.warnings)

        self.assertIn("provider live", warnings)
        self.assertIn("secret or API key handling", warnings)
        self.assertIn("No provider endpoint", warnings)
        self.assertIn("no network or prompt sending", review.boundary_text)

    def test_all_authority_and_external_flags_remain_false(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())

        self.assertFalse(review.authority_granted)
        self.assertFalse(review.execution_allowed)
        self.assertFalse(review.dispatch_allowed)
        self.assertFalse(review.provider_call_allowed)
        self.assertFalse(review.artifact_write_allowed)
        self.assertFalse(review.persistence_allowed)
        self.assertFalse(review.real_provider_config_created)
        self.assertFalse(review.provider_live_enabled)
        self.assertFalse(review.provider_request_created)
        self.assertFalse(review.prompt_sent)
        self.assertFalse(review.provider_config_read)
        self.assertFalse(review.provider_config_mutated)
        self.assertFalse(review.secret_accessed)
        self.assertFalse(review.api_key_accessed)
        self.assertFalse(review.credential_accessed)
        self.assertFalse(review.endpoint_configured)
        self.assertFalse(review.network_client_created)
        self.assertFalse(review.merge_authority_granted)
        self.assertFalse(review.review_executes_anything)

    def test_state_names_contain_no_dangerous_authority_language(self) -> None:
        dangerous = (
            "provider_ready", "provider_live_ready", "config_ready", "api_key_ready",
            "secret_ready", "send_ready", "prompt_ready", "execute_ready",
            "dispatch_ready", "approved", "authorized", "allowed",
            "permission_granted", "merge_ready",
        )
        for state in (
            PROVIDER_CONFIG_REVIEW_READY,
            PROVIDER_CONFIG_REVIEW_BLOCKED,
            PROVIDER_CONFIG_REVIEW_INVALID,
        ):
            with self.subTest(state=state):
                self.assertFalse(any(term in state for term in dangerous))

    def test_same_input_produces_same_output(self) -> None:
        source = self.make_prompt_review()

        self.assertEqual(
            build_provider_config_review(source),
            build_provider_config_review(source),
        )

    def test_input_object_is_not_mutated(self) -> None:
        source = self.make_prompt_review()
        before = source.to_dict()

        build_provider_config_review(source)

        self.assertEqual(before, source.to_dict())

    def test_input_dictionary_is_not_mutated(self) -> None:
        mapping = self.make_prompt_review().to_dict()
        before = dict(mapping)

        build_provider_config_review(mapping)

        self.assertEqual(before, mapping)

    def test_review_is_immutable(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())

        with self.assertRaises(FrozenInstanceError):
            review.state = PROVIDER_CONFIG_REVIEW_BLOCKED
        self.assertIsInstance(review.provider_policy_material, tuple)

    def test_dict_serialization_is_stable(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())

        first = provider_config_review_to_dict(review)
        second = review.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["provider_policy_material"], second["provider_policy_material"])

    def test_render_is_stable_and_review_only(self) -> None:
        review = build_provider_config_review(self.make_prompt_review())

        first = render_provider_config_review(review)
        second = render_provider_config_review(review)

        self.assertEqual(first, second)
        self.assertIn("blocked_by_default", first)
        self.assertIn("not real provider configuration", first)

    def test_helpers_reject_unknown_review_input(self) -> None:
        for value in (None, {}, "review", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    provider_config_review_to_dict(value)
                with self.assertRaises(ValueError):
                    render_provider_config_review(value)

    def test_fail_closed_constructor_forces_all_safety_flags_false(self) -> None:
        review = ProviderConfigReview(
            state=PROVIDER_CONFIG_REVIEW_INVALID,
            source_prompt_packet_state="unsafe",
            source_handoff_state="unsafe",
            source_implication_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            provider_policy_material=("unsafe",),
            blockers=("invalid source",),
            warnings=(),
            review_context=("unsafe",),
            review_next=(),
            constraints=(),
            boundary_text="unsafe",
            authority_granted=True,
            execution_allowed=True,
            dispatch_allowed=True,
            provider_call_allowed=True,
            artifact_write_allowed=True,
            persistence_allowed=True,
            real_provider_config_created=True,
            provider_live_enabled=True,
            provider_request_created=True,
            prompt_sent=True,
            provider_config_read=True,
            provider_config_mutated=True,
            secret_accessed=True,
            api_key_accessed=True,
            credential_accessed=True,
            endpoint_configured=True,
            network_client_created=True,
            merge_authority_granted=True,
            review_executes_anything=True,
        )

        self.assertEqual(PROVIDER_POLICY_MATERIAL, review.provider_policy_material)
        self.assertEqual("", review.decision_id)
        self.assertFalse(review.authority_granted)
        self.assertFalse(review.provider_live_enabled)
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
            self.assertFalse(module_name.startswith("runtime.provider_config"))
            self.assertFalse(module_name.startswith("runtime.provider_live"))
            self.assertNotIn("artifact", module_name)

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {
            "system", "write_text", "write_bytes", "write", "open", "send",
            "post", "get", "request", "execute", "dispatch",
        }:
            self.assertNotIn(attr, called_attrs)

    def test_module_has_no_config_secret_or_endpoint_access(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "os.environ", "getenv", "load_dotenv", "provider_config.",
            "provider_live_adapter.", "send_prompt", "api.openai", "api.anthropic",
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

    def make_failed_prompt_review(self, state: str) -> PromptPacketReview:
        return PromptPacketReview(
            state=state,
            source_handoff_state="",
            source_implication_state="",
            decision_id="",
            decision_hash="",
            decision_status="",
            bundle_id="",
            bundle_hash="",
            prompt_material=(),
            blockers=("source prompt review blocked",),
            warnings=("Source remains review-only.",),
            review_context=(),
            review_next=("Review the source blocker.",),
            constraints=(),
            boundary_text="",
        )

    def make_prompt_review(self) -> PromptPacketReview:
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
        handoff = build_decision_review_handoff(implication)
        return build_prompt_packet_review(handoff)
