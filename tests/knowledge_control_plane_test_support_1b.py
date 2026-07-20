from __future__ import annotations

from dataclasses import replace

from runtime.knowledge_modules.contracts import (
    DESCRIPTOR_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION,
    KnowledgeModuleDescriptor,
    KnowledgeModuleFailure,
    KnowledgeModuleVerificationResult,
    canonical_hash,
)
from runtime.knowledge_modules.instances import (
    AVAILABLE,
    INSTANCE_SCHEMA_VERSION,
    KnowledgeModuleInstanceDescriptor,
    KnowledgeModuleInstanceRegistration,
)
from runtime.knowledge_modules.planning import KNOWLEDGE_QUERY_SCHEMA_VERSION, KnowledgeQuery
from runtime.knowledge_modules.policy import DEFAULT_KNOWLEDGE_HUB_POLICY, KnowledgeHubPolicy
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
from runtime.knowledge_modules.transports import LOCAL_READ_ONLY_PROCESS
from tests.knowledge_module_test_support_1a import (
    SHA_A,
    SHA_B,
    SyntheticAdapter as LegacySyntheticAdapter,
    synthetic_configuration,
)


def module_descriptor(module_id: str = "alpha-knowledge-1a", *, domain: str = "TEST") -> KnowledgeModuleDescriptor:
    return KnowledgeModuleDescriptor(
        schema_version=DESCRIPTOR_SCHEMA_VERSION,
        module_id=module_id,
        module_version="1a",
        display_name=f"Synthetic {module_id}",
        description="Test-only provider-independent knowledge module.",
        domain=domain,
        subdomains=("SYNTHETIC",),
        jurisdictions=("DE-BUND",),
        languages=("de",),
        source_classes=("OFFICIAL_CONSOLIDATED_TEXT",),
        corpus_snapshot_ids=("synthetic-snapshot-1a",),
        temporal_snapshot_id="synthetic-temporal-1a",
        retrieval_modes=("SOURCE_DISCOVERY", "VERIFIED_AS_OF"),
        supported_filters=("as_of_date", "jurisdictions", "languages"),
        coverage_status="SYNTHETIC_ONLY",
        currentness_status="PARTIAL_TEMPORAL_COVERAGE",
        licence_status="INTERNAL_RESEARCH_ONLY",
        known_limitations=("Synthetic test evidence only.",),
        enabled_by_default=False,
        authority_status="NON_AUTHORITATIVE",
        capability_ids=(),
    )


def instance_descriptor(
    descriptor: KnowledgeModuleDescriptor,
    *,
    instance_id: str | None = None,
    transport_kind: str = LOCAL_READ_ONLY_PROCESS,
    availability_status: str = AVAILABLE,
    priority: int = 100,
) -> KnowledgeModuleInstanceDescriptor:
    return KnowledgeModuleInstanceDescriptor(
        schema_version=INSTANCE_SCHEMA_VERSION,
        instance_id=instance_id or f"{descriptor.module_id}-local",
        module_id=descriptor.module_id,
        module_version=descriptor.module_version,
        deployment_id=f"{descriptor.module_id}-deployment",
        transport_kind=transport_kind,
        availability_status=availability_status,
        corpus_snapshot_ids=descriptor.corpus_snapshot_ids,
        temporal_snapshot_id=descriptor.temporal_snapshot_id,
        instance_configuration_hash=canonical_hash(
            {"module_id": descriptor.module_id, "transport_kind": transport_kind}
        ),
        expected_module_descriptor_hash=descriptor.descriptor_hash,
        priority=priority,
    )


def registry_with(
    *entries: tuple[KnowledgeModuleDescriptor, type, KnowledgeModuleInstanceDescriptor],
) -> KnowledgeModuleRegistry:
    registry = KnowledgeModuleRegistry()
    for descriptor, adapter, _instance in entries:
        registry = registry.register_static_module(
            KnowledgeModuleRegistration(descriptor, adapter)
        )
    for _descriptor, adapter, instance in entries:
        registry = registry.register_instance(
            KnowledgeModuleInstanceRegistration(instance, adapter)
        )
    return registry


