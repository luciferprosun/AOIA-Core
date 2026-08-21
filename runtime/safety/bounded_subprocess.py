from __future__ import annotations

import base64
import codecs
import json
import locale
import math
import os
import select
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from numbers import Real
from os import PathLike
from pathlib import Path
from types import MappingProxyType
from typing import Any


SUBPROCESS_HARD_TIMEOUT_REASON_CODE = "SUBPROCESS_HARD_TIMEOUT"
PROCESS_CPU_LIMIT_REASON_CODE = "PROCESS_CPU_LIMIT"
PROCESS_MEMORY_LIMIT_REASON_CODE = "PROCESS_MEMORY_LIMIT"
PROCESS_FILE_LIMIT_REASON_CODE = "PROCESS_FILE_LIMIT"
PROCESS_COUNT_LIMIT_REASON_CODE = "PROCESS_COUNT_LIMIT"
PROCESS_TREE_TERMINATED_REASON_CODE = "PROCESS_TREE_TERMINATED"
PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE = "PROCESS_CONTAINMENT_SETUP_FAILED"
PROCESS_CONTAINMENT_LOST_REASON_CODE = "PROCESS_CONTAINMENT_LOST"
MIN_HARD_TIMEOUT_SECONDS = 0.01
MAX_HARD_TIMEOUT_SECONDS = 600.0

_SUPERVISOR_SCHEMA = "AOIA_SUBPROCESS_SUPERVISOR_1A"
_SUPERVISOR_PATH = Path(__file__).with_name("subprocess_supervisor.py")
_REPORT_LIMIT_BYTES = 32 * 1024
_CLEANUP_ALLOWANCE_SECONDS = 2.0
_SUPERVISOR_WALL_ALLOWANCE_SECONDS = 4.0
_PIPE_EOF_ALLOWANCE_SECONDS = 0.75


class SubprocessTimeoutPolicyError(ValueError):
    """Raised before process creation when a hard timeout is missing or unsafe."""


class SubprocessContainmentError(RuntimeError):
    """Fail closed when tree containment cannot prove durable terminal truth."""

    def __init__(self, reason_code: str = PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE) -> None:
        self.reason_code = reason_code
        super().__init__("bounded subprocess containment did not prove a safe terminal state")


class SubprocessCancelledError(RuntimeError):
    """A runtime-owned cancellation was fenced before process dispatch."""

    reason_code = "TASK_CANCELLED"

    def __init__(self, cmd: Sequence[str]) -> None:
        self.cmd = tuple(cmd)
        super().__init__("bounded subprocess was cancelled before dispatch")


