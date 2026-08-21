from __future__ import annotations

"""Typed provider failures for truthful runtime boundary translation."""

import sys

from runtime.outcomes import NZReasonCode


if __name__ == "runtime.providers.errors":
    sys.modules.setdefault("providers.errors", sys.modules[__name__])
elif __name__ == "providers.errors":
    sys.modules.setdefault("runtime.providers.errors", sys.modules[__name__])


class ModelProviderError(RuntimeError):
    reason_code = NZReasonCode.MODEL_PROVIDER_ERROR.value
    message_safe = "The model provider could not complete the request."


class ModelResponseMalformedError(ModelProviderError):
    reason_code = NZReasonCode.MODEL_RESPONSE_MALFORMED.value
    message_safe = "The model provider returned an invalid response."


class ModelTimeoutError(ModelProviderError):
    reason_code = NZReasonCode.MODEL_TIMEOUT.value
    message_safe = "The model request reached its timeout."


class ModelQuotaError(ModelProviderError):
    reason_code = NZReasonCode.MODEL_QUOTA.value
    message_safe = "The model provider rejected the request because its quota is unavailable."


class ModelNetworkError(ModelProviderError):
    reason_code = NZReasonCode.MODEL_NETWORK_FAILURE.value
    message_safe = "The model provider could not be reached."


def validate_model_response_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelResponseMalformedError(
            "Provider response text was missing or empty."
        )
    return value


def provider_reason_code(error: BaseException) -> str:
    explicit = getattr(error, "reason_code", None)
    if isinstance(explicit, str) and explicit.startswith("MODEL_"):
        return explicit
    error_type = type(error)
    is_http_error = (
        error_type.__module__ == "urllib.error"
        and error_type.__name__ == "HTTPError"
    )
    is_url_error = (
        error_type.__module__ == "urllib.error"
        and error_type.__name__ == "URLError"
    )
    if is_http_error:
        code = getattr(error, "code", None)
        if code == 429:
            return NZReasonCode.MODEL_QUOTA.value
        if code in {408, 504}:
            return NZReasonCode.MODEL_TIMEOUT.value
        return NZReasonCode.MODEL_PROVIDER_ERROR.value
    if isinstance(error, TimeoutError):
        return NZReasonCode.MODEL_TIMEOUT.value
    if is_url_error:
        if isinstance(getattr(error, "reason", None), TimeoutError):
            return NZReasonCode.MODEL_TIMEOUT.value
        return NZReasonCode.MODEL_NETWORK_FAILURE.value
    if isinstance(error, ConnectionError):
        return NZReasonCode.MODEL_NETWORK_FAILURE.value
    return NZReasonCode.MODEL_PROVIDER_ERROR.value


def typed_provider_error(error: BaseException) -> ModelProviderError:
    if isinstance(error, ModelProviderError):
        return error
    reason_code = provider_reason_code(error)
    error_type = {
        NZReasonCode.MODEL_RESPONSE_MALFORMED.value: ModelResponseMalformedError,
        NZReasonCode.MODEL_TIMEOUT.value: ModelTimeoutError,
        NZReasonCode.MODEL_QUOTA.value: ModelQuotaError,
        NZReasonCode.MODEL_NETWORK_FAILURE.value: ModelNetworkError,
    }.get(reason_code, ModelProviderError)
    return error_type(error_type.message_safe)
