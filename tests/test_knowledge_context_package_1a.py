from __future__ import annotations

import unittest
from dataclasses import replace

from runtime.knowledge_modules.context_policy import KnowledgeContextLimits
from runtime.knowledge_modules.contracts import KnowledgeModuleError
from tests.knowledge_context_test_support_1a import context_fixture, zero_module_fixture


class KnowledgeContextPackage1ATests(unittest.TestCase):
    def test_zero_module_package_is_valid_empty_and_non_authoritative(self):
        package = zero_module_fixture().package
        self.assertEqual(package.selected_module_ids, ())
        self.assertEqual(package.module_sections, ())
        self.assertEqual(package.total_evidence_items, 0)
        self.assertEqual(package.authority_status, "NON_AUTHORITATIVE")
        for name in (
            "can_approve", "can_write", "can_execute", "can_commit", "can_push",
            "can_call_provider", "can_call_tools", "can_change_gate",
            "can_satisfy_human_barrier", "gate_satisfied",
        ):
            self.assertFalse(getattr(package, name))

    def test_one_module_section_preserves_complete_source_provenance(self):
        package = context_fixture().package
        section = package.module_sections[0]
        item = section.evidence_items[0]
        self.assertEqual(item.module_id, section.module_id)
        self.assertEqual(item.instance_id, section.instance_id)
        self.assertEqual(item.corpus_snapshot_id, section.corpus_snapshot_ids[0])
        self.assertEqual(len(item.source_object_sha256), 64)
        self.assertEqual(len(item.evidence_hash), 64)
        self.assertEqual(item.data_classification, "UNTRUSTED_EVIDENCE_DATA")
        self.assertIn("CURRENTNESS_NOT_VERIFIED", item.warnings)

    def test_derived_bundle_snapshot_is_preserved_with_instance_source_snapshots(self):
        section = context_fixture(derived_snapshot=True).package.module_sections[0]
        self.assertEqual(
            ("derived-factory-snapshot-1a", "synthetic-snapshot-1a"),
            section.corpus_snapshot_ids,
        )
        self.assertEqual(
            "derived-factory-snapshot-1a",
            section.evidence_items[0].corpus_snapshot_id,
        )

    def test_context_package_identity_is_deterministic(self):
        first = context_fixture().package
        second = context_fixture().package
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.context_package_hash, second.context_package_hash)

    def test_context_package_rejects_authority_claim(self):
        package = context_fixture().package
        with self.assertRaises(KnowledgeModuleError) as caught:
            replace(package, can_call_tools=True, context_package_id="", context_package_hash="")
        self.assertEqual(caught.exception.status, "KNOWLEDGE_CONTEXT_AUTHORITY_CLAIM_BLOCKED")

    def test_context_section_rejects_machine_specific_location_metadata(self):
        section = context_fixture().package.module_sections[0]
        with self.assertRaises(KnowledgeModuleError) as caught:
            replace(
                section,
                known_limitations=("Corpus at /home/operator/private-corpus",),
                module_section_hash="",
            )
        self.assertEqual(caught.exception.status, "KNOWLEDGE_CONTEXT_INVALID")

    def test_global_context_limit_uses_fair_deterministic_truncation(self):
        limits = KnowledgeContextLimits(
            maximum_total_context_characters=1_024,
            minimum_context_characters_per_module=256,
        )
        first = context_fixture(
            ("alpha-module-1a", "beta-module-1a"),
            long_excerpt=True,
            limits=limits,
        ).package
        second = context_fixture(
            ("alpha-module-1a", "beta-module-1a"),
            long_excerpt=True,
            limits=limits,
        ).package
        self.assertEqual(first.total_context_characters, 1_024)
        self.assertEqual(
            tuple(section.context_characters for section in first.module_sections),
            (768, 256),
        )
        self.assertTrue(first.truncated)
        self.assertEqual(first.context_package_hash, second.context_package_hash)
        for section in first.module_sections:
            self.assertTrue(section.truncated)
            self.assertEqual(len(section.evidence_items[0].source_object_sha256), 64)
            self.assertIn("CURRENTNESS_NOT_VERIFIED", section.evidence_items[0].warnings)


if __name__ == "__main__":
    unittest.main()
