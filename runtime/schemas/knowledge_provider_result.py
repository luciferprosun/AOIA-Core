"""Schema-version catalogue for the explicit provider bridge result."""

from runtime.knowledge_modules.provider_result import (
    PROVIDER_REQUEST_SCHEMA_VERSION,
    PROVIDER_RESULT_SCHEMA_VERSION,
)


KNOWLEDGE_PROVIDER_RESULT_SCHEMA_VERSIONS = (
    PROVIDER_REQUEST_SCHEMA_VERSION,
    PROVIDER_RESULT_SCHEMA_VERSION,
)


__all__ = ("KNOWLEDGE_PROVIDER_RESULT_SCHEMA_VERSIONS",)
