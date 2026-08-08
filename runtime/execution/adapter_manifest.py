"""Strict, hash-bound, non-executing adapter manifest metadata.

R3.2 defines which adapter identities may exist and what those identities may
claim.  It deliberately contains no adapter implementation, dispatch, provider,
network, process, credential-store, or filesystem-mutation capability.
"""

from __future__ import annotations

if __name__ != "runtime.execution.adapter_manifest":
    raise ImportError(
        "adapter manifest metadata must be imported as "
        "runtime.execution.adapter_manifest"
    )

import ipaddress
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from .canonical_serialization import (
    CanonicalSerializationError,
    FrozenDict,
    canonical_json_bytes,
    domain_separated_sha256,
    freeze_json,
    hashes_equal,
    require_sha256,
    thaw_json,
)


AOIA_ADAPTER_MANIFEST_ENTRY_V1: Final = "AOIA_ADAPTER_MANIFEST_ENTRY_V1"
AOIA_ADAPTER_MANIFEST_V1: Final = "AOIA_ADAPTER_MANIFEST_V1"
AOIA_ADAPTER_IMPLEMENTATION_V1: Final = "AOIA_ADAPTER_IMPLEMENTATION_V1"
AOIA_DATA_SCHEMA_V1: Final = "AOIA_DATA_SCHEMA_V1"

_MANIFEST_PATH: Final = Path(__file__).with_name("adapter_manifest_registry.json")
_MAX_MANIFEST_BYTES: Final = 8_388_608
_MAX_ADAPTERS: Final = 1_024
_MAX_IDENTIFIER_BYTES: Final = 128
_MAX_SCHEMA_DEPTH: Final = 8
_MAX_SCHEMA_NODES: Final = 256
_MAX_SCHEMA_PROPERTIES: Final = 256
_MAX_SCHEMA_STRING_BYTES: Final = 1_073_741_824
_MAX_SCHEMA_ITEMS: Final = 10_000
_MAX_POLICY_ITEMS: Final = 10_000

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_VERSION = re.compile(r"^[1-9][0-9]*$")
_CREDENTIAL_REFERENCE = re.compile(r"^credential:[a-z][a-z0-9._-]{0,127}$")
_SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

_TOP_LEVEL_FIELDS: Final = {
    "schema_version",
    "manifest_version",
    "adapters",
    "manifest_hash",
}
_ENTRY_FIELDS: Final = {
    "adapter_id",
    "adapter_version",
    "adapter_type",
    "implementation_reference",
    "operation",
    "protocol",
    "allowed_resource_types",
    "argument_schema",
    "output_schema",
    "allowed_destinations",
    "allowed_filesystem_paths",
    "network_required",
    "write_capability",
    "required_permissions",
    "required_credentials",
    "environment_allowlist",
    "timeout_seconds",
    "maximum_input_bytes",
    "maximum_output_bytes",
    "maximum_results",
    "retry_policy",
    "failure_policy",
    "evidence_policy",
    "redaction_policy",
    "audit_policy",
    "sandbox_policy",
    "provenance",
    "implementation_sha256",
    "adapter_entry_hash",
    "enabled",
}
_ADAPTER_TYPES: Final = frozenset(
    {
        "provider",
        "mcp",
        "browser",
        "filesystem",
        "git",
        "package",
        "test",
        "fixed-process",
        "coding-assistant",
        "internal",
    }
)
_PROTOCOLS: Final = frozenset(
    {
        "none",
        "https",
        "mcp-https",
        "mcp-stdio",
        "filesystem",
        "git-local",
        "git-https",
        "fixed-process",
    }
)
_NETWORK_PROTOCOLS: Final = frozenset({"https", "mcp-https", "git-https"})
_PROCESS_PROTOCOLS: Final = frozenset({"mcp-stdio", "fixed-process"})
_RESOURCE_TYPES: Final = frozenset(
    {
        "artifact",
        "browser-session",
        "directory",
        "file",
        "git-repository",
        "mcp-server",
        "network-destination",
        "package",
        "provider-request",
        "test-suite",
    }
)
_PERMISSIONS: Final = frozenset(
    {
        "browser.navigate",
        "filesystem.read",
        "filesystem.write",
        "git.read",
        "git.write",
        "mcp.call",
        "network.connect",
        "package.install",
        "provider.invoke",
        "subprocess.fixed",
        "test.run",
    }
)
_SAFE_ENVIRONMENT: Final = frozenset({"LANG", "LC_ALL", "LC_CTYPE", "TZ"})
_CREDENTIAL_TYPES: Final = frozenset(
    {
        "api-key",
        "oauth2-token",
        "session-token",
        "username-password",
        "client-certificate",
        "ssh-key",
    }
)
_FILESYSTEM_ROOTS: Final = frozenset({"repository", "workspace", "temporary"})
_FILESYSTEM_ACCESS: Final = frozenset(
    {"read-file", "read-directory", "write-file", "create-file"}
)
_WRITE_FILESYSTEM_ACCESS: Final = frozenset({"write-file", "create-file"})
_ALLOWED_PROTOCOLS_BY_TYPE: Final = {
    "provider": frozenset({"https"}),
    "mcp": frozenset({"mcp-https", "mcp-stdio"}),
    "browser": frozenset({"https"}),
    "filesystem": frozenset({"filesystem"}),
    "git": frozenset({"git-local", "git-https"}),
    "package": frozenset({"fixed-process"}),
    "test": frozenset({"fixed-process"}),
    "fixed-process": frozenset({"fixed-process"}),
    "coding-assistant": frozenset({"none", "https"}),
    "internal": frozenset({"none"}),
}
_REQUIRED_PERMISSION_BY_TYPE: Final = {
    "provider": "provider.invoke",
    "mcp": "mcp.call",
    "browser": "browser.navigate",
    "git": "git.read",
    "package": "package.install",
    "test": "test.run",
    "fixed-process": "subprocess.fixed",
}
_RESERVED_ARGUMENT_NAMES: Final = frozenset(
    {
        "command",
        "argv",
        "executable",
        "shell",
        "module",
        "import",
        "callable",
        "url",
        "uri",
        "endpoint",
        "host",
        "scheme",
        "port",
        "environment",
    }
)


