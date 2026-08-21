from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from runtime.providers.contracts import (
    BLOCKED,
    DRY_RUN_PREVIEW,
    ERROR,
    LIVE_SUCCESS,
    ProviderActivationStatus,
    ProviderRequestEnvelope,
    ProviderRuntimeResult,
)
from runtime.providers.payloads import (
    build_deterministic_mock_response,
    build_provider_payload,
)
from runtime.providers.errors import (
    ModelProviderError,
    ModelResponseMalformedError,
    provider_reason_code,
    validate_model_response_text,
)
from runtime.providers.redaction import redact_provider_data, redact_provider_text
from runtime.providers.runtime_policy import ProviderRuntimePolicy


_OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_KIMI_ENDPOINT = "https://api.moonshot.ai/v1/chat/completions"
_GEMINI_ENDPOINT_PREFIX = "https://generativelanguage.googleapis.com/v1beta/models/"
_DEFAULT_KIMI_KEY_FILE_PARTS = ("Desktop", "API TOKENy", "kimi kodex")


def run_provider_request(
    envelope: ProviderRequestEnvelope,
    *,
    live: bool = False,
    acknowledge_live_provider_test: bool = False,
    activation_status: ProviderActivationStatus | str = ProviderActivationStatus.DRY_RUN_ONLY,
    timeout_seconds: int = 30,
) -> ProviderRuntimeResult:
    decision = ProviderRuntimePolicy.evaluate(
        envelope,
        live=live,
        acknowledge_live_provider_test=acknowledge_live_provider_test,
        activation_status=activation_status,
    )
    mode = "live" if live else "dry_run"
    if not decision.allowed:
        return _result(envelope, mode=mode, status=BLOCKED, error_message=decision.reason)
    if not live:
        response = (
            build_deterministic_mock_response(envelope)
            if envelope.provider_id == "mock_chat"
            else None
        )
        return _result(
            envelope,
            mode="dry_run",
            status=DRY_RUN_PREVIEW,
            response_text=response,
        )

    api_key = _read_api_key(envelope.provider_id)
    key_decision = ProviderRuntimePolicy.evaluate(
        envelope,
        live=True,
        acknowledge_live_provider_test=acknowledge_live_provider_test,
        activation_status=activation_status,
        api_key_present=bool(api_key),
    )
    if not key_decision.allowed:
        return _result(envelope, mode="live", status=BLOCKED, error_message=key_decision.reason)
    try:
        response_text = _perform_live_http_call(
            envelope,
            api_key=api_key,
            timeout_seconds=_validated_timeout(timeout_seconds),
        )
        return _result(
            envelope,
            mode="live",
            status=LIVE_SUCCESS,
            response_text=response_text,
            known_secrets=(api_key,),
        )
    except (ModelProviderError, HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return _result(
            envelope,
            mode="live",
            status=ERROR,
            error_message=redact_provider_text(error, known_secrets=(api_key,)),
            reason_code=provider_reason_code(error),
            known_secrets=(api_key,),
        )


def _read_api_key(provider_id: str) -> str:
    if provider_id == "kimi_chat":
        return (
            os.environ.get("KIMI_API_KEY", "").strip()
            or os.environ.get("MOONSHOT_API_KEY", "").strip()
            or _read_api_key_file(os.environ.get("KIMI_API_KEY_FILE") or _default_kimi_key_file())
        )
    if provider_id == "openrouter_chat":
        return os.environ.get("OPENROUTER_API_KEY", "").strip()
    if provider_id == "gemini_chat":
        return (
            os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )
    return ""


def _read_api_key_file(path_text: str) -> str:
    path = Path(path_text).expanduser()
    try:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _default_kimi_key_file() -> str:
    return str(Path.home().joinpath(*_DEFAULT_KIMI_KEY_FILE_PARTS))


def _perform_live_http_call(
    envelope: ProviderRequestEnvelope,
    *,
    api_key: str,
    timeout_seconds: int,
) -> str:
    safe_model_id = redact_provider_text(
        envelope.model_id,
        known_secrets=(api_key,),
    )
    payload = redact_provider_data(
        build_provider_payload(envelope),
        known_secrets=(api_key,),
    )
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if envelope.provider_id == "kimi_chat":
        request = Request(
            _KIMI_ENDPOINT,
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
    elif envelope.provider_id == "openrouter_chat":
        request = Request(
            _OPENROUTER_ENDPOINT,
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
    elif envelope.provider_id == "gemini_chat":
        endpoint = (
            _GEMINI_ENDPOINT_PREFIX
            + quote(safe_model_id, safe="")
            + ":generateContent"
        )
        request = Request(
            endpoint,
            data=body,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
    else:
        raise ValueError("provider has no live Runtime 1A gateway")
    with urlopen(request, timeout=timeout_seconds) as response:
        try:
            response_data = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ModelResponseMalformedError(
                "Provider response was not valid JSON."
            ) from error
    return _extract_response_text(envelope.provider_id, response_data)


def _extract_response_text(provider_id: str, payload: object) -> str:
    try:
        if provider_id in {"kimi_chat", "openrouter_chat"}:
            value = payload["choices"][0]["message"]["content"]  # type: ignore[index]
        else:
            value = payload["candidates"][0]["content"]["parts"][0]["text"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as error:
        raise ModelResponseMalformedError(
            "Provider response did not match the expected schema."
        ) from error
    return redact_provider_text(validate_model_response_text(value))


def _result(
    envelope: ProviderRequestEnvelope,
    *,
    mode: str,
    status: str,
    response_text: str | None = None,
    error_message: str | None = None,
    reason_code: str | None = None,
    known_secrets: tuple[str, ...] = (),
) -> ProviderRuntimeResult:
    return ProviderRuntimeResult(
        provider_id=envelope.provider_id,
        model_id=redact_provider_text(
            envelope.model_id,
            known_secrets=known_secrets,
        ),
        mode=mode,
        status=status,
        redacted_request_preview=redact_provider_text(
            envelope.payload_preview,
            known_secrets=known_secrets,
        ),
        response_text=(
            redact_provider_text(response_text, known_secrets=known_secrets)
            if response_text is not None
            else None
        ),
        error_message=(
            redact_provider_text(error_message, known_secrets=known_secrets)
            if error_message is not None
            else None
        ),
        reason_code=reason_code,
    )


def _validated_timeout(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 60:
        raise ValueError("timeout_seconds must be between 1 and 60")
    return value
