from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from runtime.provider_config import _get_gemini_api_key, _get_openrouter_api_key
    from runtime.provider_registry import require_provider_live_call_allowed
except ModuleNotFoundError:  # pragma: no cover - script launch path
    from provider_config import _get_gemini_api_key, _get_openrouter_api_key
    from provider_registry import require_provider_live_call_allowed


"""Provider/network-capable surface.

This module is not an approved autonomous runtime provider execution path.
Provider calls must not be reachable from model/proposal/public runtime flow
without an explicit controlled gateway and human approval policy.
"""

PROVIDER_NETWORK_SURFACE = True
APPROVED_RUNTIME_PROVIDER_FLOW = False
PROVIDER_CALLS_FROZEN = True
AOIA_PROVIDER_CALLS_ENABLED = os.environ.get("AOIA_PROVIDER_CALLS_ENABLED") == "1"


def _provider_calls_enabled() -> bool:
    return AOIA_PROVIDER_CALLS_ENABLED or os.environ.get("AOIA_PROVIDER_CALLS_ENABLED") == "1"


def _require_provider_calls_enabled(provider_id: str) -> None:
    require_provider_live_call_allowed(provider_id)
    if not _provider_calls_enabled():
        raise RuntimeError(
            "Provider/network calls are frozen by default and not approved for autonomous runtime use. "
            "Set AOIA_PROVIDER_CALLS_ENABLED=1 only for explicit controlled manual testing."
        )


@dataclass(frozen=True)
class ProviderCallResult:
    provider_id: str
    model_id: str
    call_made: bool
    output_text: str = ""
    output_trusted: bool = False
    error: str = ""

    def __post_init__(self) -> None:
        if self.output_trusted is not False:
            raise ValueError("provider output must remain untrusted")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def call_selected_provider_once(
    *,
    provider_id: str,
    model_id: str,
    user_prompt: str,
    human_approved: bool,
    provider_call_permitted: bool,
    policy_rejected: bool,
) -> ProviderCallResult:
    if human_approved is not True:
        return _blocked(provider_id, model_id, "human approval is required")
    if provider_call_permitted is not True:
        return _blocked(provider_id, model_id, "provider call is not permitted")
    if policy_rejected:
        return _blocked(provider_id, model_id, "policy rejected this provider call")
    if not user_prompt.strip():
        return _blocked(provider_id, model_id, "prompt is required")
    try:
        require_provider_live_call_allowed(provider_id)
    except RuntimeError as error:
        return _blocked(provider_id, model_id, str(error))
    if not _provider_calls_enabled():
        return _blocked(
            provider_id,
            model_id,
            "Provider/network calls are frozen by default and not approved for autonomous runtime use.",
        )

    if provider_id == "gemini":
        return _call_gemini_once(model_id=model_id, user_prompt=user_prompt)
    if provider_id == "openrouter":
        return _call_openrouter_once(model_id=model_id, user_prompt=user_prompt)
    if provider_id == "local":
        return _blocked(provider_id, model_id, "local model execution not implemented in M1-ROUTER-A")
    return _blocked(provider_id, model_id, "provider is not supported in M1-ROUTER-A")


def _blocked(provider_id: str, model_id: str, error: str) -> ProviderCallResult:
    return ProviderCallResult(
        provider_id=provider_id,
        model_id=model_id,
        call_made=False,
        output_text="",
        output_trusted=False,
        error=error,
    )


def _call_gemini_once(*, model_id: str, user_prompt: str) -> ProviderCallResult:
    _require_provider_calls_enabled("gemini")
    api_key = _get_gemini_api_key()
    if api_key is None:
        return _blocked("gemini", model_id, "Gemini provider is not configured")

    gemini_model = model_id.removeprefix("gemini/")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
    request = Request(
        url,
        data=json.dumps({"contents": [{"parts": [{"text": user_prompt}]}]}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _send_json_request(
        provider_id="gemini",
        model_id=model_id,
        request=request,
        extractor=_extract_gemini_text,
    )


def _call_openrouter_once(*, model_id: str, user_prompt: str) -> ProviderCallResult:
    _require_provider_calls_enabled("openrouter")
    api_key = _get_openrouter_api_key()
    if api_key is None:
        return _blocked("openrouter", model_id, "OpenRouter provider is not configured")

    openrouter_model = model_id.removeprefix("openrouter/")
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(
            {
                "model": openrouter_model,
                "messages": [{"role": "user", "content": user_prompt}],
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _send_json_request(
        provider_id="openrouter",
        model_id=model_id,
        request=request,
        extractor=_extract_openrouter_text,
    )


def _send_json_request(*, provider_id: str, model_id: str, request: Request, extractor) -> ProviderCallResult:
    _require_provider_calls_enabled(provider_id)
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return ProviderCallResult(
            provider_id=provider_id,
            model_id=model_id,
            call_made=True,
            output_text="",
            output_trusted=False,
            error=f"provider HTTP error {error.code}",
        )
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        return ProviderCallResult(
            provider_id=provider_id,
            model_id=model_id,
            call_made=True,
            output_text="",
            output_trusted=False,
            error=f"provider call failed: {type(error).__name__}",
        )

    return ProviderCallResult(
        provider_id=provider_id,
        model_id=model_id,
        call_made=True,
        output_text=extractor(payload),
        output_trusted=False,
        error="",
    )


def _extract_gemini_text(payload: dict) -> str:
    parts = (
        payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return "\n".join(str(part.get("text", "")) for part in parts if part.get("text"))


def _extract_openrouter_text(payload: dict) -> str:
    choices = payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content", ""))