class AdapterManifestFailureCode(str, Enum):
    ADAPTER_MANIFEST_MISSING = "ADAPTER_MANIFEST_MISSING"
    ADAPTER_MANIFEST_INVALID = "ADAPTER_MANIFEST_INVALID"
    ADAPTER_MANIFEST_HASH_MISMATCH = "ADAPTER_MANIFEST_HASH_MISMATCH"
    ADAPTER_MANIFEST_SCHEMA_UNSUPPORTED = "ADAPTER_MANIFEST_SCHEMA_UNSUPPORTED"
    ADAPTER_MANIFEST_VERSION_UNSUPPORTED = "ADAPTER_MANIFEST_VERSION_UNSUPPORTED"
    ADAPTER_MANIFEST_TOO_LARGE = "ADAPTER_MANIFEST_TOO_LARGE"
    ADAPTER_ENTRY_DUPLICATE = "ADAPTER_ENTRY_DUPLICATE"
    ADAPTER_ENTRY_INVALID = "ADAPTER_ENTRY_INVALID"
    ADAPTER_ENTRY_HASH_MISMATCH = "ADAPTER_ENTRY_HASH_MISMATCH"
    ADAPTER_INITIAL_STATE_VIOLATION = "ADAPTER_INITIAL_STATE_VIOLATION"
    ADAPTER_PERMISSION_POLICY_INVALID = "ADAPTER_PERMISSION_POLICY_INVALID"
    ADAPTER_LIMIT_POLICY_INVALID = "ADAPTER_LIMIT_POLICY_INVALID"
    ADAPTER_RETRY_POLICY_INVALID = "ADAPTER_RETRY_POLICY_INVALID"
    ADAPTER_FAILURE_POLICY_INVALID = "ADAPTER_FAILURE_POLICY_INVALID"
    ADAPTER_UNKNOWN = "ADAPTER_UNKNOWN"
    ADAPTER_VERSION_UNKNOWN = "ADAPTER_VERSION_UNKNOWN"
    ADAPTER_DISABLED = "ADAPTER_DISABLED"
    ADAPTER_IMPLEMENTATION_UNKNOWN = "ADAPTER_IMPLEMENTATION_UNKNOWN"
    ADAPTER_IMPLEMENTATION_UNMANIFESTED = "ADAPTER_IMPLEMENTATION_UNMANIFESTED"
    ADAPTER_IMPLEMENTATION_HASH_MISMATCH = "ADAPTER_IMPLEMENTATION_HASH_MISMATCH"
    ADAPTER_ARGUMENT_SCHEMA_INVALID = "ADAPTER_ARGUMENT_SCHEMA_INVALID"
    ADAPTER_OUTPUT_SCHEMA_INVALID = "ADAPTER_OUTPUT_SCHEMA_INVALID"
    ADAPTER_DESTINATION_POLICY_INVALID = "ADAPTER_DESTINATION_POLICY_INVALID"
    ADAPTER_FILESYSTEM_POLICY_INVALID = "ADAPTER_FILESYSTEM_POLICY_INVALID"
    ADAPTER_ENVIRONMENT_POLICY_INVALID = "ADAPTER_ENVIRONMENT_POLICY_INVALID"
    ADAPTER_CREDENTIAL_POLICY_INVALID = "ADAPTER_CREDENTIAL_POLICY_INVALID"
    ADAPTER_SECRET_MATERIAL_FORBIDDEN = "ADAPTER_SECRET_MATERIAL_FORBIDDEN"
    ADAPTER_EVIDENCE_POLICY_INVALID = "ADAPTER_EVIDENCE_POLICY_INVALID"
    ADAPTER_REDACTION_POLICY_INVALID = "ADAPTER_REDACTION_POLICY_INVALID"
    ADAPTER_AUDIT_POLICY_INVALID = "ADAPTER_AUDIT_POLICY_INVALID"
    ADAPTER_SANDBOX_POLICY_INVALID = "ADAPTER_SANDBOX_POLICY_INVALID"
    ADAPTER_ARBITRARY_COMMAND_FORBIDDEN = "ADAPTER_ARBITRARY_COMMAND_FORBIDDEN"
    ADAPTER_ARBITRARY_EXECUTABLE_FORBIDDEN = "ADAPTER_ARBITRARY_EXECUTABLE_FORBIDDEN"
    ADAPTER_ARBITRARY_URL_FORBIDDEN = "ADAPTER_ARBITRARY_URL_FORBIDDEN"
    ADAPTER_DYNAMIC_IMPORT_FORBIDDEN = "ADAPTER_DYNAMIC_IMPORT_FORBIDDEN"
    ADAPTER_DYNAMIC_CALLABLE_FORBIDDEN = "ADAPTER_DYNAMIC_CALLABLE_FORBIDDEN"
    ADAPTER_SHELL_MODE_FORBIDDEN = "ADAPTER_SHELL_MODE_FORBIDDEN"


