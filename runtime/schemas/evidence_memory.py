from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EvidenceSourceType(str, Enum):
    HUMAN_ENTERED = "HUMAN_ENTERED"
    LOCAL_PARSED_DOCUMENT = "LOCAL_PARSED_DOCUMENT"
    SOURCE_METADATA = "SOURCE_METADATA"


class NonEvidenceChannel(str, Enum):
    PROVIDER_CRITIQUE = "PROVIDER_CRITIQUE"
    REASONING_TRACE = "REASONING_TRACE"
    CANONICAL_KNOWLEDGE = "CANONICAL_KNOWLEDGE"
    CONTRADICTION_REGISTRY = "CONTRADICTION_REGISTRY"


class EvidenceTrustState(str, Enum):
    CANDIDATE = "CANDIDATE"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    REJECTED = "REJECTED"
    CANONICAL_READY = "CANONICAL_READY"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _coerce_bool(value: bool) -> bool:
    if not isinstance(value, bool):
        raise TypeError("boolean safety fields must be bool")
    return value


@dataclass(frozen=True)
class EvidenceProvenance:
    source_id: str
    source_type: EvidenceSourceType
    source_uri: str
    collected_at: str
    collector: str
    content_hash: str
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _coerce_text("source_id", self.source_id))
        object.__setattr__(self, "source_type", EvidenceSourceType(self.source_type))
        object.__setattr__(self, "source_uri", _coerce_text("source_uri", self.source_uri))
        object.__setattr__(self, "collected_at", _coerce_text("collected_at", self.collected_at))
        object.__setattr__(self, "collector", _coerce_text("collector", self.collector))
        object.__setattr__(self, "content_hash", _coerce_text("content_hash", self.content_hash))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_uri": self.source_uri,
            "collected_at": self.collected_at,
            "collector": self.collector,
            "content_hash": self.content_hash,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EvidenceMemoryRecord:
    evidence_id: str
    created_at: str
    source_type: EvidenceSourceType
    trust_state: EvidenceTrustState
    content_text: str
    content_hash: str
    provenance: EvidenceProvenance
    human_reviewed: bool = False
    provider_generated: bool = False
    canonical_write_allowed: bool = False
    contradiction_registry_write_allowed: bool = False
    action_approval_allowed: bool = False
    execution_allowed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        content = _coerce_text("content_text", self.content_text)
        content_hash = _hash_text(content)
        source_type = EvidenceSourceType(self.source_type)
        trust_state = EvidenceTrustState(self.trust_state)
        if not isinstance(self.provenance, EvidenceProvenance):
            raise TypeError("provenance must be an EvidenceProvenance")
        if self.provenance.source_type is not source_type:
            raise ValueError("record source_type must match provenance source_type")

        object.__setattr__(self, "evidence_id", _coerce_text("evidence_id", self.evidence_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "trust_state", trust_state)
        object.__setattr__(self, "content_text", content)
        object.__setattr__(self, "content_hash", content_hash)
        object.__setattr__(self, "human_reviewed", _coerce_bool(self.human_reviewed))
        object.__setattr__(self, "provider_generated", _coerce_bool(self.provider_generated))
        object.__setattr__(self, "canonical_write_allowed", False)
        object.__setattr__(self, "contradiction_registry_write_allowed", False)
        object.__setattr__(self, "action_approval_allowed", False)
        object.__setattr__(self, "execution_allowed", False)
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "created_at": self.created_at,
            "source_type": self.source_type.value,
            "trust_state": self.trust_state.value,
            "content_text": self.content_text,
            "content_hash": self.content_hash,
            "provenance": self.provenance.to_dict(),
            "human_reviewed": self.human_reviewed,
            "provider_generated": self.provider_generated,
            "canonical_write_allowed": self.canonical_write_allowed,
            "contradiction_registry_write_allowed": self.contradiction_registry_write_allowed,
            "action_approval_allowed": self.action_approval_allowed,
            "execution_allowed": self.execution_allowed,
            "notes": self.notes,
        }


def _create_evidence_record(
    *,
    source_type: EvidenceSourceType,
    content_text: str,
    source_id: str,
    source_uri: str = "",
    collector: str = "human",
    notes: str = "",
    created_at: str | None = None,
    evidence_id: str | None = None,
) -> EvidenceMemoryRecord:
    content = _coerce_text("content_text", content_text)
    timestamp = created_at or _utc_now_iso()
    content_hash = _hash_text(content)
    record_id = evidence_id or "evidence-" + _hash_text(
        "\n".join([source_type.value, source_id, source_uri, content_hash, timestamp])
    )[:24]
    provenance = EvidenceProvenance(
        source_id=source_id,
        source_type=source_type,
        source_uri=source_uri,
        collected_at=timestamp,
        collector=collector,
        content_hash=content_hash,
        notes=notes,
    )
    return EvidenceMemoryRecord(
        evidence_id=record_id,
        created_at=timestamp,
        source_type=source_type,
        trust_state=EvidenceTrustState.CANDIDATE,
        content_text=content,
        content_hash=content_hash,
        provenance=provenance,
        human_reviewed=False,
        provider_generated=False,
        canonical_write_allowed=False,
        contradiction_registry_write_allowed=False,
        action_approval_allowed=False,
        execution_allowed=False,
        notes=notes,
    )


def create_human_entered_evidence(
    *,
    content_text: str,
    source_id: str,
    source_uri: str = "",
    collector: str = "human",
    notes: str = "",
    created_at: str | None = None,
    evidence_id: str | None = None,
) -> EvidenceMemoryRecord:
    return _create_evidence_record(
        source_type=EvidenceSourceType.HUMAN_ENTERED,
        content_text=content_text,
        source_id=source_id,
        source_uri=source_uri,
        collector=collector,
        notes=notes,
        created_at=created_at,
        evidence_id=evidence_id,
    )


def create_local_parsed_document_evidence(
    *,
    content_text: str,
    source_id: str,
    source_uri: str = "",
    collector: str = "local_parser_adapter",
    notes: str = "",
    created_at: str | None = None,
    evidence_id: str | None = None,
) -> EvidenceMemoryRecord:
    return _create_evidence_record(
        source_type=EvidenceSourceType.LOCAL_PARSED_DOCUMENT,
        content_text=content_text,
        source_id=source_id,
        source_uri=source_uri,
        collector=collector,
        notes=notes,
        created_at=created_at,
        evidence_id=evidence_id,
    )


def classify_non_evidence_input(value: object) -> NonEvidenceChannel | None:
    if isinstance(value, NonEvidenceChannel):
        return value
    if isinstance(value, str):
        try:
            return NonEvidenceChannel(value)
        except ValueError:
            return None
    if getattr(value, "untrusted", False) is True:
        return NonEvidenceChannel.PROVIDER_CRITIQUE
    if {"source_provider", "source_model", "response_text"}.issubset(set(getattr(value, "keys", lambda: [])())):
        return NonEvidenceChannel.PROVIDER_CRITIQUE
    return None


def evidence_record_to_dict(record: EvidenceMemoryRecord) -> dict[str, Any]:
    if not isinstance(record, EvidenceMemoryRecord):
        raise TypeError("record must be an EvidenceMemoryRecord")
    return record.to_dict()
