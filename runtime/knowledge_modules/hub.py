"""Explicit-selection Knowledge Hub 1A compatibility and generic 1B control plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from runtime.knowledge_modules.contracts import (
    KnowledgeModuleConfiguration,
    KnowledgeModuleDescriptor,
    KnowledgeModuleError,
    KnowledgeModuleFailure,
    KnowledgeModuleVerificationResult,
)
from runtime.knowledge_modules.evidence import (
    HUB_RESULT_SCHEMA_VERSION,
    KnowledgeEvidenceBundle,
    KnowledgeHubResult,
)
from runtime.knowledge_modules.composite import (
    EXECUTION_RESULT_SCHEMA_VERSION,
    KnowledgeHubExecutionResult,
    ModuleExecutionOutcome,
    build_composite_evidence_bundle,
)
from runtime.knowledge_modules.instances import (
    AVAILABLE,
    DEGRADED,
    UNAVAILABLE,
    CONTROL_RECORD_SCHEMA_VERSION,
    KnowledgeModuleControlRecord,
)
from runtime.knowledge_modules.planning import (
    CompositeKnowledgeQueryPlan,
    KnowledgeQuery,
    ModuleQueryPlan,
    build_composite_query_plan,
)
from runtime.knowledge_modules.policy import (
    DEFAULT_KNOWLEDGE_HUB_POLICY,
    KnowledgeHubPolicy,
)
from runtime.knowledge_modules.profiles import KnowledgeProfile
from runtime.knowledge_modules.registry import KnowledgeModuleRegistry
from runtime.knowledge_modules.selection import (
    KnowledgeModuleQuery,
    KnowledgeModuleSelection,
)


@dataclass(frozen=True, slots=True)
class KnowledgeHub1A:
    registry: KnowledgeModuleRegistry

    def list_modules(self) -> tuple[KnowledgeModuleDescriptor, ...]:
        return self.registry.list_descriptors()

    def get_descriptor(self, module_id: str) -> KnowledgeModuleDescriptor:
        registration = self.registry.resolve(module_id)
        if registration is None:
            raise KnowledgeModuleError("UNKNOWN_MODULE_ID", f"module is not registered: {module_id}")
        return registration.descriptor

    def validate_selection(
        self,
        selection: KnowledgeModuleSelection,
    ) -> tuple[KnowledgeModuleDescriptor, ...]:
        descriptors: list[KnowledgeModuleDescriptor] = []
        for module_id in selection.module_ids:
            registration = self.registry.resolve(module_id)
            if registration is None:
                raise KnowledgeModuleError(
                    "UNKNOWN_MODULE_ID", f"module is not registered: {module_id}"
                )
            if registration.descriptor.enabled_by_default:
                raise KnowledgeModuleError(
                    "MODULE_AUTHORITY_CLAIM_BLOCKED", "registered module enabled itself"
                )
            descriptors.append(registration.descriptor)
        return tuple(descriptors)

    def verify_module(
        self,
        module_id: str,
        configuration: KnowledgeModuleConfiguration,
    ) -> KnowledgeModuleVerificationResult:
        registration = self.registry.resolve(module_id)
        if registration is None:
            raise KnowledgeModuleError("UNKNOWN_MODULE_ID", f"module is not registered: {module_id}")
        adapter = registration.adapter_factory()
        return adapter.verify(configuration, registration.descriptor)

    def query(
        self,
        selection: KnowledgeModuleSelection,
        query: KnowledgeModuleQuery,
        configurations: Mapping[str, KnowledgeModuleConfiguration],
    ) -> KnowledgeHubResult:
        descriptors = self.validate_selection(selection)
        if not descriptors:
            return KnowledgeHubResult(
                schema_version=HUB_RESULT_SCHEMA_VERSION,
                status="NO_KNOWLEDGE_MODULE_SELECTED",
                selection_hash=selection.selection_hash,
                selected_module_ids=(),
                verification_results=(),
                evidence_bundles=(),
                module_failures=(),
            )

        verification_results: list[KnowledgeModuleVerificationResult] = []
        bundles: list[KnowledgeEvidenceBundle] = []
        failures: list[KnowledgeModuleFailure] = []
        for descriptor in descriptors:
            registration = self.registry.resolve(descriptor.module_id)
            assert registration is not None
            configuration = configurations.get(descriptor.module_id)
            if not isinstance(configuration, KnowledgeModuleConfiguration):
                failures.append(
                    KnowledgeModuleFailure.create(
                        descriptor.module_id,
                        "MODULE_NOT_AVAILABLE",
                        "explicit module configuration is missing",
                    )
                )
                continue
            adapter = registration.adapter_factory()
            try:
                verification = adapter.verify(configuration, descriptor)
            except KnowledgeModuleError as exc:
                failures.append(
                    KnowledgeModuleFailure.create(descriptor.module_id, exc.status, exc.reason)
                )
                continue
            except Exception:
                failures.append(
                    KnowledgeModuleFailure.create(
                        descriptor.module_id,
                        "MODULE_OUTPUT_MALFORMED",
                        "module verification failed closed",
                    )
                )
                continue
            verification_results.append(verification)
            if not verification.valid:
                failures.extend(verification.failures)
                continue
            try:
                bundles.append(adapter.query(configuration, query, descriptor))
            except KnowledgeModuleError as exc:
                failures.append(
                    KnowledgeModuleFailure.create(descriptor.module_id, exc.status, exc.reason)
                )
            except Exception:
                failures.append(
                    KnowledgeModuleFailure.create(
                        descriptor.module_id,
                        "MODULE_OUTPUT_MALFORMED",
                        "module query failed closed",
                    )
                )

        if bundles and not failures:
            status = (
                "KNOWLEDGE_EVIDENCE_AVAILABLE"
                if any(bundle.evidence_items for bundle in bundles)
                else "KNOWLEDGE_RETRIEVAL_NO_EVIDENCE"
            )
        elif bundles:
            status = "PARTIAL_KNOWLEDGE_MODULE_FAILURE"
        else:
            status = "KNOWLEDGE_MODULE_FAILURE"
        return KnowledgeHubResult(
            schema_version=HUB_RESULT_SCHEMA_VERSION,
            status=status,
            selection_hash=selection.selection_hash,
            selected_module_ids=selection.module_ids,
            verification_results=tuple(verification_results),
            evidence_bundles=tuple(bundles),
            module_failures=tuple(failures),
        )


_GLOBAL_INTEGRITY_FAILURES = {
    "COMPOSITE_BUILD_FAILED",
    "CORPUS_VERIFICATION_FAILED",
    "GLOBAL_BUDGET_EXCEEDED",
    "MODULE_AUTHORITY_CLAIM_BLOCKED",
    "PROFILE_INVALID",
    "PROFILE_LIMIT_EXCEEDED",
}


@dataclass(frozen=True, slots=True)
class KnowledgeHub1B:
    """Generic sequential control plane over explicit module instances."""

    registry: KnowledgeModuleRegistry
    policy: KnowledgeHubPolicy = DEFAULT_KNOWLEDGE_HUB_POLICY

    def __post_init__(self) -> None:
        self.registry.validate_registry()

    def list_module_descriptors(self) -> tuple[KnowledgeModuleDescriptor, ...]:
        return self.registry.list_module_descriptors()

    def get_module_descriptor(self, module_id: str) -> KnowledgeModuleDescriptor:
        return self.registry.get_module_descriptor(module_id)

    def list_module_instances(self, module_id: str | None = None):
        return self.registry.list_module_instances(module_id)

    def get_module_instance(self, instance_id: str):
        return self.registry.get_module_instance(instance_id)

    def validate_profile(self, profile: KnowledgeProfile) -> tuple[tuple[object, ...], ...]:
        return self.registry.resolve_profile(profile, self.policy)

    def plan_query(
        self,
        profile: KnowledgeProfile,
        query: KnowledgeQuery,
    ) -> CompositeKnowledgeQueryPlan:
        return build_composite_query_plan(self.registry, profile, query, self.policy)

    def verify_instance(
        self,
        instance_id: str,
        configuration: object,
    ) -> KnowledgeModuleVerificationResult:
        instance = self.registry.get_module_instance(instance_id)
        descriptor = self.registry.get_module_descriptor(instance.module_id)
        result = self.registry.verify_instance(instance_id, configuration)
        if (
            result.module_id != descriptor.module_id
            or result.module_version != descriptor.module_version
            or result.descriptor_hash != descriptor.descriptor_hash
        ):
            raise KnowledgeModuleError(
                "MODULE_DESCRIPTOR_MISMATCH", "verified instance identity differs"
            )
        return result

    def query_instance(
        self,
        instance_id: str,
        query: ModuleQueryPlan,
        configuration: object,
    ) -> KnowledgeEvidenceBundle:
        bundle = self.registry.query_instance(instance_id, query, configuration)
        self._validate_bundle(query, bundle)
        return bundle

    def control_model(
        self,
        profile: KnowledgeProfile | None = None,
    ) -> tuple[KnowledgeModuleControlRecord, ...]:
        selected = {
            item.module_id
            for item in (() if profile is None else profile.selected_modules)
            if item.enabled
        }
        controls: list[KnowledgeModuleControlRecord] = []
        for descriptor in self.registry.list_module_descriptors():
            instances = self.registry.list_module_instances(descriptor.module_id)
            available = tuple(
                item.instance_id
                for item in instances
                if item.availability_status in (AVAILABLE, DEGRADED)
            )
            if any(item.availability_status == AVAILABLE for item in instances):
                status = AVAILABLE
            elif any(item.availability_status == DEGRADED for item in instances):
                status = DEGRADED
            elif instances:
                status = instances[0].availability_status
            else:
                status = UNAVAILABLE
            controls.append(
                KnowledgeModuleControlRecord(
                    schema_version=CONTROL_RECORD_SCHEMA_VERSION,
                    module_id=descriptor.module_id,
                    display_name=descriptor.display_name,
                    description=descriptor.description,
                    domain=descriptor.domain,
                    module_version=descriptor.module_version,
                    available_instances=available,
                    availability_status=status,
                    enabled_by_default=False,
                    currently_selected=descriptor.module_id in selected,
                    supported_retrieval_modes=descriptor.retrieval_modes,
                    known_limitations=descriptor.known_limitations,
                )
            )
        return tuple(controls)

    def execute(
        self,
        profile: KnowledgeProfile,
        query: KnowledgeQuery,
        instance_configurations: Mapping[str, object],
    ) -> KnowledgeHubExecutionResult:
        plan = self.plan_query(profile, query)
        outcomes: dict[str, ModuleExecutionOutcome] = {}
        failures: list[KnowledgeModuleFailure] = []
        verification_results: list[KnowledgeModuleVerificationResult] = []
        for module_plan in plan.module_plans:
            instance_registration = self.registry.resolve_instance(module_plan.instance_id)
            logical_registration = self.registry.resolve(module_plan.module_id)
            if instance_registration is None or logical_registration is None:
                raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "planned registration disappeared")
            if module_plan.instance_id not in instance_configurations:
                failures.append(
                    self._failure(
                        module_plan.module_id,
                        module_plan.instance_id,
                        "MODULE_UNAVAILABLE",
                        "explicit instance configuration is missing",
                    )
                )
                continue
            configuration = instance_configurations[module_plan.instance_id]
            adapter = instance_registration.adapter_factory()
            try:
                verification = adapter.verify(configuration, logical_registration.descriptor)
            except KnowledgeModuleError as exc:
                self._raise_global(exc)
                failures.append(
                    self._failure(module_plan.module_id, module_plan.instance_id, exc.status, exc.reason)
                )
                continue
            except Exception:
                failures.append(
                    self._failure(
                        module_plan.module_id,
                        module_plan.instance_id,
                        "MODULE_VERIFICATION_FAILED",
                        "module instance verification failed closed",
                    )
                )
                continue
            verification_results.append(verification)
            if not verification.valid:
                for failure in verification.failures:
                    error = KnowledgeModuleError(failure.code, failure.message)
                    self._raise_global(error)
                    failures.append(
                        self._failure(
                            module_plan.module_id,
                            module_plan.instance_id,
                            failure.code,
                            failure.message,
                        )
                    )
                continue
            try:
                self._validate_verification(module_plan, verification)
            except KnowledgeModuleError as exc:
                self._raise_global(exc)
                failures.append(
                    self._failure(module_plan.module_id, module_plan.instance_id, exc.status, exc.reason)
                )
                continue
            try:
                query_plan = getattr(adapter, "query_plan", None)
                if not callable(query_plan):
                    raise KnowledgeModuleError(
                        "MODULE_OUTPUT_MALFORMED",
                        "instance adapter does not implement the generic query-plan boundary",
                    )
                bundle = query_plan(configuration, module_plan, logical_registration.descriptor)
            except KnowledgeModuleError as exc:
                self._raise_global(exc)
                failures.append(
                    self._failure(module_plan.module_id, module_plan.instance_id, exc.status, exc.reason)
                )
                continue
            except Exception:
                failures.append(
                    self._failure(
                        module_plan.module_id,
                        module_plan.instance_id,
                        "MODULE_OUTPUT_MALFORMED",
                        "module query failed closed",
                    )
                )
                continue
            try:
                self._validate_bundle(module_plan, bundle)
            except KnowledgeModuleError as exc:
                self._raise_global(exc)
                failures.append(
                    self._failure(module_plan.module_id, module_plan.instance_id, exc.status, exc.reason)
                )
                continue
            outcomes[module_plan.instance_id] = ModuleExecutionOutcome(
                descriptor=logical_registration.descriptor,
                instance=instance_registration.descriptor,
                bundle=bundle,
            )
        composite = build_composite_evidence_bundle(
            profile,
            plan,
            outcomes,
            tuple(failures),
            self.policy,
        )
        if not plan.module_plans:
            status = "NO_KNOWLEDGE_MODULE_SELECTED"
        elif outcomes and failures:
            status = "PARTIAL_KNOWLEDGE_MODULE_FAILURE"
        elif failures:
            status = "KNOWLEDGE_MODULE_FAILURE"
        elif composite.total_evidence_items:
            status = "KNOWLEDGE_EVIDENCE_AVAILABLE"
        else:
            status = "KNOWLEDGE_RETRIEVAL_NO_EVIDENCE"
        return KnowledgeHubExecutionResult(
            schema_version=EXECUTION_RESULT_SCHEMA_VERSION,
            status=status,
            profile=profile,
            query_plan=plan,
            composite_bundle=composite,
            verification_results=tuple(verification_results),
        )

    @staticmethod
    def _failure(
        module_id: str,
        instance_id: str,
        code: str,
        message: str,
    ) -> KnowledgeModuleFailure:
        normalized = {
            "MODULE_NOT_AVAILABLE": "MODULE_UNAVAILABLE",
            "CORPUS_SNAPSHOT_MISMATCH": "SNAPSHOT_MISMATCH",
            "TEMPORAL_SNAPSHOT_MISMATCH": "SNAPSHOT_MISMATCH",
        }.get(code, code)
        return KnowledgeModuleFailure.create(
            module_id,
            normalized,
            message,
            details=(("instance_id", instance_id),),
        )

    @staticmethod
    def _raise_global(error: KnowledgeModuleError) -> None:
        if error.status in _GLOBAL_INTEGRITY_FAILURES:
            raise error

    @staticmethod
    def _validate_verification(
        module_plan: ModuleQueryPlan,
        verification: KnowledgeModuleVerificationResult,
    ) -> None:
        if (
            verification.module_id != module_plan.module_id
            or verification.module_version != module_plan.module_version
            or verification.descriptor_hash != module_plan.expected_module_descriptor_hash
        ):
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "verified module identity differs")

    @staticmethod
    def _validate_bundle(
        module_plan: ModuleQueryPlan,
        bundle: KnowledgeEvidenceBundle,
    ) -> None:
        if (
            bundle.module_id != module_plan.module_id
            or bundle.module_version != module_plan.module_version
            or bundle.descriptor_hash != module_plan.expected_module_descriptor_hash
            or bundle.retrieval_mode != module_plan.retrieval_mode
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "module bundle binding differs")
        if (
            len(bundle.evidence_items) > module_plan.max_results
            or bundle.total_context_characters > module_plan.max_total_context_characters
            or any(len(item.bounded_excerpt) > module_plan.max_excerpt_characters for item in bundle.evidence_items)
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "module exceeded planned budget")


__all__ = ("KnowledgeHub1A", "KnowledgeHub1B")
