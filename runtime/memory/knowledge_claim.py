from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .evidence_link import KnowledgeEvidenceLink
from .knowledge_source import KnowledgeSource
from .validation import (
    KNOWLEDGE_CLAIM_SCHEMA_VERSION,
    KNOWLEDGE_DISCOVERY_ONLY,
    KnowledgeValidationError,
    assert_inert_authority_flags,
    authority_flags,
    metadata_to_dict,
    normalize_unique_records,
    optional_hash,
    require_identifier,
    require_metadata,
    validate_claim_safety,
    verify_recorded_hash,
)


@dataclass(frozen=True)
class KnowledgeClaim:
    """Immutable claim whose evidence links bind it to source-backed excerpts."""

    claim_id: str
    statement: str
    sources: tuple[KnowledgeSource, ...]
    evidence_links: tuple[KnowledgeEvidenceLink, ...]
    author_type: str = "source"
    review_status: str = "review_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    previous_claim_hash: str = ""
    claim_hash: str = ""
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    schema_version: str = field(default=KNOWLEDGE_CLAIM_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        claim_id = require_identifier("claim_id", self.claim_id)
        normalized_sources = normalize_unique_records(
            "sources",
            self.sources,
            record_type=KnowledgeSource,
            identifier_field="source_id",
        )
        normalized_links = normalize_unique_records(
            "evidence_links",
            self.evidence_links,
            record_type=KnowledgeEvidenceLink,
            identifier_field="evidence_id",
        )
        normalized_metadata = require_metadata(self.metadata)
        validate_claim_safety(
            statement=self.statement,
            author_type=self.author_type,
            review_status=self.review_status,
            metadata=normalized_metadata,
        )
        sources_by_id = {source.source_id: source for source in normalized_sources}
        linked_source_ids: set[str] = set()
        for link in normalized_links:
            if link.claim_id != claim_id:
                raise KnowledgeValidationError("KnowledgeEvidenceLink must reference its owning claim_id")
            source = sources_by_id.get(link.source_id)
            if source is None:
                raise KnowledgeValidationError("KnowledgeEvidenceLink must reference a claim source_id")
            if source.evidence_status == KNOWLEDGE_DISCOVERY_ONLY:
                raise KnowledgeValidationError(f"{source.source_type} cannot satisfy claim evidence")
            linked_source_ids.add(link.source_id)
        if linked_source_ids != set(sources_by_id):
            raise KnowledgeValidationError("every claim source must have an explicit evidence link")
        material = {
            "schema_version": self.schema_version,
            "claim_id": claim_id,
            "statement": self.statement,
            "source_hashes": tuple(source.source_hash for source in normalized_sources),
            "evidence_hashes": tuple(link.evidence_hash for link in normalized_links),
            "author_type": self.author_type,
            "review_status": self.review_status,
            "metadata": normalized_metadata,
            "previous_claim_hash": optional_hash("previous_claim_hash", self.previous_claim_hash),
            **authority_flags(),
        }
        assert_inert_authority_flags(material)
        object.__setattr__(self, "sources", normalized_sources)
        object.__setattr__(self, "evidence_links", normalized_links)
        object.__setattr__(self, "metadata", normalized_metadata)
        object.__setattr__(self, "claim_hash", verify_recorded_hash("claim_hash", self.claim_hash, material))

    def revision_placeholder(
        self,
        *,
        claim_id: str,
        statement: str,
        evidence_links: tuple[KnowledgeEvidenceLink, ...],
        metadata: Mapping[str, Any] | None = None,
    ) -> "KnowledgeClaim":
        """Create an inert revision only with caller-supplied, newly bound evidence."""

        return KnowledgeClaim(
            claim_id=claim_id,
            statement=statement,
            sources=self.sources,
            evidence_links=evidence_links,
            author_type=self.author_type,
            review_status="needs_review",
            metadata={} if metadata is None else metadata,
            previous_claim_hash=self.claim_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "statement": self.statement,
            "sources": tuple(source.to_dict() for source in self.sources),
            "evidence_links": tuple(link.to_dict() for link in self.evidence_links),
            "author_type": self.author_type,
            "review_status": self.review_status,
            "metadata": metadata_to_dict(self.metadata),
            "previous_claim_hash": self.previous_claim_hash,
            "claim_hash": self.claim_hash,
            **authority_flags(),
        }
