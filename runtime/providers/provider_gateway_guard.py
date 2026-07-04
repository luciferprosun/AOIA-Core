from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION = "1A"

PROVIDER_GATEWAY_GUARD_ALLOWED_METADATA_ONLY = "ALLOW_METADATA_ONLY"
PROVIDER_GATEWAY_GUARD_BLOCKED = "BLOCKED"

PROVIDER_GATEWAY_GUARD_ALLOWED_REVIEW_ONLY = "PROVIDER_GATEWAY_GUARD_ALLOWED_REVIEW_ONLY"
PROVIDER_GATEWAY_GUARD_BLOCKED_MALFORMED_EVIDENCE = "PROVIDER_GATEWAY_GUARD_BLOCKED_MALFORMED_EVIDENCE"
PROVIDER_GATEWAY_GUARD_BLOCKED_STALE_EVIDENCE = "PROVIDER_GATEWAY_GUARD_BLOCKED_STALE_EVIDENCE"
PROVIDER_GATEWAY_GUARD_BLOCKED_IDENTITY_MISMATCH = "PROVIDER_GATEWAY_GUARD_BLOCKED_IDENTITY_MISMATCH"
PROVIDER_GATEWAY_GUARD_BLOCKED_CIRCUIT_OPEN = "PROVIDER_GATEWAY_GUARD_BLOCKED_CIRCUIT_OPEN"
PROVIDER_GATEWAY_GUARD_BLOCKED_FAILURE_THRESHOLD = "PROVIDER_GATEWAY_GUARD_BLOCKED_FAILURE_THRESHOLD"
PROVIDER_GATEWAY_GUARD_BLOCKED_RATE_LIMIT = "PROVIDER_GATEWAY_GUARD_BLOCKED_RATE_LIMIT"

_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class ProviderGatewayGuardConfig:
    schema_version: str
    max_attempts_per_window: int
    window_seconds: int
    failure_threshold: int
    cooldown_seconds: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        if self.schema_version != PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION:
            raise ValueError("unsupported provider gateway guard schema version")
        object.__setattr__(self, "max_attempts_per_window", _positive_int("max_attempts_per_window", self.max_attempts_per_window))
        object.__setattr__(self, "window_seconds", _positive_int("window_seconds", self.window_seconds))
        object.__setattr__(self, "failure_threshold", _positive_int("failure_threshold", self.failure_threshold))
        object.__setattr__(self, "cooldown_seconds", _positive_int("cooldown_seconds", self.cooldown_seconds))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_attempts_per_window": self.max_attempts_per_window,
            "window_seconds": self.window_seconds,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
        }


@dataclass(frozen=True)
class ProviderGatewayGuardState:
    schema_version: str
    provider_id: str
    operation_purpose: str
    consecutive_failures: int
    circuit_opened_at_tick: int | None
    recent_attempt_ticks: tuple[int, ...]
    state_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        if self.schema_version != PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION:
            raise ValueError("unsupported provider gateway guard state schema version")
        object.__setattr__(self, "provider_id", _required_text("provider_id", self.provider_id))
        object.__setattr__(self, "operation_purpose", _required_text("operation_purpose", self.operation_purpose))
        object.__setattr__(self, "consecutive_failures", _nonnegative_int("consecutive_failures", self.consecutive_failures))
        if self.circuit_opened_at_tick is not None:
            object.__setattr__(self, "circuit_opened_at_tick", _nonnegative_int("circuit_opened_at_tick", self.circuit_opened_at_tick))
        ticks = tuple(sorted(_nonnegative_int("recent_attempt_tick", item) for item in self.recent_attempt_ticks))
        object.__setattr__(self, "recent_attempt_ticks", ticks)
        if not _sha256_like(self.state_hash):
            raise ValueError("state_hash must be a sha256 hex digest")
        if self.state_hash != compute_provider_gateway_guard_hash(_state_hash_material(self)):
            raise ValueError("state_hash does not match provider gateway guard state evidence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "operation_purpose": self.operation_purpose,
            "consecutive_failures": self.consecutive_failures,
            "circuit_opened_at_tick": self.circuit_opened_at_tick,
            "recent_attempt_ticks": self.recent_attempt_ticks,
            "state_hash": self.state_hash,
        }


