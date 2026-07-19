from __future__ import annotations

from dataclasses import replace

from runtime.knowledge_modules.contracts import (
    DESCRIPTOR_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION,
    KnowledgeModuleConfiguration,
    KnowledgeModuleDescriptor,
    KnowledgeModuleFailure,
    KnowledgeModuleVerificationResult,
)
from runtime.knowledge_modules.evidence import (
    KnowledgeCoverageWarning,
    KnowledgeEvidenceBundle,
    evidence_bundle_from_fields,
    evidence_item_from_fields,
)
from runtime.knowledge_modules.selection import KnowledgeModuleQuery


SHA_A = "a" * 64
SHA_B = "b" * 64
HEAD_A = "1" * 40


def synthetic_descriptor(module_id: str = "synthetic-law-1a") -> KnowledgeModuleDescriptor:
    return KnowledgeModuleDescriptor(
        schema_version=DESCRIPTOR_SCHEMA_VERSION,
        module_id=module_id,
        module_version="1a",
        display_name="Synthetic Law",
        description="Deterministic test-only read-only module.",
        domain="LAW",
        subdomains=("SYNTHETIC",),
        jurisdictions=("DE-BUND",),
        languages=("de",),
        source_classes=("OFFICIAL_CONSOLIDATED_TEXT",),
        corpus_snapshot_ids=("synthetic-snapshot-1a",),
        temporal_snapshot_id="synthetic-temporal-1a",
        retrieval_modes=("SOURCE_DISCOVERY", "VERIFIED_AS_OF"),
        supported_filters=("jurisdictions", "languages"),
        coverage_status="SYNTHETIC_ONLY",
        currentness_status="PARTIAL_TEMPORAL_COVERAGE",
        licence_status="INTERNAL_RESEARCH_ONLY",
        known_limitations=("Synthetic test evidence only.",),
        enabled_by_default=False,
        authority_status="NON_AUTHORITATIVE",
        capability_ids=(),
    )


def synthetic_configuration(module_id: str = "synthetic-law-1a") -> KnowledgeModuleConfiguration:
    return KnowledgeModuleConfiguration(
        schema_version="knowledge-module-configuration-1a",
        module_repository_path="/tmp/synthetic-module",
        corpus_data_root="/tmp/synthetic-corpus",
        approved_resolved_corpus_path="/tmp/synthetic-corpus",
        expected_repository_head=HEAD_A,
        expected_module_id=module_id,
        expected_module_version="1a",
        expected_descriptor_hash=SHA_A,
        expected_corpus_snapshot_id="synthetic-snapshot-1a",
        expected_corpus_snapshot_ids=("synthetic-snapshot-1a",),
        expected_temporal_snapshot_id="synthetic-temporal-1a",
        expected_eu_snapshot_id="synthetic-eu-1a",
        expected_eu_snapshot_manifest_hash=SHA_B,
        expected_manifest_hashes=(("manifests/small.json", SHA_A),),
    )


