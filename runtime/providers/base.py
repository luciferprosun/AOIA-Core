from __future__ import annotations

import os
from dataclasses import dataclass


PROVIDER_NETWORK_SURFACE = True
APPROVED_RUNTIME_PROVIDER_FLOW = False
PROVIDER_CALLS_FROZEN = True
AOIA_PROVIDER_CALLS_ENABLED = os.environ.get("AOIA_PROVIDER_CALLS_ENABLED") == "1"


def provider_calls_enabled() -> bool:
    return AOIA_PROVIDER_CALLS_ENABLED or os.environ.get("AOIA_PROVIDER_CALLS_ENABLED") == "1"


def require_provider_calls_enabled() -> None:
    if not provider_calls_enabled():
        raise RuntimeError(
            "Provider/network calls are frozen by default and not approved for autonomous runtime use. "
            "Set AOIA_PROVIDER_CALLS_ENABLED=1 only for explicit controlled manual testing."
        )


@dataclass(frozen=True)
class ModelProvider:
    """Small provider interface used by the runtime."""

    provider: str
    model: str

    @property
    def full_name(self) -> str:
        return f"{self.provider}/{self.model}"

    def generate(self, prompt: str) -> str:
        raise NotImplementedError
