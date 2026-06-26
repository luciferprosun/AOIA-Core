from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    ControlWriteContext,
    write_preview_artifact_after_human_gate,
)
from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import evaluate_human_decision_pre_artifact_gate
from runtime.human_decision_gated_artifact_write import (
    BLOCKED_CONTROLLED_WRITE,
    BLOCKED_WRITE_KILL_SWITCH,
)
from runtime.patches.patch_preview import (
    MAX_PATCH_PREVIEW_FILES,
    MAX_PATCH_PREVIEW_FILE_BYTES,
    PATCH_PREVIEW_BLOCKED_DUPLICATE_TARGET,
    PATCH_PREVIEW_BLOCKED_EMPTY_EDIT_LIST,
    PATCH_PREVIEW_BLOCKED_OVERSIZED_CONTENT,
    PATCH_PREVIEW_BLOCKED_TOO_MANY_FILES,
    PATCH_PREVIEW_BLOCKED_UNSAFE_PATH,
    PATCH_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION,
    PATCH_PREVIEW_READY,
    PATCH_RISK_DIFF_TRUNCATED,
    PATCH_RISK_DOCS_TARGET,
    PATCH_RISK_MULTIPLE_FILES,
    PATCH_RISK_RUNTIME_TARGET,
    PATCH_RISK_TEST_TARGET,
    PatchFileEdit,
    build_patch_preview,
    canonical_patch_preview_json,
    compute_patch_preview_hash,
)
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_PREVIEW_MODULE = REPO_ROOT / "runtime" / "patches" / "patch_preview.py"
CONTENT = "# Patch preview fixture\n"
UPDATED_CONTENT = "# Patch preview fixture\n\nUpdated.\n"
TARGET_PATH = "docs/patch-preview.md"
PACKET_HASH = "a" * 64
ARTIFACT_HASH = hashlib.sha256(UPDATED_CONTENT.encode("utf-8")).hexdigest()


