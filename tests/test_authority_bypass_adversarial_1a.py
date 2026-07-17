from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from runtime.artifact_preview import (
    ArtifactPreviewRequest,
    ArtifactPreviewStatus,
    build_artifact_preview,
)
from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
    CONTROL_WRITE_BLOCKED_INVALID_PREVIEW,
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    ControlWriteContext,
    write_preview_artifact_after_human_gate,
)
from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import evaluate_human_decision_pre_artifact_gate
from runtime.human_decision_gated_artifact_write import (
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    ERROR_FAIL_CLOSED,
    write_artifact_after_human_gate,
)
from runtime.providers.contracts import ProviderRuntimeResult, UNTRUSTED
from runtime.providers.critic import critique_provider_result
from runtime.safety.sandbox_artifact_runner import (
    MAX_SANDBOX_ARTIFACT_BYTES,
    write_sandbox_artifact,
)
from runtime.safety.write_kill_switch import WRITES_ENABLED
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalSourceTrust,
    ActionProposalStatus,
    build_action_proposal,
)
from runtime.schemas.sandbox_artifact import (
    SANDBOX_ARTIFACT_CONTRACT_VERSION,
    SandboxArtifactState,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES_UNDER_AUTHORITY_SCAN = (
    REPO_ROOT / "runtime" / "artifact_preview.py",
    REPO_ROOT / "runtime" / "control_write.py",
    REPO_ROOT / "runtime" / "human_decision_gated_artifact_write.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
    REPO_ROOT / "runtime" / "schemas" / "action_proposal.py",
    REPO_ROOT / "runtime" / "providers" / "critic.py",
)

PACKET_HASH = "a" * 64
CONTENT = "# Authority bypass adversarial fixture\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
OTHER_CONTENT = "# Different reviewed artifact\n"
OTHER_ARTIFACT_HASH = hashlib.sha256(OTHER_CONTENT.encode("utf-8")).hexdigest()


class AuthorityBypassAdversarial1ATests(unittest.TestCase):
    def test_forged_artifact_preview_authority_fields_remain_inert_and_block_control_write(self):
        for field_name in (
            "write_performed",
            "can_write",
            "can_execute",
            "can_commit",
            "can_change_gate",
        ):
            with self.subTest(field_name=field_name):
                preview = self.preview()
                object.__setattr__(preview, field_name, True)
                writer = Mock(wraps=write_artifact_after_human_gate)

                result = self.run_control_write_with_enabled_switch(
                    preview=preview,
                    writer=writer,
                )

                self.assertEqual(CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, result.status)
                self.assertFalse(result.artifact_write_occurred)
                self.assertFalse(result.provider_output_trusted)
                self.assertFalse(result.metadata_authority)
                self.assertEqual(0, writer.call_count)

    def test_forged_provider_critic_report_authority_fields_remain_metadata_only(self):
        report = critique_provider_result(self.provider_result())
        forced = replace(
            report,
            output_trust="TRUSTED",
            can_approve=True,
            can_write=True,
            can_execute=True,
            can_change_gate=True,
        )

        self.assertEqual(UNTRUSTED, forced.output_trust)
        self.assertFalse(forced.can_approve)
        self.assertFalse(forced.can_write)
        self.assertFalse(forced.can_execute)
        self.assertFalse(forced.can_change_gate)

        object.__setattr__(forced, "can_approve", True)
        object.__setattr__(forced, "can_write", True)
        object.__setattr__(forced, "can_execute", True)
        object.__setattr__(forced, "can_change_gate", True)
        object.__setattr__(forced, "output_trust", "TRUSTED")

        result = self.run_control_write_with_enabled_switch(gate_result=forced)

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.metadata_authority)

    def test_forged_action_proposal_execution_fields_do_not_create_dispatch_or_authority(self):
        proposal = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=("reports/result.md",),
                arguments={"content": CONTENT},
                source_trust=ActionProposalSourceTrust.PROVIDER_UNTRUSTED,
                proposed_by="provider-output",
                summary="forged proposal cannot execute",
            )
        )
        forced = replace(
            proposal,
            execution_permitted=True,
            execution_implemented=True,
            human_approved=True,
        )

        self.assertFalse(forced.execution_permitted)
        self.assertFalse(forced.execution_implemented)
        self.assertTrue(forced.human_approved)

        result = self.run_control_write_with_enabled_switch(
            gate_result=forced.to_dict()
        )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(hasattr(forced, "dispatch"))
        self.assertFalse(hasattr(forced, "execute"))

    def test_forged_or_incomplete_gate_evidence_fails_closed(self):
        valid_gate = self.gate().to_dict()
        cases = {
            "missing_gate_result": {},
            "approve_missing_nested_proof": {
                key: value for key, value in valid_gate.items() if key != "gate_result"
            },
            "missing_approval_decision_id": self.gate_with_nested(
                approval_decision_id=""
            ),
            "missing_audit_event_id": self.gate_with_nested(audit_event_id=""),
            "missing_expected_packet_hash": {
                **valid_gate,
                "packet_hash": None,
            },
            "missing_expected_artifact_hash": {
                **valid_gate,
                "artifact_hash": None,
            },
            "provider_output_trusted": {
                **valid_gate,
                "provider_output_trusted": True,
            },
            "metadata_authority": {
                **valid_gate,
                "metadata_authority": True,
            },
            "artifact_write_occurred": {
                **valid_gate,
                "artifact_write_occurred": True,
            },
            "stale_or_mismatched_gate": {
                **valid_gate,
                "packet_hash": "b" * 64,
            },
        }

        for name, gate_result in cases.items():
            with self.subTest(name=name):
                writer = Mock(wraps=write_artifact_after_human_gate)

                result = self.run_control_write_with_enabled_switch(
                    gate_result=gate_result,
                    writer=writer,
                )

                self.assertTrue(result.blocking)
                self.assertFalse(result.artifact_write_occurred)
                self.assertFalse(result.provider_output_trusted)
                self.assertFalse(result.metadata_authority)
                self.assertEqual(0, writer.call_count)

    def test_hash_mismatch_and_replay_attacks_block_fail_closed(self):
        malformed_preview = self.preview()
        object.__setattr__(malformed_preview, "proposed_sha256", "not-a-sha256")

        replay_preview = self.preview(proposed_content=OTHER_CONTENT)
        old_gate = self.gate().to_dict()

        cases = (
            (
                "proposed_content_hash_mismatch",
                {"proposed_content_text": "changed after preview\n"},
                CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
            ),
            (
                "expected_packet_hash_mismatch",
                {"expected_packet_hash": "b" * 64},
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
            (
                "expected_artifact_hash_mismatch",
                {"expected_artifact_hash": "c" * 64},
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
            (
                "malformed_preview_hash",
                {"preview": malformed_preview},
                CONTROL_WRITE_BLOCKED_INVALID_PREVIEW,
            ),
            (
                "old_gate_reused_for_different_artifact_hash",
                {
                    "preview": replay_preview,
                    "proposed_content_text": OTHER_CONTENT,
                    "gate_result": old_gate,
                },
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
            (
                "preview_content_changed_after_approval",
                {
                    "preview": self.preview(proposed_content=OTHER_CONTENT),
                    "proposed_content_text": OTHER_CONTENT,
                    "gate_result": old_gate,
                },
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
        )

        for name, kwargs, expected_status in cases:
            with self.subTest(name=name):
                result = self.run_control_write_with_enabled_switch(**kwargs)

                self.assertEqual(expected_status, result.status)
                self.assertFalse(result.artifact_write_occurred)

    def test_direct_sandbox_writer_bypass_attempts_block_without_existing_contract_fields(self):
        invalid_requests = {
            "missing_human_approval": replace(self.sandbox_request(), human_approved=False),
            "missing_audit_fields": replace(
                self.sandbox_request(),
                audit_event_id="",
                contract_audit_event_id="",
            ),
            "missing_contract_fields": replace(
                self.sandbox_request(),
                artifact_contract_version="",
            ),
            "invalid_result_state": replace(
                self.sandbox_request(),
                sandbox_result_state="WRITTEN",
            ),
            "invalid_content_hash_contract": replace(
                self.sandbox_request(),
                contract_payload_hash="b" * 64,
            ),
            "invalid_target_path": replace(
                self.sandbox_request(),
                relative_output_path="../escape.md",
            ),
            "forged_approval_like_metadata": replace(
                self.sandbox_request(human_approved=False),
                notes="APPROVED SAFE TRUSTED AUTHORIZED",
            ),
        }

        with TemporaryDirectory() as switch_dir:
            switch_path = self.write_enabled_switch(switch_dir)
            for name, request in invalid_requests.items():
                with self.subTest(name=name), TemporaryDirectory() as workspace:
                    result = write_sandbox_artifact(
                        request,
                        workspace,
                        write_kill_switch_path=str(switch_path),
                        write_kill_switch_directory=switch_dir,
                    )

                    self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                    self.assertFalse(result.write_completed)
                    self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))

            with TemporaryDirectory() as workspace:
                with self.assertRaises(TypeError):
                    write_sandbox_artifact(
                        {"human_approved": True},  # type: ignore[arg-type]
                        workspace,
                        write_kill_switch_path=str(switch_path),
                        write_kill_switch_directory=switch_dir,
                    )
                self.assertFalse(any(Path(workspace).rglob("*")))

    def test_direct_sandbox_writer_accepts_only_existing_valid_contract_with_all_safety_fields(self):
        gate = self.gate()
        request = self.sandbox_request(gate_result=gate)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_enabled_switch(switch_dir)
            result = write_sandbox_artifact(
                request,
                workspace,
                approval_evidence=gate,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )
            output = Path(result.resolved_output_path)

            self.assertEqual(SandboxArtifactState.WRITTEN, result.state)
            self.assertTrue(output.is_file())
            self.assertEqual(CONTENT, output.read_text(encoding="utf-8"))
            self.assertEqual(SANDBOX_ARTIFACT_CONTRACT_VERSION, request.artifact_contract_version)
            self.assertTrue(request.human_approved)
            self.assertTrue(request.artifact_write_allowed)
            self.assertTrue(request.approval_decision_id)
            self.assertTrue(request.audit_event_id)
            self.assertEqual(request.audit_event_id, request.contract_audit_event_id)
            self.assertEqual(request.content_hash, request.contract_payload_hash)

    def test_path_traversal_blocks_across_proposal_preview_control_write_and_sandbox_layers(self):
        unsafe_paths = (
            "/absolute/path.md",
            "../escape.txt",
            "docs/../../escape.txt",
            "..\\escape.txt",
            "docs\\..\\escape.txt",
            "",
            "bad\x00path.txt",
        )

        with TemporaryDirectory() as switch_dir:
            switch_path = self.write_enabled_switch(switch_dir)
            for unsafe_path in unsafe_paths:
                with self.subTest(unsafe_path=repr(unsafe_path)):
                    proposal = build_action_proposal(
                        ActionProposalRequest(
                            action_kind=ActionProposalKind.FILE_WRITE,
                            target_refs=(unsafe_path,),
                            arguments={"content": CONTENT},
                        )
                    )
                    preview = self.preview(target_path=unsafe_path)
                    control_result = self.run_control_write_with_enabled_switch(
                        preview=preview
                    )

                    with TemporaryDirectory() as workspace:
                        sandbox_result = write_sandbox_artifact(
                            self.sandbox_request(relative_output_path=unsafe_path),
                            workspace,
                            write_kill_switch_path=str(switch_path),
                            write_kill_switch_directory=switch_dir,
                        )

                        self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))

                    self.assertEqual(ActionProposalStatus.INVALID_TARGET, proposal.status)
                    self.assertEqual(ArtifactPreviewStatus.INVALID_TARGET, preview.status)
                    self.assertEqual(CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, control_result.status)
                    self.assertEqual(SandboxArtifactState.BLOCKED, sandbox_result.state)

    def test_symlink_and_directory_targets_block_before_or_during_sandbox_write(self):
        with TemporaryDirectory() as switch_dir:
            switch_path = self.write_enabled_switch(switch_dir)
            with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
                link = Path(workspace) / "linked.md"
                try:
                    link.symlink_to(Path(outside) / "escape.md")
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlink creation not supported here: {exc}")

                result = write_sandbox_artifact(
                    self.sandbox_request(relative_output_path="linked.md"),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                self.assertFalse((Path(outside) / "escape.md").exists())

            with TemporaryDirectory() as workspace:
                directory_target = Path(workspace) / "directory.md"
                directory_target.mkdir()

                result = write_sandbox_artifact(
                    self.sandbox_request(relative_output_path="directory.md"),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                self.assertFalse(result.write_completed)

    def test_sandbox_hard_limits_block_fail_closed(self):
        with TemporaryDirectory() as switch_dir:
            switch_path = self.write_enabled_switch(switch_dir)
            over_limit = "x" * (MAX_SANDBOX_ARTIFACT_BYTES + 1)
            with TemporaryDirectory() as workspace:
                result = write_sandbox_artifact(
                    self.sandbox_request(
                        relative_output_path="over-limit.md",
                        content_text=over_limit,
                    ),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )
                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                self.assertFalse(result.write_attempted)

            with TemporaryDirectory() as workspace:
                output = Path(workspace) / "existing.md"
                output.write_text("original", encoding="utf-8")

                result = write_sandbox_artifact(
                    self.sandbox_request(relative_output_path="existing.md"),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                self.assertEqual("original", output.read_text(encoding="utf-8"))

            with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
                parent_link = Path(workspace) / "escape"
                try:
                    parent_link.symlink_to(Path(outside), target_is_directory=True)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlink creation not supported here: {exc}")

                result = write_sandbox_artifact(
                    self.sandbox_request(relative_output_path="escape/result.md"),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                self.assertFalse((Path(outside) / "result.md").exists())

            with TemporaryDirectory() as workspace:
                result = write_sandbox_artifact(
                    self.sandbox_request(relative_output_path="../escape.md"),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)

    def test_metadata_as_authority_attempts_do_not_satisfy_gate_or_write_authority(self):
        provider_result = self.provider_result()
        critic_report = critique_provider_result(provider_result)
        artifact_preview = self.preview()
        action_proposal = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=("reports/result.md",),
                arguments={"content": CONTENT},
            )
        )
        authority_words = {
            "tags": ["APPROVED", "SAFE", "TRUSTED", "AUTHORIZED"],
            "hats": ["HAT_APPROVED", "HAT_TRUSTED"],
            "tetrads": ["TETRAD_AUTHORIZED"],
            "metadata_authority": True,
            "provider_output_trusted": True,
        }
        attempts = (
            provider_result.to_dict(),
            critic_report,
            critic_report.to_dict(),
            artifact_preview,
            artifact_preview.__dict__,
            action_proposal,
            action_proposal.to_dict(),
            {"decision": "APPROVED", "safe": True, "trusted": True},
            authority_words,
        )

        for attempt in attempts:
            with self.subTest(attempt_type=type(attempt).__name__):
                result = self.run_control_write_with_enabled_switch(
                    gate_result=attempt
                )

                self.assertTrue(result.blocking)
                self.assertFalse(result.artifact_write_occurred)
                self.assertFalse(result.provider_output_trusted)
                self.assertFalse(result.metadata_authority)

    def test_static_no_new_capability_scan_for_authority_sensitive_runtime_modules(self):
        forbidden_imports = {
            "subprocess",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.cloud",
            "git",
        }
        forbidden_calls = {
            ("os", "system"),
            ("subprocess", "run"),
            ("subprocess", "Popen"),
            ("subprocess", "call"),
            ("subprocess", "check_call"),
            ("subprocess", "check_output"),
            ("webbrowser", "open"),
        }
        forbidden_names = {
            "Popen",
            "exec",
            "eval",
            "dispatch",
            "tool_call",
            "install_package",
            "approval_bypass",
        }

        for path in RUNTIME_FILES_UNDER_AUTHORITY_SCAN:
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports: list[str] = []
                called_names: set[str] = set()
                called_attrs: set[tuple[str | None, str]] = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.append(node.module)
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            called_names.add(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            owner = (
                                node.func.value.id
                                if isinstance(node.func.value, ast.Name)
                                else None
                            )
                            called_attrs.add((owner, node.func.attr))

                for module_name in imports:
                    self.assertFalse(
                        any(
                            module_name == forbidden
                            or module_name.startswith(forbidden + ".")
                            for forbidden in forbidden_imports
                        ),
                        module_name,
                    )
                self.assertTrue(forbidden_calls.isdisjoint(called_attrs))
                self.assertTrue(forbidden_names.isdisjoint(called_names))

    def run_control_write_with_enabled_switch(
        self,
        *,
        preview=None,
        proposed_content_text: str = CONTENT,
        gate_result=None,
        expected_packet_hash: str | None = PACKET_HASH,
        expected_artifact_hash: str | None = None,
        metadata=None,
        writer=None,
    ):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_enabled_switch(switch_dir)
            result = write_preview_artifact_after_human_gate(
                preview=preview or self.preview(),
                proposed_content_text=proposed_content_text,
                workspace_root=workspace,
                gate_result=self.gate() if gate_result is None else gate_result,
                context=self.context(),
                expected_packet_hash=expected_packet_hash,
                expected_artifact_hash=expected_artifact_hash,
                metadata=metadata,
                gated_writer=writer or write_artifact_after_human_gate,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )
            self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))
            return result

    @staticmethod
    def write_enabled_switch(switch_dir: str) -> Path:
        switch_path = Path(switch_dir) / "write_kill_switch.state"
        switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
        return switch_path

    def preview(self, **changes):
        values = {
            "target_path": "reports/authority-bypass.md",
            "proposed_content": CONTENT,
            "artifact_kind": "text",
        }
        values.update(changes)
        return build_artifact_preview(ArtifactPreviewRequest(**values))

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="authority-bypass-run",
            sandbox_request_id="authority-bypass-sandbox-request",
            sandbox_result_id="authority-bypass-sandbox-result",
            requested_by="human-authority-reviewer",
            dry_run_trace_id="authority-bypass-dry-run",
            sandbox_policy_decision_id="authority-bypass-policy-decision",
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-authority-bypass",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-authority-reviewer",
            reason="reviewed exact authority bypass fixture content",
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

    def gate_with_nested(self, **nested_changes) -> dict:
        gate = self.gate().to_dict()
        nested = dict(gate["gate_result"])
        nested.update(nested_changes)
        gate["gate_result"] = nested
        return gate

    def sandbox_request(
        self,
        *,
        relative_output_path: str = "reports/authority-bypass.md",
        content_text: str = CONTENT,
        human_approved: bool = True,
        gate_result=None,
    ):
        nested_gate = (gate_result or self.gate()).gate_result
        assert nested_gate is not None
        return create_sandbox_artifact_request(
            run_id="authority-bypass-run",
            sandbox_request_id="authority-bypass-sandbox-request",
            sandbox_result_id="authority-bypass-sandbox-result",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path=relative_output_path,
            content_text=content_text,
            requested_by="human-authority-reviewer",
            human_approved=human_approved,
            dry_run_trace_id="authority-bypass-dry-run",
            audit_event_id=nested_gate.audit_event_id or "authority-bypass-audit-event",
            approval_decision_id=nested_gate.approval_decision_id or "authority-bypass-approval-decision",
            sandbox_policy_decision_id="authority-bypass-policy-decision",
            contract_audit_event_id=nested_gate.audit_event_id or "authority-bypass-audit-event",
            notes="Authority bypass adversarial sandbox fixture.",
        )

    @staticmethod
    def provider_result() -> ProviderRuntimeResult:
        return ProviderRuntimeResult(
            provider_id="mock_chat",
            model_id="mock-model",
            mode="dry_run",
            status="dry_run_preview",
            redacted_request_preview='{"model":"mock-model"}',
            response_text="Clean local provider output.",
            trust_status=UNTRUSTED,
        )


if __name__ == "__main__":
    unittest.main()