class AdapterManifestError(ValueError):
    """A fail-closed manifest denial with a stable machine-readable code."""

    def __init__(self, code: AdapterManifestFailureCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {message}")


@dataclass(frozen=True, slots=True)
class ManifestIdentity:
    schema_version: int
    manifest_version: str
    manifest_hash: str


@dataclass(frozen=True, slots=True)
class AdapterEntry:
    adapter_id: str
    adapter_version: str
    adapter_type: str
    implementation_reference: str
    operation: str
    protocol: str
    allowed_resource_types: tuple[str, ...]
    argument_schema: FrozenDict
    output_schema: FrozenDict
    allowed_destinations: tuple[FrozenDict, ...]
    allowed_filesystem_paths: tuple[FrozenDict, ...]
    network_required: bool
    write_capability: bool
    required_permissions: tuple[str, ...]
    required_credentials: tuple[FrozenDict, ...]
    environment_allowlist: tuple[str, ...]
    timeout_seconds: int
    maximum_input_bytes: int
    maximum_output_bytes: int
    maximum_results: int
    retry_policy: FrozenDict
    failure_policy: FrozenDict
    evidence_policy: FrozenDict
    redaction_policy: FrozenDict
    audit_policy: FrozenDict
    sandbox_policy: FrozenDict
    provenance: FrozenDict
    implementation_sha256: str
    adapter_entry_hash: str
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "adapter_type": self.adapter_type,
            "implementation_reference": self.implementation_reference,
            "operation": self.operation,
            "protocol": self.protocol,
            "allowed_resource_types": list(self.allowed_resource_types),
            "argument_schema": thaw_json(self.argument_schema),
            "output_schema": thaw_json(self.output_schema),
            "allowed_destinations": [thaw_json(item) for item in self.allowed_destinations],
            "allowed_filesystem_paths": [
                thaw_json(item) for item in self.allowed_filesystem_paths
            ],
            "network_required": self.network_required,
            "write_capability": self.write_capability,
            "required_permissions": list(self.required_permissions),
            "required_credentials": [
                thaw_json(item) for item in self.required_credentials
            ],
            "environment_allowlist": list(self.environment_allowlist),
            "timeout_seconds": self.timeout_seconds,
            "maximum_input_bytes": self.maximum_input_bytes,
            "maximum_output_bytes": self.maximum_output_bytes,
            "maximum_results": self.maximum_results,
            "retry_policy": thaw_json(self.retry_policy),
            "failure_policy": thaw_json(self.failure_policy),
            "evidence_policy": thaw_json(self.evidence_policy),
            "redaction_policy": thaw_json(self.redaction_policy),
            "audit_policy": thaw_json(self.audit_policy),
            "sandbox_policy": thaw_json(self.sandbox_policy),
            "provenance": thaw_json(self.provenance),
            "implementation_sha256": self.implementation_sha256,
            "adapter_entry_hash": self.adapter_entry_hash,
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class AdapterManifest:
    schema_version: int
    manifest_version: str
    adapters: tuple[AdapterEntry, ...]
    manifest_hash: str

    @property
    def identity(self) -> ManifestIdentity:
        return ManifestIdentity(
            schema_version=self.schema_version,
            manifest_version=self.manifest_version,
            manifest_hash=self.manifest_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_version": self.manifest_version,
            "adapters": [entry.to_dict() for entry in self.adapters],
            "manifest_hash": self.manifest_hash,
        }


@dataclass(frozen=True, slots=True)
class _ImplementationIdentity:
    implementation_reference: str
    implementation_sha256: str


_REGISTERED_IMPLEMENTATION_IDENTITIES: Final[Mapping[
    tuple[str, str], _ImplementationIdentity
]] = MappingProxyType({})


def _deny(code: AdapterManifestFailureCode, message: str) -> None:
    raise AdapterManifestError(code, message)


def _exact_object(
    name: str,
    value: object,
    expected: set[str],
    code: AdapterManifestFailureCode,
) -> dict[str, Any]:
    if type(value) is not dict:
        _deny(code, f"{name} must be a plain JSON object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected, key=repr)
        _deny(code, f"{name} fields differ; missing={missing!r}; unknown={unknown!r}")
    return dict(value)


def _required_string(
    name: str,
    value: object,
    code: AdapterManifestFailureCode,
    *,
    maximum_bytes: int = _MAX_IDENTIFIER_BYTES,
) -> str:
    if type(value) is not str or not value:
        _deny(code, f"{name} must be a nonempty string")
    if value != value.strip() or any(ord(character) < 32 or ord(character) == 127 for character in value):
        _deny(code, f"{name} is not canonical text")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        _deny(code, f"{name} is not valid UTF-8")
    if len(encoded) > maximum_bytes:
        _deny(code, f"{name} is too large")
    return value


def _identifier(
    name: str,
    value: object,
    code: AdapterManifestFailureCode,
) -> str:
    text = _required_string(name, value, code)
    if not _IDENTIFIER.fullmatch(text):
        _deny(code, f"{name} is not a lowercase logical identifier")
    return text


def _version(name: str, value: object, code: AdapterManifestFailureCode) -> str:
    text = _required_string(name, value, code)
    if not _VERSION.fullmatch(text):
        _deny(code, f"{name} is not a canonical positive decimal version")
    return text


def _exact_integer(
    name: str,
    value: object,
    code: AdapterManifestFailureCode,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _deny(code, f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def _exact_boolean(
    name: str,
    value: object,
    code: AdapterManifestFailureCode,
) -> bool:
    if type(value) is not bool:
        _deny(code, f"{name} must be an exact boolean")
    return value


def _sha256(
    name: str,
    value: object,
    code: AdapterManifestFailureCode,
) -> str:
    try:
        return require_sha256(value, field_name=name)
    except CanonicalSerializationError as exc:
        _deny(code, str(exc))


def _sorted_unique_enum(
    name: str,
    value: object,
    allowed: frozenset[str],
    code: AdapterManifestFailureCode,
) -> tuple[str, ...]:
    if type(value) is not list:
        _deny(code, f"{name} must be a JSON array")
    if any(type(item) is not str or item not in allowed for item in value):
        _deny(code, f"{name} contains an unsupported value")
    if value != sorted(set(value)):
        _deny(code, f"{name} must be sorted and unique")
    return tuple(value)


def _reserved_argument_code(
    value: str,
) -> AdapterManifestFailureCode | None:
    normalized = re.sub(r"[^a-z0-9]", "", value.casefold())
    if normalized == "command":
        return AdapterManifestFailureCode.ADAPTER_ARBITRARY_COMMAND_FORBIDDEN
    if normalized in {"argv", "executable"}:
        return AdapterManifestFailureCode.ADAPTER_ARBITRARY_EXECUTABLE_FORBIDDEN
    if normalized in {"url", "uri", "endpoint", "host", "scheme", "port"}:
        return AdapterManifestFailureCode.ADAPTER_ARBITRARY_URL_FORBIDDEN
    if normalized in {"module", "import"}:
        return AdapterManifestFailureCode.ADAPTER_DYNAMIC_IMPORT_FORBIDDEN
    if normalized == "callable":
        return AdapterManifestFailureCode.ADAPTER_DYNAMIC_CALLABLE_FORBIDDEN
    if normalized == "shell":
        return AdapterManifestFailureCode.ADAPTER_SHELL_MODE_FORBIDDEN
    if normalized == "environment":
        return AdapterManifestFailureCode.ADAPTER_ENVIRONMENT_POLICY_INVALID
    return None


def _canonical_allowed_values(
    name: str,
    value: object,
    expected_type: type,
    code: AdapterManifestFailureCode,
) -> tuple[object, ...]:
    if type(value) is not list:
        _deny(code, f"{name} must be a JSON array")
    if len(value) > _MAX_SCHEMA_ITEMS:
        _deny(code, f"{name} exceeds the bounded schema item count")
    if any(type(item) is not expected_type for item in value):
        _deny(code, f"{name} contains a value of the wrong exact type")
    try:
        rendered = [canonical_json_bytes(item) for item in value]
    except CanonicalSerializationError as exc:
        _deny(code, f"{name} contains a non-canonical value: {exc}")
    if len(set(rendered)) != len(rendered) or rendered != sorted(rendered):
        _deny(code, f"{name} must be canonically sorted and unique")
    return tuple(value)


def _validate_schema_node(
    value: object,
    *,
    name: str,
    code: AdapterManifestFailureCode,
    depth: int,
    count: list[int],
    reject_reserved_names: bool,
) -> FrozenDict:
    if depth > _MAX_SCHEMA_DEPTH:
        _deny(code, f"{name} exceeds the maximum schema depth")
    count[0] += 1
    if count[0] > _MAX_SCHEMA_NODES:
        _deny(code, f"{name} exceeds the maximum schema node count")
    if type(value) is not dict or type(value.get("type")) is not str:
        _deny(code, f"{name} must be a typed schema object")
    node_type = value["type"]
    if node_type == "string":
        expected = {
            "type",
            "semantic_type",
            "minimum_bytes",
            "maximum_bytes",
            "allowed_values",
        }
        node = _exact_object(name, value, expected, code)
        _identifier(f"{name}.semantic_type", node["semantic_type"], code)
        minimum = _exact_integer(
            f"{name}.minimum_bytes",
            node["minimum_bytes"],
            code,
            minimum=0,
            maximum=_MAX_SCHEMA_STRING_BYTES,
        )
        maximum = _exact_integer(
            f"{name}.maximum_bytes",
            node["maximum_bytes"],
            code,
            minimum=0,
            maximum=_MAX_SCHEMA_STRING_BYTES,
        )
        if minimum > maximum:
            _deny(code, f"{name} string bounds are inconsistent")
        allowed = _canonical_allowed_values(
            f"{name}.allowed_values", node["allowed_values"], str, code
        )
        if any(not minimum <= len(item.encode("utf-8")) <= maximum for item in allowed):
            _deny(code, f"{name}.allowed_values violates the string bounds")
    elif node_type == "integer":
        expected = {"type", "minimum", "maximum", "allowed_values"}
        node = _exact_object(name, value, expected, code)
        minimum = _exact_integer(
            f"{name}.minimum", node["minimum"], code, minimum=-(2**63), maximum=2**63 - 1
        )
        maximum = _exact_integer(
            f"{name}.maximum", node["maximum"], code, minimum=-(2**63), maximum=2**63 - 1
        )
        if minimum > maximum:
            _deny(code, f"{name} integer bounds are inconsistent")
        allowed = _canonical_allowed_values(
            f"{name}.allowed_values", node["allowed_values"], int, code
        )
        if any(not minimum <= item <= maximum for item in allowed):
            _deny(code, f"{name}.allowed_values violates the integer bounds")
    elif node_type == "boolean":
        node = _exact_object(name, value, {"type"}, code)
    elif node_type == "null":
        node = _exact_object(name, value, {"type"}, code)
    elif node_type == "array":
        expected = {
            "type",
            "items",
            "minimum_items",
            "maximum_items",
            "unique_items",
        }
        node = _exact_object(name, value, expected, code)
        minimum = _exact_integer(
            f"{name}.minimum_items",
            node["minimum_items"],
            code,
            minimum=0,
            maximum=_MAX_SCHEMA_ITEMS,
        )
        maximum = _exact_integer(
            f"{name}.maximum_items",
            node["maximum_items"],
            code,
            minimum=0,
            maximum=_MAX_SCHEMA_ITEMS,
        )
        if minimum > maximum:
            _deny(code, f"{name} array bounds are inconsistent")
        _exact_boolean(f"{name}.unique_items", node["unique_items"], code)
        node["items"] = thaw_json(
            _validate_schema_node(
                node["items"],
                name=f"{name}.items",
                code=code,
                depth=depth + 1,
                count=count,
                reject_reserved_names=reject_reserved_names,
            )
        )
    elif node_type == "object":
        expected = {
            "type",
            "properties",
            "required",
            "additional_properties",
            "maximum_properties",
        }
        node = _exact_object(name, value, expected, code)
        if type(node["properties"]) is not dict:
            _deny(code, f"{name}.properties must be a JSON object")
        properties = node["properties"]
        if len(properties) > _MAX_SCHEMA_PROPERTIES:
            _deny(code, f"{name}.properties is too large")
        checked_properties: dict[str, Any] = {}
        for property_name, property_schema in properties.items():
            _identifier(f"{name}.properties key", property_name, code)
            reserved_code = _reserved_argument_code(property_name)
            if reject_reserved_names and reserved_code is not None:
                _deny(
                    reserved_code,
                    f"{name} contains a reserved authority-bearing argument name",
                )
            checked_properties[property_name] = thaw_json(
                _validate_schema_node(
                    property_schema,
                    name=f"{name}.properties.{property_name}",
                    code=code,
                    depth=depth + 1,
                    count=count,
                    reject_reserved_names=reject_reserved_names,
                )
            )
        required = node["required"]
        if (
            type(required) is not list
            or any(type(item) is not str for item in required)
            or required != sorted(set(required))
            or not set(required) <= set(properties)
        ):
            _deny(code, f"{name}.required must be sorted, unique, and name properties")
        if node["additional_properties"] is not False:
            _deny(code, f"{name}.additional_properties must be false")
        maximum = _exact_integer(
            f"{name}.maximum_properties",
            node["maximum_properties"],
            code,
            minimum=0,
            maximum=_MAX_SCHEMA_PROPERTIES,
        )
        if maximum < len(properties):
            _deny(code, f"{name}.maximum_properties is smaller than properties")
        node["properties"] = checked_properties
    else:
        _deny(code, f"{name}.type is unsupported")
    try:
        frozen = freeze_json(node)
    except CanonicalSerializationError as exc:
        _deny(code, f"{name} is not canonical JSON: {exc}")
    if type(frozen) is not FrozenDict:
        _deny(code, f"{name} must be a schema object")
    return frozen


def _validate_data_schema(
    value: object,
    *,
    name: str,
    code: AdapterManifestFailureCode,
    reject_reserved_names: bool,
) -> FrozenDict:
    schema = _exact_object(name, value, {"schema_version", "root"}, code)
    if schema["schema_version"] != AOIA_DATA_SCHEMA_V1:
        _deny(code, f"{name}.schema_version is unsupported")
    if type(schema["root"]) is not dict or schema["root"].get("type") != "object":
        _deny(code, f"{name}.root must be a bounded object schema")
    root = _validate_schema_node(
        schema["root"],
        name=f"{name}.root",
        code=code,
        depth=1,
        count=[0],
        reject_reserved_names=reject_reserved_names,
    )
    schema["root"] = thaw_json(root)
    frozen = freeze_json(schema)
    if type(frozen) is not FrozenDict:
        _deny(code, f"{name} must be a schema object")
    return frozen


def _validate_destination(value: object) -> FrozenDict:
    code = AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID
    destination = _exact_object(
        "allowed destination", value, {"scheme", "host", "port"}, code
    )
    if destination["scheme"] != "https":
        _deny(code, "destination scheme must be exactly https")
    host = _required_string(
        "destination host", destination["host"], code, maximum_bytes=253
    )
    if host != host.lower() or host.endswith(".") or "*" in host:
        _deny(code, "destination host is not a canonical exact identity")
    if any(character in host for character in ("/", "?", "#", "@", "%")):
        _deny(code, "destination host contains URL components")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            host.encode("ascii", errors="strict")
        except UnicodeError:
            _deny(code, "destination DNS identity must be lowercase ASCII")
        labels = host.split(".")
        if len(labels) < 2 or any(not _DNS_LABEL.fullmatch(label) for label in labels):
            _deny(code, "destination DNS identity is malformed")
    else:
        if str(address) != host or not address.is_global:
            _deny(code, "destination IP must be canonical and globally routable")
    _exact_integer(
        "destination port", destination["port"], code, minimum=1, maximum=65_535
    )
    return freeze_json(destination)


def _validate_destinations(value: object) -> tuple[FrozenDict, ...]:
    code = AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID
    if type(value) is not list:
        _deny(code, "allowed_destinations must be a JSON array")
    if len(value) > _MAX_POLICY_ITEMS:
        _deny(code, "allowed_destinations exceeds the bounded policy item count")
    checked = tuple(_validate_destination(item) for item in value)
    keys = tuple((item["scheme"], item["host"], item["port"]) for item in checked)
    if len(set(keys)) != len(keys):
        _deny(code, "allowed_destinations contains duplicates")
    if keys != tuple(sorted(keys)):
        _deny(code, "allowed_destinations must use canonical order")
    return checked


def _validate_relative_path(value: object) -> str:
    code = AdapterManifestFailureCode.ADAPTER_FILESYSTEM_POLICY_INVALID
    path = _required_string(
        "filesystem relative_path", value, code, maximum_bytes=4_096
    )
    if (
        path.startswith(("/", "~"))
        or "\\" in path
        or "//" in path
        or path.endswith("/")
        or any(character in path for character in "*?[]")
    ):
        _deny(code, "filesystem relative_path is not a bounded logical path")
    components = path.split("/")
    if any(component in ("", ".", "..") for component in components):
        _deny(code, "filesystem relative_path contains unsafe components")
    if components[0].endswith(":"):
        _deny(code, "filesystem relative_path resembles an absolute drive path")
    return path


def _validate_filesystem_paths(value: object) -> tuple[FrozenDict, ...]:
    code = AdapterManifestFailureCode.ADAPTER_FILESYSTEM_POLICY_INVALID
    if type(value) is not list:
        _deny(code, "allowed_filesystem_paths must be a JSON array")
    if len(value) > _MAX_POLICY_ITEMS:
        _deny(code, "allowed_filesystem_paths exceeds the bounded policy item count")
    checked: list[FrozenDict] = []
    for item in value:
        rule = _exact_object(
            "filesystem rule",
            item,
            {"root_id", "relative_path", "access", "symlink_policy"},
            code,
        )
        if rule["root_id"] not in _FILESYSTEM_ROOTS:
            _deny(code, "filesystem root_id is unsupported")
        rule["relative_path"] = _validate_relative_path(rule["relative_path"])
        if rule["access"] not in _FILESYSTEM_ACCESS:
            _deny(code, "filesystem access is unsupported")
        if rule["symlink_policy"] != "forbid":
            _deny(code, "filesystem symlink policy must be forbid")
        checked.append(freeze_json(rule))
    keys = tuple(
        (item["root_id"], item["relative_path"], item["access"], item["symlink_policy"])
        for item in checked
    )
    if len(set(keys)) != len(keys):
        _deny(code, "allowed_filesystem_paths contains duplicates")
    if keys != tuple(sorted(keys)):
        _deny(code, "allowed_filesystem_paths must use canonical order")
    return tuple(checked)


_SECRET_PATTERNS: Final = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]{8,}"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:sk-(?:proj-)?|gh[pousr]_|github_pat_)[a-z0-9_-]{8,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
)


def _text_contains_secret_material(value: str) -> bool:
    lowered = value.casefold()
    if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
        return True
    if any(token in lowered for token in ("os.environ", "getenv(", "$(", "$" + "{")):
        return True
    return value.startswith(("/", "~")) or lowered.startswith(("file:", "env:"))


def _contains_secret_material(value: object) -> bool:
    if type(value) is str:
        return _text_contains_secret_material(value)
    if type(value) is list:
        return any(_contains_secret_material(item) for item in value)
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is str:
                normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
                if normalized in {
                    "apikey",
                    "bearer",
                    "cookie",
                    "password",
                    "privatekey",
                    "secret",
                    "secretvalue",
                    "token",
                    "value",
                }:
                    return True
            if _contains_secret_material(key) or _contains_secret_material(item):
                return True
        return False
    return False


def _validate_credentials(value: object) -> tuple[FrozenDict, ...]:
    secret_code = AdapterManifestFailureCode.ADAPTER_SECRET_MATERIAL_FORBIDDEN
    code = AdapterManifestFailureCode.ADAPTER_CREDENTIAL_POLICY_INVALID
    if type(value) is not list:
        _deny(code, "required_credentials must be a JSON array")
    if len(value) > _MAX_POLICY_ITEMS:
        _deny(code, "required_credentials exceeds the bounded policy item count")
    if _contains_secret_material(value):
        _deny(secret_code, "credential metadata contains secret-like material")
    checked: list[FrozenDict] = []
    for item in value:
        credential = _exact_object(
            "credential metadata",
            item,
            {"credential_type", "credential_reference"},
            code,
        )
        if credential["credential_type"] not in _CREDENTIAL_TYPES:
            _deny(code, "credential_type is unsupported")
        reference = credential["credential_reference"]
        if type(reference) is not str or not _CREDENTIAL_REFERENCE.fullmatch(reference):
            _deny(code, "credential_reference is not an opaque logical reference")
        checked.append(freeze_json(credential))
    keys = tuple(
        (item["credential_type"], item["credential_reference"]) for item in checked
    )
    if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
        _deny(code, "required_credentials must be canonically sorted and unique")
    return tuple(checked)


def _validate_environment(value: object) -> tuple[str, ...]:
    code = AdapterManifestFailureCode.ADAPTER_ENVIRONMENT_POLICY_INVALID
    if type(value) is not list or any(type(item) is not str for item in value):
        _deny(code, "environment_allowlist must be a JSON string array")
    if value != sorted(set(value)):
        _deny(code, "environment_allowlist must be sorted and unique")
    if any(item not in _SAFE_ENVIRONMENT for item in value):
        _deny(code, "environment_allowlist contains an unsafe or inherited name")
    return tuple(value)


def _validate_retry_policy(value: object) -> FrozenDict:
    code = AdapterManifestFailureCode.ADAPTER_RETRY_POLICY_INVALID
    policy = _exact_object(
        "retry_policy", value, {"mode", "maximum_attempts", "backoff_seconds"}, code
    )
    if policy != {"mode": "none", "maximum_attempts": 1, "backoff_seconds": 0}:
        _deny(code, "retry_policy must be the inert no-retry policy")
    return freeze_json(policy)


def _validate_failure_policy(value: object) -> FrozenDict:
    code = AdapterManifestFailureCode.ADAPTER_FAILURE_POLICY_INVALID
    policy = _exact_object(
        "failure_policy",
        value,
        {"mode", "on_timeout", "on_error", "allow_partial_results"},
        code,
    )
    expected = {
        "mode": "fail-closed",
        "on_timeout": "deny",
        "on_error": "deny",
        "allow_partial_results": False,
    }
    if policy != expected:
        _deny(code, "failure_policy must deny timeout, errors, and partial results")
    return freeze_json(policy)


def _validate_policy_reference(
    name: str,
    value: object,
    code: AdapterManifestFailureCode,
    *,
    sandbox: bool = False,
) -> FrozenDict:
    expected = {"policy_id", "policy_version", "policy_hash"}
    if sandbox:
        expected.add("required")
    policy = _exact_object(name, value, expected, code)
    _identifier(f"{name}.policy_id", policy["policy_id"], code)
    _version(f"{name}.policy_version", policy["policy_version"], code)
    _sha256(f"{name}.policy_hash", policy["policy_hash"], code)
    if sandbox and policy["required"] is not True:
        _deny(code, f"{name}.required must be true")
    return freeze_json(policy)


def _validate_provenance(value: object) -> FrozenDict:
    code = AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID
    provenance = _exact_object(
        "provenance", value, {"repository_id", "source_commit"}, code
    )
    if provenance["repository_id"] != "luciferprosun/AOIA-Core":
        _deny(code, "provenance.repository_id differs")
    if type(provenance["source_commit"]) is not str or not _SOURCE_COMMIT.fullmatch(
        provenance["source_commit"]
    ):
        _deny(code, "provenance.source_commit must be a full lowercase Git identity")
    return freeze_json(provenance)


def _dangerous_field_code(field: object) -> AdapterManifestFailureCode | None:
    if type(field) is not str:
        return AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID
    normalized = field.casefold().replace("-", "_")
    if normalized in {"command", "shell_command"}:
        return AdapterManifestFailureCode.ADAPTER_ARBITRARY_COMMAND_FORBIDDEN
    if normalized in {"argv", "argv0", "executable", "binary"}:
        return AdapterManifestFailureCode.ADAPTER_ARBITRARY_EXECUTABLE_FORBIDDEN
    if normalized in {"url", "uri", "endpoint"}:
        return AdapterManifestFailureCode.ADAPTER_ARBITRARY_URL_FORBIDDEN
    if normalized in {
        "module",
        "module_path",
        "import",
        "import_path",
        "class",
        "function",
    }:
        return AdapterManifestFailureCode.ADAPTER_DYNAMIC_IMPORT_FORBIDDEN
    if normalized in {"callable", "callback", "handler"}:
        return AdapterManifestFailureCode.ADAPTER_DYNAMIC_CALLABLE_FORBIDDEN
    if normalized in {"shell", "shell_true"}:
        return AdapterManifestFailureCode.ADAPTER_SHELL_MODE_FORBIDDEN
    return None


def _validate_entry_cross_fields(entry: AdapterEntry) -> None:
    if entry.protocol not in _ALLOWED_PROTOCOLS_BY_TYPE[entry.adapter_type]:
        _deny(
            AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
            "adapter_type and protocol are inconsistent",
        )
    required_permission = _REQUIRED_PERMISSION_BY_TYPE.get(entry.adapter_type)
    if required_permission is not None and required_permission not in entry.required_permissions:
        _deny(
            AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
            "adapter_type is missing its closed-set permission",
        )
    network_protocol = entry.protocol in _NETWORK_PROTOCOLS
    if network_protocol != entry.network_required:
        _deny(
            AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
            "protocol and network_required differ",
        )
    if entry.network_required:
        if (
            not entry.allowed_destinations
            or "network.connect" not in entry.required_permissions
        ):
            _deny(
                AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
                "network adapters require exact destinations and network.connect",
            )
    elif entry.allowed_destinations or "network.connect" in entry.required_permissions:
        _deny(
            AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
            "non-network adapters cannot claim destinations or network.connect",
        )
    if entry.protocol in _PROCESS_PROTOCOLS:
        if "subprocess.fixed" not in entry.required_permissions:
            _deny(
                AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
                "fixed process protocols require subprocess.fixed",
            )
    elif "subprocess.fixed" in entry.required_permissions:
        _deny(
            AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
            "subprocess.fixed is limited to fixed process protocols",
        )
    for rule in entry.allowed_filesystem_paths:
        if rule["access"] in _WRITE_FILESYSTEM_ACCESS:
            if (
                not entry.write_capability
                or "filesystem.write" not in entry.required_permissions
            ):
                _deny(
                    AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
                    "filesystem write rules require explicit write metadata",
                )
        elif "filesystem.read" not in entry.required_permissions:
            _deny(
                AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
                "filesystem read rules require filesystem.read",
            )


def _entry_hash_material(entry: AdapterEntry) -> dict[str, Any]:
    material = entry.to_dict()
    material.pop("adapter_entry_hash")
    return material


def _compute_entry_hash(entry: AdapterEntry) -> str:
    return domain_separated_sha256(
        AOIA_ADAPTER_MANIFEST_ENTRY_V1, _entry_hash_material(entry)
    )


def verify_adapter_entry(value: object) -> AdapterEntry:
    if type(value) is AdapterEntry:
        value = value.to_dict()
    if type(value) is dict:
        for field in value:
            if field not in _ENTRY_FIELDS:
                dangerous = _dangerous_field_code(field)
                if dangerous is not None:
                    _deny(dangerous, f"forbidden adapter field: {field!r}")
    code = AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID
    payload = _exact_object("adapter entry", value, _ENTRY_FIELDS, code)
    adapter_id = _identifier("adapter_id", payload["adapter_id"], code)
    adapter_version = _version("adapter_version", payload["adapter_version"], code)
    adapter_type = payload["adapter_type"]
    if type(adapter_type) is not str or adapter_type not in _ADAPTER_TYPES:
        _deny(code, "adapter_type is unsupported")
    implementation_reference = payload["implementation_reference"]
    expected_reference = f"aoia_adapter:{adapter_id}:{adapter_version}"
    if implementation_reference != expected_reference:
        if type(implementation_reference) is str and (
            implementation_reference.startswith(("http://", "https://"))
            or "://" in implementation_reference
        ):
            _deny(
                AdapterManifestFailureCode.ADAPTER_ARBITRARY_URL_FORBIDDEN,
                "implementation_reference cannot be a URL",
            )
        _deny(
            AdapterManifestFailureCode.ADAPTER_DYNAMIC_IMPORT_FORBIDDEN,
            "implementation_reference must be the derived logical identity",
        )
    operation = _identifier("operation", payload["operation"], code)
    protocol = payload["protocol"]
    if type(protocol) is not str or protocol not in _PROTOCOLS:
        _deny(code, "protocol is unsupported")
    allowed_resource_types = _sorted_unique_enum(
        "allowed_resource_types",
        payload["allowed_resource_types"],
        _RESOURCE_TYPES,
        code,
    )
    argument_schema = _validate_data_schema(
        payload["argument_schema"],
        name="argument_schema",
        code=AdapterManifestFailureCode.ADAPTER_ARGUMENT_SCHEMA_INVALID,
        reject_reserved_names=True,
    )
    output_schema = _validate_data_schema(
        payload["output_schema"],
        name="output_schema",
        code=AdapterManifestFailureCode.ADAPTER_OUTPUT_SCHEMA_INVALID,
        reject_reserved_names=False,
    )
    allowed_destinations = _validate_destinations(payload["allowed_destinations"])
    allowed_filesystem_paths = _validate_filesystem_paths(
        payload["allowed_filesystem_paths"]
    )
    network_required = _exact_boolean("network_required", payload["network_required"], code)
    write_capability = _exact_boolean("write_capability", payload["write_capability"], code)
    required_permissions = _sorted_unique_enum(
        "required_permissions",
        payload["required_permissions"],
        _PERMISSIONS,
        AdapterManifestFailureCode.ADAPTER_PERMISSION_POLICY_INVALID,
    )
    required_credentials = _validate_credentials(payload["required_credentials"])
    environment_allowlist = _validate_environment(payload["environment_allowlist"])
    timeout_seconds = _exact_integer(
        "timeout_seconds",
        payload["timeout_seconds"],
        AdapterManifestFailureCode.ADAPTER_LIMIT_POLICY_INVALID,
        minimum=1,
        maximum=3_600,
    )
    maximum_input_bytes = _exact_integer(
        "maximum_input_bytes",
        payload["maximum_input_bytes"],
        AdapterManifestFailureCode.ADAPTER_LIMIT_POLICY_INVALID,
        minimum=0,
        maximum=1_073_741_824,
    )
    maximum_output_bytes = _exact_integer(
        "maximum_output_bytes",
        payload["maximum_output_bytes"],
        AdapterManifestFailureCode.ADAPTER_LIMIT_POLICY_INVALID,
        minimum=0,
        maximum=1_073_741_824,
    )
    maximum_results = _exact_integer(
        "maximum_results",
        payload["maximum_results"],
        AdapterManifestFailureCode.ADAPTER_LIMIT_POLICY_INVALID,
        minimum=0,
        maximum=10_000,
    )
    retry_policy = _validate_retry_policy(payload["retry_policy"])
    failure_policy = _validate_failure_policy(payload["failure_policy"])
    evidence_policy = _validate_policy_reference(
        "evidence_policy",
        payload["evidence_policy"],
        AdapterManifestFailureCode.ADAPTER_EVIDENCE_POLICY_INVALID,
    )
    redaction_policy = _validate_policy_reference(
        "redaction_policy",
        payload["redaction_policy"],
        AdapterManifestFailureCode.ADAPTER_REDACTION_POLICY_INVALID,
    )
    audit_policy = _validate_policy_reference(
        "audit_policy",
        payload["audit_policy"],
        AdapterManifestFailureCode.ADAPTER_AUDIT_POLICY_INVALID,
    )
    sandbox_policy = _validate_policy_reference(
        "sandbox_policy",
        payload["sandbox_policy"],
        AdapterManifestFailureCode.ADAPTER_SANDBOX_POLICY_INVALID,
        sandbox=True,
    )
    provenance = _validate_provenance(payload["provenance"])
    implementation_sha256 = _sha256(
        "implementation_sha256", payload["implementation_sha256"], code
    )
    adapter_entry_hash = _sha256(
        "adapter_entry_hash", payload["adapter_entry_hash"], code
    )
    enabled = _exact_boolean("enabled", payload["enabled"], code)
    if enabled:
        _deny(
            AdapterManifestFailureCode.ADAPTER_INITIAL_STATE_VIOLATION,
            "R3.2 adapter entries must remain disabled",
        )
    entry = AdapterEntry(
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        adapter_type=adapter_type,
        implementation_reference=implementation_reference,
        operation=operation,
        protocol=protocol,
        allowed_resource_types=allowed_resource_types,
        argument_schema=argument_schema,
        output_schema=output_schema,
        allowed_destinations=allowed_destinations,
        allowed_filesystem_paths=allowed_filesystem_paths,
        network_required=network_required,
        write_capability=write_capability,
        required_permissions=required_permissions,
        required_credentials=required_credentials,
        environment_allowlist=environment_allowlist,
        timeout_seconds=timeout_seconds,
        maximum_input_bytes=maximum_input_bytes,
        maximum_output_bytes=maximum_output_bytes,
        maximum_results=maximum_results,
        retry_policy=retry_policy,
        failure_policy=failure_policy,
        evidence_policy=evidence_policy,
        redaction_policy=redaction_policy,
        audit_policy=audit_policy,
        sandbox_policy=sandbox_policy,
        provenance=provenance,
        implementation_sha256=implementation_sha256,
        adapter_entry_hash=adapter_entry_hash,
        enabled=enabled,
    )
    _validate_entry_cross_fields(entry)
    try:
        computed_entry_hash = _compute_entry_hash(entry)
    except CanonicalSerializationError as exc:
        _deny(code, f"adapter entry exceeds canonical bounds: {exc}")
    if not hashes_equal(entry.adapter_entry_hash, computed_entry_hash):
        _deny(
            AdapterManifestFailureCode.ADAPTER_ENTRY_HASH_MISMATCH,
            "adapter_entry_hash does not bind the entry semantics",
        )
    return entry


def _manifest_hash_material(
    schema_version: int,
    manifest_version: str,
    entries: tuple[AdapterEntry, ...],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "manifest_version": manifest_version,
        "adapters": [entry.to_dict() for entry in entries],
    }


def _compute_manifest_hash(
    schema_version: int,
    manifest_version: str,
    entries: tuple[AdapterEntry, ...],
) -> str:
    return domain_separated_sha256(
        AOIA_ADAPTER_MANIFEST_V1,
        _manifest_hash_material(schema_version, manifest_version, entries),
    )


def verify_manifest(value: object) -> AdapterManifest:
    if type(value) is AdapterManifest:
        value = value.to_dict()
    code = AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID
    payload = _exact_object("adapter manifest", value, _TOP_LEVEL_FIELDS, code)
    schema_version = payload["schema_version"]
    if type(schema_version) is not int or schema_version != 1:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_SCHEMA_UNSUPPORTED,
            "schema_version must be exact integer 1",
        )
    manifest_version = _version("manifest_version", payload["manifest_version"], code)
    if manifest_version != "1":
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_VERSION_UNSUPPORTED,
            "manifest_version is unsupported",
        )
    raw_entries = payload["adapters"]
    if type(raw_entries) is not list:
        _deny(code, "adapters must be a JSON array")
    if len(raw_entries) > _MAX_ADAPTERS:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_TOO_LARGE,
            "adapter count exceeds the R3.2 limit",
        )
    seen: set[tuple[str, str]] = set()
    for raw in raw_entries:
        if type(raw) is not dict:
            _deny(AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID, "adapter entry is not an object")
        raw_id = raw.get("adapter_id")
        raw_version = raw.get("adapter_version")
        if type(raw_id) is str and type(raw_version) is str:
            identity = (raw_id, raw_version)
            if identity in seen:
                _deny(
                    AdapterManifestFailureCode.ADAPTER_ENTRY_DUPLICATE,
                    "duplicate adapter_id and adapter_version",
                )
            seen.add(identity)
    entries = tuple(verify_adapter_entry(raw) for raw in raw_entries)
    entries = tuple(sorted(entries, key=lambda item: (item.adapter_id, item.adapter_version)))
    manifest_hash = _sha256("manifest_hash", payload["manifest_hash"], code)
    try:
        computed = _compute_manifest_hash(schema_version, manifest_version, entries)
    except CanonicalSerializationError as exc:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_TOO_LARGE,
            f"manifest exceeds canonical bounds: {exc}",
        )
    if not hashes_equal(manifest_hash, computed):
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_HASH_MISMATCH,
            "manifest_hash does not bind the canonical manifest",
        )
    return AdapterManifest(
        schema_version=schema_version,
        manifest_version=manifest_version,
        adapters=entries,
        manifest_hash=manifest_hash,
    )


