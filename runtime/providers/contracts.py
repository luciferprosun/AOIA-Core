from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


UNTRUSTED = "UNTRUSTED"
DRY_RUN_PREVIEW = "dry_run_preview"
LIVE_SUCCESS = "live_success"
BLOCKED = "blocked"
ERROR = "error"


class ProviderId(str, Enum):
    MOCK_CHAT = "mock_chat"
    OPENROUTER_CHAT = "openrouter_chat"
    GEMINI_CHAT = "gemini_chat"
    OPENAI_CHAT = "openai_chat"
    ANTHROPIC_CHAT = "anthropic_chat"
    GOOGLE_GEMINI_CHAT = "google_gemini_chat"
    LOCAL_OLLAMA_CHAT = "local_ollama_chat"


class ProviderActivationStatus(str, Enum):
    DISABLED = "disabled"
    DRY_RUN_ONLY = "dry_run_only"
    LIVE_ALLOWED_FOR_MANUAL_TEST = "live_allowed_for_manual_test"


KNOWN_RUNTIME_PROVIDER_IDS = tuple(item.value for item in ProviderId)


@dataclass(frozen=True)
class ProviderCapabilityDescriptor:
    provider_id: str
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_images: bool = False
    supports_json: bool = False
    max_input_tokens: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", normalize_provider_id(self.provider_id))
        if self.max_input_tokens is not None:
            if isinstance(self.max_input_tokens, bool) or self.max_input_tokens <= 0:
                raise ValueError("max_input_tokens must be positive or None")


@dataclass(frozen=True)
class ProviderMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        role = _required_text(self.role, "role").casefold()
        if role not in {"system", "user", "assistant"}:
            raise ValueError("unsupported message role")
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "content", _required_text(self.content, "content"))

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ProviderRequestEnvelope:
    provider_id: str
    model_id: str
    prompt: str
    messages: tuple[ProviderMessage, ...]
    params: tuple[tuple[str, int | float | str | bool | None], ...]
    dry_run: bool
    created_at: str
    payload_preview: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", normalize_provider_id(self.provider_id))
        if not isinstance(self.model_id, str):
            raise ValueError("model_id must be a string")
        if not isinstance(self.prompt, str):
            raise ValueError("prompt must be a string")
        if not isinstance(self.messages, tuple) or not all(
            isinstance(item, ProviderMessage) for item in self.messages
        ):
            raise ValueError("messages must be an immutable ProviderMessage tuple")
        if not isinstance(self.params, tuple):
            raise ValueError("params must be an immutable tuple")
        if not isinstance(self.dry_run, bool):
            raise ValueError("dry_run must be boolean")
        object.__setattr__(self, "model_id", self.model_id.strip())
        object.__setattr__(self, "prompt", self.prompt.strip())
        object.__setattr__(self, "created_at", _required_text(self.created_at, "created_at"))
        object.__setattr__(
            self,
            "payload_preview",
            _required_text(self.payload_preview, "payload_preview"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "prompt": self.prompt,
            "messages": [item.to_dict() for item in self.messages],
            "params": {key: value for key, value in self.params},
            "dry_run": self.dry_run,
            "created_at": self.created_at,
            "payload_preview": self.payload_preview,
        }


@dataclass(frozen=True)
class ProviderRuntimeResult:
    provider_id: str
    model_id: str
    mode: str
    status: str
    redacted_request_preview: str
    response_text: str | None = None
    error_message: str | None = None
    trust_status: str = UNTRUSTED

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", normalize_provider_id(self.provider_id))
        if self.mode not in {"dry_run", "live"}:
            raise ValueError("mode must be dry_run or live")
        if self.status not in {DRY_RUN_PREVIEW, LIVE_SUCCESS, BLOCKED, ERROR}:
            raise ValueError("unsupported provider runtime result status")
        if self.trust_status != UNTRUSTED:
            raise ValueError("provider runtime output must remain UNTRUSTED")
        object.__setattr__(self, "model_id", str(self.model_id).strip())
        object.__setattr__(
            self,
            "redacted_request_preview",
            _required_text(self.redacted_request_preview, "redacted_request_preview"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "mode": self.mode,
            "status": self.status,
            "redacted_request_preview": self.redacted_request_preview,
            "response_text": self.response_text,
            "error_message": self.error_message,
            "trust_status": UNTRUSTED,
        }


def normalize_provider_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("provider_id must be a known string")
    normalized = value.strip().casefold()
    if normalized not in KNOWN_RUNTIME_PROVIDER_IDS:
        raise ValueError("unknown provider_id")
    return normalized


def normalize_activation_status(value: object) -> ProviderActivationStatus:
    if isinstance(value, ProviderActivationStatus):
        return value
    if isinstance(value, str):
        try:
            return ProviderActivationStatus(value.strip().casefold())
        except ValueError as error:
            raise ValueError("unknown provider activation status") from error
    raise ValueError("provider activation status is required")


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()
