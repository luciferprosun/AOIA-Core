from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .validation import (
    KNOWLEDGE_EVIDENCE_LINK_SCHEMA_VERSION,
    assert_inert_authority_flags,
    authority_flags,
    metadata_to_dict,
    require_identifier,
    require_metadata,
    require_text,
    verify_recorded_hash,
)


@dataclass(frozen=True)
class KnowledgeEvidenceLink:
    """Immutable binding from one claim to one source excerpt."""

    evidence_id: str
    source_id: str
    claim_id: str
    locator: str
    excerpt: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence_hash: str = ""
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    schema_version: str = field(default=KNOWLEDGE_EVIDENCE_LINK_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        normalized_metadata = require_metadata(self.metadata)
        material = {
            "schema_version": self.schema_version,
            "evidence_id": require_identifier("evidence_id", self.evidence_id),
            "source_id": require_identifier("source_id", self.source_id),
            "claim_id": require_identifier("claim_id", self.claim_id),
            "locator": require_text("locator", self.locator),
            "excerpt": require_text("excerpt", self.excerpt),
            "metadata": normalized_metadata,
            **authority_flags(),
        }
        assert_inert_authority_flags(material)
        object.__setattr__(self, "metadata", normalized_metadata)
        object.__setattr__(self, "evidence_hash", verify_recorded_hash("evidence_hash", self.evidence_hash, material))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "claim_id": self.claim_id,
            "locator": self.locator,
            "excerpt": self.excerpt,
            "metadata": metadata_to_dict(self.metadata),
            "evidence_hash": self.evidence_hash,
            **authority_flags(),
        }
