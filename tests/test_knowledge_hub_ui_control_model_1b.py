from __future__ import annotations

import unittest

from runtime.knowledge_modules.german_law import production_knowledge_module_registry
from runtime.knowledge_modules.hub import KnowledgeHub1B
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    instance_descriptor,
    module_descriptor,
    profile,
    registry_with,
    selection,
)


class KnowledgeHubUIControlModel1BTests(unittest.TestCase):
    def test_control_model_has_ui_fields_and_is_disabled_by_default(self):
        record = KnowledgeHub1B(production_knowledge_module_registry()).control_model()[0]
        payload = record.to_dict()
        self.assertEqual(payload["module_id"], "de-law-federal-1a")
        self.assertEqual(payload["available_instances"], ["de-law-federal-1a-local"])
        self.assertFalse(payload["enabled_by_default"])
        self.assertFalse(payload["currently_selected"])
        self.assertFalse(payload["can_call_provider"])

    def test_checkbox_state_maps_only_to_request_selection_enabled(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, instance)))
        disabled = profile(selection(descriptor, instance, enabled=False))
        enabled = profile(selection(descriptor, instance, enabled=True))
        self.assertFalse(hub.control_model(disabled)[0].currently_selected)
        self.assertTrue(hub.control_model(enabled)[0].currently_selected)
        self.assertFalse(hub.control_model()[0].currently_selected)


if __name__ == "__main__":
    unittest.main()
