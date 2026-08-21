from __future__ import annotations

import ast
import base64
import errno
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from runtime.safety import bounded_subprocess
from runtime.safety.bounded_subprocess import (
    PROCESS_CONTAINMENT_LOST_REASON_CODE,
    PROCESS_COUNT_LIMIT_REASON_CODE,
    PROCESS_CPU_LIMIT_REASON_CODE,
    PROCESS_FILE_LIMIT_REASON_CODE,
    PROCESS_TREE_TERMINATED_REASON_CODE,
    SUBPROCESS_RESOURCE_PROFILES,
    SubprocessContainmentError,
    SubprocessCancelledError,
    SubprocessResourceLimitError,
    SubprocessResourceProfileName,
    SubprocessTimeoutPolicyError,
    SubprocessTreeTimeoutExpired,
    _reports,
    _validate_supervisor_exit_status,
    run_bounded_subprocess,
)
from runtime.outcomes import NZOutcomeStatus, outcome_from_exception
from runtime.safety.subprocess_env import build_subprocess_env
from runtime.safety.subprocess_supervisor import _decode_config


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProcessResourceContainmentTests(unittest.TestCase):
    def test_named_profiles_are_finite_and_cover_each_runtime_class(self) -> None:
        self.assertEqual(set(SubprocessResourceProfileName), set(SUBPROCESS_RESOURCE_PROFILES))
        for profile in SUBPROCESS_RESOURCE_PROFILES.values():
            self.assertGreater(profile.cpu_seconds, 0)
            self.assertGreater(profile.address_space_bytes, 0)
            self.assertGreater(profile.tree_memory_bytes, 0)
            self.assertGreater(profile.open_files, 0)
            self.assertGreater(profile.max_tasks, 0)
            self.assertGreater(profile.max_capture_bytes, 0)
        self.assertIsNone(SUBPROCESS_RESOURCE_PROFILES[SubprocessResourceProfileName.GIT].file_size_bytes)

    def test_supervisor_configuration_is_strict_and_bounded(self) -> None:
        base = {
            "schema": "AOIA_SUBPROCESS_SUPERVISOR_1A",
            "timeout_seconds": 1,
            "cpu_seconds": 1,
            "address_space_bytes": 1024 * 1024,
            "tree_memory_bytes": 1024 * 1024,
            "open_files": 16,
            "max_tasks": 2,
            "file_size_bytes": 1024,
            "executable": None,
        }
        self.assertEqual(base, _decode_config(self.encode_supervisor_config(base)))
        malformed = [
            "!!!!",
            self.encode_supervisor_raw(
                '{"schema":"AOIA_SUBPROCESS_SUPERVISOR_1A","timeout_seconds":1,'
                '"timeout_seconds":2,"cpu_seconds":1,"address_space_bytes":1,'
                '"tree_memory_bytes":1,"open_files":1,"max_tasks":1,'
                '"file_size_bytes":1,"executable":null}'
            ),
        ]
        for timeout in (float("nan"), float("inf"), 0.001, 601, 10**1000):
            malformed.append(self.encode_supervisor_config({**base, "timeout_seconds": timeout}))
        for field, value in (
            ("cpu_seconds", 601),
            ("address_space_bytes", 1 << 63),
            ("tree_memory_bytes", 1 << 63),
            ("open_files", 1_048_577),
            ("max_tasks", 4097),
            ("file_size_bytes", 1 << 63),
        ):
            malformed.append(self.encode_supervisor_config({**base, field: value}))
            malformed.append(self.encode_supervisor_config({**base, field: 10**1000}))
        for value in malformed:
            with self.subTest(value=value[:40]), self.assertRaises(ValueError):
                _decode_config(value)

    def test_minimum_timeout_does_not_turn_reaped_success_into_timeout(self) -> None:
        for _ in range(5):
            completed = self.run_child(["/bin/true"], timeout=0.05)
            self.assertEqual(0, completed.returncode)

    def test_normal_child_preserves_text_bytes_check_input_and_stderr_redirect(self) -> None:
        text = self.run_child(
            [sys.executable, "-c", "import sys; print(sys.stdin.read()); print('err', file=sys.stderr)"],
            timeout=2,
            input="hello",
            capture_output=True,
            text=True,
        )
        self.assertEqual("hello\n", text.stdout)
        self.assertEqual("err\n", text.stderr)
        binary = self.run_child(
            [sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'bytes')"],
            timeout=2,
            stdout=subprocess.PIPE,
        )
        self.assertEqual(b"bytes", binary.stdout)
        combined = self.run_child(
            [sys.executable, "-c", "import sys;print('out');print('err',file=sys.stderr)"],
            timeout=2,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertIn("out", combined.stdout)
        self.assertIn("err", combined.stdout)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_child(["/bin/false"], timeout=2, check=True)

    def test_timeout_terminates_and_reaps_same_group_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "descendant.pid"
            code = (
                "import os,pathlib,sys,time;"
                "pid=os.fork();"
                "(pathlib.Path(sys.argv[1]).write_text(str(os.getpid())),time.sleep(30)) if pid==0 else time.sleep(30)"
            )
            with self.assertRaises(SubprocessTreeTimeoutExpired):
                self.run_child([sys.executable, "-c", code, str(pid_path)], timeout=0.2)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_text_mode_timeout_preserves_stdlib_bytes_and_truncation_metadata(self) -> None:
        code = "import sys,time;print('partial',flush=True);time.sleep(30)"
        with self.assertRaises(SubprocessTreeTimeoutExpired) as caught:
            self.run_child(
                [sys.executable, "-c", code],
                timeout=0.2,
                capture_output=True,
                text=True,
            )
        self.assertIsInstance(caught.exception.output, bytes)
        self.assertIn(b"partial", caught.exception.output)
        self.assertTrue(caught.exception.tree_cleanup_intervened)

    def test_invalid_utf8_cannot_mask_timeout_or_cpu_limit_truth(self) -> None:
        timeout_code = "import os,time;os.write(1,b'\\xff');time.sleep(30)"
        with self.assertRaises(SubprocessTreeTimeoutExpired) as timed_out:
            self.run_child(
                [sys.executable, "-c", timeout_code],
                timeout=0.2,
                capture_output=True,
                text=True,
            )
        self.assertEqual(b"\xff", timed_out.exception.output)

        cpu_code = "import os;os.write(1,b'\\xff');exec('while True: pass')"
        with self.profile(cpu_seconds=1):
            with self.assertRaises(SubprocessResourceLimitError) as cpu_limited:
                self.run_child(
                    [sys.executable, "-c", cpu_code],
                    timeout=5,
                    capture_output=True,
                    text=True,
                )
        self.assertEqual(PROCESS_CPU_LIMIT_REASON_CODE, cpu_limited.exception.reason_code)
        self.assertEqual(b"\xff", cpu_limited.exception.output)

    def test_timeout_terminates_double_fork_setsid_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "daemon.pid"
            code = "\n".join(
                (
                    "import os, pathlib, sys, time",
                    "first = os.fork()",
                    "if first == 0:",
                    "    os.setsid()",
                    "    second = os.fork()",
                    "    if second == 0:",
                    "        pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')",
                    "        time.sleep(30)",
                    "    os._exit(0)",
                    "time.sleep(30)",
                )
            )
            with self.assertRaises(SubprocessTreeTimeoutExpired):
                self.run_child([sys.executable, "-c", code, str(pid_path)], timeout=0.25)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_successful_leader_with_detached_descendant_is_explicit_non_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "daemon.pid"
            code = "\n".join(
                (
                    "import os, pathlib, sys, time",
                    "pid = os.fork()",
                    "if pid == 0:",
                    "    os.setsid()",
                    "    pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')",
                    "    time.sleep(30)",
                    "os._exit(0)",
                )
            )
            with self.assertRaises(SubprocessResourceLimitError) as caught:
                self.run_child([sys.executable, "-c", code, str(pid_path)], timeout=2)
            self.assertEqual(PROCESS_TREE_TERMINATED_REASON_CODE, caught.exception.reason_code)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_term_ignoring_tree_is_killed_with_bounded_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "child.pid"
            code = "\n".join(
                (
                    "import os, pathlib, signal, sys, time",
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN)",
                    "pid = os.fork()",
                    "if pid == 0:",
                    "    signal.signal(signal.SIGTERM, signal.SIG_IGN)",
                    "    pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')",
                    "    time.sleep(30)",
                    "time.sleep(30)",
                )
            )
            started = time.monotonic()
            with self.assertRaises(SubprocessTreeTimeoutExpired):
                self.run_child([sys.executable, "-c", code, str(pid_path)], timeout=0.2)
            self.assertLess(time.monotonic() - started, 3.0)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_cpu_limit_has_exact_reason(self) -> None:
        with self.profile(cpu_seconds=1):
            with self.assertRaises(SubprocessResourceLimitError) as caught:
                self.run_child([sys.executable, "-c", "while True: pass"], timeout=5)
        self.assertEqual(PROCESS_CPU_LIMIT_REASON_CODE, caught.exception.reason_code)

    def test_cpu_reason_survives_residual_descendant_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp, self.profile(cpu_seconds=1):
            pid_path = Path(raw_tmp) / "daemon.pid"
            code = "\n".join(
                (
                    "import os, pathlib, sys, time",
                    "pid = os.fork()",
                    "if pid == 0:",
                    "    os.setsid()",
                    "    pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')",
                    "    time.sleep(30)",
                    "while True: pass",
                )
            )
            with self.assertRaises(SubprocessResourceLimitError) as caught:
                self.run_child([sys.executable, "-c", code, str(pid_path)], timeout=5)
            self.assertEqual(PROCESS_CPU_LIMIT_REASON_CODE, caught.exception.reason_code)
            self.assertTrue(caught.exception.tree_cleanup_intervened)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_aggregate_memory_limit_has_exact_observed_reason(self) -> None:
        with self.profile(
            address_space_bytes=512 * 1024 * 1024,
            tree_memory_bytes=64 * 1024 * 1024,
        ):
            with self.assertRaises(SubprocessResourceLimitError) as caught:
                self.run_child(
                    [sys.executable, "-c", "import time;x=bytearray(128*1024*1024);time.sleep(30)"],
                    timeout=5,
                    capture_output=True,
                    text=True,
                )
        self.assertEqual("PROCESS_MEMORY_LIMIT", caught.exception.reason_code)

    def test_file_descriptor_limit_is_enforced(self) -> None:
        code = "\n".join(
            (
                "import errno, os",
                "items=[]",
                "try:",
                "    while True: items.append(open('/dev/null','rb'))",
                "except OSError as exc:",
                "    print(exc.errno, len(items))",
            )
        )
        with self.profile(open_files=32):
            completed = self.run_child([sys.executable, "-c", code], timeout=3, capture_output=True, text=True)
        code_value, opened = (int(value) for value in completed.stdout.split())
        self.assertEqual(errno.EMFILE, code_value)
        self.assertLess(opened, 32)

    def test_file_size_limit_has_exact_reason(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp, self.profile(file_size_bytes=64 * 1024):
            output = Path(raw_tmp) / "large.bin"
            with output.open("wb") as stream, self.assertRaises(SubprocessResourceLimitError) as caught:
                self.run_child(
                    ["/usr/bin/head", "-c", str(1024 * 1024), "/dev/zero"],
                    timeout=3,
                    stdout=stream,
                )
        self.assertEqual(PROCESS_FILE_LIMIT_REASON_CODE, caught.exception.reason_code)

    def test_process_task_count_monitor_has_exact_reason_and_reaps(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp, self.profile(max_tasks=2):
            pid_path = Path(raw_tmp) / "pids.json"
            code = "\n".join(
                (
                    "import json, os, pathlib, sys, time",
                    "pids=[]",
                    "for _ in range(6):",
                    "    pid=os.fork()",
                    "    if pid == 0: time.sleep(30); os._exit(0)",
                    "    pids.append(pid)",
                    "pathlib.Path(sys.argv[1]).write_text(json.dumps(pids), encoding='utf-8')",
                    "time.sleep(30)",
                )
            )
            with self.assertRaises(SubprocessResourceLimitError) as caught:
                self.run_child([sys.executable, "-c", code, str(pid_path)], timeout=3)
            self.assertEqual(PROCESS_COUNT_LIMIT_REASON_CODE, caught.exception.reason_code)
            if pid_path.exists():
                for pid in json.loads(pid_path.read_text(encoding="utf-8")):
                    self.assert_pid_gone(pid)

    def test_capture_is_bounded_and_truthfully_marked(self) -> None:
        with self.profile(max_capture_bytes=64 * 1024):
            completed = self.run_child(
                [sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'x'*(1024*1024))"],
                timeout=3,
                capture_output=True,
            )
        self.assertEqual(64 * 1024, len(completed.stdout))
        self.assertTrue(completed.stdout_truncated)
        self.assertFalse(completed.stderr_truncated)

    def test_truncated_utf8_and_check_error_keep_truthful_metadata(self) -> None:
        with self.profile(max_capture_bytes=64 * 1024):
            completed = self.run_child(
                [sys.executable, "-c", "import sys;sys.stdout.write('€'*100000)"],
                timeout=3,
                capture_output=True,
                text=True,
            )
            self.assertTrue(completed.stdout_truncated)
            self.assertTrue(completed.stdout)
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                self.run_child(
                    [sys.executable, "-c", "import sys;sys.stdout.write('x'*100000);sys.exit(7)"],
                    timeout=3,
                    capture_output=True,
                    check=True,
                )
        self.assertTrue(caught.exception.stdout_truncated)
        self.assertFalse(caught.exception.stderr_truncated)

    def test_args_and_input_are_bounded_before_dispatch(self) -> None:
        with self.assertRaises(SubprocessTimeoutPolicyError):
            self.run_child("/bin/true", timeout=2)
        with self.profile(max_capture_bytes=64):
            with self.assertRaises(SubprocessTimeoutPolicyError):
                self.run_child(
                    ["/bin/cat"],
                    timeout=2,
                    input=b"x" * 65,
                    capture_output=True,
                )

    def test_live_cancellation_terminates_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "child.pid"
            code = (
                "import os,pathlib,sys,time;pid=os.fork();"
                "(pathlib.Path(sys.argv[1]).write_text(str(os.getpid())),time.sleep(30)) "
                "if pid==0 else time.sleep(30)"
            )
            cancellation = threading.Event()
            def cancel_after_descendant_starts() -> None:
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and not pid_path.is_file():
                    time.sleep(0.01)
                cancellation.set()

            canceller = threading.Thread(target=cancel_after_descendant_starts)
            canceller.start()
            try:
                with self.assertRaises(SubprocessResourceLimitError) as caught:
                    self.run_child(
                        [sys.executable, "-c", code, str(pid_path)],
                        timeout=5,
                        cancel_event=cancellation,
                    )
            finally:
                canceller.join(2.5)
            self.assertEqual(PROCESS_TREE_TERMINATED_REASON_CODE, caught.exception.reason_code)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_preexisting_cancellation_fences_target_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            marker = Path(raw_tmp) / "dispatched"
            cancellation = threading.Event()
            cancellation.set()
            with self.assertRaises(SubprocessCancelledError) as caught:
                self.run_child(
                    [sys.executable, "-c", "import pathlib,sys;pathlib.Path(sys.argv[1]).touch()", str(marker)],
                    timeout=2,
                    cancel_event=cancellation,
                )
            self.assertEqual("TASK_CANCELLED", caught.exception.reason_code)
            self.assertFalse(marker.exists())

    def test_cancellation_bootstrap_race_never_loses_supervision(self) -> None:
        for delay in (0.0, 0.0001, 0.001, 0.005):
            for attempt in range(5):
                with self.subTest(delay=delay, attempt=attempt), tempfile.TemporaryDirectory() as raw_tmp:
                    pid_path = Path(raw_tmp) / "target.pid"
                    cancellation = threading.Event()
                    timer = threading.Timer(delay, cancellation.set)
                    timer.start()
                    try:
                        with self.assertRaises(
                            (SubprocessCancelledError, SubprocessResourceLimitError)
                        ) as caught:
                            self.run_child(
                                [
                                    sys.executable,
                                    "-c",
                                    "import os,pathlib,sys,time;pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(30)",
                                    str(pid_path),
                                ],
                                timeout=3,
                                cancel_event=cancellation,
                            )
                    finally:
                        timer.join()
                    self.assertIn(
                        caught.exception.reason_code,
                        {"TASK_CANCELLED", PROCESS_TREE_TERMINATED_REASON_CODE},
                    )
                    if pid_path.exists():
                        self.assert_pid_gone(int(pid_path.read_text(encoding="utf-8")))

    def test_supervisor_protocol_rejects_false_success_and_bad_linkage(self) -> None:
        started = {
            "schema": "AOIA_SUBPROCESS_SUPERVISOR_1A",
            "event": "STARTED",
            "target_pid": 123,
            "target_start_time": 456,
        }
        terminal = {
            "schema": "AOIA_SUBPROCESS_SUPERVISOR_1A",
            "event": "TERMINAL",
            "containment_status": "CONTAINED",
            "reason_code": None,
            "timed_out": False,
            "cleanup_proven": True,
            "tree_cleanup_intervened": False,
            "target_pid": 123,
            "returncode": 0,
            "usage": {"user_seconds": 0.0, "system_seconds": 0.0, "max_rss_kib": 1},
        }
        valid = b"\n".join(json.dumps(item).encode("utf-8") for item in (started, terminal)) + b"\n"
        parsed_started, parsed_terminal = _reports(valid)
        self.assertEqual(started, parsed_started)
        self.assertEqual(terminal, parsed_terminal)

        invalid_records = (
            (terminal,),
            (terminal, started),
            (started, {**terminal, "target_pid": 999}),
            (started, {**terminal, "containment_status": "FAILED"}),
            (started, {**terminal, "reason_code": "PROCESS_CONTAINMENT_SETUP_FAILED"}),
            (started, {**terminal, "tree_cleanup_intervened": True}),
            (started, {**terminal, "unexpected": True}),
        )
        for records in invalid_records:
            raw = b"\n".join(json.dumps(item).encode("utf-8") for item in records) + b"\n"
            with self.subTest(records=records), self.assertRaises(SubprocessContainmentError) as caught:
                _reports(raw)
            self.assertEqual(PROCESS_CONTAINMENT_LOST_REASON_CODE, caught.exception.reason_code)

    def test_supervisor_exit_status_must_match_exact_report_shape(self) -> None:
        minimal_raw = json.dumps(
            {
                "schema": "AOIA_SUBPROCESS_SUPERVISOR_1A",
                "event": "TERMINAL",
                "containment_status": "FAILED",
                "reason_code": "PROCESS_CONTAINMENT_SETUP_FAILED",
            }
        ).encode("utf-8") + b"\n"
        minimal_started, minimal_terminal = _reports(minimal_raw)
        _validate_supervisor_exit_status(125, minimal_started, minimal_terminal)
        with self.assertRaises(SubprocessContainmentError):
            _validate_supervisor_exit_status(0, minimal_started, minimal_terminal)

        started = {
            "schema": "AOIA_SUBPROCESS_SUPERVISOR_1A",
            "event": "STARTED",
            "target_pid": 123,
            "target_start_time": 456,
        }
        terminal = {
            "schema": "AOIA_SUBPROCESS_SUPERVISOR_1A",
            "event": "TERMINAL",
            "containment_status": "CONTAINED",
            "reason_code": None,
            "timed_out": False,
            "cleanup_proven": True,
            "tree_cleanup_intervened": False,
            "target_pid": 123,
            "returncode": 0,
            "usage": None,
        }
        full_raw = b"\n".join(
            json.dumps(item).encode("utf-8") for item in (started, terminal)
        ) + b"\n"
        full_started, full_terminal = _reports(full_raw)
        _validate_supervisor_exit_status(0, full_started, full_terminal)
        for returncode in (125, -signal.SIGKILL):
            with self.subTest(returncode=returncode), self.assertRaises(SubprocessContainmentError):
                _validate_supervisor_exit_status(returncode, full_started, full_terminal)

    def test_internal_report_truncation_fails_closed(self) -> None:
        with self.assertRaises(SubprocessContainmentError) as caught:
            _reports(b"{" + b" " * (bounded_subprocess._REPORT_LIMIT_BYTES + 1))
        self.assertEqual(PROCESS_CONTAINMENT_LOST_REASON_CODE, caught.exception.reason_code)

    def test_resource_exceptions_translate_to_explicit_outcomes(self) -> None:
        timeout = outcome_from_exception(SubprocessTreeTimeoutExpired(["child"], 1))
        self.assertEqual(NZOutcomeStatus.TIMEOUT, timeout.status)
        self.assertEqual("SUBPROCESS_HARD_TIMEOUT", timeout.reason_code)
        lost = outcome_from_exception(
            SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE)
        )
        self.assertEqual(NZOutcomeStatus.UNKNOWN_OUTCOME, lost.status)
        self.assertEqual(PROCESS_CONTAINMENT_LOST_REASON_CODE, lost.reason_code)
        cancelled = outcome_from_exception(SubprocessCancelledError(["child"]))
        self.assertEqual(NZOutcomeStatus.CANCELLED, cancelled.status)
        self.assertEqual("TASK_CANCELLED", cancelled.reason_code)

    def test_ambient_secret_is_not_inherited(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "NZ_P12_SECRET_001"}, clear=False):
            completed = self.run_child(
                [sys.executable, "-c", "import os;print(os.environ.get('OPENAI_API_KEY'))"],
                timeout=2,
                capture_output=True,
                text=True,
            )
        self.assertEqual("None", completed.stdout.strip())
        self.assertNotIn("NZ_P12_SECRET_001", completed.stdout)

    def test_supervisor_loss_is_explicit_and_never_success(self) -> None:
        code = "import os,signal,time;os.kill(os.getppid(), signal.SIGKILL);time.sleep(30)"
        with self.assertRaises(SubprocessContainmentError) as caught:
            self.run_child([sys.executable, "-c", code], timeout=2)
        self.assertEqual(PROCESS_CONTAINMENT_LOST_REASON_CODE, caught.exception.reason_code)

    def test_invalid_utf8_cannot_mask_supervisor_loss(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "target.pid"
            code = (
                "import os,pathlib,signal,sys,time;"
                "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));"
                "os.write(1,b'\\xff');"
                "os.kill(os.getppid(),signal.SIGKILL);"
                "time.sleep(30)"
            )
            with self.assertRaises(SubprocessContainmentError) as caught:
                self.run_child(
                    [sys.executable, "-c", code, str(pid_path)],
                    timeout=2,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(PROCESS_CONTAINMENT_LOST_REASON_CODE, caught.exception.reason_code)
            self.assert_pid_gone(self.wait_pid_file(pid_path))

    def test_hostile_supervisor_loss_with_escaped_pipe_holder_is_bounded_and_leak_free(self) -> None:
        # A same-UID hostile child can kill its single-process supervisor; no
        # delegated cgroup/namespace exists on this host. That case must be
        # explicit containment loss, and parent-side bounded collectors must
        # still release every AOIA thread/fd. The synthetic escape is then
        # removed by the test harness through a PID/start-time-bound pidfd.
        before_fds = len(tuple(Path("/proc/self/fd").iterdir()))
        with tempfile.TemporaryDirectory() as raw_tmp:
            marker = Path(raw_tmp) / "escaped.pid"
            code = "\n".join(
                (
                    "import os, pathlib, signal, sys, time",
                    "pid = os.fork()",
                    "if pid == 0:",
                    "    os.setsid()",
                    "    pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')",
                    "    time.sleep(30)",
                    "deadline = time.monotonic() + 2",
                    "while not pathlib.Path(sys.argv[1]).exists() and time.monotonic() < deadline: time.sleep(0.01)",
                    "os.kill(os.getppid(), signal.SIGKILL)",
                    "time.sleep(30)",
                )
            )
            escaped_pid = None
            started = time.monotonic()
            try:
                with self.assertRaises(SubprocessContainmentError) as caught:
                    self.run_child(
                        [sys.executable, "-c", code, str(marker)],
                        timeout=3,
                        capture_output=True,
                    )
                self.assertEqual(PROCESS_CONTAINMENT_LOST_REASON_CODE, caught.exception.reason_code)
                self.assertLess(time.monotonic() - started, 4.0)
                escaped_pid = self.wait_pid_file(marker)
            finally:
                if escaped_pid is not None:
                    self.kill_validated_synthetic(escaped_pid, marker)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and any(
            thread.name.startswith("aoia-bounded-") for thread in threading.enumerate()
        ):
            time.sleep(0.01)
        self.assertFalse(
            any(thread.name.startswith("aoia-bounded-") for thread in threading.enumerate())
        )
        self.assertEqual(before_fds, len(tuple(Path("/proc/self/fd").iterdir())))

    def test_no_preexec_and_all_call_sites_choose_typed_profile(self) -> None:
        active = tuple((REPO_ROOT / root).rglob("*.py") for root in ("runtime", "scripts"))
        callsites: list[str] = []
        for group in active:
            for path in group:
                if "__pycache__" in path.parts:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    if any(keyword.arg == "preexec_fn" for keyword in node.keywords):
                        self.fail(f"preexec_fn found at {path}:{node.lineno}")
                    if isinstance(node.func, ast.Name) and node.func.id == "run_bounded_subprocess":
                        if path.name != "bounded_subprocess.py":
                            self.assertTrue(
                                any(keyword.arg == "resource_profile" for keyword in node.keywords),
                                f"missing profile at {path}:{node.lineno}",
                            )
                            callsites.append(f"{path}:{node.lineno}")
        self.assertEqual(13, len(callsites))

    def run_child(self, args, *, timeout, **kwargs):
        return run_bounded_subprocess(
            args,
            env=build_subprocess_env(),
            timeout=timeout,
            resource_profile=SubprocessResourceProfileName.CONTROLLED_TEST,
            shell=False,
            **kwargs,
        )

    @staticmethod
    def encode_supervisor_config(payload: dict[str, object]) -> str:
        return ProcessResourceContainmentTests.encode_supervisor_raw(
            json.dumps(payload, separators=(",", ":"))
        )

    @staticmethod
    def encode_supervisor_raw(raw: str) -> str:
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")

    def profile(self, **changes):
        current = SUBPROCESS_RESOURCE_PROFILES[SubprocessResourceProfileName.CONTROLLED_TEST]
        replacement = replace(current, **changes)
        profiles = MappingProxyType({**SUBPROCESS_RESOURCE_PROFILES, current.name: replacement})
        return patch.object(bounded_subprocess, "SUBPROCESS_RESOURCE_PROFILES", profiles)

    @staticmethod
    def wait_pid_file(path: Path) -> int:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if path.is_file():
                return int(path.read_text(encoding="utf-8"))
            time.sleep(0.01)
        raise AssertionError("child pid evidence was not created")

    @staticmethod
    def assert_pid_gone(pid: int) -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.01)
        raise AssertionError(f"synthetic child pid {pid} survived containment")

    @staticmethod
    def kill_validated_synthetic(pid: int, marker: Path) -> None:
        command_line = Path(f"/proc/{pid}/cmdline").read_bytes()
        if os.fsencode(str(marker)) not in command_line:
            raise AssertionError("refusing to signal an unvalidated process")
        stat_before = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        start_before = int(stat_before[stat_before.rfind(")") + 2 :].split()[19])
        pidfd = os.pidfd_open(pid, 0)
        try:
            stat_after = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
            start_after = int(stat_after[stat_after.rfind(")") + 2 :].split()[19])
            if start_after != start_before:
                raise AssertionError("synthetic process identity changed before cleanup")
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        finally:
            os.close(pidfd)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
            except FileNotFoundError:
                return
            if stat[stat.rfind(")") + 2 :].split()[0] == "Z":
                return
            time.sleep(0.01)
        raise AssertionError("validated synthetic escape remained live after harness cleanup")


if __name__ == "__main__":
    unittest.main()
