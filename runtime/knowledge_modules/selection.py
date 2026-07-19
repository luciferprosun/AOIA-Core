"""Per-request Knowledge Module selection and bounded query contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import (
    JsonContract,
    KnowledgeModuleError,
    canonical_hash,
)


SELECTION_SCHEMA_VERSION = "knowledge-module-selection-1a"
QUERY_SCHEMA_VERSION = "knowledge-module-query-1a"
RETRIEVAL_MODES = ("SOURCE_DISCOVERY", "VERIFIED_AS_OF")

_MODULE_ID = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
_JURISDICTION = re.compile(r"[A-Z]{2}(?:-[A-Z0-9]{1,12})?\Z")
_LANGUAGE = re.compile(r"[a-z]{2,3}\Z")
_IMPLICIT_CURRENTNESS = re.compile(
    r"(?<![\w-])(today|currently|now|latest|presently)(?![\w-])",
    re.IGNORECASE,
)

DOCUMENT_TYPES = (
    "STATUTE_OR_REGULATION",
    "ADMINISTRATIVE_RULE",
    "OFFICIAL_PROMULGATION",
    "OFFICIAL_METADATA",
)
SOURCE_CLASSES = (
    "OFFICIAL_CONSOLIDATED_TEXT",
    "OFFICIAL_ADMINISTRATIVE_RULE",
    "OFFICIAL_PROMULGATION",
    "OFFICIAL_METADATA",
)


def _unique_sorted_strings(name: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", f"{name} must be a sequence")
    try:
        result = tuple(value)
    except TypeError as exc:
        raise KnowledgeModuleError(
            "INVALID_KNOWLEDGE_QUERY", f"{name} must be a sequence"
        ) from exc
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise KnowledgeModuleError(
            "INVALID_KNOWLEDGE_QUERY", f"{name} contains an invalid string"
        )
    normalized = tuple(item.strip() for item in result)
    if len(normalized) != len(set(normalized)):
        raise KnowledgeModuleError(
            "DUPLICATE_MODULE_ID" if name == "module_ids" else "INVALID_KNOWLEDGE_QUERY",
            f"{name} contains duplicates",
        )
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class KnowledgeModuleSelection(JsonContract):
    schema_version: str = SELECTION_SCHEMA_VERSION
    module_ids: tuple[str, ...] = ()
    selection_hash: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SELECTION_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_SELECTION", "selection schema differs")
        try:
            module_ids = _unique_sorted_strings("module_ids", self.module_ids)
        except KnowledgeModuleError as exc:
            if exc.status == "INVALID_KNOWLEDGE_QUERY":
                raise KnowledgeModuleError("INVALID_MODULE_SELECTION", exc.reason) from exc
            raise
        if any(not _MODULE_ID.fullmatch(module_id) for module_id in module_ids):
            raise KnowledgeModuleError("INVALID_MODULE_SELECTION", "selection has invalid module ID")
        object.__setattr__(self, "module_ids", module_ids)
        payload = self.to_dict()
        supplied = payload.pop("selection_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_SELECTION", "selection hash differs")
        object.__setattr__(self, "selection_hash", expected)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeModuleSelection":
        if not isinstance(value, Mapping):
            raise KnowledgeModuleError("INVALID_MODULE_SELECTION", "selection must be an object")
        unknown = sorted(set(value) - set(cls.__dataclass_fields__))
        if unknown:
            raise KnowledgeModuleError(
                "INVALID_MODULE_SELECTION", f"KnowledgeModuleSelection unknown fields: {unknown}"
            )
        try:
            return cls(**dict(value))
        except TypeError as exc:
            raise KnowledgeModuleError(
                "INVALID_MODULE_SELECTION", "selection fields are incomplete"
            ) from exc


@dataclass(frozen=True, slots=True)
class KnowledgeModuleQuery(JsonContract):
    question: str
    retrieval_mode: str
    as_of_date: str | None = None
    jurisdictions: tuple[str, ...] = ("DE-BUND",)
    document_types: tuple[str, ...] = ()
    source_classes: tuple[str, ...] = ()
    languages: tuple[str, ...] = ("de",)
    include_administrative_rules: bool = False
    max_results: int = 10
    max_excerpt_characters: int = 2_000
    max_total_context_characters: int = 16_000
    schema_version: str = QUERY_SCHEMA_VERSION
    query_hash: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != QUERY_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "query schema differs")
        if not isinstance(self.question, str) or not self.question.strip():
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "question must not be empty")
        object.__setattr__(self, "question", self.question.strip())
        if self.retrieval_mode not in RETRIEVAL_MODES:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY", f"retrieval_mode must be one of {RETRIEVAL_MODES}"
            )
        for name in ("jurisdictions", "document_types", "source_classes", "languages"):
            object.__setattr__(
                self,
                name,
                _unique_sorted_strings(name, getattr(self, name)),
            )
        if not self.jurisdictions or any(
            not _JURISDICTION.fullmatch(item) for item in self.jurisdictions
        ):
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "invalid jurisdictions")
        if not self.languages or any(not _LANGUAGE.fullmatch(item) for item in self.languages):
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "invalid languages")
        unknown_documents = set(self.document_types) - set(DOCUMENT_TYPES)
        unknown_sources = set(self.source_classes) - set(SOURCE_CLASSES)
        if unknown_documents or unknown_sources:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY",
                f"unsupported filters: documents={sorted(unknown_documents)}, sources={sorted(unknown_sources)}",
            )
        if type(self.include_administrative_rules) is not bool:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY", "include_administrative_rules must be boolean"
            )
        administrative_filter = (
            "ADMINISTRATIVE_RULE" in self.document_types
            or "OFFICIAL_ADMINISTRATIVE_RULE" in self.source_classes
        )
        if administrative_filter and not self.include_administrative_rules:
            raise KnowledgeModuleError(
                "CONFLICTING_KNOWLEDGE_FILTERS",
                "administrative-rule filter conflicts with include_administrative_rules=false",
            )
        if self.retrieval_mode == "VERIFIED_AS_OF":
            if self.as_of_date is None:
                raise KnowledgeModuleError(
                    "INVALID_KNOWLEDGE_QUERY", "VERIFIED_AS_OF requires explicit as_of_date"
                )
            self._validate_iso_date(self.as_of_date)
        else:
            if self.as_of_date is not None:
                raise KnowledgeModuleError(
                    "INVALID_KNOWLEDGE_QUERY",
                    "SOURCE_DISCOVERY cannot carry an as_of_date",
                )
            if _IMPLICIT_CURRENTNESS.search(self.question):
                raise KnowledgeModuleError(
                    "IMPLICIT_CURRENTNESS_FORBIDDEN",
                    "SOURCE_DISCOVERY cannot imply a current-law determination",
                )
        limits = (
            ("max_results", self.max_results, 1, 20),
            ("max_excerpt_characters", self.max_excerpt_characters, 256, 4_000),
            (
                "max_total_context_characters",
                self.max_total_context_characters,
                1_024,
                32_000,
            ),
        )
        for name, value, minimum, maximum in limits:
            if type(value) is not int or not minimum <= value <= maximum:
                raise KnowledgeModuleError(
                    "INVALID_KNOWLEDGE_QUERY",
                    f"{name} must be an integer from {minimum} through {maximum}",
                )
        payload = self.to_dict()
        supplied = payload.pop("query_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "query hash differs")
        object.__setattr__(self, "query_hash", expected)

    @staticmethod
    def _validate_iso_date(value: str) -> None:
        if not isinstance(value, str):
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "as_of_date must be a string")
        try:
            normalized = date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY", "as_of_date must be YYYY-MM-DD"
            ) from exc
        if normalized != value:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY", "as_of_date must be YYYY-MM-DD"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeModuleQuery":
        if not isinstance(value, Mapping):
            raise KnowledgeModuleError("INVALID_KNOWLEDGE_QUERY", "query must be an object")
        unknown = sorted(set(value) - set(cls.__dataclass_fields__))
        if unknown:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY", f"KnowledgeModuleQuery unknown fields: {unknown}"
            )
        try:
            return cls(**dict(value))
        except TypeError as exc:
            raise KnowledgeModuleError(
                "INVALID_KNOWLEDGE_QUERY", "query fields are incomplete"
            ) from exc


__all__ = (
    "DOCUMENT_TYPES",
    "KnowledgeModuleQuery",
    "KnowledgeModuleSelection",
    "QUERY_SCHEMA_VERSION",
    "RETRIEVAL_MODES",
    "SELECTION_SCHEMA_VERSION",
    "SOURCE_CLASSES",
)
