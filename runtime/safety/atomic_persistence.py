from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import math
import os
import stat
import tempfile
import time
from collections.abc import Callable, Mapping
from numbers import Real
from pathlib import Path
from typing import Any, TypeVar


STATE_LOCK_TIMEOUT_REASON_CODE = "STATE_LOCK_TIMEOUT"
STATE_SERIALIZATION_FAILED_REASON_CODE = "STATE_SERIALIZATION_FAILED"
STATE_ATOMIC_WRITE_FAILED_REASON_CODE = "STATE_ATOMIC_WRITE_FAILED"
STATE_APPEND_FAILED_REASON_CODE = "STATE_APPEND_FAILED"
STATE_READ_FAILED_REASON_CODE = "STATE_READ_FAILED"
STATE_CORRUPT_REASON_CODE = "STATE_CORRUPT"

DEFAULT_STATE_LOCK_TIMEOUT_SECONDS = 5.0
MAX_STATE_LOCK_TIMEOUT_SECONDS = 300.0
LOCK_POLL_INTERVAL_SECONDS = 0.01


_UpdateResult = TypeVar("_UpdateResult")


class PersistenceError(RuntimeError):
    """Base error for explicit AOIA persistence-boundary failures."""

    reason_code = "PERSISTENCE_ERROR"

    def __init__(self, message: str, *, target_path: Path | None = None) -> None:
        super().__init__(message)
        self.target_path = target_path
        self.correlation: dict[str, str] = {}

    def attach_correlation(self, identity: Mapping[str, object]) -> PersistenceError:
        """Attach existing runtime identity without fabricating low-level IDs."""
        for field in ("request_id", "trace_id", "model_call_id", "action_id"):
            value = identity.get(field)
            if isinstance(value, str) and value.strip():
                self.correlation[field] = value
        return self


class StateLockTimeoutError(PersistenceError):
    reason_code = STATE_LOCK_TIMEOUT_REASON_CODE


class StateSerializationError(PersistenceError):
    reason_code = STATE_SERIALIZATION_FAILED_REASON_CODE


class AtomicWriteError(PersistenceError):
    reason_code = STATE_ATOMIC_WRITE_FAILED_REASON_CODE


class AppendWriteError(PersistenceError):
    reason_code = STATE_APPEND_FAILED_REASON_CODE


class PersistenceReadError(PersistenceError):
    reason_code = STATE_READ_FAILED_REASON_CODE


class StateCorruptionError(PersistenceError):
    reason_code = STATE_CORRUPT_REASON_CODE


