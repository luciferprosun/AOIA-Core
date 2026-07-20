from __future__ import annotations

import unittest

from runtime.knowledge_modules.hub import KnowledgeHub1B
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    instance_descriptor,
    module_descriptor,
    profile,
    query,
    registry_with,
    selection,
)


class KnowledgeBudgetAllocation1BTests(unittest.TestCase):
    def test_per_module_caps_are_never_exceeded(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, instance)))
        selected = profile(
            selection(descriptor, instance, max_results=20, max_context=32_000),
            max_results=20,
            max_context=32_000,
        )
        plan = hub.plan_query(selected, query())
        self.assertEqual(plan.module_plans[0].max_results, 20)
        self.assertEqual(plan.module_plans[0].max_total_context_characters, 32_000)
        self.assertEqual(plan.module_plans[0].max_excerpt_characters, 4_000)

    def test_reserve_prevents_first_module_from_consuming_global_budget(self):
        descriptors = tuple(module_descriptor(f"module-{index}-1a") for index in range(3))
        instances = tuple(instance_descriptor(item) for item in descriptors)
        hub = KnowledgeHub1B(
            registry_with(
                *((descriptor, SyntheticAdapter, instance) for descriptor, instance in zip(descriptors, instances, strict=True))
            )
        )
        selected = profile(
            *(selection(descriptor, instance, priority=index, max_results=10, max_context=10_000)
              for index, (descriptor, instance) in enumerate(zip(descriptors, instances, strict=True))),
            max_results=12,
            max_context=12_000,
        )
        plan = hub.plan_query(selected, query())
        self.assertEqual([item.max_results for item in plan.module_plans], [10, 1, 1])
        self.assertEqual([item.max_total_context_characters for item in plan.module_plans], [9_952, 1_024, 1_024])


if __name__ == "__main__":
    unittest.main()
