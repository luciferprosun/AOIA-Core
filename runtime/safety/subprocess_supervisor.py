from __future__ import annotations

"""Trusted single-threaded Linux supervisor for AOIA child processes.

This module is executed as a fresh Python interpreter.  Keeping ``fork`` and
``setrlimit`` here avoids Python's unsafe ``preexec_fn`` path in the
multi-threaded web runtime.  The supervisor becomes a child subreaper before it
forks the requested program, so double-forked descendants are adopted and can
be terminated and reaped before a terminal result is reported.
"""

import base64
import binascii
import ctypes
import errno
import json
import math
import os
import resource
import signal
import select
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "AOIA_SUBPROCESS_SUPERVISOR_1A"
PROCESS_CPU_LIMIT = "PROCESS_CPU_LIMIT"
PROCESS_MEMORY_LIMIT = "PROCESS_MEMORY_LIMIT"
PROCESS_FILE_LIMIT = "PROCESS_FILE_LIMIT"
PROCESS_COUNT_LIMIT = "PROCESS_COUNT_LIMIT"
PROCESS_TREE_TERMINATED = "PROCESS_TREE_TERMINATED"
SUBPROCESS_HARD_TIMEOUT = "SUBPROCESS_HARD_TIMEOUT"
CONTAINMENT_SETUP_FAILED = "PROCESS_CONTAINMENT_SETUP_FAILED"

_PR_SET_PDEATHSIG = 1
_PR_SET_CHILD_SUBREAPER = 36
_POLL_SECONDS = 0.01
_TERM_GRACE_SECONDS = 0.35
_KILL_GRACE_SECONDS = 0.75
_MAX_FREEZE_PASSES = 8


@dataclass(frozen=True)
class _ProcessBinding:
    pid: int
    start_time: int
    process_group: int
    session: int


@dataclass(frozen=True)
class _Discovery:
    processes: dict[int, _ProcessBinding]
    complete: bool


@dataclass
class _ReapState:
    target_pid: int
    target_binding: _ProcessBinding | None = None
    target_status: int | None = None
    target_usage: resource.struct_rusage | None = None


_stop_requested = False


def _handle_stop(_signum: int, _frame: Any) -> None:
    global _stop_requested
    _stop_requested = True


def _cancellation_requested(fd: int) -> bool:
    """Latch a parent cancellation byte without relying on signal readiness."""
    global _stop_requested
    if _stop_requested:
        return True
    try:
        value = os.read(fd, 1)
    except BlockingIOError:
        return False
    except OSError:
        _stop_requested = True
        return True
    # A byte is an explicit cancellation. EOF means the owning AOIA parent
    # disappeared/closed its authority channel, which is also fail-closed.
    if value or value == b"":
        _stop_requested = True
    return _stop_requested


