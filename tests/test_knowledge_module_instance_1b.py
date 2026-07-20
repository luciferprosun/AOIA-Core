from __future__ import annotations

import dataclasses
import unittest
from dataclasses import replace

from runtime.knowledge_modules.contracts import AUTHORITY_FLAG_NAMES, KnowledgeModuleError
from runtime.knowledge_modules.german_law import (
    GERMAN_LAW_INSTANCE_ID,
    GERMAN_LAW_LOCAL_INSTANCE,
    EXPECTED_GERMAN_LAW_DESCRIPTOR,
    production_knowledge_module_registry,
)
from runtime.knowledge_modules.instances import (
    AVAILABLE,
    INSTANCE_SCHEMA_VERSION,
    TRANSPORT_NOT_IMPLEMENTED,
    KnowledgeModuleInstanceDescriptor,
)
from runtime.knowledge_modules.transports import REMOTE_READ_ONLY_SERVICE
from tests.knowledge_control_plane_test_support_1b import instance_descriptor, module_descriptor


class KnowledgeModuleInstance1BTests(unittest.TestCase):
    def test_production_instance_is_separate_from_logical_module(self):
        registry = production_knowledge_module_registry()
        self.assertEqual([item.module_id for item in registry.list_module_descriptors()], ["de-law-federal-1a"])
        self.assertEqual([item.instance_id for item in registry.list_module_instances()], [GERMAN_LAW_INSTANCE_ID])
        self.assertEqual(GERMAN_LAW_LOCAL_INSTANCE.availability_status, AVAILABLE)
        self.assertEqual(GERMAN_LAW_LOCAL_INSTANCE.expected_module_descriptor_hash, EXPECTED_GERMAN_LAW_DESCRIPTOR.descriptor_hash)
        self.assertNotIn("path", GERMAN_LAW_LOCAL_INSTANCE.to_dict())

    def test_instance_identity_is_immutable_deterministic_and_location_independent(self):
        descriptor = module_descriptor()
        first = instance_descriptor(descriptor)
        second = instance_descriptor(descriptor)
        self.assertEqual(first.instance_hash, second.instance_hash)
        self.assertTrue(first.__dataclass_params__.frozen)
        self.assertTrue(hasattr(type(first), "__slots__"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.instance_id = "mutated"
        serialized = str(first.to_dict())
        self.assertNotIn("/home/", serialized)
        self.assertNotIn("/media/", serialized)

    def test_instance_authority_and_default_activation_are_impossible(self):
        instance = instance_descriptor(module_descriptor())
        for field in AUTHORITY_FLAG_NAMES:
            with self.subTest(field=field):
                with self.assertRaises(KnowledgeModuleError):
                    replace(instance, instance_hash="", **{field: True})
        with self.assertRaises(KnowledgeModuleError):
            replace(instance, instance_hash="", enabled_by_default=True)

    def test_reserved_remote_transport_is_schema_only(self):
        descriptor = module_descriptor("remote-test-1a")
        remote = KnowledgeModuleInstanceDescriptor(
            schema_version=INSTANCE_SCHEMA_VERSION,
            instance_id="remote-test-1a-service",
            module_id=descriptor.module_id,
            module_version=descriptor.module_version,
            deployment_id="remote-test-1a-deployment",
            transport_kind=REMOTE_READ_ONLY_SERVICE,
            availability_status=TRANSPORT_NOT_IMPLEMENTED,
            corpus_snapshot_ids=descriptor.corpus_snapshot_ids,
            temporal_snapshot_id=descriptor.temporal_snapshot_id,
            instance_configuration_hash="a" * 64,
            expected_module_descriptor_hash=descriptor.descriptor_hash,
            priority=100,
        )
        self.assertEqual(remote.availability_status, TRANSPORT_NOT_IMPLEMENTED)
        self.assertFalse(remote.can_call_provider)
        self.assertFalse(remote.can_execute)


if __name__ == "__main__":
    unittest.main()
