"""Provider-facing data types shared by the desktop demo.

Deliberately minimal: this module has no dependency on the AOIA-Core
production runtime's provider registry/gateway. Provider output produced
through these types is never treated as authority by any other part of
this application — see ``apps/aoia_desktop_demo/README.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(Exception):
    """Raised for any provider/network failure. Messages passed to this
    exception must already be secret-redacted by the caller."""


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    context_length: int | None = None
    prompt_price: str | None = None
    completion_price: str | None = None

    @property
    def is_free(self) -> bool:
        def _is_zero(value: str | None) -> bool:
            if not value:
                return False
            try:
                return float(value) == 0.0
            except ValueError:
                return False

        return _is_zero(self.prompt_price) and _is_zero(self.completion_price)


@dataclass(frozen=True)
class ChatResult:
    content: str
    model: str
    raw_finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
