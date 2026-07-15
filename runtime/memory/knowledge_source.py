from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .validation import (
    KNOWLEDGE_SOURCE_SCHEMA_VERSION,
    assert_inert_authority_flags,
    authority_flags,
    metadata_to_dict,
    require_hash,
    require_identifier,
    require_metadata,
    require_text,
    source_evidence_status,
    validate_source_safety,
    verify_recorded_hash,
)


@dataclass(frozen=True)
class KnowledgeSource:
    """Immutable source metadata; it is evidence material, never authority."""

    source_id: str
    description: str
    url: str
    citation: str
    content_hash: str
    source_type: str = "document"
    authority_label: str = "evidence_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source_hash: str = ""
    evidence_status: str = field(default="", init=False)
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    schema_version: str = field(default=KNOWLEDGE_SOURCE_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        normalized_metadata = require_metadata(self.metadata)
        validate_source_safety(
            source_type=self.source_type,
            authority_label=self.authority_label,
            metadata=normalized_metadata,
        )
        evidence_status = source_evidence_status(self.source_type)
        material = {
            "schema_version": self.schema_version,
            "source_id": require_identifier("source_id", self.source_id),
            "description": require_text("description", self.description),
            "url": require_text("url", self.url),
            "citation": require_text("citation", self.citation),
            "content_hash": require_hash("content_hash", self.content_hash),
            "source_type": self.source_type,
            "evidence_status": evidence_status,
            "authority_label": self.authority_label,
            "metadata": normalized_metadata,
            **authority_flags(),
        }
        assert_inert_authority_flags(material)
        object.__setattr__(self, "evidence_status", evidence_status)
        object.__setattr__(self, "metadata", normalized_metadata)
        object.__setattr__(self, "source_hash", verify_recorded_hash("source_hash", self.source_hash, material))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "description": self.description,
            "url": self.url,
            "citation": self.citation,
            "content_hash": self.content_hash,
            "source_type": self.source_type,
            "evidence_status": self.evidence_status,
            "authority_label": self.authority_label,
            "metadata": metadata_to_dict(self.metadata),
            "source_hash": self.source_hash,
            **authority_flags(),
        }
