from __future__ import annotations

import json
import unittest

from runtime.knowledge_modules.provider_bridge import KnowledgeProviderBridge1A
from tests.knowledge_context_test_support_1a import context_fixture, target


class KnowledgeContextProviderIndependence1ATests(unittest.TestCase):
    def test_package_contains_no_provider_model_credentials_or_machine_paths(self):
        package = context_fixture().package
        payload = package.to_dict()
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn("provider_id", payload)
        self.assertNotIn("model_id", payload)
        for forbidden in (
            "api_key", "OPENROUTER_API_KEY", "github_token", "/home/", "/media/",
            "module_repository_path", "corpus_data_root",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_same_package_binds_to_two_targets_without_identity_change(self):
        fixture = context_fixture()
        package = fixture.package
        profile_hash = fixture.profile.profile_hash
        first = KnowledgeProviderBridge1A.prepare_provider_request(
            package, target("openrouter_chat", "model-a")
        )
        second = KnowledgeProviderBridge1A.prepare_provider_request(
            package, target("gemini_chat", "model-b")
        )
        self.assertEqual(package.context_package_hash, fixture.package.context_package_hash)
        self.assertEqual(profile_hash, fixture.profile.profile_hash)
        self.assertNotEqual(first.request.request_hash, second.request.request_hash)
        self.assertEqual(first.request.context_package_hash, second.request.context_package_hash)

    def test_provider_selection_does_not_modify_module_selection(self):
        fixture = context_fixture(("alpha-module-1a", "beta-module-1a"))
        before = fixture.package.selected_module_ids
        KnowledgeProviderBridge1A.prepare_provider_request(
            fixture.package, target("openrouter_chat", "one")
        )
        KnowledgeProviderBridge1A.prepare_provider_request(
            fixture.package, target("kimi_chat", "two")
        )
        self.assertEqual(fixture.package.selected_module_ids, before)


if __name__ == "__main__":
    unittest.main()
