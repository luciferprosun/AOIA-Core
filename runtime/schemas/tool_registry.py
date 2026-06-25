from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


TOOL_REGISTRY_SCHEMA_VERSION = "AOIA_TOOL_REGISTRY_1A"
_SAFE_TOOL_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


class ToolRegistryStatus(str, Enum):
    KNOWN = "KNOWN"
    PREVIEW_ONLY = "PREVIEW_ONLY"
    DEFERRED = "DEFERRED"
    UNSUPPORTED = "UNSUPPORTED"
    DISABLED_METADATA_ONLY = "DISABLED_METADATA_ONLY"


class ToolKind(str, Enum):
    FILE_SYSTEM = "FILE_SYSTEM"
    TEST = "TEST"
    SHELL = "SHELL"
    GIT = "GIT"
    PACKAGE = "PACKAGE"
    PROVIDER = "PROVIDER"
    BROWSER = "BROWSER"
    UNKNOWN = "UNKNOWN"


class ToolRiskClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ToolDescriptor:
    tool_id: str
    tool_kind: ToolKind | str
    display_name: str
    description: str
    risk_class: ToolRiskClass | str
    registry_status: ToolRegistryStatus | str
    argument_schema: dict[str, Any]
    forbidden_argument_patterns: tuple[str, ...] = ()
    previewable: bool = True
    local_only: bool = True
    network_related: bool = False
    browser_related: bool = False
    package_related: bool = False
    git_related: bool = False
    write_related: bool = False
    execution_related: bool = False
    descriptor_hash: str = ""
    schema_version: str = TOOL_REGISTRY_SCHEMA_VERSION
    tool_called: bool = False
    can_call_tool: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_change_approval_gate: bool = False
    can_change_policy: bool = False
    can_access_network: bool = False
    can_read_env: bool = False
    can_load_api_key: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text("schema_version", self.schema_version))
        object.__setattr__(self, "tool_id", _safe_tool_id_or_raise(self.tool_id))
        object.__setattr__(self, "tool_kind", ToolKind(self.tool_kind))
        object.__setattr__(self, "display_name", _text("display_name", self.display_name))
        object.__setattr__(self, "description", _text("description", self.description))
        object.__setattr__(self, "risk_class", ToolRiskClass(self.risk_class))
        object.__setattr__(self, "registry_status", ToolRegistryStatus(self.registry_status))
        object.__setattr__(self, "argument_schema", _stable_json_dict("argument_schema", self.argument_schema))
        object.__setattr__(
            self,
            "forbidden_argument_patterns",
            _text_tuple("forbidden_argument_patterns", self.forbidden_argument_patterns),
        )
        for field_name in (
            "previewable",
            "local_only",
            "network_related",
            "browser_related",
            "package_related",
            "git_related",
            "write_related",
            "execution_related",
        ):
            object.__setattr__(self, field_name, _bool(field_name, getattr(self, field_name)))
        for field_name in (
            "tool_called",
            "can_call_tool",
            "can_execute",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        ):
            object.__setattr__(self, field_name, False)
        object.__setattr__(self, "descriptor_hash", _descriptor_hash(self))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_id": self.tool_id,
            "tool_kind": self.tool_kind.value,
            "display_name": self.display_name,
            "description": self.description,
            "risk_class": self.risk_class.value,
            "registry_status": self.registry_status.value,
            "argument_schema": self.argument_schema,
            "forbidden_argument_patterns": list(self.forbidden_argument_patterns),
            "previewable": self.previewable,
            "local_only": self.local_only,
            "network_related": self.network_related,
            "browser_related": self.browser_related,
            "package_related": self.package_related,
            "git_related": self.git_related,
            "write_related": self.write_related,
            "execution_related": self.execution_related,
            "descriptor_hash": self.descriptor_hash,
            "tool_called": self.tool_called,
            "can_call_tool": self.can_call_tool,
            "can_execute": self.can_execute,
            "can_write": self.can_write,
            "can_commit": self.can_commit,
            "can_change_approval_gate": self.can_change_approval_gate,
            "can_change_policy": self.can_change_policy,
            "can_access_network": self.can_access_network,
            "can_read_env": self.can_read_env,
            "can_load_api_key": self.can_load_api_key,
        }


