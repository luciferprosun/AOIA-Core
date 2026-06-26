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
from runtime.patches.patch_barrier import (
    PATCH_BARRIER_APPROVED,
    PATCH_BARRIER_BLOCKED,
    PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM,
    PATCH_BARRIER_BLOCKED_HASH_MISMATCH,
    PATCH_BARRIER_BLOCKED_MISSING_DECISION,
    PATCH_BARRIER_BLOCKED_MISSING_DECISION_ID,
    PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH,
    PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH,
    PATCH_BARRIER_BLOCKED_PATCH_POLICY_HASH_MISMATCH,
    PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH,
    PATCH_BARRIER_BLOCKED_POLICY_BLOCK_APPROVE,
    PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH,
    PATCH_BARRIER_BLOCKED_UNKNOWN_DECISION,
    PATCH_BARRIER_REJECTED,
    PATCH_BARRIER_RISK_NEEDS_REVIEW_HUMAN_OVERRIDE,
    PATCH_BARRIER_RISK_POLICY_BLOCK_REJECTION_RECORD,
    PATCH_BARRIER_VERIFIED,
    PATCH_DECISION_APPROVE,
    PATCH_DECISION_REJECT,
    HumanPatchBarrierResult,
    canonical_patch_barrier_json,
    compute_patch_barrier_hash,
    create_human_patch_barrier,
    verify_human_patch_barrier,
)
from runtime.patches.patch_policy import PATCH_POLICY_BLOCK, PATCH_POLICY_NEEDS_REVIEW, PATCH_POLICY_PASS, check_patch_local_policy
from runtime.patches.patch_preview import PatchFileEdit, build_patch_preview
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_BARRIER_MODULE = REPO_ROOT / "runtime" / "patches" / "patch_barrier.py"
CONTENT = "# Human patch barrier fixture\n"
UPDATED_CONTENT = "# Human patch barrier fixture\n\nUpdated.\n"
TARGET_PATH = "docs/human-patch-barrier.md"
PACKET_HASH = "a" * 64
ARTIFACT_HASH = hashlib.sha256(UPDATED_CONTENT.encode("utf-8")).hexdigest()