def selection(
    descriptor: KnowledgeModuleDescriptor,
    instance: KnowledgeModuleInstanceDescriptor,
    *,
    priority: int = 0,
    enabled: bool = True,
    max_results: int = 10,
    max_context: int = 16_000,
    retrieval_mode: str = "SOURCE_DISCOVERY",
    filters: tuple[tuple[str, object], ...] = (),
) -> KnowledgeProfileModuleSelection:
    return KnowledgeProfileModuleSelection(
        schema_version=PROFILE_MODULE_SCHEMA_VERSION,
        module_id=descriptor.module_id,
        instance_id=instance.instance_id,
        enabled=enabled,
        priority=priority,
        per_module_max_results=max_results,
        per_module_max_context_characters=max_context,
        retrieval_mode=retrieval_mode,
        module_specific_filters=filters,
    )


def profile(
    *selections: KnowledgeProfileModuleSelection,
    max_modules: int = 8,
    max_results: int = 80,
    max_context: int = 64_000,
) -> KnowledgeProfile:
    return KnowledgeProfile(
        schema_version=PROFILE_SCHEMA_VERSION,
        profile_id="synthetic-request-profile-1b",
        display_name="Synthetic request profile",
        selected_modules=tuple(selections),
        global_max_modules=max_modules,
        global_max_results=max_results,
        global_max_context_characters=max_context,
    )


def query(question: str = "§ 1 SYN") -> KnowledgeQuery:
    return KnowledgeQuery(
        schema_version=KNOWLEDGE_QUERY_SCHEMA_VERSION,
        question=question,
    )


def configurations(*descriptors: KnowledgeModuleDescriptor):
    return {
        f"{descriptor.module_id}-local": synthetic_configuration(descriptor.module_id)
        for descriptor in descriptors
    }


def _synthetic_query_from_plan(plan):
    from runtime.knowledge_modules.selection import KnowledgeModuleQuery

    filters = dict(plan.module_specific_filters)
    return KnowledgeModuleQuery(
        question=plan.question,
        retrieval_mode=plan.retrieval_mode,
        as_of_date=filters.get("as_of_date"),
        jurisdictions=tuple(filters.get("jurisdictions", ("DE-BUND",))),
        document_types=tuple(filters.get("document_types", ())),
        source_classes=tuple(filters.get("source_classes", ())),
        languages=tuple(filters.get("languages", ("de",))),
        include_administrative_rules=filters.get("include_administrative_rules", False),
        max_results=plan.max_results,
        max_excerpt_characters=plan.max_excerpt_characters,
        max_total_context_characters=plan.max_total_context_characters,
    )


class SyntheticAdapter(LegacySyntheticAdapter):
    def query_plan(self, configuration, plan, expected_descriptor):
        return self.query(
            configuration,
            _synthetic_query_from_plan(plan),
            expected_descriptor,
        )


class NonfatalFailingAdapter(SyntheticAdapter):
    def verify(self, configuration, expected_descriptor):
        del configuration
        failure = KnowledgeModuleFailure.create(
            expected_descriptor.module_id,
            "MODULE_VERIFICATION_FAILED",
            "synthetic unavailable module",
        )
        return KnowledgeModuleVerificationResult(
            schema_version=VERIFICATION_SCHEMA_VERSION,
            module_id=expected_descriptor.module_id,
            module_version=expected_descriptor.module_version,
            valid=False,
            status="MODULE_VERIFICATION_FAILED",
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


class AuthorityClaimingAdapter(SyntheticAdapter):
    def verify(self, configuration, expected_descriptor):
        from runtime.knowledge_modules.contracts import KnowledgeModuleError

        del configuration, expected_descriptor
        raise KnowledgeModuleError(
            "MODULE_AUTHORITY_CLAIM_BLOCKED", "synthetic adapter claimed authority"
        )


class RecordingAdapter(SyntheticAdapter):
    calls: list[tuple[str, str]] = []

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    def verify(self, configuration, expected_descriptor):
        type(self).calls.append(("verify", expected_descriptor.module_id))
        return super().verify(configuration, expected_descriptor)

    def query(self, configuration, knowledge_query, expected_descriptor):
        type(self).calls.append(("query", expected_descriptor.module_id))
        return super().query(configuration, knowledge_query, expected_descriptor)

def policy(**changes) -> KnowledgeHubPolicy:
    return replace(DEFAULT_KNOWLEDGE_HUB_POLICY, policy_hash="", **changes)


__all__ = (
    "AuthorityClaimingAdapter",
    "NonfatalFailingAdapter",
    "RecordingAdapter",
    "SHA_A",
    "SHA_B",
    "SyntheticAdapter",
    "configurations",
    "instance_descriptor",
    "module_descriptor",
    "policy",
    "profile",
    "query",
    "registry_with",
    "selection",
    "synthetic_configuration",
)