class SubprocessResourceLimitError(subprocess.CalledProcessError):
    def __init__(
        self,
        returncode: int,
        cmd: Sequence[str],
        reason_code: str,
        *,
        output: Any = None,
        stderr: Any = None,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
        tree_cleanup_intervened: bool = False,
        resource_usage: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(returncode, cmd, output=output, stderr=stderr)
        self.reason_code = reason_code
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated
        self.tree_cleanup_intervened = tree_cleanup_intervened
        self.resource_usage = resource_usage


class SubprocessTreeTimeoutExpired(subprocess.TimeoutExpired):
    reason_code = SUBPROCESS_HARD_TIMEOUT_REASON_CODE
    containment_reason_code = PROCESS_TREE_TERMINATED_REASON_CODE

    def __init__(
        self,
        cmd: Sequence[str],
        timeout: float,
        *,
        output: Any = None,
        stderr: Any = None,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
        tree_cleanup_intervened: bool = True,
        resource_usage: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(cmd, timeout, output=output, stderr=stderr)
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated
        self.tree_cleanup_intervened = tree_cleanup_intervened
        self.resource_usage = resource_usage


class SubprocessResourceProfileName(str, Enum):
    CONTROLLED_TEST = "CONTROLLED_TEST"
    GIT = "GIT"
    PDF = "PDF"
    PACKAGE = "PACKAGE"
    SCEMDA = "SCEMDA"
    INTERNAL_UTILITY = "INTERNAL_UTILITY"


@dataclass(frozen=True)
class SubprocessResourceProfile:
    name: SubprocessResourceProfileName
    cpu_seconds: int
    address_space_bytes: int
    tree_memory_bytes: int
    open_files: int
    max_tasks: int
    file_size_bytes: int | None
    max_capture_bytes: int


_MIB = 1024 * 1024
_GIB = 1024 * _MIB
SUBPROCESS_RESOURCE_PROFILES: Mapping[
    SubprocessResourceProfileName, SubprocessResourceProfile
] = MappingProxyType(
    {
        SubprocessResourceProfileName.CONTROLLED_TEST: SubprocessResourceProfile(
            SubprocessResourceProfileName.CONTROLLED_TEST, 180, 1 * _GIB, 1280 * _MIB, 256, 16, 512 * _MIB, 4 * _MIB
        ),
        SubprocessResourceProfileName.GIT: SubprocessResourceProfile(
            # Git writes source/index/pack files, so RLIMIT_FSIZE could corrupt
            # repository state. Pipe capture is still independently bounded.
            SubprocessResourceProfileName.GIT, 180, 1 * _GIB, 1280 * _MIB, 256, 16, None, 4 * _MIB
        ),
        SubprocessResourceProfileName.PDF: SubprocessResourceProfile(
            SubprocessResourceProfileName.PDF, 120, 768 * _MIB, 768 * _MIB, 128, 8, 1 * _GIB, 2 * _MIB
        ),
        SubprocessResourceProfileName.PACKAGE: SubprocessResourceProfile(
            SubprocessResourceProfileName.PACKAGE, 300, 1536 * _MIB, 1536 * _MIB, 512, 24, 2 * _GIB, 4 * _MIB
        ),
        SubprocessResourceProfileName.SCEMDA: SubprocessResourceProfile(
            SubprocessResourceProfileName.SCEMDA, 120, 1 * _GIB, 1 * _GIB, 256, 12, 512 * _MIB, 2 * _MIB
        ),
        SubprocessResourceProfileName.INTERNAL_UTILITY: SubprocessResourceProfile(
            SubprocessResourceProfileName.INTERNAL_UTILITY, 180, 768 * _MIB, 768 * _MIB, 256, 12, 512 * _MIB, 2 * _MIB
        ),
    }
)


class BoundedCompletedProcess(subprocess.CompletedProcess[Any]):
    def __init__(
        self,
        args: Sequence[str],
        returncode: int,
        stdout: Any,
        stderr: Any,
        *,
        stdout_truncated: bool,
        stderr_truncated: bool,
        resource_profile: str,
        resource_usage: Mapping[str, Any] | None,
    ) -> None:
        super().__init__(args, returncode, stdout, stderr)
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated
        self.resource_profile = resource_profile
        self.resource_usage = resource_usage


class _BoundedCollector:
    def __init__(self, stream: Any, limit: int, label: str) -> None:
        self._stream = stream
        self._limit = limit
        self._buffer = bytearray()
        self.total_bytes = 0
        self.error: BaseException | None = None
        self._stop = threading.Event()
        self.reached_eof = False
        self._thread = threading.Thread(
            target=self._drain,
            name=f"aoia-bounded-{label}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def join(self) -> None:
        self._thread.join(_PIPE_EOF_ALLOWANCE_SECONDS)
        if self._thread.is_alive():
            self._stop.set()
            self._thread.join(_PIPE_EOF_ALLOWANCE_SECONDS)
        if self._thread.is_alive() or self.error is not None or not self.reached_eof:
            raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE) from self.error

    def value(self) -> bytes:
        return bytes(self._buffer)

    def abort(self) -> None:
        self._stop.set()
        self._thread.join(_PIPE_EOF_ALLOWANCE_SECONDS)
        if self._thread.is_alive():
            try:
                self._stream.close()
            except OSError:
                pass
            self._thread.join(_PIPE_EOF_ALLOWANCE_SECONDS)

    @property
    def truncated(self) -> bool:
        return self.total_bytes > self._limit

    def _drain(self) -> None:
        try:
            fd = self._stream.fileno()
            os.set_blocking(fd, False)
            while True:
                if self._stop.is_set():
                    return
                ready, _, _ = select.select((fd,), (), (), 0.05)
                if not ready:
                    continue
                try:
                    chunk = os.read(fd, 64 * 1024)
                except BlockingIOError:
                    continue
                if not chunk:
                    self.reached_eof = True
                    break
                self.total_bytes += len(chunk)
                remaining = self._limit - len(self._buffer)
                if remaining > 0:
                    self._buffer.extend(chunk[:remaining])
        except BaseException as exc:
            self.error = exc
        finally:
            try:
                self._stream.close()
            except OSError:
                pass


def validate_hard_timeout_seconds(value: object) -> float:
    """Return a finite hard timeout within the runtime-owned global bounds."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout must be a finite number of seconds"
        )
    try:
        seconds = float(value)
    except OverflowError as exc:
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout must be a finite number of seconds"
        ) from exc
    if not math.isfinite(seconds):
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout must be a finite number of seconds"
        )
    if seconds < MIN_HARD_TIMEOUT_SECONDS or seconds > MAX_HARD_TIMEOUT_SECONDS:
        raise SubprocessTimeoutPolicyError(
            "subprocess hard timeout is outside runtime policy bounds"
        )
    return seconds


def _profile(value: SubprocessResourceProfileName | str) -> SubprocessResourceProfile:
    try:
        name = value if isinstance(value, SubprocessResourceProfileName) else SubprocessResourceProfileName(value)
    except (TypeError, ValueError) as exc:
        raise SubprocessTimeoutPolicyError("unknown subprocess resource profile") from exc
    return SUBPROCESS_RESOURCE_PROFILES[name]


def _encoded_config(profile: SubprocessResourceProfile, seconds: float, executable: str | None) -> str:
    payload = {
        "schema": _SUPERVISOR_SCHEMA,
        "timeout_seconds": seconds,
        "cpu_seconds": profile.cpu_seconds,
        "address_space_bytes": profile.address_space_bytes,
        "tree_memory_bytes": profile.tree_memory_bytes,
        "open_files": profile.open_files,
        "max_tasks": profile.max_tasks,
        "file_size_bytes": profile.file_size_bytes,
        "executable": executable,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _reports(raw: bytes) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not raw or len(raw) > _REPORT_LIMIT_BYTES:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    records: list[dict[str, Any]] = []
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("duplicate report field")
            result[name] = value
        return result
    try:
        for line in raw.splitlines():
            value = json.loads(line.decode("utf-8"), object_pairs_hook=reject_duplicates)
            if not isinstance(value, dict) or value.get("schema") != _SUPERVISOR_SCHEMA:
                raise ValueError("bad report")
            records.append(value)
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE) from exc
    if len(records) not in {1, 2} or records[-1].get("event") != "TERMINAL":
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    started = records[0] if len(records) == 2 else None
    if started is not None:
        if started.get("event") != "STARTED" or set(started) != {
            "schema", "event", "target_pid", "target_start_time"
        }:
            raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
        for name in ("target_pid", "target_start_time"):
            if isinstance(started.get(name), bool) or not isinstance(started.get(name), int) or started[name] <= 0:
                raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    terminal = records[-1]
    minimal_setup_fields = {"schema", "event", "containment_status", "reason_code"}
    full_fields = {
        "schema", "event", "containment_status", "reason_code", "timed_out",
        "cleanup_proven", "target_pid", "returncode", "usage",
        "tree_cleanup_intervened",
    }
    if set(terminal) == minimal_setup_fields:
        if (
            started is not None
            or terminal.get("containment_status") != "FAILED"
            or terminal.get("reason_code") != PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE
        ):
            raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
        return None, terminal
    if set(terminal) != full_fields:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if terminal.get("containment_status") != "CONTAINED" or terminal.get("cleanup_proven") is not True:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if not isinstance(terminal.get("timed_out"), bool) or not isinstance(terminal.get("tree_cleanup_intervened"), bool):
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    target_pid = terminal.get("target_pid")
    returncode = terminal.get("returncode")
    if target_pid is not None and (isinstance(target_pid, bool) or not isinstance(target_pid, int) or target_pid <= 0):
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if returncode is not None and (isinstance(returncode, bool) or not isinstance(returncode, int)):
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if started is not None and target_pid != started["target_pid"]:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    reason = terminal.get("reason_code")
    allowed_reasons = {
        None,
        SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
        PROCESS_CPU_LIMIT_REASON_CODE,
        PROCESS_MEMORY_LIMIT_REASON_CODE,
        PROCESS_FILE_LIMIT_REASON_CODE,
        PROCESS_COUNT_LIMIT_REASON_CODE,
        PROCESS_TREE_TERMINATED_REASON_CODE,
        PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE,
    }
    if reason not in allowed_reasons:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if started is None and reason not in {
        PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE,
        PROCESS_TREE_TERMINATED_REASON_CODE,
    }:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if started is not None and reason == PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if terminal["timed_out"] is not (reason == SUBPROCESS_HARD_TIMEOUT_REASON_CODE):
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    cleanup_intervened = terminal["tree_cleanup_intervened"]
    if reason is None and cleanup_intervened:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if reason in {
        SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
        PROCESS_MEMORY_LIMIT_REASON_CODE,
        PROCESS_COUNT_LIMIT_REASON_CODE,
        PROCESS_TREE_TERMINATED_REASON_CODE,
        PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE,
    } and not cleanup_intervened:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if reason == PROCESS_CPU_LIMIT_REASON_CODE and returncode != -signal.SIGXCPU:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if reason == PROCESS_FILE_LIMIT_REASON_CODE and returncode != -signal.SIGXFSZ:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    usage = terminal.get("usage")
    if usage is not None:
        if set(usage) != {"user_seconds", "system_seconds", "max_rss_kib"}:
            raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value < 0
            for value in usage.values()
        ):
            raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    return started, terminal


def _validate_supervisor_exit_status(
    returncode: int,
    started: dict[str, Any] | None,
    terminal: dict[str, Any],
) -> None:
    minimal_setup = set(terminal) == {
        "schema",
        "event",
        "containment_status",
        "reason_code",
    }
    if minimal_setup:
        if started is not None or returncode != 125:
            raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
        return
    if returncode != 0:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)


def _decoded(
    value: bytes | None,
    *,
    text_mode: bool,
    encoding: str | None,
    errors: str | None,
    truncated: bool,
) -> Any:
    if value is None or not text_mode:
        return value
    codec = encoding or locale.getpreferredencoding(False)
    if truncated:
        decoder = codecs.getincrementaldecoder(codec)(errors or "strict")
        text = decoder.decode(value, final=False)
    else:
        text = value.decode(codec, errors or "strict")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _stop_supervisor(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=_CLEANUP_ALLOWANCE_SECONDS)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=_CLEANUP_ALLOWANCE_SECONDS)
            except subprocess.TimeoutExpired as exc:
                raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE) from exc


def _send_cancellation(fd: int) -> None:
    try:
        os.write(fd, b"C")
    except (BrokenPipeError, OSError):
        # Supervisor exit/protocol validation below remains authoritative.
        pass


def run_bounded_subprocess(
    args: Sequence[str | bytes | PathLike[str] | PathLike[bytes]],
    *,
    env: Mapping[str, str],
    timeout: object,
    resource_profile: SubprocessResourceProfileName | str,
    cancel_event: threading.Event | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run one Linux process tree through the fresh trusted supervisor."""
    seconds = validate_hard_timeout_seconds(timeout)
    selected = _profile(resource_profile)
    if cancel_event is not None and (
        not hasattr(cancel_event, "is_set") or not callable(cancel_event.is_set)
    ):
        raise SubprocessTimeoutPolicyError("cancel_event must expose is_set()")
    if sys.platform != "linux" or not _SUPERVISOR_PATH.is_file():
        raise SubprocessContainmentError()
    if kwargs.pop("shell", False) is not False:
        raise SubprocessTimeoutPolicyError(
            "bounded subprocess execution does not permit shell=True"
        )
    for name in ("preexec_fn", "start_new_session", "process_group", "pass_fds"):
        if name in kwargs:
            raise SubprocessTimeoutPolicyError(f"subprocess option {name} is runtime-owned")
    if kwargs.pop("close_fds", True) is False:
        raise SubprocessTimeoutPolicyError("bounded subprocess execution requires close_fds")

    if isinstance(args, (str, bytes, os.PathLike)):
        raise SubprocessTimeoutPolicyError("bounded subprocess args must be a sequence, not bare text")
    target_args = [os.fsdecode(os.fspath(value)) for value in args]
    if not target_args or any("\x00" in value for value in target_args):
        raise SubprocessTimeoutPolicyError("bounded subprocess args must be non-empty safe text")
    if cancel_event is not None and cancel_event.is_set():
        # Fence a cancellation that is already authoritative before creating
        # the supervisor.  No target process can be dispatched on this path.
        raise SubprocessCancelledError(target_args)
    child_env = {str(name): str(value) for name, value in env.items()}
    executable_value = kwargs.pop("executable", None)
    executable = None if executable_value is None else os.fsdecode(executable_value)
    if executable is not None and (not executable or "\x00" in executable):
        raise SubprocessTimeoutPolicyError("bounded subprocess executable must be safe text")
    capture_output = kwargs.pop("capture_output", False)
    check = kwargs.pop("check", False)
    input_value = kwargs.pop("input", None)
    text_value = kwargs.pop("text", None)
    universal_newlines = kwargs.pop("universal_newlines", None)
    encoding = kwargs.pop("encoding", None)
    errors = kwargs.pop("errors", None)
    if text_value is not None and universal_newlines is not None and bool(text_value) != bool(universal_newlines):
        raise SubprocessTimeoutPolicyError("conflicting text mode options")
    text_mode = bool(text_value or universal_newlines or encoding or errors)
    stdout_spec = kwargs.pop("stdout", None)
    stderr_spec = kwargs.pop("stderr", None)
    stdin_spec = kwargs.pop("stdin", None)
    if capture_output:
        if stdout_spec is not None or stderr_spec is not None:
            raise ValueError("stdout and stderr arguments may not be used with capture_output")
        stdout_spec = stderr_spec = subprocess.PIPE
    if input_value is not None:
        if stdin_spec is not None:
            raise ValueError("stdin and input arguments may not both be used")
        stdin_spec = subprocess.PIPE
    if input_value is None:
        input_bytes = None
    elif isinstance(input_value, str):
        if not text_mode:
            raise TypeError("write() argument must be bytes")
        input_bytes = input_value.encode(encoding or locale.getpreferredencoding(False), errors or "strict")
    else:
        input_bytes = bytes(input_value)
    if input_bytes is not None and len(input_bytes) > selected.max_capture_bytes:
        raise SubprocessTimeoutPolicyError("bounded subprocess input exceeds the resource profile")

    report_r, report_w = os.pipe2(os.O_CLOEXEC)
    cancel_r, cancel_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
    config = _encoded_config(selected, seconds, executable)
    supervisor_args = [
        sys.executable,
        "-I",
        str(_SUPERVISOR_PATH),
        str(report_w),
        str(cancel_r),
        config,
        *target_args,
    ]
    process: subprocess.Popen[bytes] | None = None
    stdout_collector = stderr_collector = report_collector = None
    writer: threading.Thread | None = None
    input_stop = threading.Event()
    cancellation_sent = False
    try:
        process = subprocess.Popen(
            supervisor_args,
            env=child_env,
            stdin=stdin_spec,
            stdout=stdout_spec,
            stderr=stderr_spec,
            start_new_session=True,
            pass_fds=(report_w, cancel_r),
            close_fds=True,
            **kwargs,
        )
        os.close(report_w)
        report_w = -1
        os.close(cancel_r)
        cancel_r = -1
        report_stream = os.fdopen(report_r, "rb", buffering=0)
        report_r = -1
        report_collector = _BoundedCollector(report_stream, _REPORT_LIMIT_BYTES, "report")
        report_collector.start()
        if process.stdout is not None:
            stdout_collector = _BoundedCollector(process.stdout, selected.max_capture_bytes, "stdout")
            stdout_collector.start()
        if process.stderr is not None:
            stderr_collector = _BoundedCollector(process.stderr, selected.max_capture_bytes, "stderr")
            stderr_collector.start()
        if process.stdin is not None:
            def write_input() -> None:
                try:
                    fd = process.stdin.fileno()
                    os.set_blocking(fd, False)
                    view = memoryview(input_bytes or b"")
                    while view and not input_stop.is_set():
                        _, writable, _ = select.select((), (fd,), (), 0.05)
                        if not writable:
                            continue
                        try:
                            written = os.write(fd, view)
                        except BlockingIOError:
                            continue
                        view = view[written:]
                except (BrokenPipeError, OSError, ValueError):
                    pass
                finally:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass

            writer = threading.Thread(
                target=write_input,
                name="aoia-bounded-input",
                daemon=True,
            )
            writer.start()
        outer_deadline = time.monotonic() + seconds + _SUPERVISOR_WALL_ALLOWANCE_SECONDS
        while process.poll() is None:
            if (
                not cancellation_sent
                and cancel_event is not None
                and cancel_event.is_set()
            ):
                _send_cancellation(cancel_w)
                cancellation_sent = True
                os.close(cancel_w)
                cancel_w = -1
            remaining = outer_deadline - time.monotonic()
            if remaining <= 0:
                _stop_supervisor(process)
                break
            try:
                process.wait(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                continue
        if writer is not None:
            writer.join(_PIPE_EOF_ALLOWANCE_SECONDS)
            if writer.is_alive():
                input_stop.set()
                writer.join(_PIPE_EOF_ALLOWANCE_SECONDS)
            if writer.is_alive():
                raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
        for collector in (stdout_collector, stderr_collector, report_collector):
            if collector is not None:
                collector.join()
    except BaseException:
        input_stop.set()
        if process is not None:
            _stop_supervisor(process)
        for collector in (stdout_collector, stderr_collector, report_collector):
            if collector is not None:
                collector.abort()
        raise
    finally:
        for fd in (report_r, report_w, cancel_r, cancel_w):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass

    assert process is not None and report_collector is not None
    stdout_raw = None if stdout_collector is None else stdout_collector.value()
    stderr_raw = None if stderr_collector is None else stderr_collector.value()
    stdout_truncated = False if stdout_collector is None else stdout_collector.truncated
    stderr_truncated = False if stderr_collector is None else stderr_collector.truncated
    if report_collector.truncated:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    started, terminal = _reports(report_collector.value())
    _validate_supervisor_exit_status(process.returncode, started, terminal)
    reason = terminal.get("reason_code")
    returncode = terminal.get("returncode")
    if returncode is not None and (isinstance(returncode, bool) or not isinstance(returncode, int)):
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    if reason == SUBPROCESS_HARD_TIMEOUT_REASON_CODE and terminal.get("timed_out") is True:
        raise SubprocessTreeTimeoutExpired(
            target_args,
            seconds,
            # Match subprocess.run: TimeoutExpired carries captured bytes even
            # when text=True. The bounded prefix/truncation metadata remains.
            output=stdout_raw,
            stderr=stderr_raw,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            tree_cleanup_intervened=terminal["tree_cleanup_intervened"],
            resource_usage=terminal.get("usage"),
        )
    if (
        cancellation_sent
        and started is None
        and reason == PROCESS_TREE_TERMINATED_REASON_CODE
    ):
        raise SubprocessCancelledError(target_args)
    if reason == PROCESS_CONTAINMENT_SETUP_FAILED_REASON_CODE:
        raise SubprocessContainmentError()
    if reason in {
        PROCESS_CPU_LIMIT_REASON_CODE,
        PROCESS_MEMORY_LIMIT_REASON_CODE,
        PROCESS_FILE_LIMIT_REASON_CODE,
        PROCESS_COUNT_LIMIT_REASON_CODE,
        PROCESS_TREE_TERMINATED_REASON_CODE,
    }:
        raise SubprocessResourceLimitError(
            125 if returncode is None else returncode,
            target_args,
            reason,
            # A typed resource terminal is authoritative. Preserve bounded raw
            # bytes so malformed text cannot mask it with UnicodeDecodeError.
            output=stdout_raw,
            stderr=stderr_raw,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            tree_cleanup_intervened=terminal["tree_cleanup_intervened"],
            resource_usage=terminal.get("usage"),
        )
    if reason is not None or returncode is None:
        raise SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
    # Strict text decoding is a compatibility behavior only after ordinary
    # contained completion has been proven. It cannot override stronger
    # timeout/resource/containment terminal truth above.
    stdout = _decoded(
        stdout_raw, text_mode=text_mode, encoding=encoding, errors=errors, truncated=stdout_truncated
    )
    stderr = _decoded(
        stderr_raw, text_mode=text_mode, encoding=encoding, errors=errors, truncated=stderr_truncated
    )
    completed = BoundedCompletedProcess(
        target_args,
        returncode,
        stdout,
        stderr,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        resource_profile=selected.name.value,
        resource_usage=terminal.get("usage") if isinstance(terminal.get("usage"), dict) else None,
    )
    if check and returncode:
        error = subprocess.CalledProcessError(returncode, target_args, output=stdout, stderr=stderr)
        error.stdout_truncated = stdout_truncated  # type: ignore[attr-defined]
        error.stderr_truncated = stderr_truncated  # type: ignore[attr-defined]
        raise error
    return completed