def synthetic_bundle(
    descriptor: KnowledgeModuleDescriptor,
    query: KnowledgeModuleQuery,
    *,
    excerpt: str = "Synthetic source-bound excerpt.",
) -> KnowledgeEvidenceBundle:
    temporal_status = (
        "CURRENTNESS_NOT_VERIFIED"
        if query.retrieval_mode == "SOURCE_DISCOVERY"
        else "VERIFIED_AS_OF"
    )
    warnings = (
        ("CURRENTNESS_NOT_VERIFIED",)
        if query.retrieval_mode == "SOURCE_DISCOVERY"
        else ()
    )
    item = evidence_item_from_fields(
        module_id=descriptor.module_id,
        module_version=descriptor.module_version,
        corpus_snapshot_id="synthetic-snapshot-1a",
        temporal_snapshot_id="synthetic-temporal-1a",
        retrieval_mode=query.retrieval_mode,
        jurisdiction="DE-BUND",
        document_id=f"{descriptor.module_id}:document-1",
        provision_id=f"{descriptor.module_id}:provision-1",
        version_id=f"{descriptor.module_id}:version-1",
        document_type="STATUTE_OR_REGULATION",
        source_class="OFFICIAL_CONSOLIDATED_TEXT",
        official_title="Synthetic Statute",
        official_abbreviation="SYN",
        provision_number="1",
        heading="Synthetic heading",
        bounded_excerpt=excerpt,
        excerpt_truncated=False,
        source_url="https://official.invalid/synthetic",
        source_object_sha256=SHA_A,
        publication_reference=None,
        publication_date="2025-01-01",
        effective_from=(
            "2025-01-01" if query.retrieval_mode == "VERIFIED_AS_OF" else None
        ),
        effective_until=None,
        temporal_status=temporal_status,
        licence_status="INTERNAL_RESEARCH_ONLY",
        retrieval_score=1.0,
        warnings=warnings,
        source_snapshot_id="synthetic-snapshot-1a",
        authority_status="NON_AUTHORITATIVE_EVIDENCE",
    )
    coverage = (
        (
            KnowledgeCoverageWarning.create(
                "CURRENTNESS_NOT_VERIFIED",
                "Synthetic discovery does not establish currentness.",
            ),
        )
        if query.retrieval_mode == "SOURCE_DISCOVERY"
        else ()
    )
    return evidence_bundle_from_fields(
        query_hash=query.query_hash,
        module_id=descriptor.module_id,
        module_version=descriptor.module_version,
        descriptor_hash=descriptor.descriptor_hash,
        retrieval_mode=query.retrieval_mode,
        query_as_of_date=query.as_of_date,
        corpus_snapshot_id="synthetic-snapshot-1a",
        temporal_snapshot_id="synthetic-temporal-1a",
        evidence_items=(item,),
        coverage_warnings=coverage,
        retrieval_failures=(),
        total_context_characters=len(excerpt),
        truncated=False,
        authority_status="NON_AUTHORITATIVE_EVIDENCE_BUNDLE",
    )


class SyntheticAdapter:
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
            external_verification_hash=SHA_B,
            descriptor=expected_descriptor,
            failures=(),
        )

    def query(self, configuration, query, expected_descriptor):
        del configuration
        return synthetic_bundle(expected_descriptor, query)


class FailingAdapter:
    def verify(self, configuration, expected_descriptor):
        del configuration
        failure = KnowledgeModuleFailure.create(
            expected_descriptor.module_id,
            "CORPUS_VERIFICATION_FAILED",
            "synthetic fail-closed verification",
        )
        return KnowledgeModuleVerificationResult(
            schema_version=VERIFICATION_SCHEMA_VERSION,
            module_id=expected_descriptor.module_id,
            module_version=expected_descriptor.module_version,
            valid=False,
            status="CORPUS_VERIFICATION_FAILED",
            repository_head=None,
            descriptor_hash=None,
            resolved_corpus_path=None,
            corpus_snapshot_ids=(),
            temporal_snapshot_id=None,
            manifest_hashes=(),
            external_verification_hash=None,
            descriptor=None,
            failures=(failure,),
        )

    def query(self, configuration, query, expected_descriptor):
        raise AssertionError("query must not run after failed verification")


class NoEvidenceAdapter(SyntheticAdapter):
    def query(self, configuration, query, expected_descriptor):
        del configuration
        failure = KnowledgeModuleFailure.create(
            expected_descriptor.module_id,
            "NO_TEMPORAL_EVIDENCE",
            "synthetic temporal evidence is unavailable",
        )
        return evidence_bundle_from_fields(
            query_hash=query.query_hash,
            module_id=expected_descriptor.module_id,
            module_version=expected_descriptor.module_version,
            descriptor_hash=expected_descriptor.descriptor_hash,
            retrieval_mode=query.retrieval_mode,
            query_as_of_date=query.as_of_date,
            corpus_snapshot_id="synthetic-snapshot-1a",
            temporal_snapshot_id="synthetic-temporal-1a",
            evidence_items=(),
            coverage_warnings=(),
            retrieval_failures=(failure,),
            total_context_characters=0,
            truncated=False,
            authority_status="NON_AUTHORITATIVE_EVIDENCE_BUNDLE",
        )


def with_configuration(configuration: KnowledgeModuleConfiguration, **changes):
    return replace(configuration, **changes)
