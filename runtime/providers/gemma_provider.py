from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ModelProvider, require_provider_calls_enabled
from .errors import ModelResponseMalformedError, validate_model_response_text
from .openai_compatible import OpenAICompatibleProvider


PROVIDER_NETWORK_SURFACE = True
APPROVED_RUNTIME_PROVIDER_FLOW = False
PROVIDER_CALLS_FROZEN = True


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
        require_provider_calls_enabled(self.provider)
        errors: list[str] = []
        provider_errors: list[BaseException] = []

        try:
            return validate_model_response_text(self._generate_ollama(prompt)).strip()
        except Exception as error:
            errors.append(f"ollama: {error}")
            provider_errors.append(error)

        if self.hf_token:
            try:
                return validate_model_response_text(self._generate_huggingface(prompt)).strip()
            except Exception as error:
                errors.append(f"huggingface: {error}")
                provider_errors.append(error)

        if self.openai_base_url:
            try:
                provider = OpenAICompatibleProvider(
                    provider="gemma",
                    api_key=self.openai_api_key,
                    model=self.model,
                    base_url=self.openai_base_url,
                )
                return validate_model_response_text(provider.generate(prompt)).strip()
            except Exception as error:
                errors.append(f"openai-compatible: {error}")
                provider_errors.append(error)

        if provider_errors and all(
            isinstance(error, ModelResponseMalformedError)
            for error in provider_errors
        ):
            raise ModelResponseMalformedError(
                "Every configured Gemma backend returned a malformed response."
            ) from provider_errors[-1]

        raise RuntimeError(
            "Gemma worker provider is not configured or reachable. Checked:\n- "
            + "\n- ".join(errors)
        )

    def _generate_ollama(self, prompt: str) -> str:
        require_provider_calls_enabled("ollama")
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
            try:
                payload = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ModelResponseMalformedError(
                    "Ollama response was not valid JSON."
                ) from error
        if not isinstance(payload, dict) or "response" not in payload:
            raise ModelResponseMalformedError(
                "Ollama response did not match the expected schema."
            )
        return validate_model_response_text(payload["response"]).strip()

    def _generate_huggingface(self, prompt: str) -> str:
        require_provider_calls_enabled(self.provider)
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
                try:
                    payload = json.loads(response.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ModelResponseMalformedError(
                        "Hugging Face response was not valid JSON."
                    ) from error
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HF inference HTTP {error.code}: {detail}") from error

        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                return validate_model_response_text(first.get("generated_text")).strip()
        if isinstance(payload, dict):
            return validate_model_response_text(
                payload.get("generated_text") or payload.get("text")
            ).strip()
        raise ModelResponseMalformedError(
            "Hugging Face response did not match the expected schema."
        )
