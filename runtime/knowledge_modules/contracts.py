"""Immutable provider-independent contracts for Knowledge Hub 1A."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, Mapping


NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
DESCRIPTOR_SCHEMA_VERSION = "knowledge-module-descriptor-1a"
CONFIGURATION_SCHEMA_VERSION = "knowledge-module-configuration-1a"
FAILURE_SCHEMA_VERSION = "knowledge-module-failure-1a"
VERIFICATION_SCHEMA_VERSION = "knowledge-module-verification-1a"

AUTHORITY_FLAG_NAMES = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "can_satisfy_human_barrier",
    "can_provide_binding_legal_advice",
    "gate_satisfied",
)

_HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_MODULE_ID = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")


class KnowledgeModuleError(ValueError):
    """Stable fail-closed error raised by common Knowledge Module contracts."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


def _json_compatible(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_compatible(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _json_compatible(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (tuple, list)):
        return [_json_compatible(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"value is not JSON-compatible: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON with sorted keys and compact separators."""

    return json.dumps(
        _json_compatible(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    status: str = "MODULE_OUTPUT_MALFORMED",
    label: str = "object",
) -> None:
    if not isinstance(value, Mapping):
        raise KnowledgeModuleError(status, f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise KnowledgeModuleError(
            status,
            f"{label} fields differ; missing={missing}, unknown={unknown}",
        )


def false_authority_values() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_FLAG_NAMES}


def reject_enabled_authority(
    value: Any,
    *,
    status: str = "MODULE_AUTHORITY_CLAIM_BLOCKED",
) -> None:
    """Recursively reject any external attempt to enable an authority flag."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in AUTHORITY_FLAG_NAMES and item is not False:
                raise KnowledgeModuleError(status, f"authority field {key} must be false")
            reject_enabled_authority(item, status=status)
    elif isinstance(value, (tuple, list)):
        for item in value:
            reject_enabled_authority(item, status=status)


def _tuple_strings(name: str, value: Any, *, sort_values: bool = False) -> tuple[str, ...]:
    if isinstance(value, str):
        raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} must be a sequence")
    try:
        result = tuple(value)
    except TypeError as exc:
        raise KnowledgeModuleError(
            "INVALID_MODULE_CONTRACT", f"{name} must be a sequence"
        ) from exc
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise KnowledgeModuleError(
            "INVALID_MODULE_CONTRACT", f"{name} contains an invalid string"
        )
    normalized = tuple(item.strip() for item in result)
    if len(normalized) != len(set(normalized)):
        raise KnowledgeModuleError(
            "INVALID_MODULE_CONTRACT", f"{name} contains duplicates"
        )
    return tuple(sorted(normalized)) if sort_values else normalized


class JsonContract:
    def to_dict(self) -> dict[str, Any]:
        value = _json_compatible(self)
        if not isinstance(value, dict):
            raise TypeError("contract did not serialize to an object")
        return value


@dataclass(frozen=True, slots=True)
class KnowledgeModuleDescriptor(JsonContract):
    schema_version: str
    module_id: str
    module_version: str
    display_name: str
    description: str
    domain: str
    subdomains: tuple[str, ...]
    jurisdictions: tuple[str, ...]
    languages: tuple[str, ...]
    source_classes: tuple[str, ...]
    corpus_snapshot_ids: tuple[str, ...]
    temporal_snapshot_id: str
    retrieval_modes: tuple[str, ...]
    supported_filters: tuple[str, ...]
    coverage_status: str
    currentness_status: str
    licence_status: str
    known_limitations: tuple[str, ...]
    enabled_by_default: bool
    authority_status: str
    capability_ids: tuple[str, ...]
    descriptor_hash: str = ""
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
        if self.schema_version != DESCRIPTOR_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "descriptor schema differs")
        if not isinstance(self.module_id, str) or not _MODULE_ID.fullmatch(self.module_id):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "invalid module_id")
        for name in (
            "module_version",
            "display_name",
            "description",
            "domain",
            "temporal_snapshot_id",
            "coverage_status",
            "currentness_status",
            "licence_status",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", f"{name} is required")
        for name in (
            "subdomains",
            "jurisdictions",
            "languages",
            "source_classes",
            "corpus_snapshot_ids",
            "supported_filters",
            "known_limitations",
            "capability_ids",
        ):
            object.__setattr__(
                self,
                name,
                _tuple_strings(name, getattr(self, name), sort_values=True),
            )
        object.__setattr__(
            self,
            "retrieval_modes",
            _tuple_strings("retrieval_modes", self.retrieval_modes),
        )
        if self.retrieval_modes != ("SOURCE_DISCOVERY", "VERIFIED_AS_OF"):
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONTRACT",
                "descriptor must expose exactly SOURCE_DISCOVERY and VERIFIED_AS_OF",
            )
        if not self.jurisdictions or not self.languages or not self.corpus_snapshot_ids:
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONTRACT", "descriptor coverage identity is incomplete"
            )
        if self.authority_status != NON_AUTHORITATIVE:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "descriptor is authoritative"
            )
        if type(self.enabled_by_default) is not bool or self.enabled_by_default:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "module cannot be enabled by default"
            )
        if self.capability_ids:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "module cannot carry capabilities"
            )
        if any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "descriptor authority flags must be false"
            )
        payload = self.to_dict()
        supplied = payload.pop("descriptor_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError(
                "MODULE_DESCRIPTOR_MISMATCH", "descriptor hash does not match its fields"
            )
        object.__setattr__(self, "descriptor_hash", expected)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeModuleDescriptor":
        exact_fields(
            value,
            set(cls.__dataclass_fields__),
            status="INVALID_MODULE_CONTRACT",
            label="KnowledgeModuleDescriptor",
        )
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class KnowledgeModuleConfiguration(JsonContract):
    schema_version: str
    module_repository_path: str
    corpus_data_root: str
    approved_resolved_corpus_path: str
    expected_repository_head: str
    expected_module_id: str
    expected_module_version: str
    expected_descriptor_hash: str
    expected_corpus_snapshot_id: str
    expected_corpus_snapshot_ids: tuple[str, ...]
    expected_temporal_snapshot_id: str
    expected_eu_snapshot_id: str
    expected_eu_snapshot_manifest_hash: str
    expected_manifest_hashes: tuple[tuple[str, str], ...]
    query_timeout_seconds: int = 60
    verification_timeout_seconds: int = 1_800
    maximum_stdout_bytes: int = 524_288
    maximum_stderr_bytes: int = 65_536

    def __post_init__(self) -> None:
        if self.schema_version != CONFIGURATION_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONFIGURATION", "configuration schema differs")
        for name in (
            "module_repository_path",
            "corpus_data_root",
            "approved_resolved_corpus_path",
            "expected_module_id",
            "expected_module_version",
            "expected_corpus_snapshot_id",
            "expected_temporal_snapshot_id",
            "expected_eu_snapshot_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONFIGURATION", f"{name} is required"
                )
        if not _MODULE_ID.fullmatch(self.expected_module_id):
            raise KnowledgeModuleError("INVALID_MODULE_CONFIGURATION", "invalid expected module ID")
        if not _HEX_40.fullmatch(self.expected_repository_head):
            raise KnowledgeModuleError("INVALID_MODULE_CONFIGURATION", "invalid repository pin")
        for name in ("expected_descriptor_hash", "expected_eu_snapshot_manifest_hash"):
            if not _HEX_64.fullmatch(getattr(self, name)):
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONFIGURATION", f"{name} must be a SHA-256"
                )
        snapshots = _tuple_strings(
            "expected_corpus_snapshot_ids",
            self.expected_corpus_snapshot_ids,
            sort_values=True,
        )
        if not snapshots:
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONFIGURATION", "corpus snapshot pins are required"
            )
        object.__setattr__(self, "expected_corpus_snapshot_ids", snapshots)
        manifest_pairs: list[tuple[str, str]] = []
        for item in self.expected_manifest_hashes:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONFIGURATION", "manifest pins must be path/hash pairs"
                )
            relative, digest = item
            if (
                not isinstance(relative, str)
                or not relative
                or relative.startswith("/")
                or ".." in relative.split("/")
                or not isinstance(digest, str)
                or not _HEX_64.fullmatch(digest)
            ):
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONFIGURATION", "invalid manifest path or hash pin"
                )
            manifest_pairs.append((relative, digest))
        if not manifest_pairs or len(manifest_pairs) != len({path for path, _ in manifest_pairs}):
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONFIGURATION", "manifest pins are missing or duplicated"
            )
        object.__setattr__(self, "expected_manifest_hashes", tuple(sorted(manifest_pairs)))
        limits = (
            ("query_timeout_seconds", self.query_timeout_seconds, 1, 600),
            ("verification_timeout_seconds", self.verification_timeout_seconds, 1, 3_600),
            ("maximum_stdout_bytes", self.maximum_stdout_bytes, 4_096, 1_048_576),
            ("maximum_stderr_bytes", self.maximum_stderr_bytes, 1_024, 262_144),
        )
        for name, value, minimum, maximum in limits:
            if type(value) is not int or not minimum <= value <= maximum:
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONFIGURATION",
                    f"{name} must be an integer from {minimum} through {maximum}",
                )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeModuleConfiguration":
        if not isinstance(value, Mapping):
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONFIGURATION", "configuration must be an object"
            )
        unknown = sorted(set(value) - set(cls.__dataclass_fields__))
        if unknown:
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONFIGURATION",
                f"KnowledgeModuleConfiguration unknown fields: {unknown}",
            )
        try:
            return cls(**dict(value))
        except TypeError as exc:
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONFIGURATION", "configuration fields are incomplete"
            ) from exc


@dataclass(frozen=True, slots=True)
class KnowledgeModuleFailure(JsonContract):
    schema_version: str
    module_id: str
    code: str
    message: str
    details: tuple[tuple[str, str], ...] = ()
    authority_status: str = NON_AUTHORITATIVE
    failure_hash: str = ""
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
        if self.schema_version != FAILURE_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "failure schema differs")
        if any(
            not isinstance(value, str) or not value
            for value in (self.module_id, self.code, self.message)
        ):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "failure identity is incomplete")
        normalized: list[tuple[str, str]] = []
        for item in self.details:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "invalid failure details")
            key, value = item
            if not isinstance(key, str) or not isinstance(value, str):
                raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "invalid failure details")
            normalized.append((key, value))
        object.__setattr__(self, "details", tuple(sorted(normalized)))
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "failure cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("failure_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "failure hash differs")
        object.__setattr__(self, "failure_hash", expected)

    @classmethod
    def create(
        cls,
        module_id: str,
        code: str,
        message: str,
        *,
        details: tuple[tuple[str, str], ...] = (),
    ) -> "KnowledgeModuleFailure":
        return cls(
            schema_version=FAILURE_SCHEMA_VERSION,
            module_id=module_id,
            code=code,
            message=message,
            details=details,
        )


@dataclass(frozen=True, slots=True)
class KnowledgeModuleVerificationResult(JsonContract):
    schema_version: str
    module_id: str
    module_version: str
    valid: bool
    status: str
    repository_head: str | None
    descriptor_hash: str | None
    resolved_corpus_path: str | None
    corpus_snapshot_ids: tuple[str, ...]
    temporal_snapshot_id: str | None
    manifest_hashes: tuple[tuple[str, str], ...]
    external_verification_hash: str | None
    descriptor: KnowledgeModuleDescriptor | None
    failures: tuple[KnowledgeModuleFailure, ...]
    network_calls: int = 0
    provider_calls: int = 0
    authority_status: str = NON_AUTHORITATIVE
    verification_hash: str = ""
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
        if self.schema_version != VERIFICATION_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "verification schema differs")
        if type(self.valid) is not bool or not self.module_id or not self.module_version or not self.status:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "invalid verification result")
        object.__setattr__(
            self,
            "corpus_snapshot_ids",
            _tuple_strings(
                "corpus_snapshot_ids", self.corpus_snapshot_ids, sort_values=True
            ),
        )
        object.__setattr__(self, "manifest_hashes", tuple(sorted(self.manifest_hashes)))
        object.__setattr__(
            self,
            "failures",
            tuple(sorted(self.failures, key=lambda item: (item.module_id, item.code, item.message))),
        )
        if self.valid:
            if self.status != "VERIFIED" or self.failures or self.descriptor is None:
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONTRACT", "valid verification result is incomplete"
                )
            if self.descriptor.module_id != self.module_id:
                raise KnowledgeModuleError(
                    "INVALID_MODULE_CONTRACT", "verified descriptor module differs"
                )
        elif not self.failures:
            raise KnowledgeModuleError(
                "INVALID_MODULE_CONTRACT", "failed verification requires a failure"
            )
        if self.network_calls != 0 or self.provider_calls != 0:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "verification cannot call network or provider"
            )
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "verification cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("verification_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "verification hash differs")
        object.__setattr__(self, "verification_hash", expected)


__all__ = (
    "AUTHORITY_FLAG_NAMES",
    "CONFIGURATION_SCHEMA_VERSION",
    "DESCRIPTOR_SCHEMA_VERSION",
    "FAILURE_SCHEMA_VERSION",
    "KnowledgeModuleConfiguration",
    "KnowledgeModuleDescriptor",
    "KnowledgeModuleError",
    "KnowledgeModuleFailure",
    "KnowledgeModuleVerificationResult",
    "NON_AUTHORITATIVE",
    "VERIFICATION_SCHEMA_VERSION",
    "canonical_hash",
    "canonical_json_bytes",
    "exact_fields",
    "false_authority_values",
    "reject_enabled_authority",
)
