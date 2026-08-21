from __future__ import annotations

"""Bounded, local-only resource controls for the AOIA operator HTTP server."""

import hashlib
import io
import math
import socket
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from typing import Callable, Mapping, TypeVar


WEB_MAX_CONCURRENT_REQUESTS_ENV = "AOIA_WEB_MAX_CONCURRENT_REQUESTS"
WEB_MAX_QUEUED_REQUESTS_ENV = "AOIA_WEB_MAX_QUEUED_REQUESTS"
WEB_LISTEN_BACKLOG_ENV = "AOIA_WEB_LISTEN_BACKLOG"
WEB_MAX_CLIENT_REQUESTS_ENV = "AOIA_WEB_MAX_CLIENT_REQUESTS"
WEB_HEADER_TIMEOUT_ENV = "AOIA_WEB_HEADER_TIMEOUT_SECONDS"
WEB_BODY_TIMEOUT_ENV = "AOIA_WEB_BODY_TIMEOUT_SECONDS"
WEB_WRITE_TIMEOUT_ENV = "AOIA_WEB_WRITE_TIMEOUT_SECONDS"
WEB_REQUEST_DEADLINE_ENV = "AOIA_WEB_REQUEST_DEADLINE_SECONDS"
WEB_RATE_WINDOW_ENV = "AOIA_WEB_RATE_WINDOW_SECONDS"
WEB_HEALTH_RATE_ENV = "AOIA_WEB_HEALTH_RATE_LIMIT"
WEB_READ_RATE_ENV = "AOIA_WEB_READ_RATE_LIMIT"
WEB_MUTATION_RATE_ENV = "AOIA_WEB_MUTATION_RATE_LIMIT"
WEB_RATE_MAX_ENTRIES_ENV = "AOIA_WEB_RATE_MAX_ENTRIES"
WEB_RATE_TTL_ENV = "AOIA_WEB_RATE_TTL_SECONDS"


@dataclass(frozen=True)
class WebResourceLimits:
    max_concurrent_requests: int = 8
    max_queued_requests: int = 16
    listen_backlog: int = 16
    max_client_requests: int = 4
    header_timeout_seconds: float = 5.0
    body_timeout_seconds: float = 15.0
    write_timeout_seconds: float = 5.0
    request_deadline_seconds: float = 120.0
    rate_window_seconds: float = 60.0
    health_rate_limit: int = 120
    read_rate_limit: int = 120
    mutation_rate_limit: int = 30
    rate_max_entries: int = 256
    rate_ttl_seconds: float = 120.0

    def __post_init__(self) -> None:
        _bounded_int("max_concurrent_requests", self.max_concurrent_requests, 1, 64)
        _bounded_int("max_queued_requests", self.max_queued_requests, 0, 256)
        _bounded_int("listen_backlog", self.listen_backlog, 1, 256)
        _bounded_int("max_client_requests", self.max_client_requests, 1, 64)
        if self.max_client_requests > self.max_concurrent_requests + self.max_queued_requests:
            raise ValueError("max_client_requests exceeds total request capacity")
        _bounded_float("header_timeout_seconds", self.header_timeout_seconds, 0.05, 60.0)
        _bounded_float("body_timeout_seconds", self.body_timeout_seconds, 0.05, 300.0)
        _bounded_float("write_timeout_seconds", self.write_timeout_seconds, 0.05, 60.0)
        _bounded_float("request_deadline_seconds", self.request_deadline_seconds, 0.1, 900.0)
        _bounded_float("rate_window_seconds", self.rate_window_seconds, 0.1, 3600.0)
        _bounded_int("health_rate_limit", self.health_rate_limit, 1, 100_000)
        _bounded_int("read_rate_limit", self.read_rate_limit, 1, 100_000)
        _bounded_int("mutation_rate_limit", self.mutation_rate_limit, 1, 100_000)
        _bounded_int("rate_max_entries", self.rate_max_entries, 1, 4096)
        _bounded_float("rate_ttl_seconds", self.rate_ttl_seconds, 0.1, 86_400.0)
        if self.rate_ttl_seconds < self.rate_window_seconds:
            raise ValueError("rate_ttl_seconds must cover the rate window")


