from __future__ import annotations

import unittest

from runtime.model_router import (
    create_model_selection_proposal,
    evaluate_model_selection_policy,
    execute_approved_model_call_once,
)
from runtime.provider_clients import ProviderCallResult
from runtime.schemas.model_router import RoutingDecisionStatus, TaskSensitivity


class M1RouterBoundaryChecks(unittest.TestCase):
    def test_selection_proposal_is_metadata_not_provider_execution(self) -> None:
        proposal = create_model_selection_proposal(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public reviewer prompt",
        )
        decision = evaluate_model_selection_policy(proposal=proposal)

        self.assertEqual(RoutingDecisionStatus.PROPOSED.value, proposal["status"])
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, decision["status"])
        self.assertTrue(proposal["human_review_required"])
        self.assertFalse(proposal["provider_call_permitted"])
        self.assertFalse(decision["provider_call_permitted"])
        self.assertFalse(proposal["automatic_fallback_permitted"])
        self.assertFalse(proposal["execution_permitted"])
        self.assertFalse(proposal["canonical_promotion_permitted"])
        self.assertNotIn("output_text", proposal)
        self.assertNotIn("call_made", proposal)

    def test_call_path_blocks_before_provider_without_human_approval(self) -> None:
        provider_invocations: list[dict[str, object]] = []

        def fail_if_invoked(**kwargs):
            provider_invocations.append(kwargs)
            self.fail("provider call function must not be invoked without human approval")

        result = execute_approved_model_call_once(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public reviewer prompt",
            human_approved=False,
            provider_call_func=fail_if_invoked,
        )

        self.assertEqual([], provider_invocations)
        self.assertFalse(result["call_made"])
        self.assertFalse(result["output_trusted"])
        self.assertFalse(result["approval"]["provider_call_permitted"])
        self.assertFalse(result["automatic_fallback_used"])
        self.assertFalse(result["execution_triggered"])
        self.assertFalse(result["canonical_promotion_triggered"])

    def test_policy_rejection_blocks_provider_even_with_human_approval_flag(self) -> None:
        provider_invocations: list[dict[str, object]] = []

        def fail_if_invoked(**kwargs):
            provider_invocations.append(kwargs)
            self.fail("policy-rejected route must not invoke provider call function")

        result = execute_approved_model_call_once(
            provider_id="openrouter",
            model_id="openrouter/free",
            task_sensitivity=TaskSensitivity.SENSITIVE.value,
            user_prompt="sensitive reviewer prompt",
            human_approved=True,
            provider_call_func=fail_if_invoked,
        )

        self.assertEqual([], provider_invocations)
        self.assertFalse(result["call_made"])
        self.assertFalse(result["output_trusted"])
        self.assertEqual(RoutingDecisionStatus.REJECTED_BY_POLICY.value, result["decision"]["status"])
        self.assertFalse(result["approval"]["provider_call_permitted"])
        self.assertFalse(result["audit_event"]["call_made"])
        self.assertFalse(result["audit_event"]["provider_output_trusted"])

    def test_openrouter_free_generic_route_is_blocked_for_sensitive_canonical_and_secret_adjacent(self) -> None:
        for sensitivity in (
            TaskSensitivity.SENSITIVE,
            TaskSensitivity.CANONICAL,
            TaskSensitivity.SECRET_ADJACENT,
        ):
            with self.subTest(sensitivity=sensitivity.value):
                proposal = create_model_selection_proposal(
                    provider_id="openrouter",
                    model_id="openrouter/free",
                    task_sensitivity=sensitivity.value,
                    user_prompt="reviewer prompt",
                )
                decision = evaluate_model_selection_policy(proposal=proposal)

                self.assertEqual(RoutingDecisionStatus.REJECTED_BY_POLICY.value, decision["status"])
                self.assertFalse(decision["provider_call_permitted"])
                self.assertFalse(decision["automatic_fallback_permitted"])
                self.assertFalse(decision["execution_permitted"])
                self.assertFalse(decision["canonical_promotion_permitted"])

    def test_approved_mock_provider_output_remains_untrusted_and_non_authoritative(self) -> None:
        provider_invocations: list[dict[str, object]] = []

        def fake_provider_call(**kwargs):
            provider_invocations.append(kwargs)
            return ProviderCallResult(
                provider_id=str(kwargs["provider_id"]),
                model_id=str(kwargs["model_id"]),
                call_made=True,
                output_text="mock provider proposal text",
                output_trusted=False,
            )

        result = execute_approved_model_call_once(
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
            user_prompt="public reviewer prompt",
            human_approved=True,
            provider_call_func=fake_provider_call,
        )

        self.assertEqual(1, len(provider_invocations))
        self.assertTrue(result["call_made"])
        self.assertEqual("mock provider proposal text", result["output_text"])
        self.assertFalse(result["output_trusted"])
        self.assertFalse(result["audit_event"]["provider_output_trusted"])
        self.assertFalse(result["automatic_fallback_used"])
        self.assertFalse(result["execution_triggered"])
        self.assertFalse(result["canonical_promotion_triggered"])


if __name__ == "__main__":
    unittest.main()
