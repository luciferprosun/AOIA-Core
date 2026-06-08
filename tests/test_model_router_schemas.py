from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.schemas.model_router import (
    ModelCatalogEntry,
    ModelProviderProfile,
    ModelRoutingDecision,
    ModelSelectionApproval,
    ModelSelectionProposal,
    ModelTaskContext,
    ProviderClass,
    RoutingDecisionStatus,
    TaskSensitivity,
    TrustLevel,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "runtime" / "schemas" / "model_router.py"


class ModelRouterSchemaTests(unittest.TestCase):
    def _public_context(self) -> ModelTaskContext:
        return ModelTaskContext(
            task_id="task-1",
            sensitivity=TaskSensitivity.PUBLIC_DEV,
            prompt_summary_redacted="Public development prompt.",
            requester="human-reviewer",
        )

    def _canonical_context(self) -> ModelTaskContext:
        return ModelTaskContext(
            task_id="task-2",
            sensitivity=TaskSensitivity.CANONICAL,
            prompt_summary_redacted="Canonical task summary.",
            requester="human-reviewer",
            canonical_task=True,
        )

    def _proposal(self) -> ModelSelectionProposal:
        return ModelSelectionProposal(
            proposal_id="proposal-1",
            task_context=self._public_context(),
            requested_model_id="gemini-2.5-flash",
            requested_provider_id="gemini",
            provider_class=ProviderClass.GEMINI,
            trust_level=TrustLevel.THIRD_PARTY_PAID,
            rationale="Human should review remote provider use.",
        )

    def test_enums_have_expected_values(self) -> None:
        self.assertEqual(ProviderClass.GEMINI.value, "GEMINI")
        self.assertEqual(ProviderClass.OPENROUTER.value, "OPENROUTER")
        self.assertEqual(ProviderClass.OPENROUTER_FREE.value, "OPENROUTER_FREE")
        self.assertEqual(ProviderClass.PAID_MODEL.value, "PAID_MODEL")
        self.assertEqual(ProviderClass.LOCAL_MODEL.value, "LOCAL_MODEL")
        self.assertEqual(ProviderClass.DISABLED.value, "DISABLED")
        self.assertEqual(ProviderClass.UNKNOWN.value, "UNKNOWN")
        self.assertEqual(TrustLevel.LOCAL_ONLY.value, "LOCAL_ONLY")
        self.assertEqual(TaskSensitivity.SECRET_ADJACENT.value, "SECRET_ADJACENT")
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, "REQUIRES_HUMAN_APPROVAL")

    def test_provider_profile_defaults_are_disabled_and_noncanonical(self) -> None:
        profile = ModelProviderProfile(
            provider_id="gemini",
            display_name="Gemini",
            provider_class=ProviderClass.GEMINI,
            trust_level=TrustLevel.THIRD_PARTY_PAID,
        )

        self.assertFalse(profile.enabled)
        self.assertFalse(profile.allows_sensitive_tasks)
        self.assertFalse(profile.allows_canonical_tasks)
        self.assertEqual((), profile.notes)

    def test_provider_profile_is_frozen(self) -> None:
        profile = ModelProviderProfile(
            provider_id="local",
            display_name="Local model",
            provider_class=ProviderClass.LOCAL_MODEL,
            trust_level=TrustLevel.LOCAL_ONLY,
        )

        with self.assertRaises(FrozenInstanceError):
            profile.enabled = True

    def test_free_or_unknown_provider_rejects_sensitive_and_canonical_flags(self) -> None:
        for provider_class, trust_level in (
            (ProviderClass.OPENROUTER_FREE, TrustLevel.THIRD_PARTY_FREE),
            (ProviderClass.UNKNOWN, TrustLevel.UNKNOWN),
        ):
            with self.subTest(provider_class=provider_class):
                with self.assertRaises(ValueError):
                    ModelProviderProfile(
                        provider_id="provider",
                        display_name="Provider",
                        provider_class=provider_class,
                        trust_level=trust_level,
                        allows_sensitive_tasks=True,
                    )
                with self.assertRaises(ValueError):
                    ModelProviderProfile(
                        provider_id="provider",
                        display_name="Provider",
                        provider_class=provider_class,
                        trust_level=trust_level,
                        allows_canonical_tasks=True,
                    )

    def test_disabled_or_unknown_provider_cannot_be_enabled(self) -> None:
        for provider_class in (ProviderClass.DISABLED, ProviderClass.UNKNOWN):
            with self.subTest(provider_class=provider_class):
                with self.assertRaises(ValueError):
                    ModelProviderProfile(
                        provider_id="disabled-provider",
                        display_name="Disabled provider",
                        provider_class=provider_class,
                        trust_level=TrustLevel.UNKNOWN,
                        enabled=True,
                    )

    def test_local_provider_requires_local_only_trust(self) -> None:
        with self.assertRaises(ValueError):
            ModelProviderProfile(
                provider_id="local",
                display_name="Local model",
                provider_class=ProviderClass.LOCAL_MODEL,
                trust_level=TrustLevel.THIRD_PARTY_PAID,
            )

    def test_model_catalog_entry_rejects_free_sensitive_or_canonical_use(self) -> None:
        with self.assertRaises(ValueError):
            ModelCatalogEntry(
                model_id="free-model",
                display_name="Free model",
                provider_id="openrouter",
                provider_class=ProviderClass.OPENROUTER_FREE,
                trust_level=TrustLevel.THIRD_PARTY_FREE,
                free_tier=True,
                allows_sensitive_tasks=True,
            )
        with self.assertRaises(ValueError):
            ModelCatalogEntry(
                model_id="free-model",
                display_name="Free model",
                provider_id="openrouter",
                provider_class=ProviderClass.OPENROUTER_FREE,
                trust_level=TrustLevel.THIRD_PARTY_FREE,
                free_tier=True,
                allows_canonical_tasks=True,
            )

    def test_model_catalog_entry_rejects_free_and_paid_together(self) -> None:
        with self.assertRaises(ValueError):
            ModelCatalogEntry(
                model_id="confused-model",
                display_name="Confused model",
                provider_id="provider",
                provider_class=ProviderClass.OPENROUTER,
                trust_level=TrustLevel.THIRD_PARTY_PAID,
                free_tier=True,
                paid_tier=True,
            )

    def test_task_context_rejects_secret_or_execution_requests(self) -> None:
        with self.assertRaises(ValueError):
            ModelTaskContext(
                task_id="task-secret",
                sensitivity=TaskSensitivity.SENSITIVE,
                prompt_summary_redacted="Contains secret-adjacent material.",
                requester="human-reviewer",
                secret_bearing=True,
            )
        with self.assertRaises(ValueError):
            ModelTaskContext(
                task_id="task-exec",
                sensitivity=TaskSensitivity.PUBLIC_DEV,
                prompt_summary_redacted="Execution request.",
                requester="human-reviewer",
                execution_requested=True,
            )

    def test_model_selection_proposal_defaults_are_inert(self) -> None:
        proposal = self._proposal()

        self.assertEqual(RoutingDecisionStatus.PROPOSED, proposal.status)
        self.assertTrue(proposal.human_review_required)
        self.assertFalse(proposal.provider_call_permitted)
        self.assertFalse(proposal.automatic_fallback_permitted)
        self.assertFalse(proposal.execution_permitted)
        self.assertFalse(proposal.canonical_promotion_permitted)

    def test_model_selection_proposal_rejects_authority_flags(self) -> None:
        bad_flags = {
            "human_review_required": False,
            "provider_call_permitted": True,
            "automatic_fallback_permitted": True,
            "execution_permitted": True,
            "canonical_promotion_permitted": True,
            "status": RoutingDecisionStatus.APPROVED_BY_HUMAN,
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "proposal_id": "proposal-1",
                    "task_context": self._public_context(),
                    "requested_model_id": "model",
                    "requested_provider_id": "provider",
                    "provider_class": ProviderClass.GEMINI,
                    "trust_level": TrustLevel.THIRD_PARTY_PAID,
                    "rationale": "Review required.",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    ModelSelectionProposal(**kwargs)

    def test_secret_bearing_proposal_must_be_policy_rejected(self) -> None:
        secret_context = ModelTaskContext(
            task_id="task-secret",
            sensitivity=TaskSensitivity.SECRET_ADJACENT,
            prompt_summary_redacted="Secret-bearing prompt redacted.",
            requester="human-reviewer",
            secret_bearing=True,
        )

        with self.assertRaises(ValueError):
            ModelSelectionProposal(
                proposal_id="proposal-secret",
                task_context=secret_context,
                requested_model_id="model",
                requested_provider_id="provider",
                provider_class=ProviderClass.GEMINI,
                trust_level=TrustLevel.THIRD_PARTY_PAID,
                rationale="Must be blocked.",
            )

    def test_free_or_unknown_provider_cannot_be_proposed_for_canonical_tasks(self) -> None:
        for provider_class, trust_level in (
            (ProviderClass.OPENROUTER_FREE, TrustLevel.THIRD_PARTY_FREE),
            (ProviderClass.UNKNOWN, TrustLevel.UNKNOWN),
        ):
            with self.subTest(provider_class=provider_class):
                with self.assertRaises(ValueError):
                    ModelSelectionProposal(
                        proposal_id="proposal-canonical",
                        task_context=self._canonical_context(),
                        requested_model_id="model",
                        requested_provider_id="provider",
                        provider_class=provider_class,
                        trust_level=trust_level,
                        rationale="Canonical task cannot use free or unknown provider.",
                    )

    def test_approval_record_remains_non_calling(self) -> None:
        approval = ModelSelectionApproval(
            approval_id="approval-1",
            proposal_id="proposal-1",
            reviewer_human_id="human-reviewer",
            approved_provider_id="gemini",
            approved_model_id="gemini-2.5-flash",
            timestamp_utc="2026-06-08T10:00:00Z",
            approval_scope="proposal-only",
        )

        self.assertEqual(RoutingDecisionStatus.APPROVED_BY_HUMAN, approval.status)
        self.assertFalse(approval.provider_call_permitted)
        self.assertFalse(approval.automatic_fallback_permitted)
        self.assertFalse(approval.execution_permitted)
        self.assertFalse(approval.canonical_promotion_permitted)

    def test_approval_record_rejects_active_authority_flags(self) -> None:
        for field in (
            "provider_call_permitted",
            "automatic_fallback_permitted",
            "execution_permitted",
            "canonical_promotion_permitted",
        ):
            with self.subTest(field=field):
                kwargs = {
                    "approval_id": "approval-1",
                    "proposal_id": "proposal-1",
                    "reviewer_human_id": "human-reviewer",
                    "approved_provider_id": "gemini",
                    "approved_model_id": "gemini-2.5-flash",
                    "timestamp_utc": "2026-06-08T10:00:00Z",
                    "approval_scope": "proposal-only",
                    field: True,
                }
                with self.assertRaises(ValueError):
                    ModelSelectionApproval(**kwargs)

    def test_routing_decision_requires_review_and_audit_without_authority(self) -> None:
        decision = ModelRoutingDecision(
            decision_id="decision-1",
            proposal_id="proposal-1",
            provider_id="gemini",
            model_id="gemini-2.5-flash",
            reason="Human approval required before any future call.",
        )

        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL, decision.status)
        self.assertTrue(decision.human_review_required)
        self.assertTrue(decision.audit_log_required)
        self.assertFalse(decision.provider_call_permitted)
        self.assertFalse(decision.automatic_fallback_permitted)
        self.assertFalse(decision.execution_permitted)
        self.assertFalse(decision.canonical_promotion_permitted)

    def test_routing_decision_rejects_approval_or_authority_flags(self) -> None:
        bad_flags = {
            "status": RoutingDecisionStatus.APPROVED_BY_HUMAN,
            "human_review_required": False,
            "audit_log_required": False,
            "provider_call_permitted": True,
            "automatic_fallback_permitted": True,
            "execution_permitted": True,
            "canonical_promotion_permitted": True,
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "decision_id": "decision-1",
                    "proposal_id": "proposal-1",
                    "provider_id": "gemini",
                    "model_id": "gemini-2.5-flash",
                    "reason": "No active routing.",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    ModelRoutingDecision(**kwargs)

    def test_no_execution_like_methods_exist(self) -> None:
        objects = (
            ModelProviderProfile(
                provider_id="gemini",
                display_name="Gemini",
                provider_class=ProviderClass.GEMINI,
                trust_level=TrustLevel.THIRD_PARTY_PAID,
            ),
            ModelCatalogEntry(
                model_id="gemini-2.5-flash",
                display_name="Gemini Flash",
                provider_id="gemini",
                provider_class=ProviderClass.GEMINI,
                trust_level=TrustLevel.THIRD_PARTY_PAID,
            ),
            self._public_context(),
            self._proposal(),
            ModelSelectionApproval(
                approval_id="approval-1",
                proposal_id="proposal-1",
                reviewer_human_id="human-reviewer",
                approved_provider_id="gemini",
                approved_model_id="gemini-2.5-flash",
                timestamp_utc="2026-06-08T10:00:00Z",
                approval_scope="proposal-only",
            ),
            ModelRoutingDecision(
                decision_id="decision-1",
                proposal_id="proposal-1",
                provider_id="gemini",
                model_id="gemini-2.5-flash",
                reason="Human approval required.",
            ),
        )
        forbidden_methods = (
            "run",
            "execute",
            "route",
            "call",
            "call_model",
            "fallback",
            "health_check",
            "promote",
            "canonicalize",
            "commit",
            "push",
            "open_browser",
        )
        for item in objects:
            for method_name in forbidden_methods:
                with self.subTest(item=type(item).__name__, method=method_name):
                    self.assertFalse(callable(getattr(item, method_name, None)))

    def test_schema_module_contains_no_forbidden_implementation_imports_or_terms(self) -> None:
        source = SCHEMA_PATH.read_text(encoding="utf-8")
        forbidden_terms = (
            "subprocess",
            "os.system",
            "Popen",
            "requests",
            "httpx",
            "urllib",
            "exec(",
            "eval(",
            "openai",
            "anthropic",
            "google",
            "browser_tools",
            "web_reader",
            "shell_tools",
            "def run",
            "def execute",
            "def route",
            "def call_model",
            "def health_check",
            "def promote",
            "def canonicalize",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