def load_web_resource_limits(environ: Mapping[str, str]) -> WebResourceLimits:
    defaults = WebResourceLimits()
    try:
        return WebResourceLimits(
            max_concurrent_requests=_env_int(environ, WEB_MAX_CONCURRENT_REQUESTS_ENV, defaults.max_concurrent_requests),
            max_queued_requests=_env_int(environ, WEB_MAX_QUEUED_REQUESTS_ENV, defaults.max_queued_requests),
            listen_backlog=_env_int(environ, WEB_LISTEN_BACKLOG_ENV, defaults.listen_backlog),
            max_client_requests=_env_int(environ, WEB_MAX_CLIENT_REQUESTS_ENV, defaults.max_client_requests),
            header_timeout_seconds=_env_float(environ, WEB_HEADER_TIMEOUT_ENV, defaults.header_timeout_seconds),
            body_timeout_seconds=_env_float(environ, WEB_BODY_TIMEOUT_ENV, defaults.body_timeout_seconds),
            write_timeout_seconds=_env_float(environ, WEB_WRITE_TIMEOUT_ENV, defaults.write_timeout_seconds),
            request_deadline_seconds=_env_float(environ, WEB_REQUEST_DEADLINE_ENV, defaults.request_deadline_seconds),
            rate_window_seconds=_env_float(environ, WEB_RATE_WINDOW_ENV, defaults.rate_window_seconds),
            health_rate_limit=_env_int(environ, WEB_HEALTH_RATE_ENV, defaults.health_rate_limit),
            read_rate_limit=_env_int(environ, WEB_READ_RATE_ENV, defaults.read_rate_limit),
            mutation_rate_limit=_env_int(environ, WEB_MUTATION_RATE_ENV, defaults.mutation_rate_limit),
            rate_max_entries=_env_int(environ, WEB_RATE_MAX_ENTRIES_ENV, defaults.rate_max_entries),
            rate_ttl_seconds=_env_float(environ, WEB_RATE_TTL_ENV, defaults.rate_ttl_seconds),
        )
    except (TypeError, ValueError) as error:
        raise ValueError("AOIA web resource policy is invalid") from error


T = TypeVar("T")


class BoundedExecutor:
    """Thread pool whose running plus queued work is strictly bounded."""

    def __init__(self, *, max_workers: int, max_queue: int, thread_name_prefix: str) -> None:
        _bounded_int("max_workers", max_workers, 1, 64)
        _bounded_int("max_queue", max_queue, 0, 256)
        self._permits = BoundedSemaphore(max_workers + max_queue)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
        )

    def submit(self, function: Callable[..., T], /, *args, **kwargs) -> Future[T] | None:
        if not self._permits.acquire(blocking=False):
            return None
        try:
            future = self._executor.submit(function, *args, **kwargs)
        except BaseException:
            self._permits.release()
            raise
        future.add_done_callback(self._release)
        return future

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _release(self, _future: Future[object]) -> None:
        self._permits.release()


@dataclass
class _Bucket:
    tokens: float
    updated_at: float
    last_seen: float


