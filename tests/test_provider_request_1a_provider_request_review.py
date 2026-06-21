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
from runtime.provider_config_review import build_provider_config_review
from runtime.provider_request_review import (
    PROVIDER_REQUEST_REVIEW_BLOCKED,
    PROVIDER_REQUEST_REVIEW_INVALID,
    PROVIDER_REQUEST_REVIEW_READY,
    REQUEST_POLICY_MATERIAL,
    ProviderRequestReview,
    build_provider_request_review,
    provider_request_review_to_dict,
    render_provider_request_review,
)
from runtime.review_session_bundle import create_review_session_bundle
from runtime.review_session_snapshot import create_review_session_snapshot
from runtime.secret_boundary_review import (
    SECRET_BOUNDARY_REVIEW_BLOCKED,
    SECRET_BOUNDARY_REVIEW_INVALID,
    SECRET_BOUNDARY_REVIEW_READY,
    SecretBoundaryReview,
    build_secret_boundary_review,
)
from runtime.validated_decision_readiness import build_validated_decision_readiness_map


RUNTIME_FILE = Path(__file__).parents[1] / "runtime" / "provider_request_review.py"


class ProviderRequestReviewTests(unittest.TestCase):
    def test_missing_input_returns_invalid(self) -> None:
        review = build_provider_request_review(None)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
        self.assertTrue(review.blockers)
        self.assertFalse(review.authority_granted)

    def test_malformed_input_returns_invalid(self) -> None:
        for value in ("review", 1, [], object()):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(
                    PROVIDER_REQUEST_REVIEW_INVALID,
                    build_provider_request_review(value).state,
                )

    def test_missing_field_returns_invalid(self) -> None:
        malformed = self.make_secret_review().to_dict()
        malformed.pop("decision_hash")

        review = build_provider_request_review(malformed)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
        self.assertIn("canonical schema", review.blockers[0])

    def test_unknown_source_state_returns_invalid(self) -> None:
        malformed = self.make_secret_review().to_dict()
        malformed["state"] = "provider_request_ready"

        self.assertEqual(
            PROVIDER_REQUEST_REVIEW_INVALID,
            build_provider_request_review(malformed).state,
        )

    def test_noncanonical_input_returns_invalid(self) -> None:
        malformed = self.make_secret_review().to_dict()
        malformed["secret_loaded"] = True

        review = build_provider_request_review(malformed)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
        self.assertIn("canonical", review.blockers[0])

    def test_blocked_secret_boundary_returns_blocked(self) -> None:
        source = self.make_failed_secret_review(SECRET_BOUNDARY_REVIEW_BLOCKED)

        review = build_provider_request_review(source)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_BLOCKED, review.state)
        self.assertEqual(SECRET_BOUNDARY_REVIEW_BLOCKED, review.source_secret_boundary_state)
        self.assertFalse(review.provider_call_allowed)

    def test_invalid_secret_boundary_returns_invalid(self) -> None:
        source = self.make_failed_secret_review(SECRET_BOUNDARY_REVIEW_INVALID)

        review = build_provider_request_review(source)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
        self.assertEqual(SECRET_BOUNDARY_REVIEW_INVALID, review.source_secret_boundary_state)

    def test_valid_secret_boundary_returns_ready_review(self) -> None:
        source = self.make_secret_review()

        review = build_provider_request_review(source)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_READY, review.state)
        self.assertEqual(SECRET_BOUNDARY_REVIEW_READY, review.source_secret_boundary_state)
        self.assertEqual("provider_config_review_ready", review.source_provider_config_state)
        self.assertEqual("ready_for_implication_review", review.source_readiness_state)
        self.assertTrue(review.is_review_only)

    def test_canonical_dictionary_is_accepted(self) -> None:
        source = self.make_secret_review()

        review = build_provider_request_review(source.to_dict())

        self.assertEqual(PROVIDER_REQUEST_REVIEW_READY, review.state)
        self.assertEqual(source.decision_id, review.decision_id)

    def test_blockers_are_preserved(self) -> None:
        source = self.make_failed_secret_review(SECRET_BOUNDARY_REVIEW_BLOCKED)

        review = build_provider_request_review(source)

        self.assertEqual(source.blockers, review.blockers)

    def test_warnings_are_preserved_and_extended(self) -> None:
        source = self.make_secret_review()

        review = build_provider_request_review(source)

        for warning in source.warnings:
            self.assertIn(warning, review.warnings)
        self.assertGreater(len(review.warnings), len(source.warnings))

    def test_review_context_and_constraints_are_carried_forward(self) -> None:
        source = self.make_secret_review()

        review = build_provider_request_review(source)

        self.assertEqual(source.review_context, review.review_context)
        self.assertEqual(source.review_next, review.review_next)
        for constraint in source.constraints:
            self.assertIn(constraint, review.constraints)

    def test_policy_material_is_generic_static_and_bounded(self) -> None:
        review = build_provider_request_review(self.make_secret_review())

        self.assertEqual(REQUEST_POLICY_MATERIAL, review.request_policy_material)
        self.assertLessEqual(len(review.request_policy_material), 40)
        self.assertTrue(all(len(item) <= 512 for item in review.request_policy_material))
        material = " ".join(review.request_policy_material).lower()
        for forbidden in (
            "http://",
            "https://",
            "token=",
            "secret=",
            "api_key=",
            "org_",
            "proj_",
            "project_id",
        ):
            self.assertNotIn(forbidden, material)

    def test_constructor_strips_supplied_request_policy_material(self) -> None:
        review = ProviderRequestReview(
            state=PROVIDER_REQUEST_REVIEW_INVALID,
            source_secret_boundary_state="unsafe",
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
            request_policy_material=("api_key=do-not-keep", "https://example.invalid"),
            blockers=("invalid source",),
            warnings=(),
            review_context=(),
            review_next=(),
            constraints=(),
            boundary_text="unsafe",
        )

        self.assertEqual(REQUEST_POLICY_MATERIAL, review.request_policy_material)
        self.assertNotIn("do-not-keep", str(review.to_dict()))

    def test_ready_constructor_forces_canonical_source_states(self) -> None:
        source = self.make_secret_review()
        review = ProviderRequestReview(
            state=PROVIDER_REQUEST_REVIEW_READY,
            source_secret_boundary_state="unsafe",
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
            request_policy_material=(),
            blockers=(),
            warnings=(),
            review_context=("review context",),
            review_next=("review next",),
            constraints=(),
            boundary_text="unsafe",
        )

        self.assertEqual(SECRET_BOUNDARY_REVIEW_READY, review.source_secret_boundary_state)
        self.assertEqual("provider_config_review_ready", review.source_provider_config_state)
        self.assertEqual("prompt_packet_review_ready", review.source_prompt_packet_state)
        self.assertEqual("handoff_ready", review.source_handoff_state)
        self.assertEqual("ready_for_implication_review", review.source_implication_state)
        self.assertEqual("ready_for_implication_review", review.source_readiness_state)

    def test_tampered_source_policy_material_fails_closed_without_echo(self) -> None:
        source = self.make_secret_review()
        object.__setattr__(source, "secret_policy_material", ("org_do-not-echo",))

        review = build_provider_request_review(source)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
        self.assertNotIn("do-not-echo", str(review.to_dict()))

    def test_inherited_endpoint_warning_fails_closed_without_echo(self) -> None:
        source = self.make_secret_review()
        object.__setattr__(source, "warnings", ("https://provider.example",))

        review = build_provider_request_review(source)

        self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
        self.assertNotIn("provider.example", str(review.to_dict()))

    def test_inherited_sensitive_or_executable_context_fails_closed(self) -> None:
        values = (
            "api_key=do-not-use",
            "password=do-not-use",
            "-----BEGIN PRIVATE KEY-----",
            "export SERVICE_TOKEN=value",
            "https://provider.example",
            "org_example",
            "proj_example",
            "project_id=example",
            "openai",
            "anthropic",
            "gemini",
            "gpt-live",
            "claude-live",
            'request body {"model":"live"}',
            "message payload for live use",
            "platform integration setup",
            "billing account",
            "cost-generating request",
            "send prompt now",
            "execute command now",
            "dispatch request now",
        )
        for value in values:
            source = self.make_secret_review()
            object.__setattr__(source, "review_context", (value,))
            with self.subTest(value=value):
                review = build_provider_request_review(source)
                self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
                self.assertNotIn(value, str(review.to_dict()))

    def test_inherited_platform_or_cost_constraint_fails_closed(self) -> None:
        for value, marker in (
            ("platform integration marker-1", "marker-1"),
            ("paid API path marker-2", "marker-2"),
            ("cost=marker-3", "marker-3"),
        ):
            source = self.make_secret_review()
            object.__setattr__(source, "constraints", (value,))
            with self.subTest(value=value):
                review = build_provider_request_review(source)
                self.assertEqual(PROVIDER_REQUEST_REVIEW_INVALID, review.state)
                self.assertNotIn(marker, str(review.to_dict()))

    def test_output_includes_no_authority_warning(self) -> None:
        review = build_provider_request_review(self.make_secret_review())
        warnings = " ".join(review.warnings)

        self.assertIn("not a real provider request", warnings)
        self.assertIn("no authority granted", review.boundary_text)

    def test_output_includes_all_external_boundaries(self) -> None:
        review = build_provider_request_review(self.make_secret_review())
        rendered = render_provider_request_review(review)

        self.assertIn("not a real provider request or request payload", rendered)
        self.assertIn("no provider live, provider call, or model call", rendered)
        self.assertIn("no prompt sending", rendered)
        self.assertIn("no secret, API key, or environment reads", rendered)
        self.assertIn("no endpoint, network client, or platform integration", rendered)
        self.assertIn("no paid API or cost-generating path", rendered)

    def test_all_authority_and_external_flags_remain_false(self) -> None:
        review = build_provider_request_review(self.make_secret_review())
        flags = (
            "authority_granted",
            "execution_allowed",
            "dispatch_allowed",
            "provider_call_allowed",
            "artifact_write_allowed",
            "persistence_allowed",
            "provider_live_enabled",
            "real_provider_request_created",
            "request_payload_created",
            "prompt_sent",
            "model_call_created",
            "endpoint_configured",
            "network_client_created",
            "secret_loaded",
            "api_key_loaded",
            "credential_accessed",
            "environment_variables_read",
            "env_file_read",
            "provider_config_created",
            "provider_config_read",
            "provider_config_mutated",
            "secret_config_created",
            "secret_config_read",
            "secret_config_mutated",
            "platform_integration_created",
            "organization_id_used",
            "project_id_used",
            "paid_api_used",
            "cost_generating_path_created",
            "merge_authority_granted",
            "review_executes_anything",
        )
        for flag in flags:
            with self.subTest(flag=flag):
                self.assertFalse(getattr(review, flag))

    def test_state_names_contain_no_dangerous_authority_language(self) -> None:
        dangerous = (
            "provider_request_ready",
            "provider_live_ready",
            "request_ready",
            "payload_ready",
            "prompt_ready",
            "send_ready",
            "model_ready",
            "secret_ready",
            "api_key_ready",
            "credential_ready",
            "execute_ready",
            "dispatch_ready",
            "approved",
            "authorized",
            "allowed",
            "permission_granted",
            "merge_ready",
        )
        for state in (
            PROVIDER_REQUEST_REVIEW_READY,
            PROVIDER_REQUEST_REVIEW_BLOCKED,
            PROVIDER_REQUEST_REVIEW_INVALID,
        ):
            with self.subTest(state=state):
                self.assertFalse(any(term in state for term in dangerous))

    def test_same_input_produces_same_output(self) -> None:
        source = self.make_secret_review()

        self.assertEqual(
            build_provider_request_review(source),
            build_provider_request_review(source),
        )

    def test_input_object_is_not_mutated(self) -> None:
        source = self.make_secret_review()
        before = source.to_dict()

        build_provider_request_review(source)

        self.assertEqual(before, source.to_dict())

    def test_input_dictionary_is_not_mutated(self) -> None:
        mapping = self.make_secret_review().to_dict()
        before = copy.deepcopy(mapping)

        build_provider_request_review(mapping)

        self.assertEqual(before, mapping)

    def test_review_is_immutable(self) -> None:
        review = build_provider_request_review(self.make_secret_review())

        with self.assertRaises(FrozenInstanceError):
            review.state = PROVIDER_REQUEST_REVIEW_BLOCKED
        self.assertIsInstance(review.request_policy_material, tuple)

    def test_dict_serialization_is_stable(self) -> None:
        review = build_provider_request_review(self.make_secret_review())

        first = provider_request_review_to_dict(review)
        second = review.to_dict()

        self.assertEqual(first, second)
        self.assertIsNot(first["request_policy_material"], second["request_policy_material"])

    def test_render_is_stable_and_review_only(self) -> None:
        review = build_provider_request_review(self.make_secret_review())

        first = render_provider_request_review(review)
        second = render_provider_request_review(review)

        self.assertEqual(first, second)
        self.assertIn("blocked_by_default", first)
        self.assertIn("generic provider request review only", first)
        self.assertIn("no paid API or cost-generating path", first)

    def test_helpers_reject_unknown_review_input(self) -> None:
        for value in (None, {}, "review", object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    provider_request_review_to_dict(value)
                with self.assertRaises(ValueError):
                    render_provider_request_review(value)

    def test_fail_closed_constructor_forces_all_safety_flags_false(self) -> None:
        review = ProviderRequestReview(
            state=PROVIDER_REQUEST_REVIEW_INVALID,
            source_secret_boundary_state="unsafe",
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
            request_policy_material=("unsafe",),
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
            provider_live_enabled=True,
            real_provider_request_created=True,
            request_payload_created=True,
            prompt_sent=True,
            model_call_created=True,
            endpoint_configured=True,
            network_client_created=True,
            secret_loaded=True,
            api_key_loaded=True,
            credential_accessed=True,
            environment_variables_read=True,
            env_file_read=True,
            provider_config_created=True,
            provider_config_read=True,
            provider_config_mutated=True,
            secret_config_created=True,
            secret_config_read=True,
            secret_config_mutated=True,
            platform_integration_created=True,
            organization_id_used=True,
            project_id_used=True,
            paid_api_used=True,
            cost_generating_path_created=True,
            merge_authority_granted=True,
            review_executes_anything=True,
        )

        self.assertEqual(REQUEST_POLICY_MATERIAL, review.request_policy_material)
        self.assertEqual("", review.decision_id)
        self.assertFalse(review.authority_granted)
        self.assertFalse(review.real_provider_request_created)
        self.assertFalse(review.cost_generating_path_created)

    def test_module_performs_no_io_network_platform_or_capability_calls(self) -> None:
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
            self.assertEqual(
                module_name == "runtime.provider_request_review",
                module_name.startswith("runtime.provider_request"),
            )
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

    def test_module_has_no_environment_secret_endpoint_or_platform_access(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()

        for term in (
            "os.environ",
            "os.getenv",
            "load_dotenv",
            "dotenv_values",
            "keyring.",
            "provider_live_adapter.",
            "provider_config.",
            "provider_request_flow.",
            "send_prompt",
            "api.openai",
            "api.anthropic",
            "billing_client",
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

    def make_failed_secret_review(self, state: str) -> SecretBoundaryReview:
        return SecretBoundaryReview(
            state=state,
            source_provider_config_state="",
            source_prompt_packet_state="",
            source_handoff_state="",
            source_implication_state="",
            source_readiness_state="",
            decision_id="",
            decision_hash="",
            decision_status="",
            bundle_id="",
            bundle_hash="",
            secret_policy_material=(),
            blockers=("source secret boundary blocked",),
            warnings=("Source remains review-only.",),
            review_context=(),
            review_next=("Review the source blocker.",),
            constraints=(),
            boundary_text="",
        )

    def make_secret_review(self) -> SecretBoundaryReview:
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
        provider_review = build_provider_config_review(prompt_review)
        return build_secret_boundary_review(provider_review)


if __name__ == "__main__":
    unittest.main()
