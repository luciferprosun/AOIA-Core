from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from runtime.artifact_preview import ArtifactPreviewStatus
from runtime.bridges.proposal_preview_gate_binding import (
    PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
    PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE,
    PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW,
    PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PROPOSAL,
    PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_TARGET_MISMATCH,
    PROPOSAL_PREVIEW_GATE_BINDING_READY,
    build_proposal_preview_gate_binding,
    canonical_binding_json,
    compute_proposal_preview_gate_binding_hash,
)
from runtime.bridges.proposal_to_preview import build_preview_from_action_proposal
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
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalSourceTrust,
    build_action_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BINDING_MODULE = REPO_ROOT / "runtime" / "bridges" / "proposal_preview_gate_binding.py"
CONTENT = "# Proposal preview gate binding fixture\n"
OTHER_CONTENT = "# Different binding fixture\n"
TARGET_PATH = "reports/proposal-preview-gate.txt"
OTHER_TARGET_PATH = "reports/other-proposal-preview-gate.txt"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
OTHER_ARTIFACT_HASH = hashlib.sha256(OTHER_CONTENT.encode("utf-8")).hexdigest()


class ProposalPreviewGateBinding1ATests(unittest.TestCase):
    def test_valid_proposal_preview_binding_is_created(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)

        result = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=ARTIFACT_HASH,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_READY, result.status)
        self.assertTrue(result.binding_valid)
        self.assertIsNotNone(result.binding_hash)
        self.assertEqual(proposal.proposal_hash, result.proposal_hash)
        self.assertEqual(preview.preview_id, result.preview_id)
        self.assertEqual(ARTIFACT_HASH, result.preview_proposed_hash)
        self.assertEqual(ARTIFACT_HASH, result.expected_artifact_hash)
        self.assertEqual(packet_hash, result.expected_packet_hash)

    def test_binding_hash_is_deterministic(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)

        first = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=ARTIFACT_HASH,
        )
        second = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=ARTIFACT_HASH,
        )

        self.assertEqual(first.binding_hash, second.binding_hash)
        self.assertEqual(first.binding_material, second.binding_material)

    def test_canonical_binding_json_is_deterministic_independent_of_dict_order(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}

        self.assertEqual(canonical_binding_json(left), canonical_binding_json(right))
        self.assertEqual(
            compute_proposal_preview_gate_binding_hash(left),
            compute_proposal_preview_gate_binding_hash(right),
        )

    def test_binding_includes_proposal_and_preview_metadata_where_available(self):
        result = self.valid_binding()

        self.assertEqual(result.proposal_id, result.binding_material["proposal_id"])
        self.assertEqual(result.proposal_hash, result.binding_material["proposal_hash"])
        self.assertEqual(ActionProposalKind.FILE_WRITE.value, result.binding_material["proposal_kind"])
        self.assertEqual(result.proposal_source_trust, result.binding_material["proposal_source_trust"])
        self.assertEqual(result.preview_id, result.binding_material["preview_id"])
        self.assertEqual(TARGET_PATH, result.binding_material["preview_target_path"])
        self.assertEqual(ARTIFACT_HASH, result.binding_material["preview_proposed_hash"])

    def test_file_write_proposal_validates_with_matching_preview(self):
        result = self.valid_binding()

        self.assertTrue(result.binding_valid)
        self.assertEqual(ActionProposalKind.FILE_WRITE.value, result.proposal_kind)
        self.assertEqual(TARGET_PATH, result.preview_target_path)

    def test_non_file_proposal_is_rejected(self):
        proposal = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.SHELL_COMMAND,
                target_refs=(TARGET_PATH,),
                arguments={"command": "echo metadata-only"},
            )
        )
        _, preview = self.proposal_and_preview()

        result = build_proposal_preview_gate_binding(proposal=proposal, preview=preview)

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PROPOSAL, result.status)
        self.assertFalse(result.binding_valid)

    def test_proposal_target_mismatch_blocks(self):
        proposal, preview = self.proposal_and_preview()
        mismatched = replace(proposal, target_refs=(OTHER_TARGET_PATH,))

        result = build_proposal_preview_gate_binding(proposal=mismatched, preview=preview)

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_TARGET_MISMATCH, result.status)
        self.assertFalse(result.binding_valid)

    def test_preview_status_not_ready_blocks(self):
        proposal, preview = self.proposal_and_preview()
        not_ready = replace(preview, status=ArtifactPreviewStatus.BLOCKED_BY_POLICY)

        result = build_proposal_preview_gate_binding(proposal=proposal, preview=not_ready)

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW, result.status)

    def test_malformed_preview_hash_blocks(self):
        proposal, preview = self.proposal_and_preview()
        malformed = replace(preview, proposed_sha256="not-a-sha256")

        result = build_proposal_preview_gate_binding(proposal=proposal, preview=malformed)

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW, result.status)

    def test_missing_proposal_hash_blocks_when_required(self):
        proposal, preview = self.proposal_and_preview()
        missing_hash = replace(proposal, proposal_hash="")

        result = build_proposal_preview_gate_binding(proposal=missing_hash, preview=preview)

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PROPOSAL, result.status)

    def test_missing_preview_proposed_hash_blocks(self):
        proposal, preview = self.proposal_and_preview()
        missing_hash = replace(preview, proposed_sha256="")

        result = build_proposal_preview_gate_binding(proposal=proposal, preview=missing_hash)

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW, result.status)

    def test_expected_artifact_hash_mismatch_blocks(self):
        proposal, preview = self.proposal_and_preview()

        result = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_artifact_hash=OTHER_ARTIFACT_HASH,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_expected_packet_hash_mismatch_blocks(self):
        proposal, preview = self.proposal_and_preview()
        gate = self.gate(self.packet_hash_for(proposal, preview), ARTIFACT_HASH).to_dict()

        result = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash="b" * 64,
            expected_artifact_hash=ARTIFACT_HASH,
            gate_result=gate,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_gate_artifact_hash_mismatch_blocks(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        gate = self.gate(packet_hash, OTHER_ARTIFACT_HASH).to_dict()

        result = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=ARTIFACT_HASH,
            gate_result=gate,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_gate_missing_required_fields_block(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        base = self.gate(packet_hash, ARTIFACT_HASH).to_dict()
        nested = dict(base["gate_result"])
        cases = {
            "missing_expected_packet_hash": (base, None, ARTIFACT_HASH),
            "missing_expected_artifact_hash": (base, packet_hash, None),
            "missing_approval_decision_id": ({**base, "gate_result": {**nested, "approval_decision_id": ""}}, packet_hash, ARTIFACT_HASH),
            "missing_audit_event_id": ({**base, "gate_result": {**nested, "audit_event_id": ""}}, packet_hash, ARTIFACT_HASH),
            "missing_audit_event_hash": ({**base, "gate_result": {**nested, "audit_event_hash": ""}}, packet_hash, ARTIFACT_HASH),
        }

        for name, (gate_result, expected_packet, expected_artifact) in cases.items():
            with self.subTest(name=name):
                result = build_proposal_preview_gate_binding(
                    proposal=proposal,
                    preview=preview,
                    expected_packet_hash=expected_packet,
                    expected_artifact_hash=expected_artifact,
                    gate_result=gate_result,
                )

                self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_stale_replayed_gate_for_different_proposal_blocks(self):
        proposal_a, preview_a = self.proposal_and_preview(target_path=TARGET_PATH)
        proposal_b, preview_b = self.proposal_and_preview(target_path=OTHER_TARGET_PATH)
        gate_for_a = self.gate(self.packet_hash_for(proposal_a, preview_a), ARTIFACT_HASH).to_dict()

        result = build_proposal_preview_gate_binding(
            proposal=proposal_b,
            preview=preview_b,
            expected_packet_hash=self.packet_hash_for(proposal_b, preview_b),
            expected_artifact_hash=ARTIFACT_HASH,
            gate_result=gate_for_a,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_stale_replayed_gate_for_different_preview_blocks(self):
        proposal, preview_a = self.proposal_and_preview()
        preview_b = replace(preview_a, preview_id="artifact-preview-" + "b" * 24)
        gate_for_a = self.gate(self.packet_hash_for(proposal, preview_a), ARTIFACT_HASH).to_dict()

        result = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview_b,
            expected_packet_hash=self.packet_hash_for(proposal, preview_b),
            expected_artifact_hash=ARTIFACT_HASH,
            gate_result=gate_for_a,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_stale_replayed_gate_for_different_artifact_hash_blocks(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        gate = self.gate(packet_hash, OTHER_ARTIFACT_HASH).to_dict()

        result = build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=ARTIFACT_HASH,
            gate_result=gate,
        )

        self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_gate_optional_proposal_preview_metadata_mismatch_blocks(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        base = self.gate(packet_hash, ARTIFACT_HASH).to_dict()
        cases = {
            "proposal_hash": {**base, "proposal_hash": "b" * 64},
            "preview_id": {**base, "preview_id": "artifact-preview-" + "b" * 24},
            "preview_proposed_hash": {**base, "preview_proposed_hash": OTHER_ARTIFACT_HASH},
        }

        for name, gate_result in cases.items():
            with self.subTest(name=name):
                result = build_proposal_preview_gate_binding(
                    proposal=proposal,
                    preview=preview,
                    expected_packet_hash=packet_hash,
                    expected_artifact_hash=ARTIFACT_HASH,
                    gate_result=gate_result,
                )

                self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH, result.status)

    def test_gate_authority_like_metadata_blocks(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        base = self.gate(packet_hash, ARTIFACT_HASH).to_dict()
        cases = {
            "metadata_authority": {**base, "metadata_authority": True},
            "provider_output_trusted": {**base, "provider_output_trusted": True},
            "artifact_write_occurred": {**base, "artifact_write_occurred": True},
        }

        for name, gate_result in cases.items():
            with self.subTest(name=name):
                result = build_proposal_preview_gate_binding(
                    proposal=proposal,
                    preview=preview,
                    expected_packet_hash=packet_hash,
                    expected_artifact_hash=ARTIFACT_HASH,
                    gate_result=gate_result,
                )

                self.assertEqual(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE, result.status)

    def test_binding_result_authority_fields_are_false(self):
        result = self.valid_binding()

        for field_name in self.authority_fields():
            with self.subTest(field_name=field_name):
                self.assertIs(False, getattr(result, field_name))
                self.assertIs(False, result.to_dict()[field_name])

    def test_binding_result_cannot_satisfy_control_write_gate_evidence_by_itself(self):
        proposal, preview = self.proposal_and_preview()
        binding = self.valid_binding(proposal=proposal, preview=preview)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=binding.to_dict(),
                context=self.context(),
                expected_packet_hash=binding.expected_packet_hash,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_binding_result_cannot_bypass_kill_switch_disabled_state(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        binding = self.valid_binding(proposal=proposal, preview=preview)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_DISABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(packet_hash, ARTIFACT_HASH),
                context=self.context(),
                expected_packet_hash=binding.expected_packet_hash,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=binding.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_binding_result_cannot_bypass_workspace_guard_failure(self):
        proposal, preview = self.proposal_and_preview(target_path="linked-parent/result.txt")
        packet_hash = self.packet_hash_for(proposal, preview)
        binding = self.valid_binding(proposal=proposal, preview=preview)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            link = Path(workspace) / "linked-parent"
            try:
                link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(packet_hash, ARTIFACT_HASH),
                context=self.context(),
                expected_packet_hash=binding.expected_packet_hash,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=binding.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertFalse((Path(outside) / "result.txt").exists())

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_binding_result_cannot_bypass_hash_mismatch(self):
        proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        binding = self.valid_binding(proposal=proposal, preview=preview)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text="changed after binding\n",
                workspace_root=workspace,
                gate_result=self.gate(packet_hash, ARTIFACT_HASH),
                context=self.context(),
                expected_packet_hash=binding.expected_packet_hash,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=binding.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_static_no_new_capability_scan_includes_binding_module(self):
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

        scan = scan_module(BINDING_MODULE)

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

    def proposal_and_preview(
        self,
        *,
        target_path: str = TARGET_PATH,
        source_trust: ActionProposalSourceTrust = ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
    ):
        proposal = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=(target_path,),
                arguments={"content": CONTENT},
                source_trust=source_trust,
                proposed_by="mock-provider-output",
                summary="proposal preview gate binding fixture",
            )
        )
        bridge = build_preview_from_action_proposal(
            proposal=proposal,
            proposed_content_text=CONTENT,
            expected_target_path=target_path,
        )
        assert bridge.artifact_preview is not None
        return proposal, bridge.artifact_preview

    def valid_binding(self, *, proposal=None, preview=None):
        if proposal is None or preview is None:
            proposal, preview = self.proposal_and_preview()
        packet_hash = self.packet_hash_for(proposal, preview)
        return build_proposal_preview_gate_binding(
            proposal=proposal,
            preview=preview,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=preview.proposed_sha256,
            gate_result=self.gate(packet_hash, preview.proposed_sha256),
        )

    def packet_hash_for(self, proposal, preview) -> str:
        material = {
            "proposal_hash": proposal.proposal_hash,
            "proposal_id": proposal.proposal_id,
            "preview_id": preview.preview_id,
            "preview_target_path": preview.target_path,
            "preview_proposed_hash": preview.proposed_sha256,
        }
        return hashlib.sha256(canonical_binding_json(material).encode("utf-8")).hexdigest()

    def gate(self, packet_hash: str, artifact_hash: str):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-proposal-preview-gate",
            displayed_packet_hash=packet_hash,
            current_packet_hash=packet_hash,
            displayed_artifact_hash=artifact_hash,
            current_artifact_hash=artifact_hash,
            human_actor="human-reviewer-proposal-preview-gate",
            reason="reviewed exact proposal preview gate binding artifact",
        )
        bridge = build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=artifact_hash,
        )
        with TemporaryDirectory() as audit_dir:
            handoff = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(audit_dir),
                expected_packet_hash=packet_hash,
                expected_artifact_hash=artifact_hash,
            )
        return evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=bridge.approval_decision,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=artifact_hash,
        )

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="proposal-preview-gate-binding-run",
            sandbox_request_id="proposal-preview-gate-binding-sandbox-request",
            sandbox_result_id="proposal-preview-gate-binding-sandbox-result",
            requested_by="human-reviewer-proposal-preview-gate",
            dry_run_trace_id="proposal-preview-gate-binding-dry-run",
            sandbox_policy_decision_id="proposal-preview-gate-binding-policy",
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
