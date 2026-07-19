"""Immutable Knowledge Module registry metadata; it performs no dispatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from runtime.knowledge_modules.contracts import (
    KnowledgeModuleConfiguration,
    KnowledgeModuleDescriptor,
    KnowledgeModuleError,
    KnowledgeModuleVerificationResult,
    NON_AUTHORITATIVE,
)
from runtime.knowledge_modules.evidence import KnowledgeEvidenceBundle
from runtime.knowledge_modules.selection import KnowledgeModuleQuery


class KnowledgeModuleAdapter(Protocol):
    def verify(
        self,
        configuration: KnowledgeModuleConfiguration,
        expected_descriptor: KnowledgeModuleDescriptor,
    ) -> KnowledgeModuleVerificationResult: ...

    def query(
        self,
        configuration: KnowledgeModuleConfiguration,
        query: KnowledgeModuleQuery,
        expected_descriptor: KnowledgeModuleDescriptor,
    ) -> KnowledgeEvidenceBundle: ...


AdapterFactory = Callable[[], KnowledgeModuleAdapter]


@dataclass(frozen=True, slots=True)
class KnowledgeModuleRegistration:
    descriptor: KnowledgeModuleDescriptor
    adapter_factory: AdapterFactory = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.descriptor.enabled_by_default:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "registered module is enabled by default"
            )
        if not callable(self.adapter_factory):
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "adapter factory is invalid")

    @property
    def module_id(self) -> str:
        return self.descriptor.module_id

    @property
    def module_version(self) -> str:
        return self.descriptor.module_version

    def to_dict(self) -> dict[str, object]:
        return {
            "module_id": self.module_id,
            "module_version": self.module_version,
            "display_name": self.descriptor.display_name,
            "descriptor_hash": self.descriptor.descriptor_hash,
            "enabled_by_default": False,
            "authority_status": NON_AUTHORITATIVE,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeModuleRegistry:
    registrations: tuple[KnowledgeModuleRegistration, ...] = ()
    authority_status: str = NON_AUTHORITATIVE

    def __post_init__(self) -> None:
        if self.authority_status != NON_AUTHORITATIVE:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "registry cannot carry authority"
            )
        ordered = tuple(sorted(self.registrations, key=lambda item: item.module_id))
        if len(ordered) != len({item.module_id for item in ordered}):
            raise KnowledgeModuleError("DUPLICATE_MODULE_ID", "registry repeats a module ID")
        object.__setattr__(self, "registrations", ordered)

    def register(self, registration: KnowledgeModuleRegistration) -> "KnowledgeModuleRegistry":
        if any(item.module_id == registration.module_id for item in self.registrations):
            raise KnowledgeModuleError("DUPLICATE_MODULE_ID", "module ID is already registered")
        return KnowledgeModuleRegistry((*self.registrations, registration))

    def resolve(self, module_id: str) -> KnowledgeModuleRegistration | None:
        if not isinstance(module_id, str):
            raise KnowledgeModuleError("UNKNOWN_MODULE_ID", "module ID must be a string")
        return next(
            (item for item in self.registrations if item.module_id == module_id),
            None,
        )

    def list_descriptors(self) -> tuple[KnowledgeModuleDescriptor, ...]:
        return tuple(item.descriptor for item in self.registrations)


__all__ = (
    "AdapterFactory",
    "KnowledgeModuleAdapter",
    "KnowledgeModuleRegistration",
    "KnowledgeModuleRegistry",
)
