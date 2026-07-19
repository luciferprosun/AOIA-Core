from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.hub import KnowledgeHub1A
from runtime.knowledge_modules.registry import KnowledgeModuleRegistration, KnowledgeModuleRegistry
from runtime.knowledge_modules.selection import KnowledgeModuleQuery, KnowledgeModuleSelection
from tests.knowledge_module_test_support_1a import (
    NoEvidenceAdapter,
    SyntheticAdapter,
    synthetic_configuration,
    synthetic_descriptor,
)


class KnowledgeHub1ATests(unittest.TestCase):
    def setUp(self):
        self.descriptor = synthetic_descriptor()
        self.hub = KnowledgeHub1A(
            KnowledgeModuleRegistry().register(
                KnowledgeModuleRegistration(self.descriptor, SyntheticAdapter)
            )
        )
        self.query = KnowledgeModuleQuery(
            question="§ 1 SYN", retrieval_mode="SOURCE_DISCOVERY"
        )

    def test_zero_modules_is_valid_non_error_result(self):
        result = self.hub.query(KnowledgeModuleSelection(), self.query, {})
        self.assertEqual(result.status, "NO_KNOWLEDGE_MODULE_SELECTED")
        self.assertEqual(result.selected_module_ids, ())
        self.assertEqual(result.evidence_bundles, ())
        self.assertEqual(result.module_failures, ())
        self.assertFalse(result.can_call_provider)

    def test_explicit_selection_produces_isolated_evidence(self):
        selection = KnowledgeModuleSelection(module_ids=(self.descriptor.module_id,))
        result = self.hub.query(
            selection,
            self.query,
            {self.descriptor.module_id: synthetic_configuration()},
        )
        self.assertEqual(result.status, "KNOWLEDGE_EVIDENCE_AVAILABLE")
        self.assertEqual(result.selected_module_ids, (self.descriptor.module_id,))
        self.assertEqual(len(result.evidence_bundles), 1)
        self.assertEqual(result.evidence_bundles[0].module_id, self.descriptor.module_id)
        self.assertFalse(result.can_approve)
        self.assertFalse(result.can_write)
        self.assertFalse(result.can_execute)

    def test_unknown_module_id_blocks(self):
        with self.assertRaises(KnowledgeModuleError) as caught:
            self.hub.validate_selection(KnowledgeModuleSelection(module_ids=("unknown-1a",)))
        self.assertEqual(caught.exception.status, "UNKNOWN_MODULE_ID")

    def test_missing_configuration_fails_without_fallback(self):
        result = self.hub.query(
            KnowledgeModuleSelection(module_ids=(self.descriptor.module_id,)),
            self.query,
            {},
        )
        self.assertEqual(result.status, "KNOWLEDGE_MODULE_FAILURE")
        self.assertEqual([item.code for item in result.module_failures], ["MODULE_NOT_AVAILABLE"])
        self.assertEqual(result.evidence_bundles, ())

    def test_selection_is_not_persisted_between_requests(self):
        selected = self.hub.query(
            KnowledgeModuleSelection(module_ids=(self.descriptor.module_id,)),
            self.query,
            {self.descriptor.module_id: synthetic_configuration()},
        )
        empty = self.hub.query(KnowledgeModuleSelection(), self.query, {})
        self.assertEqual(selected.status, "KNOWLEDGE_EVIDENCE_AVAILABLE")
        self.assertEqual(empty.status, "NO_KNOWLEDGE_MODULE_SELECTED")
        self.assertEqual(empty.selected_module_ids, ())
        self.assertFalse(hasattr(self.hub, "selected_module_ids"))

    def test_identical_inputs_produce_identical_result_and_bundle_hashes(self):
        selection = KnowledgeModuleSelection(module_ids=(self.descriptor.module_id,))
        configurations = {self.descriptor.module_id: synthetic_configuration()}
        first = self.hub.query(selection, self.query, configurations)
        second = self.hub.query(selection, self.query, configurations)
        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(
            first.evidence_bundles[0].bundle_hash,
            second.evidence_bundles[0].bundle_hash,
        )

    def test_successful_fail_closed_retrieval_does_not_claim_evidence_available(self):
        hub = KnowledgeHub1A(
            KnowledgeModuleRegistry().register(
                KnowledgeModuleRegistration(self.descriptor, NoEvidenceAdapter)
            )
        )
        query = KnowledgeModuleQuery(
            question="§ 1 SYN",
            retrieval_mode="VERIFIED_AS_OF",
            as_of_date="2025-01-01",
        )
        result = hub.query(
            KnowledgeModuleSelection(module_ids=(self.descriptor.module_id,)),
            query,
            {self.descriptor.module_id: synthetic_configuration()},
        )
        self.assertEqual(result.status, "KNOWLEDGE_RETRIEVAL_NO_EVIDENCE")
        self.assertEqual(result.evidence_bundles[0].evidence_items, ())
        self.assertEqual(
            [failure.code for failure in result.evidence_bundles[0].retrieval_failures],
            ["NO_TEMPORAL_EVIDENCE"],
        )


if __name__ == "__main__":
    unittest.main()
