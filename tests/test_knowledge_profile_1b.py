from __future__ import annotations

import dataclasses
import unittest
from dataclasses import replace

from runtime.knowledge_modules.contracts import AUTHORITY_FLAG_NAMES, KnowledgeModuleError
from runtime.knowledge_modules.profiles import (
    EXPOSE,
    REPORT_AND_CONTINUE_UNRELATED_MODULES,
    REQUEST_ONLY,
)
from tests.knowledge_control_plane_test_support_1b import (
    instance_descriptor,
    module_descriptor,
    profile,
    selection,
)


class KnowledgeProfile1BTests(unittest.TestCase):
    def test_zero_one_and_multi_module_profiles_are_valid(self):
        empty = profile()
        alpha = module_descriptor("alpha-module-1a")
        beta = module_descriptor("beta-module-1a")
        alpha_instance = instance_descriptor(alpha)
        beta_instance = instance_descriptor(beta)
        one = profile(selection(alpha, alpha_instance))
        multiple = profile(
            selection(beta, beta_instance, priority=20),
            selection(alpha, alpha_instance, priority=10),
        )
        self.assertEqual(empty.enabled_selections, ())
        self.assertEqual(len(one.enabled_selections), 1)
        self.assertEqual([item.module_id for item in multiple.enabled_selections], [alpha.module_id, beta.module_id])

    def test_profile_is_request_only_non_authoritative_and_frozen(self):
        value = profile()
        self.assertEqual(value.selection_scope, REQUEST_ONLY)
        self.assertEqual(value.conflict_policy, EXPOSE)
        self.assertEqual(value.failure_policy, REPORT_AND_CONTINUE_UNRELATED_MODULES)
        self.assertTrue(value.__dataclass_params__.frozen)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            value.profile_id = "other"
        for field in AUTHORITY_FLAG_NAMES:
            self.assertFalse(getattr(value, field), field)

    def test_profile_hash_and_order_are_deterministic(self):
        alpha = module_descriptor("alpha-module-1a")
        beta = module_descriptor("beta-module-1a")
        alpha_selection = selection(alpha, instance_descriptor(alpha), priority=1)
        beta_selection = selection(beta, instance_descriptor(beta), priority=2)
        first = profile(beta_selection, alpha_selection)
        second = profile(alpha_selection, beta_selection)
        self.assertEqual(first.profile_hash, second.profile_hash)
        self.assertEqual(first.selected_modules, second.selected_modules)

    def test_duplicate_modules_instances_and_authority_claims_block(self):
        alpha = module_descriptor("alpha-module-1a")
        alpha_instance = instance_descriptor(alpha)
        selected = selection(alpha, alpha_instance)
        with self.assertRaises(KnowledgeModuleError):
            profile(selected, selected)
        beta = module_descriptor("beta-module-1a")
        reused = instance_descriptor(beta, instance_id=alpha_instance.instance_id)
        with self.assertRaises(KnowledgeModuleError):
            profile(selected, selection(beta, reused))
        with self.assertRaises(KnowledgeModuleError):
            replace(profile(), profile_hash="", can_write=True)

    def test_disabled_checkbox_record_is_not_enabled(self):
        descriptor = module_descriptor()
        selected = selection(descriptor, instance_descriptor(descriptor), enabled=False)
        value = profile(selected)
        self.assertEqual(value.enabled_selections, ())
        self.assertFalse(value.selected_modules[0].enabled)

    def test_verified_as_of_requires_an_exact_iso_date_filter(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        for filters in ((), (("as_of_date", "2026-7-1"),), (("as_of_date", "not-a-date"),)):
            with self.subTest(filters=filters):
                with self.assertRaises(KnowledgeModuleError):
                    selection(
                        descriptor,
                        instance,
                        retrieval_mode="VERIFIED_AS_OF",
                        filters=filters,
                    )
        valid = selection(
            descriptor,
            instance,
            retrieval_mode="VERIFIED_AS_OF",
            filters=(("as_of_date", "2026-07-01"),),
        )
        self.assertEqual(dict(valid.module_specific_filters)["as_of_date"], "2026-07-01")

    def test_profile_and_selection_unknown_fields_are_rejected(self):
        descriptor = module_descriptor()
        selected = selection(descriptor, instance_descriptor(descriptor))
        selection_payload = selected.to_dict()
        selection_payload["provider"] = "forbidden"
        with self.assertRaises(KnowledgeModuleError):
            type(selected).from_dict(selection_payload)
        profile_payload = profile(selected).to_dict()
        profile_payload["persist"] = True
        with self.assertRaises(KnowledgeModuleError):
            type(profile(selected)).from_dict(profile_payload)


if __name__ == "__main__":
    unittest.main()
