from __future__ import annotations

import os

from .base import ModelProvider


class GeminiProvider(ModelProvider):
    """Gemini implementation of the small provider interface."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from google import genai
        except ImportError as error:
            raise ImportError(
                "google-genai is required only when the Gemini provider is selected."
            ) from error

        os.environ["GEMINI_API_KEY"] = api_key
        os.environ.pop("GOOGLE_API_KEY", None)
        super().__init__(provider="gemini", model=model)
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return (response.text or "").strip()
