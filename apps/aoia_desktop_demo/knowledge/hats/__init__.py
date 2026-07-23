"""Generic, read-only Knowledge HAT attachment boundary."""

from .contracts import (
    HatAttachment,
    HatBinding,
    HatDescriptor,
    HatEvidenceBundle,
    HatPassage,
    HatRetrievalLimits,
    HatStatus,
    HatValidationError,
    KnowledgeHatAdapter,
)
from .service import HatAttachmentService, HatServiceError

__all__ = (
    "HatAttachment",
    "HatAttachmentService",
    "HatBinding",
    "HatDescriptor",
    "HatEvidenceBundle",
    "HatPassage",
    "HatRetrievalLimits",
    "HatServiceError",
    "HatStatus",
    "HatValidationError",
    "KnowledgeHatAdapter",
)
