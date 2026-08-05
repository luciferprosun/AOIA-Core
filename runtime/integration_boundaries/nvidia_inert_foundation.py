"""Disabled-by-default, non-authoritative NVIDIA integration contracts.

This module is a structural boundary only.  It deliberately has no provider,
network, process, filesystem, environment, GPU, tool, approval, or ledger
integration.  A future adapter requires a separate implementation and review.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


NVIDIA_CONFIG_SCHEMA_VERSION = "AOIA_NVIDIA_INTEGRATION_CONFIG_1A"
NVIDIA_CAPABILITY_SCHEMA_VERSION = "AOIA_NVIDIA_CAPABILITY_DECLARATION_1A"
NVIDIA_AVAILABILITY_SCHEMA_VERSION = "AOIA_NVIDIA_AVAILABILITY_1A"
NVIDIA_ADVISORY_REQUEST_SCHEMA_VERSION = "AOIA_NVIDIA_ADVISORY_REQUEST_1A"
NVIDIA_PROVENANCE_SCHEMA_VERSION = "AOIA_NVIDIA_ADVISORY_PROVENANCE_1A"
NVIDIA_FAILURE_SCHEMA_VERSION = "AOIA_NVIDIA_FAILURE_RESULT_1A"
NVIDIA_ADVISORY_RESPONSE_SCHEMA_VERSION = "AOIA_NVIDIA_ADVISORY_RESPONSE_1A"

NVIDIA_PROVIDER_IDENTITY = "nvidia"
NVIDIA_DISABLED_ADAPTER_IDENTITY = "nvidia-disabled-adapter-1a"
EXTERNAL_ADVISORY_NON_AUTHORITY = "EXTERNAL ADVISORY - NON-AUTHORITY"
NON_AUTHORITY = "NON_AUTHORITY"
STRUCTURAL_CONTRACT_ONLY = "STRUCTURAL_CONTRACT_ONLY"

NVIDIA_REASON_DISABLED_BY_DEFAULT = "NVIDIA_FOUNDATION_DISABLED_BY_DEFAULT"
NVIDIA_REASON_INVALID_CONFIGURATION = "NVIDIA_FOUNDATION_BLOCKED_INVALID_CONFIGURATION"

DEFERRED_NVIDIA_CAPABILITY_IDS = (
    "nvidia.advisory.analysis",
    "nvidia.advisory.guardrail",
    "nvidia.advisory.policy_signal",
    "nvidia.evidence.source",
    "nvidia.runtime.optional",
)

_ALLOWED_CONFIG_FIELDS = frozenset(
    {
        "schema_version",
        "enabled",
        "adapter_identity",
        "requested_capability_ids",
    }
)
_IDENTIFIER_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789-._:"
)
_EFFECT_AND_AUTHORITY_FIELDS = (
    "network_called",
    "gpu_used",
    "process_started",
    "filesystem_written",
    "tool_called",
    "provider_selected",
    "ledger_mutated",
    "memory_patch_created",
    "action_proposal_created",
    "approval_created",
    "can_approve",
    "can_execute",
    "can_write",
    "can_mutate_ledger",
    "can_change_gate",
    "can_bypass_kill_switch",
    "can_bypass_workspace_guard",
)
_FAILURE_MESSAGES = {
    NVIDIA_REASON_DISABLED_BY_DEFAULT: (
        "NVIDIA integration is disabled by default; no advisory was produced."
    ),
    NVIDIA_REASON_INVALID_CONFIGURATION: (
        "NVIDIA foundation configuration is invalid; integration remains disabled."
    ),
}


class NvidiaFoundationStatus(str, Enum):
    DISABLED = "DISABLED"
    BLOCKED_INVALID_CONFIGURATION = "BLOCKED_INVALID_CONFIGURATION"


@dataclass(frozen=True, slots=True)
class NvidiaIntegrationConfig:
    schema_version: str = NVIDIA_CONFIG_SCHEMA_VERSION
    enabled: bool = False
    adapter_identity: str = NVIDIA_DISABLED_ADAPTER_IDENTITY
    requested_capability_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_CONFIG_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA foundation configuration schema")
        if type(self.enabled) is not bool or self.enabled:
            raise ValueError("NVIDIA foundation configuration must remain disabled")
        if self.adapter_identity != NVIDIA_DISABLED_ADAPTER_IDENTITY:
            raise ValueError("unsupported NVIDIA foundation adapter identity")
        if not isinstance(self.requested_capability_ids, tuple):
            raise ValueError("requested NVIDIA capabilities must be an immutable tuple")
        if self.requested_capability_ids:
            raise ValueError("NVIDIA foundation cannot activate capabilities")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NVIDIA_CONFIG_SCHEMA_VERSION,
            "enabled": False,
            "adapter_identity": NVIDIA_DISABLED_ADAPTER_IDENTITY,
            "requested_capability_ids": (),
        }


@dataclass(frozen=True, slots=True)
class NvidiaFailureResult:
    reason_code: str
    schema_version: str = NVIDIA_FAILURE_SCHEMA_VERSION
    status: str = NvidiaFoundationStatus.DISABLED.value
    message: str = ""
    retryable: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_FAILURE_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA foundation failure schema")
        if self.reason_code not in _FAILURE_MESSAGES:
            raise ValueError("unsupported NVIDIA foundation failure reason")
        status = (
            NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value
            if self.reason_code == NVIDIA_REASON_INVALID_CONFIGURATION
            else NvidiaFoundationStatus.DISABLED.value
        )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "message", _FAILURE_MESSAGES[self.reason_code])
        object.__setattr__(self, "retryable", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NVIDIA_FAILURE_SCHEMA_VERSION,
            "status": self.status,
            "reason_code": self.reason_code,
            "message": self.message,
            "retryable": False,
        }


@dataclass(frozen=True, slots=True)
class NvidiaCapabilityDeclaration:
    schema_version: str = NVIDIA_CAPABILITY_SCHEMA_VERSION
    provider_identity: str = NVIDIA_PROVIDER_IDENTITY
    adapter_identity: str = NVIDIA_DISABLED_ADAPTER_IDENTITY
    active_capability_ids: tuple[str, ...] = ()
    deferred_capability_ids: tuple[str, ...] = DEFERRED_NVIDIA_CAPABILITY_IDS
    network_access: bool = False
    gpu_access: bool = False
    process_access: bool = False
    filesystem_write_access: bool = False
    tool_access: bool = False
    approval_authority: bool = False
    ledger_mutation_access: bool = False
    memory_patch_access: bool = False
    automatic_selection: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_CAPABILITY_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA capability declaration schema")
        if self.provider_identity != NVIDIA_PROVIDER_IDENTITY:
            raise ValueError("unsupported NVIDIA provider identity")
        if self.adapter_identity != NVIDIA_DISABLED_ADAPTER_IDENTITY:
            raise ValueError("unsupported NVIDIA adapter identity")
        object.__setattr__(self, "active_capability_ids", ())
        object.__setattr__(
            self, "deferred_capability_ids", DEFERRED_NVIDIA_CAPABILITY_IDS
        )
        for field_name in (
            "network_access",
            "gpu_access",
            "process_access",
            "filesystem_write_access",
            "tool_access",
            "approval_authority",
            "ledger_mutation_access",
            "memory_patch_access",
            "automatic_selection",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NVIDIA_CAPABILITY_SCHEMA_VERSION,
            "provider_identity": NVIDIA_PROVIDER_IDENTITY,
            "adapter_identity": NVIDIA_DISABLED_ADAPTER_IDENTITY,
            "active_capability_ids": (),
            "deferred_capability_ids": DEFERRED_NVIDIA_CAPABILITY_IDS,
            "network_access": False,
            "gpu_access": False,
            "process_access": False,
            "filesystem_write_access": False,
            "tool_access": False,
            "approval_authority": False,
            "ledger_mutation_access": False,
            "memory_patch_access": False,
            "automatic_selection": False,
        }


@dataclass(frozen=True, slots=True)
class NvidiaAvailability:
    status: str
    reason_code: str
    config_present: bool
    schema_version: str = NVIDIA_AVAILABILITY_SCHEMA_VERSION
    provider_identity: str = NVIDIA_PROVIDER_IDENTITY
    adapter_identity: str = NVIDIA_DISABLED_ADAPTER_IDENTITY
    active_capability_ids: tuple[str, ...] = ()
    network_available: bool = False
    gpu_available: bool = False
    runtime_available: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_AVAILABILITY_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA availability schema")
        expected = {
            NVIDIA_REASON_DISABLED_BY_DEFAULT: NvidiaFoundationStatus.DISABLED.value,
            NVIDIA_REASON_INVALID_CONFIGURATION: (
                NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value
            ),
        }
        if expected.get(self.reason_code) != self.status:
            raise ValueError("NVIDIA availability status and reason differ")
        if type(self.config_present) is not bool:
            raise ValueError("NVIDIA config_present must be boolean")
        object.__setattr__(self, "provider_identity", NVIDIA_PROVIDER_IDENTITY)
        object.__setattr__(self, "adapter_identity", NVIDIA_DISABLED_ADAPTER_IDENTITY)
        object.__setattr__(self, "active_capability_ids", ())
        object.__setattr__(self, "network_available", False)
        object.__setattr__(self, "gpu_available", False)
        object.__setattr__(self, "runtime_available", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NVIDIA_AVAILABILITY_SCHEMA_VERSION,
            "status": self.status,
            "reason_code": self.reason_code,
            "config_present": self.config_present,
            "provider_identity": NVIDIA_PROVIDER_IDENTITY,
            "adapter_identity": NVIDIA_DISABLED_ADAPTER_IDENTITY,
            "active_capability_ids": (),
            "network_available": False,
            "gpu_available": False,
            "runtime_available": False,
        }


@dataclass(frozen=True, slots=True)
class NvidiaConfigResolution:
    config: NvidiaIntegrationConfig
    availability: NvidiaAvailability
    failure: NvidiaFailureResult | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "availability": self.availability.to_dict(),
            "failure": None if self.failure is None else self.failure.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class NvidiaAdvisoryRequest:
    correlation_id: str
    capability_identity: str
    evidence_hashes: tuple[str, ...]
    created_at_tick: int
    schema_version: str = NVIDIA_ADVISORY_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_ADVISORY_REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA advisory request schema")
        object.__setattr__(
            self, "correlation_id", _required_identifier(self.correlation_id)
        )
        if self.capability_identity not in DEFERRED_NVIDIA_CAPABILITY_IDS:
            raise ValueError("unsupported deferred NVIDIA capability identity")
        object.__setattr__(
            self, "evidence_hashes", _validated_hash_tuple(self.evidence_hashes)
        )
        object.__setattr__(
            self, "created_at_tick", _nonnegative_integer(self.created_at_tick)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NVIDIA_ADVISORY_REQUEST_SCHEMA_VERSION,
            "correlation_id": self.correlation_id,
            "capability_identity": self.capability_identity,
            "evidence_hashes": self.evidence_hashes,
            "created_at_tick": self.created_at_tick,
        }


@dataclass(frozen=True, slots=True)
class NvidiaAdvisoryProvenance:
    capability_identity: str
    request_correlation_id: str
    evidence_hashes: tuple[str, ...]
    generated_at_tick: int
    schema_version: str = NVIDIA_PROVENANCE_SCHEMA_VERSION
    provider_identity: str = NVIDIA_PROVIDER_IDENTITY
    adapter_identity: str = NVIDIA_DISABLED_ADAPTER_IDENTITY
    source_kind: str = STRUCTURAL_CONTRACT_ONLY
    advisory_label: str = EXTERNAL_ADVISORY_NON_AUTHORITY
    authority_status: str = NON_AUTHORITY

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_PROVENANCE_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA advisory provenance schema")
        if self.capability_identity not in DEFERRED_NVIDIA_CAPABILITY_IDS:
            raise ValueError("unsupported NVIDIA provenance capability identity")
        object.__setattr__(
            self,
            "request_correlation_id",
            _required_identifier(self.request_correlation_id),
        )
        object.__setattr__(
            self, "evidence_hashes", _validated_hash_tuple(self.evidence_hashes)
        )
        object.__setattr__(
            self, "generated_at_tick", _nonnegative_integer(self.generated_at_tick)
        )
        object.__setattr__(self, "provider_identity", NVIDIA_PROVIDER_IDENTITY)
        object.__setattr__(self, "adapter_identity", NVIDIA_DISABLED_ADAPTER_IDENTITY)
        object.__setattr__(self, "source_kind", STRUCTURAL_CONTRACT_ONLY)
        object.__setattr__(self, "advisory_label", EXTERNAL_ADVISORY_NON_AUTHORITY)
        object.__setattr__(self, "authority_status", NON_AUTHORITY)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NVIDIA_PROVENANCE_SCHEMA_VERSION,
            "provider_identity": NVIDIA_PROVIDER_IDENTITY,
            "adapter_identity": NVIDIA_DISABLED_ADAPTER_IDENTITY,
            "capability_identity": self.capability_identity,
            "request_correlation_id": self.request_correlation_id,
            "evidence_hashes": self.evidence_hashes,
            "generated_at_tick": self.generated_at_tick,
            "source_kind": STRUCTURAL_CONTRACT_ONLY,
            "advisory_label": EXTERNAL_ADVISORY_NON_AUTHORITY,
            "authority_status": NON_AUTHORITY,
        }


@dataclass(frozen=True, slots=True)
class NvidiaAdvisoryResponse:
    status: str
    correlation_id: str
    capability_identity: str
    availability: NvidiaAvailability
    provenance: NvidiaAdvisoryProvenance
    failure: NvidiaFailureResult
    schema_version: str = NVIDIA_ADVISORY_RESPONSE_SCHEMA_VERSION
    advisory_label: str = EXTERNAL_ADVISORY_NON_AUTHORITY
    authority_status: str = NON_AUTHORITY
    advisory_payload: None = None
    human_review_required: bool = True
    network_called: bool = False
    gpu_used: bool = False
    process_started: bool = False
    filesystem_written: bool = False
    tool_called: bool = False
    provider_selected: bool = False
    ledger_mutated: bool = False
    memory_patch_created: bool = False
    action_proposal_created: bool = False
    approval_created: bool = False
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_mutate_ledger: bool = False
    can_change_gate: bool = False
    can_bypass_kill_switch: bool = False
    can_bypass_workspace_guard: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != NVIDIA_ADVISORY_RESPONSE_SCHEMA_VERSION:
            raise ValueError("unsupported NVIDIA advisory response schema")
        if self.status not in {
            NvidiaFoundationStatus.DISABLED.value,
            NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value,
        }:
            raise ValueError("unsupported NVIDIA advisory response status")
        correlation_id = _required_identifier(self.correlation_id)
        if self.capability_identity not in DEFERRED_NVIDIA_CAPABILITY_IDS:
            raise ValueError("unsupported NVIDIA response capability identity")
        if self.availability.status != self.status or self.failure.status != self.status:
            raise ValueError("NVIDIA response status differs from fail-closed evidence")
        if self.provenance.request_correlation_id != correlation_id:
            raise ValueError("NVIDIA response provenance correlation differs")
        if self.provenance.capability_identity != self.capability_identity:
            raise ValueError("NVIDIA response provenance capability differs")
        object.__setattr__(self, "correlation_id", correlation_id)
        object.__setattr__(self, "advisory_label", EXTERNAL_ADVISORY_NON_AUTHORITY)
        object.__setattr__(self, "authority_status", NON_AUTHORITY)
        object.__setattr__(self, "advisory_payload", None)
        object.__setattr__(self, "human_review_required", True)
        for field_name in _EFFECT_AND_AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": NVIDIA_ADVISORY_RESPONSE_SCHEMA_VERSION,
            "status": self.status,
            "correlation_id": self.correlation_id,
            "capability_identity": self.capability_identity,
            "availability": self.availability.to_dict(),
            "provenance": self.provenance.to_dict(),
            "failure": self.failure.to_dict(),
            "advisory_label": EXTERNAL_ADVISORY_NON_AUTHORITY,
            "authority_status": NON_AUTHORITY,
            "advisory_payload": None,
            "human_review_required": True,
        }
        for field_name in _EFFECT_AND_AUTHORITY_FIELDS:
            data[field_name] = False
        return data


def resolve_nvidia_integration_config(
    raw_config: object | None = None,
) -> NvidiaConfigResolution:
    if raw_config is None:
        return _disabled_resolution(config_present=False)
    if isinstance(raw_config, NvidiaIntegrationConfig):
        return _disabled_resolution(config_present=True, config=raw_config)
    if not isinstance(raw_config, Mapping):
        return _invalid_resolution(config_present=True)
    try:
        if not set(raw_config).issubset(_ALLOWED_CONFIG_FIELDS):
            return _invalid_resolution(config_present=True)
        requested = raw_config.get("requested_capability_ids", ())
        if isinstance(requested, list):
            requested = tuple(requested)
        config = NvidiaIntegrationConfig(
            schema_version=raw_config.get(
                "schema_version", NVIDIA_CONFIG_SCHEMA_VERSION
            ),
            enabled=raw_config.get("enabled", False),
            adapter_identity=raw_config.get(
                "adapter_identity", NVIDIA_DISABLED_ADAPTER_IDENTITY
            ),
            requested_capability_ids=requested,
        )
    except Exception:
        return _invalid_resolution(config_present=True)
    return _disabled_resolution(config_present=True, config=config)


def create_nvidia_advisory_request(
    *,
    correlation_id: str,
    capability_identity: str,
    evidence_hashes: tuple[str, ...] = (),
    created_at_tick: int,
) -> NvidiaAdvisoryRequest:
    return NvidiaAdvisoryRequest(
        correlation_id=correlation_id,
        capability_identity=capability_identity,
        evidence_hashes=evidence_hashes,
        created_at_tick=created_at_tick,
    )


def get_nvidia_capability_declaration() -> NvidiaCapabilityDeclaration:
    return _NVIDIA_CAPABILITY_DECLARATION


def list_active_nvidia_capabilities() -> tuple[str, ...]:
    return ()


def list_deferred_nvidia_capabilities() -> tuple[str, ...]:
    return DEFERRED_NVIDIA_CAPABILITY_IDS


class InertNvidiaAdapter:
    """Null adapter that can only return fail-closed structural evidence."""

    __slots__ = ("_resolution",)

    def __init__(self, raw_config: object | None = None) -> None:
        self._resolution = resolve_nvidia_integration_config(raw_config)

    @property
    def configuration(self) -> NvidiaIntegrationConfig:
        return self._resolution.config

    @property
    def availability(self) -> NvidiaAvailability:
        return self._resolution.availability

    @property
    def capability_declaration(self) -> NvidiaCapabilityDeclaration:
        return _NVIDIA_CAPABILITY_DECLARATION

    def request_advisory(
        self, request: NvidiaAdvisoryRequest
    ) -> NvidiaAdvisoryResponse:
        if not isinstance(request, NvidiaAdvisoryRequest):
            raise ValueError("NVIDIA advisory request contract is required")
        failure = self._resolution.failure or NvidiaFailureResult(
            NVIDIA_REASON_DISABLED_BY_DEFAULT
        )
        provenance = NvidiaAdvisoryProvenance(
            capability_identity=request.capability_identity,
            request_correlation_id=request.correlation_id,
            evidence_hashes=request.evidence_hashes,
            generated_at_tick=request.created_at_tick,
        )
        return NvidiaAdvisoryResponse(
            status=self._resolution.availability.status,
            correlation_id=request.correlation_id,
            capability_identity=request.capability_identity,
            availability=self._resolution.availability,
            provenance=provenance,
            failure=failure,
        )


def _disabled_resolution(
    *,
    config_present: bool,
    config: NvidiaIntegrationConfig | None = None,
) -> NvidiaConfigResolution:
    return NvidiaConfigResolution(
        config=config or NvidiaIntegrationConfig(),
        availability=NvidiaAvailability(
            status=NvidiaFoundationStatus.DISABLED.value,
            reason_code=NVIDIA_REASON_DISABLED_BY_DEFAULT,
            config_present=config_present,
        ),
        failure=None,
    )


def _invalid_resolution(*, config_present: bool) -> NvidiaConfigResolution:
    failure = NvidiaFailureResult(NVIDIA_REASON_INVALID_CONFIGURATION)
    return NvidiaConfigResolution(
        config=NvidiaIntegrationConfig(),
        availability=NvidiaAvailability(
            status=NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value,
            reason_code=NVIDIA_REASON_INVALID_CONFIGURATION,
            config_present=config_present,
        ),
        failure=failure,
    )


def _required_identifier(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("identifier must be text")
    normalized = value.strip().casefold()
    if (
        not normalized
        or len(normalized) > 128
        or normalized[0] not in frozenset("abcdefghijklmnopqrstuvwxyz0123456789")
        or any(character not in _IDENTIFIER_CHARACTERS for character in normalized)
    ):
        raise ValueError("identifier has an unsupported format")
    return normalized


def _validated_hash_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError("evidence hashes must be an immutable tuple")
    normalized: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
        ):
            raise ValueError("evidence hash must be lowercase SHA-256 text")
        normalized.append(item)
    if len(normalized) > 64:
        raise ValueError("too many NVIDIA evidence hashes")
    return tuple(sorted(set(normalized)))


def _nonnegative_integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("tick must be a non-negative integer")
    return value


_NVIDIA_CAPABILITY_DECLARATION = NvidiaCapabilityDeclaration()
