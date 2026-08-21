from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from runtime.sensitive_redaction import REDACTION_MARKER, build_current_runtime_redactor


REDACTED = REDACTION_MARKER


def redact_provider_text(text: object, *, known_secrets: Sequence[str] = ()) -> str:
    return build_current_runtime_redactor(
        additional_values=known_secrets,
    ).redact_text(text)


def redact_provider_data(
    value: object,
    *,
    known_secrets: Sequence[str] = (),
) -> Any:
    # Mapping import remains part of this compatibility surface and documents
    # the accepted structured input without maintaining a second redactor.
    if not isinstance(value, (Mapping, list, tuple, str, bytes, int, float, bool, type(None))):
        return REDACTED
    return build_current_runtime_redactor(
        additional_values=known_secrets,
    ).redact(value)