class _DuplicateJsonKey(ValueError):
    pass


class _ForbiddenJsonNumber(ValueError):
    pass


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def _reject_json_number(_value: str) -> None:
    raise _ForbiddenJsonNumber


def _parse_manifest_bytes(value: object) -> AdapterManifest:
    if type(value) is not bytes:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            "raw manifest must be bytes",
        )
    if len(value) > _MAX_MANIFEST_BYTES:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_TOO_LARGE,
            "raw manifest exceeds the byte limit",
        )
    try:
        text = value.decode("utf-8", errors="strict")
        decoded = json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_float=_reject_json_number,
            parse_constant=_reject_json_number,
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        _DuplicateJsonKey,
        _ForbiddenJsonNumber,
        RecursionError,
        ValueError,
    ) as exc:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            f"manifest is not strict bounded JSON: {type(exc).__name__}",
        )
    return verify_manifest(decoded)


def _verify_implementation_identity(
    entry: AdapterEntry,
    identities: Mapping[tuple[str, str], _ImplementationIdentity],
) -> None:
    identity = identities.get((entry.adapter_id, entry.adapter_version))
    if identity is None:
        _deny(
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_UNKNOWN,
            "adapter identity has no source-controlled implementation identity",
        )
    if (
        type(identity) is not _ImplementationIdentity
        or identity.implementation_reference != entry.implementation_reference
        or not hashes_equal(identity.implementation_sha256, entry.implementation_sha256)
    ):
        _deny(
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_HASH_MISMATCH,
            "manifest implementation identity differs from the source-controlled identity",
        )


