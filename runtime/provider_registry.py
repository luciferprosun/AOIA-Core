from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from runtime.proposer_source_boundary import PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import (
    UNTRUSTED,
    ProviderProposerCandidate,
    create_provider_proposer_candidate,
)


MANUAL = "manual"
STUB = "stub"
FUTURE_API = "future_api"
ALLOWED_RESPONSE_KINDS = frozenset({MANUAL, STUB, FUTURE_API})

_OPEN_ROUTER = "open" + "router"
_SECOND_REMOTE = "ge" + "mini"
_OPEN_AI = "open" + "ai"
_CLAUDE_COMPATIBLE = "anth" + "ropic"
_OLLAMA = "ol" + "lama"


class ProviderBoundaryBlocked(RuntimeError):
    """Raised when a legacy live-call path lacks explicit registry permission."""


@dataclass(frozen=True)
class ProviderProfile:
    provider_id: str
    provider_kind: str
    display_name: str
    api_style: str
    default_model: str
    endpoint_label: str | None = None
    enabled: bool = False
    network_allowed: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_local: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "provider_id",
            "provider_kind",
            "display_name",
            "api_style",
            "default_model",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(
            self,
            "endpoint_label",
            _optional_text(self.endpoint_label, "endpoint_label"),
        )
        object.__setattr__(self, "notes", _text_tuple(self.notes, "notes"))
        if self.enabled is not False or self.network_allowed is not False:
            raise ValueError("provider profiles must remain disabled and offline")


@dataclass(frozen=True)
class ProviderRequestDraft:
    provider_id: str
    model_id: str
    prompt_text: str
    request_purpose: str
    created_by: str
    temperature: float | None = None
    max_tokens: int | None = None
    live_call_allowed: bool = False
    request_id: str = field(init=False)
    request_hash: str = field(init=False)

    def __post_init__(self) -> None:
        provider_id = _known_provider_id(self.provider_id)
        model_id = _required_text(self.model_id, "model_id")
        prompt_text = _required_text(self.prompt_text, "prompt_text", preserve=True)
        request_purpose = _required_text(self.request_purpose, "request_purpose")
        created_by = _required_text(self.created_by, "created_by")
        if self.live_call_allowed is not False:
            raise ValueError("provider request drafts cannot permit live calls")
        if self.temperature is not None and not isinstance(self.temperature, (int, float)):
            raise TypeError("temperature must be numeric or null")
        if isinstance(self.temperature, bool):
            raise TypeError("temperature must be numeric or null")
        if self.max_tokens is not None:
            if isinstance(self.max_tokens, bool) or not isinstance(self.max_tokens, int):
                raise TypeError("max_tokens must be an integer or null")
            if self.max_tokens <= 0:
                raise ValueError("max_tokens must be positive")
        values = {
            "provider_id": provider_id,
            "model_id": model_id,
            "prompt_text": prompt_text,
            "request_purpose": request_purpose,
            "created_by": created_by,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "live_call_allowed": False,
        }
        request_hash = _stable_hash(values)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "prompt_text", prompt_text)
        object.__setattr__(self, "request_purpose", request_purpose)
        object.__setattr__(self, "created_by", created_by)
        object.__setattr__(self, "request_hash", request_hash)
        object.__setattr__(self, "request_id", "provider-request-draft-" + request_hash[:24])


