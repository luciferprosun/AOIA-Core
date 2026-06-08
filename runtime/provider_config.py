from __future__ import annotations

import os


_GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
_OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"


def _clean_key(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _get_gemini_api_key() -> str | None:
    return _clean_key(os.environ.get(_GEMINI_API_KEY_ENV))


def _get_openrouter_api_key() -> str | None:
    return _clean_key(os.environ.get(_OPENROUTER_API_KEY_ENV))


def is_gemini_configured() -> bool:
    return _get_gemini_api_key() is not None


def is_openrouter_configured() -> bool:
    return _get_openrouter_api_key() is not None


def get_provider_config_status() -> dict[str, bool]:
    return {
        "gemini_configured": is_gemini_configured(),
        "openrouter_configured": is_openrouter_configured(),
    }
