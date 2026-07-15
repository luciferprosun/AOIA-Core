from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .knowledge_claim import KnowledgeClaim
from .provenance import KnowledgeProvenance
from .validation import (
    KNOWLEDGE_CARD_SCHEMA_VERSION,
    KnowledgeValidationError,
    assert_inert_authority_flags,
    authority_flags,
    metadata_to_dict,
    normalize_unique_records,
    require_identifier,
    require_metadata,
    require_review_status,
    verify_recorded_hash,
)


@dataclass(frozen=True)
class KnowledgeCard:
    """Immutable evidence-linked container, distinct from the legacy Tetrad."""

    card_id: str
    claims: tuple[KnowledgeClaim, ...]
    provenance: KnowledgeProvenance
    review_status: str = "review_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    card_hash: str = ""
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    schema_version: str = field(default=KNOWLEDGE_CARD_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        card_id = require_identifier("card_id", self.card_id)
        normalized_claims = normalize_unique_records(
            "claims",
            self.claims,
            record_type=KnowledgeClaim,
            identifier_field="claim_id",
        )
        if not isinstance(self.provenance, KnowledgeProvenance):
            raise KnowledgeValidationError("provenance must be a KnowledgeProvenance record")
        normalized_metadata = require_metadata(self.metadata)
        if self.provenance.card_id != card_id:
            raise KnowledgeValidationError("KnowledgeProvenance must reference its owning card_id")

        sources_by_id: dict[str, str] = {}
        evidence_by_id: dict[str, str] = {}
        for claim in normalized_claims:
            for source in claim.sources:
                existing_hash = sources_by_id.get(source.source_id)
                if existing_hash is not None:
                    raise KnowledgeValidationError(f"duplicate source_id: {source.source_id}")
                sources_by_id[source.source_id] = source.source_hash
            for link in claim.evidence_links:
                if link.evidence_id in evidence_by_id:
                    raise KnowledgeValidationError(f"duplicate evidence_id: {link.evidence_id}")
                evidence_by_id[link.evidence_id] = link.evidence_hash

        source_hashes = tuple(sorted(sources_by_id.values()))
        evidence_hashes = tuple(sorted(evidence_by_id.values()))
        provenance_claim_hashes = tuple(sorted(claim.claim_hash for claim in normalized_claims))
        if self.provenance.source_hashes != source_hashes:
            raise KnowledgeValidationError("KnowledgeProvenance source_hashes must exactly match card sources")
        if self.provenance.evidence_hashes != evidence_hashes:
            raise KnowledgeValidationError("KnowledgeProvenance evidence_hashes must exactly match card evidence")
        if self.provenance.claim_hashes != provenance_claim_hashes:
            raise KnowledgeValidationError("KnowledgeProvenance claim_hashes must exactly match card claims")

        claim_hashes = tuple(claim.claim_hash for claim in normalized_claims)
        material = {
            "schema_version": self.schema_version,
            "card_id": card_id,
            "claim_hashes": claim_hashes,
            "provenance_hash": self.provenance.provenance_hash,
            "review_status": require_review_status(self.review_status),
            "metadata": normalized_metadata,
            **authority_flags(),
        }
        assert_inert_authority_flags(material)
        object.__setattr__(self, "claims", normalized_claims)
        object.__setattr__(self, "metadata", normalized_metadata)
        object.__setattr__(self, "card_hash", verify_recorded_hash("card_hash", self.card_hash, material))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "card_id": self.card_id,
            "claims": tuple(claim.to_dict() for claim in self.claims),
            "provenance": self.provenance.to_dict(),
            "review_status": self.review_status,
            "metadata": metadata_to_dict(self.metadata),
            "card_hash": self.card_hash,
            **authority_flags(),
        }
