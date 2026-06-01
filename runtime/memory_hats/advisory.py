"""Standalone advisory warning data object for Memory Hats.

This module converts reviewed local tags into advisory warning records. It does
not access storage, execute commands, render UI, inject prompts, or integrate
with RHCSA grammar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.memory_hats.tags import PheromoneTag, ReviewStatus


@dataclass(slots=True)
class AdvisoryWarning:
    """Structured non-blocking advisory derived from a local Memory Hat tag."""

    tag_fingerprint: str
    hat_id: str
    tag_type: str
    normalized_trigger: str
    correction_text: str
    evidence_refs: list[str]
    review_status: str
    confidence: str
    active: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation without side effects."""
        return {
            "tag_fingerprint": self.tag_fingerprint,
            "hat_id": self.hat_id,
            "tag_type": self.tag_type,
            "normalized_trigger": self.normalized_trigger,
            "correction_text": self.correction_text,
            "evidence_refs": list(self.evidence_refs),
            "review_status": self.review_status,
            "confidence": self.confidence,
            "active": self.active,
            "reason": self.reason,
        }


def advisory_from_tag(tag: PheromoneTag) -> AdvisoryWarning | None:
    """Create an advisory warning from an active local tag.

    Confirmed tags become high-confidence advisories. Candidate tags become
    low-confidence advisories. Rejected tags are inactive and return None.
    """
    if tag.review_status == ReviewStatus.REJECTED:
        return None

    if tag.review_status == ReviewStatus.CONFIRMED:
        confidence = "high"
        reason = "human-confirmed local advisory tag"
    else:
        confidence = "low"
        reason = "candidate local advisory tag pending review"

    return AdvisoryWarning(
        tag_fingerprint=tag.fingerprint_hash,
        hat_id=tag.hat_id,
        tag_type=tag.tag_type.value,
        normalized_trigger=tag.normalized_trigger,
        correction_text=tag.correction_text,
        evidence_refs=list(tag.evidence_refs),
        review_status=tag.review_status.value,
        confidence=confidence,
        active=True,
        reason=reason,
    )