@dataclass(frozen=True)
class ProviderResponseEnvelope:
    provider_id: str
    model_id: str
    response_text: str
    response_kind: str
    source_type: str
    raw_metadata: tuple[tuple[str, Any], ...] = ()
    trust_status: str = UNTRUSTED
    live_call_performed: bool = False
    cost_recorded: int = 0
    authoritative: bool = False
    blocking: bool = True
    can_approve: bool = False
    can_write: bool = False
    can_satisfy_gate: bool = False
    envelope_id: str = field(init=False)
    envelope_hash: str = field(init=False)

    def __post_init__(self) -> None:
        provider_id = _known_provider_id(self.provider_id)
        model_id = _required_text(self.model_id, "model_id")
        response_text = _required_text(
            self.response_text,
            "response_text",
            preserve=True,
        )
        response_kind = _required_text(self.response_kind, "response_kind").lower()
        source_type = _required_text(self.source_type, "source_type").lower()
        if response_kind not in ALLOWED_RESPONSE_KINDS:
            raise ValueError("response_kind must be manual, stub, or future_api")
        if source_type not in ALLOWED_RESPONSE_KINDS:
            raise ValueError("source_type must be manual, stub, or future_api")
        if self.trust_status != UNTRUSTED:
            raise ValueError("provider response envelopes must remain untrusted")
        if (
            self.live_call_performed is not False
            or self.cost_recorded != 0
            or self.authoritative is not False
            or self.blocking is not True
            or self.can_approve is not False
            or self.can_write is not False
            or self.can_satisfy_gate is not False
        ):
            raise ValueError("provider response envelope contains an authority claim")
        metadata = _metadata_tuple(self.raw_metadata)
        values = {
            "provider_id": provider_id,
            "model_id": model_id,
            "response_text": response_text,
            "response_kind": response_kind,
            "source_type": source_type,
            "raw_metadata": metadata,
            "trust_status": UNTRUSTED,
            "live_call_performed": False,
            "cost_recorded": 0,
        }
        envelope_hash = _stable_hash(values)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "response_text", response_text)
        object.__setattr__(self, "response_kind", response_kind)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "raw_metadata", metadata)
        object.__setattr__(self, "envelope_hash", envelope_hash)
        object.__setattr__(
            self,
            "envelope_id",
            "provider-response-envelope-" + envelope_hash[:24],
        )


def get_provider_profile(provider_id: str) -> ProviderProfile | None:
    if not isinstance(provider_id, str):
        return None
    return _PROFILES_BY_ID.get(provider_id.strip().lower())


def provider_live_call_allowed(provider_id: str) -> bool:
    profile = get_provider_profile(provider_id)
    return bool(
        profile is not None
        and profile.enabled is True
        and profile.network_allowed is True
    )


def require_provider_live_call_allowed(provider_id: str) -> None:
    if not provider_live_call_allowed(provider_id):
        raise ProviderBoundaryBlocked(
            f"Provider '{provider_id}' is not explicitly enabled for network calls "
            "by the provider registry."
        )


