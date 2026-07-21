from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace

from runtime.epistemic_orchestra.canonical import canonical_sha256
from runtime.epistemic_orchestra.live_run_preview import build_live_run_preview
from runtime.epistemic_orchestra.live_session import (
    LiveSessionError,
    LiveSessionUseRegistry,
    LiveStageExecutionError,
    consume_live_stage_authorization,
    run_live_orchestra_session,
)
from runtime.epistemic_orchestra.role_binding import (
    OrchestraOperatorRole,
    build_model_role_assignment,
    build_orchestra_role_selection,
)
from runtime.providers.model_profiles import ModelProfile
from runtime.providers.user_connections import ProviderConnection


NO_ISSUES = '{"critic_outcome":"NO_MATERIAL_ISSUE_FOUND","issues":[]}'


class _MockExactInvoker:
    def __init__(
        self,
        *,
        fail_at: int | None = None,
        non_boolean_authority: bool = False,
        mismatched_binding: bool = False,
    ) -> None:
        self.calls: list[dict] = []
        self.fail_at = fail_at
        self.non_boolean_authority = non_boolean_authority
        self.mismatched_binding = mismatched_binding

    def __call__(self, **kwargs):
        consume_live_stage_authorization(
            kwargs["stage_authorization"],
            binding=kwargs["binding"],
            provider_prompt=kwargs["prompt"],
            max_tokens=kwargs["max_tokens"],
            timeout_seconds=kwargs["timeout_seconds"],
        )
        self.calls.append(kwargs)
        if self.fail_at == len(self.calls) - 1:
            raise TimeoutError("one exact attempt failed")
        role = kwargs["binding"].operator_role
        if role == OrchestraOperatorRole.MAIN.value:
            response = "Initial untrusted draft"
        elif role in (OrchestraOperatorRole.CRITIC.value, OrchestraOperatorRole.AUDITOR.value):
            response = NO_ISSUES
        else:
            response = "Synthesized non-authoritative draft"
        return SimpleNamespace(
            binding_hash=(
                "0" * 64
                if self.mismatched_binding
                else kwargs["binding"].binding_hash
            ),
            connection_id=kwargs["binding"].connection_id,
            model_profile_id=kwargs["binding"].model_profile_id,
            remote_model_id=kwargs["binding"].remote_model_id,
            response_text=response,
            trust_status="UNTRUSTED",
            authority_status="NON_AUTHORITATIVE",
            authoritative=0 if self.non_boolean_authority else False,
            can_approve=False,
            can_write=False,
            can_execute=False,
            can_satisfy_gate=False,
        )


