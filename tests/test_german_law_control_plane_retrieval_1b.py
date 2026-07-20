from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from runtime.knowledge_modules.german_law import (
    EXPECTED_GERMAN_LAW_DESCRIPTOR,
    EXPECTED_MANIFEST_HASHES,
    GERMAN_LAW_EXPECTED_HEAD,
    GERMAN_LAW_INSTANCE_ID,
    GERMAN_LAW_LOCAL_INSTANCE,
    GERMAN_LAW_MODULE_ID,
    GermanLawModuleAdapter,
    production_german_law_configuration,
)
from runtime.knowledge_modules.contracts import (
    VERIFICATION_SCHEMA_VERSION,
    KnowledgeModuleVerificationResult,
)
from runtime.knowledge_modules.hub import KnowledgeHub1B
from runtime.knowledge_modules.instances import KnowledgeModuleInstanceRegistration
from runtime.knowledge_modules.planning import KNOWLEDGE_QUERY_SCHEMA_VERSION, KnowledgeQuery
from runtime.knowledge_modules.profiles import (
    PROFILE_MODULE_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
    KnowledgeProfile,
    KnowledgeProfileModuleSelection,
)
from runtime.knowledge_modules.registry import (
    KnowledgeModuleRegistration,
    KnowledgeModuleRegistry,
)


GERMAN_REPOSITORY = "/home/l/AOIA_PRODUCTION/repos/AOIA-German-Law-Knowledge-Pack"
CORPUS_ROOT = "/home/l/AOIA_PRODUCTION/data/german-law-corpus"


def manifest_hashes():
    root = Path(CORPUS_ROOT).resolve()
    return tuple(
        (relative, hashlib.sha256((root / relative).read_bytes()).hexdigest())
        for relative, _ in EXPECTED_MANIFEST_HASHES
    )


class RealQueryAdapter(GermanLawModuleAdapter):
    """Keep unit execution bounded; the production CLI separately runs hat-verify."""

    def verify(self, configuration, expected_descriptor):
        return KnowledgeModuleVerificationResult(
            schema_version=VERIFICATION_SCHEMA_VERSION,
            module_id=expected_descriptor.module_id,
            module_version=expected_descriptor.module_version,
            valid=True,
            status="VERIFIED",
            repository_head=configuration.expected_repository_head,
            descriptor_hash=expected_descriptor.descriptor_hash,
            resolved_corpus_path=configuration.approved_resolved_corpus_path,
            corpus_snapshot_ids=expected_descriptor.corpus_snapshot_ids,
            temporal_snapshot_id=expected_descriptor.temporal_snapshot_id,
            manifest_hashes=configuration.expected_manifest_hashes,
            external_verification_hash="f" * 64,
            descriptor=expected_descriptor,
            failures=(),
        )


class GermanLawControlPlaneRetrieval1BTests(unittest.TestCase):
    def test_real_local_instance_retrieval_is_source_bound_and_read_only(self):
        registry = KnowledgeModuleRegistry().register_static_module(
            KnowledgeModuleRegistration(EXPECTED_GERMAN_LAW_DESCRIPTOR, RealQueryAdapter)
        ).register_instance(
            KnowledgeModuleInstanceRegistration(GERMAN_LAW_LOCAL_INSTANCE, RealQueryAdapter)
        )
        hub = KnowledgeHub1B(registry)
        profile = KnowledgeProfile(
            schema_version=PROFILE_SCHEMA_VERSION,
            profile_id="german-law-real-request-1b",
            display_name="German Law real retrieval",
            selected_modules=(
                KnowledgeProfileModuleSelection(
                    schema_version=PROFILE_MODULE_SCHEMA_VERSION,
                    module_id=GERMAN_LAW_MODULE_ID,
                    instance_id=GERMAN_LAW_INSTANCE_ID,
                    enabled=True,
                    priority=0,
                    per_module_max_results=8,
                    per_module_max_context_characters=16_000,
                    retrieval_mode="SOURCE_DISCOVERY",
                ),
            ),
            global_max_modules=8,
            global_max_results=8,
            global_max_context_characters=16_000,
        )
        query = KnowledgeQuery(
            schema_version=KNOWLEDGE_QUERY_SCHEMA_VERSION,
            question="§ 2 NachwG",
        )
        configuration = production_german_law_configuration(
            module_repository_path=GERMAN_REPOSITORY,
            corpus_data_root=CORPUS_ROOT,
            expected_repository_head=GERMAN_LAW_EXPECTED_HEAD,
        )
        before = manifest_hashes()
        first = hub.execute(profile, query, {GERMAN_LAW_INSTANCE_ID: configuration})
        self.assertEqual(before, manifest_hashes())
        self.assertEqual(first.status, "KNOWLEDGE_EVIDENCE_AVAILABLE")
        wrapper = first.composite_bundle.module_bundles[0]
        self.assertEqual(wrapper.instance_id, GERMAN_LAW_INSTANCE_ID)
        self.assertEqual(len(wrapper.evidence_bundle.evidence_items), 1)
        self.assertRegex(wrapper.item_provenance[0].source_object_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(wrapper.item_provenance[0].temporal_status, "CURRENTNESS_NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
