from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.control_write import ControlWriteContext, write_preview_artifact_after_human_gate
from runtime.git_ops.git_env import build_hardened_git_env
from runtime.git_ops.git_read import (
    GIT_READ_BLOCKED,
    GIT_READ_BLOCKED_OUTPUT_LIMIT,
    GIT_READ_BLOCKED_UNSAFE_PATH_ARGUMENT,
    GIT_READ_BLOCKED_UNSUPPORTED_COMMAND,
    GIT_READ_COMMAND_BLOCKED,
    GIT_READ_ERROR,
    GIT_READ_ERROR_TIMEOUT,
    GIT_READ_READY,
    GitReadCommand,
    GitReadRequest,
    canonical_git_read_json,
    compute_git_read_hash,
    read_local_git_state,
    run_allowlisted_git_read,
    validate_git_workspace_root,
)
from runtime.git_ops.git_sanitize import redact_git_secrets, sanitize_git_output


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_READ_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_read.py"
GIT_ENV_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_env.py"
GIT_SANITIZE_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_sanitize.py"
STEP26_MODULE = REPO_ROOT / "runtime" / "patches" / "post_patch_controlled_test_integration.py"
AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "git_write_authority_granted",
    "provider_authority_granted",
    "execution_authority_granted",
)


class GitEnvironmentHardeningReadAdapter1ATests(unittest.TestCase):
    def test_valid_git_repo_produces_structured_result_with_head_branch_and_clean_state(self):
        with git_repo() as repo:
            result = read_local_git_state(GitReadRequest(workspace_root=str(repo)))

        self.assertEqual(GIT_READ_READY, result.status)
        self.assertEqual(str(repo), result.repo_root)
        self.assertRegex(result.head_sha or "", r"^[0-9a-f]{40}$")
        self.assertEqual("main", result.branch_name)
        self.assertFalse(result.detached_head)
        self.assertTrue(result.clean)
        self.assertEqual((), result.staged_paths)
        self.assertEqual((), result.unstaged_paths)
        self.assertEqual((), result.untracked_paths)
        self.assertEqual((GIT_READ_READY,), tuple({result.status}))
        self.assertIn("evidence only", result.reason)

    def test_result_detects_staged_unstaged_and_untracked_paths(self):
        with git_repo() as repo:
            (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
            self.git(repo, "add", "staged.txt")
            (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
            (repo / "untracked.txt").write_text("new\n", encoding="utf-8")

            result = read_local_git_state(GitReadRequest(workspace_root=str(repo)))

        self.assertEqual(GIT_READ_READY, result.status)
        self.assertFalse(result.clean)
        self.assertIn("staged.txt", result.staged_paths)
        self.assertIn("tracked.txt", result.unstaged_paths)
        self.assertIn("untracked.txt", result.untracked_paths)
        self.assert_authority_false(result)

    def test_file_named_force_and_pathlike_names_are_inert_output_only(self):
        with git_repo() as repo:
            (repo / "--force").write_text("flag-shaped filename\n", encoding="utf-8")
            (repo / "colon:(glob)").write_text("pathspec-shaped filename\n", encoding="utf-8")

            result = read_local_git_state(GitReadRequest(workspace_root=str(repo)))

        self.assertEqual(GIT_READ_READY, result.status)
        self.assertIn("--force", result.untracked_paths)
        self.assertIn("colon:(glob)", result.untracked_paths)
        self.assert_authority_false(result)

    def test_clean_and_dirty_repo_are_evidence_only(self):
        with git_repo() as repo:
            clean = read_local_git_state(GitReadRequest(workspace_root=str(repo)))
            (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            dirty = read_local_git_state(GitReadRequest(workspace_root=str(repo)))

        for result in (clean, dirty):
            self.assertEqual(GIT_READ_READY, result.status)
            self.assertFalse(result.can_approve)
            self.assertFalse(result.can_write)
            self.assertFalse(result.can_commit)
            self.assertFalse(result.can_push)
            self.assertFalse(result.git_write_authority_granted)
            self.assertIn("evidence", result.reason)

    def test_git_read_hash_and_canonical_json_are_deterministic(self):
        with git_repo() as repo:
            first = read_local_git_state(GitReadRequest(workspace_root=str(repo)))
            second = read_local_git_state(GitReadRequest(workspace_root=str(repo)))

        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        self.assertEqual(first.git_read_hash, second.git_read_hash)
        self.assertEqual(canonical_git_read_json(left), canonical_git_read_json(right))
        self.assertEqual(compute_git_read_hash(left), compute_git_read_hash(right))

    def test_authority_fields_always_false_even_if_replaced(self):
        with git_repo() as repo:
            result = read_local_git_state(GitReadRequest(workspace_root=str(repo)))
            forced = replace(
                result,
                can_approve=True,
                can_write=True,
                can_execute=True,
                can_commit=True,
                can_push=True,
                can_call_provider=True,
                can_change_gate=True,
                git_write_authority_granted=True,
                provider_authority_granted=True,
                execution_authority_granted=True,
            )

        self.assert_authority_false(forced)
        data = forced.to_dict()
        for field in AUTHORITY_FIELDS:
            self.assertIs(data[field], False)

    def test_non_git_directory_missing_workspace_and_outside_repo_root_block(self):
        with TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp).resolve()
            non_git = read_local_git_state(GitReadRequest(workspace_root=str(root)))
            missing = read_local_git_state(GitReadRequest(workspace_root=None))
            repo_parent = root / "repo"
            self.init_repo(repo_parent)
            child = repo_parent / "child"
            child.mkdir()
            child_result = read_local_git_state(GitReadRequest(workspace_root=str(child)))

        self.assertEqual(GIT_READ_BLOCKED, non_git.status)
        self.assertEqual(GIT_READ_BLOCKED, missing.status)
        self.assertEqual(GIT_READ_BLOCKED, child_result.status)
        self.assertIn("GIT_READ_BLOCKED_REPO_ROOT_OUTSIDE_WORKSPACE", child_result.reason_codes)

    def test_wrong_cwd_does_not_escape_workspace(self):
        with TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp).resolve()
            repo = root / "repo"
            self.init_repo(repo)
            outside = root / "outside"
            outside.mkdir()

            result = read_local_git_state(GitReadRequest(workspace_root=str(outside)))

        self.assertEqual(GIT_READ_BLOCKED, result.status)

    def test_pathspec_traversal_magic_symlink_escape_and_force_are_rejected_or_impossible(self):
        with git_repo() as repo:
            for path_argument in ("../x", ":(glob)*", str(repo / "link"), "--force"):
                with self.subTest(path_argument=path_argument):
                    result = validate_git_workspace_root(str(repo), path_argument=path_argument)

                    self.assertEqual(GIT_READ_BLOCKED, result.status)
                    self.assertEqual((GIT_READ_BLOCKED_UNSAFE_PATH_ARGUMENT,), result.reason_codes)

            request_fields = set(GitReadRequest.__dataclass_fields__)
            self.assertNotIn("pathspec", request_fields)
            self.assertNotIn("paths", request_fields)

    def test_no_raw_command_string_accepted_and_arbitrary_or_write_commands_block_before_subprocess(self):
        with git_repo() as repo:
            request = GitReadRequest(workspace_root=str(repo))
            for command in ("status", "COMMIT", "PUSH", "FETCH", "PULL", "ADD"):
                with self.subTest(command=command), patch("runtime.git_ops.git_read.subprocess.run") as run_mock:
                    evidence = run_allowlisted_git_read(request, command)  # type: ignore[arg-type]

                    self.assertEqual(GIT_READ_COMMAND_BLOCKED, evidence.status)
                    self.assertEqual(GIT_READ_BLOCKED_UNSUPPORTED_COMMAND, evidence.reason_code)
                    self.assertFalse(evidence.subprocess_started)
                    run_mock.assert_not_called()

    def test_allowlisted_subprocess_uses_arg_list_shell_false_timeout_cwd_and_hardened_env(self):
        with git_repo() as repo:
            completed = subprocess.CompletedProcess(args=("git",), returncode=0, stdout=str(repo) + "\n", stderr="")
            with patch("runtime.git_ops.git_read.subprocess.run", return_value=completed) as run_mock:
                evidence = run_allowlisted_git_read(GitReadRequest(workspace_root=str(repo)), GitReadCommand.SHOW_TOPLEVEL)

        self.assertEqual("PASS", evidence.status)
        self.assertEqual(("git", "rev-parse", "--show-toplevel"), run_mock.call_args.args[0])
        self.assertIs(run_mock.call_args.kwargs["shell"], False)
        self.assertEqual(str(repo), run_mock.call_args.kwargs["cwd"])
        self.assertEqual(10, run_mock.call_args.kwargs["timeout"])
        env = run_mock.call_args.kwargs["env"]
        self.assertEqual("0", env["GIT_TERMINAL_PROMPT"])
        self.assertEqual("1", env["GIT_CONFIG_NOGLOBAL"])
        self.assertEqual("1", env["GIT_CONFIG_NOSYSTEM"])
        self.assertEqual("", env["GIT_PAGER"])
        self.assertEqual("", env["GIT_EXTERNAL_DIFF"])
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GITHUB_TOKEN", env)

    def test_malicious_ambient_git_environment_has_no_effect(self):
        ambient = {
            "GIT_PAGER": "touch pager_marker",
            "GIT_EDITOR": "touch editor_marker",
            "GIT_SSH_COMMAND": "touch ssh_marker",
            "GIT_EXTERNAL_DIFF": "touch diff_marker",
            "GIT_CONFIG_GLOBAL": "/tmp/evil-config",
            "GIT_CONFIG_SYSTEM": "/tmp/evil-system-config",
            "GIT_DIR": "/tmp/evil-git-dir",
            "GIT_WORK_TREE": "/tmp/evil-work-tree",
            "OPENAI_API_KEY": "secret",
            "GITHUB_TOKEN": "secret",
        }

        env = build_hardened_git_env(ambient)

        self.assertEqual("", env["GIT_PAGER"])
        self.assertEqual(":", env["GIT_EDITOR"])
        self.assertEqual("", env["GIT_SSH_COMMAND"])
        self.assertEqual("", env["GIT_EXTERNAL_DIFF"])
        self.assertEqual("/dev/null", env["GIT_CONFIG_GLOBAL"])
        self.assertEqual("/dev/null", env["GIT_CONFIG_SYSTEM"])
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GIT_WORK_TREE", env)
        self.assertNotIn("GIT_COMMON_DIR", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GITHUB_TOKEN", env)

    def test_malicious_hooks_pager_config_and_external_diff_do_not_execute_during_read(self):
        with git_repo() as repo:
            marker = repo / "marker"
            hook = repo / ".git" / "hooks" / "pre-commit"
            hook.write_text("#!/bin/sh\nprintf hook > marker\n", encoding="utf-8")
            hook.chmod(0o755)
            self.git(repo, "config", "core.pager", f"sh -c 'printf pager > {marker}'")
            self.git(repo, "config", "diff.external", f"sh -c 'printf diff > {marker}'")
            (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")

            result = read_local_git_state(GitReadRequest(workspace_root=str(repo)))

        self.assertEqual(GIT_READ_READY, result.status)
        self.assertFalse(marker.exists())

    def test_stdout_and_stderr_secret_redaction_and_control_sanitization(self):
        raw = (
            "\x1b[31mghp_abcdefghijklmnopqrstuvwxyz123456"
            " github_pat_abcdefghijklmnopqrstuvwxyz123456"
            " https://TOKENVALUE@github.com/org/repo"
            " token=abc123 access_token=def456\x07"
        )
        sanitized = sanitize_git_output(raw)

        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", sanitized)
        self.assertNotIn("TOKENVALUE", sanitized)
        self.assertNotIn("abc123", sanitized)
        self.assertNotIn("def456", sanitized)
        self.assertNotIn("\x1b", sanitized)
        self.assertNotIn("\x07", sanitized)
        self.assertIn("ghp_[REDACTED]", sanitized)
        self.assertIn("github_pat_[REDACTED]", sanitized)
        self.assertIn("https://[REDACTED]@github.com", sanitized)
        self.assertIn("token=[REDACTED]", sanitized)
        self.assertIn("access_token=[REDACTED]", sanitized)
        self.assertEqual(sanitized, redact_git_secrets(sanitized))

    def test_subprocess_stdout_and_stderr_are_redacted_before_result_and_hash(self):
        with git_repo() as repo:
            completed = subprocess.CompletedProcess(
                args=("git",),
                returncode=1,
                stdout="ghp_abcdefghijklmnopqrstuvwxyz123456",
                stderr="access_token=secret123",
            )
            with patch("runtime.git_ops.git_read.subprocess.run", return_value=completed):
                evidence = run_allowlisted_git_read(GitReadRequest(workspace_root=str(repo)), GitReadCommand.VERIFY_HEAD)

        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", evidence.stdout_preview)
        self.assertNotIn("secret123", evidence.stderr_preview)
        self.assertIn("ghp_[REDACTED]", evidence.stdout_preview)
        self.assertIn("access_token=[REDACTED]", evidence.stderr_preview)

    def test_oversized_output_is_bounded_and_fail_closed(self):
        with git_repo() as repo:
            completed = subprocess.CompletedProcess(args=("git",), returncode=0, stdout="x" * 1000, stderr="")
            with patch("runtime.git_ops.git_read.subprocess.run", return_value=completed):
                evidence = run_allowlisted_git_read(
                    GitReadRequest(workspace_root=str(repo), max_output_bytes=256),
                    GitReadCommand.STATUS_PORCELAIN,
                )

        self.assertEqual("ERROR", evidence.status)
        self.assertEqual(GIT_READ_BLOCKED_OUTPUT_LIMIT, evidence.reason_code)
        self.assertTrue(evidence.stdout_truncated)
        self.assertLessEqual(len(evidence.stdout_preview.encode("utf-8")), 256)

    def test_timeout_returns_stable_error_result(self):
        with git_repo() as repo:
            timeout = subprocess.TimeoutExpired(cmd=("git",), timeout=1, output="ghp_abcdefghijklmnopqrstuvwxyz123456", stderr="")
            with patch("runtime.git_ops.git_read.subprocess.run", side_effect=timeout):
                first = run_allowlisted_git_read(GitReadRequest(workspace_root=str(repo)), GitReadCommand.STATUS_PORCELAIN)
                second = run_allowlisted_git_read(GitReadRequest(workspace_root=str(repo)), GitReadCommand.STATUS_PORCELAIN)

        self.assertEqual("ERROR", first.status)
        self.assertEqual(GIT_READ_ERROR_TIMEOUT, first.reason_code)
        self.assertTrue(first.timeout_expired)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", first.stdout_preview)

    def test_result_cannot_satisfy_control_write_gate_or_commit_push_authority(self):
        with git_repo() as repo:
            result = read_local_git_state(GitReadRequest(workspace_root=str(repo)))
            artifact = repo / "artifact.txt"
            context = ControlWriteContext(
                run_id="run",
                sandbox_request_id="sandbox-request",
                sandbox_result_id="sandbox-result",
                requested_by="test",
                dry_run_trace_id="dry-run",
                sandbox_policy_decision_id="policy",
            )
            control = write_preview_artifact_after_human_gate(
                preview=result,
                proposed_content_text="blocked",
                workspace_root=str(repo),
                gate_result=result,
                context=context,
                gated_writer=lambda **kwargs: self.fail("git read result must not reach gated writer"),
            )

        self.assertFalse(control.artifact_write_occurred)
        self.assertFalse(result.can_commit)
        self.assertFalse(result.can_push)
        self.assertFalse(result.git_write_authority_granted)

    def test_static_boundary_allows_subprocess_only_in_step26_and_step27a_modules(self):
        allowed = {
            STEP26_MODULE,
            GIT_READ_MODULE,
            REPO_ROOT / "runtime" / "git_ops" / "controlled_git_commit.py",
            REPO_ROOT / "runtime" / "git_ops" / "git_controlled_push.py",
            REPO_ROOT / "runtime" / "execution" / "controlled_test_runner.py",
            REPO_ROOT / "runtime" / "commands" / "local_commands.py",
            REPO_ROOT / "runtime" / "tools" / "build_rhcsa_library.py",
        }
        findings = []
        for path in runtime_files():
            scan = scan_module(path)
            if "subprocess" in scan.imports or "subprocess.run" in scan.calls:
                if path not in allowed:
                    findings.append(path.relative_to(REPO_ROOT).as_posix())

        self.assertEqual([], findings)

    def test_static_boundary_forbids_shell_true_python_git_network_provider_and_env_secret_reads(self):
        forbidden_import_prefixes = (
            "git",
            "GitPython",
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
            "ssl",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.genai",
            "ollama",
            "webbrowser",
            "selenium",
            "playwright",
        )
        for path in (GIT_READ_MODULE, GIT_ENV_MODULE, GIT_SANITIZE_MODULE):
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                scan = scan_module(path)
                source = path.read_text(encoding="utf-8").casefold()
                self.assertNotIn("shell=true", source)
                self.assertNotIn("os.environ", source)
                self.assertNotIn("getenv", source)
                self.assertEqual(
                    [],
                    [
                        module_name
                        for module_name in scan.imports
                        if matches_any_prefix(module_name, forbidden_import_prefixes)
                    ],
                )

    def test_no_github_api_network_or_provider_capability_added(self):
        text = "\n".join(path.read_text(encoding="utf-8") for path in (GIT_READ_MODULE, GIT_ENV_MODULE, GIT_SANITIZE_MODULE))
        forbidden = (
            "github.com/api",
            "api.github.com",
            "ls-remote",
            "openai",
            "anthropic",
            "requests",
            "httpx",
        )

        self.assertEqual([], [item for item in forbidden if item in text.casefold()])

    @staticmethod
    def init_repo(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        GitEnvironmentHardeningReadAdapter1ATests.git(path, "init", "-q", "-b", "main")
        (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
        GitEnvironmentHardeningReadAdapter1ATests.git(path, "add", "tracked.txt")
        GitEnvironmentHardeningReadAdapter1ATests.git(
            path,
            "-c",
            "user.name=AOIA Test",
            "-c",
            "user.email=aoia@example.invalid",
            "commit",
            "-q",
            "-m",
            "initial",
        )

    @staticmethod
    def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", *args),
            cwd=repo,
            shell=False,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def assert_authority_false(self, result) -> None:
        for field in AUTHORITY_FIELDS:
            self.assertIs(getattr(result, field), False)


def git_repo():
    class RepoContext:
        def __enter__(self):
            self.tmp = TemporaryDirectory()
            self.repo = Path(self.tmp.name).resolve() / "repo"
            GitEnvironmentHardeningReadAdapter1ATests.init_repo(self.repo)
            return self.repo.resolve()

        def __exit__(self, exc_type, exc, tb):
            self.tmp.cleanup()
            return False

    return RepoContext()


def runtime_files() -> tuple[Path, ...]:
    excluded = {"__pycache__", "knowledge", "reports"}
    return tuple(
        sorted(
            path
            for path in (REPO_ROOT / "runtime").rglob("*.py")
            if not any(part in excluded for part in path.parts)
        )
    )


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.append(name)
    return type("Scan", (), {"imports": tuple(imports), "calls": tuple(calls)})()


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if parts:
            return ".".join((aliases.get(parts[0], parts[0]), *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


def matches_any_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in prefixes)


if __name__ == "__main__":
    unittest.main()
