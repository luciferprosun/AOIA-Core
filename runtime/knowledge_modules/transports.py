"""Schema-only transport contracts for Knowledge Module instances."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)


TRANSPORT_SCHEMA_VERSION = "knowledge-module-transport-1b"
LOCAL_READ_ONLY_PROCESS = "LOCAL_READ_ONLY_PROCESS"
REMOTE_READ_ONLY_SERVICE = "REMOTE_READ_ONLY_SERVICE"
TRANSPORT_KINDS = (LOCAL_READ_ONLY_PROCESS, REMOTE_READ_ONLY_SERVICE)


@dataclass(frozen=True, slots=True)
class KnowledgeModuleTransportDescriptor(JsonContract):
    schema_version: str
    transport_kind: str
    implemented: bool
    read_only: bool
    network_access: bool
    automatic_retry: bool
    automatic_failover: bool
    authority_status: str = NON_AUTHORITATIVE
    transport_hash: str = ""
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
        if self.schema_version != TRANSPORT_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "transport schema differs")
        if self.transport_kind not in TRANSPORT_KINDS:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "transport kind is unsupported")
        for name in (
            "implemented",
            "read_only",
            "network_access",
            "automatic_retry",
            "automatic_failover",
        ):
            if type(getattr(self, name)) is not bool:
                raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} must be boolean")
        if not self.read_only or self.automatic_retry or self.automatic_failover:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED",
                "knowledge transports must be read-only without retry or failover",
            )
        if self.transport_kind == LOCAL_READ_ONLY_PROCESS and (
            not self.implemented or self.network_access
        ):
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONTRACT", "local transport identity differs"
            )
        if self.transport_kind == REMOTE_READ_ONLY_SERVICE and (
            self.implemented or self.network_access
        ):
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONTRACT", "remote transport must remain reserved and inert"
            )
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "transport cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("transport_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "transport hash differs")
        object.__setattr__(self, "transport_hash", expected)

    def require_implemented(self) -> None:
        if not self.implemented:
            raise KnowledgeModuleError(
                "TRANSPORT_NOT_IMPLEMENTED",
                f"transport is reserved but not implemented: {self.transport_kind}",
            )


LOCAL_PROCESS_TRANSPORT = KnowledgeModuleTransportDescriptor(
    schema_version=TRANSPORT_SCHEMA_VERSION,
    transport_kind=LOCAL_READ_ONLY_PROCESS,
    implemented=True,
    read_only=True,
    network_access=False,
    automatic_retry=False,
    automatic_failover=False,
)

RESERVED_REMOTE_TRANSPORT = KnowledgeModuleTransportDescriptor(
    schema_version=TRANSPORT_SCHEMA_VERSION,
    transport_kind=REMOTE_READ_ONLY_SERVICE,
    implemented=False,
    read_only=True,
    network_access=False,
    automatic_retry=False,
    automatic_failover=False,
)


def transport_descriptor(transport_kind: str) -> KnowledgeModuleTransportDescriptor:
    if transport_kind == LOCAL_READ_ONLY_PROCESS:
        return LOCAL_PROCESS_TRANSPORT
    if transport_kind == REMOTE_READ_ONLY_SERVICE:
        return RESERVED_REMOTE_TRANSPORT
    raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "transport kind is unsupported")


__all__ = (
    "LOCAL_PROCESS_TRANSPORT",
    "LOCAL_READ_ONLY_PROCESS",
    "KnowledgeModuleTransportDescriptor",
    "REMOTE_READ_ONLY_SERVICE",
    "RESERVED_REMOTE_TRANSPORT",
    "TRANSPORT_KINDS",
    "TRANSPORT_SCHEMA_VERSION",
    "transport_descriptor",
)