class HumanPatchBarrier1ATests(unittest.TestCase):
    def test_approve_decision_creates_hash_bound_patch_barrier_for_pass_policy(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)

        self.assertIsInstance(barrier, HumanPatchBarrierResult)
        self.assertEqual(PATCH_BARRIER_APPROVED, barrier.status)
        self.assertTrue(barrier.barrier_valid)
        self.assertTrue(barrier.patch_approved)
        self.assertFalse(barrier.patch_applied)
        self.assertEqual(self.preview().preview_hash, barrier.patch_preview_hash)
        self.assertEqual(self.policy().policy_hash, barrier.patch_policy_hash)
        self.assertEqual((TARGET_PATH,), barrier.target_paths)

    def test_reject_decision_creates_rejection_barrier(self):
        barrier = self.barrier(PATCH_DECISION_REJECT, reason="not desired")

        self.assertEqual(PATCH_BARRIER_REJECTED, barrier.status)
        self.assertTrue(barrier.barrier_valid)
        self.assertTrue(barrier.patch_rejected)
        self.assertFalse(barrier.patch_approved)

    def test_missing_and_unknown_decisions_block(self):
        cases = {
            "missing": (None, PATCH_BARRIER_BLOCKED_MISSING_DECISION),
            "unknown": ("MAYBE", PATCH_BARRIER_BLOCKED_UNKNOWN_DECISION),
            "ambiguous": ("YES", PATCH_BARRIER_BLOCKED_MISSING_DECISION),
        }

        for name, (decision, reason_code) in cases.items():
            with self.subTest(name=name):
                barrier = self.barrier(decision)

                self.assertEqual(PATCH_BARRIER_BLOCKED, barrier.status)
                self.assertFalse(barrier.barrier_valid)
                self.assertEqual(reason_code, barrier.reason_code)

    def test_missing_decision_id_blocks(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE, decision_id=None)

        self.assertEqual(PATCH_BARRIER_BLOCKED, barrier.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_MISSING_DECISION_ID, barrier.reason_code)

    def test_missing_patch_preview_hash_blocks(self):
        preview = replace(self.preview(), preview_hash="not-a-hash")
        barrier = self.barrier(PATCH_DECISION_APPROVE, preview=preview)

        self.assertEqual(PATCH_BARRIER_BLOCKED, barrier.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH, barrier.reason_code)

    def test_missing_patch_policy_hash_blocks(self):
        policy = replace(self.policy(), policy_hash="not-a-hash")
        barrier = self.barrier(PATCH_DECISION_APPROVE, policy=policy)

        self.assertEqual(PATCH_BARRIER_BLOCKED, barrier.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH, barrier.reason_code)

    def test_missing_patch_policy_preview_hash_blocks(self):
        policy = replace(self.policy(), patch_preview_hash=None)
        barrier = self.barrier(PATCH_DECISION_APPROVE, policy=policy)

        self.assertEqual(PATCH_BARRIER_BLOCKED, barrier.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH, barrier.reason_code)

    def test_patch_preview_hash_mismatch_blocks_verification(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        verified = verify_human_patch_barrier(barrier, expected_patch_preview_hash="b" * 64)

        self.assertEqual(PATCH_BARRIER_BLOCKED, verified.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH, verified.reason_code)

    def test_patch_policy_hash_mismatch_blocks_verification(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        verified = verify_human_patch_barrier(barrier, expected_patch_policy_hash="c" * 64)

        self.assertEqual(PATCH_BARRIER_BLOCKED, verified.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_PATCH_POLICY_HASH_MISMATCH, verified.reason_code)

    def test_approval_for_patch_a_fails_for_patch_b(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        other_preview = self.preview_for("docs/other.md", "# Other\n", "# Old\n")
        verified = verify_human_patch_barrier(barrier, expected_patch_preview_hash=other_preview.preview_hash)

        self.assertEqual(PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH, verified.reason_code)

    def test_approval_for_policy_a_fails_for_policy_b(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        other_policy = self.policy_for("docs/other.md", "# Other\n", "# Old\n")
        verified = verify_human_patch_barrier(barrier, expected_patch_policy_hash=other_policy.policy_hash)

        self.assertEqual(PATCH_BARRIER_BLOCKED_PATCH_POLICY_HASH_MISMATCH, verified.reason_code)

    def test_target_binding_mismatch_blocks_verification(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        verified = verify_human_patch_barrier(barrier, expected_target_paths=("docs/other.md",))

        self.assertEqual(PATCH_BARRIER_BLOCKED, verified.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH, verified.reason_code)

    def test_policy_block_approve_blocks_and_reject_records_safe_rejection(self):
        preview = self.preview_for(".env", "TOKEN=value\n", "")
        policy = check_patch_local_policy(preview)
        self.assertEqual(PATCH_POLICY_BLOCK, policy.status)

        approve = self.barrier(PATCH_DECISION_APPROVE, preview=preview, policy=policy)
        reject = self.barrier(PATCH_DECISION_REJECT, preview=preview, policy=policy)

        self.assertEqual(PATCH_BARRIER_BLOCKED, approve.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_POLICY_BLOCK_APPROVE, approve.reason_code)
        self.assertEqual(PATCH_BARRIER_REJECTED, reject.status)
        self.assertIn(PATCH_BARRIER_RISK_POLICY_BLOCK_REJECTION_RECORD, reject.risk_flags)
        self.assertFalse(reject.patch_applied)

    def test_needs_review_approve_behavior_is_explicit_and_risk_marked(self):
        preview = self.preview_for("runtime/control_write.py", "VALUE = 1\n", "VALUE = 0\n")
        policy = check_patch_local_policy(preview)
        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, policy.status)

        barrier = self.barrier(PATCH_DECISION_APPROVE, preview=preview, policy=policy)

        self.assertEqual(PATCH_BARRIER_APPROVED, barrier.status)
        self.assertIn(PATCH_BARRIER_RISK_NEEDS_REVIEW_HUMAN_OVERRIDE, barrier.risk_flags)
        self.assertFalse(barrier.can_write)

    def test_barrier_hash_is_deterministic(self):
        first = self.barrier(PATCH_DECISION_APPROVE)
        second = self.barrier(PATCH_DECISION_APPROVE)

        self.assertEqual(first.barrier_hash, second.barrier_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_canonical_barrier_json_is_deterministic_independent_of_dict_order(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}

        self.assertEqual(canonical_patch_barrier_json(left), canonical_patch_barrier_json(right))
        self.assertEqual(compute_patch_barrier_hash(left), compute_patch_barrier_hash(right))

    def test_meaningful_changes_change_barrier_hash(self):
        base = self.barrier(PATCH_DECISION_APPROVE)
        changed_decision = self.barrier(PATCH_DECISION_REJECT)
        changed_preview = self.barrier(
            PATCH_DECISION_APPROVE,
            preview=self.preview_for("docs/other.md", "# Other\n", "# Old\n"),
            policy=self.policy_for("docs/other.md", "# Other\n", "# Old\n"),
        )
        changed_policy = self.barrier(
            PATCH_DECISION_APPROVE,
            preview=self.preview_for("runtime/control_write.py", "VALUE = 1\n", "VALUE = 0\n"),
            policy=self.policy_for("runtime/control_write.py", "VALUE = 1\n", "VALUE = 0\n"),
        )

        self.assertNotEqual(base.barrier_hash, changed_decision.barrier_hash)
        self.assertNotEqual(base.barrier_hash, changed_preview.barrier_hash)
        self.assertNotEqual(base.barrier_hash, changed_policy.barrier_hash)

    def test_changed_reason_and_target_binding_are_detected_by_verification(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE, reason="looks good")
        changed_reason = replace(barrier.decision, reason="changed")
        changed_target = replace(barrier.decision, target_paths=("docs/other.md",))

        reason_result = verify_human_patch_barrier(changed_reason)
        target_result = verify_human_patch_barrier(changed_target)

        self.assertEqual(PATCH_BARRIER_BLOCKED_HASH_MISMATCH, reason_result.reason_code)
        self.assertEqual(PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH, target_result.reason_code)

    def test_changed_decision_is_detected_by_verification(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        changed = replace(barrier.decision, decision_value=PATCH_DECISION_REJECT)

        verified = verify_human_patch_barrier(changed)

        self.assertEqual(PATCH_BARRIER_BLOCKED, verified.status)
        self.assertEqual(PATCH_BARRIER_BLOCKED_HASH_MISMATCH, verified.reason_code)

    def test_verify_valid_barrier_as_dict(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)

        verified = verify_human_patch_barrier(
            barrier.to_dict(),
            expected_patch_preview_hash=barrier.patch_preview_hash,
            expected_patch_policy_hash=barrier.patch_policy_hash,
            expected_target_paths=barrier.target_paths,
            expected_policy_status=PATCH_POLICY_PASS,
        )

        self.assertEqual(PATCH_BARRIER_VERIFIED, verified.status)
        self.assertTrue(verified.barrier_valid)
        self.assertTrue(verified.patch_approved)

    def test_authority_like_fields_true_block_verification(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        forged = barrier.decision
        object.__setattr__(forged, "can_write", True)
        forged_result = self.barrier(PATCH_DECISION_APPROVE)
        object.__setattr__(forged_result, "can_write", True)
        forged_dict = self.barrier(PATCH_DECISION_APPROVE).to_dict()
        forged_dict["can_write"] = True

        for item in (forged, forged_result, forged_dict):
            with self.subTest(item=type(item).__name__):
                verified = verify_human_patch_barrier(item)

                self.assertEqual(PATCH_BARRIER_BLOCKED, verified.status)
                self.assertEqual(PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM, verified.reason_code)

    def test_barrier_authority_fields_are_false(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)

        for item in (barrier, barrier.decision):
            for field_name in self.authority_fields():
                with self.subTest(item=type(item).__name__, field_name=field_name):
                    self.assertIs(False, getattr(item, field_name))
                    self.assertIs(False, item.to_dict()[field_name])
        self.assertFalse(barrier.patch_applied)
        self.assertFalse(barrier.file_written)
        self.assertFalse(barrier.provider_called)
        self.assertFalse(barrier.action_dispatched)

    def test_approve_barrier_cannot_satisfy_control_write_gate_evidence_by_itself(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=UPDATED_CONTENT,
                workspace_root=workspace,
                gate_result=barrier.to_dict(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_approve_barrier_cannot_bypass_kill_switch_disabled_state(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
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
                metadata=barrier.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_approve_barrier_cannot_bypass_workspace_guard_failure(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
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
                metadata=barrier.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertFalse((Path(outside) / "result.txt").exists())

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_approve_barrier_cannot_bypass_hash_mismatch(self):
        barrier = self.barrier(PATCH_DECISION_APPROVE)
        preview = self.artifact_preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text="changed after barrier\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=barrier.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_patch_barrier_does_not_write_files_or_apply_patch(self):
        with TemporaryDirectory() as workspace:
            target = Path(workspace) / TARGET_PATH
            barrier = self.barrier(PATCH_DECISION_APPROVE)

            self.assertFalse(target.exists())
            self.assertFalse(hasattr(barrier, "apply"))
            self.assertFalse(hasattr(barrier, "write"))
            self.assertFalse(hasattr(barrier, "execute"))
            self.assertFalse(hasattr(barrier, "dispatch"))
            self.assertFalse(hasattr(barrier, "call_provider"))

    def test_static_no_new_capability_scan_includes_patch_barrier_module(self):
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

        scan = scan_module(PATCH_BARRIER_MODULE)

        self.assertEqual(
            [],
            [
                module_name
                for module_name in scan["imports"]
                if matches_any_prefix(module_name, forbidden_import_prefixes)
            ],
        )
        self.assertEqual([], [call_name for call_name in scan["calls"] if call_name in forbidden_calls])

    def preview(self):
        result = build_patch_preview(
            [
                PatchFileEdit(
                    target_path=TARGET_PATH,
                    proposed_content=UPDATED_CONTENT,
                    original_content=CONTENT,
                )
            ]
        )
        assert result.patch_preview is not None
        return result.patch_preview

    def policy(self):
        policy = check_patch_local_policy(self.preview())
        self.assertEqual(PATCH_POLICY_PASS, policy.status)
        return policy

    def preview_for(self, target_path: str, proposed: str, original: str):
        result = build_patch_preview([PatchFileEdit(target_path, proposed, original)])
        assert result.patch_preview is not None
        return result.patch_preview

    def policy_for(self, target_path: str, proposed: str, original: str):
        return check_patch_local_policy(self.preview_for(target_path, proposed, original))

    def barrier(self, decision_value, *, preview=None, policy=None, decision_id="patch-decision-1", reason=None):
        patch_preview = self.preview() if preview is None else preview
        patch_policy = self.policy() if policy is None else policy
        return create_human_patch_barrier(
            decision_value=decision_value,
            patch_preview=patch_preview,
            patch_policy=patch_policy,
            decision_id=decision_id,
            reviewer_id="local-operator",
            created_at="2026-06-26T16:39:00Z",
            reason=reason,
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
            packet_id="packet-step23",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="reviewer-step23",
            reason="reviewed exact human patch barrier fixture",
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

    def context(self):
        return ControlWriteContext(
            run_id="human-patch-barrier-run",
            sandbox_request_id="human-patch-barrier-sandbox-request",
            sandbox_result_id="human-patch-barrier-sandbox-result",
            requested_by="reviewer-step23",
            dry_run_trace_id="human-patch-barrier-dry-run",
            sandbox_policy_decision_id="human-patch-barrier-policy",
        )

    def write_switch(self, switch_dir: str, value: str):
        path = Path(switch_dir) / "write-switch.txt"
        path.write_text(value, encoding="utf-8")
        return path

    def authority_fields(self):
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


def scan_module(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Call):
            calls.append(call_name(node.func))
    return {"imports": imports, "calls": calls}


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def matches_any_prefix(module_name: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in forbidden_prefixes)


if __name__ == "__main__":
    unittest.main()
