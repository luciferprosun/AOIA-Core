from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from commands import local_commands
from runtime.knowledge.tools import pdf_extract
from runtime.safety.bounded_subprocess import (
    MAX_HARD_TIMEOUT_SECONDS,
    SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
    SubprocessResourceProfileName,
    SubprocessTimeoutPolicyError,
    run_bounded_subprocess,
    validate_hard_timeout_seconds,
)
from runtime.safety.subprocess_env import build_subprocess_env
from runtime.tools import build_rhcsa_library
from tools import shell_tools


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SOURCE_ROOTS = ("runtime", "scripts", "apps", "tools", "build_support")
EXPECTED_BOUNDED_PROCESS_SITES = {
    "runtime/commands/local_commands.py": 1,
    "runtime/execution/controlled_test_runner.py": 1,
    "runtime/git_ops/controlled_git_commit.py": 1,
    "runtime/git_ops/git_controlled_push.py": 1,
    "runtime/git_ops/git_read.py": 1,
    "runtime/knowledge/tools/pdf_extract.py": 2,
    "runtime/package_ops/controlled_package_install.py": 2,
    "runtime/patches/post_patch_controlled_test_integration.py": 1,
    "runtime/release_attestation.py": 1,
    "runtime/tools/build_rhcsa_library.py": 2,
    "scripts/dev/create_ioa_lab_clone.py": 1,
}
EXPECTED_RAW_PROCESS_BOUNDARY = {"runtime/safety/bounded_subprocess.py": 1}
EXPECTED_TRUSTED_FORK_BOUNDARY = {"runtime/safety/subprocess_supervisor.py": 1}
EXPECTED_TRUSTED_EXEC_BOUNDARY = {"runtime/safety/subprocess_supervisor.py": 1}
SUBPROCESS_CALLS = {
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.getoutput",
    "subprocess.getstatusoutput",
}
OTHER_PROCESS_CALLS = {
    "os.system",
    "os.popen",
    "os.fork",
    "os.forkpty",
    "os.posix_spawn",
    "os.posix_spawnp",
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
    "pty.spawn",
    "pexpect.spawn",
    "multiprocessing.Process",
}


