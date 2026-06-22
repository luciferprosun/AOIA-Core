from __future__ import annotations

import ast
import copy
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from runtime.provider_live_readiness_review import (
    FUTURE_PROVIDER_HINT,
    LIVE_READINESS_POLICY_MATERIAL,
    LIVE_READINESS_STATUS,
    PROVIDER_LIVE_READINESS_REVIEW_BLOCKED,
    PROVIDER_LIVE_READINESS_REVIEW_INVALID,
    PROVIDER_LIVE_READINESS_REVIEW_READY,
    ProviderLiveReadinessReview,
    build_provider_live_readiness_review,
    provider_live_readiness_review_to_dict,
    render_provider_live_readiness_review,
)
from runtime.provider_request_review import (
    PROVIDER_REQUEST_REVIEW_BLOCKED,
    PROVIDER_REQUEST_REVIEW_INVALID,
    PROVIDER_REQUEST_REVIEW_READY,
    ProviderRequestReview,
)


RUNTIME_FILE = Path(__file__).parents[1] / "runtime" / "provider_live_readiness_review.py"


class ProviderLiveReadinessReviewTests(unittest.TestCase):
    def test_missing_and_malformed_input_return_invalid(self) -> None:
        for source in (None, "review", 1, [], object()):
            with self.subTest(source=type(source).__name__):
                review = build_provider_live_readiness_review(source)
                self.assertEqual(PROVIDER_LIVE_READINESS_REVIEW_INVALID, review.state)
                self.assertFalse(review.authority_granted)

    def test_missing_or_tampered_canonical_field_returns_invalid(self) -> None:
        source = self.make_ready_source().to_dict()
        source.pop("decision_hash")
        self.assertEqual(
            PROVIDER_LIVE_READINESS_REVIEW_INVALID,
            build_provider_live_readiness_review(source).state,
        )

    def test_blocked_looking_but_noncanonical_source_returns_invalid(self) -> None:
        source = self.make_ready_source().to_dict()
        source["state"] = PROVIDER_REQUEST_REVIEW_BLOCKED
        source["blockers"] = ["claimed blocker"]

        review = build_provider_live_readiness_review(source)

        self.assertEqual(PROVIDER_LIVE_READINESS_REVIEW_INVALID, review.state)
        source = self.make_ready_source().to_dict()
        source["provider_call_allowed"] = True
        self.assertEqual(
            PROVIDER_LIVE_READINESS_REVIEW_INVALID,
            build_provider_live_readiness_review(source).state,
        )

    def test_blocked_and_invalid_sources_fail_closed(self) -> None:
        blocked = build_provider_live_readiness_review(
            self.make_failed_source(PROVIDER_REQUEST_REVIEW_BLOCKED)
        )
        invalid = build_provider_live_readiness_review(
            self.make_failed_source(PROVIDER_REQUEST_REVIEW_INVALID)
        )
        self.assertEqual(PROVIDER_LIVE_READINESS_REVIEW_BLOCKED, blocked.state)
        self.assertEqual(("source request blocked",), blocked.blockers)
        self.assertEqual(PROVIDER_LIVE_READINESS_REVIEW_INVALID, invalid.state)

    def test_valid_source_returns_ready_review(self) -> None:
        source = self.make_ready_source()
        review = build_provider_live_readiness_review(source)
        self.assertEqual(PROVIDER_LIVE_READINESS_REVIEW_READY, review.state)
        self.assertEqual(PROVIDER_REQUEST_REVIEW_READY, review.source_provider_request_state)
        self.assertEqual(source.decision_id, review.decision_id)
        self.assertTrue(review.is_review_only)

    def test_canonical_dictionary_is_accepted(self) -> None:
        source = self.make_ready_source()
        review = build_provider_live_readiness_review(source.to_dict())
        self.assertEqual(PROVIDER_LIVE_READINESS_REVIEW_READY, review.state)
        self.assertEqual(source.bundle_hash, review.bundle_hash)

    def test_source_material_is_preserved_and_extended_deterministically(self) -> None:
        source = self.make_ready_source()
        review = build_provider_live_readiness_review(source)
        self.assertEqual(source.review_context, review.review_context)
        for item in source.warnings:
            self.assertIn(item, review.warnings)
        for item in source.review_next:
            self.assertIn(item, review.review_next)
        for item in source.constraints:
            self.assertIn(item, review.constraints)

    def test_policy_is_static_bounded_zero_cost_and_not_live(self) -> None:
        review = build_provider_live_readiness_review(self.make_ready_source())
        self.assertEqual(LIVE_READINESS_POLICY_MATERIAL, review.live_readiness_policy_material)
        self.assertLessEqual(len(review.live_readiness_policy_material), 40)
        self.assertTrue(all(len(item) <= 512 for item in review.live_readiness_policy_material))
        self.assertEqual("not_live_review_only", LIVE_READINESS_STATUS)
        self.assertEqual("openrouter_future_candidate_review_only", FUTURE_PROVIDER_HINT)

    def test_boundary_text_and_render_are_explicit_and_stable(self) -> None:
        review = build_provider_live_readiness_review(self.make_ready_source())
        rendered = render_provider_live_readiness_review(review)
        self.assertEqual(rendered, render_provider_live_readiness_review(review))
        for phrase in (
            "not Provider Live or OpenRouter Live",
            "OpenRouter is a future candidate label only",
            "no API key, secret, environment, endpoint, or network access",
            "zero-cost and not cost-generating",
            "not an execution instruction",
            "no authority granted",
        ):
            self.assertIn(phrase, rendered)

    def test_future_requirements_are_explicit(self) -> None:
        review = build_provider_live_readiness_review(self.make_ready_source())
        material = " ".join(review.live_readiness_policy_material)
        for phrase in (
            "future_openrouter_adapter_contract_required",
            "future_key_boundary_required",
            "future_cost_guard_required",
            "future_manual_one_shot_test_required",
            "future_provider_live_requires_explicit_human_approval",
        ):
            self.assertIn(phrase, material)

    def test_all_external_and_authority_flags_are_false(self) -> None:
        review = build_provider_live_readiness_review(self.make_ready_source())
        for name in (
            "authority_granted", "provider_live_enabled", "openrouter_live_enabled",
            "provider_configured", "provider_call_allowed", "model_call_allowed",
            "prompt_send_allowed", "api_key_loaded", "secret_loaded",
            "environment_variables_read", "env_file_read", "endpoint_configured",
            "network_client_created", "cost_generating_path_created",
            "execution_allowed", "dispatch_allowed", "artifact_write_allowed",
            "persistence_allowed", "merge_authority_granted", "review_executes_anything",
        ):
            self.assertFalse(getattr(review, name), name)

    def test_constructor_forces_policy_metadata_and_flags(self) -> None:
        source = self.make_ready_source()
        review = self.make_output(source, authority_granted=True, openrouter_live_enabled=True)
        self.assertFalse(review.authority_granted)
        self.assertFalse(review.openrouter_live_enabled)
        self.assertEqual(LIVE_READINESS_POLICY_MATERIAL, review.live_readiness_policy_material)
        self.assertEqual(FUTURE_PROVIDER_HINT, review.future_provider_hint)

    def test_output_is_immutable_and_deterministic(self) -> None:
        source = self.make_ready_source()
        first = build_provider_live_readiness_review(source)
        second = build_provider_live_readiness_review(source)
        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.state = "changed"  # type: ignore[misc]

    def test_source_object_and_dictionary_are_not_mutated(self) -> None:
        source = self.make_ready_source()
        before = copy.deepcopy(source.to_dict())
        build_provider_live_readiness_review(source)
        self.assertEqual(before, source.to_dict())
        mapping = source.to_dict()
        mapping_before = copy.deepcopy(mapping)
        build_provider_live_readiness_review(mapping)
        self.assertEqual(mapping_before, mapping)

    def test_to_dict_is_canonical_and_deterministic(self) -> None:
        review = build_provider_live_readiness_review(self.make_ready_source())
        first = provider_live_readiness_review_to_dict(review)
        second = provider_live_readiness_review_to_dict(review)
        self.assertEqual(first, second)
        self.assertIsInstance(first["warnings"], list)
        self.assertFalse(first["openrouter_live_enabled"])

    def test_helpers_reject_unknown_output(self) -> None:
        with self.assertRaises(ValueError):
            provider_live_readiness_review_to_dict(None)
        with self.assertRaises(ValueError):
            render_provider_live_readiness_review(None)

    def test_module_imports_only_inert_source_surface(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        called_names: set[str] = set()
        called_attrs: set[str] = set()
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
        forbidden = (
            "os", "pathlib", "subprocess", "socket", "requests", "urllib", "httpx",
            "aiohttp", "sqlite3", "dotenv", "keyring", "openai", "anthropic",
            "runtime.providers", "runtime.provider_config", "runtime.provider_live_adapter",
            "runtime.provider_clients", "runtime.dispatch", "runtime.execution",
        )
        for module in imports:
            self.assertFalse(any(module == item or module.startswith(item + ".") for item in forbidden))
        self.assertIn("runtime.provider_request_review", imports)
        for name in ("open", "print", "eval", "exec"):
            self.assertNotIn(name, called_names)
        for name in (
            "getenv", "read_text", "read_bytes", "write_text", "write_bytes", "open",
            "send", "post", "request", "execute", "dispatch",
        ):
            self.assertNotIn(name, called_attrs)

    def test_module_has_no_live_or_external_capability_tokens(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").lower()
        for term in (
            "os.environ", "os.getenv", "load_dotenv", "keyring.", "requests.",
            "socket.", "urllib.", "provider_live_adapter.", "provider_clients.",
            "https://", "http://", "openrouter_api_key", "openai_api_key",
            "canonical promotion", "hat store", "tetrad", "fts5", "zstd",
        ):
            self.assertNotIn(term, source)

    def test_provider_request_regression_shape_is_unchanged(self) -> None:
        source = self.make_ready_source()
        before = source.to_dict()
        build_provider_live_readiness_review(source)
        self.assertEqual(before, source.to_dict())

    def make_ready_source(self) -> ProviderRequestReview:
        return ProviderRequestReview(
            state=PROVIDER_REQUEST_REVIEW_READY,
            source_secret_boundary_state="secret_boundary_review_ready",
            source_provider_config_state="provider_config_review_ready",
            source_prompt_packet_state="prompt_packet_review_ready",
            source_handoff_state="handoff_ready",
            source_implication_state="ready_for_implication_review",
            source_readiness_state="ready_for_implication_review",
            decision_id="decision-a",
            decision_hash="decision-hash-a",
            decision_status="APPROVE_FOR_NEXT_REVIEW_STEP",
            bundle_id="bundle-a",
            bundle_hash="bundle-hash-a",
            request_policy_material=(),
            blockers=(),
            warnings=("Source is review-only.",),
            review_context=("Review context only.",),
            review_next=("Continue bounded review.",),
            constraints=("human_review_required",),
            boundary_text="",
        )

    def make_failed_source(self, state: str) -> ProviderRequestReview:
        return ProviderRequestReview(
            state=state,
            source_secret_boundary_state="",
            source_provider_config_state="",
            source_prompt_packet_state="",
            source_handoff_state="",
            source_implication_state="",
            source_readiness_state="",
            decision_id="", decision_hash="", decision_status="", bundle_id="", bundle_hash="",
            request_policy_material=(),
            blockers=("source request blocked",),
            warnings=("Source remains review-only.",),
            review_context=(),
            review_next=("Review the blocker.",),
            constraints=(),
            boundary_text="",
        )

    def make_output(self, source: ProviderRequestReview, **overrides: object) -> ProviderLiveReadinessReview:
        values: dict[str, object] = {
            "state": PROVIDER_LIVE_READINESS_REVIEW_READY,
            "source_provider_request_state": source.state,
            "source_secret_boundary_state": source.source_secret_boundary_state,
            "source_provider_config_state": source.source_provider_config_state,
            "source_prompt_packet_state": source.source_prompt_packet_state,
            "source_handoff_state": source.source_handoff_state,
            "source_implication_state": source.source_implication_state,
            "source_readiness_state": source.source_readiness_state,
            "decision_id": source.decision_id, "decision_hash": source.decision_hash,
            "decision_status": source.decision_status, "bundle_id": source.bundle_id,
            "bundle_hash": source.bundle_hash, "live_target_label": "unsafe",
            "future_provider_hint": "unsafe", "live_readiness_status": "unsafe",
            "live_readiness_policy_material": ("unsafe",), "blockers": (),
            "warnings": (), "review_context": source.review_context,
            "review_next": source.review_next, "constraints": (), "boundary_text": "unsafe",
        }
        values.update(overrides)
        return ProviderLiveReadinessReview(**values)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
