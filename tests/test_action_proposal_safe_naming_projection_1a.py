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
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalRiskFlag,
    ActionProposalSourceTrust,
    build_action_proposal,
)
from runtime.schemas.action_proposal_projection import (
    ACTION_PROPOSAL_SAFE_PROJECTION_READY,
    ActionProposalSafeProjection,
    project_action_proposal_for_review,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTION_MODULE = REPO_ROOT / "runtime" / "schemas" / "action_proposal_projection.py"
PACKET_HASH = "a" * 64
CONTENT = "# Action proposal safe projection fixture\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
TARGET_PATH = "reports/action-proposal-safe-projection.txt"


class ActionProposalSafeNamingProjection1ATests(unittest.TestCase):
    def test_valid_action_proposal_projects_to_safe_review_projection(self):
        proposal = self.proposal(ActionProposalKind.FILE_WRITE)

        projection = project_action_proposal_for_review(proposal)

        self.assertIsInstance(projection, ActionProposalSafeProjection)
        self.assertEqual(ACTION_PROPOSAL_SAFE_PROJECTION_READY, projection.status)
        self.assertTrue(projection.projection_ready)
        self.assertEqual("proposed_file_write_metadata", projection.safe_display_kind)
        self.assertIn("metadata only", projection.metadata_only_warning.casefold())

    def test_projection_preserves_original_proposal_id_and_hash_if_available(self):
        proposal = self.proposal(ActionProposalKind.FILE_WRITE)

        projection = project_action_proposal_for_review(proposal)

        self.assertEqual(proposal.proposal_id, projection.original_proposal_id)
        self.assertEqual(proposal.proposal_hash, projection.original_proposal_hash)
        self.assertEqual(proposal.action_kind.value, projection.original_action_kind)

    def test_projection_preserves_source_trust_without_upgrading_trust(self):
        for source_trust in ActionProposalSourceTrust:
            with self.subTest(source_trust=source_trust):
                proposal = self.proposal(ActionProposalKind.FILE_WRITE, source_trust=source_trust)

                projection = project_action_proposal_for_review(proposal)

                self.assertEqual(source_trust.value, projection.source_trust)
                self.assertFalse(projection.can_call_provider)
                self.assertFalse(projection.provider_authority_granted)
                self.assertNotIn("trusted", projection.safe_display_kind.casefold())

    def test_projection_preserves_risk_flags_as_metadata(self):
        proposal = self.proposal(
            ActionProposalKind.FILE_WRITE,
            source_trust=ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
        )

        projection = project_action_proposal_for_review(proposal)

        self.assertIn(ActionProposalRiskFlag.FILESYSTEM_WRITE.value, projection.risk_flags)
        self.assertIn(ActionProposalRiskFlag.MUTATING_ACTION.value, projection.risk_flags)
        self.assertIn(ActionProposalRiskFlag.PROVIDER_OUTPUT_UNTRUSTED.value, projection.risk_flags)
        self.assertFalse(projection.can_write)
        self.assertFalse(projection.write_authority_granted)

    def test_action_kinds_display_as_proposed_review_metadata_not_executable_actions(self):
        cases = {
            ActionProposalKind.FILE_WRITE: "proposed_file_write_metadata",
            ActionProposalKind.SHELL_COMMAND: "proposed_shell_command_metadata",
            ActionProposalKind.GIT_COMMIT: "proposed_git_commit_metadata",
            ActionProposalKind.GIT_PUSH: "proposed_git_push_metadata",
            ActionProposalKind.BROWSER_ACTION: "proposed_browser_action_metadata",
            ActionProposalKind.PACKAGE_INSTALL: "proposed_package_install_metadata",
            ActionProposalKind.PROVIDER_CALL: "proposed_provider_call_metadata",
            "made_up_action": "unknown_proposed_action_metadata",
        }

        forbidden_display_terms = (
            "approved",
            "authorized",
            "permission",
            "execute_now",
            "dispatch",
            "run_now",
            "write_now",
            "commit_now",
            "push_now",
        )
        for action_kind, expected_display_kind in cases.items():
            with self.subTest(action_kind=action_kind):
                proposal = self.proposal(action_kind)

                projection = project_action_proposal_for_review(proposal)

                self.assertEqual(expected_display_kind, projection.safe_display_kind)
                display_text = " ".join(
                    (
                        projection.safe_display_kind or "",
                        projection.safe_display_name or "",
                        projection.execution_status_summary,
                    )
                ).casefold()
                self.assertIn("metadata", display_text)
                for term in forbidden_display_terms:
                    self.assertNotIn(term, display_text)
                self.assertFalse(projection.can_execute)
                self.assertFalse(projection.execution_authority_granted)

    def test_projection_authority_fields_are_false(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.GIT_PUSH))

        for field_name in self.authority_fields():
            with self.subTest(field_name=field_name):
                self.assertIs(False, getattr(projection, field_name))
                self.assertIs(False, projection.to_dict()[field_name])

    def test_projection_has_no_dispatch_or_execution_methods(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.SHELL_COMMAND))

        for name in ("execute", "dispatch", "write", "commit", "push", "call_provider", "approve"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(projection, name))

    def test_projection_cannot_satisfy_control_write_gate_evidence(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.FILE_WRITE))
        preview = self.preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=projection.to_dict(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_projection_cannot_bypass_kill_switch_disabled_state(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.FILE_WRITE))
        preview = self.preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_DISABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=projection.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_projection_cannot_bypass_hash_mismatch(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.FILE_WRITE))
        preview = self.preview()

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text="changed after projection\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=projection.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_projection_cannot_bypass_workspace_guard_failure(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.FILE_WRITE))
        preview = self.preview(target_path="linked-parent/result.txt")

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
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                metadata=projection.to_dict(),
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertFalse((Path(outside) / "result.txt").exists())

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_projection_cannot_be_used_as_preview_provider_or_commit_authority(self):
        projection = project_action_proposal_for_review(self.proposal(ActionProposalKind.PROVIDER_CALL))
        data = projection.to_dict()

        self.assertFalse(data["can_write"])
        self.assertFalse(data["can_execute"])
        self.assertFalse(data["can_commit"])
        self.assertFalse(data["can_push"])
        self.assertFalse(data["can_call_provider"])
        self.assertFalse(data["provider_authority_granted"])
        self.assertNotIn("decision", data)
        self.assertNotIn("packet_hash", data)
        self.assertNotIn("artifact_hash", data)
        self.assertNotIn("gate_result", data)

    def test_static_no_new_capability_scan_includes_projection_module(self):
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

        scan = scan_module(PROJECTION_MODULE)

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

    def proposal(
        self,
        action_kind: ActionProposalKind | str,
        *,
        source_trust: ActionProposalSourceTrust = ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
    ):
        return build_action_proposal(
            ActionProposalRequest(
                action_kind=action_kind,
                target_refs=(TARGET_PATH,),
                arguments={"content": CONTENT},
                source_trust=source_trust,
                proposed_by="safe-projection-test",
                summary="safe projection fixture",
            )
        )

    def preview(self, *, target_path: str = TARGET_PATH):
        return build_artifact_preview(
            ArtifactPreviewRequest(
                target_path=target_path,
                proposed_content=CONTENT,
                artifact_kind="text",
                provider_output_trust="untrusted",
            )
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-action-proposal-safe-projection",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-action-proposal-safe-projection",
            reason="reviewed exact safe projection fixture",
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
            run_id="action-proposal-safe-projection-run",
            sandbox_request_id="action-proposal-safe-projection-sandbox-request",
            sandbox_result_id="action-proposal-safe-projection-sandbox-result",
            requested_by="human-reviewer-action-proposal-safe-projection",
            dry_run_trace_id="action-proposal-safe-projection-dry-run",
            sandbox_policy_decision_id="action-proposal-safe-projection-policy",
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
