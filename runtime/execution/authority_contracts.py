"""Immutable, hash-bound vocabulary for future authorized execution.

R3.1 contracts are data only.  They do not approve, dispatch, reserve,
resolve, write, call a provider, or execute anything.
"""

from __future__ import annotations

if __name__ != "runtime.execution.authority_contracts":
    raise ImportError(
        "authority contracts must be imported as runtime.execution.authority_contracts"
    )

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from .canonical_serialization import (
    CanonicalSerializationError,
    FrozenDict,
    domain_separated_sha256,
    freeze_json,
    hashes_equal,
    require_sha256,
    thaw_json,
)


AOIA_CASE_V1 = "AOIA_CASE_V1"
AOIA_EXACT_SCOPE_V1 = "AOIA_EXACT_SCOPE_V1"
AOIA_PLAN_STEP_V1 = "AOIA_PLAN_STEP_V1"
AOIA_VISIBLE_PLAN_V1 = "AOIA_VISIBLE_PLAN_V1"
AOIA_HUMAN_EXECUTION_APPROVAL_V1 = "AOIA_HUMAN_EXECUTION_APPROVAL_V1"
AOIA_APPROVED_EXECUTION_REQUEST_V1 = "AOIA_APPROVED_EXECUTION_REQUEST_V1"
AOIA_NORMALIZED_ARGUMENTS_V1 = "AOIA_NORMALIZED_ARGUMENTS_V1"
AOIA_RESOURCE_IDENTITY_V1 = "AOIA_RESOURCE_IDENTITY_V1"

_RFC3339_UTC = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)


class AuthorityContractError(ValueError):
    """Raised when authority contract data is structurally invalid."""


class AuthorityHashMismatch(AuthorityContractError):
    """Raised when an externally supplied hash does not match its material."""


class AuthorityBindingMismatch(AuthorityContractError):
    """Raised when separately valid contracts do not describe one exact action."""


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWABLE = "REVIEWABLE"
    APPROVED = "APPROVED"
    INVALIDATED = "INVALIDATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ApprovalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class _HashBoundContract:
    _HASH_DOMAIN: ClassVar[str]
    _HASH_FIELD: ClassVar[str]

    def _hash_material(self) -> dict[str, Any]:
        raise NotImplementedError

    def compute_hash(self) -> str:
        return domain_separated_sha256(self._HASH_DOMAIN, self._hash_material())

    def verify_hash(self) -> bool:
        return hashes_equal(getattr(self, self._HASH_FIELD), self.compute_hash())


