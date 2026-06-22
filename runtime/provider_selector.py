from __future__ import annotations

from dataclasses import dataclass
from typing import Any


OPENAI_CHAT = "openai_chat"
ANTHROPIC_CHAT = "anthropic_chat"
GOOGLE_GEMINI_CHAT = "google_gemini_chat"
LOCAL_OLLAMA_CHAT = "local_ollama_chat"
MOCK_CHAT = "mock_chat"

KNOWN_CHAT_PROVIDER_IDS = (
    OPENAI_CHAT,
    ANTHROPIC_CHAT,
    GOOGLE_GEMINI_CHAT,
    LOCAL_OLLAMA_CHAT,
    MOCK_CHAT,
)
CHAT_PROVIDER_SELECTION = "CHAT_PROVIDER_SELECTION"
CHAT_PROVIDER_SELECTION_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ChatProviderSelection:
    selected_provider_id: str
    selection_kind: str = "chat_provider_metadata"
    is_metadata_only: bool = True
    provider_enabled: bool = False
    provider_call_allowed: bool = False
    network_allowed: bool = False
    authority_granted: bool = False
    approval_granted: bool = False
    gate_satisfied: bool = False
    artifact_write_allowed: bool = False
    execution_allowed: bool = False
    object_type: str = CHAT_PROVIDER_SELECTION
    schema_version: str = CHAT_PROVIDER_SELECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        provider_id = normalize_chat_provider_id(self.selected_provider_id)
        object.__setattr__(self, "selected_provider_id", provider_id)
        object.__setattr__(self, "selection_kind", "chat_provider_metadata")
        object.__setattr__(self, "is_metadata_only", True)
        for name in (
            "provider_enabled",
            "provider_call_allowed",
            "network_allowed",
            "authority_granted",
            "approval_granted",
            "gate_satisfied",
            "artifact_write_allowed",
            "execution_allowed",
        ):
            object.__setattr__(self, name, False)
        object.__setattr__(self, "object_type", CHAT_PROVIDER_SELECTION)
        object.__setattr__(self, "schema_version", CHAT_PROVIDER_SELECTION_SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "selected_provider_id": self.selected_provider_id,
            "selection_kind": self.selection_kind,
            "is_metadata_only": self.is_metadata_only,
            "provider_enabled": self.provider_enabled,
            "provider_call_allowed": self.provider_call_allowed,
            "network_allowed": self.network_allowed,
            "authority_granted": self.authority_granted,
            "approval_granted": self.approval_granted,
            "gate_satisfied": self.gate_satisfied,
            "artifact_write_allowed": self.artifact_write_allowed,
            "execution_allowed": self.execution_allowed,
        }


def select_chat_provider(provider_id: object) -> ChatProviderSelection:
    return ChatProviderSelection(selected_provider_id=normalize_chat_provider_id(provider_id))


def normalize_chat_provider_id(provider_id: object) -> str:
    if not isinstance(provider_id, str):
        raise ValueError("chat provider id must be a non-empty string")
    normalized = provider_id.strip().casefold()
    if normalized not in KNOWN_CHAT_PROVIDER_IDS:
        raise ValueError("unknown chat provider id")
    return normalized


def chat_provider_selection_to_dict(selection: object) -> dict[str, Any]:
    if not isinstance(selection, ChatProviderSelection):
        raise ValueError("selection must be a ChatProviderSelection")
    return selection.to_dict()
