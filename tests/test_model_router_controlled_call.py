from __future__ import annotations

import unittest

from runtime.model_router import (
    approve_model_selection,
    create_model_selection_proposal,
    evaluate_model_selection_policy,
    execute_approved_model_call_once,
)
from runtime.provider_clients import ProviderCallResult
from runtime.schemas.model_router import RoutingDecisionStatus, TaskSensitivity


class ModelRouterControlledCallTests(unittest.TestCase):
    def _proposal(self) -> dict[str, object]:
        return create_model_selection_proposal(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public test prompt",
        )

    def test_proposal_requires_human_approval_and_does_not_permit_call(self) -> None:
        proposal = self._proposal()
        decision = evaluate_model_selection_policy(proposal=proposal)

        self.assertTrue(proposal["human_review_required"])
        self.assertFalse(proposal["provider_call_permitted"])
        self.assertFalse(proposal["automatic_fallback_permitted"])
        self.assertEqual(RoutingDecisionStatus.PROPOSED.value, proposal["status"])
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, decision["status"])
        self.assertFalse(decision["provider_call_permitted"])

    def test_no_provider_call_without_approval(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_call(**kwargs):
            calls.append(kwargs)
            return ProviderCallResult(
                provider_id=kwargs["provider_id"],
                model_id=kwargs["model_id"],
                call_made=True,
                output_text="should not happen",
            )

        result = execute_approved_model_call_once(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public test prompt",
            human_approved=False,
            provider_call_func=fake_call,
        )

        self.assertEqual([], calls)
        self.assertFalse(result["call_made"])
        self.assertFalse(result["output_trusted"])
        self.assertIn("human approval", result["error"])

    def test_no_provider_call_when_policy_blocks_provider_call_permission(self) -> None:
        calls: list[dict[str, object]] = []

        result = execute_approved_model_call_once(
            provider_id="openrouter",
            model_id="openrouter/free",
            task_sensitivity=TaskSensitivity.SENSITIVE.value,
            user_prompt="sensitive prompt",
            human_approved=True,
            provider_call_func=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual([], calls)
        self.assertFalse(result["call_made"])
        self.assertFalse(result["output_trusted"])
        self.assertEqual(RoutingDecisionStatus.REJECTED_BY_POLICY.value, result["decision"]["status"])

    def test_approval_result_permits_only_one_selected_call_after_policy_review(self) -> None:
        proposal = self._proposal()
        decision = evaluate_model_selection_policy(proposal=proposal)
        approval = approve_model_selection(
            proposal=proposal,
            decision=decision,
            human_approved=True,
        )

        self.assertTrue(approval["human_approved"])
        self.assertTrue(approval["provider_call_permitted"])
        self.assertFalse(approval["automatic_fallback_permitted"])
        self.assertFalse(approval["execution_permitted"])
        self.assertFalse(approval["canonical_promotion_permitted"])

    def test_approved_call_uses_mocked_provider_once_and_keeps_output_untrusted(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_call(**kwargs):
            calls.append(kwargs)
            return ProviderCallResult(
                provider_id=kwargs["provider_id"],
                model_id=kwargs["model_id"],
                call_made=True,
                output_text="mocked provider output",
                output_trusted=False,
            )

        result = execute_approved_model_call_once(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public test prompt",
            human_approved=True,
            provider_call_func=fake_call,
        )

        self.assertEqual(1, len(calls))
        self.assertTrue(result["call_made"])
        self.assertEqual("mocked provider output", result["output_text"])
        self.assertFalse(result["output_trusted"])
        self.assertFalse(result["automatic_fallback_used"])
        self.assertFalse(result["execution_triggered"])
        self.assertFalse(result["canonical_promotion_triggered"])
        self.assertFalse(result["audit_event"]["provider_output_trusted"])

    def test_openrouter_free_rejected_for_sensitive_canonical_and_secret_adjacent(self) -> None:
        for sensitivity in (
            TaskSensitivity.SENSITIVE,
            TaskSensitivity.CANONICAL,
            TaskSensitivity.SECRET_ADJACENT,
        ):
            with self.subTest(sensitivity=sensitivity):
                proposal = create_model_selection_proposal(
                    provider_id="openrouter",
                    model_id="openrouter/free",
                    task_sensitivity=sensitivity.value,
                    user_prompt="test prompt",
                )
                decision = evaluate_model_selection_policy(proposal=proposal)
                self.assertEqual(RoutingDecisionStatus.REJECTED_BY_POLICY.value, decision["status"])

    def test_generic_openrouter_free_route_is_not_callable_without_exact_model_id(self) -> None:
        proposal = create_model_selection_proposal(
            provider_id="openrouter",
            model_id="openrouter/free",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public test prompt",
        )
        decision = evaluate_model_selection_policy(proposal=proposal)

        self.assertEqual(RoutingDecisionStatus.REJECTED_BY_POLICY.value, decision["status"])
        self.assertIn("exact model IDs", decision["reason"])

    def test_unknown_or_disabled_provider_is_rejected(self) -> None:
        cases = (
            ("missing", "missing/model"),
            ("disabled", "disabled/unknown-provider"),
        )
        for provider_id, model_id in cases:
            with self.subTest(provider_id=provider_id):
                proposal = create_model_selection_proposal(
                    provider_id=provider_id,
                    model_id=model_id,
                    task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
                    user_prompt="public test prompt",
                )
                decision = evaluate_model_selection_policy(proposal=proposal)
                self.assertEqual(RoutingDecisionStatus.DISABLED.value, decision["status"])

    def test_no_automatic_fallback_fields_are_enabled(self) -> None:
        result = execute_approved_model_call_once(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public test prompt",
            human_approved=False,
        )

        self.assertFalse(result["proposal"]["automatic_fallback_permitted"])
        self.assertFalse(result["decision"]["automatic_fallback_permitted"])
        self.assertFalse(result["approval"]["automatic_fallback_permitted"])
        self.assertFalse(result["automatic_fallback_used"])


if __name__ == "__main__":
    unittest.main()