def _verify_implementation_registry_closure(
    manifest: AdapterManifest,
    identities: Mapping[tuple[str, str], _ImplementationIdentity],
) -> None:
    manifest_keys = {
        (entry.adapter_id, entry.adapter_version): entry for entry in manifest.adapters
    }
    identity_keys = set(identities)
    if identity_keys - set(manifest_keys):
        _deny(
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_UNMANIFESTED,
            "source-controlled implementation identity is absent from the manifest",
        )
    if set(manifest_keys) - identity_keys:
        _deny(
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_UNKNOWN,
            "manifest adapter identity is absent from the source-controlled registry",
        )
    for key, entry in manifest_keys.items():
        _verify_implementation_identity(entry, {key: identities[key]})


def _verify_no_unmanifested_implementation_identities(
    manifest: AdapterManifest,
    identities: Mapping[tuple[str, str], _ImplementationIdentity],
) -> None:
    manifest_keys = {
        (entry.adapter_id, entry.adapter_version) for entry in manifest.adapters
    }
    if set(identities) - manifest_keys:
        _deny(
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_UNMANIFESTED,
            "source-controlled implementation identity is absent from the manifest",
        )


def load_manifest() -> AdapterManifest:
    """Load only the fixed checked-in production manifest and verify it fully."""

    try:
        if _MANIFEST_PATH.is_symlink() or not _MANIFEST_PATH.is_file():
            _deny(
                AdapterManifestFailureCode.ADAPTER_MANIFEST_MISSING,
                "fixed production manifest is missing or not a regular file",
            )
        raw = _MANIFEST_PATH.read_bytes()
    except AdapterManifestError:
        raise
    except OSError as exc:
        _deny(
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            f"fixed production manifest cannot be read: {type(exc).__name__}",
        )
    manifest = _parse_manifest_bytes(raw)
    _verify_no_unmanifested_implementation_identities(
        manifest, _REGISTERED_IMPLEMENTATION_IDENTITIES
    )
    return manifest


