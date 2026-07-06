from __future__ import annotations

import os
from pathlib import Path


_GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
_OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
_KIMI_API_KEY_ENV = "KIMI_API_KEY"
_MOONSHOT_API_KEY_ENV = "MOONSHOT_API_KEY"
_KIMI_API_KEY_FILE_ENV = "KIMI_API_KEY_FILE"
_DEFAULT_KIMI_KEY_FILE_PARTS = ("Desktop", "API TOKENy", "kimi kodex")


def _clean_key(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _get_gemini_api_key() -> str | None:
    return _clean_key(os.environ.get(_GEMINI_API_KEY_ENV))


def _get_openrouter_api_key() -> str | None:
    return _clean_key(os.environ.get(_OPENROUTER_API_KEY_ENV))


def _get_kimi_api_key() -> str | None:
    env_key = _clean_key(os.environ.get(_KIMI_API_KEY_ENV)) or _clean_key(os.environ.get(_MOONSHOT_API_KEY_ENV))
    if env_key is not None:
        return env_key
    return _clean_key(_read_key_file(os.environ.get(_KIMI_API_KEY_FILE_ENV) or _default_kimi_key_file()))


def _read_key_file(path_text: str) -> str | None:
    path = Path(path_text).expanduser()
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _default_kimi_key_file() -> str:
    return str(Path.home().joinpath(*_DEFAULT_KIMI_KEY_FILE_PARTS))


def is_gemini_configured() -> bool:
    return _get_gemini_api_key() is not None


def is_openrouter_configured() -> bool:
    return _get_openrouter_api_key() is not None


def is_kimi_configured() -> bool:
    return _get_kimi_api_key() is not None


def get_provider_config_status() -> dict[str, bool]:
    return {
        "gemini_configured": is_gemini_configured(),
        "kimi_configured": is_kimi_configured(),
        "openrouter_configured": is_openrouter_configured(),
    }
