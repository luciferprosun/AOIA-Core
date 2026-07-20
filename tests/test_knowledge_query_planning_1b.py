from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.hub import KnowledgeHub1B
from runtime.knowledge_modules.planning import SEQUENTIAL
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    instance_descriptor,
    module_descriptor,
    policy,
    profile,
    query,
    registry_with,
    selection,
)


class KnowledgeQueryPlanning1BTests(unittest.TestCase):
    def _fixture(self):
        alpha = module_descriptor("alpha-module-1a")
        beta = module_descriptor("beta-module-1a")
        alpha_instance = instance_descriptor(alpha)
        beta_instance = instance_descriptor(beta)
        hub = KnowledgeHub1B(
            registry_with(
                (beta, SyntheticAdapter, beta_instance),
                (alpha, SyntheticAdapter, alpha_instance),
            )
        )
        selected = profile(
            selection(beta, beta_instance, priority=20, max_results=6, max_context=6_000),
            selection(alpha, alpha_instance, priority=10, max_results=6, max_context=6_000),
            max_results=8,
            max_context=8_000,
        )
        return hub, selected

    def test_plan_is_stable_sequential_and_preserves_explicit_priority(self):
        hub, selected = self._fixture()
        first = hub.plan_query(selected, query("same bounded human question"))
        second = hub.plan_query(selected, query("same bounded human question"))
        self.assertEqual(first.plan_hash, second.plan_hash)
        self.assertEqual(first.execution_model, SEQUENTIAL)
        self.assertEqual(
            [item.module_id for item in first.module_plans],
            ["alpha-module-1a", "beta-module-1a"],
        )
        self.assertTrue(all(item.question == "same bounded human question" for item in first.module_plans))

    def test_fair_reserve_and_priority_allocation_are_deterministic(self):
        hub, selected = self._fixture()
        plan = hub.plan_query(selected, query())
        self.assertEqual([item.max_results for item in plan.module_plans], [6, 2])
        self.assertEqual([item.max_total_context_characters for item in plan.module_plans], [6_000, 2_000])
        self.assertEqual(plan.total_planned_results, 8)
        self.assertEqual(plan.total_planned_context_characters, 8_000)

    def test_global_budget_must_reserve_every_enabled_module(self):
        alpha = module_descriptor("alpha-module-1a")
        beta = module_descriptor("beta-module-1a")
        alpha_instance = instance_descriptor(alpha)
        beta_instance = instance_descriptor(beta)
        hub = KnowledgeHub1B(
            registry_with(
                (alpha, SyntheticAdapter, alpha_instance),
                (beta, SyntheticAdapter, beta_instance),
            ),
            policy(minimum_context_characters_per_module=1_024),
        )
        selected = profile(
            selection(alpha, alpha_instance, max_context=1_024),
            selection(beta, beta_instance, max_context=1_024),
            max_results=2,
            max_context=1_024,
        )
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.plan_query(selected, query())
        self.assertEqual(caught.exception.status, "GLOBAL_BUDGET_EXCEEDED")

    def test_question_does_not_semantically_activate_or_reorder_modules(self):
        hub, selected = self._fixture()
        plan = hub.plan_query(selected, query("This looks relevant only to beta"))
        self.assertEqual(len(plan.module_plans), 2)
        self.assertEqual(plan.module_plans[0].module_id, "alpha-module-1a")
        empty = profile(max_results=1, max_context=1_024)
        self.assertEqual(hub.plan_query(empty, query("§ 2 NachwG")).module_plans, ())


if __name__ == "__main__":
    unittest.main()
