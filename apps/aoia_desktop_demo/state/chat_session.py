"""In-memory chat session model.

Testable without opening a graphical window: nothing here imports
``tkinter`` or performs any I/O. This module owns conversation state and
request-cancellation bookkeeping only; it never itself calls a provider,
retries, or falls back — those decisions belong to the caller (``app.py``),
and this module intentionally offers no method that would let that
happen implicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

from ..providers.base import ChatMessage

_request_id_counter = count(1)


@dataclass(frozen=True)
class TranscriptEntry:
    role: str  # "user" | "assistant" | "error"
    content: str
    knowledge_profile_id: str | None = None


class ChatSession:
    """A single in-memory, multi-turn conversation.

    - ``system_context`` is kept separate from the visible transcript.
    - There is no automatic retry and no automatic provider fallback:
      each send is one explicit, independent request.
    - Cancellation is modeled with a monotonically increasing request id;
      only the result matching the *current* id is ever applied, so a
      canceled or superseded request cannot silently reappear.
    """

    def __init__(self) -> None:
        self.system_context: str | None = None
        self.transcript: list[TranscriptEntry] = []
        self._active_request_id: int | None = None

    def new_chat(self) -> None:
        self.transcript.clear()
        self.system_context = None
        self._active_request_id = None

    def clear_chat(self) -> None:
        self.new_chat()

    def add_user_message(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self.transcript.append(TranscriptEntry(role="user", content=text))

    def add_assistant_message(self, text: str, *, knowledge_profile_id: str | None = None) -> None:
        self.transcript.append(
            TranscriptEntry(role="assistant", content=text, knowledge_profile_id=knowledge_profile_id)
        )

    def add_error_message(self, text: str) -> None:
        self.transcript.append(TranscriptEntry(role="error", content=text))

    def messages_for_provider(self, extra_system_message: str | None = None) -> list[ChatMessage]:
        """Build the exact message list to send. No hidden extra messages
        beyond what is passed here and what is already in the transcript."""
        messages: list[ChatMessage] = []
        if self.system_context:
            messages.append(ChatMessage(role="system", content=self.system_context))
        if extra_system_message:
            messages.append(ChatMessage(role="system", content=extra_system_message))
        for entry in self.transcript:
            if entry.role in ("user", "assistant"):
                messages.append(ChatMessage(role=entry.role, content=entry.content))
        return messages

    # --- request lifecycle -------------------------------------------------

    def begin_request(self) -> int:
        """Allocate and record a new active request id. Only one request
        is considered active at a time (the caller is responsible for not
        starting a second one while ``has_active_request`` is true)."""
        request_id = next(_request_id_counter)
        self._active_request_id = request_id
        return request_id

    @property
    def has_active_request(self) -> bool:
        return self._active_request_id is not None

    def is_current(self, request_id: int) -> bool:
        """True only if ``request_id`` is still the active one — i.e. it
        was not canceled and no newer request has superseded it."""
        return self._active_request_id == request_id

    def end_request(self, request_id: int) -> None:
        if self._active_request_id == request_id:
            self._active_request_id = None

    def cancel_active_request(self) -> None:
        """Mark whatever request is active as no longer current. A result
        that arrives later for the old id will be ignored by ``is_current``."""
        self._active_request_id = None
