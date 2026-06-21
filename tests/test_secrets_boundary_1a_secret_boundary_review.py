from __future__ import annotations

import ast
import copy
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
from runtime.prompt_packet_review import build_prompt_packet_review
from runtime.provider_config_review import (
    PROVIDER_CONFIG_REVIEW_BLOCKED,
    PROVIDER_CONFIG_REVIEW_INVALID,
    PROVIDER_CONFIG_REVIEW_READY,
    ProviderConfigReview,
    build_provider_config_review,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.secret_boundary_review import (
    SECRET_BOUNDARY_REVIEW_BLOCKED,
    SECRET_BOUNDARY_REVIEW_INVALID,
    SECRET_BOUNDARY_REVIEW_READY,
    SECRET_POLICY_MATERIAL,
    SecretBoundaryReview,
    build_secret_boundary_review,
    render_secret_boundary_review,
    secret_boundary_review_to_dict,
)
from runtime.validated_decision_readiness import build_validated_decision_readiness_map


RUNTIME_FILE = Path(__file__).parents[1] / "runtime" / "secret_boundary_review.py"


class SecretBoundaryReviewTests(unittest.TestCase):
    def test_missing_input_returns_invalid(self) -> None:
        review = build_secret_boundary_review(None)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertTrue(review.blockers)
        self.assertFalse(review.authority_granted)

    def test_malformed_input_returns_invalid(self) -> None:
        for value in ("review", 1, [], object()):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(
                    SECRET_BOUNDARY_REVIEW_INVALID,
                    build_secret_boundary_review(value).state,
                )

    def test_missing_field_returns_invalid(self) -> None:
        malformed = self.make_provider_review().to_dict()
        malformed.pop("decision_hash")

        review = build_secret_boundary_review(malformed)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertIn("canonical schema", review.blockers[0])

    def test_unknown_source_state_returns_invalid(self) -> None:
        malformed = self.make_provider_review().to_dict()
        malformed["state"] = "secret_ready"

        self.assertEqual(
            SECRET_BOUNDARY_REVIEW_INVALID,
            build_secret_boundary_review(malformed).state,
        )

    def test_noncanonical_input_returns_invalid(self) -> None:
        malformed = self.make_provider_review().to_dict()
        malformed["secret_accessed"] = True

        review = build_secret_boundary_review(malformed)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertIn("canonical", review.blockers[0])

    def test_blocked_provider_review_returns_blocked(self) -> None:
        source = self.make_failed_provider_review(PROVIDER_CONFIG_REVIEW_BLOCKED)

        review = build_secret_boundary_review(source)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_BLOCKED, review.state)
        self.assertEqual(PROVIDER_CONFIG_REVIEW_BLOCKED, review.source_provider_config_state)
        self.assertFalse(review.authority_granted)

    def test_invalid_provider_review_returns_invalid(self) -> None:
        source = self.make_failed_provider_review(PROVIDER_CONFIG_REVIEW_INVALID)

        review = build_secret_boundary_review(source)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertEqual(PROVIDER_CONFIG_REVIEW_INVALID, review.source_provider_config_state)

    def test_valid_provider_review_returns_ready_review(self) -> None:
        source = self.make_provider_review()

        review = build_secret_boundary_review(source)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_READY, review.state)
        self.assertEqual(PROVIDER_CONFIG_REVIEW_READY, review.source_provider_config_state)
        self.assertEqual("ready_for_implication_review", review.source_readiness_state)
        self.assertTrue(review.is_review_only)

    def test_canonical_dictionary_is_accepted(self) -> None:
        source = self.make_provider_review()

        review = build_secret_boundary_review(source.to_dict())

        self.assertEqual(SECRET_BOUNDARY_REVIEW_READY, review.state)
        self.assertEqual(source.decision_id, review.decision_id)

    def test_blockers_are_preserved(self) -> None:
        source = self.make_failed_provider_review(PROVIDER_CONFIG_REVIEW_BLOCKED)

        review = build_secret_boundary_review(source)

        self.assertEqual(source.blockers, review.blockers)

    def test_warnings_are_preserved_and_extended(self) -> None:
        source = self.make_provider_review()

        review = build_secret_boundary_review(source)

        for warning in source.warnings:
            self.assertIn(warning, review.warnings)
        self.assertGreater(len(review.warnings), len(source.warnings))

    def test_review_context_and_constraints_are_carried_forward(self) -> None:
        source = self.make_provider_review()

        review = build_secret_boundary_review(source)

        self.assertEqual(source.review_context, review.review_context)
        self.assertEqual(source.review_next, review.review_next)
        for constraint in source.constraints:
            self.assertIn(constraint, review.constraints)

    def test_policy_material_is_static_and_bounded(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())

        self.assertEqual(SECRET_POLICY_MATERIAL, review.secret_policy_material)
        self.assertLessEqual(len(review.secret_policy_material), 40)
        self.assertTrue(all(len(item) <= 512 for item in review.secret_policy_material))
        for forbidden in ("http://", "https://", "token=", "secret=", "api_key="):
            self.assertNotIn(forbidden, " ".join(review.secret_policy_material).lower())

    def test_constructor_strips_supplied_secret_policy_material(self) -> None:
        review = SecretBoundaryReview(
            state=SECRET_BOUNDARY_REVIEW_INVALID,
            source_provider_config_state="unsafe",
            source_prompt_packet_state="unsafe",
            source_handoff_state="unsafe",
            source_implication_state="unsafe",
            source_readiness_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            secret_policy_material=("api_key=do-not-keep", "https://example.invalid"),
            blockers=("invalid source",),
            warnings=(),
            review_context=(),
            review_next=(),
            constraints=(),
            boundary_text="unsafe",
        )

        self.assertEqual(SECRET_POLICY_MATERIAL, review.secret_policy_material)
        self.assertNotIn("do-not-keep", str(review.to_dict()))

    def test_ready_constructor_forces_canonical_source_states(self) -> None:
        source = self.make_provider_review()
        review = SecretBoundaryReview(
            state=SECRET_BOUNDARY_REVIEW_READY,
            source_provider_config_state="unsafe",
            source_prompt_packet_state="unsafe",
            source_handoff_state="unsafe",
            source_implication_state="unsafe",
            source_readiness_state="unsafe",
            decision_id=source.decision_id,
            decision_hash=source.decision_hash,
            decision_status=source.decision_status,
            bundle_id=source.bundle_id,
            bundle_hash=source.bundle_hash,
            secret_policy_material=(),
            blockers=(),
            warnings=(),
            review_context=("review context",),
            review_next=("review next",),
            constraints=(),
            boundary_text="unsafe",
        )

        self.assertEqual(PROVIDER_CONFIG_REVIEW_READY, review.source_provider_config_state)
        self.assertEqual("prompt_packet_review_ready", review.source_prompt_packet_state)
        self.assertEqual("handoff_ready", review.source_handoff_state)
        self.assertEqual("ready_for_implication_review", review.source_implication_state)
        self.assertEqual("ready_for_implication_review", review.source_readiness_state)

    def test_tampered_source_policy_material_fails_closed_without_echo(self) -> None:
        source = self.make_provider_review()
        object.__setattr__(source, "provider_policy_material", ("secret=do-not-echo",))

        review = build_secret_boundary_review(source)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertNotIn("do-not-echo", str(review.to_dict()))

    def test_inherited_secret_like_constraint_fails_closed_without_echo(self) -> None:
        source = self.make_provider_review()
        object.__setattr__(source, "constraints", ("token=do-not-echo",))

        review = build_secret_boundary_review(source)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertNotIn("do-not-echo", str(review.to_dict()))

    def test_inherited_endpoint_warning_fails_closed_without_echo(self) -> None:
        source = self.make_provider_review()
        object.__setattr__(source, "warnings", ("https://provider.example",))

        review = build_secret_boundary_review(source)

        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
        self.assertNotIn("provider.example", str(review.to_dict()))

    def test_inherited_secret_endpoint_or_command_context_fails_closed(self) -> None:
        values = (
            "api_key=do-not-use",
            "password=do-not-use",
            "-----BEGIN PRIVATE KEY-----",
            "export SERVICE_TOKEN=value",
            "https://provider.example",
            "openai",
            "gpt-live",
            "send prompt now",
            "execute command now",
            "dispatch request now",
        )
        for value in values:
            source = self.make_provider_review()
            object.__setattr__(source, "review_context", (value,))
            with self.subTest(value=value):
                review = build_secret_boundary_review(source)
                self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.state)
                self.assertNotIn(value, str(review.to_dict()))

    def test_output_includes_no_authority_warning(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())
        warnings = " ".join(review.warnings)

        self.assertIn("not secret loading", warnings)
        self.assertIn("no authority granted", review.boundary_text)

    def test_output_includes_secret_env_provider_send_network_boundaries(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())
        rendered = render_secret_boundary_review(review)

        self.assertIn("no secret or API key loading", rendered)
        self.assertIn("no environment variable or env file reads", rendered)
        self.assertIn("not provider configuration or provider live", rendered)
        self.assertIn("not a provider request", rendered)
        self.assertIn("no network or prompt sending", rendered)

    def test_all_authority_and_external_flags_remain_false(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())
        flags = (
            "authority_granted",
            "execution_allowed",
            "dispatch_allowed",
            "provider_call_allowed",
            "artifact_write_allowed",
            "persistence_allowed",
            "real_secret_boundary_created",
            "secret_config_created",
            "secret_config_read",
            "secret_config_mutated",
            "secret_loaded",
            "secret_read",
            "secret_stored",
            "secret_displayed",
            "api_key_loaded",
            "api_key_accessed",
            "api_key_stored",
            "credential_accessed",
            "environment_variables_read",
            "env_file_read",
            "real_provider_config_created",
            "provider_config_read",
            "provider_config_mutated",
            "provider_live_enabled",
            "provider_request_created",
            "prompt_sent",
            "endpoint_configured",
            "network_client_created",
            "merge_authority_granted",
            "review_executes_anything",
        )
        for flag in flags:
            with self.subTest(flag=flag):
                self.assertFalse(getattr(review, flag))

    def test_state_names_contain_no_dangerous_authority_language(self) -> None:
        dangerous = (
            "secret_ready",
            "api_key_ready",
            "credential_ready",
            "provider_ready",
            "provider_live_ready",
            "config_ready",
            "send_ready",
            "prompt_ready",
            "execute_ready",
            "dispatch_ready",
            "approved",
            "authorized",
            "allowed",
            "permission_granted",
            "merge_ready",
        )
        for state in (
            SECRET_BOUNDARY_REVIEW_READY,
            SECRET_BOUNDARY_REVIEW_BLOCKED,
            SECRET_BOUNDARY_REVIEW_INVALID,
        ):
            with self.subTest(state=state):
                self.assertFalse(any(term in state for term in dangerous))

    def test_same_input_produces_same_output(self) -> None:
        source = self.make_provider_review()

        self.assertEqual(
            build_secret_boundary_review(source),
            build_secret_boundary_review(source),
        )

    def test_input_object_is_not_mutated(self) -> None:
        source = self.make_provider_review()
        before = source.to_dict()

        build_secret_boundary_review(source)

        self.assertEqual(before, source.to_dict())

    def test_input_dictionary_is_not_mutated(self) -> None:
        mapping = self.make_provider_review().to_dict()
        before = copy.deepcopy(mapping)

        build_secret_boundary_review(mapping)

        self.assertEqual(before, mapping)

    def test_review_is_immutable(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())

        with self.assertRaises(FrozenInstanceError):
            review.state = SECRET_BOUNDARY_REVIEW_BLOCKED
        self.assertIsInstance(review.secret_policy_material, tuple)

    def test_dict_serialization_is_stable(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())

        first = secret_boundary_review_to_dict(review)
        second = review.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["secret_policy_material"], second["secret_policy_material"])

    def test_render_is_stable_and_review_only(self) -> None:
        review = build_secret_boundary_review(self.make_provider_review())

        first = render_secret_boundary_review(review)
        second = render_secret_boundary_review(review)

        self.assertEqual(first, second)
        self.assertIn("blocked_by_default", first)
        self.assertIn("not a real secret boundary", first)

    def test_helpers_reject_unknown_review_input(self) -> None:
        for value in (None, {}, "review", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    secret_boundary_review_to_dict(value)
                with self.assertRaises(ValueError):
                    render_secret_boundary_review(value)

    def test_fail_closed_constructor_forces_all_safety_flags_false(self) -> None:
        review = SecretBoundaryReview(
            state=SECRET_BOUNDARY_REVIEW_INVALID,
            source_provider_config_state="unsafe",
            source_prompt_packet_state="unsafe",
            source_handoff_state="unsafe",
            source_implication_state="unsafe",
            source_readiness_state="unsafe",
            decision_id="unsafe",
            decision_hash="unsafe",
            decision_status="unsafe",
            bundle_id="unsafe",
            bundle_hash="unsafe",
            secret_policy_material=("unsafe",),
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
            real_secret_boundary_created=True,
            secret_config_created=True,
            secret_config_read=True,
            secret_config_mutated=True,
            secret_loaded=True,
            secret_read=True,
            secret_stored=True,
            secret_displayed=True,
            api_key_loaded=True,
            api_key_accessed=True,
            api_key_stored=True,
            credential_accessed=True,
            environment_variables_read=True,
            env_file_read=True,
            real_provider_config_created=True,
            provider_config_read=True,
            provider_config_mutated=True,
            provider_live_enabled=True,
            provider_request_created=True,
            prompt_sent=True,
            endpoint_configured=True,
            network_client_created=True,
            merge_authority_granted=True,
            review_executes_anything=True,
        )

        self.assertEqual(SECRET_POLICY_MATERIAL, review.secret_policy_material)
        self.assertEqual("", review.decision_id)
        self.assertFalse(review.authority_granted)
        self.assertFalse(review.secret_loaded)
        self.assertFalse(review.environment_variables_read)

    def test_module_performs_no_io_network_or_capability_calls(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "sqlite3",
            "dotenv",
            "keyring",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
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
            self.assertNotEqual("runtime.provider_config", module_name)
            self.assertFalse(module_name.startswith("runtime.provider_live"))
            self.assertFalse(module_name.startswith("runtime.provider_request"))
            self.assertNotIn("artifact", module_name)

        for name in {"eval", "exec", "open", "print"}:
            self.assertNotIn(name, called_names)
        for attr in {
            "system",
            "getenv",
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "write",
            "open",
            "send",
            "post",
            "get",
            "request",
            "execute",
            "dispatch",
        }:
            self.assertNotIn(attr, called_attrs)

    def test_module_has_no_environment_secret_or_endpoint_access(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "os.environ",
            "os.getenv",
            "load_dotenv",
            "dotenv_values",
            "keyring.",
            "provider_live_adapter.",
            "provider_config.",
            "send_prompt",
            "api.openai",
            "api.anthropic",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_module_adds_no_ui_storage_or_retrieval_architecture(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "hat store",
            "tetrad",
            "evidence memory",
            "canonical promotion",
            "fts5",
            "zstd",
            "knowledge pack",
            "fastapi",
            "flask",
            "click.command",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def make_failed_provider_review(self, state: str) -> ProviderConfigReview:
        return ProviderConfigReview(
            state=state,
            source_prompt_packet_state="",
            source_handoff_state="",
            source_implication_state="",
            decision_id="",
            decision_hash="",
            decision_status="",
            bundle_id="",
            bundle_hash="",
            provider_policy_material=(),
            blockers=("source provider review blocked",),
            warnings=("Source remains review-only.",),
            review_context=(),
            review_next=("Review the source blocker.",),
            constraints=(),
            boundary_text="",
        )

    def make_provider_review(self) -> ProviderConfigReview:
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
        prompt_review = build_prompt_packet_review(handoff)
        return build_provider_config_review(prompt_review)


if __name__ == "__main__":
    unittest.main()