@dataclass(frozen=True)
class ProviderGatewayGuardResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    provider_id: str | None
    operation_purpose: str | None
    current_tick: int | None
    attempts_in_window: int
    next_allowed_tick: int | None
    guard_hash: str
    human_review_required: bool = True
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "can_approve", False)
        object.__setattr__(self, "can_execute", False)
        object.__setattr__(self, "can_write", False)
        object.__setattr__(self, "can_push", False)
        object.__setattr__(self, "can_call_provider", False)
        object.__setattr__(self, "can_change_gate", False)
        object.__setattr__(self, "gate_satisfied", False)
        if not _sha256_like(self.guard_hash):
            raise ValueError("guard_hash must be a sha256 hex digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "provider_id": self.provider_id,
            "operation_purpose": self.operation_purpose,
            "current_tick": self.current_tick,
            "attempts_in_window": self.attempts_in_window,
            "next_allowed_tick": self.next_allowed_tick,
            "guard_hash": self.guard_hash,
            "human_review_required": True,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
        }


def default_provider_gateway_guard_config() -> ProviderGatewayGuardConfig:
    return ProviderGatewayGuardConfig(
        schema_version=PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION,
        max_attempts_per_window=1,
        window_seconds=60,
        failure_threshold=1,
        cooldown_seconds=300,
    )


def create_provider_gateway_guard_state(
    *,
    provider_id: str,
    operation_purpose: str,
    consecutive_failures: int = 0,
    circuit_opened_at_tick: int | None = None,
    recent_attempt_ticks: tuple[int, ...] = (),
) -> ProviderGatewayGuardState:
    material = {
        "schema_version": PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION,
        "provider_id": _required_text("provider_id", provider_id),
        "operation_purpose": _required_text("operation_purpose", operation_purpose),
        "consecutive_failures": _nonnegative_int("consecutive_failures", consecutive_failures),
        "circuit_opened_at_tick": None if circuit_opened_at_tick is None else _nonnegative_int("circuit_opened_at_tick", circuit_opened_at_tick),
        "recent_attempt_ticks": tuple(sorted(_nonnegative_int("recent_attempt_tick", item) for item in recent_attempt_ticks)),
    }
    return ProviderGatewayGuardState(state_hash=compute_provider_gateway_guard_hash(material), **material)


