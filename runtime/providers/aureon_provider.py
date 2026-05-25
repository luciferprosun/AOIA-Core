from __future__ import annotations

import os

from .base import ModelProvider
from .openai_compatible import OpenAICompatibleProvider


class AureonProvider(ModelProvider):
    """Aureon-compatible cloud provider.

    If no live backend is configured, the provider exposes only a bounded
    diagnostic greeting. Operational planning still requires a configured
    backend.
    """

    def __init__(self, model: str) -> None:
        super().__init__(provider="aureon", model=model)
        self._backend = self._build_backend(model)

    def generate(self, prompt: str) -> str:
        if self._backend is None:
            lowered = prompt.lower()
            if "hello" in lowered or "are you ai" in lowered or "witaj" in lowered:
                return (
                    '{"action":"respond","message":"Jestem lokalnym Aureon adapterem diagnostycznym. '
                    'Backend AUREON_API_BASE_URL nie jest skonfigurowany, więc mogę tylko zgłosić status, '
                    'a nie wykonywać planowania.","confidence_label":"high"}'
                )
            raise RuntimeError(
                "Aureon backend is not configured. Set AUREON_API_BASE_URL or use another provider."
            )
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
