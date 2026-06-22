from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from runtime.providers.contracts import (
    ProviderMessage,
    ProviderRequestEnvelope,
    normalize_provider_id,
)
from runtime.providers.redaction import redact_provider_data


_PAYLOAD_PROVIDER_IDS = {"mock_chat", "openrouter_chat", "gemini_chat"}
_METADATA_ONLY_PROVIDER_IDS = {
    "openai_chat",
    "anthropic_chat",
    "google_gemini_chat",
    "local_ollama_chat",
}
_ALLOWED_PARAM_NAMES = {"max_tokens", "temperature"}


def build_provider_envelope(
    *,
    provider_id: object,
    model_id: str,
    prompt: str = "",
    messages: Sequence[Mapping[str, object] | ProviderMessage] = (),
    params: Mapping[str, object] | None = None,
    dry_run: bool = True,
    created_at: str,
) -> ProviderRequestEnvelope:
    normalized_provider = normalize_provider_id(provider_id)
    normalized_messages = _normalize_messages(messages)
    normalized_prompt = _string_value(prompt, "prompt")
    if normalized_prompt.strip() and normalized_messages:
        raise ValueError("provide prompt or messages, not both")
    normalized_params = _normalize_params(params or {})
    normalized_model = _string_value(model_id, "model_id").strip()
    if normalized_provider in _PAYLOAD_PROVIDER_IDS:
        payload = build_provider_payload_values(
            provider_id=normalized_provider,
            model_id=normalized_model,
            prompt=normalized_prompt.strip(),
            messages=normalized_messages,
            params=normalized_params,
        )
    else:
        if normalized_provider not in _METADATA_ONLY_PROVIDER_IDS:
            raise ValueError("unknown provider_id")
        payload = {
            "provider_id": normalized_provider,
            "model_id": normalized_model,
            "metadata_only": True,
            "runtime_payload_supported": False,
            "input_summary": {
                "prompt_present": bool(normalized_prompt.strip()),
                "message_count": len(normalized_messages),
            },
        }
    preview = json.dumps(
        redact_provider_data(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return ProviderRequestEnvelope(
        provider_id=normalized_provider,
        model_id=model_id,
        prompt=normalized_prompt,
        messages=normalized_messages,
        params=normalized_params,
        dry_run=dry_run,
        created_at=created_at,
        payload_preview=preview,
    )


def build_provider_payload(envelope: ProviderRequestEnvelope) -> dict[str, Any]:
    if not isinstance(envelope, ProviderRequestEnvelope):
        raise ValueError("envelope must be a ProviderRequestEnvelope")
    return build_provider_payload_values(
        provider_id=envelope.provider_id,
        model_id=envelope.model_id,
        prompt=envelope.prompt,
        messages=envelope.messages,
        params=envelope.params,
    )


def build_provider_payload_values(
    *,
    provider_id: object,
    model_id: str,
    prompt: str,
    messages: tuple[ProviderMessage, ...],
    params: tuple[tuple[str, int | float | str | bool | None], ...],
) -> dict[str, Any]:
    provider = normalize_provider_id(provider_id)
    if provider not in _PAYLOAD_PROVIDER_IDS:
        raise ValueError("provider is metadata-only in Provider Runtime 1A")
    message_values = _message_values(prompt, messages)
    param_values = dict(params)
    if provider in {"mock_chat", "openrouter_chat"}:
        payload: dict[str, Any] = {"model": model_id, "messages": message_values}
        if "max_tokens" in param_values:
            payload["max_tokens"] = param_values["max_tokens"]
        if "temperature" in param_values:
            payload["temperature"] = param_values["temperature"]
        return payload

    generation_config: dict[str, Any] = {}
    if "max_tokens" in param_values:
        generation_config["maxOutputTokens"] = param_values["max_tokens"]
    if "temperature" in param_values:
        generation_config["temperature"] = param_values["temperature"]
    return {
        "contents": [
            {
                "role": _gemini_role(item["role"]),
                "parts": [{"text": item["content"]}],
            }
            for item in message_values
        ],
        "generationConfig": generation_config,
    }


def build_deterministic_mock_response(envelope: ProviderRequestEnvelope) -> str:
    if envelope.provider_id != "mock_chat":
        raise ValueError("deterministic mock response requires mock_chat")
    digest = hashlib.sha256(envelope.payload_preview.encode("utf-8")).hexdigest()[:16]
    return f"mock_chat deterministic response [{digest}]"


def _normalize_messages(
    values: Sequence[Mapping[str, object] | ProviderMessage],
) -> tuple[ProviderMessage, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("messages must be a sequence of message records")
    normalized: list[ProviderMessage] = []
    for value in values:
        if isinstance(value, ProviderMessage):
            normalized.append(value)
        elif isinstance(value, Mapping) and set(value) == {"role", "content"}:
            normalized.append(
                ProviderMessage(role=value["role"], content=value["content"])  # type: ignore[arg-type]
            )
        else:
            raise ValueError("message must contain only role and content")
    return tuple(normalized)


def _normalize_params(
    values: Mapping[str, object],
) -> tuple[tuple[str, int | float | str | bool | None], ...]:
    if not isinstance(values, Mapping):
        raise ValueError("params must be a mapping")
    if any(not isinstance(key, str) or key not in _ALLOWED_PARAM_NAMES for key in values):
        raise ValueError("unsupported provider parameter; fallback is not available")
    normalized: list[tuple[str, int | float | str | bool | None]] = []
    for key in sorted(values):
        value = values[key]
        if key == "max_tokens":
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("max_tokens must be a positive integer")
        elif key == "temperature":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("temperature must be numeric")
            if not 0 <= float(value) <= 2:
                raise ValueError("temperature must be between 0 and 2")
        normalized.append((key, value))  # type: ignore[arg-type]
    return tuple(normalized)


def _message_values(prompt: str, messages: tuple[ProviderMessage, ...]) -> list[dict[str, str]]:
    if messages:
        return [message.to_dict() for message in messages]
    return [{"role": "user", "content": prompt}] if prompt else []


def _gemini_role(role: str) -> str:
    return "model" if role == "assistant" else "user"


def _string_value(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value
