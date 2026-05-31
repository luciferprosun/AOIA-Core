"""Standalone advisory tag structures for the Memory Hats prototype.

This module defines data shapes only. It does not perform storage, routing,
hashing, command validation, command execution, or runtime integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TagType(str, Enum):
    """Local advisory correction tag categories."""

    UNSUPPORTED_CLAIM = "unsupported_claim"
    IMPLEMENTATION_OVERCLAIM = "implementation_overclaim"
    COMMAND_SHAPE_SUSPICIOUS = "command_shape_suspicious"
    UNSUPPORTED_LINUX_COMMAND = "unsupported_linux_command"
    STATE_CHANGING_COMMAND_REQUIRES_REVIEW = (
        "state_changing_command_requires_review"
    )
    CONTRADICTS_KNOWN_STATE = "contradicts_known_state"
    CONFIDENCE_EVIDENCE_MISMATCH = "confidence_evidence_mismatch"
    MODEL_DISAGREEMENT = "model_disagreement"
    POSSIBLE_SECRET_EXPOSURE = "possible_secret_exposure"


class ReviewStatus(str, Enum):
    """Human review state for a local advisory tag."""

    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class SafetyLevel(str, Enum):
    """Explicitly non-blocking safety label for GT-HAT-1."""

    ADVISORY = "advisory"


@dataclass(slots=True)
class PheromoneTag:
    """Minimal local advisory correction record.

    The fingerprint and normalized trigger are supplied by later phases. This
    class intentionally avoids hashing, normalization, storage, or routing.
    """

    fingerprint_hash: str
    hat_id: str
    path: str
    tag_type: TagType
    normalized_trigger: str
    correction_text: str
    first_seen: str
    last_seen: str
    evidence_refs: list[str] = field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.CANDIDATE
    seen_count: int = 1
    hat_version: str | None = None
    created_by: str = "manual"
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation without file I/O."""

        return {
            "fingerprint_hash": self.fingerprint_hash,
            "hat_id": self.hat_id,
            "path": self.path,
            "tag_type": self.tag_type.value,
            "normalized_trigger": self.normalized_trigger,
            "correction_text": self.correction_text,
            "evidence_refs": list(self.evidence_refs),
            "review_status": self.review_status.value,
            "seen_count": self.seen_count,
            "hat_version": self.hat_version,
            "created_by": self.created_by,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PheromoneTag":
        """Create a tag from a dictionary produced by to_dict()."""

        payload = dict(data)
        payload["tag_type"] = TagType(payload["tag_type"])
        payload["review_status"] = ReviewStatus(
            payload.get("review_status", ReviewStatus.CANDIDATE.value)
        )
        payload["evidence_refs"] = list(payload.get("evidence_refs", []))
        return cls(**payload)
