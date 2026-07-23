"""Explicit trusted adapter registration; no plugin discovery or dynamic imports."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .catalog import HatCatalogEntry, load_catalog
from .contracts import HatDescriptor, HatValidationError, KnowledgeHatAdapter

NONE_HAT_ID = "none"
NONE_DESCRIPTOR = HatDescriptor(
    hat_id=NONE_HAT_ID,
    display_name="None",
    domain="none",
    adapter_id="none",
    descriptor_schema_version=1,
    evidence_schema_version=1,
    external_resource=False,
    authoritative=False,
)
AdapterFactory = Callable[[], KnowledgeHatAdapter]


class HatRegistry:
    """A static, inspectable mapping from trusted logical ids to factories."""

    def __init__(
        self,
        entries: tuple[HatCatalogEntry, ...],
        factories: Mapping[str, AdapterFactory],
    ) -> None:
        self._entries = {entry.descriptor.hat_id: entry for entry in entries}
        self._factories = dict(factories)
        if set(self._entries) != set(self._factories):
            raise HatValidationError("catalog and explicit adapter registrations differ")
        self._adapters: dict[str, KnowledgeHatAdapter] = {}
        for hat_id, factory in self._factories.items():
            if not callable(factory):
                raise HatValidationError("adapter factory must be callable")
            if not isinstance(hat_id, str) or not hat_id:
                raise HatValidationError("registered HAT id must be non-empty text")

    @classmethod
    def default(cls) -> "HatRegistry":
        from .adapters.german_federal_employment_worker_law import (  # explicit trusted registration
            GermanFederalEmploymentWorkerLawAdapter,
        )

        return cls(
            load_catalog(),
            {
                "german_federal_employment_worker_law": GermanFederalEmploymentWorkerLawAdapter,
            },
        )

    def list_descriptors(self) -> tuple[HatDescriptor, ...]:
        return (NONE_DESCRIPTOR, *(entry.descriptor for entry in self._entries.values()))

    def entry(self, hat_id: str) -> HatCatalogEntry:
        try:
            return self._entries[hat_id]
        except KeyError as exc:
            raise HatValidationError("unknown HAT id") from exc

    def adapter(self, hat_id: str) -> KnowledgeHatAdapter:
        if hat_id == NONE_HAT_ID:
            raise HatValidationError("None has no adapter")
        entry = self.entry(hat_id)
        if hat_id not in self._adapters:
            adapter = self._factories[hat_id]()
            if not isinstance(adapter, KnowledgeHatAdapter):
                raise HatValidationError("registered adapter does not implement the HAT protocol")
            descriptor = adapter.descriptor()
            if descriptor != entry.descriptor:
                raise HatValidationError("catalog and adapter descriptors disagree")
            self._adapters[hat_id] = adapter
        return self._adapters[hat_id]

    def known_binding_keys(self) -> dict[str, str]:
        return {hat_id: entry.binding_key for hat_id, entry in self._entries.items()}
