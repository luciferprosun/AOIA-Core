from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


class ProviderGatewayBlockedError(RuntimeError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_nonnegative_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


@dataclass(frozen=True)
class ProviderGatewayConfig:
    enabled: bool = False
    provider_name: str = ""
    model_name: str = ""
    max_calls_per_session: int = 0
    max_input_chars: int = 0
    allow_network: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled", bool(self.enabled))
        object.__setattr__(self, "provider_name", _require_text("provider_name", self.provider_name))
        object.__setattr__(self, "model_name", _require_text("model_name", self.model_name))
        object.__setattr__(
            self,
            "max_calls_per_session",
            _require_nonnegative_int("max_calls_per_session", self.max_calls_per_session),
        )
        object.__setattr__(
            self,
            "max_input_chars",
            _require_nonnegative_int("max_input_chars", self.max_input_chars),
        )
        object.__setattr__(self, "allow_network", bool(self.allow_network))


@dataclass(frozen=True)
class ProviderGatewayAttempt:
    attempted: bool
    blocked: bool
    reason: str
    provider_name: str
    model_name: str
    request_hash: str
    audit_event_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempted", bool(self.attempted))
        object.__setattr__(self, "blocked", True)
        object.__setattr__(self, "reason", _require_text("reason", self.reason))
        object.__setattr__(self, "provider_name", _require_text("provider_name", self.provider_name))
        object.__setattr__(self, "model_name", _require_text("model_name", self.model_name))
        object.__setattr__(self, "request_hash", _require_text("request_hash", self.request_hash))
        object.__setattr__(self, "audit_event_id", _require_text("audit_event_id", self.audit_event_id))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def provider_gateway_block_reason(config: ProviderGatewayConfig) -> str:
    if not isinstance(config, ProviderGatewayConfig):
        raise TypeError("config must be a ProviderGatewayConfig")
    if not config.enabled:
        return "provider gateway disabled by default"
    if not config.allow_network:
        return "provider gateway network access disabled"
    if config.max_calls_per_session <= 0:
        return "provider gateway call ceiling is zero"
    return "provider gateway live calls unavailable in M2-B1"


def assert_provider_gateway_blocked(config: ProviderGatewayConfig) -> None:
    raise ProviderGatewayBlockedError(provider_gateway_block_reason(config))


def build_blocked_provider_attempt(
    *,
    request_text: str,
    config: ProviderGatewayConfig | None = None,
    audit_event_id: str | None = None,
    reason: str | None = None,
) -> ProviderGatewayAttempt:
    gateway_config = config or ProviderGatewayConfig()
    request_value = _require_text("request_text", request_text)
    reason_value = reason or provider_gateway_block_reason(gateway_config)
    audit_id = audit_event_id or "provider-gateway-" + _hash_text(
        "\n".join(
            [
                gateway_config.provider_name,
                gateway_config.model_name,
                _hash_text(request_value),
                reason_value,
                _utc_now_iso(),
            ]
        )
    )[:24]
    return ProviderGatewayAttempt(
        attempted=True,
        blocked=True,
        reason=reason_value,
        provider_name=gateway_config.provider_name,
        model_name=gateway_config.model_name,
        request_hash=_hash_text(request_value),
        audit_event_id=audit_id,
    )


def request_provider_critique_blocked(
    *,
    request_text: str,
    config: ProviderGatewayConfig | None = None,
    raise_on_block: bool = False,
) -> ProviderGatewayAttempt:
    gateway_config = config or ProviderGatewayConfig()
    attempt = build_blocked_provider_attempt(request_text=request_text, config=gateway_config)
    if raise_on_block:
        raise ProviderGatewayBlockedError(attempt.reason)
    return attempt