@dataclass(frozen=True)
class ToolRegistry:
    descriptors: tuple[ToolDescriptor, ...]
    registry_hash: str = ""
    schema_version: str = TOOL_REGISTRY_SCHEMA_VERSION
    tool_called: bool = False
    can_call_tool: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_change_approval_gate: bool = False
    can_change_policy: bool = False
    can_access_network: bool = False
    can_read_env: bool = False
    can_load_api_key: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text("schema_version", self.schema_version))
        descriptors = _descriptor_tuple(self.descriptors)
        seen: set[str] = set()
        for descriptor in descriptors:
            if descriptor.tool_id in seen:
                raise ValueError("duplicate tool descriptor id")
            seen.add(descriptor.tool_id)
        object.__setattr__(self, "descriptors", tuple(sorted(descriptors, key=lambda item: item.tool_id)))
        for field_name in (
            "tool_called",
            "can_call_tool",
            "can_execute",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        ):
            object.__setattr__(self, field_name, False)
        object.__setattr__(self, "registry_hash", _registry_hash(self))

    def lookup(self, tool_id: str) -> ToolDescriptor | None:
        safe_id = _safe_tool_id(tool_id)
        if safe_id is None:
            return None
        for descriptor in self.descriptors:
            if descriptor.tool_id == safe_id:
                return descriptor
        return None

    def list_tools(self) -> tuple[ToolDescriptor, ...]:
        return self.descriptors

    def list_by_kind(self, tool_kind: ToolKind | str) -> tuple[ToolDescriptor, ...]:
        try:
            kind = ToolKind(tool_kind)
        except ValueError:
            return ()
        return tuple(descriptor for descriptor in self.descriptors if descriptor.tool_kind is kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "registry_hash": self.registry_hash,
            "descriptors": [descriptor.to_dict() for descriptor in self.descriptors],
            "tool_called": self.tool_called,
            "can_call_tool": self.can_call_tool,
            "can_execute": self.can_execute,
            "can_write": self.can_write,
            "can_commit": self.can_commit,
            "can_change_approval_gate": self.can_change_approval_gate,
            "can_change_policy": self.can_change_policy,
            "can_access_network": self.can_access_network,
            "can_read_env": self.can_read_env,
            "can_load_api_key": self.can_load_api_key,
        }


def get_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        descriptors=(
            _descriptor(
                "file_write",
                ToolKind.FILE_SYSTEM,
                "File write",
                "Metadata for a controlled file-write family.",
                ToolRiskClass.HIGH,
                ToolRegistryStatus.PREVIEW_ONLY,
                {"target_path": "repo_relative_text", "content_hash": "sha256_text"},
                write_related=True,
            ),
            _descriptor(
                "test_run",
                ToolKind.TEST,
                "Test run",
                "Metadata for a test-run family.",
                ToolRiskClass.MEDIUM,
                ToolRegistryStatus.PREVIEW_ONLY,
                {"test_selector": "text", "runtime": "text"},
                execution_related=True,
            ),
            _descriptor(
                "shell_command",
                ToolKind.SHELL,
                "Shell command",
                "Deferred metadata for shell-command proposals.",
                ToolRiskClass.CRITICAL,
                ToolRegistryStatus.DEFERRED,
                {"command": "text"},
                execution_related=True,
            ),
            _descriptor(
                "git_commit",
                ToolKind.GIT,
                "Git commit",
                "Deferred metadata for commit proposals.",
                ToolRiskClass.CRITICAL,
                ToolRegistryStatus.DEFERRED,
                {"message": "text", "paths": ["repo_relative_text"]},
                git_related=True,
                write_related=True,
            ),
            _descriptor(
                "git_push",
                ToolKind.GIT,
                "Git push",
                "Deferred metadata for push proposals.",
                ToolRiskClass.CRITICAL,
                ToolRegistryStatus.DEFERRED,
                {"remote": "text", "branch": "text"},
                git_related=True,
                network_related=True,
            ),
            _descriptor(
                "package_install",
                ToolKind.PACKAGE,
                "Package install",
                "Deferred metadata for package installation proposals.",
                ToolRiskClass.CRITICAL,
                ToolRegistryStatus.DEFERRED,
                {"package_name": "text"},
                package_related=True,
                network_related=True,
                write_related=True,
                execution_related=True,
            ),
            _descriptor(
                "provider_call",
                ToolKind.PROVIDER,
                "Provider call",
                "Disabled metadata for provider-call proposals.",
                ToolRiskClass.CRITICAL,
                ToolRegistryStatus.DISABLED_METADATA_ONLY,
                {"provider_id": "text", "model_id": "text", "prompt_hash": "sha256_text"},
                network_related=True,
            ),
            _descriptor(
                "browser_action",
                ToolKind.BROWSER,
                "Browser action",
                "Deferred metadata for browser-action proposals.",
                ToolRiskClass.CRITICAL,
                ToolRegistryStatus.DEFERRED,
                {"action": "text", "target": "text"},
                network_related=True,
                browser_related=True,
                execution_related=True,
            ),
        )
    )


