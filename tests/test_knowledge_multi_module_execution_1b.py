from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.hub import KnowledgeHub1B
from tests.knowledge_control_plane_test_support_1b import (
    AuthorityClaimingAdapter,
    NonfatalFailingAdapter,
    RecordingAdapter,
    SyntheticAdapter,
    configurations,
    instance_descriptor,
    module_descriptor,
    profile,
    query,
    registry_with,
    selection,
)


class KnowledgeMultiModuleExecution1BTests(unittest.TestCase):
    def test_execution_is_sequential_in_plan_order_and_has_no_retry(self):
        alpha = module_descriptor("alpha-module-1a")
        beta = module_descriptor("beta-module-1a")
        alpha_instance = instance_descriptor(alpha)
        beta_instance = instance_descriptor(beta)
        RecordingAdapter.reset()
        hub = KnowledgeHub1B(
            registry_with(
                (beta, RecordingAdapter, beta_instance),
                (alpha, RecordingAdapter, alpha_instance),
            )
        )
        selected = profile(
            selection(beta, beta_instance, priority=2),
            selection(alpha, alpha_instance, priority=1),
        )
        result = hub.execute(selected, query(), configurations(alpha, beta))
        self.assertEqual(result.status, "KNOWLEDGE_EVIDENCE_AVAILABLE")
        self.assertEqual(
            RecordingAdapter.calls,
            [("verify", "alpha-module-1a"), ("query", "alpha-module-1a"),
             ("verify", "beta-module-1a"), ("query", "beta-module-1a")],
        )

    def test_unrelated_explicit_module_continues_after_nonfatal_failure(self):
        failed = module_descriptor("failed-module-1a")
        good = module_descriptor("good-module-1a")
        failed_instance = instance_descriptor(failed)
        good_instance = instance_descriptor(good)
        hub = KnowledgeHub1B(
            registry_with(
                (failed, NonfatalFailingAdapter, failed_instance),
                (good, SyntheticAdapter, good_instance),
            )
        )
        selected = profile(
            selection(failed, failed_instance, priority=1),
            selection(good, good_instance, priority=2),
        )
        result = hub.execute(selected, query(), configurations(failed, good))
        self.assertEqual(result.status, "PARTIAL_KNOWLEDGE_MODULE_FAILURE")
        self.assertEqual([item.module_id for item in result.composite_bundle.module_bundles], [good.module_id])
        self.assertEqual([item.module_id for item in result.composite_bundle.module_failures], [failed.module_id])

    def test_failure_does_not_activate_unselected_module(self):
        failed = module_descriptor("failed-module-1a")
        unselected = module_descriptor("unselected-module-1a")
        failed_instance = instance_descriptor(failed)
        unselected_instance = instance_descriptor(unselected)
        hub = KnowledgeHub1B(
            registry_with(
                (failed, NonfatalFailingAdapter, failed_instance),
                (unselected, RecordingAdapter, unselected_instance),
            )
        )
        RecordingAdapter.reset()
        result = hub.execute(profile(selection(failed, failed_instance)), query(), configurations(failed))
        self.assertEqual(result.status, "KNOWLEDGE_MODULE_FAILURE")
        self.assertEqual(RecordingAdapter.calls, [])
        self.assertEqual(result.composite_bundle.selected_module_ids, (failed.module_id,))

    def test_authority_claim_is_a_global_fail_closed_error(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, AuthorityClaimingAdapter, instance)))
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.execute(profile(selection(descriptor, instance)), query(), configurations(descriptor))
        self.assertEqual(caught.exception.status, "MODULE_AUTHORITY_CLAIM_BLOCKED")


if __name__ == "__main__":
    unittest.main()