def get_manifest_identity() -> ManifestIdentity:
    """Return the verified fixed production manifest identity."""

    return load_manifest().identity


def _find_entry(
    manifest: AdapterManifest,
    adapter_id: object,
    adapter_version: object,
) -> AdapterEntry:
    if type(adapter_id) is not str:
        _deny(AdapterManifestFailureCode.ADAPTER_UNKNOWN, "adapter_id is unknown")
    versions = tuple(
        entry for entry in manifest.adapters if entry.adapter_id == adapter_id
    )
    if not versions:
        _deny(AdapterManifestFailureCode.ADAPTER_UNKNOWN, "adapter_id is unknown")
    if type(adapter_version) is not str:
        _deny(
            AdapterManifestFailureCode.ADAPTER_VERSION_UNKNOWN,
            "adapter_version is unknown",
        )
    for entry in versions:
        if entry.adapter_version == adapter_version:
            return entry
    _deny(
        AdapterManifestFailureCode.ADAPTER_VERSION_UNKNOWN,
        "adapter_version is unknown",
    )


def _resolve_adapter_metadata(
    manifest: AdapterManifest,
    adapter_id: object,
    adapter_version: object,
    identities: Mapping[tuple[str, str], _ImplementationIdentity],
) -> AdapterEntry:
    entry = _find_entry(manifest, adapter_id, adapter_version)
    if not entry.enabled:
        _deny(
            AdapterManifestFailureCode.ADAPTER_DISABLED,
            "adapter metadata is registered but disabled",
        )
    _verify_implementation_identity(entry, identities)
    return entry


def resolve_adapter_metadata(
    adapter_id: object,
    adapter_version: object,
) -> AdapterEntry:
    """Resolve verified production metadata without exposing an implementation."""

    return _resolve_adapter_metadata(
        load_manifest(),
        adapter_id,
        adapter_version,
        _REGISTERED_IMPLEMENTATION_IDENTITIES,
    )


def is_adapter_enabled(adapter_id: object, adapter_version: object) -> bool:
    """Report the verified enabled bit; unknown identities fail closed."""

    return _find_entry(load_manifest(), adapter_id, adapter_version).enabled


__all__ = (
    "AOIA_ADAPTER_IMPLEMENTATION_V1",
    "AOIA_ADAPTER_MANIFEST_ENTRY_V1",
    "AOIA_ADAPTER_MANIFEST_V1",
    "AOIA_DATA_SCHEMA_V1",
    "AdapterEntry",
    "AdapterManifest",
    "AdapterManifestError",
    "AdapterManifestFailureCode",
    "ManifestIdentity",
    "get_manifest_identity",
    "is_adapter_enabled",
    "load_manifest",
    "resolve_adapter_metadata",
    "verify_adapter_entry",
    "verify_manifest",
)
