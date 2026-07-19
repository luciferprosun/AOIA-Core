"""Minimal explicit-selection Knowledge Hub 1A."""

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


__all__ = ("KnowledgeHub1A",)
