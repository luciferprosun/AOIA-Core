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
from runtime.knowledge_modules.instances import (
    AVAILABLE,
    DEGRADED,
    DISABLED,
    SNAPSHOT_MISMATCH,
    TRANSPORT_NOT_IMPLEMENTED,
    UNAVAILABLE,
    VERSION_MISMATCH,
    KnowledgeModuleInstanceDescriptor,
    KnowledgeModuleInstanceRegistration,
)
from runtime.knowledge_modules.planning import ModuleQueryPlan
from runtime.knowledge_modules.selection import KnowledgeModuleQuery
from runtime.knowledge_modules.transports import transport_descriptor


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

    def query_plan(
        self,
        configuration: object,
        plan: ModuleQueryPlan,
        expected_descriptor: KnowledgeModuleDescriptor,
    ) -> KnowledgeEvidenceBundle: ...


AdapterFactory = Callable[[], KnowledgeModuleAdapter]
MODULE_REGISTRATION_SCHEMA_VERSION = "knowledge-module-registration-1b"


@dataclass(frozen=True, slots=True)
class KnowledgeModuleRegistration:
    descriptor: KnowledgeModuleDescriptor
    adapter_factory: AdapterFactory = field(repr=False, compare=False)
    registration_enabled: bool = True
    schema_version: str = MODULE_REGISTRATION_SCHEMA_VERSION
    authority_status: str = NON_AUTHORITATIVE

    def __post_init__(self) -> None:
        if self.descriptor.enabled_by_default:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "registered module is enabled by default"
            )
        if not callable(self.adapter_factory):
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "adapter factory is invalid")
        if type(self.registration_enabled) is not bool:
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "registration flag is invalid")
        if self.schema_version != MODULE_REGISTRATION_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "registration schema differs")
        if self.authority_status != NON_AUTHORITATIVE:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "logical registration cannot carry authority"
            )

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
    instance_registrations: tuple[KnowledgeModuleInstanceRegistration, ...] = ()

    def __post_init__(self) -> None:
        if self.authority_status != NON_AUTHORITATIVE:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "registry cannot carry authority"
            )
        ordered = tuple(sorted(self.registrations, key=lambda item: item.module_id))
        if len(ordered) != len({item.module_id for item in ordered}):
            raise KnowledgeModuleError("DUPLICATE_MODULE_ID", "registry repeats a module ID")
        object.__setattr__(self, "registrations", ordered)
        instances = tuple(sorted(self.instance_registrations, key=lambda item: item.instance_id))
        if len(instances) != len({item.instance_id for item in instances}):
            raise KnowledgeModuleError("DUPLICATE_INSTANCE_ID", "registry repeats an instance ID")
        object.__setattr__(self, "instance_registrations", instances)

    def register(self, registration: KnowledgeModuleRegistration) -> "KnowledgeModuleRegistry":
        if any(item.module_id == registration.module_id for item in self.registrations):
            raise KnowledgeModuleError("DUPLICATE_MODULE_ID", "module ID is already registered")
        return KnowledgeModuleRegistry(
            (*self.registrations, registration),
            self.authority_status,
            self.instance_registrations,
        )

    def register_static_module(
        self,
        registration: KnowledgeModuleRegistration,
    ) -> "KnowledgeModuleRegistry":
        return self.register(registration)

    def register_instance(
        self,
        registration: KnowledgeModuleInstanceRegistration,
    ) -> "KnowledgeModuleRegistry":
        if any(item.instance_id == registration.instance_id for item in self.instance_registrations):
            raise KnowledgeModuleError("DUPLICATE_INSTANCE_ID", "instance ID is already registered")
        logical = self.resolve(registration.module_id)
        if logical is None:
            raise KnowledgeModuleError("MODULE_NOT_REGISTERED", "instance module is not registered")
        self._validate_instance_binding(logical, registration.descriptor)
        return KnowledgeModuleRegistry(
            self.registrations,
            self.authority_status,
            (*self.instance_registrations, registration),
        )

    def resolve(self, module_id: str) -> KnowledgeModuleRegistration | None:
        if not isinstance(module_id, str):
            raise KnowledgeModuleError("UNKNOWN_MODULE_ID", "module ID must be a string")
        return next(
            (item for item in self.registrations if item.module_id == module_id),
            None,
        )

    def list_descriptors(self) -> tuple[KnowledgeModuleDescriptor, ...]:
        return tuple(item.descriptor for item in self.registrations)

    def list_module_descriptors(self) -> tuple[KnowledgeModuleDescriptor, ...]:
        return self.list_descriptors()

    def get_module_descriptor(self, module_id: str) -> KnowledgeModuleDescriptor:
        registration = self.resolve(module_id)
        if registration is None:
            raise KnowledgeModuleError("MODULE_NOT_REGISTERED", f"module is not registered: {module_id}")
        return registration.descriptor

    def list_module_instances(
        self,
        module_id: str | None = None,
    ) -> tuple[KnowledgeModuleInstanceDescriptor, ...]:
        if module_id is not None and self.resolve(module_id) is None:
            raise KnowledgeModuleError("MODULE_NOT_REGISTERED", f"module is not registered: {module_id}")
        return tuple(
            item.descriptor
            for item in self.instance_registrations
            if module_id is None or item.module_id == module_id
        )

    def resolve_instance(self, instance_id: str) -> KnowledgeModuleInstanceRegistration | None:
        if not isinstance(instance_id, str):
            raise KnowledgeModuleError("MODULE_INSTANCE_NOT_REGISTERED", "instance ID must be a string")
        return next(
            (item for item in self.instance_registrations if item.instance_id == instance_id),
            None,
        )

    def get_module_instance(self, instance_id: str) -> KnowledgeModuleInstanceDescriptor:
        registration = self.resolve_instance(instance_id)
        if registration is None:
            raise KnowledgeModuleError(
                "MODULE_INSTANCE_NOT_REGISTERED", f"module instance is not registered: {instance_id}"
            )
        return registration.descriptor

    def validate_registry(self) -> None:
        if self.authority_status != NON_AUTHORITATIVE:
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "registry cannot carry authority")
        for instance in self.instance_registrations:
            logical = self.resolve(instance.module_id)
            if logical is None:
                raise KnowledgeModuleError("MODULE_NOT_REGISTERED", "instance module is not registered")
            self._validate_instance_binding(logical, instance.descriptor)

    @staticmethod
    def _validate_instance_binding(
        logical: KnowledgeModuleRegistration,
        instance: KnowledgeModuleInstanceDescriptor,
    ) -> None:
        descriptor = logical.descriptor
        if descriptor.module_id != instance.module_id:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "module and instance IDs differ")
        if descriptor.module_version != instance.module_version:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "module and instance versions differ")
        if descriptor.descriptor_hash != instance.expected_module_descriptor_hash:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "instance descriptor pin differs")
        transport_descriptor(instance.transport_kind)

    @staticmethod
    def _require_instance_usable(
        registration: KnowledgeModuleInstanceRegistration,
    ) -> None:
        instance = registration.descriptor
        if not registration.registration_enabled or instance.availability_status == DISABLED:
            raise KnowledgeModuleError("MODULE_DISABLED", f"module instance is disabled: {instance.instance_id}")
        if instance.availability_status == UNAVAILABLE:
            raise KnowledgeModuleError("MODULE_UNAVAILABLE", f"module instance is unavailable: {instance.instance_id}")
        if instance.availability_status == VERSION_MISMATCH:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "instance version status differs")
        if instance.availability_status == SNAPSHOT_MISMATCH:
            raise KnowledgeModuleError("SNAPSHOT_MISMATCH", "instance snapshot status differs")
        if instance.availability_status == TRANSPORT_NOT_IMPLEMENTED:
            raise KnowledgeModuleError("TRANSPORT_NOT_IMPLEMENTED", "instance transport is not implemented")
        if instance.availability_status not in (AVAILABLE, DEGRADED):
            raise KnowledgeModuleError("MODULE_UNAVAILABLE", "instance availability status blocks selection")
        transport_descriptor(instance.transport_kind).require_implemented()

    def resolve_profile(self, profile: object, policy: object) -> tuple[tuple[object, ...], ...]:
        from runtime.knowledge_modules.policy import KnowledgeHubPolicy
        from runtime.knowledge_modules.profiles import KnowledgeProfile

        if not isinstance(profile, KnowledgeProfile) or not isinstance(policy, KnowledgeHubPolicy):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile or policy type differs")
        self.validate_registry()
        enabled = profile.enabled_selections
        maximum_modules = min(
            profile.global_max_modules,
            policy.default_max_selected_modules,
            policy.absolute_max_selected_modules,
        )
        if len(enabled) > maximum_modules:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "profile exceeds reviewed module maximum")
        if profile.global_max_results > policy.maximum_total_evidence_items:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "profile result budget exceeds policy")
        if profile.global_max_context_characters > policy.maximum_total_context_characters:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "profile context budget exceeds policy")
        resolved: list[tuple[object, ...]] = []
        for selection in enabled:
            logical = self.resolve(selection.module_id)
            if logical is None:
                raise KnowledgeModuleError("MODULE_NOT_REGISTERED", f"module is not registered: {selection.module_id}")
            if not logical.registration_enabled:
                raise KnowledgeModuleError("MODULE_DISABLED", f"module registration is disabled: {selection.module_id}")
            instance_registration = self.resolve_instance(selection.instance_id)
            if instance_registration is None:
                raise KnowledgeModuleError(
                    "MODULE_INSTANCE_NOT_REGISTERED", f"instance is not registered: {selection.instance_id}"
                )
            instance = instance_registration.descriptor
            if instance.module_id != selection.module_id:
                raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "selected module and instance differ")
            self._validate_instance_binding(logical, instance)
            self._require_instance_usable(instance_registration)
            if selection.per_module_max_results > policy.maximum_per_module_results:
                raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "module result budget exceeds policy")
            if selection.per_module_max_context_characters > policy.maximum_per_module_context_characters:
                raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "module context budget exceeds policy")
            resolved.append((selection, logical, instance_registration))
        return tuple(resolved)

    def verify_instance(
        self,
        instance_id: str,
        configuration: object,
    ) -> KnowledgeModuleVerificationResult:
        self.validate_registry()
        instance_registration = self.resolve_instance(instance_id)
        if instance_registration is None:
            raise KnowledgeModuleError("MODULE_INSTANCE_NOT_REGISTERED", "instance is not registered")
        self._require_instance_usable(instance_registration)
        logical = self.resolve(instance_registration.module_id)
        if logical is None:
            raise KnowledgeModuleError("MODULE_NOT_REGISTERED", "instance module is not registered")
        adapter = instance_registration.adapter_factory()
        return adapter.verify(configuration, logical.descriptor)

    def query_instance(
        self,
        instance_id: str,
        query: ModuleQueryPlan,
        configuration: object,
    ) -> KnowledgeEvidenceBundle:
        self.validate_registry()
        instance_registration = self.resolve_instance(instance_id)
        if instance_registration is None:
            raise KnowledgeModuleError("MODULE_INSTANCE_NOT_REGISTERED", "instance is not registered")
        self._require_instance_usable(instance_registration)
        logical = self.resolve(instance_registration.module_id)
        if logical is None:
            raise KnowledgeModuleError("MODULE_NOT_REGISTERED", "instance module is not registered")
        if not isinstance(query, ModuleQueryPlan):
            raise KnowledgeModuleError("PROFILE_INVALID", "instance query plan type differs")
        if query.instance_id != instance_id or query.module_id != logical.module_id:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "instance query plan binding differs")
        adapter = instance_registration.adapter_factory()
        query_plan = getattr(adapter, "query_plan", None)
        if not callable(query_plan):
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED",
                "instance adapter does not implement the generic query-plan boundary",
            )
        return query_plan(configuration, query, logical.descriptor)


__all__ = (
    "AdapterFactory",
    "KnowledgeModuleAdapter",
    "KnowledgeModuleRegistration",
    "KnowledgeModuleRegistry",
    "MODULE_REGISTRATION_SCHEMA_VERSION",
)
