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
from runtime.safety.subprocess_env import (
    SubprocessEnvironmentPolicyError,
    build_subprocess_env,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / "runtime"
EXPECTED_RUNTIME_BOUNDED_PROCESS_SITES = {
    "commands/local_commands.py": 1,
    "execution/controlled_test_runner.py": 1,
    "git_ops/controlled_git_commit.py": 1,
    "git_ops/git_controlled_push.py": 1,
    "git_ops/git_read.py": 1,
    "knowledge/tools/pdf_extract.py": 2,
    "package_ops/controlled_package_install.py": 2,
    "patches/post_patch_controlled_test_integration.py": 1,
    "tools/build_rhcsa_library.py": 2,
}
EXPECTED_RAW_PROCESS_BOUNDARY = {"safety/bounded_subprocess.py": 1}


class SubprocessEnvironmentIsolationTests(unittest.TestCase):
    def test_safe_runtime_values_survive_and_unrelated_values_do_not(self) -> None:
        ambient = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp/aoia-safe-home",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TERM": "xterm-256color",
            "AOIA_UNRELATED": "must-not-be-inherited",
            "PYTHONPATH": "/tmp/untrusted-python-path",
            "VIRTUAL_ENV": "/tmp/untrusted-parent-venv",
        }

        child = build_subprocess_env(ambient)

        self.assertEqual("/usr/bin:/bin", child["PATH"])
        self.assertEqual("/tmp/aoia-safe-home", child["HOME"])
        self.assertEqual("C.UTF-8", child["LANG"])
        self.assertEqual("C.UTF-8", child["LC_ALL"])
        self.assertEqual("xterm-256color", child["TERM"])
        self.assertNotIn("AOIA_UNRELATED", child)
        self.assertNotIn("PYTHONPATH", child)
        self.assertNotIn("VIRTUAL_ENV", child)

    def test_provider_generic_and_aws_secrets_are_absent_from_policy_output(self) -> None:
        ambient = {
            "PATH": "/usr/bin:/bin",
            "OPENAI_API_KEY": "NZ_TEST_SECRET_001",
            "SOME_PRIVATE_TOKEN": "NZ_TEST_SECRET_002",
            "AWS_ACCESS_KEY_ID": "NZ_TEST_AWS_ACCESS",
            "AWS_SECRET_ACCESS_KEY": "NZ_TEST_AWS_SECRET",
            "AWS_SESSION_TOKEN": "NZ_TEST_AWS_SESSION",
            "DATABASE_URL": "postgresql://synthetic.invalid/test",
        }

        child = build_subprocess_env(ambient)

        self.assertEqual({"PATH": "/usr/bin:/bin"}, child)

    def test_policy_does_not_mutate_parent_environment(self) -> None:
        synthetic = {
            "OPENAI_API_KEY": "NZ_TEST_SECRET_001",
            "SOME_PRIVATE_TOKEN": "NZ_TEST_SECRET_002",
        }
        with patch.dict(os.environ, synthetic, clear=False):
            before = dict(os.environ)
            child = build_subprocess_env()
            after = dict(os.environ)

        self.assertEqual(before, after)
        self.assertIsNot(child, os.environ)
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertNotIn("SOME_PRIVATE_TOKEN", child)

    def test_fixed_environment_rejects_sensitive_or_unknown_names(self) -> None:
        with self.assertRaises(SubprocessEnvironmentPolicyError):
            build_subprocess_env(inherit_names=(), fixed={"OPENAI_API_KEY": "synthetic"})
        with self.assertRaises(SubprocessEnvironmentPolicyError):
            build_subprocess_env(inherit_names=(), fixed={"AOIA_ARBITRARY": "value"})
        with self.assertRaises(SubprocessEnvironmentPolicyError):
            build_subprocess_env(inherit_names=("OPENAI_API_KEY",))

    def test_live_scemda_python_boundary_filters_secrets_and_preserves_runtime_values(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            project = root / "project"
            addon_dir = project / "addons" / "scemda"
            safe_home = root / "safe-home"
            addon_dir.mkdir(parents=True)
            safe_home.mkdir()
            (addon_dir / "scemda_agent_v2.py").write_text(
                "\n".join(
                    (
                        "import json",
                        "import os",
                        "import shutil",
                        "import subprocess",
                        "probe = subprocess.run(['printf', 'NZ_ENV_OK'], capture_output=True, text=True, check=True)",
                        "print(json.dumps({",
                        "    'PATH': os.environ.get('PATH'),",
                        "    'HOME': os.environ.get('HOME'),",
                        "    'LANG': os.environ.get('LANG'),",
                        "    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),",
                        "    'SOME_PRIVATE_TOKEN': os.environ.get('SOME_PRIVATE_TOKEN'),",
                        "    'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),",
                        "    'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),",
                        "    'AWS_SESSION_TOKEN': os.environ.get('AWS_SESSION_TOKEN'),",
                        "    'printf_path': shutil.which('printf'),",
                        "    'command_output': probe.stdout,",
                        "}, sort_keys=True))",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            runtime = SimpleNamespace(project_dir=project)
            ambient = {
                "AOIA_SHELL_EXECUTION_ENABLED": "1",
                "PATH": "/usr/bin:/bin",
                "HOME": str(safe_home),
                "LANG": "C.UTF-8",
                "OPENAI_API_KEY": "NZ_TEST_SECRET_001",
                "SOME_PRIVATE_TOKEN": "NZ_TEST_SECRET_002",
                "AWS_ACCESS_KEY_ID": "NZ_TEST_AWS_ACCESS",
                "AWS_SECRET_ACCESS_KEY": "NZ_TEST_AWS_SECRET",
                "AWS_SESSION_TOKEN": "NZ_TEST_AWS_SESSION",
            }
            with (
                patch.dict(os.environ, ambient, clear=False),
                patch.object(local_commands, "SCEMDA_ZIP", root / "missing.zip"),
                patch("builtins.input", return_value=""),
            ):
                result = local_commands.cmd_scemda("--environment-probe", runtime)

        self.assertTrue(result.handled)
        lines = result.message.splitlines()
        self.assertEqual("Exit code: 0", lines[0])
        payload = json.loads(lines[1])
        self.assertEqual("/usr/bin:/bin", payload["PATH"])
        self.assertEqual(str(safe_home), payload["HOME"])
        self.assertEqual("C.UTF-8", payload["LANG"])
        self.assertEqual("/usr/bin/printf", payload["printf_path"])
        self.assertEqual("NZ_ENV_OK", payload["command_output"])
        self.assertIsNone(payload["OPENAI_API_KEY"])
        self.assertIsNone(payload["SOME_PRIVATE_TOKEN"])
        self.assertIsNone(payload["AWS_ACCESS_KEY_ID"])
        self.assertIsNone(payload["AWS_SECRET_ACCESS_KEY"])
        self.assertIsNone(payload["AWS_SESSION_TOKEN"])
        self.assertNotIn("NZ_TEST_SECRET_001", result.message)
        self.assertNotIn("NZ_TEST_SECRET_002", result.message)

    def test_pdf_utility_receives_sanitized_environment(self) -> None:
        completed = subprocess.CompletedProcess(
            args=("pdfinfo", "synthetic.pdf"),
            returncode=0,
            stdout="Pages: 7\n",
            stderr="",
        )
        ambient = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp/aoia-pdf-home",
            "OPENAI_API_KEY": "NZ_TEST_SECRET_001",
        }
        with patch.dict(os.environ, ambient, clear=False), patch.object(
            pdf_extract.subprocess,
            "run",
            return_value=completed,
        ) as run_mock:
            pages = pdf_extract.read_page_count("pdfinfo", Path("synthetic.pdf"))

        self.assertEqual(7, pages)
        child = run_mock.call_args.kwargs["env"]
        self.assertEqual("/usr/bin:/bin", child["PATH"])
        self.assertEqual("/tmp/aoia-pdf-home", child["HOME"])
        self.assertNotIn("OPENAI_API_KEY", child)

    def test_every_active_runtime_process_site_passes_explicit_environment(self) -> None:
        discovered_bounded: dict[str, int] = {}
        discovered_raw: dict[str, int] = {}
        missing_environment: list[str] = []
        missing_timeout: list[str] = []
        forbidden_os_process_calls: list[str] = []

        for path in sorted(RUNTIME_ROOT.rglob("*.py")):
            if "archive" in path.parts or "forensic_exports" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(RUNTIME_ROOT).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Name) and node.func.id == "run_bounded_subprocess":
                    discovered_bounded[relative] = discovered_bounded.get(relative, 0) + 1
                    if not any(keyword.arg == "env" for keyword in node.keywords):
                        missing_environment.append(f"{relative}:{node.lineno}")
                    if not any(keyword.arg == "timeout" for keyword in node.keywords):
                        missing_timeout.append(f"{relative}:{node.lineno}")
                    continue
                if not isinstance(node.func, ast.Attribute):
                    continue
                owner = node.func.value
                if isinstance(owner, ast.Name) and owner.id == "subprocess" and node.func.attr in {
                    "run",
                    "Popen",
                    "call",
                    "check_call",
                    "check_output",
                }:
                    discovered_raw[relative] = discovered_raw.get(relative, 0) + 1
                    if not any(keyword.arg == "env" for keyword in node.keywords):
                        missing_environment.append(f"{relative}:{node.lineno}")
                    if not any(keyword.arg == "timeout" for keyword in node.keywords):
                        missing_timeout.append(f"{relative}:{node.lineno}")
                if (
                    isinstance(owner, ast.Name)
                    and owner.id == "os"
                    and node.func.attr in {"system", "popen"}
                ):
                    forbidden_os_process_calls.append(f"{relative}:{node.lineno}")

        self.assertEqual(EXPECTED_RUNTIME_BOUNDED_PROCESS_SITES, discovered_bounded)
        self.assertEqual(EXPECTED_RAW_PROCESS_BOUNDARY, discovered_raw)
        self.assertEqual([], missing_environment)
        self.assertEqual([], missing_timeout)
        self.assertEqual([], forbidden_os_process_calls)

    def test_development_only_clone_utility_also_passes_explicit_environment(self) -> None:
        path = REPO_ROOT / "scripts" / "dev" / "create_ioa_lab_clone.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_bounded_subprocess"
        ]

        self.assertEqual(1, len(calls))
        self.assertTrue(any(keyword.arg == "env" for keyword in calls[0].keywords))
        self.assertTrue(any(keyword.arg == "timeout" for keyword in calls[0].keywords))


if __name__ == "__main__":
    unittest.main()