def _prctl(option: int, value: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = (
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    )
    prctl.restype = ctypes.c_int
    if prctl(option, value, 0, 0, 0) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def _decode_config(raw: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("duplicate supervisor configuration field")
            result[name] = value
        return result

    try:
        padding = "=" * (-len(raw) % 4)
        decoded = base64.b64decode(
            raw + padding,
            altchars=b"-_",
            validate=True,
        ).decode("utf-8")
        payload = json.loads(decoded, object_pairs_hook=reject_duplicate_keys)
    except (ValueError, UnicodeError, json.JSONDecodeError, binascii.Error) as exc:
        raise ValueError("invalid supervisor configuration") from exc
    if not isinstance(payload, dict) or payload.get("schema") != REPORT_SCHEMA:
        raise ValueError("unsupported supervisor configuration")
    allowed = {
        "schema",
        "timeout_seconds",
        "cpu_seconds",
        "address_space_bytes",
        "tree_memory_bytes",
        "open_files",
        "max_tasks",
        "file_size_bytes",
        "executable",
    }
    if set(payload) != allowed:
        raise ValueError("malformed supervisor configuration")
    timeout = payload["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("invalid supervisor timeout")
    if isinstance(timeout, int):
        timeout_valid = 0.01 <= timeout <= 600
    else:
        timeout_valid = math.isfinite(timeout) and 0.01 <= timeout <= 600.0
    if not timeout_valid:
        raise ValueError("invalid supervisor timeout")
    resource_caps = {
        "cpu_seconds": 600,
        "address_space_bytes": (1 << 63) - 1,
        "tree_memory_bytes": (1 << 63) - 1,
        "open_files": 1_048_576,
        "max_tasks": 4096,
        "file_size_bytes": (1 << 63) - 1,
    }
    for name, cap in resource_caps.items():
        value = payload[name]
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 < value <= cap
        ):
            raise ValueError("invalid supervisor resource limit")
    executable = payload["executable"]
    if executable is not None and (not isinstance(executable, str) or not executable):
        raise ValueError("invalid target executable")
    return payload


def _write_report(fd: int, payload: dict[str, Any]) -> None:
    record = json.dumps(
        {"schema": REPORT_SCHEMA, **payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    view = memoryview(record)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def _binding_checked(pid: int) -> tuple[_ProcessBinding | None, bool]:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        close = stat.rfind(")")
        fields = stat[close + 2 :].split()
        return (
            _ProcessBinding(
                pid=pid,
                start_time=int(fields[19]),
                process_group=int(fields[2]),
                session=int(fields[3]),
            ),
            True,
        )
    except FileNotFoundError:
        return None, True
    except (PermissionError, OSError, ValueError, IndexError):
        return None, False


def _binding(pid: int) -> _ProcessBinding | None:
    return _binding_checked(pid)[0]


def _same_process(item: _ProcessBinding) -> bool:
    current = _binding(item.pid)
    return current is not None and current.start_time == item.start_time


def _open_bound_pidfd(item: _ProcessBinding) -> int | None:
    """Open a stable process handle and revalidate its immutable start time."""
    try:
        pidfd = os.pidfd_open(item.pid, 0)
    except (AttributeError, ProcessLookupError, PermissionError, OSError):
        return None
    if not _same_process(item):
        os.close(pidfd)
        return None
    return pidfd


def _task_children(pid: int) -> tuple[set[int], bool]:
    children: set[int] = set()
    try:
        task_paths = tuple(Path(f"/proc/{pid}/task").iterdir())
    except FileNotFoundError:
        return children, True
    except (PermissionError, OSError):
        return children, False
    complete = True
    for task_path in task_paths:
        try:
            raw = (task_path / "children").read_text(encoding="ascii").strip()
        except FileNotFoundError:
            continue
        except (PermissionError, OSError):
            complete = False
            continue
        for value in raw.split():
            try:
                children.add(int(value))
            except ValueError:
                complete = False
    return children, complete


def _descendants(root_pid: int) -> _Discovery:
    found: dict[int, _ProcessBinding] = {}
    initial, complete = _task_children(root_pid)
    pending = list(initial)
    while pending:
        pid = pending.pop()
        if pid in found or pid == root_pid:
            continue
        item, binding_complete = _binding_checked(pid)
        complete = complete and binding_complete
        if item is None:
            continue
        found[pid] = item
        children, child_complete = _task_children(pid)
        complete = complete and child_complete
        pending.extend(children)
    return _Discovery(found, complete)


def _task_count(processes: dict[int, _ProcessBinding]) -> tuple[int, bool]:
    count = 0
    complete = True
    for item in processes.values():
        current, binding_complete = _binding_checked(item.pid)
        complete = complete and binding_complete
        if current is None or current.start_time != item.start_time:
            continue
        try:
            count += sum(1 for _ in Path(f"/proc/{item.pid}/task").iterdir())
        except FileNotFoundError:
            continue
        except (PermissionError, OSError):
            complete = False
    return count, complete


def _tree_rss_bytes(processes: dict[int, _ProcessBinding]) -> tuple[int, bool]:
    total = 0
    complete = True
    page_size = os.sysconf("SC_PAGE_SIZE")
    for item in processes.values():
        current, binding_complete = _binding_checked(item.pid)
        complete = complete and binding_complete
        if current is None or current.start_time != item.start_time:
            continue
        try:
            fields = Path(f"/proc/{item.pid}/statm").read_text(encoding="ascii").split()
            total += int(fields[1]) * page_size
        except FileNotFoundError:
            continue
        except (PermissionError, OSError, ValueError, IndexError):
            complete = False
    return total, complete


def _signal_pid(item: _ProcessBinding, signum: int) -> None:
    pidfd = _open_bound_pidfd(item)
    if pidfd is None:
        return
    try:
        signal.pidfd_send_signal(pidfd, signum)
    except (AttributeError, ProcessLookupError, PermissionError, OSError):
        pass
    finally:
        os.close(pidfd)


def _reap_available(state: _ReapState) -> None:
    while True:
        try:
            pid, status, usage = os.wait4(-1, os.WNOHANG)
        except ChildProcessError:
            break
        except InterruptedError:
            continue
        if pid == 0:
            break
        if pid == state.target_pid and state.target_status is None:
            state.target_status = status
            state.target_usage = usage


def _terminate_tree(state: _ReapState, supervisor_pid: int) -> bool:
    discovery = _descendants(supervisor_pid)
    proof_complete = discovery.complete
    if state.target_binding is not None:
        discovery.processes.setdefault(state.target_pid, state.target_binding)
    for item in discovery.processes.values():
        _signal_pid(item, signal.SIGTERM)

    deadline = time.monotonic() + _TERM_GRACE_SECONDS
    while time.monotonic() < deadline:
        _reap_available(state)
        discovery = _descendants(supervisor_pid)
        proof_complete = proof_complete and discovery.complete
        if not discovery.processes and proof_complete:
            return proof_complete
        time.sleep(_POLL_SECONDS)

    # Stop each currently bound task, rescan until no new task can be created,
    # then escalate.  The supervisor itself is never stopped or killed.
    previous: set[tuple[int, int]] = set()
    stable = False
    for _ in range(_MAX_FREEZE_PASSES):
        discovery = _descendants(supervisor_pid)
        proof_complete = proof_complete and discovery.complete
        current = {
            (item.pid, item.start_time) for item in discovery.processes.values()
        }
        for item in discovery.processes.values():
            _signal_pid(item, signal.SIGSTOP)
        if current == previous:
            stable = True
            break
        previous = current
        time.sleep(_POLL_SECONDS)

    discovery = _descendants(supervisor_pid)
    proof_complete = proof_complete and discovery.complete
    if state.target_binding is not None and _same_process(state.target_binding):
        discovery.processes.setdefault(state.target_pid, state.target_binding)
    for item in discovery.processes.values():
        _signal_pid(item, signal.SIGKILL)

    deadline = time.monotonic() + _KILL_GRACE_SECONDS
    while time.monotonic() < deadline:
        _reap_available(state)
        discovery = _descendants(supervisor_pid)
        proof_complete = proof_complete and discovery.complete
        if not discovery.processes and proof_complete:
            return proof_complete
        time.sleep(_POLL_SECONDS)
    return False


def _count_uid_tasks(real_uid: int) -> int:
    count = 0
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            status_lines = (process / "status").read_text(encoding="ascii").splitlines()
            uid_line = next(line for line in status_lines if line.startswith("Uid:"))
            if int(uid_line.split()[1]) != real_uid:
                continue
            count += sum(1 for _ in (process / "task").iterdir())
        except (FileNotFoundError, PermissionError, OSError, StopIteration, ValueError):
            continue
    return count


def _tighten_limit(kind: int, soft: int, hard: int | None = None) -> None:
    _old_soft, old_hard = resource.getrlimit(kind)
    desired_hard = soft if hard is None else hard
    if old_hard != resource.RLIM_INFINITY:
        desired_hard = min(desired_hard, int(old_hard))
    desired_soft = min(soft, desired_hard)
    resource.setrlimit(kind, (desired_soft, desired_hard))


def _apply_limits(config: dict[str, Any], uid_task_count: int) -> None:
    _tighten_limit(resource.RLIMIT_CORE, 0)
    cpu = config["cpu_seconds"]
    if cpu is not None:
        _tighten_limit(resource.RLIMIT_CPU, cpu, cpu + 1)
    address_space = config["address_space_bytes"]
    if address_space is not None:
        _tighten_limit(resource.RLIMIT_AS, address_space)
    open_files = config["open_files"]
    if open_files is not None:
        _tighten_limit(resource.RLIMIT_NOFILE, open_files)
    file_size = config["file_size_bytes"]
    if file_size is not None:
        _tighten_limit(resource.RLIMIT_FSIZE, file_size)
    max_tasks = config["max_tasks"]
    if max_tasks is not None and hasattr(resource, "RLIMIT_NPROC"):
        # Linux RLIMIT_NPROC is per-real-UID, not a per-tree counter.  The
        # supervisor independently monitors its tree; this dynamic ceiling is
        # only a conservative fork-bomb backstop around the launch baseline.
        _tighten_limit(resource.RLIMIT_NPROC, uid_task_count + max_tasks + 8)


def _restore_exec_signals() -> None:
    signal.pthread_sigmask(signal.SIG_SETMASK, set())
    for name in ("SIGPIPE", "SIGXFZ", "SIGXFSZ", "SIGTERM", "SIGINT"):
        signum = getattr(signal, name, None)
        if signum is not None:
            signal.signal(signum, signal.SIG_DFL)


def _child_exec(
    target_args: list[str],
    executable: str | None,
    config: dict[str, Any],
    report_fd: int,
    cancel_fd: int,
    setup_fd: int,
    dispatch_fd: int,
    uid_task_count: int,
    supervisor_pid: int,
) -> None:
    try:
        os.close(report_fd)
        os.close(cancel_fd)
        _prctl(_PR_SET_PDEATHSIG, signal.SIGKILL)
        if os.getppid() != supervisor_pid:
            raise RuntimeError("supervisor changed before target setup")
        os.setpgid(0, 0)
        _restore_exec_signals()
        _apply_limits(config, uid_task_count)
        if os.read(dispatch_fd, 1) != b"G" or _stop_requested:
            raise RuntimeError("target dispatch was not granted")
        os.close(dispatch_fd)
        if os.getppid() != supervisor_pid:
            raise RuntimeError("supervisor changed before target dispatch")
        os.execvpe(executable or target_args[0], target_args, dict(os.environ))
    except BaseException:
        try:
            os.write(setup_fd, b"PROCESS_CONTAINMENT_SETUP_FAILED")
        except OSError:
            pass
        os._exit(127)


def _wait_setup_pipe(fd: int, deadline: float) -> tuple[bytes, bool]:
    output = bytearray()
    while time.monotonic() < deadline:
        ready, _, _ = select.select((fd,), (), (), min(0.05, max(0.0, deadline - time.monotonic())))
        if not ready:
            continue
        try:
            chunk = os.read(fd, 256)
        except InterruptedError:
            continue
        if not chunk:
            return bytes(output), True
        output.extend(chunk[: 256 - len(output)])
    return bytes(output), False


def _status_reason(status: int | None) -> str | None:
    if status is None or not os.WIFSIGNALED(status):
        return None
    signum = os.WTERMSIG(status)
    if signum == signal.SIGXCPU:
        return PROCESS_CPU_LIMIT
    if signum == getattr(signal, "SIGXFSZ", -1):
        return PROCESS_FILE_LIMIT
    return None


def supervise(
    config: dict[str, Any],
    target_args: list[str],
    report_fd: int,
    cancel_fd: int,
) -> int:
    if sys.platform != "linux" or not Path("/proc/self/task").is_dir():
        _write_report(report_fd, {"event": "TERMINAL", "containment_status": "FAILED", "reason_code": CONTAINMENT_SETUP_FAILED})
        return 125
    if not target_args or any(not isinstance(value, str) or "\x00" in value for value in target_args):
        _write_report(report_fd, {"event": "TERMINAL", "containment_status": "FAILED", "reason_code": CONTAINMENT_SETUP_FAILED})
        return 125

    parent_pid = os.getppid()
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    try:
        _prctl(_PR_SET_PDEATHSIG, signal.SIGTERM)
        if os.getppid() != parent_pid:
            raise RuntimeError("supervisor parent changed during setup")
        _prctl(_PR_SET_CHILD_SUBREAPER, 1)
    except (OSError, RuntimeError):
        _write_report(report_fd, {"event": "TERMINAL", "containment_status": "FAILED", "reason_code": CONTAINMENT_SETUP_FAILED})
        return 125

    if _cancellation_requested(cancel_fd):
        _write_report(
            report_fd,
            {
                "event": "TERMINAL",
                "containment_status": "CONTAINED",
                "reason_code": PROCESS_TREE_TERMINATED,
                "timed_out": False,
                "cleanup_proven": True,
                # The cancellation fence, rather than target execution, is the
                # intervening containment action on this no-dispatch path.
                "tree_cleanup_intervened": True,
                "target_pid": None,
                "returncode": None,
                "usage": None,
            },
        )
        return 0

    setup_r, setup_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
    dispatch_r, dispatch_w = os.pipe2(os.O_CLOEXEC)
    uid_task_count = _count_uid_tasks(os.getuid())
    try:
        target_pid = os.fork()
    except OSError:
        os.close(setup_r)
        os.close(setup_w)
        os.close(dispatch_r)
        os.close(dispatch_w)
        _write_report(report_fd, {"event": "TERMINAL", "containment_status": "FAILED", "reason_code": CONTAINMENT_SETUP_FAILED})
        return 125
    if target_pid == 0:
        os.close(setup_r)
        os.close(dispatch_w)
        _child_exec(
            target_args,
            config["executable"],
            config,
            report_fd,
            cancel_fd,
            setup_w,
            dispatch_r,
            uid_task_count,
            os.getppid(),
        )
        raise AssertionError("unreachable")
    os.close(setup_w)
    os.close(dispatch_r)
    target_binding = None
    for _ in range(20):
        target_binding = _binding(target_pid)
        if target_binding is not None:
            break
        time.sleep(0.001)
    state = _ReapState(target_pid=target_pid, target_binding=target_binding)
    reason_code: str | None = None
    timed_out = False
    cleanup_proven = True
    deadline: float | None = None
    tree_cleanup_intervened = False
    postfork_complete = False
    try:
        if target_binding is None or _cancellation_requested(cancel_fd):
            reason_code = CONTAINMENT_SETUP_FAILED if target_binding is None else PROCESS_TREE_TERMINATED
            try:
                os.close(dispatch_w)
            except OSError:
                pass
            tree_cleanup_intervened = True
            cleanup_proven = _terminate_tree(state, os.getpid())
        else:
            if _cancellation_requested(cancel_fd):
                reason_code = PROCESS_TREE_TERMINATED
                os.close(dispatch_w)
                tree_cleanup_intervened = True
                cleanup_proven = _terminate_tree(state, os.getpid())
            else:
                try:
                    os.write(dispatch_w, b"G")
                except OSError:
                    reason_code = CONTAINMENT_SETUP_FAILED
                finally:
                    os.close(dispatch_w)
                setup_error, setup_complete = _wait_setup_pipe(
                    setup_r,
                    time.monotonic() + 2.0,
                )
                if setup_error or not setup_complete:
                    reason_code = CONTAINMENT_SETUP_FAILED
                    tree_cleanup_intervened = True
                    cleanup_proven = _terminate_tree(state, os.getpid())
                else:
                    deadline = time.monotonic() + float(config["timeout_seconds"])
                    _write_report(
                        report_fd,
                        {
                            "event": "STARTED",
                            "target_pid": target_pid,
                            "target_start_time": target_binding.start_time,
                        },
                    )

        while reason_code is None and state.target_status is None:
            _reap_available(state)
            discovery = _descendants(os.getpid())
            task_count, count_complete = _task_count(discovery.processes)
            tree_rss, memory_complete = _tree_rss_bytes(discovery.processes)
            if not discovery.complete or not count_complete or not memory_complete:
                reason_code = CONTAINMENT_SETUP_FAILED
            elif config["max_tasks"] is not None and task_count > config["max_tasks"]:
                reason_code = PROCESS_COUNT_LIMIT
            elif config["tree_memory_bytes"] is not None and tree_rss > config["tree_memory_bytes"]:
                reason_code = PROCESS_MEMORY_LIMIT
            elif state.target_status is not None:
                break
            elif _cancellation_requested(cancel_fd) or (
                deadline is not None and time.monotonic() >= deadline
            ):
                # Close the small observation window between the first reap and
                # the monotonic deadline check. A target already at terminal
                # truth must not be relabelled as a timeout or cancellation.
                _reap_available(state)
                if state.target_status is not None:
                    break
                timed_out = deadline is not None and time.monotonic() >= deadline
                reason_code = SUBPROCESS_HARD_TIMEOUT if timed_out else PROCESS_TREE_TERMINATED
            if reason_code is not None:
                tree_cleanup_intervened = True
                cleanup_proven = _terminate_tree(state, os.getpid())
                break
            time.sleep(_POLL_SECONDS)

        _reap_available(state)
        if reason_code is None:
            reason_code = _status_reason(state.target_status)
        residual = _descendants(os.getpid())
        task_count, count_complete = _task_count(residual.processes)
        tree_rss, memory_complete = _tree_rss_bytes(residual.processes)
        if config["max_tasks"] is not None and task_count > config["max_tasks"]:
            reason_code = PROCESS_COUNT_LIMIT
        if (
            reason_code != PROCESS_COUNT_LIMIT
            and config["tree_memory_bytes"] is not None
            and tree_rss > config["tree_memory_bytes"]
        ):
            reason_code = PROCESS_MEMORY_LIMIT
        if not residual.complete or not count_complete or not memory_complete:
            cleanup_proven = False
            reason_code = reason_code or CONTAINMENT_SETUP_FAILED
        if residual.processes:
            tree_cleanup_intervened = True
            cleanup_proven = _terminate_tree(state, os.getpid()) and cleanup_proven
            if reason_code is None:
                reason_code = PROCESS_TREE_TERMINATED

        postfork_complete = True
    finally:
        try:
            os.close(setup_r)
        except OSError:
            pass
        if not postfork_complete:
            tree_cleanup_intervened = True
            cleanup_proven = _terminate_tree(state, os.getpid()) and cleanup_proven
            _reap_available(state)

    exit_code = 125 if state.target_status is None else os.waitstatus_to_exitcode(state.target_status)
    usage_payload = None
    if state.target_usage is not None:
        usage_payload = {
            "user_seconds": round(float(state.target_usage.ru_utime), 6),
            "system_seconds": round(float(state.target_usage.ru_stime), 6),
            "max_rss_kib": int(state.target_usage.ru_maxrss),
        }
    _write_report(
        report_fd,
        {
            "event": "TERMINAL",
            "containment_status": "CONTAINED" if cleanup_proven else "FAILED",
            "reason_code": reason_code,
            "timed_out": timed_out,
            "cleanup_proven": cleanup_proven,
            "tree_cleanup_intervened": tree_cleanup_intervened,
            "target_pid": target_pid,
            "returncode": exit_code,
            "usage": usage_payload,
        },
    )
    return 0 if cleanup_proven else 125


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) < 4:
        return 125
    try:
        report_fd = int(values[0])
        cancel_fd = int(values[1])
        config = _decode_config(values[2])
    except (ValueError, TypeError):
        return 125
    target_args = values[3:]
    try:
        return supervise(config, target_args, report_fd, cancel_fd)
    except BaseException:
        try:
            _write_report(
                report_fd,
                {
                    "event": "TERMINAL",
                    "containment_status": "FAILED",
                    "reason_code": CONTAINMENT_SETUP_FAILED,
                },
            )
        except OSError:
            pass
        return 125
    finally:
        try:
            os.close(report_fd)
        except OSError:
            pass
        try:
            os.close(cancel_fd)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
