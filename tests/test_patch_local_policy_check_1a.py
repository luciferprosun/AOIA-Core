from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
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
from runtime.patches.patch_policy import (
    PATCH_POLICY_BLOCK,
    PATCH_POLICY_BLOCKED_DUPLICATE_TARGET,
    PATCH_POLICY_BLOCKED_MALFORMED_PREVIEW,
    PATCH_POLICY_BLOCKED_MISSING_PREVIEW,
    PATCH_POLICY_BLOCKED_PREVIEW_AUTHORITY,
    PATCH_POLICY_BLOCKED_PREVIEW_NOT_READY,
    PATCH_POLICY_BLOCKED_SECRET_TARGET,
    PATCH_POLICY_BLOCKED_UNSAFE_TARGET,
    PATCH_POLICY_FINDING_AUTHORITY_TEXT,
    PATCH_POLICY_FINDING_BOUNDARY_TARGET,
    PATCH_POLICY_FINDING_CAPABILITY_TEXT,
    PATCH_POLICY_FINDING_LARGE_PATCH,
    PATCH_POLICY_FINDING_MULTI_FILE,
    PATCH_POLICY_NEEDS_REVIEW,
    PATCH_POLICY_PASS,
    PATCH_POLICY_RISK_CAPABILITY_TEXT,
    PATCH_POLICY_RISK_DOCS_CHANGE,
    PATCH_POLICY_RISK_RUNTIME_CHANGE,
    PATCH_POLICY_RISK_TEST_CHANGE,
    PatchPolicyCheckResult,
    canonical_patch_policy_json,
    check_patch_local_policy,
    compute_patch_policy_hash,
)
from runtime.patches.patch_preview import PatchFileEdit, PatchPreview, build_patch_preview
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_POLICY_MODULE = REPO_ROOT / "runtime" / "patches" / "patch_policy.py"
CONTENT = "# Patch policy fixture\n"
UPDATED_CONTENT = "# Patch policy fixture\n\nUpdated.\n"
TARGET_PATH = "docs/patch-policy.md"
PACKET_HASH = "a" * 64
ARTIFACT_HASH = hashlib.sha256(UPDATED_CONTENT.encode("utf-8")).hexdigest()


