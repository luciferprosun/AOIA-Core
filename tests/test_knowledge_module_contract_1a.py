from __future__ import annotations

import dataclasses
import json
import unittest
from dataclasses import replace

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    KnowledgeModuleDescriptor,
    KnowledgeModuleError,
    canonical_hash,
    canonical_json_bytes,
)
from runtime.knowledge_modules.evidence import evidence_item_from_fields
from runtime.knowledge_modules.german_law import EXPECTED_GERMAN_LAW_DESCRIPTOR
from tests.knowledge_module_test_support_1a import SHA_A, synthetic_bundle, synthetic_descriptor
from runtime.knowledge_modules.selection import KnowledgeModuleQuery


class KnowledgeModuleContract1ATests(unittest.TestCase):
    def test_descriptor_identity_is_stable_disabled_and_non_authoritative(self):
        descriptor = EXPECTED_GERMAN_LAW_DESCRIPTOR
        self.assertEqual(descriptor.module_id, "de-law-federal-1a")
        self.assertEqual(descriptor.module_version, "1a")
        self.assertFalse(descriptor.enabled_by_default)
        self.assertEqual(descriptor.authority_status, "NON_AUTHORITATIVE")
        self.assertEqual(descriptor.capability_ids, ())
        for field in AUTHORITY_FLAG_NAMES:
            self.assertFalse(getattr(descriptor, field), field)

    def test_contracts_are_frozen_slotted_and_deterministically_serialized(self):
        descriptor = synthetic_descriptor()
        self.assertTrue(descriptor.__dataclass_params__.frozen)
        self.assertTrue(hasattr(type(descriptor), "__slots__"))
        first = canonical_json_bytes(descriptor)
        second = canonical_json_bytes(descriptor.to_dict())
        self.assertEqual(first, second)
        self.assertEqual(canonical_hash(descriptor), canonical_hash(descriptor.to_dict()))
        self.assertEqual(json.loads(first), descriptor.to_dict())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            descriptor.display_name = "mutated"

    def test_descriptor_rejects_every_enabled_authority_field(self):
        descriptor = synthetic_descriptor()
        for field in AUTHORITY_FLAG_NAMES:
            with self.subTest(field=field):
                with self.assertRaises(KnowledgeModuleError) as caught:
                    replace(descriptor, descriptor_hash="", **{field: True})
                self.assertEqual(caught.exception.status, "MODULE_AUTHORITY_CLAIM_BLOCKED")

    def test_evidence_requires_source_identity_hash_and_false_capabilities(self):
        query = KnowledgeModuleQuery(question="§ 1 SYN", retrieval_mode="SOURCE_DISCOVERY")
        item = synthetic_bundle(synthetic_descriptor(), query).evidence_items[0]
        self.assertRegex(item.source_object_sha256, r"^[0-9a-f]{64}$")
        self.assertTrue(item.document_id)
        self.assertTrue(item.module_id)
        self.assertTrue(item.module_version)
        self.assertEqual(item.authority_status, "NON_AUTHORITATIVE_EVIDENCE")
        for field in AUTHORITY_FLAG_NAMES:
            self.assertFalse(getattr(item, field), field)
        values = item.to_dict()
        values.update(evidence_id="", evidence_hash="", source_object_sha256="not-a-hash")
        with self.assertRaises(KnowledgeModuleError):
            evidence_item_from_fields(
                **{
                    key: value
                    for key, value in values.items()
                    if key not in {"schema_version", "evidence_id", "evidence_hash"}
                }
            )

    def test_descriptor_from_dict_rejects_unknown_fields(self):
        value = synthetic_descriptor().to_dict()
        value["provider"] = "forbidden"
        with self.assertRaises(KnowledgeModuleError):
            KnowledgeModuleDescriptor.from_dict(value)


if __name__ == "__main__":
    unittest.main()
