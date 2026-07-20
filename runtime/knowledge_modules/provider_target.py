"""Explicit provider/model selection kept separate from Knowledge Profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import JsonContract, KnowledgeModuleError, canonical_hash


PROVIDER_TARGET_SCHEMA_VERSION = "knowledge-provider-target-1a"
_PROVIDER_ID = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")


@dataclass(frozen=True, slots=True)
class ProviderTarget(JsonContract):
    schema_version: str
    provider_id: str
    model_id: str
    dry_run: bool = True
    live_call_requested: bool = False
    live_call_acknowledged: bool = False
    max_tokens: int = 1_024
    temperature: float = 0.0
    target_hash: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_TARGET_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider target schema differs")
        if not isinstance(self.provider_id, str):
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider ID must be text")
        provider_id = self.provider_id.strip().casefold()
        if not _PROVIDER_ID.fullmatch(provider_id):
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider ID is invalid")
        object.__setattr__(self, "provider_id", provider_id)
        if (
            not isinstance(self.model_id, str)
            or not self.model_id.strip()
            or len(self.model_id) > 512
            or any(ord(character) < 32 for character in self.model_id)
        ):
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "explicit model ID is invalid")
        object.__setattr__(self, "model_id", self.model_id.strip())
        for name in ("dry_run", "live_call_requested", "live_call_acknowledged"):
            if type(getattr(self, name)) is not bool:
                raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", f"{name} must be boolean")
        if self.live_call_requested and self.dry_run:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "live request cannot be marked dry-run")
        if not self.live_call_requested and not self.dry_run:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "non-live target must remain dry-run")
        if self.live_call_acknowledged and not self.live_call_requested:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "live acknowledgment lacks a live request")
        if type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 4_096:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider token budget differs")
        if type(self.temperature) not in (int, float) or not 0 <= float(self.temperature) <= 2:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider temperature differs")
        object.__setattr__(self, "temperature", float(self.temperature))
        payload = self.to_dict()
        supplied = payload.pop("target_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider target hash differs")
        object.__setattr__(self, "target_hash", expected)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderTarget":
        if not isinstance(value, Mapping):
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider target must be an object")
        unknown = sorted(set(value) - set(cls.__dataclass_fields__))
        if unknown:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", f"provider target unknown fields: {unknown}")
        try:
            return cls(**dict(value))
        except TypeError as exc:
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider target fields are incomplete") from exc


__all__ = ("PROVIDER_TARGET_SCHEMA_VERSION", "ProviderTarget")
