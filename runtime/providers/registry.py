from __future__ import annotations

from runtime.providers.contracts import (
    KNOWN_RUNTIME_PROVIDER_IDS,
    ProviderCapabilityDescriptor,
    normalize_provider_id,
)


_RUNTIME_PROVIDER_DESCRIPTORS = (
    ProviderCapabilityDescriptor("mock_chat", supports_json=True),
    ProviderCapabilityDescriptor("openrouter_chat", supports_json=True),
    ProviderCapabilityDescriptor("gemini_chat", supports_json=True),
    ProviderCapabilityDescriptor("openai_chat", supports_json=True),
    ProviderCapabilityDescriptor("anthropic_chat", supports_json=True),
    ProviderCapabilityDescriptor("google_gemini_chat", supports_json=True),
    ProviderCapabilityDescriptor("local_ollama_chat"),
)
_DESCRIPTORS_BY_ID = {
    descriptor.provider_id: descriptor for descriptor in _RUNTIME_PROVIDER_DESCRIPTORS
}

if tuple(_DESCRIPTORS_BY_ID) != KNOWN_RUNTIME_PROVIDER_IDS:
    raise RuntimeError("runtime provider registry order must remain canonical")


def list_runtime_providers() -> tuple[ProviderCapabilityDescriptor, ...]:
    return _RUNTIME_PROVIDER_DESCRIPTORS


def get_runtime_provider(provider_id: object) -> ProviderCapabilityDescriptor:
    return _DESCRIPTORS_BY_ID[normalize_provider_id(provider_id)]
