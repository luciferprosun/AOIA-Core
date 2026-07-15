from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .validation import (
    KNOWLEDGE_PROVENANCE_SCHEMA_VERSION,
    assert_inert_authority_flags,
    authority_flags,
    metadata_to_dict,
    normalize_hash_tuple,
    require_identifier,
    require_metadata,
    require_review_status,
    require_text,
    verify_recorded_hash,
)


@dataclass(frozen=True)
class KnowledgeProvenance:
    """Immutable, card-bound provenance manifest; never verification or approval."""

    provenance_id: str
    card_id: str
    source_hashes: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    claim_hashes: tuple[str, ...]
    created_by: str
    review_status: str = "review_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance_hash: str = ""
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    schema_version: str = field(default=KNOWLEDGE_PROVENANCE_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        normalized_metadata = require_metadata(self.metadata)
        source_hashes = normalize_hash_tuple("source_hashes", self.source_hashes)
        evidence_hashes = normalize_hash_tuple("evidence_hashes", self.evidence_hashes)
        claim_hashes = normalize_hash_tuple("claim_hashes", self.claim_hashes)
        material = {
            "schema_version": self.schema_version,
            "provenance_id": require_identifier("provenance_id", self.provenance_id),
            "card_id": require_identifier("card_id", self.card_id),
            "source_hashes": source_hashes,
            "evidence_hashes": evidence_hashes,
            "claim_hashes": claim_hashes,
            "created_by": require_text("created_by", self.created_by),
            "review_status": require_review_status(self.review_status),
            "metadata": normalized_metadata,
            **authority_flags(),
        }
        assert_inert_authority_flags(material)
        object.__setattr__(self, "source_hashes", source_hashes)
        object.__setattr__(self, "evidence_hashes", evidence_hashes)
        object.__setattr__(self, "claim_hashes", claim_hashes)
        object.__setattr__(self, "metadata", normalized_metadata)
        object.__setattr__(
            self,
            "provenance_hash",
            verify_recorded_hash("provenance_hash", self.provenance_hash, material),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provenance_id": self.provenance_id,
            "card_id": self.card_id,
            "source_hashes": self.source_hashes,
            "evidence_hashes": self.evidence_hashes,
            "claim_hashes": self.claim_hashes,
            "created_by": self.created_by,
            "review_status": self.review_status,
            "metadata": metadata_to_dict(self.metadata),
            "provenance_hash": self.provenance_hash,
            **authority_flags(),
        }
