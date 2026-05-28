from __future__ import annotations

from dataclasses import dataclass


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
