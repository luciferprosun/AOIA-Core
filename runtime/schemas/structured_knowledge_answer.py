"""Schema-version catalogue for strict untrusted knowledge answers."""

from runtime.knowledge_modules.citation_validation import CITATION_VALIDATION_SCHEMA_VERSION
from runtime.knowledge_modules.structured_answer import STRUCTURED_ANSWER_SCHEMA_VERSION


STRUCTURED_KNOWLEDGE_ANSWER_SCHEMA_VERSIONS = (
    CITATION_VALIDATION_SCHEMA_VERSION,
    STRUCTURED_ANSWER_SCHEMA_VERSION,
)


__all__ = ("STRUCTURED_KNOWLEDGE_ANSWER_SCHEMA_VERSIONS",)
