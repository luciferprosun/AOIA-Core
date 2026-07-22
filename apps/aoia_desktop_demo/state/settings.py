"""Non-secret local configuration for the desktop demo.

The API key is never part of this module's persisted state. It is held
only by ``SessionSecrets`` (in-memory, session-only) in ``app.py``.
"""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..providers.openrouter import DEFAULT_APP_TITLE, OPENROUTER_BASE_URL

CONFIG_DIR = Path.home() / ".config" / "aoia-control-chat-demo"
CONFIG_PATH = CONFIG_DIR / "config.json"
CONFIG_SCHEMA_VERSION = 2

# Provider types available to the form. This catalog does not represent a
# configured connection and never makes a route active by itself.
PROVIDER_CATALOG = ("openrouter",)
_MODEL_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._:-]*\Z")

_ALLOWED_KEYS = {
    "provider",
    "api_base_url",
    "app_title",
    "timeout_seconds",
    "manual_model_id",
    "selected_model_id",
    "max_response_tokens",
    "knowledge_profile_id",
    "window_width",
    "window_height",
    "observer_slots",
    "pre_delivery_critical_loop_enabled",
}

_OBSERVER_ROLES = {
    "Logic & Claims",
    "Safety & Authority",
    "Evidence & Consistency",
}
_OBSERVER_KEYS = {"enabled", "role", "provider_id", "model_id"}


@dataclass
class DemoSettings:
    provider: str = ""
    api_base_url: str = ""
    app_title: str = DEFAULT_APP_TITLE
    timeout_seconds: float = 30.0
    manual_model_id: str = ""
    selected_model_id: str = ""
    max_response_tokens: int | None = None
    knowledge_profile_id: str = "none"
    window_width: int = 1100
    window_height: int = 720
    observer_slots: list[dict[str, object]] = field(default_factory=list)
    pre_delivery_critical_loop_enabled: bool = False

    def to_json_dict(self) -> dict:
        data = asdict(self)
        assert set(data) <= _ALLOWED_KEYS, "attempted to persist an unexpected settings field"
        return data

    def has_configured_provider_connection(self) -> bool:
        """Whether the non-secret portion identifies one supported connection."""
        return (
            self.provider == "openrouter"
            and self.api_base_url.rstrip("/") == OPENROUTER_BASE_URL
            and bool(_MODEL_ID_PATTERN.fullmatch(self.manual_model_id.strip() or self.selected_model_id.strip()))
        )

    def configured_provider_ids(self) -> tuple[str, ...]:
        return (self.provider,) if self.has_configured_provider_connection() else ()


def load_settings() -> DemoSettings:
    """Load explicit non-secret settings and fail closed on stale records.

    Version-1 files have no operator-created marker and may contain demo
    defaults. They are removed once rather than being restored on each start.
    """
    if not CONFIG_PATH.exists():
        return DemoSettings()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DemoSettings()
    if not isinstance(raw, dict):
        return DemoSettings()

    if raw.get("schema_version") != CONFIG_SCHEMA_VERSION or raw.get("operator_created") is not True:
        clear_settings()
        return DemoSettings()

    defaults = DemoSettings()
    filtered = {key: value for key, value in raw.items() if key in _ALLOWED_KEYS}
    if not _settings_fields_are_well_formed(filtered):
        return defaults
    try:
        return DemoSettings(**{**asdict(defaults), **filtered})
    except TypeError:
        return defaults


def save_settings(settings: DemoSettings) -> None:
    """Persist non-secret settings only. Never call this with a dict that
    contains an API key field."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, stat.S_IRWXU)  # 0700, best-effort
    except OSError:
        pass
    payload = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "operator_created": True,
        **settings.to_json_dict(),
    }
    CONFIG_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 0600, best-effort
    except OSError:
        pass


def clear_settings() -> None:
    """Remove the local non-secret config file, if present."""
    try:
        CONFIG_PATH.unlink()
    except FileNotFoundError:
        pass


@dataclass
class SessionSecrets:
    """In-memory-only holder for the API key. Never serialized, never logged.

    ``source`` records where the key came from purely for display purposes
    (currently "session-entry") — never the key value itself.
    """

    api_key: str | None = field(default=None, repr=False)
    source: str = "none"

    def set_for_session(self, api_key: str) -> None:
        self.api_key = api_key or None
        self.source = "session-entry" if api_key else "none"

    def clear(self) -> None:
        self.api_key = None
        self.source = "none"

    def __repr__(self) -> str:  # defensive: never let a stray print leak the key
        return f"SessionSecrets(source={self.source!r}, has_key={bool(self.api_key)})"


def _settings_fields_are_well_formed(values: dict[str, object]) -> bool:
    """Reject malformed persisted state before it can look active."""
    string_fields = {
        "provider",
        "api_base_url",
        "app_title",
        "manual_model_id",
        "selected_model_id",
        "knowledge_profile_id",
    }
    if any(key in values and not isinstance(values[key], str) for key in string_fields):
        return False
    if "provider" in values and values["provider"].strip().casefold() not in {"", *PROVIDER_CATALOG}:
        return False
    if "timeout_seconds" in values and (
        isinstance(values["timeout_seconds"], bool) or not isinstance(values["timeout_seconds"], (int, float))
    ):
        return False
    if "max_response_tokens" in values and values["max_response_tokens"] is not None and (
        isinstance(values["max_response_tokens"], bool) or not isinstance(values["max_response_tokens"], int)
    ):
        return False
    for key in ("window_width", "window_height"):
        if key in values and (isinstance(values[key], bool) or not isinstance(values[key], int)):
            return False
    if "pre_delivery_critical_loop_enabled" in values and not isinstance(
        values["pre_delivery_critical_loop_enabled"], bool
    ):
        return False
    observer_slots = values.get("observer_slots", [])
    if not isinstance(observer_slots, list) or len(observer_slots) not in {0, 3}:
        return False
    for slot in observer_slots:
        if not isinstance(slot, dict) or set(slot) != _OBSERVER_KEYS:
            return False
        if not isinstance(slot["enabled"], bool):
            return False
        if not isinstance(slot["role"], str) or slot["role"] not in _OBSERVER_ROLES:
            return False
        if not isinstance(slot["provider_id"], str) or slot["provider_id"].casefold() not in {"", *PROVIDER_CATALOG}:
            return False
        if not isinstance(slot["model_id"], str):
            return False
        if slot["model_id"] and not _MODEL_ID_PATTERN.fullmatch(slot["model_id"]):
            return False
    return True