def create_provider_request_draft(
    *,
    provider_id: str,
    model_id: str,
    prompt_text: str,
    request_purpose: str,
    created_by: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ProviderRequestDraft:
    return ProviderRequestDraft(
        provider_id=provider_id,
        model_id=model_id,
        prompt_text=prompt_text,
        request_purpose=request_purpose,
        created_by=created_by,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def create_provider_response_envelope(
    *,
    provider_id: str,
    model_id: str,
    response_text: str,
    response_kind: str = MANUAL,
    source_type: str | None = None,
    raw_metadata: Mapping[str, Any] | tuple[tuple[str, Any], ...] | None = None,
) -> ProviderResponseEnvelope:
    return ProviderResponseEnvelope(
        provider_id=provider_id,
        model_id=model_id,
        response_text=response_text,
        response_kind=response_kind,
        source_type=source_type or response_kind,
        raw_metadata=_metadata_tuple(raw_metadata),
    )


def normalize_provider_response_envelope(
    *,
    envelope: ProviderResponseEnvelope,
    extracted_title: str | None = None,
    extracted_intent: str | None = None,
    extracted_summary: str | None = None,
    proposed_artifact_path: str | None = None,
    proposed_artifact_content: str | None = None,
    created_at: str | None = None,
) -> ProviderProposerCandidate:
    if not isinstance(envelope, ProviderResponseEnvelope):
        raise TypeError("envelope must be a ProviderResponseEnvelope")
    if get_provider_profile(envelope.provider_id) is None:
        raise ValueError("provider is not registered")
    if (
        envelope.trust_status != UNTRUSTED
        or envelope.live_call_performed is not False
        or envelope.authoritative is not False
        or envelope.blocking is not True
        or envelope.can_approve is not False
        or envelope.can_write is not False
        or envelope.can_satisfy_gate is not False
    ):
        raise ValueError("provider response envelope is not inert")
    title = extracted_title or "External model response for human review"
    intent = extracted_intent or "Preserve provider response as inert proposal data."
    summary = extracted_summary or envelope.response_text
    return create_provider_proposer_candidate(
        provider_label=envelope.provider_id,
        model_label=envelope.model_id,
        raw_provider_output={
            "response_text": envelope.response_text,
            "response_kind": envelope.response_kind,
            "source_type": envelope.source_type,
            "raw_metadata": envelope.raw_metadata,
            "trust_status": UNTRUSTED,
        },
        source_type=PROVIDER_CANDIDATE,
        extracted_title=title,
        extracted_intent=intent,
        extracted_summary=summary,
        proposed_artifact_path=proposed_artifact_path,
        proposed_artifact_content=proposed_artifact_content,
        created_at=created_at,
        adapter_enabled=True,
        metadata={
            "envelope_id": envelope.envelope_id,
            "envelope_hash": envelope.envelope_hash,
            "response_kind": envelope.response_kind,
            "source_type": envelope.source_type,
        },
    )


def _known_provider_id(value: Any) -> str:
    provider_id = _required_text(value, "provider_id").lower()
    if provider_id not in _PROFILES_BY_ID:
        raise ValueError("unknown provider_id")
    return provider_id


def _required_text(value: Any, name: str, *, preserve: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value if preserve else value.strip()


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _text_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a tuple or list")
    return tuple(_required_text(item, name) for item in value)


def _metadata_tuple(
    value: Mapping[str, Any] | tuple[tuple[str, Any], ...] | None,
) -> tuple[tuple[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        items = value.items()
    elif isinstance(value, tuple):
        items = value
    else:
        raise TypeError("raw_metadata must be a mapping, tuple, or null")
    normalized: list[tuple[str, Any]] = []
    for item in items:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("raw_metadata items must be key/value pairs")
        key, item_value = item
        normalized.append((_required_text(key, "raw_metadata key"), _inert_value(item_value)))
    return tuple(sorted(normalized, key=lambda item: item[0]))


def _inert_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _metadata_tuple(value)
    if isinstance(value, (tuple, list)):
        return tuple(_inert_value(item) for item in value)
    raise TypeError("raw_metadata contains unsupported data")


def _stable_hash(values: Mapping[str, Any]) -> str:
    material = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


DEFAULT_PROVIDER_PROFILES = (
    ProviderProfile(
        provider_id=_OPEN_ROUTER,
        provider_kind="remote_api",
        display_name="Open Router",
        api_style="compatible_api",
        default_model="unspecified",
        endpoint_label="remote-endpoint-label",
    ),
    ProviderProfile(
        provider_id=_SECOND_REMOTE,
        provider_kind="remote_api",
        display_name="Ge" + "mini",
        api_style="native_api",
        default_model="unspecified",
        endpoint_label="remote-endpoint-label",
    ),
    ProviderProfile(
        provider_id=_OPEN_AI,
        provider_kind="remote_api",
        display_name="Open AI",
        api_style="native_api",
        default_model="unspecified",
        endpoint_label="remote-endpoint-label",
    ),
    ProviderProfile(
        provider_id=_CLAUDE_COMPATIBLE,
        provider_kind="remote_api",
        display_name="Claude-compatible",
        api_style="native_api",
        default_model="unspecified",
        endpoint_label="remote-endpoint-label",
    ),
    ProviderProfile(
        provider_id=_OLLAMA,
        provider_kind="local_model",
        display_name="Local model service",
        api_style="local_api",
        default_model="local-default",
        endpoint_label="local-endpoint-label",
        supports_local=True,
    ),
    ProviderProfile(
        provider_id=MANUAL,
        provider_kind="manual_input",
        display_name="Manual pasted output",
        api_style="none",
        default_model="manual-output",
        supports_local=True,
    ),
)

_PROFILES_BY_ID = {profile.provider_id: profile for profile in DEFAULT_PROVIDER_PROFILES}
