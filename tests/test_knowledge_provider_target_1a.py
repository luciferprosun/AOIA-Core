from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.provider_target import PROVIDER_TARGET_SCHEMA_VERSION, ProviderTarget


class KnowledgeProviderTarget1ATests(unittest.TestCase):
    def test_target_is_explicit_dry_run_and_contains_no_secret_or_endpoint_fields(self):
        target = ProviderTarget(
            schema_version=PROVIDER_TARGET_SCHEMA_VERSION,
            provider_id="openrouter_chat",
            model_id="explicit-model",
        )
        self.assertTrue(target.dry_run)
        self.assertFalse(target.live_call_requested)
        payload = target.to_dict()
        self.assertNotIn("api_key", payload)
        self.assertNotIn("endpoint", payload)
        self.assertNotIn("headers", payload)
        self.assertNotIn("fallback_provider", payload)

    def test_target_rejects_unknown_fields_and_conflicting_live_flags(self):
        with self.assertRaises(KnowledgeModuleError):
            ProviderTarget.from_dict({
                "schema_version": PROVIDER_TARGET_SCHEMA_VERSION,
                "provider_id": "openrouter_chat",
                "model_id": "m",
                "endpoint": "https://attacker.invalid",
            })
        with self.assertRaises(KnowledgeModuleError):
            ProviderTarget(
                schema_version=PROVIDER_TARGET_SCHEMA_VERSION,
                provider_id="openrouter_chat",
                model_id="m",
                live_call_requested=True,
                dry_run=True,
            )

    def test_target_hash_is_stable_and_changes_with_provider(self):
        first = ProviderTarget(PROVIDER_TARGET_SCHEMA_VERSION, "openrouter_chat", "m")
        second = ProviderTarget(PROVIDER_TARGET_SCHEMA_VERSION, "openrouter_chat", "m")
        third = ProviderTarget(PROVIDER_TARGET_SCHEMA_VERSION, "gemini_chat", "m")
        self.assertEqual(first.target_hash, second.target_hash)
        self.assertNotEqual(first.target_hash, third.target_hash)


if __name__ == "__main__":
    unittest.main()
