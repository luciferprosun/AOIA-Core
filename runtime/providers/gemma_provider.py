from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ModelProvider
from .openai_compatible import OpenAICompatibleProvider


class GemmaProvider(ModelProvider):
    """Gemma worker provider with local Ollama first and HF fallback."""

    def __init__(self, model: str = "gemma3:4b") -> None:
        super().__init__(provider="gemma", model=model)
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.hf_token = os.getenv("HF_TOKEN", "").strip() or os.getenv("HUGGINGFACE_API_KEY", "").strip()
        self.hf_model = os.getenv("GEMMA_HF_MODEL", "google/gemma-2-2b-it")
        self.openai_base_url = os.getenv("GEMMA_OPENAI_BASE_URL", "").strip().rstrip("/")
        self.openai_api_key = os.getenv("GEMMA_OPENAI_API_KEY", "").strip()

    def generate(self, prompt: str) -> str:
        errors: list[str] = []

        try:
            return self._generate_ollama(prompt)
        except Exception as error:
            errors.append(f"ollama: {error}")

        if self.hf_token:
            try:
                return self._generate_huggingface(prompt)
            except Exception as error:
                errors.append(f"huggingface: {error}")

        if self.openai_base_url:
            try:
                provider = OpenAICompatibleProvider(
                    provider="gemma",
                    api_key=self.openai_api_key,
                    model=self.model,
                    base_url=self.openai_base_url,
                )
                return provider.generate(prompt)
            except Exception as error:
                errors.append(f"openai-compatible: {error}")

        raise RuntimeError(
            "Gemma worker provider is not configured or reachable. Checked:\n- "
            + "\n- ".join(errors)
        )

    def _generate_ollama(self, prompt: str) -> str:
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("response", "")).strip()

    def _generate_huggingface(self, prompt: str) -> str:
        body = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 700,
                "temperature": 0.1,
                "return_full_text": False,
            },
        }
        request = urllib.request.Request(
            f"https://api-inference.huggingface.co/models/{self.hf_model}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HF inference HTTP {error.code}: {detail}") from error

        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                return str(first.get("generated_text", "")).strip()
        if isinstance(payload, dict):
            return str(payload.get("generated_text", "") or payload.get("text", "")).strip()
        raise RuntimeError(f"Unexpected HF inference payload: {payload}")
