from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


NOT_CANONICAL = "NOT_CANONICAL"
_REDACTED = "[REDACTED_SECRET]"
_MAX_PROMPT_SUMMARY_CHARS = 240

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AIza[0-9A-Za-z_\-]{8,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{8,}"),
    re.compile(r"\bOPENAI_API_KEY\s*=\s*[^\s,;]+"),
    re.compile(r"\bGEMINI_API_KEY\s*=\s*[^\s,;]+"),
    re.compile(r"\bANTHROPIC_API_KEY\s*=\s*[^\s,;]+"),
    re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]{20,}"),
    re.compile(r"\b[A-Za-z0-9_\-]{32,}\.[A-Za-z0-9_\-]{12,}\.[A-Za-z0-9_\-]{12,}\b"),
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(_REDACTED, redacted)
    return redacted


def summarize_prompt(text: str, max_chars: int = _MAX_PROMPT_SUMMARY_CHARS) -> str:
    normalized = " ".join(redact_secrets(text).split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in _SAFETY_FIELD_NAMES:
            sanitized[f"metadata_{key}"] = _sanitize_metadata_value(value)
        else:
            sanitized[str(key)] = _sanitize_metadata_value(value)
    return sanitized


def _sanitize_metadata_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return _sanitize_metadata({str(k): v for k, v in value.items()})
    if isinstance(value, list):
        return [_sanitize_metadata_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_metadata_value(item) for item in value)
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return redact_secrets(str(value))


_SAFETY_FIELD_NAMES = {
    "untrusted",
    "human_reviewed",
    "canonical_status",
    "action_authorized",
    "execution_permitted",
    "provider_call_permitted",
    "blocked",
}


@dataclass(frozen=True)
class ProviderCritiqueRecord:
    record_id: str
    created_at_utc: str
    source_provider: str
    model_name: str
    request_hash: str
    response_hash: str
    prompt_summary: str
    critique_text: str
    untrusted: bool = True
    human_reviewed: bool = False
    canonical_status: str = NOT_CANONICAL
    action_authorized: bool = False
    execution_permitted: bool = False
    provider_call_permitted: bool = False
    blocked: bool = True
    block_reason: str = "provider calls are disabled"
    cost_ceiling_state: str = "BLOCKED_MAX_CALLS_0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.untrusted is not True:
            object.__setattr__(self, "untrusted", True)
        if self.human_reviewed is not False:
            object.__setattr__(self, "human_reviewed", False)
        if self.canonical_status != NOT_CANONICAL:
            object.__setattr__(self, "canonical_status", NOT_CANONICAL)
        if self.action_authorized is not False:
            object.__setattr__(self, "action_authorized", False)
        if self.execution_permitted is not False:
            object.__setattr__(self, "execution_permitted", False)
        if self.provider_call_permitted is not False:
            object.__setattr__(self, "provider_call_permitted", False)
        if self.blocked is not True:
            object.__setattr__(self, "blocked", True)

        object.__setattr__(self, "source_provider", redact_secrets(self.source_provider))
        object.__setattr__(self, "model_name", redact_secrets(self.model_name))
        object.__setattr__(self, "prompt_summary", summarize_prompt(self.prompt_summary))
        object.__setattr__(self, "critique_text", redact_secrets(self.critique_text))
        object.__setattr__(self, "block_reason", redact_secrets(self.block_reason))
        object.__setattr__(self, "cost_ceiling_state", redact_secrets(self.cost_ceiling_state))
        object.__setattr__(self, "metadata", _sanitize_metadata(self.metadata))

    @classmethod
    def blocked_attempt(
        cls,
        *,
        source_provider: str,
        model_name: str,
        prompt_text: str,
        block_reason: str,
        cost_ceiling_state: str,
        metadata: dict[str, Any] | None = None,
    ) -> "ProviderCritiqueRecord":
        return cls(
            record_id=f"provider-critic-{uuid4().hex}",
            created_at_utc=utc_now_iso(),
            source_provider=source_provider,
            model_name=model_name,
            request_hash=hash_text(prompt_text),
            response_hash=hash_text(""),
            prompt_summary=summarize_prompt(prompt_text),
            critique_text="",
            blocked=True,
            block_reason=block_reason,
            cost_ceiling_state=cost_ceiling_state,
            metadata=metadata or {},
        )

    @classmethod
    def from_untrusted_output(
        cls,
        *,
        source_provider: str,
        model_name: str,
        prompt_text: str,
        critique_text: str,
        metadata: dict[str, Any] | None = None,
        **attempted_flags: Any,
    ) -> "ProviderCritiqueRecord":
        init_payload: dict[str, Any] = {
            "record_id": f"provider-critic-{uuid4().hex}",
            "created_at_utc": utc_now_iso(),
            "source_provider": source_provider,
            "model_name": model_name,
            "request_hash": hash_text(prompt_text),
            "response_hash": hash_text(critique_text),
            "prompt_summary": summarize_prompt(prompt_text),
            "critique_text": redact_secrets(critique_text),
            "blocked": True,
            "block_reason": "provider output stored as untrusted local review artifact",
            "cost_ceiling_state": "INERT_RECORD_ONLY",
            "metadata": {**(metadata or {}), "attempted_flags": attempted_flags},
        }
        init_payload.update(attempted_flags)
        return cls(**init_payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderCritiqueRecord":
        allowed = {
            "record_id",
            "created_at_utc",
            "source_provider",
            "model_name",
            "request_hash",
            "response_hash",
            "prompt_summary",
            "critique_text",
            "untrusted",
            "human_reviewed",
            "canonical_status",
            "action_authorized",
            "execution_permitted",
            "provider_call_permitted",
            "blocked",
            "block_reason",
            "cost_ceiling_state",
            "metadata",
        }
        return cls(**{key: value for key, value in payload.items() if key in allowed})


def assert_untrusted_record(record: ProviderCritiqueRecord) -> None:
    if record.untrusted is not True:
        raise ValueError("provider critique record must remain untrusted")


def assert_not_canonical(record: ProviderCritiqueRecord) -> None:
    if record.canonical_status != NOT_CANONICAL:
        raise ValueError("provider critique record must remain non-canonical")


def assert_no_action_authority(record: ProviderCritiqueRecord) -> None:
    if record.action_authorized or record.execution_permitted:
        raise ValueError("provider critique record must not authorize actions or execution")
