"""Deployment-instance contracts separated from logical module identity."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)
from runtime.knowledge_modules.transports import (
    LOCAL_READ_ONLY_PROCESS,
    REMOTE_READ_ONLY_SERVICE,
    transport_descriptor,
)


INSTANCE_SCHEMA_VERSION = "knowledge-module-instance-1b"
INSTANCE_REGISTRATION_SCHEMA_VERSION = "knowledge-module-instance-registration-1b"
CONTROL_RECORD_SCHEMA_VERSION = "knowledge-module-control-record-1b"

AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"
DEGRADED = "DEGRADED"
DISABLED = "DISABLED"
VERSION_MISMATCH = "VERSION_MISMATCH"
SNAPSHOT_MISMATCH = "SNAPSHOT_MISMATCH"
TRANSPORT_NOT_IMPLEMENTED = "TRANSPORT_NOT_IMPLEMENTED"
AVAILABILITY_STATUSES = (
    AVAILABLE,
    UNAVAILABLE,
    DEGRADED,
    DISABLED,
    VERSION_MISMATCH,
    SNAPSHOT_MISMATCH,
    TRANSPORT_NOT_IMPLEMENTED,
)

_IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _sorted_strings(name: str, values: Any, *, required: bool = True) -> tuple[str, ...]:
    if isinstance(values, str):
        raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} must be a sequence")
    try:
        result = tuple(values)
    except TypeError as exc:
        raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} must be a sequence") from exc
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} is invalid")
    normalized = tuple(sorted(item.strip() for item in result))
    if len(normalized) != len(set(normalized)) or (required and not normalized):
        raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} is empty or duplicated")
    return normalized


@dataclass(frozen=True, slots=True)
class KnowledgeModuleInstanceDescriptor(JsonContract):
    schema_version: str
    instance_id: str
    module_id: str
    module_version: str
    deployment_id: str
    transport_kind: str
    availability_status: str
    corpus_snapshot_ids: tuple[str, ...]
    temporal_snapshot_id: str
    instance_configuration_hash: str
    expected_module_descriptor_hash: str
    priority: int
    authority_status: str = NON_AUTHORITATIVE
    enabled_by_default: bool = False
    instance_hash: str = ""
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != INSTANCE_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "instance schema differs")
        for name in ("instance_id", "module_id", "deployment_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} is invalid")
        if not isinstance(self.module_version, str) or not self.module_version.strip():
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "module version is required")
        if self.availability_status not in AVAILABILITY_STATUSES:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "availability status is invalid")
        transport = transport_descriptor(self.transport_kind)
        if (
            self.transport_kind == REMOTE_READ_ONLY_SERVICE
            and self.availability_status != TRANSPORT_NOT_IMPLEMENTED
        ):
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONTRACT", "reserved remote instance status differs"
            )
        if (
            self.transport_kind == LOCAL_READ_ONLY_PROCESS
            and not transport.implemented
        ):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "local transport is unavailable")
        object.__setattr__(
            self,
            "corpus_snapshot_ids",
            _sorted_strings("corpus_snapshot_ids", self.corpus_snapshot_ids),
        )
        if not isinstance(self.temporal_snapshot_id, str) or not self.temporal_snapshot_id.strip():
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "temporal snapshot is required")
        for name in ("instance_configuration_hash", "expected_module_descriptor_hash"):
            if not isinstance(getattr(self, name), str) or not _SHA256.fullmatch(getattr(self, name)):
                raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} must be SHA-256")
        if type(self.priority) is not int or not 0 <= self.priority <= 10_000:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "instance priority is invalid")
        if type(self.enabled_by_default) is not bool or self.enabled_by_default:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "instance cannot be enabled by default"
            )
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "instance cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("instance_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "instance hash differs")
        object.__setattr__(self, "instance_hash", expected)


InstanceAdapterFactory = Callable[[], Any]


@dataclass(frozen=True, slots=True)
class KnowledgeModuleInstanceRegistration(JsonContract):
    descriptor: KnowledgeModuleInstanceDescriptor
    adapter_factory: InstanceAdapterFactory = field(repr=False, compare=False)
    registration_enabled: bool = True
    schema_version: str = INSTANCE_REGISTRATION_SCHEMA_VERSION
    authority_status: str = NON_AUTHORITATIVE

    def __post_init__(self) -> None:
        if self.schema_version != INSTANCE_REGISTRATION_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "instance registration schema differs")
        if not callable(self.adapter_factory):
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "instance adapter is invalid")
        if type(self.registration_enabled) is not bool:
            raise KnowledgeModuleError("INVALID_MODULE_REGISTRATION", "registration flag is invalid")
        if self.authority_status != NON_AUTHORITATIVE:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "instance registration cannot carry authority"
            )

    @property
    def instance_id(self) -> str:
        return self.descriptor.instance_id

    @property
    def module_id(self) -> str:
        return self.descriptor.module_id

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_status": NON_AUTHORITATIVE,
            "instance_hash": self.descriptor.instance_hash,
            "instance_id": self.instance_id,
            "module_id": self.module_id,
            "module_version": self.descriptor.module_version,
            "registration_enabled": self.registration_enabled,
            "transport_kind": self.descriptor.transport_kind,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeModuleControlRecord(JsonContract):
    schema_version: str
    module_id: str
    display_name: str
    description: str
    domain: str
    module_version: str
    available_instances: tuple[str, ...]
    availability_status: str
    enabled_by_default: bool
    currently_selected: bool
    supported_retrieval_modes: tuple[str, ...]
    known_limitations: tuple[str, ...]
    authority_status: str = NON_AUTHORITATIVE
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != CONTROL_RECORD_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "control record schema differs")
        if self.availability_status not in AVAILABILITY_STATUSES:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "control availability differs")
        object.__setattr__(
            self,
            "available_instances",
            _sorted_strings("available_instances", self.available_instances, required=False),
        )
        object.__setattr__(
            self,
            "supported_retrieval_modes",
            _sorted_strings("supported_retrieval_modes", self.supported_retrieval_modes),
        )
        object.__setattr__(
            self,
            "known_limitations",
            _sorted_strings("known_limitations", self.known_limitations, required=False),
        )
        if self.enabled_by_default or type(self.currently_selected) is not bool:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "control state cannot activate a module"
            )
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "control record cannot carry authority"
            )


__all__ = (
    "AVAILABLE",
    "AVAILABILITY_STATUSES",
    "CONTROL_RECORD_SCHEMA_VERSION",
    "DEGRADED",
    "DISABLED",
    "INSTANCE_REGISTRATION_SCHEMA_VERSION",
    "INSTANCE_SCHEMA_VERSION",
    "InstanceAdapterFactory",
    "KnowledgeModuleControlRecord",
    "KnowledgeModuleInstanceDescriptor",
    "KnowledgeModuleInstanceRegistration",
    "SNAPSHOT_MISMATCH",
    "TRANSPORT_NOT_IMPLEMENTED",
    "UNAVAILABLE",
    "VERSION_MISMATCH",
)
