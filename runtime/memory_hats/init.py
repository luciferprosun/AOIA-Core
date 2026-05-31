"""Exports for standalone Memory Hats advisory tag structures."""

from runtime.memory_hats.dedup import (
    compute_fingerprint,
    fingerprint_for_trigger,
    normalize_trigger,
)
from runtime.memory_hats.tags import (
    PheromoneTag,
    ReviewStatus,
    SafetyLevel,
    TagType,
)

__all__ = [
    "compute_fingerprint",
    "fingerprint_for_trigger",
    "normalize_trigger",
    "PheromoneTag",
    "ReviewStatus",
    "SafetyLevel",
    "TagType",
]
