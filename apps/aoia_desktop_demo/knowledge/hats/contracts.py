"""Immutable contracts shared by every trusted Knowledge HAT adapter."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol, runtime_checkable


HAT_STATE = Literal["ready", "unavailable", "invalid"]
_HEX = frozenset("0123456789abcdef")


class HatValidationError(ValueError):
    """A deterministic, fail-closed HAT contract error."""


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _required_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HatValidationError(f"{name} must be non-empty text")


def _optional_text(name: str, value: object) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise HatValidationError(f"{name} must be non-empty text or None")


@dataclass(frozen=True, slots=True)
class HatDescriptor:
    hat_id: str
    display_name: str
    domain: str
    adapter_id: str
    descriptor_schema_version: int
    evidence_schema_version: int
    external_resource: bool
    authoritative: bool

    def __post_init__(self) -> None:
        for name in ("hat_id", "display_name", "domain", "adapter_id"):
            _required_text(name, getattr(self, name))
        if type(self.descriptor_schema_version) is not int or self.descriptor_schema_version < 1:
            raise HatValidationError("descriptor_schema_version must be a positive integer")
        if type(self.evidence_schema_version) is not int or self.evidence_schema_version < 1:
            raise HatValidationError("evidence_schema_version must be a positive integer")
        if type(self.external_resource) is not bool or type(self.authoritative) is not bool:
            raise HatValidationError("descriptor capability flags must be booleans")
        if self.authoritative:
            raise HatValidationError("Knowledge HAT descriptors must remain non-authoritative")


@dataclass(frozen=True, slots=True)
class HatBinding:
    hat_id: str
    binding_key: str
    root: Path

    def __post_init__(self) -> None:
        _required_text("hat_id", self.hat_id)
        _required_text("binding_key", self.binding_key)
        if not isinstance(self.root, Path):
            raise HatValidationError("binding root must be a Path")
        if not self.root.is_absolute() or ".." in self.root.parts:
            raise HatValidationError("binding root must be an absolute traversal-free path")


@dataclass(frozen=True, slots=True)
class HatStatus:
    hat_id: str
    state: HAT_STATE
    library_id: str | None
    library_version: str | None
    manifest_id: str | None
    manifest_digest: str | None
    index_id: str | None
    index_digest: str | None
    indexed_source_count: int | None
    read_only: bool
    local_only: bool
    error_category: str | None

    def __post_init__(self) -> None:
        _required_text("hat_id", self.hat_id)
        if self.state not in ("ready", "unavailable", "invalid"):
            raise HatValidationError("unsupported HAT status")
        for name in (
            "library_id",
            "library_version",
            "manifest_id",
            "index_id",
            "error_category",
        ):
            _optional_text(name, getattr(self, name))
        for name in ("manifest_digest", "index_digest"):
            value = getattr(self, name)
            if value is not None and not is_sha256(value):
                raise HatValidationError(f"{name} must be a SHA-256 or None")
        if self.indexed_source_count is not None and (
            type(self.indexed_source_count) is not int or self.indexed_source_count < 0
        ):
            raise HatValidationError("indexed_source_count must be a non-negative integer or None")
        if type(self.read_only) is not bool or type(self.local_only) is not bool:
            raise HatValidationError("status boundary flags must be booleans")
        if self.state == "ready":
            required = (
                self.library_id,
                self.library_version,
                self.manifest_id,
                self.manifest_digest,
                self.index_id,
                self.index_digest,
            )
            if any(value is None for value in required):
                raise HatValidationError("ready status requires complete control identity")
            if not self.read_only or not self.local_only or self.error_category is not None:
                raise HatValidationError("ready status must be local-only, read-only, and error-free")
        elif self.error_category is None:
            raise HatValidationError("non-ready status requires a bounded error category")


@dataclass(frozen=True, slots=True)
class HatRetrievalLimits:
    max_results: int
    max_excerpt_chars: int
    max_total_chars: int

    def __post_init__(self) -> None:
        values = (
            ("max_results", self.max_results, 1, 20),
            ("max_excerpt_chars", self.max_excerpt_chars, 256, 8_000),
            ("max_total_chars", self.max_total_chars, 1_024, 32_000),
        )
        for name, value, lower, upper in values:
            if type(value) is not int or not lower <= value <= upper:
                raise HatValidationError(f"{name} must be an integer from {lower} through {upper}")
        if self.max_excerpt_chars > self.max_total_chars:
            raise HatValidationError("per-excerpt bound cannot exceed the total evidence bound")


@dataclass(frozen=True, slots=True)
class HatPassage:
    source_id: str
    source_title: str
    source_locator: str
    statutory_references: tuple[str, ...]
    effective_dates: tuple[str, ...]
    excerpt: str
    rank: int
    score: int | float | None
    content_digest: str

    def __post_init__(self) -> None:
        for name in ("source_id", "source_title", "source_locator", "excerpt"):
            _required_text(name, getattr(self, name))
        locator = PurePosixPath(self.source_locator)
        if locator.is_absolute() or ".." in locator.parts or "\\" in self.source_locator:
            raise HatValidationError("source locator must remain corpus-relative")
        if not isinstance(self.statutory_references, tuple) or not isinstance(self.effective_dates, tuple):
            raise HatValidationError("passage metadata collections must be tuples")
        if any(not isinstance(value, str) or not value.strip() for value in self.statutory_references):
            raise HatValidationError("statutory references must be non-empty text")
        if any(not isinstance(value, str) or not value.strip() for value in self.effective_dates):
            raise HatValidationError("effective dates must be non-empty text")
        if type(self.rank) is not int or self.rank < 1:
            raise HatValidationError("passage rank must be a positive integer")
        if self.score is not None and (isinstance(self.score, bool) or not isinstance(self.score, (int, float))):
            raise HatValidationError("passage score must be numeric or None")
        if isinstance(self.score, float) and not math.isfinite(self.score):
            raise HatValidationError("passage score must be finite")
        if not is_sha256(self.content_digest):
            raise HatValidationError("passage content_digest must be a SHA-256")


@dataclass(frozen=True, slots=True)
class HatEvidenceBundle:
    schema_version: int
    hat_id: str
    normalized_query: str
    query_digest: str
    library_id: str
    library_version: str
    manifest_id: str
    manifest_digest: str
    index_id: str
    index_digest: str
    passages: tuple[HatPassage, ...]
    bundle_hash: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version < 1:
            raise HatValidationError("bundle schema_version must be a positive integer")
        for name in (
            "hat_id",
            "normalized_query",
            "library_id",
            "library_version",
            "manifest_id",
            "index_id",
        ):
            _required_text(name, getattr(self, name))
        for name in ("query_digest", "manifest_digest", "index_digest", "bundle_hash"):
            if not is_sha256(getattr(self, name)):
                raise HatValidationError(f"{name} must be a SHA-256")
        if not isinstance(self.passages, tuple):
            raise HatValidationError("bundle passages must be a tuple")
        if tuple(passage.rank for passage in self.passages) != tuple(range(1, len(self.passages) + 1)):
            raise HatValidationError("passage ranks must be contiguous and deterministic")


@dataclass(frozen=True, slots=True)
class HatAttachment:
    descriptor: HatDescriptor
    bundle: HatEvidenceBundle
    rendered_evidence: str
    rendered_evidence_digest: str
    attachment_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, HatDescriptor) or not isinstance(self.bundle, HatEvidenceBundle):
            raise HatValidationError("attachment requires immutable descriptor and bundle contracts")
        _required_text("rendered_evidence", self.rendered_evidence)
        if not is_sha256(self.rendered_evidence_digest) or not is_sha256(self.attachment_hash):
            raise HatValidationError("attachment digests must be SHA-256 values")
        if self.descriptor.hat_id != self.bundle.hat_id:
            raise HatValidationError("attachment descriptor and bundle HAT ids differ")
        if self.descriptor.evidence_schema_version != self.bundle.schema_version:
            raise HatValidationError("attachment evidence schema mismatch")
        if self.descriptor.authoritative:
            raise HatValidationError("attachment descriptor cannot be authoritative")


@runtime_checkable
class KnowledgeHatAdapter(Protocol):
    def descriptor(self) -> HatDescriptor:
        ...

    def inspect_status(self, binding: HatBinding) -> HatStatus:
        ...

    def retrieve(
        self,
        binding: HatBinding,
        query: str,
        *,
        limits: HatRetrievalLimits,
    ) -> HatEvidenceBundle:
        ...
