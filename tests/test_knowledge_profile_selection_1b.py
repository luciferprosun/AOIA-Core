from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.hub import KnowledgeHub1B
from runtime.knowledge_modules.instances import DISABLED
from runtime.knowledge_modules.profiles import PROFILE_MODULE_SCHEMA_VERSION, KnowledgeProfileModuleSelection
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    instance_descriptor,
    module_descriptor,
    policy,
    profile,
    registry_with,
    selection,
)
from runtime.knowledge_modules.policy import DEFAULT_KNOWLEDGE_HUB_POLICY


class KnowledgeProfileSelection1BTests(unittest.TestCase):
    def test_reviewed_default_and_absolute_module_limits_are_explicit(self):
        self.assertEqual(DEFAULT_KNOWLEDGE_HUB_POLICY.default_max_selected_modules, 8)
        self.assertEqual(DEFAULT_KNOWLEDGE_HUB_POLICY.absolute_max_selected_modules, 16)

    def test_unknown_module_unknown_instance_and_mismatch_block(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, instance)))
        unknown_module = module_descriptor("unknown-module-1a")
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.validate_profile(profile(selection(unknown_module, instance_descriptor(unknown_module))))
        self.assertEqual(caught.exception.status, "MODULE_NOT_REGISTERED")
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.validate_profile(profile(selection(descriptor, instance_descriptor(descriptor, instance_id="missing-instance"))))
        self.assertEqual(caught.exception.status, "MODULE_INSTANCE_NOT_REGISTERED")
        other = module_descriptor("other-module-1a")
        other_instance = instance_descriptor(other)
        mismatched = KnowledgeProfileModuleSelection(
            schema_version=PROFILE_MODULE_SCHEMA_VERSION,
            module_id=descriptor.module_id,
            instance_id=other_instance.instance_id,
            enabled=True,
            priority=0,
            per_module_max_results=10,
            per_module_max_context_characters=16_000,
            retrieval_mode="SOURCE_DISCOVERY",
        )
        mixed_registry = registry_with(
            (descriptor, SyntheticAdapter, instance),
            (other, SyntheticAdapter, other_instance),
        )
        with self.assertRaises(KnowledgeModuleError) as caught:
            KnowledgeHub1B(mixed_registry).validate_profile(profile(mismatched))
        self.assertEqual(caught.exception.status, "MODULE_DESCRIPTOR_MISMATCH")

    def test_disabled_instance_and_selection_above_policy_block(self):
        descriptor = module_descriptor()
        disabled = instance_descriptor(descriptor, availability_status=DISABLED)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, disabled)))
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.validate_profile(profile(selection(descriptor, disabled)))
        self.assertEqual(caught.exception.status, "MODULE_DISABLED")

        entries = []
        selections = []
        for index in range(3):
            item = module_descriptor(f"module-{index}-1a")
            deployed = instance_descriptor(item)
            entries.append((item, SyntheticAdapter, deployed))
            selections.append(selection(item, deployed, priority=index, max_results=1, max_context=1024))
        limited = KnowledgeHub1B(registry_with(*entries), policy(default_max_selected_modules=2))
        with self.assertRaises(KnowledgeModuleError) as caught:
            limited.validate_profile(profile(*selections, max_modules=3, max_results=3, max_context=3072))
        self.assertEqual(caught.exception.status, "PROFILE_LIMIT_EXCEEDED")

    def test_no_hidden_or_persisted_selection_state(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, instance)))
        first = profile(selection(descriptor, instance))
        hub.validate_profile(first)
        second = profile()
        hub.validate_profile(second)
        self.assertFalse(hasattr(hub, "selected_modules"))
        self.assertFalse(hub.control_model(second)[0].currently_selected)


if __name__ == "__main__":
    unittest.main()