def validate_lock_timeout_seconds(value: object) -> float:
    """Return a finite, bounded inter-process lock wait."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("state lock timeout must be a finite number of seconds")
    seconds = float(value)
    if not math.isfinite(seconds):
        raise ValueError("state lock timeout must be a finite number of seconds")
    if seconds < 0.0 or seconds > MAX_STATE_LOCK_TIMEOUT_SECONDS:
        raise ValueError("state lock timeout is outside runtime policy bounds")
    return seconds


def state_resource_lock_path(state_dir: Path, resource_path: Path) -> Path:
    """Return a stable per-resource lock beneath the canonical state directory."""
    state_root = Path(state_dir).resolve()
    target = Path(resource_path).resolve(strict=False)
    try:
        resource_key = target.relative_to(state_root.parent).as_posix()
    except ValueError:
        resource_key = str(target)
    digest = hashlib.sha256(resource_key.encode("utf-8")).hexdigest()[:16]
    readable_name = "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in target.name
    )[:80] or "state"
    return state_root / ".locks" / f"{readable_name}.{digest}.lock"


class InterProcessFileLock:
    """Bounded Linux inter-process exclusive lock backed by ``flock``."""

    def __init__(
        self,
        lock_path: Path,
        *,
        timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.lock_path = Path(lock_path)
        self.timeout_seconds = validate_lock_timeout_seconds(timeout_seconds)
        self._descriptor: int | None = None

    def __enter__(self) -> InterProcessFileLock:
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.lock_path, flags, 0o600)
        except OSError as exc:
            raise AtomicWriteError(
                "AOIA state lock could not be opened.",
                target_path=self.lock_path,
            ) from exc

        deadline = time.monotonic() + self.timeout_seconds
        try:
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._descriptor = descriptor
                    return self
                except BlockingIOError as exc:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0.0:
                        raise StateLockTimeoutError(
                            "AOIA state write blocked: inter-process lock timed out.",
                            target_path=self.lock_path,
                        ) from exc
                    time.sleep(min(LOCK_POLL_INTERVAL_SECONDS, remaining))
        except BaseException:
            os.close(descriptor)
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        descriptor = self._descriptor
        self._descriptor = None
        if descriptor is None:
            return
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def atomic_write_bytes(
    target_path: Path,
    payload: bytes,
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    mode: int = 0o600,
) -> None:
    """Atomically replace one locked state resource with complete bytes."""
    if not isinstance(payload, bytes):
        raise TypeError("atomic persistence payload must be bytes")
    target = Path(target_path)
    try:
        with InterProcessFileLock(lock_path, timeout_seconds=lock_timeout_seconds):
            _atomic_replace_bytes_unlocked(target, payload, mode=mode)
    except PersistenceError:
        raise
    except Exception as exc:
        raise AtomicWriteError(
            "AOIA atomic state write failed.",
            target_path=target,
        ) from exc


def atomic_write_text(
    target_path: Path,
    payload: str,
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    encoding: str = "utf-8",
    mode: int = 0o600,
) -> None:
    if not isinstance(payload, str):
        raise TypeError("atomic persistence text payload must be a string")
    try:
        encoded = payload.encode(encoding, errors="strict")
    except UnicodeError as exc:
        raise StateSerializationError(
            "AOIA state text serialization failed.",
            target_path=Path(target_path),
        ) from exc
    atomic_write_bytes(
        target_path,
        encoded,
        lock_path=lock_path,
        lock_timeout_seconds=lock_timeout_seconds,
        mode=mode,
    )


def atomic_write_json(
    target_path: Path,
    payload: Any,
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    indent: int | None = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    trailing_newline: bool = False,
    mode: int = 0o600,
) -> None:
    target = Path(target_path)
    try:
        text = json.dumps(
            payload,
            indent=indent,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StateSerializationError(
            "AOIA state JSON serialization failed.",
            target_path=target,
        ) from exc
    if trailing_newline:
        text += "\n"
    atomic_write_text(
        target,
        text,
        lock_path=lock_path,
        lock_timeout_seconds=lock_timeout_seconds,
        mode=mode,
    )


def append_json_line(
    target_path: Path,
    payload: Any,
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    mode: int = 0o600,
) -> None:
    """Serialize one complete JSON record, then append it under one lock."""
    target = Path(target_path)
    try:
        line = json.dumps(
            payload,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            separators=(",", ":") if sort_keys else None,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StateSerializationError(
            "AOIA append-log JSON serialization failed.",
            target_path=target,
        ) from exc
    append_text_line(
        target,
        line,
        lock_path=lock_path,
        lock_timeout_seconds=lock_timeout_seconds,
        mode=mode,
    )


def append_text_line(
    target_path: Path,
    line: str,
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    encoding: str = "utf-8",
    mode: int = 0o600,
) -> None:
    """Append exactly one pre-built logical line under an inter-process lock."""
    if not isinstance(line, str):
        raise TypeError("append-log record must be text")
    if "\n" in line or "\r" in line:
        raise StateSerializationError(
            "AOIA append-log record must contain exactly one logical line.",
            target_path=Path(target_path),
        )
    try:
        payload = (line + "\n").encode(encoding, errors="strict")
    except UnicodeError as exc:
        raise StateSerializationError(
            "AOIA append-log text serialization failed.",
            target_path=Path(target_path),
        ) from exc
    target = Path(target_path)
    try:
        with InterProcessFileLock(lock_path, timeout_seconds=lock_timeout_seconds):
            _append_bytes_unlocked(target, payload, mode=mode)
    except PersistenceError:
        raise
    except Exception as exc:
        raise AppendWriteError(
            "AOIA append-log write failed.",
            target_path=target,
        ) from exc


def locked_update_text(
    target_path: Path,
    update: Callable[[str], str],
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    default_text: str = "",
    encoding: str = "utf-8",
    mode: int = 0o600,
) -> None:
    """Serialize a read-modify-replace update for a text state resource."""
    target = Path(target_path)
    try:
        with InterProcessFileLock(lock_path, timeout_seconds=lock_timeout_seconds):
            if target.exists():
                try:
                    current = target.read_text(encoding=encoding, errors="strict")
                except (OSError, UnicodeError) as exc:
                    raise PersistenceReadError(
                        "AOIA text state could not be read for update.",
                        target_path=target,
                    ) from exc
            else:
                current = default_text
            replacement = update(current)
            if not isinstance(replacement, str):
                raise StateSerializationError(
                    "AOIA text state update did not produce text.",
                    target_path=target,
                )
            _atomic_replace_bytes_unlocked(
                target,
                replacement.encode(encoding, errors="strict"),
                mode=mode,
            )
    except PersistenceError:
        raise
    except Exception as exc:
        raise AtomicWriteError(
            "AOIA locked text state update failed.",
            target_path=target,
        ) from exc


def locked_update_json(
    target_path: Path,
    update: Callable[[Any | None], tuple[Any, _UpdateResult]],
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    indent: int | None = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    trailing_newline: bool = False,
    mode: int = 0o600,
) -> _UpdateResult:
    """Atomically read, transform, and replace one JSON resource under one lock.

    The callback receives ``None`` when the target does not exist and returns
    ``(replacement_payload, result)``. The result is returned only after the
    replacement is durable. Higher-level stores can therefore implement a
    compare-and-transition boundary without nesting a second ``flock`` or
    importing private atomic-write internals.
    """

    target = Path(target_path)
    try:
        with InterProcessFileLock(lock_path, timeout_seconds=lock_timeout_seconds):
            current: Any | None = None
            try:
                metadata = target.lstat()
            except FileNotFoundError:
                metadata = None
            if metadata is not None:
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                    raise StateCorruptionError(
                        "AOIA state snapshot target is not a safe regular file.",
                        target_path=target,
                    )
                flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                flags |= getattr(os, "O_NOFOLLOW", 0)
                try:
                    descriptor = os.open(target, flags)
                    with os.fdopen(descriptor, "r", encoding="utf-8", errors="strict") as handle:
                        opened = os.fstat(handle.fileno())
                        if (
                            not stat.S_ISREG(opened.st_mode)
                            or (opened.st_dev, opened.st_ino)
                            != (metadata.st_dev, metadata.st_ino)
                        ):
                            raise OSError("state snapshot changed during locked open")
                        raw = handle.read()
                except UnicodeError as exc:
                    raise StateCorruptionError(
                        "AOIA state snapshot is not valid UTF-8.",
                        target_path=target,
                    ) from exc
                except OSError as exc:
                    raise PersistenceReadError(
                        "AOIA state snapshot could not be read for update.",
                        target_path=target,
                    ) from exc
                try:
                    current = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise StateCorruptionError(
                        "AOIA state snapshot is corrupt JSON.",
                        target_path=target,
                    ) from exc

            replacement, result = update(current)
            try:
                text = json.dumps(
                    replacement,
                    indent=indent,
                    ensure_ascii=ensure_ascii,
                    sort_keys=sort_keys,
                    allow_nan=False,
                )
            except (TypeError, ValueError) as exc:
                raise StateSerializationError(
                    "AOIA state JSON serialization failed.",
                    target_path=target,
                ) from exc
            if trailing_newline:
                text += "\n"
            try:
                payload = text.encode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise StateSerializationError(
                    "AOIA state text serialization failed.",
                    target_path=target,
                ) from exc
            _atomic_replace_bytes_unlocked(target, payload, mode=mode)
            return result
    except PersistenceError:
        raise
    except OSError as exc:
        raise AtomicWriteError(
            "AOIA locked JSON state update failed.",
            target_path=target,
        ) from exc


def locked_unlink(
    target_path: Path,
    *,
    lock_path: Path,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    missing_ok: bool = True,
) -> None:
    target = Path(target_path)
    try:
        with InterProcessFileLock(lock_path, timeout_seconds=lock_timeout_seconds):
            target.unlink(missing_ok=missing_ok)
            _fsync_directory(target.parent)
    except PersistenceError:
        raise
    except Exception as exc:
        raise AtomicWriteError(
            "AOIA locked state removal failed.",
            target_path=target,
        ) from exc


def read_json_snapshot(target_path: Path) -> Any | None:
    """Read a complete JSON snapshot; missing and corrupt are distinct states."""
    target = Path(target_path)
    if not target.exists():
        return None
    try:
        raw = target.read_text(encoding="utf-8", errors="strict")
    except UnicodeError as exc:
        raise StateCorruptionError(
            "AOIA state snapshot is not valid UTF-8.",
            target_path=target,
        ) from exc
    except OSError as exc:
        raise PersistenceReadError(
            "AOIA state snapshot could not be read.",
            target_path=target,
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateCorruptionError(
            "AOIA state snapshot is corrupt JSON.",
            target_path=target,
        ) from exc


def _atomic_replace_bytes_unlocked(target: Path, payload: bytes, *, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    descriptor: int | None = None
    try:
        descriptor, raw_temporary_path = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(raw_temporary_path)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            written = handle.write(payload)
            if written != len(payload):
                raise OSError("short atomic state write")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
        _fsync_directory(target.parent)
    except PersistenceError:
        raise
    except Exception as exc:
        raise AtomicWriteError(
            "AOIA atomic state replacement failed.",
            target_path=target,
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                # Preserve the original failure; the unique temp name cannot
                # be mistaken for a completed target snapshot.
                pass


def _append_bytes_unlocked(target: Path, payload: bytes, *, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    original_size: int | None = None
    try:
        descriptor = os.open(target, flags, mode)
        original_size = os.fstat(descriptor).st_size
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short append-log write")
            view = view[written:]
        os.fsync(descriptor)
    except Exception:
        if descriptor is not None and original_size is not None:
            try:
                os.ftruncate(descriptor, original_size)
                os.fsync(descriptor)
            except OSError:
                pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not existed:
        _fsync_directory(target.parent)


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        unsupported = {
            errno.EBADF,
            errno.EINVAL,
            getattr(errno, "ENOTSUP", errno.EINVAL),
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        }
        if exc.errno in unsupported:
            return
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            unsupported = {
                errno.EBADF,
                errno.EINVAL,
                getattr(errno, "ENOTSUP", errno.EINVAL),
                getattr(errno, "EOPNOTSUPP", errno.EINVAL),
            }
            if exc.errno not in unsupported:
                raise
    finally:
        os.close(descriptor)
