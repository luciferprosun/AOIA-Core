from __future__ import annotations

import unittest
from dataclasses import replace

from runtime.knowledge_modules.citation_validation import citation_status_result
from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.provider_bridge import KnowledgeProviderBridge1A
from runtime.knowledge_modules.provider_result import (
    PROVIDER_RESULT_SCHEMA_VERSION,
    KnowledgeProviderResult,
)
from tests.knowledge_context_test_support_1a import context_fixture, target


class KnowledgeProviderResult1ATests(unittest.TestCase):
    def test_dry_run_result_is_deterministic_and_non_authoritative(self):
        fixture = context_fixture()
        bridge = KnowledgeProviderBridge1A(fixture.hub)
        first = bridge.execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        second = bridge.execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.authority_status, "NON_AUTHORITATIVE_PROVIDER_OUTPUT")
        self.assertEqual(first.knowledge_grounding_status, "KNOWLEDGE_CONTEXT_PREPARED")
        for name in (
            "can_approve", "can_write", "can_execute", "can_commit", "can_push",
            "can_call_provider", "can_call_tools", "can_change_gate",
            "can_satisfy_human_barrier", "gate_satisfied",
        ):
            self.assertFalse(getattr(first, name))

    def test_result_rejects_authority_and_request_binding_mismatch(self):
        fixture = context_fixture()
        result = KnowledgeProviderBridge1A(fixture.hub).execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        with self.assertRaises(KnowledgeModuleError):
            replace(result, can_approve=True, result_id="", result_hash="")
        with self.assertRaises(KnowledgeModuleError):
            KnowledgeProviderResult(
                schema_version=PROVIDER_RESULT_SCHEMA_VERSION,
                result_id="",
                request_id="request",
                request_hash="a" * 64,
                provider_target_hash=target().target_hash,
                provider_id="openrouter_chat",
                model_id="reviewed-model-1",
                knowledge_profile_id=fixture.package.knowledge_profile_id,
                knowledge_profile_hash=fixture.package.knowledge_profile_hash,
                selected_module_ids=fixture.package.selected_module_ids,
                selected_instance_ids=fixture.package.selected_instance_ids,
                composite_bundle_hash=fixture.package.composite_bundle_hash,
                context_package_hash=fixture.package.context_package_hash,
                provider_request_hash="b" * 64,
                provider_status="DRY_RUN_ONLY",
                structured_answer=None,
                citation_validation=citation_status_result("DRY_RUN_ONLY", fixture.package),
                warnings=(),
                module_failures=(),
                knowledge_grounding_status="DRY_RUN_ONLY",
                provider_invocation_count=1,
            )


if __name__ == "__main__":
    unittest.main()