def evaluate_provider_gateway_guard(
    *,
    config: ProviderGatewayGuardConfig | Mapping[str, Any],
    state: ProviderGatewayGuardState | Mapping[str, Any],
    provider_id: str,
    operation_purpose: str,
    current_tick: int,
) -> ProviderGatewayGuardResult:
    try:
        guard_config = _coerce_config(config)
        guard_state = _coerce_state(state)
        provider = _required_text("provider_id", provider_id)
        purpose = _required_text("operation_purpose", operation_purpose)
        tick = _nonnegative_int("current_tick", current_tick)
    except (TypeError, ValueError):
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_MALFORMED_EVIDENCE,),
        )

    if guard_state.provider_id != provider or guard_state.operation_purpose != purpose:
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_IDENTITY_MISMATCH,),
            provider_id=provider,
            operation_purpose=purpose,
            current_tick=tick,
        )

    if any(item > tick for item in guard_state.recent_attempt_ticks):
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_STALE_EVIDENCE,),
            provider_id=provider,
            operation_purpose=purpose,
            current_tick=tick,
        )

    if guard_state.circuit_opened_at_tick is not None and guard_state.circuit_opened_at_tick > tick:
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_STALE_EVIDENCE,),
            provider_id=provider,
            operation_purpose=purpose,
            current_tick=tick,
        )

    next_allowed_tick = _next_allowed_tick(guard_config, guard_state)
    if next_allowed_tick is not None and tick < next_allowed_tick:
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_CIRCUIT_OPEN,),
            provider_id=provider,
            operation_purpose=purpose,
            current_tick=tick,
            attempts_in_window=_attempts_in_window(guard_state, guard_config, tick),
            next_allowed_tick=next_allowed_tick,
        )

    if guard_state.consecutive_failures >= guard_config.failure_threshold and guard_state.circuit_opened_at_tick is None:
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_FAILURE_THRESHOLD,),
            provider_id=provider,
            operation_purpose=purpose,
            current_tick=tick,
            attempts_in_window=_attempts_in_window(guard_state, guard_config, tick),
        )

    attempts = _attempts_in_window(guard_state, guard_config, tick)
    if attempts >= guard_config.max_attempts_per_window:
        return _result(
            status=PROVIDER_GATEWAY_GUARD_BLOCKED,
            reason_codes=(PROVIDER_GATEWAY_GUARD_BLOCKED_RATE_LIMIT,),
            provider_id=provider,
            operation_purpose=purpose,
            current_tick=tick,
            attempts_in_window=attempts,
        )

    return _result(
        status=PROVIDER_GATEWAY_GUARD_ALLOWED_METADATA_ONLY,
        reason_codes=(PROVIDER_GATEWAY_GUARD_ALLOWED_REVIEW_ONLY,),
        provider_id=provider,
        operation_purpose=purpose,
        current_tick=tick,
        attempts_in_window=attempts,
    )


def compute_provider_gateway_guard_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _result(
    *,
    status: str,
    reason_codes: tuple[str, ...],
    provider_id: str | None = None,
    operation_purpose: str | None = None,
    current_tick: int | None = None,
    attempts_in_window: int = 0,
    next_allowed_tick: int | None = None,
) -> ProviderGatewayGuardResult:
    material = {
        "schema_version": PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "provider_id": provider_id,
        "operation_purpose": operation_purpose,
        "current_tick": current_tick,
        "attempts_in_window": attempts_in_window,
        "next_allowed_tick": next_allowed_tick,
        "human_review_required": True,
    }
    return ProviderGatewayGuardResult(
        schema_version=PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        provider_id=provider_id,
        operation_purpose=operation_purpose,
        current_tick=current_tick,
        attempts_in_window=attempts_in_window,
        next_allowed_tick=next_allowed_tick,
        guard_hash=compute_provider_gateway_guard_hash(material),
    )


def _coerce_config(value: ProviderGatewayGuardConfig | Mapping[str, Any]) -> ProviderGatewayGuardConfig:
    if isinstance(value, ProviderGatewayGuardConfig):
        return value
    if isinstance(value, Mapping):
        return ProviderGatewayGuardConfig(**dict(value))
    raise TypeError("config must be provider gateway guard config evidence")


def _coerce_state(value: ProviderGatewayGuardState | Mapping[str, Any]) -> ProviderGatewayGuardState:
    if isinstance(value, ProviderGatewayGuardState):
        return value
    if isinstance(value, Mapping):
        return ProviderGatewayGuardState(**dict(value))
    raise TypeError("state must be provider gateway guard state evidence")


def _state_hash_material(state: ProviderGatewayGuardState) -> dict[str, Any]:
    material = state.to_dict()
    material.pop("state_hash", None)
    return material


def _attempts_in_window(state: ProviderGatewayGuardState, config: ProviderGatewayGuardConfig, current_tick: int) -> int:
    window_start = max(0, current_tick - config.window_seconds)
    return sum(1 for item in state.recent_attempt_ticks if window_start <= item <= current_tick)


def _next_allowed_tick(config: ProviderGatewayGuardConfig, state: ProviderGatewayGuardState) -> int | None:
    if state.circuit_opened_at_tick is None:
        return None
    return state.circuit_opened_at_tick + config.cooldown_seconds


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())
