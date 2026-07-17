"""Non-secret local configuration for the desktop demo.

The API key is never part of this module's persisted state. It is held
only by ``SessionSecrets`` (in-memory, session-only) in ``app.py``.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..providers.openrouter import DEFAULT_APP_TITLE, OPENROUTER_BASE_URL

CONFIG_DIR = Path.home() / ".config" / "aoia-control-chat-demo"
CONFIG_PATH = CONFIG_DIR / "config.json"

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
}


@dataclass
class DemoSettings:
    provider: str = "openrouter"
    api_base_url: str = OPENROUTER_BASE_URL
    app_title: str = DEFAULT_APP_TITLE
    timeout_seconds: float = 30.0
    manual_model_id: str = ""
    selected_model_id: str = ""
    max_response_tokens: int | None = None
    knowledge_profile_id: str = "none"
    window_width: int = 1100
    window_height: int = 720

    def to_json_dict(self) -> dict:
        data = asdict(self)
        assert set(data) <= _ALLOWED_KEYS, "attempted to persist an unexpected settings field"
        return data


def load_settings() -> DemoSettings:
    """Load non-secret settings. Returns defaults on any error or absence."""
    if not CONFIG_PATH.exists():
        return DemoSettings()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DemoSettings()
    if not isinstance(raw, dict):
        return DemoSettings()

    defaults = DemoSettings()
    filtered = {key: value for key, value in raw.items() if key in _ALLOWED_KEYS}
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
    payload = settings.to_json_dict()
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
    ("environment" or "session-entry") — never the key value itself.
    """

    api_key: str | None = field(default=None, repr=False)
    source: str = "none"

    @classmethod
    def from_environment(cls) -> "SessionSecrets":
        env_key = os.environ.get("OPENROUTER_API_KEY")
        if env_key:
            return cls(api_key=env_key, source="environment")
        return cls(api_key=None, source="none")

    def set_for_session(self, api_key: str) -> None:
        self.api_key = api_key or None
        self.source = "session-entry" if api_key else "none"

    def clear(self) -> None:
        self.api_key = None
        self.source = "none"

    def __repr__(self) -> str:  # defensive: never let a stray print leak the key
        return f"SessionSecrets(source={self.source!r}, has_key={bool(self.api_key)})"
