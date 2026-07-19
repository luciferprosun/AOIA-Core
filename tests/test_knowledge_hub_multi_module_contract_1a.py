from __future__ import annotations

import unittest

from runtime.knowledge_modules.german_law import EXPECTED_GERMAN_LAW_DESCRIPTOR
from runtime.knowledge_modules.hub import KnowledgeHub1A
from runtime.knowledge_modules.registry import KnowledgeModuleRegistration, KnowledgeModuleRegistry
from runtime.knowledge_modules.selection import KnowledgeModuleQuery, KnowledgeModuleSelection
from tests.knowledge_module_test_support_1a import (
    FailingAdapter,
    SyntheticAdapter,
    synthetic_configuration,
    synthetic_descriptor,
)


class KnowledgeHubMultiModuleContract1ATests(unittest.TestCase):
    def test_two_synthetic_modules_keep_provenance_separate(self):
        alpha = synthetic_descriptor("alpha-law-1a")
        beta = synthetic_descriptor("beta-law-1a")
        registry = KnowledgeModuleRegistry(
            (
                KnowledgeModuleRegistration(beta, SyntheticAdapter),
                KnowledgeModuleRegistration(alpha, SyntheticAdapter),
            )
        )
        hub = KnowledgeHub1A(registry)
        query = KnowledgeModuleQuery(question="§ 1 SYN", retrieval_mode="SOURCE_DISCOVERY")
        result = hub.query(
            KnowledgeModuleSelection(module_ids=(beta.module_id, alpha.module_id)),
            query,
            {
                alpha.module_id: synthetic_configuration(alpha.module_id),
                beta.module_id: synthetic_configuration(beta.module_id),
            },
        )
        self.assertEqual(result.status, "KNOWLEDGE_EVIDENCE_AVAILABLE")
        self.assertEqual(
            tuple(bundle.module_id for bundle in result.evidence_bundles),
            (alpha.module_id, beta.module_id),
        )
        for bundle in result.evidence_bundles:
            self.assertTrue(all(item.module_id == bundle.module_id for item in bundle.evidence_items))
            self.assertFalse(bundle.can_approve)
            self.assertFalse(bundle.can_write)

    def test_selecting_synthetic_module_does_not_activate_german_law(self):
        synthetic = synthetic_descriptor()
        registry = KnowledgeModuleRegistry(
            (
                KnowledgeModuleRegistration(EXPECTED_GERMAN_LAW_DESCRIPTOR, FailingAdapter),
                KnowledgeModuleRegistration(synthetic, SyntheticAdapter),
            )
        )
        result = KnowledgeHub1A(registry).query(
            KnowledgeModuleSelection(module_ids=(synthetic.module_id,)),
            KnowledgeModuleQuery(question="§ 1 SYN", retrieval_mode="SOURCE_DISCOVERY"),
            {synthetic.module_id: synthetic_configuration()},
        )
        self.assertEqual(result.selected_module_ids, (synthetic.module_id,))
        self.assertEqual(
            tuple(bundle.module_id for bundle in result.evidence_bundles),
            (synthetic.module_id,),
        )
        self.assertNotIn("de-law-federal-1a", result.to_dict()["selected_module_ids"])

    def test_one_failure_does_not_fallback_or_merge_into_other_module(self):
        good = synthetic_descriptor("good-law-1a")
        failed = synthetic_descriptor("failed-law-1a")
        hub = KnowledgeHub1A(
            KnowledgeModuleRegistry(
                (
                    KnowledgeModuleRegistration(good, SyntheticAdapter),
                    KnowledgeModuleRegistration(failed, FailingAdapter),
                )
            )
        )
        result = hub.query(
            KnowledgeModuleSelection(module_ids=(good.module_id, failed.module_id)),
            KnowledgeModuleQuery(question="§ 1 SYN", retrieval_mode="SOURCE_DISCOVERY"),
            {
                good.module_id: synthetic_configuration(good.module_id),
                failed.module_id: synthetic_configuration(failed.module_id),
            },
        )
        self.assertEqual(result.status, "PARTIAL_KNOWLEDGE_MODULE_FAILURE")
        self.assertEqual([bundle.module_id for bundle in result.evidence_bundles], [good.module_id])
        self.assertEqual([failure.module_id for failure in result.module_failures], [failed.module_id])
        self.assertFalse(result.can_approve)
        self.assertFalse(result.can_execute)


if __name__ == "__main__":
    unittest.main()