class OrchestraLiveSessionBoundary1ATests(unittest.TestCase):
    def make_contracts(self, roles: tuple[str, ...]):
        connection = ProviderConnection(
            connection_id="live-connection",
            display_name="Live Connection",
            api_style="openai_compatible",
            base_url="https://models.example.test/v1",
            native_adapter_id=None,
            credential_reference="live-credential",
            enabled=True,
            created_at="operator-time",
        )
        profiles = tuple(
            ModelProfile(
                model_profile_id=f"live-model-{index}",
                connection_id=connection.connection_id,
                display_name=f"Live Model {index}",
                remote_model_id=f"vendor/live-{index}",
                enabled=True,
                allowed_roles=(role,),
            )
            for index, role in enumerate(roles)
        )
        assignments = tuple(
            build_model_role_assignment(
                ordinal=index,
                connection=connection,
                model_profile=profile,
                role=role,
            )
            for index, (profile, role) in enumerate(zip(profiles, roles))
        )
        selection = build_orchestra_role_selection(assignments)
        source_prompt = "Explain the bounded demo safely."
        run, preview = build_live_run_preview(
            orchestra_run_id=f"live-run-{len(roles)}",
            source_prompt=source_prompt,
            role_selection=selection,
            timeout_seconds=8,
            maximum_output_tokens=80,
            expires_at_epoch=200,
        )
        registry = LiveSessionUseRegistry()
        confirmation = registry.issue_confirmation(
            preview=preview,
            confirmed_preview_hash=preview.preview_hash,
            explicit_run_action=True,
            issued_at_epoch=100,
        )
        return source_prompt, run, preview, selection, registry, confirmation

    def run_flow(self, roles: tuple[str, ...], invoker: _MockExactInvoker | None = None):
        source, run, preview, selection, registry, confirmation = self.make_contracts(roles)
        exact = invoker or _MockExactInvoker()
        result = run_live_orchestra_session(
            run=run,
            preview=preview,
            source_prompt=source,
            role_selection=selection,
            confirmation=confirmation,
            registry=registry,
            current_epoch=100,
            exact_invoker=exact,
        )
        return result, exact, (source, run, preview, selection, registry, confirmation)

    def test_two_model_flow_calls_main_then_critic_and_keeps_final_inert(self) -> None:
        result, invoker, state = self.run_flow(("MAIN", "CRITIC"))
        self.assertEqual(2, len(invoker.calls))
        self.assertEqual(("MAIN", "CRITIC"), tuple(call["binding"].operator_role for call in invoker.calls))
        self.assertIn("Initial untrusted draft", invoker.calls[1]["prompt"])
        self.assertIn("UNTRUSTED_CONTEXT_JSON", invoker.calls[1]["prompt"])
        self.assertEqual("Initial untrusted draft", result.final_draft)
        self.assertFalse(result.synthesis_performed)
        self.assertEqual(3, len(result.stage_chain))
        registry = state[4]
        self.assertEqual({}, registry._issued_confirmations)
        self.assertEqual({}, registry._claimed_confirmations)
        self.assertEqual({}, registry._issued_stage_authorizations)
        self.assertEqual({}, registry._consumed_stage_authorizations)

    def test_three_model_auditor_receives_main_and_prior_critic_results(self) -> None:
        result, invoker, _state = self.run_flow(("MAIN", "CRITIC", "AUDITOR"))
        self.assertEqual(3, len(invoker.calls))
        auditor_prompt = invoker.calls[2]["prompt"]
        self.assertIn("Initial untrusted draft", auditor_prompt)
        self.assertIn("critic_responses", auditor_prompt)
        self.assertIn("NO_MATERIAL_ISSUE_FOUND", auditor_prompt)
        self.assertFalse(result.stage_results[2].critic_payload.provider_output_is_authority)

    def test_five_model_flow_synthesizes_only_a_non_authoritative_draft(self) -> None:
        roles = ("MAIN", "CRITIC", "CRITIC", "AUDITOR", "SYNTHESIZER")
        result, invoker, _state = self.run_flow(roles)
        self.assertEqual(5, len(invoker.calls))
        self.assertEqual(roles, tuple(call["binding"].operator_role for call in invoker.calls))
        self.assertEqual("Synthesized non-authoritative draft", result.final_draft)
        self.assertTrue(result.synthesis_performed)
        self.assertFalse(result.synthesis_output_is_authority)
        self.assertTrue(result.human_review_required)
        self.assertFalse(result.execution_permitted)
        self.assertFalse(result.write_permitted)

    def test_confirmation_must_match_exact_preview_and_actual_boolean_action(self) -> None:
        _source, _run, preview, _selection, registry, _confirmation = self.make_contracts(
            ("MAIN", "CRITIC")
        )
        with self.assertRaisesRegex(LiveSessionError, "exact preview"):
            registry.issue_confirmation(
                preview=preview,
                confirmed_preview_hash="0" * 64,
                explicit_run_action=True,
                issued_at_epoch=100,
            )
        with self.assertRaisesRegex(LiveSessionError, "explicit Run"):
            LiveSessionUseRegistry().issue_confirmation(
                preview=preview,
                confirmed_preview_hash=preview.preview_hash,
                explicit_run_action=1,  # type: ignore[arg-type]
                issued_at_epoch=100,
            )

    def test_one_preview_can_issue_only_one_confirmation(self) -> None:
        _source, _run, preview, _selection, registry, _confirmation = self.make_contracts(
            ("MAIN", "CRITIC")
        )
        with self.assertRaisesRegex(LiveSessionError, "already has"):
            registry.issue_confirmation(
                preview=preview,
                confirmed_preview_hash=preview.preview_hash,
                explicit_run_action=True,
                issued_at_epoch=100,
            )

    def test_stale_confirmation_fails_before_any_call(self) -> None:
        source, run, preview, selection, registry, confirmation = self.make_contracts(
            ("MAIN", "CRITIC")
        )
        invoker = _MockExactInvoker()
        with self.assertRaisesRegex(LiveSessionError, "stale or expired"):
            run_live_orchestra_session(
                run=run,
                preview=preview,
                source_prompt=source,
                role_selection=selection,
                confirmation=confirmation,
                registry=registry,
                current_epoch=201,
                exact_invoker=invoker,
            )
        self.assertEqual([], invoker.calls)

    def test_changed_selection_invalidates_preview_before_any_call(self) -> None:
        source, run, preview, selection, registry, confirmation = self.make_contracts(
            ("MAIN", "CRITIC")
        )
        changed_assignment = replace(
            selection.assignments[1],
            remote_model_id="vendor/changed",
            role_assignment_hash="",
        )
        changed_selection = replace(
            selection,
            assignments=(selection.assignments[0], changed_assignment),
            role_selection_hash="",
        )
        invoker = _MockExactInvoker()
        with self.assertRaisesRegex(Exception, "preview"):
            run_live_orchestra_session(
                run=run,
                preview=preview,
                source_prompt=source,
                role_selection=changed_selection,
                confirmation=confirmation,
                registry=registry,
                current_epoch=100,
                exact_invoker=invoker,
            )
        self.assertEqual([], invoker.calls)

    def test_session_is_consumed_before_failure_and_has_no_automatic_retry(self) -> None:
        source, run, preview, selection, registry, confirmation = self.make_contracts(
            ("MAIN", "CRITIC")
        )
        invoker = _MockExactInvoker(fail_at=0)
        with self.assertRaises(LiveStageExecutionError) as caught:
            run_live_orchestra_session(
                run=run,
                preview=preview,
                source_prompt=source,
                role_selection=selection,
                confirmation=confirmation,
                registry=registry,
                current_epoch=100,
                exact_invoker=invoker,
            )
        self.assertEqual(
            {
                "stage_id": preview.planned_calls[0].stage_id,
                "call_index": 0,
                "operator_role": "MAIN",
                "connection_id": "live-connection",
                "model_profile_id": "live-model-0",
            },
            {
                name: caught.exception.to_dict()[name]
                for name in (
                    "stage_id",
                    "call_index",
                    "operator_role",
                    "connection_id",
                    "model_profile_id",
                )
            },
        )
        self.assertNotIn("one exact attempt", str(caught.exception))
        self.assertEqual({}, registry._claimed_confirmations)
        self.assertEqual({}, registry._issued_stage_authorizations)
        self.assertEqual({}, registry._consumed_stage_authorizations)
        self.assertEqual(1, len(invoker.calls))
        with self.assertRaisesRegex(LiveSessionError, "already been consumed"):
            run_live_orchestra_session(
                run=run,
                preview=preview,
                source_prompt=source,
                role_selection=selection,
                confirmation=confirmation,
                registry=registry,
                current_epoch=100,
                exact_invoker=invoker,
            )
        self.assertEqual(1, len(invoker.calls))

    def test_every_call_is_hash_bound_to_exact_run_stage_model_role_and_parent(self) -> None:
        result, invoker, _state = self.run_flow(("MAIN", "CRITIC", "AUDITOR"))
        for stage_result, call in zip(result.stage_results, invoker.calls):
            binding = call["binding"]
            self.assertEqual(result.orchestra_run_id, binding.orchestra_run_id)
            self.assertEqual(result.run_hash, binding.run_hash)
            self.assertEqual(stage_result.binding.binding_hash, binding.binding_hash)
            self.assertEqual(call["max_tokens"], binding.maximum_output_tokens)
            self.assertEqual(call["timeout_seconds"], binding.timeout_seconds)
            self.assertEqual(64, len(binding.connection_revision_hash))
            self.assertEqual(64, len(binding.model_revision_hash))
            self.assertEqual(64, len(binding.role_assignment_hash))
            self.assertEqual(64, len(binding.source_prompt_hash))
            self.assertEqual(64, len(binding.parent_response_hash))

    def test_non_boolean_provider_authority_value_fails_closed(self) -> None:
        invoker = _MockExactInvoker(non_boolean_authority=True)
        with self.assertRaises(LiveStageExecutionError) as caught:
            self.run_flow(("MAIN", "CRITIC"), invoker=invoker)
        self.assertIn("authoritative differs", str(caught.exception.__cause__))
        self.assertEqual(1, len(invoker.calls))

    def test_cross_stage_or_cached_result_binding_fails_closed(self) -> None:
        invoker = _MockExactInvoker(mismatched_binding=True)
        with self.assertRaises(LiveStageExecutionError) as caught:
            self.run_flow(("MAIN", "CRITIC"), invoker=invoker)
        self.assertIn("binding_hash differs", str(caught.exception.__cause__))
        self.assertEqual(1, len(invoker.calls))

    def test_auditor_before_critic_is_rejected(self) -> None:
        connection = ProviderConnection(
            connection_id="order-connection",
            display_name="Order Connection",
            api_style="openai_compatible",
            base_url="https://models.example.test/v1",
            native_adapter_id=None,
            credential_reference="order-key",
            enabled=True,
            created_at="operator-time",
        )
        roles = ("MAIN", "AUDITOR", "CRITIC")
        profiles = tuple(
            ModelProfile(
                model_profile_id=f"order-{index}",
                connection_id=connection.connection_id,
                display_name=f"Order {index}",
                remote_model_id=f"vendor/order-{index}",
                enabled=True,
                allowed_roles=(role,),
            )
            for index, role in enumerate(roles)
        )
        assignments = tuple(
            build_model_role_assignment(
                ordinal=index,
                connection=connection,
                model_profile=profile,
                role=role,
            )
            for index, (profile, role) in enumerate(zip(profiles, roles))
        )
        with self.assertRaisesRegex(Exception, "CRITIC stages must precede AUDITOR"):
            build_orchestra_role_selection(assignments)


if __name__ == "__main__":
    unittest.main()
