from __future__ import annotations

import os

from .base import ModelProvider
from .openai_compatible import OpenAICompatibleProvider


class AureonProvider(ModelProvider):
    """Aureon-compatible cloud provider.

    This class intentionally has no offline fake responder. If no live backend
    is configured, the caller must fall back to another real cloud provider.
    """

    def __init__(self, model: str) -> None:
        super().__init__(provider="aureon", model=model)
        self._backend = self._build_backend(model)
        if self._backend is None:
            raise RuntimeError(
                "Aureon backend is not configured. Set AUREON_API_BASE_URL or use another provider."
            )

    def generate(self, prompt: str) -> str:
        return self._backend.generate(prompt)

    @staticmethod
    def _build_backend(model: str):
        base_url = os.getenv("AUREON_API_BASE_URL", "").strip().rstrip("/")
        api_key = os.getenv("AUREON_API_KEY", "").strip()

        if not base_url:
            return None

        return OpenAICompatibleProvider(
            provider="aureon",
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
