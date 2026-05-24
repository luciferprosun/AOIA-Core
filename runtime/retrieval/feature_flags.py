from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Callable


LINUX_RETRIEVAL_V1_FLAG = "AIOA_ENABLE_LINUX_RETRIEVAL_V1"
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}


def linux_retrieval_v1_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True only when the Linux retrieval v1 flag is explicitly enabled."""
    source = env if env is not None else os.environ
    value = source.get(LINUX_RETRIEVAL_V1_FLAG)
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return False


def linux_retrieval_v1_status(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    source = env if env is not None else os.environ
    value = source.get(LINUX_RETRIEVAL_V1_FLAG)
    return {
        "flag": LINUX_RETRIEVAL_V1_FLAG,
        "raw_value": value,
        "enabled": linux_retrieval_v1_enabled(source),
        "default": "off",
        "activation": "explicit_only",
    }


def linux_retrieval_boundary(env: Mapping[str, str] | None = None) -> Callable[..., Any] | None:
    """Return the canonical facade only when explicit flag activation is requested.

    This helper is intentionally not wired into runtime/main.py in Phase 0C.
    It exists to make future router activation explicit and testable.
    """
    if not linux_retrieval_v1_enabled(env):
        return None
    from retrieval.facade import retrieve_linux_knowledge

    return retrieve_linux_knowledge
