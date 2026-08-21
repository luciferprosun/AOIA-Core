from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ModelProvider, require_provider_calls_enabled
from .errors import (
    ModelNetworkError,
    ModelProviderError,
    ModelQuotaError,
    ModelResponseMalformedError,
    ModelTimeoutError,
    validate_model_response_text,
)


PROVIDER_NETWORK_SURFACE = True
APPROVED_RUNTIME_PROVIDER_FLOW = False
PROVIDER_CALLS_FROZEN = True


class OpenAICompatibleProvider(ModelProvider):
    """Minimal OpenAI-compatible chat completions provider.

    This keeps provider switching independent from the agent runtime without
    adding another package dependency.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        super().__init__(provider=provider, model=model)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str) -> str:
        require_provider_calls_enabled(self.provider)
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": int(os.getenv("OPENAI_COMPATIBLE_MAX_TOKENS", "1200")),
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
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
                        "Provider response was not valid JSON."
                    ) from error
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            error_type: type[ModelProviderError]
            if error.code == 429:
                error_type = ModelQuotaError
            elif error.code in {408, 504}:
                error_type = ModelTimeoutError
            else:
                error_type = ModelProviderError
            raise error_type(f"{self.provider} HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ModelTimeoutError("Model provider request timed out.") from error
            raise ModelNetworkError("Model provider network request failed.") from error
        except TimeoutError as error:
            raise ModelTimeoutError("Model provider request timed out.") from error

        try:
            value = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ModelResponseMalformedError(
                "Provider response did not match the expected schema."
            ) from error

        return validate_model_response_text(value).strip()
