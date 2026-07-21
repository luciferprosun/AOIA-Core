from __future__ import annotations

import http.client
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

from .base import ModelProvider, require_provider_calls_enabled


PROVIDER_NETWORK_SURFACE = True
APPROVED_RUNTIME_PROVIDER_FLOW = False
PROVIDER_CALLS_FROZEN = True
_MAXIMUM_EXACT_RESPONSE_BYTES = 1_000_000
_ALLOWED_FINISH_REASONS = frozenset({"stop", "length", "content_filter"})
_CONNECT_WORKER_SLOTS = threading.BoundedSemaphore(value=4)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class _AbsoluteDeadlineResponse:
    """One HTTPS response guarded by one absolute no-retry deadline."""

    def __init__(self, request: urllib.request.Request, *, timeout_seconds: int) -> None:
        parsed = urlsplit(request.full_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("exact provider endpoint must be HTTPS")
        self._deadline = time.monotonic() + timeout_seconds
        self._expired = threading.Event()
        self._connection = http.client.HTTPSConnection(
            parsed.hostname,
            parsed.port,
            timeout=timeout_seconds,
        )
        self._response: http.client.HTTPResponse | None = None
        self._timer = threading.Timer(timeout_seconds, self._expire)
        self._timer.daemon = True
        self._timer.start()
        try:
            self._connect_before_deadline()
            self._guard_request_transport()
            self._set_remaining_socket_timeout()
            target = parsed.path or "/"
            if parsed.query:
                target += f"?{parsed.query}"
            self._connection.request(
                request.get_method(),
                target,
                body=request.data,
                headers=dict(request.header_items()),
            )
            self._set_remaining_socket_timeout()
            response = self._connection.getresponse()
            self._set_remaining_socket_timeout()
            if not 200 <= response.status < 300:
                raise RuntimeError(f"exact provider HTTP {response.status}")
            self._response = response
        except BaseException:
            self.close()
            raise

    def _connect_before_deadline(self) -> None:
        """Bound DNS, TCP and TLS setup without letting a late worker send.

        ``HTTPSConnection.connect()`` includes synchronous DNS resolution,
        which is not reliably interrupted by a socket timeout.  Keep that
        phase in a daemon thread and wait only for the remaining absolute
        deadline.  The worker deliberately owns *only* ``connect()``: request
        bytes are emitted by the calling thread only after successful,
        in-deadline completion.  A late completion therefore has no path to a
        provider request and closes any socket it may have acquired.
        """

        if not _CONNECT_WORKER_SLOTS.acquire(blocking=False):
            raise RuntimeError("exact provider connect capacity is exhausted")

        completed = threading.Event()
        failures: list[BaseException] = []

        def connect_only() -> None:
            try:
                self._connection.connect()
            except BaseException as error:  # propagated on the calling thread
                failures.append(error)
            finally:
                try:
                    if self._expired.is_set():
                        self._connection.close()
                finally:
                    _CONNECT_WORKER_SLOTS.release()
                    completed.set()

        worker = threading.Thread(
            target=connect_only,
            name="aoia-openai-compatible-connect",
            daemon=True,
        )
        try:
            worker.start()
        except BaseException:
            _CONNECT_WORKER_SLOTS.release()
            raise
        if not completed.wait(self._remaining()):
            self._expire()
            raise TimeoutError("exact provider request exceeded its absolute deadline")
        self._remaining()
        if failures:
            raise failures[0]

    def _guard_request_transport(self) -> None:
        """Forbid implicit reconnects and gate every request send by deadline."""

        original_send = getattr(self._connection, "send", None)
        if not callable(original_send):
            # Minimal test doubles may expose request() directly.  The real
            # HTTPSConnection always exposes send(), so production takes the
            # guarded path below.
            return

        def reject_reconnect() -> None:
            raise TimeoutError("exact provider transport cannot reconnect")

        def send_before_deadline(data: object) -> object:
            self._remaining()
            return original_send(data)

        # http.client otherwise reconnects automatically when the timer closes
        # the socket between connect() and request().  Exact invocation permits
        # one connection attempt only and must never emit bytes after expiry.
        self._connection.connect = reject_reconnect  # type: ignore[method-assign]
        self._connection.send = send_before_deadline  # type: ignore[method-assign]

    def _expire(self) -> None:
        self._expired.set()
        self._connection.close()

    def _remaining(self) -> float:
        remaining = self._deadline - time.monotonic()
        if self._expired.is_set():
            raise TimeoutError("exact provider request exceeded its absolute deadline")
        if remaining <= 0:
            self._expire()
            raise TimeoutError("exact provider request exceeded its absolute deadline")
        return remaining

    def _set_remaining_socket_timeout(self) -> None:
        remaining = self._remaining()
        if self._connection.sock is not None:
            self._connection.sock.settimeout(remaining)

    def read(self, maximum_bytes: int) -> bytes:
        if (
            isinstance(maximum_bytes, bool)
            or not isinstance(maximum_bytes, int)
            or maximum_bytes <= 0
            or self._response is None
        ):
            raise ValueError("exact response read bound is invalid")
        chunks: list[bytes] = []
        size = 0
        while size < maximum_bytes:
            self._set_remaining_socket_timeout()
            chunk = self._response.read1(min(65_536, maximum_bytes - size))
            self._remaining()
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        self._timer.cancel()
        if self._response is not None:
            self._response.close()
        self._connection.close()

    def __enter__(self) -> "_AbsoluteDeadlineResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        self.close()
        return False


def _open_without_redirects(request: urllib.request.Request, *, timeout_seconds: int):
    # http.client performs no redirects; the absolute deadline wrapper also
    # closes the active socket and checks remaining time between bounded reads.
    return _AbsoluteDeadlineResponse(request, timeout_seconds=timeout_seconds)


@dataclass(frozen=True, slots=True)
class OpenAICompatibleExactResult:
    """Bounded response returned only to the exact-model provider gateway."""

    response_text: str
    finish_reason: str | None


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
        result = self._request_once(
            prompt,
            max_tokens=int(os.getenv("OPENAI_COMPATIBLE_MAX_TOKENS", "1200")),
            timeout_seconds=90,
        )
        return result.response_text

    def generate_exact_once(
        self,
        prompt: str,
        *,
        purpose: str,
        connection_id: str,
        connection_revision_hash: str,
        model_profile_id: str,
        model_revision_hash: str,
        api_style: str,
        base_url: str,
        native_adapter_id: str | None,
        credential_reference: str,
        max_tokens: int,
        timeout_seconds: int,
        transport_receipt: object,
    ) -> OpenAICompatibleExactResult:
        """Make one exact-model request after the gateway consumed live evidence.

        This is deliberately separate from the legacy registry path.  The
        single-use transport authorization is minted from a consumed live-stage
        authorization.  Calling this adapter directly therefore cannot bypass
        the manual-session boundary.
        """

        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 512:
            raise ValueError("max_tokens must be between 1 and 512")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or not 1 <= timeout_seconds <= 30
        ):
            raise ValueError("timeout_seconds must be between 1 and 30")
        return self._request_once(
            prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            exact_transport={
                "receipt": transport_receipt,
                "purpose": purpose,
                "connection_id": connection_id,
                "connection_revision_hash": connection_revision_hash,
                "model_profile_id": model_profile_id,
                "model_revision_hash": model_revision_hash,
                "remote_model_id": self.model,
                "api_style": api_style,
                "base_url": base_url,
                "native_adapter_id": native_adapter_id,
                "credential_reference": credential_reference,
            },
        )

    def _request_once(
        self,
        prompt: str,
        *,
        max_tokens: int,
        timeout_seconds: int,
        exact_transport: dict[str, object] | None = None,
    ) -> OpenAICompatibleExactResult:
        if exact_transport is None:
            # A direct call to this lowest network function remains guarded by
            # the legacy registry; exact calls must instead consume a receipt.
            require_provider_calls_enabled(self.provider)
        else:
            try:
                from runtime.providers.exact_invocation import consume_gateway_transport_receipt
            except ModuleNotFoundError:  # pragma: no cover - script launch path
                from providers.exact_invocation import consume_gateway_transport_receipt

            exact_values = dict(exact_transport)
            receipt = exact_values.pop("receipt", None)
            consume_gateway_transport_receipt(
                receipt,
                prompt=prompt,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                **exact_values,
            )
            if os.environ.get("AOIA_PROVIDER_CALLS_ENABLED") != "1":
                raise RuntimeError(
                    "provider calls remain frozen; AOIA_PROVIDER_CALLS_ENABLED=1 is also required"
                )
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be non-empty text")
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
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
            with _open_without_redirects(request, timeout_seconds=timeout_seconds) as response:
                raw = response.read(_MAXIMUM_EXACT_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            # Response bodies can echo request material or credentials.  Keep
            # the error bounded to the status code at this trust boundary.
            raise RuntimeError(f"{self.provider} HTTP {error.code}") from error
        if len(raw) > _MAXIMUM_EXACT_RESPONSE_BYTES:
            raise ValueError("provider response exceeds the bounded byte limit")
        try:
            payload = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("provider response is not valid bounded JSON") from error

        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            raise ValueError("provider response did not match the expected schema") from error
        if not isinstance(content, str) or not content.strip():
            raise ValueError("provider response text is missing")
        if finish_reason is not None and finish_reason not in _ALLOWED_FINISH_REASONS:
            raise ValueError("provider response finish_reason is malformed")
        if exact_transport is not None and finish_reason != "stop":
            raise ValueError("exact provider response did not complete")
        return OpenAICompatibleExactResult(
            response_text=content.strip(),
            finish_reason=finish_reason,
        )
