from __future__ import annotations

import unittest
from dataclasses import replace

from runtime.knowledge_modules.composite import (
    NOT_EVALUATED,
    ModuleExecutionOutcome,
    build_composite_evidence_bundle,
)
from runtime.knowledge_modules.contracts import AUTHORITY_FLAG_NAMES
from runtime.knowledge_modules.hub import KnowledgeHub1B
from runtime.knowledge_modules.planning import (
    COMPOSITE_QUERY_PLAN_SCHEMA_VERSION,
    MODULE_QUERY_PLAN_SCHEMA_VERSION,
    CompositeKnowledgeQueryPlan,
    ModuleQueryPlan,
)
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    configurations,
    instance_descriptor,
    module_descriptor,
    policy,
    profile,
    query,
    registry_with,
    selection,
    synthetic_configuration,
)
from tests.knowledge_module_test_support_1a import synthetic_bundle


class KnowledgeCompositeBundle1BTests(unittest.TestCase):
    def test_multi_module_provenance_is_preserved_without_semantic_deduplication(self):
        alpha = module_descriptor("alpha-module-1a", domain="ALPHA")
        beta = module_descriptor("beta-module-1a", domain="BETA")
        alpha_instance = instance_descriptor(alpha)
        beta_instance = instance_descriptor(beta)
        hub = KnowledgeHub1B(
            registry_with(
                (alpha, SyntheticAdapter, alpha_instance),
                (beta, SyntheticAdapter, beta_instance),
            )
        )
        selected = profile(
            selection(alpha, alpha_instance, priority=1),
            selection(beta, beta_instance, priority=2),
            max_results=20,
            max_context=32_000,
        )
        result = hub.execute(selected, query(), configurations(alpha, beta))
        bundle = result.composite_bundle
        self.assertEqual(bundle.total_evidence_items, 2)
        self.assertEqual(len(bundle.module_bundles), 2)
        self.assertEqual(bundle.conflict_evaluation_status, NOT_EVALUATED)
        self.assertEqual(
            [item.item_provenance[0].domain for item in bundle.module_bundles],
            ["ALPHA", "BETA"],
        )
        serialized = bundle.to_dict()
        self.assertEqual(
            serialized["module_bundles"][0]["evidence_items"][0]["instance_id"],
            alpha_instance.instance_id,
        )
        self.assertEqual(
            serialized["module_bundles"][0]["evidence_items"][0]["evidence_item"]["module_id"],
            alpha.module_id,
        )
        excerpts = [item.evidence_bundle.evidence_items[0].bounded_excerpt for item in bundle.module_bundles]
        self.assertEqual(excerpts[0], excerpts[1])
        for field in AUTHORITY_FLAG_NAMES:
            self.assertFalse(getattr(bundle, field), field)

    def test_composite_hash_is_deterministic(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, instance)))
        selected = profile(selection(descriptor, instance))
        first = hub.execute(selected, query(), configurations(descriptor))
        second = hub.execute(selected, query(), configurations(descriptor))
        self.assertEqual(first.composite_bundle.composite_bundle_hash, second.composite_bundle.composite_bundle_hash)
        self.assertEqual(first.result_hash, second.result_hash)

    def test_deterministic_truncation_rebuilds_evidence_with_provenance(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        legacy_query = query().question
        from runtime.knowledge_modules.selection import KnowledgeModuleQuery

        module_query = KnowledgeModuleQuery(
            question=legacy_query,
            retrieval_mode="SOURCE_DISCOVERY",
            max_results=2,
            max_excerpt_characters=4_000,
            max_total_context_characters=4_000,
        )
        source_bundle = synthetic_bundle(descriptor, module_query, excerpt="ä" * 1_000)
        plan_item = ModuleQueryPlan(
            schema_version=MODULE_QUERY_PLAN_SCHEMA_VERSION,
            module_id=descriptor.module_id,
            instance_id=instance.instance_id,
            module_version=descriptor.module_version,
            expected_module_descriptor_hash=descriptor.descriptor_hash,
            priority=0,
            question=module_query.question,
            retrieval_mode="SOURCE_DISCOVERY",
            module_specific_filters=(("jurisdictions", descriptor.jurisdictions), ("languages", descriptor.languages)),
            max_results=1,
            max_excerpt_characters=256,
            max_total_context_characters=1_024,
        )
        generic_query = query()
        selected = profile(selection(descriptor, instance, max_results=1, max_context=1_024), max_results=1, max_context=1_024)
        plan = CompositeKnowledgeQueryPlan(
            schema_version=COMPOSITE_QUERY_PLAN_SCHEMA_VERSION,
            profile_id=selected.profile_id,
            profile_hash=selected.profile_hash,
            query_hash=generic_query.query_hash,
            module_plans=(plan_item,),
            total_planned_results=1,
            total_planned_context_characters=1_024,
        )
        outcomes = {instance.instance_id: ModuleExecutionOutcome(descriptor, instance, source_bundle)}
        first = build_composite_evidence_bundle(selected, plan, outcomes, (), policy())
        second = build_composite_evidence_bundle(selected, plan, outcomes, (), policy())
        item = first.module_bundles[0].evidence_bundle.evidence_items[0]
        self.assertEqual(len(item.bounded_excerpt), 256)
        self.assertTrue(item.excerpt_truncated)
        self.assertIn("EXCERPT_TRUNCATED", item.warnings)
        self.assertTrue(first.truncated)
        self.assertEqual(first.composite_bundle_hash, second.composite_bundle_hash)


if __name__ == "__main__":
    unittest.main()
