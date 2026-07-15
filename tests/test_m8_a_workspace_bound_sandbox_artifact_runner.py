from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.sandbox_workspace import (
    SandboxPathTraversalBlockedError,
    SandboxWorkspaceViolationError,
    assert_path_inside_workspace,
    assert_safe_artifact_write_path,
)
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactResult,
    SandboxArtifactState,
    SandboxArtifactType,
    create_blocked_sandbox_artifact_result,
    create_sandbox_artifact_request,
    sandbox_artifact_request_to_dict,
    sandbox_artifact_result_to_dict,
)
from tests.canonical_human_gate_support import canonical_gate_and_artifact_request


REPO_ROOT = Path(__file__).resolve().parents[1]
M8_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "sandbox_artifact.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_workspace.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
)
M8_RUNNER_FILE = REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py"


class M8AWorkspaceBoundSandboxArtifactRunnerTests(unittest.TestCase):
    def make_request(
        self,
        *,
        relative_output_path: str = "reports/result.txt",
        content_text: str = "sandbox artifact\n",
        artifact_type: SandboxArtifactType = SandboxArtifactType.TEXT_REPORT,
        human_approved: bool = True,
    ) -> SandboxArtifactRequest:
        return create_sandbox_artifact_request(
            run_id="dry-run-m8-a",
            sandbox_request_id="sandbox-request-m8-a",
            sandbox_result_id="sandbox-result-m8-a",
            artifact_type=artifact_type,
            relative_output_path=relative_output_path,
            content_text=content_text,
            requested_by="unit-test",
            human_approved=human_approved,
            dry_run_trace_id="dry-run-trace-m8-a",
            audit_event_id="audit-event-m8-a",
        )

    def make_authorized_request(
        self,
        *,
        relative_output_path: str = "reports/result.txt",
        content_text: str = "sandbox artifact\n",
        artifact_type: SandboxArtifactType = SandboxArtifactType.TEXT_REPORT,
    ):
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path=relative_output_path,
            content_text=content_text,
            run_id="dry-run-m8-a",
            requested_by="unit-test",
        )
        if artifact_type != request.artifact_type:
            request = create_sandbox_artifact_request(
                run_id=request.run_id,
                sandbox_request_id=request.sandbox_request_id,
                sandbox_result_id=request.sandbox_result_id,
                artifact_type=artifact_type,
                relative_output_path=request.relative_output_path,
                content_text=request.content_text,
                requested_by=request.requested_by,
                human_approved=True,
                dry_run_trace_id=request.dry_run_trace_id,
                approval_decision_id=request.approval_decision_id,
                audit_event_id=request.audit_event_id,
                contract_audit_event_id=request.contract_audit_event_id,
            )
        return gate, request

    def test_sandbox_artifact_request_can_be_created(self) -> None:
        request = self.make_request()

        self.assertIsInstance(request, SandboxArtifactRequest)
        self.assertEqual(request.artifact_type, SandboxArtifactType.TEXT_REPORT)
        self.assertEqual(len(request.content_hash), 64)

    def test_sandbox_artifact_result_can_be_serialized(self) -> None:
        request = self.make_request()
        result = create_blocked_sandbox_artifact_result(
            request,
            workspace_root="/explicit/workspace",
            blocked_reason="blocked",
        )

        self.assertIsInstance(result, SandboxArtifactResult)
        self.assertIsInstance(sandbox_artifact_request_to_dict(request), dict)
        self.assertIsInstance(sandbox_artifact_result_to_dict(result), dict)
        self.assertEqual(sandbox_artifact_result_to_dict(result)["state"], SandboxArtifactState.BLOCKED.value)

    def test_content_hash_is_deterministic(self) -> None:
        first = self.make_request(content_text="same content", relative_output_path="first.txt")
        second = self.make_request(content_text="same content", relative_output_path="second.txt")
        third = self.make_request(content_text="different content", relative_output_path="third.txt")

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertNotEqual(first.content_hash, third.content_hash)

    def test_safe_txt_artifact_can_be_written_inside_temp_workspace(self) -> None:
        self.assert_safe_artifact_written("reports/result.txt", "text result\n")

    def test_safe_md_artifact_can_be_written_inside_temp_workspace(self) -> None:
        self.assert_safe_artifact_written("reports/result.md", "# Result\n")

    def test_safe_json_artifact_can_be_written_inside_temp_workspace(self) -> None:
        request, result, output = self.assert_safe_artifact_written(
            "reports/result.json",
            '{"state":"ok"}\n',
            artifact_type=SandboxArtifactType.JSON_SUMMARY,
        )

        self.assertEqual(result.content_hash, request.content_hash)
        self.assertEqual(output.suffix, ".json")

    def test_written_artifact_content_matches_request_content(self) -> None:
        request, result, _output = self.assert_safe_artifact_written("artifact.txt", "literal content")

        self.assertEqual(result.content_hash, request.content_hash)

    def test_written_result_marks_attempt_and_completion(self) -> None:
        _request, result, _output = self.assert_safe_artifact_written("artifact.txt", "done")

        self.assertTrue(result.write_attempted)
        self.assertTrue(result.write_completed)
        self.assertEqual(result.state, SandboxArtifactState.WRITTEN)

    def test_absolute_output_path_is_blocked(self) -> None:
        self.assert_runner_blocks_path("/tmp/outside.txt", "absolute artifact paths are blocked")

    def test_path_traversal_is_blocked(self) -> None:
        self.assert_runner_blocks_path("../outside.txt", "artifact path traversal is blocked")

    def test_git_path_is_blocked(self) -> None:
        self.assert_runner_blocks_path(".git/config.txt", "artifact writes into .git are blocked")

    def test_unsafe_extension_is_blocked(self) -> None:
        self.assert_runner_blocks_path("scripts/run.sh", "artifact extension is not allowed")

    def test_symlink_escape_is_blocked_when_supported(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            link_path = Path(workspace) / "escape"
            try:
                link_path.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            gate, request = self.make_authorized_request(relative_output_path="escape/outside.txt")
            result = write_sandbox_artifact(request, workspace, approval_evidence=gate)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(result.write_attempted)
            self.assertFalse((Path(outside) / "outside.txt").exists())

    def test_existing_file_overwrite_is_blocked_by_default(self) -> None:
        with TemporaryDirectory() as workspace:
            output = Path(workspace) / "artifact.txt"
            output.write_text("existing", encoding="utf-8")
            gate, request = self.make_authorized_request(relative_output_path="artifact.txt", content_text="new")

            result = write_sandbox_artifact(request, workspace, approval_evidence=gate)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(result.write_attempted)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing")

    def test_existing_file_overwrite_is_allowed_only_inside_workspace_when_requested(self) -> None:
        with TemporaryDirectory() as workspace:
            output = Path(workspace) / "artifact.txt"
            output.write_text("existing", encoding="utf-8")
            gate, request = self.make_authorized_request(relative_output_path="artifact.txt", content_text="new")

            result = write_sandbox_artifact(request, workspace, allow_overwrite=True, approval_evidence=gate)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)
            self.assertEqual(output.read_text(encoding="utf-8"), "new")
            assert_path_inside_workspace(workspace, result.resolved_output_path)

    def test_workspace_guard_rejects_output_outside_workspace(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            outside_path = str(Path(outside) / "artifact.txt")

            with self.assertRaises(SandboxPathTraversalBlockedError):
                assert_path_inside_workspace(workspace, outside_path)

    def test_artifact_runner_does_not_execute_shell_like_content(self) -> None:
        marker_name = "m8_a_marker_should_not_exist.txt"
        shell_like_content = "#!/bin/sh\nprintf executed > " + marker_name + "\n"
        with TemporaryDirectory() as workspace:
            gate, request = self.make_authorized_request(relative_output_path="script.md", content_text=shell_like_content)

            result = write_sandbox_artifact(request, workspace, approval_evidence=gate)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)
            self.assertFalse((Path(workspace) / marker_name).exists())
            self.assertEqual(Path(result.resolved_output_path).read_text(encoding="utf-8"), shell_like_content)

    def test_human_approval_is_required_but_does_not_enable_arbitrary_execution(self) -> None:
        with TemporaryDirectory() as workspace:
            request = self.make_request(human_approved=False)

            result = write_sandbox_artifact(request, workspace)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(result.write_attempted)

    def test_workspace_guard_rejects_relative_workspace_root(self) -> None:
        with self.assertRaises(SandboxWorkspaceViolationError):
            assert_safe_artifact_write_path("relative-workspace", "artifact.txt")

    def test_runtime_does_not_add_provider_api_network_calls(self) -> None:
        self.assert_forbidden_runtime_imports_absent(
            {"requests", "urllib", "http.client", "socket", "openai", "anthropic", "google.cloud"}
        )

    def test_runtime_does_not_add_subprocess_os_system_or_popen(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"subprocess", "pty", "pexpect"})
        self.assert_forbidden_runtime_terms_absent(("os.system", "Popen"))

    def test_runtime_does_not_add_browser_git_or_cloud_capability(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"webbrowser", "selenium", "playwright", "git"})
        self.assert_forbidden_runtime_imports_absent({"google.cloud", "google.generativeai"})

    def test_runtime_does_not_read_api_keys_or_environment(self) -> None:
        self.assert_forbidden_runtime_terms_absent(("dotenv", "os.environ", "API_KEY", "SECRET", "TOKEN"))

    def test_runtime_does_not_add_database_or_delete_capability(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"sqlite3", "shutil"})
        self.assert_forbidden_runtime_terms_absent(("shutil.rmtree",))

    def test_artifact_runner_does_not_modify_repo_files(self) -> None:
        repo_marker = REPO_ROOT / "__aoia_m8_a_repo_guard_should_not_exist__.txt"
        self.assertFalse(repo_marker.exists())
        with TemporaryDirectory() as workspace:
            gate, request = self.make_authorized_request(relative_output_path=repo_marker.name, content_text="workspace only")

            result = write_sandbox_artifact(request, workspace, approval_evidence=gate)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)
            self.assertFalse(repo_marker.exists())
            self.assertTrue((Path(workspace) / repo_marker.name).exists())

    def test_static_import_scan_rejects_forbidden_clients_in_new_runtime_files(self) -> None:
        forbidden_modules = {
            "subprocess",
            "pty",
            "pexpect",
            "requests",
            "urllib",
            "http.client",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "openai",
            "anthropic",
            "google.cloud",
            "google.generativeai",
            "dotenv",
            "os",
            "sqlite3",
            "shutil",
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "Path.write_text",
            "shutil.rmtree",
        )

        for source_file in M8_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            for term in forbidden_text:
                self.assertNotIn(term, source)
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for module_name in imports:
                self.assertNotIn(module_name, forbidden_modules)
                self.assertFalse(any(module_name == item or module_name.startswith(item + ".") for item in forbidden_modules))

    def test_pathlib_open_is_limited_to_artifact_runner(self) -> None:
        for source_file in M8_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            if source_file == M8_RUNNER_FILE:
                continue
            self.assertNotIn(".open(", source)

    def assert_safe_artifact_written(
        self,
        relative_output_path: str,
        content_text: str,
        *,
        artifact_type: SandboxArtifactType = SandboxArtifactType.TEXT_REPORT,
    ) -> tuple[SandboxArtifactRequest, SandboxArtifactResult, Path]:
        with TemporaryDirectory() as workspace:
            gate, request = self.make_authorized_request(
                relative_output_path=relative_output_path,
                content_text=content_text,
                artifact_type=artifact_type,
            )

            result = write_sandbox_artifact(request, workspace, approval_evidence=gate)
            output = Path(result.resolved_output_path)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)
            self.assertEqual(output.read_text(encoding="utf-8"), content_text)
            assert_path_inside_workspace(workspace, str(output))
            return request, result, output

    def assert_runner_blocks_path(self, relative_output_path: str, expected_reason: str) -> None:
        with TemporaryDirectory() as workspace:
            gate, request = self.make_authorized_request(relative_output_path=relative_output_path)

            result = write_sandbox_artifact(request, workspace, approval_evidence=gate)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(result.write_attempted)
            self.assertFalse(result.write_completed)
            self.assertIn(expected_reason, result.blocked_reason)

    def assert_forbidden_runtime_terms_absent(self, forbidden_text: tuple[str, ...]) -> None:
        for source_file in M8_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            for term in forbidden_text:
                self.assertNotIn(term, source)

    def assert_forbidden_runtime_imports_absent(self, forbidden_modules: set[str]) -> None:
        for source_file in M8_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for module_name in imports:
                self.assertNotIn(module_name, forbidden_modules)
                self.assertFalse(any(module_name == item or module_name.startswith(item + ".") for item in forbidden_modules))


if __name__ == "__main__":
    unittest.main()
