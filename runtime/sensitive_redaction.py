from __future__ import annotations

"""Bounded, in-memory redaction for non-authoritative runtime output."""

import re
from collections.abc import Iterable, Mapping
from typing import Any


REDACTION_MARKER = "[REDACTED]"
MIN_REGISTERED_SECRET_LENGTH = 8
DEFAULT_REDACTION_DEPTH = 8
DEFAULT_REDACTION_ITEMS = 256

# These are the only process-environment values registered by the default
# runtime configuration lifecycle.  The redactor never enumerates or mutates
# the full environment.
RUNTIME_SECRET_ENV_NAMES = (
    "AOIA_WEB_OPERATOR_TOKEN",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GEMMA_OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_API_KEY",
    "KIMI_API_KEY",
    "MOONSHOT_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    # Synthetic operator-test input used only when explicitly present.
    "SOME_PRIVATE_TOKEN",
    "XAI_API_KEY",
)

_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "clientsecret",
        "credential",
        "credentials",
        "password",
        "passwd",
        "private_key",
        "privatekey",
        "secret",
        "token",
        "x_goog_api_key",
        "xgoogapikey",
    }
)
_SENSITIVE_FIELD_SUFFIXES = (
    "_api_key",
    "_credential",
    "_credentials",
    "_password",
    "_private_key",
    "_secret",
    "_token",
)
_KNOWN_FORMAT_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bgsk_[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bghp_[A-Za-z0-9_]{8,}"),
    re.compile(r"\bxoxb-[A-Za-z0-9-]{8,}"),
)


class SensitiveValueRedactor:
    """Immutable registry that removes known values from output projections.

    Registration returns a new instance, so unrelated runtimes do not share a
    mutable secret registry.  Its repr deliberately exposes no values or value
    lengths.
    """

    __slots__ = ("_known_values", "_max_depth", "_max_items", "_frozen")

    def __init__(
        self,
        known_values: Iterable[object] = (),
        *,
        max_depth: int = DEFAULT_REDACTION_DEPTH,
        max_items: int = DEFAULT_REDACTION_ITEMS,
    ) -> None:
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 1:
            raise ValueError("max_depth must be a positive integer")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        values = {
            value
            for value in known_values
            if isinstance(value, str)
            and len(value) >= MIN_REGISTERED_SECRET_LENGTH
        }
        object.__setattr__(
            self,
            "_known_values",
            tuple(sorted(values, key=lambda item: (-len(item), item))),
        )
        object.__setattr__(self, "_max_depth", max_depth)
        object.__setattr__(self, "_max_items", max_items)
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("SensitiveValueRedactor is immutable")
        object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        return "SensitiveValueRedactor([in-memory values hidden])"

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str],
        *,
        names: Iterable[str] = RUNTIME_SECRET_ENV_NAMES,
        additional_values: Iterable[object] = (),
        max_depth: int = DEFAULT_REDACTION_DEPTH,
        max_items: int = DEFAULT_REDACTION_ITEMS,
    ) -> "SensitiveValueRedactor":
        values = [environ.get(name, "") for name in names]
        values.extend(additional_values)
        return cls(values, max_depth=max_depth, max_items=max_items)

    def registering(self, *values: object) -> "SensitiveValueRedactor":
        return SensitiveValueRedactor(
            (*self._known_values, *values),
            max_depth=self._max_depth,
            max_items=self._max_items,
        )

    def combining(self, other: "SensitiveValueRedactor") -> "SensitiveValueRedactor":
        if not isinstance(other, SensitiveValueRedactor):
            raise TypeError("other must be a SensitiveValueRedactor")
        return SensitiveValueRedactor(
            (*self._known_values, *other._known_values),
            max_depth=min(self._max_depth, other._max_depth),
            max_items=min(self._max_items, other._max_items),
        )

    def redact_text(self, value: object) -> str:
        text = value if isinstance(value, str) else str(value)
        for secret in self._known_values:
            text = text.replace(secret, REDACTION_MARKER)
        for pattern in _KNOWN_FORMAT_PATTERNS:
            text = pattern.sub(REDACTION_MARKER, text)
        return text

    def redact(self, value: object) -> Any:
        return self._redact(value, depth=0)

    def _redact(self, value: object, *, depth: int) -> Any:
        if isinstance(value, str):
            return self.redact_text(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, bytes):
            return self.redact_text(value.decode("utf-8", errors="replace"))
        if depth >= self._max_depth:
            return REDACTION_MARKER
        if isinstance(value, Mapping):
            redacted: dict[object, Any] = {}
            for index, (key, item) in enumerate(value.items()):
                if index >= self._max_items:
                    redacted["redaction_limit"] = REDACTION_MARKER
                    break
                safe_key = (
                    self.redact_text(key)
                    if isinstance(key, (str, int, float, bool)) or key is None
                    else REDACTION_MARKER
                )
                if safe_key in redacted:
                    safe_key = f"{safe_key}#{index}"
                if self.is_sensitive_field(key):
                    redacted[safe_key] = REDACTION_MARKER
                else:
                    redacted[safe_key] = self._redact(item, depth=depth + 1)
            return redacted
        if isinstance(value, (set, frozenset)):
            # Sets are unordered and may contain objects with secret-bearing
            # repr implementations.  Runtime records do not require them.
            return [REDACTION_MARKER]
        if isinstance(value, (list, tuple)):
            items = list(value)
            redacted_items = [
                self._redact(item, depth=depth + 1)
                for item in items[: self._max_items]
            ]
            if len(items) > self._max_items:
                redacted_items.append(REDACTION_MARKER)
            return redacted_items
        # Runtime output must remain JSON-safe.  Unknown objects can have
        # secret-bearing repr implementations, so fail closed.
        return REDACTION_MARKER

    @staticmethod
    def is_sensitive_field(value: object) -> bool:
        if not isinstance(value, str):
            return False
        normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        collapsed = normalized.replace("_", "")
        return (
            normalized in _SENSITIVE_FIELD_NAMES
            or normalized.endswith(_SENSITIVE_FIELD_SUFFIXES)
            or collapsed.endswith(
                (
                    "apikey",
                    "credential",
                    "credentials",
                    "password",
                    "privatekey",
                    "secret",
                    "token",
                )
            )
        )


def build_runtime_redactor(
    *,
    environ: Mapping[str, str],
    additional_values: Iterable[object] = (),
) -> SensitiveValueRedactor:
    """Build one runtime-owned redactor without retaining the environment."""

    return SensitiveValueRedactor.from_environment(
        environ,
        additional_values=additional_values,
    )


def build_current_runtime_redactor(
    *,
    environ: Mapping[str, str],
    additional_values: Iterable[object] = (),
) -> SensitiveValueRedactor:
    """Snapshot only the explicit secret allowlist supplied by an active caller."""

    return build_runtime_redactor(
        environ=environ,
        additional_values=additional_values,
    )