def _required_text(name: str, value: object) -> str:
    if type(value) is not str or not value:
        raise AuthorityContractError(f"{name} is required")
    if value != value.strip():
        raise AuthorityContractError(f"{name} must not contain surrounding whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise AuthorityContractError(f"{name} contains a control character")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise AuthorityContractError(f"{name} must be valid UTF-8") from exc
    return value


def _optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(name, value)


def _version(name: str, value: object) -> int:
    if type(value) is not int or value < 1:
        raise AuthorityContractError(f"{name} must be an integer greater than or equal to one")
    return value


def _nonnegative(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise AuthorityContractError(f"{name} must be a nonnegative integer")
    return value


def _timestamp(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _RFC3339_UTC.fullmatch(text):
        raise AuthorityContractError(f"{name} must be canonical RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise AuthorityContractError(f"{name} must be a valid UTC timestamp") from exc
    base = parsed.strftime("%Y-%m-%dT%H:%M:%S")
    if parsed.microsecond:
        canonical = f"{base}.{parsed.microsecond:06d}".rstrip("0") + "Z"
    else:
        canonical = base + "Z"
    if text != canonical:
        raise AuthorityContractError(f"{name} is not canonically represented")
    return text


def _require_later(*, earlier_name: str, earlier: str, later_name: str, later: str) -> None:
    before = datetime.fromisoformat(earlier[:-1] + "+00:00")
    after = datetime.fromisoformat(later[:-1] + "+00:00")
    if after <= before:
        raise AuthorityContractError(f"{later_name} must be later than {earlier_name}")


def _set_like_strings(
    name: str,
    values: object,
    *,
    forbid_wildcards: bool = False,
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise AuthorityContractError(f"{name} must be an immutable tuple")
    normalized = tuple(_required_text(name, value) for value in values)
    if len(set(normalized)) != len(normalized):
        raise AuthorityContractError(f"{name} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise AuthorityContractError(f"{name} must use canonical sorted order")
    if forbid_wildcards and any("*" in value for value in normalized):
        raise AuthorityContractError(f"{name} must not contain wildcard allows")
    return normalized


def _ordered_unique_strings(name: str, values: object, *, nonempty: bool) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise AuthorityContractError(f"{name} must be an immutable tuple")
    normalized = tuple(_required_text(name, value) for value in values)
    if nonempty and not normalized:
        raise AuthorityContractError(f"{name} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise AuthorityContractError(f"{name} must not contain duplicates")
    return normalized


def _json_mapping(name: str, value: object, *, nonempty: bool = False) -> FrozenDict:
    if type(value) not in (dict, FrozenDict):
        raise AuthorityContractError(f"{name} must be a canonical JSON object")
    try:
        frozen = freeze_json(value)
    except CanonicalSerializationError as exc:
        raise AuthorityContractError(f"{name} is not canonical JSON") from exc
    if type(frozen) is not FrozenDict:
        raise AuthorityContractError(f"{name} must be a canonical JSON object")
    if nonempty and not frozen:
        raise AuthorityContractError(f"{name} must not be empty")
    return frozen


def _limits_mapping(name: str, value: object) -> FrozenDict:
    frozen = _json_mapping(name, value, nonempty=True)
    for limit_name, limit_value in frozen.items():
        _nonnegative(f"{name}.{limit_name}", limit_value)
    return frozen


def _resource_identity(name: str, value: object) -> FrozenDict:
    frozen = _json_mapping(name, value, nonempty=True)
    for field_name in ("resource_id", "resource_type"):
        try:
            field_value = frozen[field_name]
        except KeyError as exc:
            raise AuthorityContractError(f"{name}.{field_name} is required") from exc
        _required_text(f"{name}.{field_name}", field_value)
    return frozen


def _json_value(name: str, value: object) -> Any:
    try:
        return freeze_json(value)
    except CanonicalSerializationError as exc:
        raise AuthorityContractError(f"{name} is not canonical JSON") from exc


def _previous_hash(name: str, value: object, *, version: int) -> str | None:
    if version == 1:
        if value is not None:
            raise AuthorityContractError(f"{name} must be absent for version one")
        return None
    if value is None:
        raise AuthorityContractError(f"{name} is required after version one")
    try:
        return require_sha256(value, field_name=name)
    except CanonicalSerializationError as exc:
        raise AuthorityContractError(str(exc)) from exc


def _hash(name: str, value: object) -> str:
    try:
        return require_sha256(value, field_name=name)
    except CanonicalSerializationError as exc:
        raise AuthorityContractError(str(exc)) from exc


def _strict_payload(name: str, value: object, expected: set[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise AuthorityContractError(f"{name} must be a plain dictionary")
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unknown = sorted(set(value) - expected)
        raise AuthorityContractError(
            f"{name} fields differ; missing={missing!r}; unknown={unknown!r}"
        )
    return dict(value)


def _external_tuple(name: str, value: object) -> tuple[Any, ...]:
    if type(value) is not list:
        raise AuthorityContractError(f"{name} must be a JSON array")
    return tuple(value)


def hash_normalized_arguments(value: object) -> str:
    frozen = _json_mapping("normalized_arguments", value)
    return domain_separated_sha256(AOIA_NORMALIZED_ARGUMENTS_V1, thaw_json(frozen))


def hash_resource_identity(value: object) -> str:
    frozen = _json_mapping("resource_identity", value)
    return domain_separated_sha256(AOIA_RESOURCE_IDENTITY_V1, thaw_json(frozen))


@dataclass(frozen=True, slots=True)
class Case(_HashBoundContract):
    case_id: str
    case_version: int
    created_at: str
    created_by: str
    purpose: str
    authorization_type: str
    authorization_reference: str
    authorization_subject: str
    authorization_valid_from: str
    authorization_valid_until: str
    jurisdiction: str
    data_classification: str
    scope_id: str
    policy_version: str
    status: CaseStatus
    closure_reason: str | None
    previous_case_hash: str | None
    case_hash: str = field(init=False)

    _HASH_DOMAIN: ClassVar[str] = AOIA_CASE_V1
    _HASH_FIELD: ClassVar[str] = "case_hash"

    def __post_init__(self) -> None:
        for name in (
            "case_id", "created_by", "purpose", "authorization_type",
            "authorization_reference", "authorization_subject", "jurisdiction",
            "data_classification", "scope_id", "policy_version",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "case_version", _version("case_version", self.case_version))
        object.__setattr__(self, "created_at", _timestamp("created_at", self.created_at))
        object.__setattr__(
            self,
            "authorization_valid_from",
            _timestamp("authorization_valid_from", self.authorization_valid_from),
        )
        object.__setattr__(
            self,
            "authorization_valid_until",
            _timestamp("authorization_valid_until", self.authorization_valid_until),
        )
        _require_later(
            earlier_name="authorization_valid_from",
            earlier=self.authorization_valid_from,
            later_name="authorization_valid_until",
            later=self.authorization_valid_until,
        )
        try:
            status = CaseStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise AuthorityContractError("status is invalid") from exc
        object.__setattr__(self, "status", status)
        reason = _optional_text("closure_reason", self.closure_reason)
        terminal = {CaseStatus.CLOSED, CaseStatus.EXPIRED, CaseStatus.REVOKED}
        if status is CaseStatus.OPEN and reason is not None:
            raise AuthorityContractError("OPEN case must not have a closure reason")
        if status in terminal and reason is None:
            raise AuthorityContractError("terminal case requires a closure reason")
        object.__setattr__(self, "closure_reason", reason)
        object.__setattr__(
            self,
            "previous_case_hash",
            _previous_hash("previous_case_hash", self.previous_case_hash, version=self.case_version),
        )
        object.__setattr__(self, "case_hash", self.compute_hash())

    def _hash_material(self) -> dict[str, Any]:
        return {
            "authorization_reference": self.authorization_reference,
            "authorization_subject": self.authorization_subject,
            "authorization_type": self.authorization_type,
            "authorization_valid_from": self.authorization_valid_from,
            "authorization_valid_until": self.authorization_valid_until,
            "case_id": self.case_id,
            "case_version": self.case_version,
            "closure_reason": self.closure_reason,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "data_classification": self.data_classification,
            "jurisdiction": self.jurisdiction,
            "policy_version": self.policy_version,
            "previous_case_hash": self.previous_case_hash,
            "purpose": self.purpose,
            "scope_id": self.scope_id,
            "status": self.status.value,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._hash_material(), "case_hash": self.case_hash}

    @classmethod
    def from_dict(cls, value: object) -> Case:
        expected = {
            "case_id", "case_version", "created_at", "created_by", "purpose",
            "authorization_type", "authorization_reference", "authorization_subject",
            "authorization_valid_from", "authorization_valid_until", "jurisdiction",
            "data_classification", "scope_id", "policy_version", "status",
            "closure_reason", "previous_case_hash", "case_hash",
        }
        payload = _strict_payload("Case", value, expected)
        claimed = _hash("case_hash", payload.pop("case_hash"))
        instance = cls(**payload)
        if not hashes_equal(claimed, instance.case_hash):
            raise AuthorityHashMismatch("case_hash does not match Case material")
        return instance


@dataclass(frozen=True, slots=True)
class ExactScope(_HashBoundContract):
    scope_id: str
    scope_version: int
    case_id: str
    allowed_subjects: tuple[str, ...]
    allowed_resources: tuple[str, ...]
    allowed_resource_types: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    allowed_adapters: tuple[str, ...]
    allowed_destinations: tuple[str, ...]
    allowed_protocols: tuple[str, ...]
    allowed_time_window: tuple[str, str]
    maximum_requests: int
    maximum_results: int
    maximum_payload_bytes: int
    maximum_runtime_seconds: int
    maximum_subprocesses: int
    maximum_storage_bytes: int
    maximum_retries: int
    maximum_cpu: int
    maximum_memory_bytes: int
    maximum_concurrency: int
    maximum_cost: int
    write_permissions: tuple[str, ...]
    network_permissions: tuple[str, ...]
    retention_policy: str
    explicit_denials: tuple[str, ...]
    previous_scope_hash: str | None
    scope_hash: str = field(init=False)

    _HASH_DOMAIN: ClassVar[str] = AOIA_EXACT_SCOPE_V1
    _HASH_FIELD: ClassVar[str] = "scope_hash"

    def __post_init__(self) -> None:
        for name in ("scope_id", "case_id", "retention_policy"):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "scope_version", _version("scope_version", self.scope_version))
        for name in (
            "allowed_subjects", "allowed_resources", "allowed_resource_types",
            "allowed_operations", "allowed_adapters", "allowed_destinations",
            "allowed_protocols", "write_permissions", "network_permissions",
        ):
            object.__setattr__(
                self,
                name,
                _set_like_strings(name, getattr(self, name), forbid_wildcards=True),
            )
        object.__setattr__(
            self,
            "explicit_denials",
            _set_like_strings("explicit_denials", self.explicit_denials),
        )
        if type(self.allowed_time_window) is not tuple or len(self.allowed_time_window) != 2:
            raise AuthorityContractError("allowed_time_window must be a two-item immutable tuple")
        window_start = _timestamp("allowed_time_window[0]", self.allowed_time_window[0])
        window_end = _timestamp("allowed_time_window[1]", self.allowed_time_window[1])
        _require_later(
            earlier_name="allowed_time_window[0]",
            earlier=window_start,
            later_name="allowed_time_window[1]",
            later=window_end,
        )
        object.__setattr__(self, "allowed_time_window", (window_start, window_end))
        for name in (
            "maximum_requests", "maximum_results", "maximum_payload_bytes",
            "maximum_runtime_seconds", "maximum_subprocesses", "maximum_storage_bytes",
            "maximum_retries", "maximum_cpu", "maximum_memory_bytes",
            "maximum_concurrency", "maximum_cost",
        ):
            object.__setattr__(self, name, _nonnegative(name, getattr(self, name)))
        object.__setattr__(
            self,
            "previous_scope_hash",
            _previous_hash("previous_scope_hash", self.previous_scope_hash, version=self.scope_version),
        )
        object.__setattr__(self, "scope_hash", self.compute_hash())

    def _hash_material(self) -> dict[str, Any]:
        return {
            "allowed_adapters": list(self.allowed_adapters),
            "allowed_destinations": list(self.allowed_destinations),
            "allowed_operations": list(self.allowed_operations),
            "allowed_protocols": list(self.allowed_protocols),
            "allowed_resource_types": list(self.allowed_resource_types),
            "allowed_resources": list(self.allowed_resources),
            "allowed_subjects": list(self.allowed_subjects),
            "allowed_time_window": list(self.allowed_time_window),
            "case_id": self.case_id,
            "explicit_denials": list(self.explicit_denials),
            "maximum_concurrency": self.maximum_concurrency,
            "maximum_cost": self.maximum_cost,
            "maximum_cpu": self.maximum_cpu,
            "maximum_memory_bytes": self.maximum_memory_bytes,
            "maximum_payload_bytes": self.maximum_payload_bytes,
            "maximum_requests": self.maximum_requests,
            "maximum_results": self.maximum_results,
            "maximum_retries": self.maximum_retries,
            "maximum_runtime_seconds": self.maximum_runtime_seconds,
            "maximum_storage_bytes": self.maximum_storage_bytes,
            "maximum_subprocesses": self.maximum_subprocesses,
            "network_permissions": list(self.network_permissions),
            "previous_scope_hash": self.previous_scope_hash,
            "retention_policy": self.retention_policy,
            "scope_id": self.scope_id,
            "scope_version": self.scope_version,
            "write_permissions": list(self.write_permissions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._hash_material(), "scope_hash": self.scope_hash}

    @classmethod
    def from_dict(cls, value: object) -> ExactScope:
        expected = {
            "scope_id", "scope_version", "case_id", "allowed_subjects",
            "allowed_resources", "allowed_resource_types", "allowed_operations",
            "allowed_adapters", "allowed_destinations", "allowed_protocols",
            "allowed_time_window", "maximum_requests", "maximum_results",
            "maximum_payload_bytes", "maximum_runtime_seconds", "maximum_subprocesses",
            "maximum_storage_bytes", "maximum_retries", "maximum_cpu",
            "maximum_memory_bytes", "maximum_concurrency", "maximum_cost",
            "write_permissions", "network_permissions", "retention_policy",
            "explicit_denials", "previous_scope_hash", "scope_hash",
        }
        payload = _strict_payload("ExactScope", value, expected)
        claimed = _hash("scope_hash", payload.pop("scope_hash"))
        for name in (
            "allowed_subjects", "allowed_resources", "allowed_resource_types",
            "allowed_operations", "allowed_adapters", "allowed_destinations",
            "allowed_protocols", "allowed_time_window", "write_permissions",
            "network_permissions", "explicit_denials",
        ):
            payload[name] = _external_tuple(name, payload[name])
        instance = cls(**payload)
        if not hashes_equal(claimed, instance.scope_hash):
            raise AuthorityHashMismatch("scope_hash does not match ExactScope material")
        return instance


@dataclass(frozen=True, slots=True)
class PlanStep(_HashBoundContract):
    step_index: int
    step_id: str
    adapter_id: str
    adapter_version: str
    adapter_entry_hash: str
    operation: str
    normalized_arguments: Any
    resource_identity: Any
    destination: str
    protocol: str
    limits: Any
    expected_output: Any
    evidence_policy: str
    arguments_hash: str = field(init=False)
    resource_hash: str = field(init=False)
    step_hash: str = field(init=False)

    _HASH_DOMAIN: ClassVar[str] = AOIA_PLAN_STEP_V1
    _HASH_FIELD: ClassVar[str] = "step_hash"

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_index", _nonnegative("step_index", self.step_index))
        for name in (
            "step_id", "adapter_id", "adapter_version", "operation", "destination",
            "protocol", "evidence_policy",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "adapter_entry_hash", _hash("adapter_entry_hash", self.adapter_entry_hash))
        object.__setattr__(
            self,
            "normalized_arguments",
            _json_mapping("normalized_arguments", self.normalized_arguments),
        )
        object.__setattr__(
            self,
            "resource_identity",
            _resource_identity("resource_identity", self.resource_identity),
        )
        object.__setattr__(self, "limits", _limits_mapping("limits", self.limits))
        object.__setattr__(self, "expected_output", _json_value("expected_output", self.expected_output))
        object.__setattr__(self, "arguments_hash", hash_normalized_arguments(self.normalized_arguments))
        object.__setattr__(self, "resource_hash", hash_resource_identity(self.resource_identity))
        object.__setattr__(self, "step_hash", self.compute_hash())

    def _hash_material(self) -> dict[str, Any]:
        return {
            "adapter_entry_hash": self.adapter_entry_hash,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "arguments_hash": self.arguments_hash,
            "destination": self.destination,
            "evidence_policy": self.evidence_policy,
            "expected_output": thaw_json(self.expected_output),
            "limits": thaw_json(self.limits),
            "normalized_arguments": thaw_json(self.normalized_arguments),
            "operation": self.operation,
            "protocol": self.protocol,
            "resource_hash": self.resource_hash,
            "resource_identity": thaw_json(self.resource_identity),
            "step_id": self.step_id,
            "step_index": self.step_index,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._hash_material(),
            "step_hash": self.step_hash,
        }

    @classmethod
    def from_dict(cls, value: object) -> PlanStep:
        expected = {
            "step_index", "step_id", "adapter_id", "adapter_version",
            "adapter_entry_hash", "operation", "normalized_arguments",
            "arguments_hash", "resource_identity", "resource_hash", "destination",
            "protocol", "limits", "expected_output", "evidence_policy", "step_hash",
        }
        payload = _strict_payload("PlanStep", value, expected)
        claimed_arguments = _hash("arguments_hash", payload.pop("arguments_hash"))
        claimed_resource = _hash("resource_hash", payload.pop("resource_hash"))
        claimed_step = _hash("step_hash", payload.pop("step_hash"))
        instance = cls(**payload)
        if not hashes_equal(claimed_arguments, instance.arguments_hash):
            raise AuthorityHashMismatch("arguments_hash does not match normalized arguments")
        if not hashes_equal(claimed_resource, instance.resource_hash):
            raise AuthorityHashMismatch("resource_hash does not match resource identity")
        if not hashes_equal(claimed_step, instance.step_hash):
            raise AuthorityHashMismatch("step_hash does not match PlanStep material")
        return instance


@dataclass(frozen=True, slots=True)
class VisiblePlan(_HashBoundContract):
    plan_id: str
    plan_version: int
    case_id: str
    scope_id: str
    ordered_steps: tuple[PlanStep, ...]
    expected_outputs: tuple[Any, ...]
    limits: Any
    data_classification: str
    policy_version: str
    adapter_manifest_version: str
    adapter_manifest_hash: str
    created_by: str
    created_at: str
    status: PlanStatus
    previous_plan_hash: str | None
    plan_hash: str = field(init=False)

    _HASH_DOMAIN: ClassVar[str] = AOIA_VISIBLE_PLAN_V1
    _HASH_FIELD: ClassVar[str] = "plan_hash"

    def __post_init__(self) -> None:
        for name in (
            "plan_id", "case_id", "scope_id", "data_classification", "policy_version",
            "adapter_manifest_version", "created_by",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "plan_version", _version("plan_version", self.plan_version))
        object.__setattr__(self, "adapter_manifest_hash", _hash("adapter_manifest_hash", self.adapter_manifest_hash))
        object.__setattr__(self, "created_at", _timestamp("created_at", self.created_at))
        try:
            status = PlanStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise AuthorityContractError("status is invalid") from exc
        object.__setattr__(self, "status", status)
        if type(self.ordered_steps) is not tuple or not self.ordered_steps:
            raise AuthorityContractError("ordered_steps must be a nonempty immutable tuple")
        if any(type(step) is not PlanStep for step in self.ordered_steps):
            raise AuthorityContractError("ordered_steps must contain PlanStep objects")
        if any(not step.verify_hash() for step in self.ordered_steps):
            raise AuthorityContractError("ordered_steps contains an invalid step hash")
        indexes = tuple(step.step_index for step in self.ordered_steps)
        if indexes != tuple(range(len(self.ordered_steps))):
            raise AuthorityContractError("step indexes must be unique, contiguous, and ordered")
        identifiers = tuple(step.step_id for step in self.ordered_steps)
        if len(set(identifiers)) != len(identifiers):
            raise AuthorityContractError("step IDs must be unique")
        if type(self.expected_outputs) is not tuple:
            raise AuthorityContractError("expected_outputs must be an immutable tuple")
        object.__setattr__(
            self,
            "expected_outputs",
            tuple(_json_value("expected_outputs", value) for value in self.expected_outputs),
        )
        object.__setattr__(self, "limits", _limits_mapping("limits", self.limits))
        object.__setattr__(
            self,
            "previous_plan_hash",
            _previous_hash("previous_plan_hash", self.previous_plan_hash, version=self.plan_version),
        )
        object.__setattr__(self, "plan_hash", self.compute_hash())

    def _hash_material(self) -> dict[str, Any]:
        return {
            "adapter_manifest_hash": self.adapter_manifest_hash,
            "adapter_manifest_version": self.adapter_manifest_version,
            "case_id": self.case_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "data_classification": self.data_classification,
            "expected_outputs": [thaw_json(value) for value in self.expected_outputs],
            "limits": thaw_json(self.limits),
            "ordered_step_hashes": [step.step_hash for step in self.ordered_steps],
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "policy_version": self.policy_version,
            "previous_plan_hash": self.previous_plan_hash,
            "scope_id": self.scope_id,
            "status": self.status.value,
        }

    def to_dict(self) -> dict[str, Any]:
        material = self._hash_material()
        material.pop("ordered_step_hashes")
        return {
            **material,
            "ordered_steps": [step.to_dict() for step in self.ordered_steps],
            "plan_hash": self.plan_hash,
        }

    @classmethod
    def from_dict(cls, value: object) -> VisiblePlan:
        expected = {
            "plan_id", "plan_version", "case_id", "scope_id", "ordered_steps",
            "expected_outputs", "limits", "data_classification", "policy_version",
            "adapter_manifest_version", "adapter_manifest_hash", "created_by",
            "created_at", "status", "previous_plan_hash", "plan_hash",
        }
        payload = _strict_payload("VisiblePlan", value, expected)
        claimed = _hash("plan_hash", payload.pop("plan_hash"))
        raw_steps = _external_tuple("ordered_steps", payload["ordered_steps"])
        payload["ordered_steps"] = tuple(PlanStep.from_dict(step) for step in raw_steps)
        payload["expected_outputs"] = _external_tuple("expected_outputs", payload["expected_outputs"])
        instance = cls(**payload)
        if not hashes_equal(claimed, instance.plan_hash):
            raise AuthorityHashMismatch("plan_hash does not match VisiblePlan material")
        return instance


@dataclass(frozen=True, slots=True)
class HumanApproval(_HashBoundContract):
    approval_schema_version: int
    approval_id: str
    case_id: str
    case_version: int
    case_hash: str
    scope_id: str
    scope_version: int
    scope_hash: str
    plan_id: str
    plan_version: int
    plan_hash: str
    policy_version: str
    canonical_policy_input_hash: str
    adapter_manifest_version: str
    adapter_manifest_hash: str
    operator_identity: str
    operator_session_id: str
    approved_at: str
    expires_at: str
    nonce: str
    approved_action_identities: tuple[str, ...]
    status_at_issue: ApprovalStatus
    maximum_uses: int = 1
    approval_hash: str = field(init=False)

    _HASH_DOMAIN: ClassVar[str] = AOIA_HUMAN_EXECUTION_APPROVAL_V1
    _HASH_FIELD: ClassVar[str] = "approval_hash"

    def __post_init__(self) -> None:
        for name in (
            "approval_id", "case_id", "scope_id", "plan_id", "policy_version",
            "adapter_manifest_version", "operator_identity", "operator_session_id", "nonce",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        for name in ("approval_schema_version", "case_version", "scope_version", "plan_version"):
            object.__setattr__(self, name, _version(name, getattr(self, name)))
        if self.approval_schema_version != 1:
            raise AuthorityContractError("approval_schema_version is not supported")
        for name in (
            "case_hash", "scope_hash", "plan_hash", "canonical_policy_input_hash",
            "adapter_manifest_hash",
        ):
            object.__setattr__(self, name, _hash(name, getattr(self, name)))
        object.__setattr__(self, "approved_at", _timestamp("approved_at", self.approved_at))
        object.__setattr__(self, "expires_at", _timestamp("expires_at", self.expires_at))
        _require_later(
            earlier_name="approved_at",
            earlier=self.approved_at,
            later_name="expires_at",
            later=self.expires_at,
        )
        object.__setattr__(self, "maximum_uses", _version("maximum_uses", self.maximum_uses))
        object.__setattr__(
            self,
            "approved_action_identities",
            _ordered_unique_strings(
                "approved_action_identities",
                self.approved_action_identities,
                nonempty=True,
            ),
        )
        try:
            status = ApprovalStatus(self.status_at_issue)
        except (TypeError, ValueError) as exc:
            raise AuthorityContractError("status_at_issue is invalid") from exc
        if status is not ApprovalStatus.ACTIVE:
            raise AuthorityContractError("status_at_issue must be ACTIVE")
        object.__setattr__(self, "status_at_issue", status)
        object.__setattr__(self, "approval_hash", self.compute_hash())

    def _hash_material(self) -> dict[str, Any]:
        return {
            "adapter_manifest_hash": self.adapter_manifest_hash,
            "adapter_manifest_version": self.adapter_manifest_version,
            "approval_id": self.approval_id,
            "approval_schema_version": self.approval_schema_version,
            "approved_action_identities": list(self.approved_action_identities),
            "approved_at": self.approved_at,
            "canonical_policy_input_hash": self.canonical_policy_input_hash,
            "case_hash": self.case_hash,
            "case_id": self.case_id,
            "case_version": self.case_version,
            "expires_at": self.expires_at,
            "maximum_uses": self.maximum_uses,
            "nonce": self.nonce,
            "operator_identity": self.operator_identity,
            "operator_session_id": self.operator_session_id,
            "plan_hash": self.plan_hash,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "policy_version": self.policy_version,
            "scope_hash": self.scope_hash,
            "scope_id": self.scope_id,
            "scope_version": self.scope_version,
            "status_at_issue": self.status_at_issue.value,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._hash_material(), "approval_hash": self.approval_hash}

    @classmethod
    def from_dict(cls, value: object) -> HumanApproval:
        expected = {
            "approval_schema_version", "approval_id", "case_id", "case_version",
            "case_hash", "scope_id", "scope_version", "scope_hash", "plan_id",
            "plan_version", "plan_hash", "policy_version", "canonical_policy_input_hash",
            "adapter_manifest_version", "adapter_manifest_hash", "operator_identity",
            "operator_session_id", "approved_at", "expires_at", "nonce",
            "maximum_uses", "approved_action_identities", "status_at_issue", "approval_hash",
        }
        payload = _strict_payload("HumanApproval", value, expected)
        claimed = _hash("approval_hash", payload.pop("approval_hash"))
        payload["approved_action_identities"] = _external_tuple(
            "approved_action_identities", payload["approved_action_identities"]
        )
        instance = cls(**payload)
        if not hashes_equal(claimed, instance.approval_hash):
            raise AuthorityHashMismatch("approval_hash does not match HumanApproval material")
        return instance


@dataclass(frozen=True, slots=True)
class ApprovedExecutionRequest(_HashBoundContract):
    schema_version: int
    execution_id: str
    case_id: str
    case_hash: str
    scope_id: str
    scope_hash: str
    plan_id: str
    plan_hash: str
    approval_id: str
    approval_hash: str
    approval_nonce: str
    operator_session_id: str
    action_id: str
    step_id: str
    policy_version: str
    policy_decision_id: str
    policy_decision_hash: str
    adapter_id: str
    adapter_version: str
    adapter_manifest_version: str
    adapter_manifest_hash: str
    adapter_entry_hash: str
    normalized_arguments: Any
    arguments_hash: str
    resource_identity: Any
    resource_hash: str
    resource_limits: Any
    resource_reservation_id: str
    resource_reservation_hash: str
    exact_destination: str
    protocol: str
    evidence_policy_id: str
    evidence_policy_hash: str
    redaction_policy_id: str
    redaction_policy_hash: str
    audit_policy_id: str
    audit_policy_hash: str
    kill_switch_snapshot: Any
    created_at: str
    expires_at: str
    execution_request_hash: str = field(init=False)

    _HASH_DOMAIN: ClassVar[str] = AOIA_APPROVED_EXECUTION_REQUEST_V1
    _HASH_FIELD: ClassVar[str] = "execution_request_hash"

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _version("schema_version", self.schema_version))
        if self.schema_version != 1:
            raise AuthorityContractError("schema_version is not supported")
        for name in (
            "execution_id", "case_id", "scope_id", "plan_id", "approval_id",
            "approval_nonce", "operator_session_id", "action_id", "step_id",
            "policy_version", "policy_decision_id", "adapter_id", "adapter_version",
            "adapter_manifest_version", "resource_reservation_id", "exact_destination",
            "protocol", "evidence_policy_id", "redaction_policy_id", "audit_policy_id",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        for name in (
            "case_hash", "scope_hash", "plan_hash", "approval_hash",
            "policy_decision_hash", "adapter_manifest_hash", "adapter_entry_hash",
            "arguments_hash", "resource_hash", "resource_reservation_hash",
            "evidence_policy_hash", "redaction_policy_hash", "audit_policy_hash",
        ):
            object.__setattr__(self, name, _hash(name, getattr(self, name)))
        object.__setattr__(
            self,
            "normalized_arguments",
            _json_mapping("normalized_arguments", self.normalized_arguments),
        )
        object.__setattr__(
            self,
            "resource_identity",
            _resource_identity("resource_identity", self.resource_identity),
        )
        object.__setattr__(
            self,
            "resource_limits",
            _limits_mapping("resource_limits", self.resource_limits),
        )
        object.__setattr__(
            self,
            "kill_switch_snapshot",
            _json_mapping("kill_switch_snapshot", self.kill_switch_snapshot, nonempty=True),
        )
        if not hashes_equal(self.arguments_hash, hash_normalized_arguments(self.normalized_arguments)):
            raise AuthorityHashMismatch("arguments_hash does not match normalized arguments")
        if not hashes_equal(self.resource_hash, hash_resource_identity(self.resource_identity)):
            raise AuthorityHashMismatch("resource_hash does not match resource identity")
        object.__setattr__(self, "created_at", _timestamp("created_at", self.created_at))
        object.__setattr__(self, "expires_at", _timestamp("expires_at", self.expires_at))
        _require_later(
            earlier_name="created_at",
            earlier=self.created_at,
            later_name="expires_at",
            later=self.expires_at,
        )
        object.__setattr__(self, "execution_request_hash", self.compute_hash())

    def _hash_material(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "adapter_entry_hash": self.adapter_entry_hash,
            "adapter_id": self.adapter_id,
            "adapter_manifest_hash": self.adapter_manifest_hash,
            "adapter_manifest_version": self.adapter_manifest_version,
            "adapter_version": self.adapter_version,
            "approval_hash": self.approval_hash,
            "approval_id": self.approval_id,
            "approval_nonce": self.approval_nonce,
            "arguments_hash": self.arguments_hash,
            "audit_policy_hash": self.audit_policy_hash,
            "audit_policy_id": self.audit_policy_id,
            "case_hash": self.case_hash,
            "case_id": self.case_id,
            "created_at": self.created_at,
            "evidence_policy_hash": self.evidence_policy_hash,
            "evidence_policy_id": self.evidence_policy_id,
            "exact_destination": self.exact_destination,
            "execution_id": self.execution_id,
            "expires_at": self.expires_at,
            "kill_switch_snapshot": thaw_json(self.kill_switch_snapshot),
            "normalized_arguments": thaw_json(self.normalized_arguments),
            "operator_session_id": self.operator_session_id,
            "plan_hash": self.plan_hash,
            "plan_id": self.plan_id,
            "policy_decision_hash": self.policy_decision_hash,
            "policy_decision_id": self.policy_decision_id,
            "policy_version": self.policy_version,
            "protocol": self.protocol,
            "redaction_policy_hash": self.redaction_policy_hash,
            "redaction_policy_id": self.redaction_policy_id,
            "resource_hash": self.resource_hash,
            "resource_identity": thaw_json(self.resource_identity),
            "resource_limits": thaw_json(self.resource_limits),
            "resource_reservation_hash": self.resource_reservation_hash,
            "resource_reservation_id": self.resource_reservation_id,
            "schema_version": self.schema_version,
            "scope_hash": self.scope_hash,
            "scope_id": self.scope_id,
            "step_id": self.step_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._hash_material(), "execution_request_hash": self.execution_request_hash}

    @classmethod
    def from_dict(cls, value: object) -> ApprovedExecutionRequest:
        expected = {
            "schema_version", "execution_id", "case_id", "case_hash", "scope_id",
            "scope_hash", "plan_id", "plan_hash", "approval_id", "approval_hash",
            "approval_nonce", "operator_session_id", "action_id", "step_id",
            "policy_version", "policy_decision_id", "policy_decision_hash", "adapter_id",
            "adapter_version", "adapter_manifest_version", "adapter_manifest_hash",
            "adapter_entry_hash", "normalized_arguments", "arguments_hash",
            "resource_identity", "resource_hash", "resource_limits",
            "resource_reservation_id", "resource_reservation_hash", "exact_destination",
            "protocol", "evidence_policy_id", "evidence_policy_hash",
            "redaction_policy_id", "redaction_policy_hash", "audit_policy_id",
            "audit_policy_hash", "kill_switch_snapshot", "created_at", "expires_at",
            "execution_request_hash",
        }
        payload = _strict_payload("ApprovedExecutionRequest", value, expected)
        claimed = _hash("execution_request_hash", payload.pop("execution_request_hash"))
        instance = cls(**payload)
        if not hashes_equal(claimed, instance.execution_request_hash):
            raise AuthorityHashMismatch(
                "execution_request_hash does not match ApprovedExecutionRequest material"
            )
        return instance


def validate_authority_bindings(
    *,
    case: Case,
    scope: ExactScope,
    plan: VisiblePlan,
    approval: HumanApproval,
    request: ApprovedExecutionRequest | None = None,
) -> None:
    """Validate one exact structural chain without granting execution authority."""

    contracts = (
        ("case", case, Case),
        ("scope", scope, ExactScope),
        ("plan", plan, VisiblePlan),
        ("approval", approval, HumanApproval),
    )
    for name, value, expected_type in contracts:
        if type(value) is not expected_type or not value.verify_hash():
            raise AuthorityBindingMismatch(f"{name} contract is invalid")
    if case.status is not CaseStatus.OPEN:
        raise AuthorityBindingMismatch("case is not OPEN")
    if plan.status not in {PlanStatus.REVIEWABLE, PlanStatus.APPROVED}:
        raise AuthorityBindingMismatch("plan is not reviewable")
    if approval.status_at_issue is not ApprovalStatus.ACTIVE:
        raise AuthorityBindingMismatch("approval was not issued ACTIVE")
    exact_bindings = (
        ("scope.case_id", scope.case_id, case.case_id),
        ("case.scope_id", case.scope_id, scope.scope_id),
        ("plan.case_id", plan.case_id, case.case_id),
        ("plan.scope_id", plan.scope_id, scope.scope_id),
        ("plan.policy_version", plan.policy_version, case.policy_version),
        (
            "plan.data_classification",
            plan.data_classification,
            case.data_classification,
        ),
        ("approval.case_id", approval.case_id, case.case_id),
        ("approval.case_version", approval.case_version, case.case_version),
        ("approval.case_hash", approval.case_hash, case.case_hash),
        ("approval.scope_id", approval.scope_id, scope.scope_id),
        ("approval.scope_version", approval.scope_version, scope.scope_version),
        ("approval.scope_hash", approval.scope_hash, scope.scope_hash),
        ("approval.plan_id", approval.plan_id, plan.plan_id),
        ("approval.plan_version", approval.plan_version, plan.plan_version),
        ("approval.plan_hash", approval.plan_hash, plan.plan_hash),
        ("approval.policy_version", approval.policy_version, plan.policy_version),
        (
            "approval.adapter_manifest_version",
            approval.adapter_manifest_version,
            plan.adapter_manifest_version,
        ),
        (
            "approval.adapter_manifest_hash",
            approval.adapter_manifest_hash,
            plan.adapter_manifest_hash,
        ),
    )
    for name, actual, expected in exact_bindings:
        if actual != expected:
            raise AuthorityBindingMismatch(f"{name} binding differs")
    if case.authorization_subject not in scope.allowed_subjects:
        raise AuthorityBindingMismatch("case authorization subject is outside scope")
    scope_limit_fields = {
        "maximum_concurrency": "maximum_concurrency",
        "maximum_cost": "maximum_cost",
        "maximum_cpu": "maximum_cpu",
        "maximum_input_bytes": "maximum_payload_bytes",
        "maximum_memory_bytes": "maximum_memory_bytes",
        "maximum_output_bytes": "maximum_payload_bytes",
        "maximum_payload_bytes": "maximum_payload_bytes",
        "maximum_requests": "maximum_requests",
        "maximum_results": "maximum_results",
        "maximum_retries": "maximum_retries",
        "maximum_runtime_seconds": "maximum_runtime_seconds",
        "maximum_storage_bytes": "maximum_storage_bytes",
        "maximum_subprocesses": "maximum_subprocesses",
        "timeout_seconds": "maximum_runtime_seconds",
    }

    def validate_limits(label: str, limits: FrozenDict) -> dict[str, int]:
        effective: dict[str, int] = {}
        for limit_name, requested in limits.items():
            scope_field = scope_limit_fields.get(limit_name)
            if scope_field is None:
                raise AuthorityBindingMismatch(f"{label}.{limit_name} is not scope-bound")
            if scope_field in effective:
                raise AuthorityBindingMismatch(
                    f"{label} contains duplicate aliases for {scope_field}"
                )
            if requested > getattr(scope, scope_field):
                raise AuthorityBindingMismatch(f"{label}.{limit_name} exceeds scope")
            effective[scope_field] = requested
        return effective

    plan_limits = validate_limits("plan.limits", plan.limits)
    for step in plan.ordered_steps:
        resource_id = step.resource_identity["resource_id"]
        resource_type = step.resource_identity["resource_type"]
        memberships = (
            ("adapter", step.adapter_id, scope.allowed_adapters),
            ("operation", step.operation, scope.allowed_operations),
            ("resource", resource_id, scope.allowed_resources),
            ("resource type", resource_type, scope.allowed_resource_types),
            ("destination", step.destination, scope.allowed_destinations),
            ("protocol", step.protocol, scope.allowed_protocols),
        )
        for label, value, allowed in memberships:
            if value not in allowed:
                raise AuthorityBindingMismatch(f"plan step {label} is outside scope")
        step_limits = validate_limits(f"plan step {step.step_id}.limits", step.limits)
        for limit_name, requested in step_limits.items():
            plan_limit = plan_limits.get(limit_name)
            if plan_limit is not None and requested > plan_limit:
                raise AuthorityBindingMismatch(
                    f"plan step {step.step_id}.{limit_name} exceeds visible plan"
                )

    case_created = datetime.fromisoformat(case.created_at[:-1] + "+00:00")
    plan_created = datetime.fromisoformat(plan.created_at[:-1] + "+00:00")
    approval_start = datetime.fromisoformat(approval.approved_at[:-1] + "+00:00")
    approval_end = datetime.fromisoformat(approval.expires_at[:-1] + "+00:00")
    authorization_windows = (
        (
            "case authorization",
            datetime.fromisoformat(case.authorization_valid_from[:-1] + "+00:00"),
            datetime.fromisoformat(case.authorization_valid_until[:-1] + "+00:00"),
        ),
        (
            "scope",
            datetime.fromisoformat(scope.allowed_time_window[0][:-1] + "+00:00"),
            datetime.fromisoformat(scope.allowed_time_window[1][:-1] + "+00:00"),
        ),
    )
    case_window = authorization_windows[0]
    scope_window = authorization_windows[1]
    if scope_window[1] < case_window[1] or scope_window[2] > case_window[2]:
        raise AuthorityBindingMismatch("scope window exceeds case authorization")
    if plan_created < case_created:
        raise AuthorityBindingMismatch("visible plan predates case creation")
    if approval_start < plan_created:
        raise AuthorityBindingMismatch("approval predates the visible plan")
    for label, start, end in authorization_windows:
        if plan_created < start or plan_created > end:
            raise AuthorityBindingMismatch(f"plan is outside the {label} window")
        if approval_start < start or approval_end > end:
            raise AuthorityBindingMismatch(f"approval is outside the {label} window")
    if request is None:
        return
    if type(request) is not ApprovedExecutionRequest or not request.verify_hash():
        raise AuthorityBindingMismatch("request contract is invalid")
    request_bindings = (
        ("request.case_id", request.case_id, case.case_id),
        ("request.case_hash", request.case_hash, case.case_hash),
        ("request.scope_id", request.scope_id, scope.scope_id),
        ("request.scope_hash", request.scope_hash, scope.scope_hash),
        ("request.plan_id", request.plan_id, plan.plan_id),
        ("request.plan_hash", request.plan_hash, plan.plan_hash),
        ("request.approval_id", request.approval_id, approval.approval_id),
        ("request.approval_hash", request.approval_hash, approval.approval_hash),
        ("request.approval_nonce", request.approval_nonce, approval.nonce),
        (
            "request.operator_session_id",
            request.operator_session_id,
            approval.operator_session_id,
        ),
        ("request.policy_version", request.policy_version, plan.policy_version),
        (
            "request.adapter_manifest_version",
            request.adapter_manifest_version,
            plan.adapter_manifest_version,
        ),
        (
            "request.adapter_manifest_hash",
            request.adapter_manifest_hash,
            plan.adapter_manifest_hash,
        ),
    )
    for name, actual, expected in request_bindings:
        if actual != expected:
            raise AuthorityBindingMismatch(f"{name} binding differs")
    if request.action_id not in approval.approved_action_identities:
        raise AuthorityBindingMismatch("request action is not approved")
    matching_steps = tuple(step for step in plan.ordered_steps if step.step_id == request.step_id)
    if len(matching_steps) != 1:
        raise AuthorityBindingMismatch("request step is not in the visible plan")
    step = matching_steps[0]
    step_bindings = (
        ("request.adapter_id", request.adapter_id, step.adapter_id),
        ("request.adapter_version", request.adapter_version, step.adapter_version),
        ("request.adapter_entry_hash", request.adapter_entry_hash, step.adapter_entry_hash),
        ("request.arguments_hash", request.arguments_hash, step.arguments_hash),
        ("request.resource_hash", request.resource_hash, step.resource_hash),
        ("request.exact_destination", request.exact_destination, step.destination),
        ("request.protocol", request.protocol, step.protocol),
        ("request.evidence_policy_id", request.evidence_policy_id, step.evidence_policy),
        ("request.normalized_arguments", request.normalized_arguments, step.normalized_arguments),
        ("request.resource_identity", request.resource_identity, step.resource_identity),
        ("request.resource_limits", request.resource_limits, step.limits),
    )
    for name, actual, expected in step_bindings:
        if actual != expected:
            raise AuthorityBindingMismatch(f"{name} binding differs")
    validate_limits("request.resource_limits", request.resource_limits)
    request_start = datetime.fromisoformat(request.created_at[:-1] + "+00:00")
    request_end = datetime.fromisoformat(request.expires_at[:-1] + "+00:00")
    windows = (
        *authorization_windows,
        (
            "approval",
            approval_start,
            approval_end,
        ),
    )
    for name, start, end in windows:
        if request_start < start or request_end > end:
            raise AuthorityBindingMismatch(f"request is outside the {name} window")


__all__ = (
    "AOIA_APPROVED_EXECUTION_REQUEST_V1",
    "AOIA_CASE_V1",
    "AOIA_EXACT_SCOPE_V1",
    "AOIA_HUMAN_EXECUTION_APPROVAL_V1",
    "AOIA_NORMALIZED_ARGUMENTS_V1",
    "AOIA_PLAN_STEP_V1",
    "AOIA_RESOURCE_IDENTITY_V1",
    "AOIA_VISIBLE_PLAN_V1",
    "ApprovalStatus",
    "ApprovedExecutionRequest",
    "AuthorityBindingMismatch",
    "AuthorityContractError",
    "AuthorityHashMismatch",
    "Case",
    "CaseStatus",
    "ExactScope",
    "HumanApproval",
    "PlanStatus",
    "PlanStep",
    "VisiblePlan",
    "hash_normalized_arguments",
    "hash_resource_identity",
    "validate_authority_bindings",
)
