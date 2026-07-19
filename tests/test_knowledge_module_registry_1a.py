from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.german_law import (
    EXPECTED_GERMAN_LAW_DESCRIPTOR,
    production_knowledge_module_registry,
)
from runtime.knowledge_modules.registry import (
    KnowledgeModuleRegistration,
    KnowledgeModuleRegistry,
)
from tests.knowledge_module_test_support_1a import SyntheticAdapter, synthetic_descriptor


class KnowledgeModuleRegistry1ATests(unittest.TestCase):
    def test_production_registry_contains_only_german_law(self):
        registry = production_knowledge_module_registry()
        self.assertEqual(
            tuple(item.module_id for item in registry.list_descriptors()),
            ("de-law-federal-1a",),
        )
        self.assertIs(registry.list_descriptors()[0], EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertFalse(registry.list_descriptors()[0].enabled_by_default)

    def test_registry_is_immutable_sorted_and_rejects_duplicates(self):
        alpha = KnowledgeModuleRegistration(synthetic_descriptor("alpha-module"), SyntheticAdapter)
        zulu = KnowledgeModuleRegistration(synthetic_descriptor("zulu-module"), SyntheticAdapter)
        registry = KnowledgeModuleRegistry((zulu, alpha))
        self.assertEqual(
            tuple(item.module_id for item in registry.registrations),
            ("alpha-module", "zulu-module"),
        )
        with self.assertRaises(KnowledgeModuleError) as caught:
            registry.register(alpha)
        self.assertEqual(caught.exception.status, "DUPLICATE_MODULE_ID")

    def test_registration_exposes_metadata_not_executable_configuration(self):
        registration = KnowledgeModuleRegistration(synthetic_descriptor(), SyntheticAdapter)
        self.assertEqual(
            set(registration.to_dict()),
            {
                "authority_status",
                "descriptor_hash",
                "display_name",
                "enabled_by_default",
                "module_id",
                "module_version",
            },
        )
        self.assertNotIn("path", registration.to_dict())
        self.assertNotIn("command", registration.to_dict())


if __name__ == "__main__":
    unittest.main()
