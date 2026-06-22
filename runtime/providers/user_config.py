from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from runtime.providers.contracts import normalize_provider_id


_CONFIG_FIELDS = {
    "selected_provider_id",
    "selected_model_id",
    "default_max_tokens",
    "default_mode",
    "live_enabled",
}
_SENSITIVE_FIELD_PARTS = (
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "password",
    "secret",
    "token",
)


@dataclass(frozen=True)
class ProviderSelectorConfig:
    selected_provider_id: str
    selected_model_id: str
    default_max_tokens: int = 256
    default_mode: str = "dry_run"
    live_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "selected_provider_id",
            normalize_provider_id(self.selected_provider_id),
        )
        if not isinstance(self.selected_model_id, str):
            raise ValueError("selected_model_id must be a string")
        object.__setattr__(self, "selected_model_id", self.selected_model_id.strip())
        if (
            isinstance(self.default_max_tokens, bool)
            or not isinstance(self.default_max_tokens, int)
            or self.default_max_tokens <= 0
            or self.default_max_tokens > 4096
        ):
            raise ValueError("default_max_tokens must be between 1 and 4096")
        if self.default_mode != "dry_run":
            raise ValueError("selector config default_mode must remain dry_run")
        if self.live_enabled is not False:
            raise ValueError("selector config cannot enable live provider calls")

    def to_dict(self) -> dict[str, str | int | bool]:
        return {
            "selected_provider_id": self.selected_provider_id,
            "selected_model_id": self.selected_model_id,
            "default_max_tokens": self.default_max_tokens,
            "default_mode": "dry_run",
            "live_enabled": False,
        }


def provider_selector_config_from_mapping(value: object) -> ProviderSelectorConfig:
    if not isinstance(value, Mapping):
        raise ValueError("selector config must be a mapping")
    keys = {str(key) for key in value}
    if any(
        part in key.casefold()
        for key in keys
        for part in _SENSITIVE_FIELD_PARTS
    ):
        raise ValueError("selector config cannot contain secret or credential fields")
    if not keys.issubset(_CONFIG_FIELDS):
        raise ValueError("selector config contains unsupported fields")
    if "selected_provider_id" not in value or "selected_model_id" not in value:
        raise ValueError("selector config requires provider and model identifiers")
    return ProviderSelectorConfig(
        selected_provider_id=value["selected_provider_id"],  # type: ignore[arg-type]
        selected_model_id=value["selected_model_id"],  # type: ignore[arg-type]
        default_max_tokens=value.get("default_max_tokens", 256),  # type: ignore[arg-type]
        default_mode=value.get("default_mode", "dry_run"),  # type: ignore[arg-type]
        live_enabled=value.get("live_enabled", False),  # type: ignore[arg-type]
    )