class HardExecutionTimeoutTests(unittest.TestCase):
    def test_timeout_policy_rejects_missing_nonfinite_or_unbounded_values(self) -> None:
        rejected = (
            None,
            True,
            0,
            -1,
            float("nan"),
            float("inf"),
            MAX_HARD_TIMEOUT_SECONDS + 1,
            10**1000,
        )
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(SubprocessTimeoutPolicyError):
                validate_hard_timeout_seconds(value)

        with self.assertRaises(SubprocessTimeoutPolicyError):
            run_bounded_subprocess(
                [sys.executable, "-c", "pass"],
                env=build_subprocess_env(),
                timeout=1,
                resource_profile=SubprocessResourceProfileName.CONTROLLED_TEST,
                shell=True,
            )

    def test_successful_short_child_process_completes(self) -> None:
        completed = run_bounded_subprocess(
            [sys.executable, "-c", "print('NZ_BOUNDED_OK')"],
            env=build_subprocess_env(),
            timeout=5,
            resource_profile=SubprocessResourceProfileName.CONTROLLED_TEST,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )

        self.assertEqual(0, completed.returncode)
        self.assertEqual("NZ_BOUNDED_OK", completed.stdout.strip())

    def test_real_timed_out_child_is_killed_and_reaped(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            pid_path = Path(raw_tmp) / "child.pid"
            child_code = (
                "import os, pathlib, sys, time; "
                "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8'); "
                "time.sleep(30)"
            )

            with self.assertRaises(subprocess.TimeoutExpired):
                run_bounded_subprocess(
                    [sys.executable, "-c", child_code, str(pid_path)],
                    env=build_subprocess_env(),
                    timeout=0.25,
                    resource_profile=SubprocessResourceProfileName.CONTROLLED_TEST,
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=False,
                )

            self.assertTrue(pid_path.is_file())
            child_pid = int(pid_path.read_text(encoding="utf-8"))
            self.assert_process_is_gone(child_pid)

    def test_scemda_timeout_is_distinct_kills_child_and_filters_secrets(self) -> None:
        result, evidence = self.run_timed_scemda_probe()

        self.assertTrue(result.handled)
        self.assertIn(SUBPROCESS_HARD_TIMEOUT_REASON_CODE, result.message)
        self.assertIn("terminated", result.message.casefold())
        self.assertNotIn("cancelled", result.message.casefold())
        self.assertNotIn("frozen", result.message.casefold())
        self.assertNotIn("exit code", result.message.casefold())
        self.assertIsNone(evidence["OPENAI_API_KEY"])
        self.assertNotIn("NZ_TEST_SECRET_TIMED", result.message)
        self.assert_process_is_gone(int(evidence["pid"]))

    def test_scemda_operator_decline_occurs_before_process_creation(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            project = Path(raw_tmp) / "project"
            addon_dir = project / "addons" / "scemda"
            addon_dir.mkdir(parents=True)
            (addon_dir / "scemda_agent_v2.py").write_text(
                "raise RuntimeError('must not execute')\n",
                encoding="utf-8",
            )
            runtime = SimpleNamespace(project_dir=project)
            with (
                patch.object(local_commands, "SCEMDA_ZIP", Path(raw_tmp) / "missing.zip"),
                patch("builtins.input", return_value="cancel"),
                patch.object(local_commands, "run_bounded_subprocess") as process_mock,
            ):
                result = local_commands.cmd_scemda("--probe", runtime)

        self.assertEqual("SCEMDA run cancelled.", result.message)
        process_mock.assert_not_called()

    def test_pdf_tools_report_distinct_hard_timeouts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            sleeper = root / "pdf-tool-sleeper"
            sleeper.write_text(
                f"#!{sys.executable}\nimport time\ntime.sleep(30)\n",
                encoding="utf-8",
            )
            sleeper.chmod(0o755)
            pdf_suite_tool = root / "pdf-suite-tool"
            pdf_suite_tool.write_text(
                (
                    f"#!{sys.executable}\n"
                    "import sys\n"
                    "import time\n"
                    "if '-layout' in sys.argv:\n"
                    "    time.sleep(30)\n"
                    "else:\n"
                    "    print('Pages: 1')\n"
                ),
                encoding="utf-8",
            )
            pdf_suite_tool.chmod(0o755)
            input_path = root / "input.pdf"
            output_path = root / "output.txt"
            input_path.write_bytes(b"synthetic PDF fixture")

            with patch.object(pdf_extract, "PDF_TOOL_HARD_TIMEOUT_SECONDS", 0.2):
                with self.subTest(tool="pdfinfo"), self.assertRaises(
                    pdf_extract.PdfToolHardTimeoutError
                ) as pdfinfo_error:
                    pdf_extract.read_page_count(str(sleeper), input_path)
                self.assertEqual("pdfinfo", pdfinfo_error.exception.tool_name)
                self.assertIn(SUBPROCESS_HARD_TIMEOUT_REASON_CODE, str(pdfinfo_error.exception))

                with (
                    self.subTest(tool="pdftotext"),
                    patch.object(pdf_extract.shutil, "which", return_value=str(pdf_suite_tool)),
                    self.assertRaises(pdf_extract.PdfToolHardTimeoutError) as text_error,
                ):
                    pdf_extract.extract_pdf(input_path, output_path)
                self.assertEqual("pdftotext", text_error.exception.tool_name)
                self.assertIn(SUBPROCESS_HARD_TIMEOUT_REASON_CODE, str(text_error.exception))

    def test_frozen_legacy_shell_has_no_reachable_process_backend(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp, patch.dict(
            os.environ,
            {"AOIA_SHELL_EXECUTION_ENABLED": "1"},
            clear=False,
        ), patch("runtime.safety.bounded_subprocess.subprocess.Popen") as run_mock:
            result = shell_tools.shell_execute(
                "printf SHOULD_NOT_RUN",
                Path(raw_tmp),
                timeout_seconds=1,
            )

        self.assertTrue(result["blocked"])
        self.assertTrue(result["frozen"])
        self.assertFalse(result["success"])
        run_mock.assert_not_called()

    def test_rhcsa_utility_timeout_has_a_distinct_failure_type(self) -> None:
        timeout = subprocess.TimeoutExpired(cmd=("bash",), timeout=20)
        with patch.object(
            build_rhcsa_library.shutil,
            "which",
            return_value="/synthetic/tool",
        ), patch.object(
            build_rhcsa_library,
            "run_bounded_subprocess",
            side_effect=timeout,
        ) as run_mock, self.assertRaises(
            build_rhcsa_library.RhcsaUtilityHardTimeoutError
        ) as caught:
            build_rhcsa_library.export_single_manpage("bash")

        self.assertIn(SUBPROCESS_HARD_TIMEOUT_REASON_CODE, str(caught.exception))
        self.assertEqual(20, run_mock.call_args.kwargs["timeout"])

    def test_all_active_process_sites_use_the_bounded_child_boundary(self) -> None:
        bounded: dict[str, int] = {}
        raw: dict[str, int] = {}
        trusted_forks: dict[str, int] = {}
        trusted_execs: dict[str, int] = {}
        unbounded: list[str] = []
        unsafe_shell: list[str] = []
        forbidden: list[str] = []

        for path in self.active_source_files():
            relative = path.relative_to(REPO_ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            aliases = self.import_aliases(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                call_name = self.resolve_call_name(node.func, aliases)
                if call_name == "runtime.safety.bounded_subprocess.run_bounded_subprocess":
                    bounded[relative] = bounded.get(relative, 0) + 1
                    if not self.has_keyword(node, "env") or not self.has_keyword(node, "timeout"):
                        unbounded.append(f"{relative}:{node.lineno}")
                    shell_value = self.keyword_value(node, "shell")
                    if shell_value is not False:
                        unsafe_shell.append(f"{relative}:{node.lineno}")
                elif call_name in SUBPROCESS_CALLS:
                    raw[relative] = raw.get(relative, 0) + 1
                    if relative not in EXPECTED_RAW_PROCESS_BOUNDARY and (
                        not self.has_keyword(node, "env") or not self.has_keyword(node, "timeout")
                    ):
                        unbounded.append(f"{relative}:{node.lineno}")
                elif call_name == "os.fork":
                    trusted_forks[relative] = trusted_forks.get(relative, 0) + 1
                elif call_name == "os.execvpe":
                    trusted_execs[relative] = trusted_execs.get(relative, 0) + 1
                elif self.is_forbidden_process_call(call_name):
                    forbidden.append(f"{relative}:{node.lineno}:{call_name}")

        self.assertEqual(EXPECTED_BOUNDED_PROCESS_SITES, bounded)
        self.assertEqual(EXPECTED_RAW_PROCESS_BOUNDARY, raw)
        self.assertEqual(EXPECTED_TRUSTED_FORK_BOUNDARY, trusted_forks)
        self.assertEqual(EXPECTED_TRUSTED_EXEC_BOUNDARY, trusted_execs)
        self.assertEqual([], unbounded)
        self.assertEqual([], unsafe_shell)
        self.assertEqual([], forbidden)

    def run_timed_scemda_probe(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            project = root / "project"
            addon_dir = project / "addons" / "scemda"
            addon_dir.mkdir(parents=True)
            evidence_path = root / "timed-child.json"
            (addon_dir / "scemda_agent_v2.py").write_text(
                "\n".join(
                    (
                        "import json",
                        "import os",
                        "import pathlib",
                        "import sys",
                        "import time",
                        "pathlib.Path(sys.argv[1]).write_text(json.dumps({",
                        "    'pid': os.getpid(),",
                        "    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),",
                        "}), encoding='utf-8')",
                        "time.sleep(30)",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            runtime = SimpleNamespace(project_dir=project)
            with (
                patch.dict(
                    os.environ,
                    {
                        "AOIA_SHELL_EXECUTION_ENABLED": "1",
                        "OPENAI_API_KEY": "NZ_TEST_SECRET_TIMED",
                    },
                    clear=False,
                ),
                patch.object(local_commands, "SCEMDA_ZIP", root / "missing.zip"),
                patch.object(local_commands, "SCEMDA_HARD_TIMEOUT_SECONDS", 0.25),
                patch("builtins.input", return_value=""),
            ):
                result = local_commands.cmd_scemda(str(evidence_path), runtime)

            self.assertTrue(evidence_path.is_file())
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            return result, evidence

    def active_source_files(self) -> tuple[Path, ...]:
        paths: list[Path] = []
        for root_name in ACTIVE_SOURCE_ROOTS:
            source_root = REPO_ROOT / root_name
            if not source_root.is_dir():
                continue
            for path in source_root.rglob("*.py"):
                relative = path.relative_to(REPO_ROOT)
                if "tests" in relative.parts or path.name.startswith("test_"):
                    continue
                if any(
                    relative.parts[index : index + 2] == ("archive", "forensic_exports")
                    for index in range(len(relative.parts) - 1)
                ):
                    continue
                paths.append(path)
        return tuple(sorted(paths))

    @staticmethod
    def import_aliases(tree: ast.AST) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for imported in node.names:
                    aliases[imported.asname or imported.name.split(".", 1)[0]] = imported.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for imported in node.names:
                    aliases[imported.asname or imported.name] = f"{node.module}.{imported.name}"
        return aliases

    @classmethod
    def resolve_call_name(cls, node: ast.AST, aliases: dict[str, str]) -> str:
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            parts = cls.attribute_parts(node)
            if parts:
                return ".".join((aliases.get(parts[0], parts[0]), *parts[1:]))
        return ""

    @classmethod
    def attribute_parts(cls, node: ast.AST) -> tuple[str, ...]:
        if isinstance(node, ast.Name):
            return (node.id,)
        if isinstance(node, ast.Attribute):
            return (*cls.attribute_parts(node.value), node.attr)
        return ()

    @staticmethod
    def has_keyword(node: ast.Call, name: str) -> bool:
        return any(keyword.arg == name for keyword in node.keywords)

    @staticmethod
    def keyword_value(node: ast.Call, name: str):
        for keyword in node.keywords:
            if keyword.arg == name and isinstance(keyword.value, ast.Constant):
                return keyword.value.value
        return None

    @staticmethod
    def is_forbidden_process_call(call_name: str) -> bool:
        if call_name in OTHER_PROCESS_CALLS:
            return True
        return call_name.startswith(("os.exec", "os.spawn"))

    @staticmethod
    def assert_process_is_gone(pid: int) -> None:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except PermissionError as exc:  # pragma: no cover - unexpected local host policy
            raise AssertionError(f"cannot verify terminated child pid {pid}") from exc
        raise AssertionError(f"timed-out child pid {pid} is still running")


if __name__ == "__main__":
    unittest.main()