class PatchLocalPolicyCheck1ATests(unittest.TestCase):
    def test_valid_patch_preview_produces_policy_result(self):
        result = check_patch_local_policy(self.preview().patch_preview)

        self.assertIsInstance(result, PatchPolicyCheckResult)
        self.assertEqual(PATCH_POLICY_PASS, result.status)
        self.assertEqual(self.preview().preview_hash, result.patch_preview_hash)
        self.assertEqual(("docs/patch-policy.md",), result.target_paths)
        self.assertEqual(1, result.file_count)

    def test_patch_preview_result_input_is_accepted(self):
        result = check_patch_local_policy(self.preview())

        self.assertEqual(PATCH_POLICY_PASS, result.status)
        self.assertEqual("docs", result.scope_classification)

    def test_policy_hash_is_deterministic(self):
        first = check_patch_local_policy(self.preview())
        second = check_patch_local_policy(self.preview())

        self.assertEqual(first.policy_hash, second.policy_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_canonical_policy_json_is_deterministic_independent_of_dict_order(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}

        self.assertEqual(canonical_patch_policy_json(left), canonical_patch_policy_json(right))
        self.assertEqual(compute_patch_policy_hash(left), compute_patch_policy_hash(right))

    def test_policy_hash_changes_when_patch_preview_hash_changes(self):
        preview = self.preview().patch_preview
        changed = replace(preview, preview_hash="b" * 64)

        first = check_patch_local_policy(preview)
        second = check_patch_local_policy(changed)

        self.assertNotEqual(first.policy_hash, second.policy_hash)

    def test_policy_hash_changes_when_findings_change(self):
        docs = check_patch_local_policy(self.preview())
        boundary = check_patch_local_policy(
            build_patch_preview(
                [PatchFileEdit("runtime/control_write.py", "VALUE = 1\n", "VALUE = 0\n")]
            )
        )

        self.assertNotEqual(docs.policy_hash, boundary.policy_hash)
        self.assertNotEqual(docs.findings, boundary.findings)

    def test_missing_malformed_and_not_ready_patch_preview_blocks(self):
        cases = {
            "missing": (None, PATCH_POLICY_BLOCKED_MISSING_PREVIEW),
            "malformed": (object(), PATCH_POLICY_BLOCKED_MALFORMED_PREVIEW),
            "not_ready": (replace(self.preview().patch_preview, status="PATCH_PREVIEW_BLOCKED"), PATCH_POLICY_BLOCKED_PREVIEW_NOT_READY),
        }

        for name, (value, reason_code) in cases.items():
            with self.subTest(name=name):
                result = check_patch_local_policy(value)

                self.assertEqual(PATCH_POLICY_BLOCK, result.status)
                self.assertIn(reason_code, result.reason_codes)

    def test_patch_preview_authority_like_fields_true_blocks(self):
        preview = self.preview().patch_preview
        object.__setattr__(preview, "can_write", True)

        result = check_patch_local_policy(preview)

        self.assertEqual(PATCH_POLICY_BLOCK, result.status)
        self.assertIn(PATCH_POLICY_BLOCKED_PREVIEW_AUTHORITY, result.reason_codes)

    def test_unsafe_target_metadata_blocks(self):
        cases = {
            "dot_git": ".git/config",
            "absolute": "/tmp/escape.txt",
            "traversal": "../escape.txt",
            "null_byte": "bad\x00path.txt",
        }

        for name, target_path in cases.items():
            with self.subTest(name=name):
                result = check_patch_local_policy(self.forged_preview_with_targets((target_path,)))

                self.assertEqual(PATCH_POLICY_BLOCK, result.status)
                self.assertIn(PATCH_POLICY_BLOCKED_UNSAFE_TARGET, result.reason_codes)

    def test_duplicate_target_metadata_blocks(self):
        result = check_patch_local_policy(self.forged_preview_with_targets(("docs/a.md", "docs/a.md")))

        self.assertEqual(PATCH_POLICY_BLOCK, result.status)
        self.assertIn(PATCH_POLICY_BLOCKED_DUPLICATE_TARGET, result.reason_codes)

    def test_secrets_like_file_target_blocks(self):
        result = check_patch_local_policy(build_patch_preview([PatchFileEdit(".env", "TOKEN=value\n", "")]))

        self.assertEqual(PATCH_POLICY_BLOCK, result.status)
        self.assertIn(PATCH_POLICY_BLOCKED_SECRET_TARGET, result.reason_codes)

    def test_scope_classification_runtime_tests_docs_and_mixed(self):
        cases = {
            "runtime": (build_patch_preview([PatchFileEdit("runtime/example.py", "x = 1\n", "x = 0\n")]), "runtime"),
            "tests": (build_patch_preview([PatchFileEdit("tests/example_test.py", "assert True\n", "")]), "tests"),
            "docs": (build_patch_preview([PatchFileEdit("docs/example.md", "Docs\n", "")]), "docs"),
            "mixed": (
                build_patch_preview(
                    [
                        PatchFileEdit("runtime/example.py", "x = 1\n", "x = 0\n"),
                        PatchFileEdit("tests/example_test.py", "assert True\n", ""),
                    ]
                ),
                "mixed",
            ),
        }

        for name, (preview, expected_scope) in cases.items():
            with self.subTest(name=name):
                result = check_patch_local_policy(preview)

                self.assertEqual(expected_scope, result.scope_classification)

    def test_high_risk_boundary_module_target_needs_review(self):
        result = check_patch_local_policy(
            build_patch_preview(
                [PatchFileEdit("runtime/control_write.py", "VALUE = 1\n", "VALUE = 0\n")]
            )
        )

        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, result.status)
        self.assertIn(PATCH_POLICY_FINDING_BOUNDARY_TARGET, result.reason_codes)

    def test_multi_file_large_and_scope_risk_flags_are_set(self):
        large = "x" * 120_000
        result = check_patch_local_policy(
            build_patch_preview(
                [
                    PatchFileEdit("runtime/example.py", large, "old\n"),
                    PatchFileEdit("tests/example_test.py", "assert True\n", ""),
                ]
            )
        )

        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, result.status)
        self.assertIn(PATCH_POLICY_FINDING_MULTI_FILE, result.reason_codes)
        self.assertIn(PATCH_POLICY_FINDING_LARGE_PATCH, result.reason_codes)
        self.assertIn(PATCH_POLICY_RISK_RUNTIME_CHANGE, result.risk_flags)
        self.assertIn(PATCH_POLICY_RISK_TEST_CHANGE, result.risk_flags)

    def test_docs_target_risk_flag_is_metadata_only(self):
        result = check_patch_local_policy(self.preview())

        self.assertEqual(PATCH_POLICY_PASS, result.status)
        self.assertIn(PATCH_POLICY_RISK_DOCS_CHANGE, result.risk_flags)
        self.assertFalse(result.can_write)

    def test_authority_like_text_in_proposed_content_is_flagged(self):
        result = check_patch_local_policy(
            build_patch_preview(
                [PatchFileEdit("docs/authority.md", "can_write=True\nmetadata_authority=True\n", "old\n")]
            )
        )

        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, result.status)
        self.assertIn(PATCH_POLICY_FINDING_AUTHORITY_TEXT, result.reason_codes)

    def test_risky_import_capability_text_in_proposed_content_is_flagged(self):
        result = check_patch_local_policy(
            build_patch_preview(
                [PatchFileEdit("docs/capability.md", "subprocess.run(['x'])\npip install thing\n", "old\n")]
            )
        )

        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, result.status)
        self.assertIn(PATCH_POLICY_FINDING_CAPABILITY_TEXT, result.reason_codes)
        self.assertIn(PATCH_POLICY_RISK_CAPABILITY_TEXT, result.risk_flags)

    def test_pass_policy_result_cannot_satisfy_control_write_gate_evidence(self):
        policy = check_patch_local_policy(self.preview())
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=UPDATED_CONTENT,
                workspace_root=workspace,
                gate_result=policy.to_dict(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_pass_policy_result_cannot_bypass_kill_switch_disabled_state(self):
        policy = check_patch_local_policy(self.preview())
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
                metadata=policy.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_pass_policy_result_cannot_bypass_workspace_guard_failure(self):
        policy = check_patch_local_policy(build_patch_preview([PatchFileEdit("linked-parent/result.txt", UPDATED_CONTENT, CONTENT)]))
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
                metadata=policy.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertFalse((Path(outside) / "result.txt").exists())

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_pass_policy_result_cannot_bypass_hash_mismatch(self):
        policy = check_patch_local_policy(self.preview())
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text="changed after policy\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=policy.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_policy_result_authority_fields_are_false(self):
        result = check_patch_local_policy(self.preview())

        for field_name in self.authority_fields():
            with self.subTest(field_name=field_name):
                self.assertIs(False, getattr(result, field_name))
                self.assertIs(False, result.to_dict()[field_name])

    def test_policy_result_has_no_gate_shape_or_apply_method(self):
        result = check_patch_local_policy(self.preview())
        data = result.to_dict()

        for key in ("decision", "packet_hash", "artifact_hash", "gate_result"):
            self.assertNotIn(key, data)
        for name in ("apply", "write", "execute", "dispatch", "approve", "call_provider"):
            self.assertFalse(hasattr(result, name))

    def test_static_no_new_capability_scan_includes_patch_policy_module(self):
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

        scan = scan_module(PATCH_POLICY_MODULE)

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
                )
            ]
        )

    def forged_preview_with_targets(self, target_paths: tuple[str, ...]) -> PatchPreview:
        base = self.preview().patch_preview
        assert base is not None
        files = tuple(
            replace(base.files[0], target_path=target_path)
            for target_path in target_paths
        )
        return replace(
            base,
            target_paths=target_paths,
            files=files,
            total_file_count=len(files),
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
            packet_id="packet-patch-local-policy",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-patch-local-policy",
            reason="reviewed exact patch local policy fixture",
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
            run_id="patch-local-policy-run",
            sandbox_request_id="patch-local-policy-sandbox-request",
            sandbox_result_id="patch-local-policy-sandbox-result",
            requested_by="human-reviewer-patch-local-policy",
            dry_run_trace_id="patch-local-policy-dry-run",
            sandbox_policy_decision_id="patch-local-policy-policy",
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
