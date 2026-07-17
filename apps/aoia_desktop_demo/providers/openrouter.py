"""Minimal OpenRouter client for the desktop demo.

Standard-library only (``urllib``), no retry loop, no automatic provider
fallback, no silent model substitution. Every request is explicit and
bounded (timeout + response-size cap). The API key is only ever held in
memory by the caller and is never logged or embedded in an exception
message raised from this module.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .base import ChatMessage, ChatResult, ModelInfo, ProviderError
from ..security.secret_redaction import redact_secret_text

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_APP_TITLE = "AOIA Control Chat Competition Demo"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB bound on any single response body


@dataclass
class OpenRouterConfig:
    api_key: str
    base_url: str = OPENROUTER_BASE_URL
    app_title: str = DEFAULT_APP_TITLE
    timeout_seconds: float = 30.0


class OpenRouterClient:
    """A thin, explicit OpenRouter HTTP client.

    Every call is a single request. There is no automatic retry and no
    automatic fallback to a different provider or model.
    """

    def __init__(self, config: OpenRouterConfig) -> None:
        if not config.api_key:
            raise ProviderError("No API key configured for this session.")
        self._config = config

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": self._config.app_title,
        }

    def _read_bounded(self, response) -> bytes:
        chunk = response.read(MAX_RESPONSE_BYTES + 1)
        if len(chunk) > MAX_RESPONSE_BYTES:
            raise ProviderError(
                f"Provider response exceeded the {MAX_RESPONSE_BYTES} byte safety bound."
            )
        return chunk

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            url, data=data, headers=self._headers(), method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_seconds) as response:
                raw = self._read_bounded(response)
        except urllib.error.HTTPError as error:
            detail = redact_secret_text(error.read().decode("utf-8", errors="replace"))
            raise ProviderError(f"OpenRouter HTTP {error.code}: {detail}") from None
        except urllib.error.URLError as error:
            raise ProviderError(
                f"Could not reach OpenRouter: {redact_secret_text(str(error.reason))}"
            ) from None
        except TimeoutError:
            raise ProviderError(
                f"OpenRouter request timed out after {self._config.timeout_seconds:.0f}s."
            ) from None

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderError(
                f"OpenRouter returned a malformed response: {redact_secret_text(str(error))}"
            ) from None
        if not isinstance(payload, dict):
            raise ProviderError("OpenRouter response was not a JSON object.")
        return payload

    def test_connection(self) -> bool:
        """Lightweight connectivity/auth check. Raises ProviderError on failure."""
        self._request("GET", "/models")
        return True

    def list_models(self) -> list[ModelInfo]:
        payload = self._request("GET", "/models")
        raw_models = payload.get("data")
        if not isinstance(raw_models, list):
            raise ProviderError("OpenRouter model list response was malformed (missing 'data').")

        models: list[ModelInfo] = []
        for entry in raw_models:
            if not isinstance(entry, dict):
                continue
            model_id = entry.get("id")
            if not isinstance(model_id, str) or not model_id:
                continue
            pricing = entry.get("pricing") if isinstance(entry.get("pricing"), dict) else {}
            context_length = entry.get("context_length")
            models.append(
                ModelInfo(
                    id=model_id,
                    name=str(entry.get("name") or model_id),
                    context_length=int(context_length) if isinstance(context_length, (int, float)) else None,
                    prompt_price=str(pricing.get("prompt")) if pricing.get("prompt") is not None else None,
                    completion_price=str(pricing.get("completion")) if pricing.get("completion") is not None else None,
                )
            )
        return models

    def send_chat(
        self,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
    ) -> ChatResult:
        if not model:
            raise ProviderError("No model selected. Choose or enter a model ID before sending.")
        if not messages:
            raise ProviderError("Cannot send an empty conversation.")

        body: dict = {
            "model": model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = int(max_tokens)

        payload = self._request("POST", "/chat/completions", body)

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("OpenRouter response did not include any choices.")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ProviderError("OpenRouter response choice was malformed.")
        message = first_choice.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderError("OpenRouter response message content was missing or malformed.")

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return ChatResult(
            content=message["content"].strip(),
            model=str(payload.get("model") or model),
            raw_finish_reason=first_choice.get("finish_reason"),
            usage=usage,
        )
