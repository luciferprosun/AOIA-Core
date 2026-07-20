"""Immutable request-only Knowledge Profiles and module checkbox selections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)
from runtime.knowledge_modules.selection import RETRIEVAL_MODES


PROFILE_MODULE_SCHEMA_VERSION = "knowledge-profile-module-selection-1b"
PROFILE_SCHEMA_VERSION = "knowledge-profile-1b"
REQUEST_ONLY = "REQUEST_ONLY"
EXPOSE = "EXPOSE"
REPORT_AND_CONTINUE_UNRELATED_MODULES = "REPORT_AND_CONTINUE_UNRELATED_MODULES"

_IDENTIFIER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?\Z")
_FILTER_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")


def _freeze_filter_value(value: Any) -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not -1_000_000_000 <= value <= 1_000_000_000:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "integer filter is outside bounds")
        return value
    if isinstance(value, str):
        if not value.strip() or len(value) > 4_096:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "string filter is empty or oversized")
        return value.strip()
    if isinstance(value, (tuple, list)):
        result = tuple(value)
        if len(result) > 100 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 512
            for item in result
        ):
            raise KnowledgeModuleError("PROFILE_INVALID", "filter sequences must contain strings")
        return tuple(item.strip() for item in result)
    raise KnowledgeModuleError("PROFILE_INVALID", "module filter value is unsupported")


def normalize_module_filters(value: Any) -> tuple[tuple[str, Any], ...]:
    if isinstance(value, Mapping):
        items = tuple(value.items())
    elif isinstance(value, (tuple, list)):
        items = tuple(value)
    else:
        raise KnowledgeModuleError("PROFILE_INVALID", "module_specific_filters must be a mapping")
    normalized: list[tuple[str, Any]] = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise KnowledgeModuleError("PROFILE_INVALID", "module filter must be a name/value pair")
        name, raw = item
        if not isinstance(name, str) or not _FILTER_NAME.fullmatch(name):
            raise KnowledgeModuleError("PROFILE_INVALID", "module filter name is invalid")
        normalized.append((name, _freeze_filter_value(raw)))
    normalized.sort(key=lambda item: item[0])
    if len(normalized) != len({name for name, _ in normalized}):
        raise KnowledgeModuleError("PROFILE_INVALID", "module filters contain duplicates")
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class KnowledgeProfileModuleSelection(JsonContract):
    schema_version: str
    module_id: str
    instance_id: str
    enabled: bool
    priority: int
    per_module_max_results: int
    per_module_max_context_characters: int
    retrieval_mode: str
    module_specific_filters: tuple[tuple[str, Any], ...] = ()
    authority_status: str = NON_AUTHORITATIVE
    selection_hash: str = ""
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
        if self.schema_version != PROFILE_MODULE_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROFILE_INVALID", "profile selection schema differs")
        for name in ("module_id", "instance_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                raise KnowledgeModuleError("PROFILE_INVALID", f"{name} is invalid")
        if type(self.enabled) is not bool:
            raise KnowledgeModuleError("PROFILE_INVALID", "enabled must be boolean")
        if type(self.priority) is not int or not 0 <= self.priority <= 10_000:
            raise KnowledgeModuleError("PROFILE_INVALID", "selection priority is invalid")
        if type(self.per_module_max_results) is not int or not 1 <= self.per_module_max_results <= 20:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "per-module result limit differs")
        if (
            type(self.per_module_max_context_characters) is not int
            or not 1_024 <= self.per_module_max_context_characters <= 32_000
        ):
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "per-module context limit differs")
        if self.retrieval_mode not in RETRIEVAL_MODES:
            raise KnowledgeModuleError("PROFILE_INVALID", "retrieval mode is invalid")
        object.__setattr__(
            self,
            "module_specific_filters",
            normalize_module_filters(self.module_specific_filters),
        )
        filters = dict(self.module_specific_filters)
        as_of = filters.get("as_of_date")
        if self.retrieval_mode == "VERIFIED_AS_OF" and not isinstance(as_of, str):
            raise KnowledgeModuleError("PROFILE_INVALID", "VERIFIED_AS_OF requires as_of_date filter")
        if isinstance(as_of, str):
            try:
                parsed_as_of = date.fromisoformat(as_of)
            except ValueError as exc:
                raise KnowledgeModuleError("PROFILE_INVALID", "as_of_date must be an ISO date") from exc
            if parsed_as_of.isoformat() != as_of:
                raise KnowledgeModuleError("PROFILE_INVALID", "as_of_date must use YYYY-MM-DD")
        if self.retrieval_mode == "SOURCE_DISCOVERY" and as_of is not None:
            raise KnowledgeModuleError("PROFILE_INVALID", "SOURCE_DISCOVERY cannot carry as_of_date")
        if "include_administrative_rules" in filters and type(filters["include_administrative_rules"]) is not bool:
            raise KnowledgeModuleError("PROFILE_INVALID", "administrative-rule filter must be boolean")
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "profile selection cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("selection_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile selection hash differs")
        object.__setattr__(self, "selection_hash", expected)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeProfileModuleSelection":
        if not isinstance(value, Mapping):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile selection must be an object")
        unknown = sorted(set(value) - set(cls.__dataclass_fields__))
        if unknown:
            raise KnowledgeModuleError("PROFILE_INVALID", f"profile selection unknown fields: {unknown}")
        material = dict(value)
        if isinstance(material.get("module_specific_filters"), Mapping):
            material["module_specific_filters"] = tuple(material["module_specific_filters"].items())
        try:
            return cls(**material)
        except TypeError as exc:
            raise KnowledgeModuleError("PROFILE_INVALID", "profile selection fields are incomplete") from exc


@dataclass(frozen=True, slots=True)
class KnowledgeProfile(JsonContract):
    schema_version: str
    profile_id: str
    display_name: str
    selected_modules: tuple[KnowledgeProfileModuleSelection, ...]
    global_max_modules: int
    global_max_results: int
    global_max_context_characters: int
    conflict_policy: str = EXPOSE
    failure_policy: str = REPORT_AND_CONTINUE_UNRELATED_MODULES
    selection_scope: str = REQUEST_ONLY
    authority_status: str = NON_AUTHORITATIVE
    profile_hash: str = ""
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
        if self.schema_version != PROFILE_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROFILE_INVALID", "profile schema differs")
        if not isinstance(self.profile_id, str) or not _IDENTIFIER.fullmatch(self.profile_id):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile_id is invalid")
        if (
            not isinstance(self.display_name, str)
            or not self.display_name.strip()
            or len(self.display_name) > 256
        ):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile display name is required")
        object.__setattr__(self, "display_name", self.display_name.strip())
        try:
            selections = tuple(self.selected_modules)
        except TypeError as exc:
            raise KnowledgeModuleError("PROFILE_INVALID", "selected_modules must be a sequence") from exc
        if any(not isinstance(item, KnowledgeProfileModuleSelection) for item in selections):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile selection type differs")
        selections = tuple(sorted(selections, key=lambda item: (item.priority, item.module_id, item.instance_id)))
        if len(selections) != len({item.module_id for item in selections}):
            raise KnowledgeModuleError("PROFILE_INVALID", "duplicate module selection")
        if len(selections) != len({item.instance_id for item in selections}):
            raise KnowledgeModuleError("PROFILE_INVALID", "duplicate instance selection")
        object.__setattr__(self, "selected_modules", selections)
        if type(self.global_max_modules) is not int or not 1 <= self.global_max_modules <= 16:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "global module limit differs")
        if type(self.global_max_results) is not int or self.global_max_results < 1:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "global result limit differs")
        if type(self.global_max_context_characters) is not int or self.global_max_context_characters < 1_024:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "global context limit differs")
        if len(self.enabled_selections) > self.global_max_modules:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "profile enables too many modules")
        if self.conflict_policy != EXPOSE:
            raise KnowledgeModuleError("PROFILE_INVALID", "conflict policy must be EXPOSE")
        if self.failure_policy != REPORT_AND_CONTINUE_UNRELATED_MODULES:
            raise KnowledgeModuleError("PROFILE_INVALID", "failure policy differs")
        if self.selection_scope != REQUEST_ONLY:
            raise KnowledgeModuleError("PROFILE_INVALID", "selection scope must be REQUEST_ONLY")
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "profile cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("profile_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile hash differs")
        object.__setattr__(self, "profile_hash", expected)

    @property
    def enabled_selections(self) -> tuple[KnowledgeProfileModuleSelection, ...]:
        return tuple(item for item in self.selected_modules if item.enabled)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeProfile":
        if not isinstance(value, Mapping):
            raise KnowledgeModuleError("PROFILE_INVALID", "profile must be an object")
        unknown = sorted(set(value) - set(cls.__dataclass_fields__))
        if unknown:
            raise KnowledgeModuleError("PROFILE_INVALID", f"profile unknown fields: {unknown}")
        material = dict(value)
        try:
            material["selected_modules"] = tuple(
                item if isinstance(item, KnowledgeProfileModuleSelection) else KnowledgeProfileModuleSelection.from_dict(item)
                for item in material.get("selected_modules", ())
            )
            return cls(**material)
        except TypeError as exc:
            raise KnowledgeModuleError("PROFILE_INVALID", "profile fields are incomplete") from exc


__all__ = (
    "EXPOSE",
    "KnowledgeProfile",
    "KnowledgeProfileModuleSelection",
    "PROFILE_MODULE_SCHEMA_VERSION",
    "PROFILE_SCHEMA_VERSION",
    "REPORT_AND_CONTINUE_UNRELATED_MODULES",
    "REQUEST_ONLY",
    "normalize_module_filters",
)