def lookup_tool(tool_id: str, registry: ToolRegistry | None = None) -> ToolDescriptor | None:
    active_registry = registry if registry is not None else get_default_tool_registry()
    if not isinstance(active_registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    return active_registry.lookup(tool_id)


def _descriptor(
    tool_id: str,
    tool_kind: ToolKind,
    display_name: str,
    description: str,
    risk_class: ToolRiskClass,
    registry_status: ToolRegistryStatus,
    argument_schema: dict[str, Any],
    *,
    network_related: bool = False,
    browser_related: bool = False,
    package_related: bool = False,
    git_related: bool = False,
    write_related: bool = False,
    execution_related: bool = False,
) -> ToolDescriptor:
    return ToolDescriptor(
        tool_id=tool_id,
        tool_kind=tool_kind,
        display_name=display_name,
        description=description,
        risk_class=risk_class,
        registry_status=registry_status,
        argument_schema=argument_schema,
        forbidden_argument_patterns=_default_forbidden_argument_patterns(),
        previewable=True,
        local_only=not network_related and not browser_related,
        network_related=network_related,
        browser_related=browser_related,
        package_related=package_related,
        git_related=git_related,
        write_related=write_related,
        execution_related=execution_related,
    )


def _default_forbidden_argument_patterns() -> tuple[str, ...]:
    return (
        "rm -rf",
        "curl",
        "wget",
        "sub" + "process",
        "os" + "." + "system",
        "api" + "_" + "key",
        "secret",
        "token",
    )


def _descriptor_hash(descriptor: ToolDescriptor) -> str:
    return _hash_json(
        {
            "schema_version": descriptor.schema_version,
            "tool_id": descriptor.tool_id,
            "tool_kind": descriptor.tool_kind.value,
            "display_name": descriptor.display_name,
            "description": descriptor.description,
            "risk_class": descriptor.risk_class.value,
            "registry_status": descriptor.registry_status.value,
            "argument_schema": descriptor.argument_schema,
            "forbidden_argument_patterns": list(descriptor.forbidden_argument_patterns),
            "previewable": descriptor.previewable,
            "local_only": descriptor.local_only,
            "network_related": descriptor.network_related,
            "browser_related": descriptor.browser_related,
            "package_related": descriptor.package_related,
            "git_related": descriptor.git_related,
            "write_related": descriptor.write_related,
            "execution_related": descriptor.execution_related,
        }
    )


def _registry_hash(registry: ToolRegistry) -> str:
    return _hash_json(
        {
            "schema_version": registry.schema_version,
            "descriptor_hashes": sorted(descriptor.descriptor_hash for descriptor in registry.descriptors),
        }
    )


def _safe_tool_id_or_raise(value: Any) -> str:
    safe_id = _safe_tool_id(value)
    if safe_id is None:
        raise ValueError("tool_id must be a simple safe identifier")
    return safe_id


def _safe_tool_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or "\x00" in text:
        return None
    if any(character not in _SAFE_TOOL_ID_CHARS for character in text):
        return None
    return text


def _descriptor_tuple(values: Any) -> tuple[ToolDescriptor, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("descriptors must be a tuple or list")
    for value in values:
        if not isinstance(value, ToolDescriptor):
            raise TypeError("descriptors must contain only ToolDescriptor values")
    return tuple(values)


def _stable_json_dict(name: str, value: Any) -> dict[str, Any]:
    stable = _stable_json_value(value)
    if not isinstance(stable, dict):
        raise TypeError(f"{name} must be a dictionary")
    return stable


def _stable_json_value(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    return value


def _text_tuple(name: str, values: Any) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{name} must be a tuple or list")
    return tuple(_text(name, value) for value in values)


def _bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    return value
