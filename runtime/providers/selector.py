from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.providers.contracts import (
    UNTRUSTED,
    ProviderActivationStatus,
    ProviderRuntimeResult,
    normalize_provider_id,
)
from runtime.providers.gateway import run_provider_request
from runtime.providers.payloads import build_provider_envelope
from runtime.providers.registry import get_runtime_provider, list_runtime_providers
from runtime.providers.runtime_policy import ProviderRuntimePolicy
from runtime.providers.user_config import ProviderSelectorConfig


DRY_RUN = "dry_run"
LIVE_REQUESTED = "live_requested"
_RUNTIME_SUPPORTED_IDS = frozenset({"mock_chat", "openrouter_chat", "gemini_chat"})
_LIVE_AVAILABLE_IDS = frozenset({"openrouter_chat", "gemini_chat"})
_SELECTION_SOURCES = frozenset({"operator", "manual", "config"})


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    runtime_supported: bool
    metadata_only: bool
    default_mode: str = DRY_RUN
    live_available: bool = False
    output_trust: str = UNTRUSTED

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "provider_id": self.provider_id,
            "runtime_supported": self.runtime_supported,
            "metadata_only": self.metadata_only,
            "default_mode": DRY_RUN,
            "live_available": self.live_available,
            "output_trust": UNTRUSTED,
        }


@dataclass(frozen=True)
class ProviderSelection:
    provider_id: str
    model_id: str
    mode: str
    max_tokens: int | None
    selected_by: str
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", normalize_provider_id(self.provider_id))
        if not isinstance(self.model_id, str):
            raise ValueError("model_id must be a string")
        object.__setattr__(self, "model_id", self.model_id.strip())
        if self.mode not in {DRY_RUN, LIVE_REQUESTED}:
            raise ValueError("selection mode must be dry_run or live_requested")
        if self.max_tokens is not None and (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens <= 0
            or self.max_tokens > ProviderRuntimePolicy.MAX_MANUAL_TEST_TOKENS
        ):
            raise ValueError("max_tokens must be between 1 and 4096 or None")
        if self.selected_by not in _SELECTION_SOURCES:
            raise ValueError("selected_by must be operator, manual, or config")
        if not isinstance(self.created_at, str) or not self.created_at.strip():
            raise ValueError("created_at must be caller-supplied text")
        object.__setattr__(self, "created_at", self.created_at.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "mode": self.mode,
            "max_tokens": self.max_tokens,
            "selected_by": self.selected_by,
            "created_at": self.created_at,
        }


def list_available_providers() -> tuple[ProviderStatus, ...]:
    return tuple(
        get_provider_status(descriptor.provider_id)
        for descriptor in list_runtime_providers()
        if descriptor.provider_id in _RUNTIME_SUPPORTED_IDS
    )


def get_provider_status(provider_id: object) -> ProviderStatus:
    descriptor = get_runtime_provider(provider_id)
    runtime_supported = descriptor.provider_id in _RUNTIME_SUPPORTED_IDS
    return ProviderStatus(
        provider_id=descriptor.provider_id,
        runtime_supported=runtime_supported,
        metadata_only=not runtime_supported,
        live_available=descriptor.provider_id in _LIVE_AVAILABLE_IDS,
    )


def create_provider_selection(
    *,
    provider_id: object,
    model_id: str,
    max_tokens: int | None,
    live: bool = False,
    selected_by: str = "operator",
    created_at: str,
) -> ProviderSelection:
    return ProviderSelection(
        provider_id=normalize_provider_id(provider_id),
        model_id=model_id,
        mode=LIVE_REQUESTED if live else DRY_RUN,
        max_tokens=max_tokens,
        selected_by=selected_by,
        created_at=created_at,
    )


def run_selected_provider(
    *,
    provider_id: object,
    model_id: str,
    prompt: str,
    max_tokens: int | None,
    live: bool = False,
    acknowledge_live_provider_test: bool = False,
    activation_status: ProviderActivationStatus | str = ProviderActivationStatus.DRY_RUN_ONLY,
    selected_by: str = "operator",
    created_at: str,
) -> ProviderRuntimeResult:
    selection = create_provider_selection(
        provider_id=provider_id,
        model_id=model_id,
        max_tokens=max_tokens,
        live=live,
        selected_by=selected_by,
        created_at=created_at,
    )
    params = {} if selection.max_tokens is None else {"max_tokens": selection.max_tokens}
    envelope = build_provider_envelope(
        provider_id=selection.provider_id,
        model_id=selection.model_id,
        prompt=prompt,
        params=params,
        dry_run=not live,
        created_at=selection.created_at,
    )
    return run_provider_request(
        envelope,
        live=live,
        acknowledge_live_provider_test=acknowledge_live_provider_test,
        activation_status=activation_status,
    )


def run_configured_provider(
    config: ProviderSelectorConfig,
    *,
    prompt: str,
    live: bool = False,
    acknowledge_live_provider_test: bool = False,
    activation_status: ProviderActivationStatus | str = ProviderActivationStatus.DRY_RUN_ONLY,
    created_at: str,
) -> ProviderRuntimeResult:
    if not isinstance(config, ProviderSelectorConfig):
        raise ValueError("config must be a ProviderSelectorConfig")
    return run_selected_provider(
        provider_id=config.selected_provider_id,
        model_id=config.selected_model_id,
        prompt=prompt,
        max_tokens=config.default_max_tokens,
        live=live,
        acknowledge_live_provider_test=acknowledge_live_provider_test,
        activation_status=activation_status,
        selected_by="config",
        created_at=created_at,
    )
