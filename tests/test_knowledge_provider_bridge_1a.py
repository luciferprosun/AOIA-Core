from __future__ import annotations

import unittest

from runtime.knowledge_modules.citation_validation import (
    NO_KNOWLEDGE_MODULE_SELECTED,
    PROVIDER_OUTPUT_MALFORMED,
    PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
    RETRIEVAL_FAILED_CLOSED,
)
from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.provider_bridge import KnowledgeProviderBridge1A
from runtime.providers.contracts import DRY_RUN_PREVIEW, ProviderRuntimeResult
from tests.knowledge_context_test_support_1a import (
    context_fixture,
    runtime_result,
    structured_answer_payload,
    target,
    zero_module_fixture,
)


class KnowledgeProviderBridge1ATests(unittest.TestCase):
    def test_zero_module_dry_run_is_valid_and_explicitly_ungrounded(self):
        fixture = zero_module_fixture()
        result = KnowledgeProviderBridge1A(fixture.hub).execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations={},
            provider_target=target(),
        )
        self.assertEqual(result.selected_module_ids, ())
        self.assertEqual(result.knowledge_grounding_status, NO_KNOWLEDGE_MODULE_SELECTED)
        self.assertIsNone(result.structured_answer)
        self.assertEqual(result.provider_invocation_count, 1)

    def test_strict_structured_response_uses_exact_context_and_citations(self):
        fixture = context_fixture()
        calls = []

        def runner(envelope, **kwargs):
            calls.append((envelope, kwargs))
            return runtime_result(
                structured_answer_payload(fixture.package),
                status=DRY_RUN_PREVIEW,
            )

        result = KnowledgeProviderBridge1A(fixture.hub, provider_runner=runner).execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0][1]["live"])
        self.assertFalse(calls[0][1]["acknowledge_live_provider_test"])
        self.assertEqual(calls[0][1]["activation_status"].value, "dry_run_only")
        self.assertEqual(
            result.citation_validation.status,
            PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
        )
        self.assertEqual(result.context_package_hash, fixture.package.context_package_hash)
        self.assertEqual(result.provider_invocation_count, 1)

    def test_retrieval_failure_blocks_provider_invocation_and_never_falls_back(self):
        fixture = context_fixture(include_failure=True)
        calls = []

        def runner(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("provider must not run")

        result = KnowledgeProviderBridge1A(fixture.hub, provider_runner=runner).execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        self.assertEqual(calls, [])
        self.assertEqual(result.provider_status, RETRIEVAL_FAILED_CLOSED)
        self.assertEqual(result.provider_invocation_count, 0)
        self.assertIsNone(result.request_id)

    def test_unrelated_explicit_module_may_continue_with_failure_exposed(self):
        fixture = context_fixture(
            ("failed-module-1a", "good-module-1a"), include_failure=True
        )
        good = fixture.package.module_sections[1].evidence_items[0]
        calls = []

        def runner(envelope, **kwargs):
            calls.append((envelope, kwargs))
            return runtime_result(
                structured_answer_payload(
                    fixture.package,
                    evidence_id=good.evidence_id,
                    module_id=good.module_id,
                ),
                status=DRY_RUN_PREVIEW,
            )

        result = KnowledgeProviderBridge1A(fixture.hub, provider_runner=runner).execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.citation_validation.status, PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED)
        self.assertEqual(len(result.module_failures), 1)
        self.assertEqual(result.module_failures[0].module_id, "failed-module-1a")

    def test_malformed_provider_output_is_not_repaired_or_retried(self):
        fixture = context_fixture()
        calls = []

        def runner(envelope, **kwargs):
            calls.append((envelope, kwargs))
            return runtime_result("```json\n{}\n```", status=DRY_RUN_PREVIEW)

        result = KnowledgeProviderBridge1A(fixture.hub, provider_runner=runner).execute(
            profile=fixture.profile,
            query=fixture.query,
            instance_configurations=fixture.configurations,
            provider_target=target(),
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.provider_status, PROVIDER_OUTPUT_MALFORMED)
        self.assertIsNone(result.structured_answer)

    def test_runtime_provider_or_model_identity_mismatch_fails_closed(self):
        fixture = context_fixture()

        def runner(envelope, **kwargs):
            del envelope, kwargs
            return ProviderRuntimeResult(
                provider_id="gemini_chat",
                model_id="wrong-model",
                mode="dry_run",
                status=DRY_RUN_PREVIEW,
                redacted_request_preview="{}",
            )

        with self.assertRaises(KnowledgeModuleError) as caught:
            KnowledgeProviderBridge1A(fixture.hub, provider_runner=runner).execute(
                profile=fixture.profile,
                query=fixture.query,
                instance_configurations=fixture.configurations,
                provider_target=target(),
            )
        self.assertEqual(caught.exception.status, PROVIDER_OUTPUT_MALFORMED)


if __name__ == "__main__":
    unittest.main()
