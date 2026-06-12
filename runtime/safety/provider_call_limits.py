from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class ProviderCallLimitExceededError(RuntimeError):
    pass


def _require_nonnegative_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _require_cost_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal string") from exc
    if parsed < Decimal("0"):
        raise ValueError(f"{name} must be nonnegative")
    return value


def _decimal(value: str, name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal string") from exc


@dataclass(frozen=True)
class ProviderCallBudgetConfig:
    max_calls_per_session: int = 0
    max_calls_per_day: int = 0
    max_input_chars_per_request: int = 0
    max_estimated_tokens_per_request: int = 0
    max_estimated_cost_per_session: str = "0"
    max_estimated_cost_per_day: str = "0"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_calls_per_session",
            _require_nonnegative_int("max_calls_per_session", self.max_calls_per_session),
        )
        object.__setattr__(
            self,
            "max_calls_per_day",
            _require_nonnegative_int("max_calls_per_day", self.max_calls_per_day),
        )
        object.__setattr__(
            self,
            "max_input_chars_per_request",
            _require_nonnegative_int("max_input_chars_per_request", self.max_input_chars_per_request),
        )
        object.__setattr__(
            self,
            "max_estimated_tokens_per_request",
            _require_nonnegative_int(
                "max_estimated_tokens_per_request",
                self.max_estimated_tokens_per_request,
            ),
        )
        object.__setattr__(
            self,
            "max_estimated_cost_per_session",
            _require_cost_text("max_estimated_cost_per_session", self.max_estimated_cost_per_session),
        )
        object.__setattr__(
            self,
            "max_estimated_cost_per_day",
            _require_cost_text("max_estimated_cost_per_day", self.max_estimated_cost_per_day),
        )


@dataclass(frozen=True)
class ProviderCallSessionState:
    session_id: str
    calls_attempted: int = 0
    calls_blocked: int = 0
    calls_allowed: int = 0
    estimated_cost_total: str = "0"
    day_key: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("session_id must be a nonempty string")
        object.__setattr__(self, "calls_attempted", _require_nonnegative_int("calls_attempted", self.calls_attempted))
        object.__setattr__(self, "calls_blocked", _require_nonnegative_int("calls_blocked", self.calls_blocked))
        object.__setattr__(self, "calls_allowed", _require_nonnegative_int("calls_allowed", self.calls_allowed))
        object.__setattr__(self, "estimated_cost_total", _require_cost_text("estimated_cost_total", self.estimated_cost_total))
        if not isinstance(self.day_key, str):
            raise TypeError("day_key must be a string")


def default_provider_call_budget_config() -> ProviderCallBudgetConfig:
    return ProviderCallBudgetConfig()


def estimate_tokens_from_chars(input_text: str) -> int:
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a string")
    return max(1, (len(input_text) + 3) // 4)


def assert_call_within_limits(
    config: ProviderCallBudgetConfig,
    state: ProviderCallSessionState,
    *,
    input_chars: int,
    estimated_tokens: int,
    estimated_cost: str,
) -> None:
    if not isinstance(config, ProviderCallBudgetConfig):
        raise TypeError("config must be a ProviderCallBudgetConfig")
    if not isinstance(state, ProviderCallSessionState):
        raise TypeError("state must be a ProviderCallSessionState")
    input_char_count = _require_nonnegative_int("input_chars", input_chars)
    token_count = _require_nonnegative_int("estimated_tokens", estimated_tokens)
    request_cost = _decimal(_require_cost_text("estimated_cost", estimated_cost), "estimated_cost")
    current_cost = _decimal(state.estimated_cost_total, "estimated_cost_total")

    if config.max_calls_per_session <= 0:
        raise ProviderCallLimitExceededError("provider session call ceiling is zero")
    if config.max_calls_per_day <= 0:
        raise ProviderCallLimitExceededError("provider day call ceiling is zero")
    if config.max_input_chars_per_request <= 0:
        raise ProviderCallLimitExceededError("provider input character ceiling is zero")
    if config.max_estimated_tokens_per_request <= 0:
        raise ProviderCallLimitExceededError("provider token ceiling is zero")
    if _decimal(config.max_estimated_cost_per_session, "max_estimated_cost_per_session") <= Decimal("0"):
        raise ProviderCallLimitExceededError("provider session cost ceiling is zero")
    if _decimal(config.max_estimated_cost_per_day, "max_estimated_cost_per_day") <= Decimal("0"):
        raise ProviderCallLimitExceededError("provider day cost ceiling is zero")
    if state.calls_attempted >= config.max_calls_per_session:
        raise ProviderCallLimitExceededError("provider session call ceiling exceeded")
    if state.calls_attempted >= config.max_calls_per_day:
        raise ProviderCallLimitExceededError("provider day call ceiling exceeded")
    if input_char_count > config.max_input_chars_per_request:
        raise ProviderCallLimitExceededError("provider input character ceiling exceeded")
    if token_count > config.max_estimated_tokens_per_request:
        raise ProviderCallLimitExceededError("provider token ceiling exceeded")
    if current_cost + request_cost > _decimal(config.max_estimated_cost_per_session, "max_estimated_cost_per_session"):
        raise ProviderCallLimitExceededError("provider session cost ceiling exceeded")
    if current_cost + request_cost > _decimal(config.max_estimated_cost_per_day, "max_estimated_cost_per_day"):
        raise ProviderCallLimitExceededError("provider day cost ceiling exceeded")


def record_blocked_call(state: ProviderCallSessionState) -> ProviderCallSessionState:
    if not isinstance(state, ProviderCallSessionState):
        raise TypeError("state must be a ProviderCallSessionState")
    return ProviderCallSessionState(
        session_id=state.session_id,
        calls_attempted=state.calls_attempted + 1,
        calls_blocked=state.calls_blocked + 1,
        calls_allowed=state.calls_allowed,
        estimated_cost_total=state.estimated_cost_total,
        day_key=state.day_key,
    )
