from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from runtime.artifact_preview import ArtifactPreviewStatus
from runtime.bridges.proposal_to_preview import (
    PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET,
    PROPOSAL_PREVIEW_BLOCKED_TARGET_MISMATCH,
    PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET,
    PROPOSAL_PREVIEW_BLOCKED_UNSUPPORTED_KIND,
    PROPOSAL_PREVIEW_READY,
    build_preview_from_action_proposal,
)
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
from runtime.human_decision_gated_artifact_write import BLOCKED_WRITE_KILL_SWITCH
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalSourceTrust,
    ActionProposalStatus,
    build_action_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_MODULE = REPO_ROOT / "runtime" / "bridges" / "proposal_to_preview.py"
PACKET_HASH = "a" * 64
CONTENT = "# Proposal to preview bridge fixture\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
TARGET_PATH = "reports/proposal-preview.txt"


class ProposalToPreviewBridge1ATests(unittest.TestCase):
    def test_valid_file_write_action_proposal_produces_artifact_preview(self):
        proposal = self.file_write_proposal()

        result = build_preview_from_action_proposal(
            proposal=proposal,
            proposed_content_text=CONTENT,
            original_content_text="",
            expected_target_path=TARGET_PATH,
        )

        self.assertEqual(PROPOSAL_PREVIEW_READY, result.status)
        self.assertTrue(result.preview_ready)
        self.assertIsNotNone(result.artifact_preview)
        assert result.artifact_preview is not None
        self.assertEqual(ArtifactPreviewStatus.PREVIEW_READY, result.artifact_preview.status)
        self.assertEqual(TARGET_PATH, result.artifact_preview.target_path)
        self.assertEqual(ARTIFACT_HASH, result.artifact_preview.proposed_sha256)
        self.assertFalse(result.artifact_preview.write_performed)
        self.assertFalse(result.artifact_preview.can_write)

    def test_bridge_result_contains_inert_proposal_and_preview_binding_metadata(self):
        proposal = self.file_write_proposal(source_trust=ActionProposalSourceTrust.PROVIDER_UNTRUSTED)
        result = build_preview_from_action_proposal(
            proposal=proposal,
            proposed_content_text=CONTENT,
            expected_target_path=TARGET_PATH,
        )

        self.assertEqual(proposal.proposal_id, result.proposal_id)
        self.assertEqual(proposal.proposal_hash, result.proposal_hash)
        self.assertEqual(ActionProposalKind.FILE_WRITE.value, result.proposal_kind)
        self.assertEqual(ActionProposalSourceTrust.PROVIDER_UNTRUSTED.value, result.proposal_source_trust)
        self.assertEqual(TARGET_PATH, result.target_path)
        self.assertEqual(ARTIFACT_HASH, result.preview_proposed_hash)
        self.assertIsNotNone(result.preview_id)
        self.assertEqual(proposal.proposal_id, result.binding_metadata["proposal_id"])
        self.assertEqual(proposal.proposal_hash, result.binding_metadata["proposal_hash"])
        self.assertEqual(result.preview_id, result.binding_metadata["preview_id"])
        self.assertEqual(ARTIFACT_HASH, result.binding_metadata["preview_proposed_hash"])

    def test_bridge_result_authority_fields_are_false(self):
        result = build_preview_from_action_proposal(
            proposal=self.file_write_proposal(),
            proposed_content_text=CONTENT,
        )

        for field_name in self.authority_fields():
            with self.subTest(field_name=field_name):
                self.assertIs(False, getattr(result, field_name))
                self.assertIs(False, result.to_dict()[field_name])

    def test_non_file_action_kinds_are_rejected(self):
        cases = (
            ActionProposalKind.TEST_RUN,
            ActionProposalKind.SHELL_COMMAND,
            ActionProposalKind.GIT_COMMIT,
            ActionProposalKind.GIT_PUSH,
            ActionProposalKind.PACKAGE_INSTALL,
            ActionProposalKind.PROVIDER_CALL,
            ActionProposalKind.BROWSER_ACTION,
            "made_up_action_kind",
        )

        for action_kind in cases:
            with self.subTest(action_kind=action_kind):
                proposal = build_action_proposal(
                    ActionProposalRequest(
                        action_kind=action_kind,
                        target_refs=(TARGET_PATH,),
                        arguments={"content": CONTENT},
                        source_trust=ActionProposalSourceTrust.USER_SUPPLIED,
                    )
                )

                result = build_preview_from_action_proposal(
                    proposal=proposal,
                    proposed_content_text=CONTENT,
                )

                self.assertEqual(PROPOSAL_PREVIEW_BLOCKED_UNSUPPORTED_KIND, result.status)
                self.assertFalse(result.preview_ready)
                self.assertIsNone(result.artifact_preview)

    def test_missing_target_reference_is_rejected(self):
        proposal = self.file_write_proposal(target_refs=())

        result = build_preview_from_action_proposal(
            proposal=proposal,
            proposed_content_text=CONTENT,
        )

        self.assertEqual(PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET, result.status)
        self.assertFalse(result.preview_ready)

    def test_multiple_target_references_are_rejected_as_unsupported_conflict(self):
        proposal = self.file_write_proposal(target_refs=(TARGET_PATH, "reports/other.txt"))

        result = build_preview_from_action_proposal(
            proposal=proposal,
            proposed_content_text=CONTENT,
        )

        self.assertEqual(PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET, result.status)
        self.assertFalse(result.preview_ready)

    def test_target_mismatch_is_rejected(self):
        result = build_preview_from_action_proposal(
            proposal=self.file_write_proposal(),
            proposed_content_text=CONTENT,
            expected_target_path="reports/different.txt",
        )

        self.assertEqual(PROPOSAL_PREVIEW_BLOCKED_TARGET_MISMATCH, result.status)
        self.assertFalse(result.preview_ready)

    def test_unsafe_targets_are_rejected(self):
        cases = {
            "absolute_target": "/absolute/path.txt",
            "parent_traversal": "../escape.txt",
            "nested_parent_traversal": "docs/../../escape.txt",
            "backslash_traversal": "..\\escape.txt",
            "null_byte": "bad\x00path.txt",
            "empty_path": "",
            "dot_git_target": ".git/config",
            "inside_dot_git": "docs/.git/config",
        }

        for name, target_path in cases.items():
            with self.subTest(name=name):
                proposal = replace(
                    self.file_write_proposal(),
                    status=ActionProposalStatus.PROPOSAL_READY,
                    target_refs=(target_path,),
                )

                result = build_preview_from_action_proposal(
                    proposal=proposal,
                    proposed_content_text=CONTENT,
                )

                self.assertEqual(PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET, result.status)
                self.assertFalse(result.preview_ready)
                self.assertIsNone(result.artifact_preview)

    def test_invalid_file_write_proposal_from_schema_is_rejected_fail_closed(self):
        invalid = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=("../escape.txt",),
                arguments={"content": CONTENT},
            )
        )

        result = build_preview_from_action_proposal(
            proposal=invalid,
            proposed_content_text=CONTENT,
        )

        self.assertNotEqual(PROPOSAL_PREVIEW_READY, result.status)
        self.assertFalse(result.preview_ready)

    def test_source_trust_remains_non_authoritative(self):
        cases = (
            ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
            ActionProposalSourceTrust.CRITIC_METADATA,
            ActionProposalSourceTrust.SYSTEM_METADATA,
            ActionProposalSourceTrust.USER_SUPPLIED,
        )

        for source_trust in cases:
            with self.subTest(source_trust=source_trust):
                proposal = self.file_write_proposal(source_trust=source_trust)
                result = build_preview_from_action_proposal(
                    proposal=proposal,
                    proposed_content_text=CONTENT,
                )

                self.assertEqual(source_trust.value, result.proposal_source_trust)
                self.assertTrue(proposal.human_review_required)
                self.assertFalse(result.can_write)
                self.assertFalse(result.write_authority_granted)
                self.assertFalse(result.can_change_gate)
                if source_trust is ActionProposalSourceTrust.PROVIDER_UNTRUSTED:
                    assert result.artifact_preview is not None
                    self.assertTrue(result.artifact_preview.human_review_required)

    def test_bridge_output_cannot_satisfy_control_write_gate_evidence(self):
        bridge = build_preview_from_action_proposal(
            proposal=self.file_write_proposal(),
            proposed_content_text=CONTENT,
        )
        assert bridge.artifact_preview is not None

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=bridge.artifact_preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=bridge.to_dict(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_bridge_output_cannot_bypass_kill_switch_disabled_state(self):
        bridge = build_preview_from_action_proposal(
            proposal=self.file_write_proposal(),
            proposed_content_text=CONTENT,
        )
        assert bridge.artifact_preview is not None

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_DISABLED)
            result = write_preview_artifact_after_human_gate(
                preview=bridge.artifact_preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_bridge_output_cannot_bypass_hash_mismatch(self):
        bridge = build_preview_from_action_proposal(
            proposal=self.file_write_proposal(),
            proposed_content_text=CONTENT,
        )
        assert bridge.artifact_preview is not None

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=bridge.artifact_preview,
                proposed_content_text="changed after preview\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_static_no_new_capability_scan_includes_bridge_module(self):
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
        }

        scan = scan_module(BRIDGE_MODULE)

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

    def file_write_proposal(
        self,
        *,
        target_refs: tuple[str, ...] = (TARGET_PATH,),
        source_trust: ActionProposalSourceTrust = ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
    ):
        return build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=target_refs,
                arguments={"content": CONTENT},
                source_trust=source_trust,
                proposed_by="mock-provider-output",
                summary="bridge fixture file write proposal",
            )
        )

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="proposal-preview-bridge-run",
            sandbox_request_id="proposal-preview-bridge-sandbox-request",
            sandbox_result_id="proposal-preview-bridge-sandbox-result",
            requested_by="human-reviewer-proposal-preview",
            dry_run_trace_id="proposal-preview-bridge-dry-run",
            sandbox_policy_decision_id="proposal-preview-bridge-policy",
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-proposal-preview",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-proposal-preview",
            reason="reviewed exact proposal preview artifact",
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