class DiffBasedEditProposalPatchPreview1ATests(unittest.TestCase):
    def test_valid_single_file_patch_preview_is_created(self):
        result = build_patch_preview(
            [
                PatchFileEdit(
                    target_path=TARGET_PATH,
                    proposed_content=UPDATED_CONTENT,
                    original_content=CONTENT,
                    operation="update",
                )
            ]
        )

        self.assertEqual(PATCH_PREVIEW_READY, result.status)
        self.assertTrue(result.preview_ready)
        self.assertIsNotNone(result.patch_preview)
        assert result.patch_preview is not None
        self.assertEqual(("docs/patch-preview.md",), result.patch_preview.target_paths)
        self.assertEqual(1, result.patch_preview.total_file_count)
        self.assertEqual(ARTIFACT_HASH, result.patch_preview.files[0].proposed_sha256)

    def test_valid_multi_file_patch_preview_is_created(self):
        result = build_patch_preview(
            [
                PatchFileEdit("tests/example_test.py", "assert True\n", "", operation="create"),
                PatchFileEdit("runtime/example.py", "VALUE = 1\n", "VALUE = 0\n", operation="update"),
            ]
        )

        self.assertEqual(PATCH_PREVIEW_READY, result.status)
        assert result.patch_preview is not None
        self.assertEqual(2, result.patch_preview.total_file_count)
        self.assertIn(PATCH_RISK_MULTIPLE_FILES, result.patch_preview.risk_flags)
        self.assertIn(PATCH_RISK_RUNTIME_TARGET, result.patch_preview.risk_flags)
        self.assertIn(PATCH_RISK_TEST_TARGET, result.patch_preview.risk_flags)

    def test_patch_preview_hash_is_deterministic(self):
        first = self.preview()
        second = self.preview()

        self.assertEqual(first.preview_hash, second.preview_hash)
        self.assertEqual(first.patch_preview.to_dict(), second.patch_preview.to_dict())

    def test_canonical_patch_preview_json_is_deterministic_independent_of_dict_order(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}

        self.assertEqual(canonical_patch_preview_json(left), canonical_patch_preview_json(right))
        self.assertEqual(compute_patch_preview_hash(left), compute_patch_preview_hash(right))

    def test_multi_file_preview_sorts_target_paths_deterministically(self):
        result = build_patch_preview(
            [
                PatchFileEdit("runtime/z.py", "Z = 1\n", "Z = 0\n"),
                PatchFileEdit("docs/a.md", "A\n", ""),
                PatchFileEdit("tests/m.py", "M\n", ""),
            ]
        )

        assert result.patch_preview is not None
        self.assertEqual(("docs/a.md", "runtime/z.py", "tests/m.py"), result.patch_preview.target_paths)

    def test_per_file_proposed_hashes_are_deterministic(self):
        first = self.preview()
        second = self.preview()

        self.assertEqual(
            first.patch_preview.files[0].proposed_sha256,
            second.patch_preview.files[0].proposed_sha256,
        )
        self.assertEqual(ARTIFACT_HASH, first.patch_preview.files[0].proposed_sha256)

    def test_original_hash_is_included_when_original_content_is_supplied(self):
        result = self.preview()
        original_hash = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()

        self.assertEqual(original_hash, result.patch_preview.files[0].original_sha256)

    def test_bounded_unified_diff_is_produced_when_original_content_is_supplied(self):
        result = self.preview()
        diff = result.patch_preview.files[0].diff_preview

        self.assertIsNotNone(diff)
        self.assertIn("--- a/docs/patch-preview.md", diff)
        self.assertIn("+++ b/docs/patch-preview.md", diff)
        self.assertFalse(result.patch_preview.files[0].diff_truncated)

    def test_missing_original_content_still_produces_safe_metadata(self):
        result = build_patch_preview([PatchFileEdit(TARGET_PATH, UPDATED_CONTENT, None, operation="create")])

        self.assertEqual(PATCH_PREVIEW_READY, result.status)
        assert result.patch_preview is not None
        self.assertIsNone(result.patch_preview.files[0].original_sha256)
        self.assertIsNone(result.patch_preview.files[0].diff_preview)

    def test_empty_patch_edit_list_is_rejected(self):
        result = build_patch_preview([])

        self.assertEqual(PATCH_PREVIEW_BLOCKED_EMPTY_EDIT_LIST, result.status)
        self.assertFalse(result.preview_ready)

    def test_duplicate_target_paths_are_rejected(self):
        result = build_patch_preview(
            [
                PatchFileEdit("docs/a.md", "A\n"),
                PatchFileEdit("docs/./a.md", "B\n"),
            ]
        )

        self.assertEqual(PATCH_PREVIEW_BLOCKED_DUPLICATE_TARGET, result.status)

    def test_unsafe_target_paths_are_rejected(self):
        cases = {
            "absolute": "/tmp/escape.txt",
            "parent": "../escape.txt",
            "nested_parent": "docs/../../escape.txt",
            "backslash": "..\\escape.txt",
            "null_byte": "bad\x00path.txt",
            "empty": "",
            "dot_git": ".git/config",
            "inside_dot_git": "docs/.git/config",
        }

        for name, target_path in cases.items():
            with self.subTest(name=name):
                result = build_patch_preview([PatchFileEdit(target_path, "content\n")])

                self.assertEqual(PATCH_PREVIEW_BLOCKED_UNSAFE_PATH, result.status)
                self.assertFalse(result.preview_ready)

    def test_delete_operation_is_rejected_in_step_21(self):
        result = build_patch_preview([PatchFileEdit(TARGET_PATH, "", CONTENT, operation="delete")])

        self.assertEqual(PATCH_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION, result.status)

    def test_oversized_file_content_blocks(self):
        result = build_patch_preview(
            [PatchFileEdit(TARGET_PATH, "x" * (MAX_PATCH_PREVIEW_FILE_BYTES + 1), operation="update")]
        )

        self.assertEqual(PATCH_PREVIEW_BLOCKED_OVERSIZED_CONTENT, result.status)

    def test_too_many_files_blocks(self):
        edits = [
            PatchFileEdit(f"docs/file-{index}.md", f"{index}\n")
            for index in range(MAX_PATCH_PREVIEW_FILES + 1)
        ]

        result = build_patch_preview(edits)

        self.assertEqual(PATCH_PREVIEW_BLOCKED_TOO_MANY_FILES, result.status)

    def test_diff_truncation_is_explicit_metadata(self):
        original = "".join(f"old {index}\n" for index in range(350))
        proposed = "".join(f"new {index}\n" for index in range(350))

        result = build_patch_preview([PatchFileEdit(TARGET_PATH, proposed, original)])

        self.assertEqual(PATCH_PREVIEW_READY, result.status)
        assert result.patch_preview is not None
        file_preview = result.patch_preview.files[0]
        self.assertTrue(file_preview.diff_truncated)
        self.assertIn(PATCH_RISK_DIFF_TRUNCATED, file_preview.risk_flags)
        self.assertIn(PATCH_RISK_DIFF_TRUNCATED, result.patch_preview.risk_flags)
        self.assertIn("truncated", file_preview.diff_preview)

    def test_risk_flags_are_metadata_only(self):
        result = build_patch_preview(
            [
                PatchFileEdit("runtime/example.py", "VALUE = 1\n", "VALUE = 0\n"),
                PatchFileEdit("tests/example_test.py", "assert True\n", ""),
                PatchFileEdit("docs/example.md", "# Docs\n", ""),
            ]
        )

        assert result.patch_preview is not None
        self.assertIn(PATCH_RISK_RUNTIME_TARGET, result.patch_preview.risk_flags)
        self.assertIn(PATCH_RISK_TEST_TARGET, result.patch_preview.risk_flags)
        self.assertIn(PATCH_RISK_DOCS_TARGET, result.patch_preview.risk_flags)
        self.assertFalse(result.can_write)
        self.assertFalse(result.patch_preview.can_write)
        self.assertFalse(result.write_authority_granted)

    def test_patch_preview_authority_fields_are_false(self):
        result = self.preview()

        for field_name in self.authority_fields():
            with self.subTest(field_name=field_name):
                self.assertIs(False, getattr(result, field_name))
                self.assertIs(False, result.to_dict()[field_name])
                self.assertIs(False, getattr(result.patch_preview, field_name))
                self.assertIs(False, result.patch_preview.to_dict()[field_name])

    def test_patch_preview_does_not_write_files(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            result = build_patch_preview(
                [PatchFileEdit(str(Path(workspace) / "not-written.txt"), "content\n")]
            )
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(PATCH_PREVIEW_BLOCKED_UNSAFE_PATH, result.status)
        self.assertEqual(before, after)

        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            result = build_patch_preview([PatchFileEdit("not-written.txt", "content\n")])
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(PATCH_PREVIEW_READY, result.status)
        self.assertEqual(before, after)

    def test_patch_preview_cannot_satisfy_control_write_gate_evidence(self):
        patch = self.preview()
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=UPDATED_CONTENT,
                workspace_root=workspace,
                gate_result=patch.to_dict(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_patch_preview_cannot_bypass_kill_switch_disabled_state(self):
        patch = self.preview()
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_DISABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=UPDATED_CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=patch.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_patch_preview_cannot_bypass_workspace_guard_failure(self):
        patch = build_patch_preview([PatchFileEdit("linked-parent/result.txt", UPDATED_CONTENT, CONTENT)])
        preview = self.artifact_preview(target_path="linked-parent/result.txt")

        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            link = Path(workspace) / "linked-parent"
            try:
                link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=UPDATED_CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=patch.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertFalse((Path(outside) / "result.txt").exists())

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_patch_preview_cannot_bypass_hash_mismatch(self):
        patch = self.preview()
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text="changed after patch preview\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=patch.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_static_no_new_capability_scan_includes_patch_preview_module(self):
        forbidden_import_prefixes = (
            "subprocess",
            "os",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "requests",
            "httpx",
            "git",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.genai",
            "ollama",
            "pip",
            "venv",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.providers.gateway",
            "runtime.execution",
        )
        forbidden_calls = {
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "os.popen",
            "Popen",
            "eval",
            "exec",
            "__import__",
            "importlib.import_module",
            "import_module",
            "open",
        }

        scan = scan_module(PATCH_PREVIEW_MODULE)

        self.assertEqual(
            [],
            [
                module_name
                for module_name in scan["imports"]
                if matches_any_prefix(module_name, forbidden_import_prefixes)
            ],
        )
        self.assertEqual(
            [],
            [call_name for call_name in scan["calls"] if call_name in forbidden_calls],
        )

    def preview(self):
        return build_patch_preview(
            [
                PatchFileEdit(
                    target_path=TARGET_PATH,
                    proposed_content=UPDATED_CONTENT,
                    original_content=CONTENT,
                    operation="update",
                )
            ]
        )

    def artifact_preview(self, *, target_path: str = TARGET_PATH):
        return build_artifact_preview(
            ArtifactPreviewRequest(
                target_path=target_path,
                proposed_content=UPDATED_CONTENT,
                original_content=CONTENT,
                artifact_kind="text",
                provider_output_trust="untrusted",
            )
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-diff-based-patch-preview",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-diff-based-patch-preview",
            reason="reviewed exact patch preview fixture",
        )
        bridge = build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )
        with TemporaryDirectory() as audit_dir:
            handoff = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(audit_dir),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
            )
        return evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=bridge.approval_decision,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="diff-based-patch-preview-run",
            sandbox_request_id="diff-based-patch-preview-sandbox-request",
            sandbox_result_id="diff-based-patch-preview-sandbox-result",
            requested_by="human-reviewer-diff-based-patch-preview",
            dry_run_trace_id="diff-based-patch-preview-dry-run",
            sandbox_policy_decision_id="diff-based-patch-preview-policy",
        )

    @staticmethod
    def authority_fields() -> tuple[str, ...]:
        return (
            "can_approve",
            "can_write",
            "can_execute",
            "can_commit",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "write_authority_granted",
            "execution_authority_granted",
            "provider_authority_granted",
        )

    @staticmethod
    def write_switch(switch_dir: str, value: str) -> Path:
        switch_path = Path(switch_dir) / "write_kill_switch.state"
        switch_path.write_text(value, encoding="utf-8")
        return switch_path


def scan_module(path: Path) -> dict[str, tuple[str, ...]]:
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
                full_name = f"{node.module}.{alias.name}"
                imports.append(full_name)
                aliases[alias.asname or alias.name] = full_name
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.append(name)

    return {"imports": tuple(imports), "calls": tuple(calls)}


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if not parts:
            return ""
        root = aliases.get(parts[0], parts[0])
        return ".".join((root, *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


def matches_any_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in prefixes
    )


if __name__ == "__main__":
    unittest.main()
