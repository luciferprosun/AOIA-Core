from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.hub import KnowledgeHub1B
from runtime.knowledge_modules.instances import (
    TRANSPORT_NOT_IMPLEMENTED,
    KnowledgeModuleInstanceDescriptor,
)
from runtime.knowledge_modules.transports import REMOTE_READ_ONLY_SERVICE
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    instance_descriptor,
    module_descriptor,
    profile,
    registry_with,
    selection,
    synthetic_configuration,
)


class KnowledgeModuleAvailability1BTests(unittest.TestCase):
    def test_reserved_remote_transport_fails_closed(self):
        descriptor = module_descriptor("remote-module-1a")
        local = instance_descriptor(descriptor)
        remote = KnowledgeModuleInstanceDescriptor(
            schema_version=local.schema_version,
            instance_id="remote-module-1a-service",
            module_id=descriptor.module_id,
            module_version=descriptor.module_version,
            deployment_id="remote-module-1a-deployment",
            transport_kind=REMOTE_READ_ONLY_SERVICE,
            availability_status=TRANSPORT_NOT_IMPLEMENTED,
            corpus_snapshot_ids=descriptor.corpus_snapshot_ids,
            temporal_snapshot_id=descriptor.temporal_snapshot_id,
            instance_configuration_hash=local.instance_configuration_hash,
            expected_module_descriptor_hash=descriptor.descriptor_hash,
            priority=100,
        )
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, remote)))
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.validate_profile(profile(selection(descriptor, remote)))
        self.assertEqual(caught.exception.status, "TRANSPORT_NOT_IMPLEMENTED")

    def test_exact_instance_is_required_and_no_failover_occurs(self):
        descriptor = module_descriptor()
        requested = instance_descriptor(descriptor, instance_id="alpha-knowledge-1a-primary")
        alternate = instance_descriptor(descriptor, instance_id="alpha-knowledge-1a-alternate")
        # A registry intentionally rejects a second logical tuple, so register the
        # second concrete instance through the immutable API.
        registry = registry_with((descriptor, SyntheticAdapter, requested))
        from runtime.knowledge_modules.instances import KnowledgeModuleInstanceRegistration

        registry = registry.register_instance(KnowledgeModuleInstanceRegistration(alternate, SyntheticAdapter))
        hub = KnowledgeHub1B(registry)
        missing = instance_descriptor(descriptor, instance_id="alpha-knowledge-1a-missing")
        with self.assertRaises(KnowledgeModuleError) as caught:
            hub.validate_profile(profile(selection(descriptor, missing)))
        self.assertEqual(caught.exception.status, "MODULE_INSTANCE_NOT_REGISTERED")
        self.assertEqual([item.instance_id for item in hub.list_module_instances()], [alternate.instance_id, requested.instance_id])

    def test_hub_without_any_registration_still_supports_zero_modules(self):
        from runtime.knowledge_modules.registry import KnowledgeModuleRegistry

        hub = KnowledgeHub1B(KnowledgeModuleRegistry())
        self.assertEqual(hub.list_module_descriptors(), ())
        self.assertEqual(hub.validate_profile(profile()), ())

    def test_direct_verify_and_query_operations_keep_exact_instance_binding(self):
        descriptor = module_descriptor()
        instance = instance_descriptor(descriptor)
        hub = KnowledgeHub1B(registry_with((descriptor, SyntheticAdapter, instance)))
        configuration = synthetic_configuration(descriptor.module_id)
        verification = hub.verify_instance(instance.instance_id, configuration)
        self.assertTrue(verification.valid)
        from tests.knowledge_control_plane_test_support_1b import query

        plan = hub.plan_query(profile(selection(descriptor, instance)), query()).module_plans[0]
        bundle = hub.query_instance(instance.instance_id, plan, configuration)
        self.assertEqual(bundle.module_id, descriptor.module_id)
        self.assertEqual(bundle.descriptor_hash, descriptor.descriptor_hash)


if __name__ == "__main__":
    unittest.main()