class BoundedRateLimiter:
    """Lock-protected token buckets with monotonic expiry and bounded keys."""

    def __init__(
        self,
        *,
        max_entries: int,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        _bounded_int("max_entries", max_entries, 1, 4096)
        _bounded_float("ttl_seconds", ttl_seconds, 0.1, 86_400.0)
        self._max_entries = max_entries
        self._ttl_seconds = float(ttl_seconds)
        self._clock = clock
        self._buckets: dict[tuple[str, bytes], _Bucket] = {}
        self._lock = Lock()

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._buckets)

    def allow(self, scope: str, client_key: bytes, *, capacity: int, window_seconds: float) -> bool:
        _bounded_int("capacity", capacity, 1, 100_000)
        _bounded_float("window_seconds", window_seconds, 0.1, 3600.0)
        if not isinstance(scope, str) or not scope or not isinstance(client_key, bytes) or not client_key:
            return False
        now = float(self._clock())
        if not math.isfinite(now):
            return False
        key = (scope, client_key)
        with self._lock:
            self._prune(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                if len(self._buckets) >= self._max_entries:
                    return False
                bucket = _Bucket(float(capacity), now, now)
                self._buckets[key] = bucket
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(float(capacity), bucket.tokens + elapsed * capacity / window_seconds)
            bucket.updated_at = max(bucket.updated_at, now)
            bucket.last_seen = max(bucket.last_seen, now)
            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True

    def _prune(self, now: float) -> None:
        expired = [
            key
            for key, bucket in self._buckets.items()
            if now >= bucket.last_seen and now - bucket.last_seen >= self._ttl_seconds
        ]
        for key in expired:
            self._buckets.pop(key, None)


class ClientActivityLimiter:
    """Bound per-client accepted requests without trusting HTTP headers."""

    def __init__(self, *, max_clients: int, max_per_client: int) -> None:
        _bounded_int("max_clients", max_clients, 1, 320)
        _bounded_int("max_per_client", max_per_client, 1, 64)
        self._max_clients = max_clients
        self._max_per_client = max_per_client
        self._counts: dict[bytes, int] = {}
        self._lock = Lock()

    def acquire(self, client_key: bytes) -> bool:
        if not client_key:
            return False
        with self._lock:
            count = self._counts.get(client_key, 0)
            if count >= self._max_per_client:
                return False
            if count == 0 and len(self._counts) >= self._max_clients:
                return False
            self._counts[client_key] = count + 1
            return True

    def release(self, client_key: bytes) -> None:
        with self._lock:
            count = self._counts.get(client_key, 0)
            if count <= 1:
                self._counts.pop(client_key, None)
            else:
                self._counts[client_key] = count - 1


class DeadlineReadTimeout(TimeoutError):
    pass


class DeadlineSocketReader(io.RawIOBase):
    """Raw socket reader enforcing inactivity and absolute phase deadlines."""

    def __init__(
        self,
        connection: socket.socket,
        *,
        timeout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self._connection = connection
        self._clock = clock
        self._timeout_seconds = float(timeout_seconds)
        self._deadline = float(clock()) + self._timeout_seconds

    def readable(self) -> bool:
        return True

    def fileno(self) -> int:
        return self._connection.fileno()

    def set_phase_timeout(self, timeout_seconds: float) -> None:
        _bounded_float("timeout_seconds", timeout_seconds, 0.000001, 300.0)
        self._timeout_seconds = float(timeout_seconds)
        self._deadline = float(self._clock()) + self._timeout_seconds

    def readinto(self, buffer) -> int:
        remaining = self._deadline - float(self._clock())
        if remaining <= 0:
            raise DeadlineReadTimeout("request read deadline expired")
        self._connection.settimeout(max(0.000001, min(self._timeout_seconds, remaining)))
        try:
            count = self._connection.recv_into(buffer)
        except (socket.timeout, TimeoutError) as error:
            raise DeadlineReadTimeout("request read deadline expired") from error
        if float(self._clock()) > self._deadline:
            raise DeadlineReadTimeout("request read deadline expired")
        return count


class DeadlineSocketWriter(io.RawIOBase):
    """Raw socket writer that cannot extend an absolute response deadline."""

    def __init__(
        self,
        connection: socket.socket,
        *,
        timeout_seconds: float,
        deadline: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self._connection = connection
        self._clock = clock
        self.set_deadline(deadline=deadline, timeout_seconds=timeout_seconds)

    def writable(self) -> bool:
        return True

    def fileno(self) -> int:
        return self._connection.fileno()

    def set_deadline(self, *, deadline: float, timeout_seconds: float) -> None:
        _bounded_float("timeout_seconds", timeout_seconds, 0.000001, 60.0)
        if not isinstance(deadline, (int, float)) or not math.isfinite(float(deadline)):
            raise ValueError("deadline is invalid")
        self._deadline = float(deadline)
        self._timeout_seconds = float(timeout_seconds)

    def write(self, buffer) -> int:
        remaining = self._deadline - float(self._clock())
        if remaining <= 0:
            raise TimeoutError("response write deadline expired")
        self._connection.settimeout(
            max(0.000001, min(self._timeout_seconds, remaining))
        )
        try:
            count = self._connection.send(buffer)
        except (socket.timeout, TimeoutError) as error:
            raise TimeoutError("response write deadline expired") from error
        if float(self._clock()) > self._deadline:
            raise TimeoutError("response write deadline expired")
        return count


def client_key(client_address: object) -> bytes:
    try:
        host = str(client_address[0])  # type: ignore[index]
    except (IndexError, TypeError):
        host = "unknown"
    return hashlib.sha256(host.encode("utf-8", errors="replace")).digest()


def _env_int(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    if not isinstance(raw, str) or not raw or len(raw) > 10 or not raw.isascii() or not raw.isdigit():
        raise ValueError(name)
    return int(raw, 10)


def _env_float(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = environ.get(name)
    if raw is None:
        return default
    if not isinstance(raw, str) or not raw or len(raw) > 32 or not raw.isascii():
        raise ValueError(name)
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(name)
    return value


def _bounded_int(name: str, value: object, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the supported bound")
    return value


def _bounded_float(name: str, value: object, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} is outside the supported bound")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{name} is outside the supported bound")
    return number
