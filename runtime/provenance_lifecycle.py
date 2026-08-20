"""Narrow runtime lifecycle boundary for entrypoints outside runtime tools."""

from runtime.tools.provenance import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)

__all__ = (
    "AppendOnlyProvenanceStore",
    "RuntimeProvenanceEventType",
    "new_runtime_provenance_event",
)
