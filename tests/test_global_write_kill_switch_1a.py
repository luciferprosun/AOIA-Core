from __future__ import annotations

import ast
import hashlib
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.audit.durable_audit_ledger import append_audit_entry, verify_audit_ledger
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
    ARTIFACT_WRITTEN,
    BLOCKED_CONTROLLED_WRITE,
    BLOCKED_GATE_NOT_PASSED,
    BLOCKED_WRITE_KILL_SWITCH,
    write_artifact_after_human_gate,
)
from runtime.providers.contracts import LIVE_SUCCESS, UNTRUSTED, ProviderRuntimeResult
from runtime.providers.critic import critique_provider_result
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.write_kill_switch import (
    WRITES_DISABLED,
    WRITES_ENABLED,
    WRITE_KILL_SWITCH_ALLOWED,
    WRITE_KILL_SWITCH_BLOCKED_DISABLED,
    WRITE_KILL_SWITCH_BLOCKED_EMPTY,
    WRITE_KILL_SWITCH_BLOCKED_MALFORMED,
    WRITE_KILL_SWITCH_BLOCKED_MISSING,
    WRITE_KILL_SWITCH_BLOCKED_UNKNOWN,
    WRITE_KILL_SWITCH_BLOCKED_UNREADABLE,
    WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH,
    WriteKillSwitchCheckResult,
    check_write_kill_switch_file,
    check_write_kill_switch_in_directory,
    evaluate_write_kill_switch_value,
    resolve_required_write_kill_switch,
)
from runtime.schemas.action_proposal import (
    ActionProposalType,
    create_inert_action_proposal,
)
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactState,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)
from tests import static_capability_boundary_support_1a as step14


REPO_ROOT = Path(__file__).resolve().parents[1]
KILL_SWITCH_MODULE = REPO_ROOT / "runtime" / "safety" / "write_kill_switch.py"
PACKET_HASH = "a" * 64
CONTENT = "# Step 15 write kill-switch fixture\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class GlobalWriteKillSwitch1ATests(unittest.TestCase):
    def test_enabled_kill_switch_allows_controlled_path_to_existing_checks(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(ARTIFACT_WRITTEN, result.status)
        self.assertEqual(1, writer.call_count)
        self.assertEqual(1, len(files))
        self.assertEqual(str(switch_path), writer.call_args.kwargs["write_kill_switch_path"])
        self.assertEqual(switch_dir, writer.call_args.kwargs["write_kill_switch_directory"])

    def test_disabled_kill_switch_blocks_even_with_valid_gate_evidence(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_DISABLED)

            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)

    def test_missing_switch_argument_blocks_control_write(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace:
            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
            )

            self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)

    def test_missing_switch_argument_blocks_sandbox_write(self):
        with TemporaryDirectory() as workspace:
            gate = self.gate()
            result = write_sandbox_artifact(
                self.request(gate),
                workspace,
                approval_evidence=gate,
            )

            self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))

        self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
        self.assertFalse(result.write_attempted)

    def test_missing_switch_argument_blocks_human_gated_writer(self):
        writer = Mock(wraps=write_sandbox_artifact)
        with TemporaryDirectory() as workspace:
            gate = self.gate()
            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=self.request(gate),
                workspace_root=workspace,
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                artifact_writer=writer,
            )

            self.assertEqual([], list(Path(workspace).iterdir()))

        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)

    def test_default_switch_filename_is_resolved_only_from_explicit_directory(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_switch(switch_dir, WRITES_ENABLED)
            gate = self.gate()
            result = write_sandbox_artifact(
                self.request(gate),
                workspace,
                approval_evidence=gate,
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(SandboxArtifactState.WRITTEN, result.state)
        self.assertTrue(result.write_completed)

        with TemporaryDirectory() as parent:
            missing_directory = Path(parent) / "missing"
            blocked = resolve_required_write_kill_switch(
                switch_directory=missing_directory,
            )
            invalid_directory = Path(parent) / "not-a-directory"
            invalid_directory.write_text(WRITES_ENABLED, encoding="utf-8")
            invalid = resolve_required_write_kill_switch(
                switch_directory=invalid_directory,
            )

        self.assertFalse(blocked.writes_allowed)
        self.assertEqual(WRITE_KILL_SWITCH_BLOCKED_MISSING, blocked.status.value)
        self.assertFalse(invalid.writes_allowed)
        self.assertEqual(WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH, invalid.status.value)

    def test_malformed_missing_and_invalid_switch_files_block_sandbox_write(self):
        cases = {
            "missing": (None, WRITE_KILL_SWITCH_BLOCKED_MISSING),
            "empty": ("", WRITE_KILL_SWITCH_BLOCKED_EMPTY),
            "unknown": ("ALLOW_WRITES", WRITE_KILL_SWITCH_BLOCKED_UNKNOWN),
            "malformed": (WRITES_ENABLED + "\n" + WRITES_DISABLED, WRITE_KILL_SWITCH_BLOCKED_MALFORMED),
            "disabled": (WRITES_DISABLED, WRITE_KILL_SWITCH_BLOCKED_DISABLED),
        }

        for name, (state, status) in cases.items():
            with self.subTest(name=name):
                with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
                    switch_path = Path(switch_dir) / "write_kill_switch.state"
                    if state is not None:
                        switch_path.write_text(state, encoding="utf-8")

                    result = write_sandbox_artifact(
                        self.request(),
                        workspace,
                        write_kill_switch_path=str(switch_path),
                        write_kill_switch_directory=switch_dir,
                    )

                    self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                    self.assertFalse(result.write_attempted)
                    self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))
                    self.assertEqual(
                        status,
                        check_write_kill_switch_file(
                            str(switch_path),
                            allowed_switch_directory=switch_dir,
                        ).status.value,
                    )

    def test_unreadable_switch_file_blocks_where_supported(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            original_mode = switch_path.stat().st_mode
            switch_path.chmod(0)
            try:
                check = check_write_kill_switch_file(
                    str(switch_path),
                    allowed_switch_directory=switch_dir,
                )
                if check.status.value != WRITE_KILL_SWITCH_BLOCKED_UNREADABLE:
                    self.skipTest("filesystem did not make chmod(0) file unreadable")

                result = write_sandbox_artifact(
                    self.request(),
                    workspace,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )
            finally:
                switch_path.chmod(original_mode)

        self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
        self.assertFalse(result.write_attempted)

    def test_symlink_directory_and_traversal_switch_paths_block(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_root = Path(switch_dir)
            real_switch = self.write_switch(switch_dir, WRITES_ENABLED)
            symlink_path = switch_root / "symlink.state"
            try:
                symlink_path.symlink_to(real_switch)
            except (OSError, NotImplementedError) as exc:
                symlink_path = None
                symlink_error = exc
            else:
                symlink_error = None

            cases = [
                ("directory", str(switch_root), WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH),
                ("traversal", "../escape.state", WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH),
                ("absolute_filename", str(real_switch), WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH),
                ("null_byte", "switch\x00.state", WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH),
                ("outside_directory", str(Path(workspace) / "outside.state"), WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH),
            ]
            if symlink_path is not None:
                cases.append(("symlink", str(symlink_path), WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH))
            else:
                self.assertIsNotNone(symlink_error)

            for name, path_value, status in cases:
                with self.subTest(name=name):
                    if name == "absolute_filename":
                        check = check_write_kill_switch_in_directory(
                            switch_directory=switch_dir,
                            switch_filename=path_value,
                        )
                    elif name in {"traversal", "null_byte"}:
                        check = check_write_kill_switch_in_directory(
                            switch_directory=switch_dir,
                            switch_filename=path_value,
                        )
                    else:
                        check = check_write_kill_switch_file(
                            path_value,
                            allowed_switch_directory=switch_dir,
                        )

                    self.assertEqual(status, check.status.value)

            symlink_directory = switch_root / "directory-link"
            try:
                symlink_directory.symlink_to(switch_root, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            else:
                directory_check = resolve_required_write_kill_switch(
                    switch_directory=symlink_directory,
                )
                self.assertFalse(directory_check.writes_allowed)
                self.assertEqual(
                    WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH,
                    directory_check.status.value,
                )

    def test_wrong_type_falsey_and_arbitrary_switch_configuration_fails_closed(self):
        path_cases = (
            False,
            True,
            0,
            1,
            [],
            {},
            {"enabled": True},
            object(),
        )
        for value in path_cases:
            with self.subTest(kind="path", value_type=type(value).__name__):
                result = resolve_required_write_kill_switch(value)
                self.assertFalse(result.writes_allowed)
                self.assertEqual(WRITE_KILL_SWITCH_BLOCKED_MALFORMED, result.status.value)

        directory_cases = (False, True, 0, 1, [], {}, object())
        for value in directory_cases:
            with self.subTest(kind="directory", value_type=type(value).__name__):
                result = resolve_required_write_kill_switch(
                    switch_directory=value,
                )
                self.assertFalse(result.writes_allowed)
                self.assertEqual(WRITE_KILL_SWITCH_BLOCKED_MALFORMED, result.status.value)

        self.assertFalse(resolve_required_write_kill_switch("").writes_allowed)
        self.assertFalse(
            resolve_required_write_kill_switch(switch_directory="").writes_allowed
        )

    def test_enabled_kill_switch_does_not_bypass_hash_mismatch(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text="changed after preview\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertEqual(0, writer.call_count)

    def test_enabled_kill_switch_does_not_bypass_missing_gate_evidence(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result={},
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertEqual(0, writer.call_count)

    def test_enabled_kill_switch_does_not_bypass_metadata_authority_blocks(self):
        gate = self.gate().to_dict()
        cases = {
            "metadata_authority": {**gate, "metadata_authority": True},
            "provider_output_trusted": {**gate, "provider_output_trusted": True},
        }

        for name, gate_result in cases.items():
            with self.subTest(name=name):
                writer = Mock(wraps=write_artifact_after_human_gate)
                with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
                    switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

                    result = write_preview_artifact_after_human_gate(
                        preview=self.preview(),
                        proposed_content_text=CONTENT,
                        workspace_root=workspace,
                        gate_result=gate_result,
                        context=self.context(),
                        expected_packet_hash=PACKET_HASH,
                        gated_writer=writer,
                        write_kill_switch_path=str(switch_path),
                        write_kill_switch_directory=switch_dir,
                    )

                self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
                self.assertEqual(0, writer.call_count)

    def test_enabled_kill_switch_does_not_bypass_gated_writer_gate_checks(self):
        gate = self.gate()
        request = self.request()
        blocked_gate = gate.to_dict()
        blocked_gate["pre_artifact_gate_passed"] = False
        blocked_gate["blocking"] = True

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = write_artifact_after_human_gate(
                gate_result=blocked_gate,
                artifact_request=request,
                workspace_root=workspace,
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(BLOCKED_GATE_NOT_PASSED, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_enabled_switch_cannot_replace_missing_or_forged_approval(self):
        with TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            for name, approval in (
                ("missing", None),
                ("mapping", {"approved": True, "gate_passed": True}),
                ("arbitrary", object()),
            ):
                with self.subTest(name=name), TemporaryDirectory() as workspace:
                    gate = self.gate()
                    result = write_sandbox_artifact(
                        self.request(gate),
                        workspace,
                        approval_evidence=approval,
                        write_kill_switch_path=str(switch_path),
                        write_kill_switch_directory=switch_dir,
                    )

                    self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                    self.assertFalse(result.write_attempted)
                    self.assertEqual([], list(Path(workspace).iterdir()))

    def test_switch_configuration_is_forwarded_and_rechecked_at_each_layer(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            gate = self.gate()
            sandbox_writer = Mock(wraps=write_sandbox_artifact)
            direct = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=self.request(gate),
                workspace_root=workspace,
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                artifact_writer=sandbox_writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertEqual(ARTIFACT_WRITTEN, direct.status)
            self.assertEqual(
                str(switch_path),
                sandbox_writer.call_args.kwargs["write_kill_switch_path"],
            )
            self.assertEqual(
                switch_dir,
                sandbox_writer.call_args.kwargs["write_kill_switch_directory"],
            )

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            def disable_before_lower_gate(**kwargs):
                switch_path.write_text(WRITES_DISABLED, encoding="utf-8")
                return write_artifact_after_human_gate(**kwargs)

            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=disable_before_lower_gate,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
            self.assertEqual([], list(Path(workspace).iterdir()))

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            gate = self.gate()

            def disable_before_sandbox(*args, **kwargs):
                switch_path.write_text(WRITES_DISABLED, encoding="utf-8")
                return write_sandbox_artifact(*args, **kwargs)

            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=self.request(gate),
                workspace_root=workspace,
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                artifact_writer=disable_before_sandbox,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
            self.assertEqual([], list(Path(workspace).iterdir()))

    def test_provider_critic_preview_proposal_ledger_policy_and_metadata_are_inert(self):
        provider_result = ProviderRuntimeResult(
            provider_id="mock_chat",
            model_id="step-15",
            mode="live",
            status=LIVE_SUCCESS,
            redacted_request_preview="redacted",
            response_text=WRITES_ENABLED,
            trust_status=UNTRUSTED,
        )
        critic_report = critique_provider_result(provider_result)
        action_proposal = create_inert_action_proposal(
            proposal_type=ActionProposalType.FILESYSTEM_ACTION,
            title="Enable writes",
            description="Authority-looking inert proposal",
            proposed_by="provider",
            exact_payload=WRITES_ENABLED,
            created_at="2026-07-17T00:00:00Z",
            proposal_id="step-15-inert-proposal",
        )
        static_violation = step14.StaticCapabilityViolation(
            path="runtime/inert.py",
            line=1,
            column=0,
            category="evidence-only",
            symbol="WRITES_ENABLED",
            message="static evidence remains non-authoritative",
        )
        static_scan = step14.StaticCapabilityGraphScan(
            root_path="runtime/inert.py",
            zone="other_inert",
            scanned_paths=("runtime/inert.py",),
            direct_local_imports=(),
            direct_external_imports=(),
            unresolved_imports=(),
            exemptions_applied=(),
            violations=(static_violation,),
        )

        with TemporaryDirectory() as ledger_dir:
            ledger_path = Path(ledger_dir) / "audit.jsonl"
            append_result = append_audit_entry(
                ledger_path,
                "writes_enabled",
                {"write_enabled": True, "authority": "approved"},
            )
            self.assertTrue(append_result.appended)
            assert append_result.entry is not None
            assert append_result.tip is not None
            verification_result = verify_audit_ledger(
                ledger_path,
                expected_tip=append_result.tip,
            )
            cases = {
                "provider_output": provider_result,
                "critic_report": critic_report,
                "artifact_preview": self.preview(),
                "action_proposal": action_proposal,
                "ledger_entry": append_result.entry,
                "ledger_tip": append_result.tip,
                "ledger_append_result": append_result,
                "ledger_verification_result": verification_result,
                "static_scan": static_scan,
                "static_violation": static_violation,
                "authority_metadata": {
                    "enabled": True,
                    "approved": True,
                    "allow_write": True,
                    "write_enabled": True,
                    "override": True,
                    "emergency_override": True,
                    "gate_passed": True,
                    "human_approved": True,
                    "authority": WRITES_ENABLED,
                },
            }

            for name, candidate in cases.items():
                with self.subTest(name=name), TemporaryDirectory() as workspace:
                    gate = self.gate()
                    result = write_sandbox_artifact(
                        self.request(gate),
                        workspace,
                        approval_evidence=gate,
                        write_kill_switch_path=candidate,  # type: ignore[arg-type]
                    )

                    self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                    self.assertFalse(result.write_attempted)
                    self.assertEqual([], list(Path(workspace).iterdir()))

    def test_environment_variables_cannot_enable_missing_or_disabled_state(self):
        environment = {
            "AOIA_WRITES_ENABLED": WRITES_ENABLED,
            "WRITES_ENABLED": WRITES_ENABLED,
            "WRITE_KILL_SWITCH": WRITES_ENABLED,
            "AOIA_WRITE_KILL_SWITCH": WRITES_ENABLED,
        }
        with patch.dict(os.environ, environment, clear=False):
            missing = resolve_required_write_kill_switch()
            with TemporaryDirectory() as switch_dir:
                disabled_path = self.write_switch(switch_dir, WRITES_DISABLED)
                disabled = resolve_required_write_kill_switch(
                    disabled_path,
                    switch_directory=switch_dir,
                )
                with TemporaryDirectory() as workspace:
                    gate = self.gate()
                    write_result = write_sandbox_artifact(
                        self.request(gate),
                        workspace,
                        approval_evidence=gate,
                    )
                    self.assertEqual([], list(Path(workspace).iterdir()))

        self.assertFalse(missing.writes_allowed)
        self.assertFalse(disabled.writes_allowed)
        self.assertEqual(SandboxArtifactState.BLOCKED, write_result.state)

    def test_rejected_switch_states_leave_no_target_parent_or_temporary_artifact(self):
        with TemporaryDirectory() as switch_dir:
            disabled = self.write_switch(switch_dir, WRITES_DISABLED)
            malformed = Path(switch_dir) / "malformed.state"
            malformed.write_text(WRITES_ENABLED + "\n" + WRITES_DISABLED, encoding="utf-8")
            unknown = Path(switch_dir) / "unknown.state"
            unknown.write_text("ALLOW_WRITES", encoding="utf-8")
            cases = (
                ("missing_configuration", None, None),
                ("disabled", str(disabled), switch_dir),
                ("malformed", str(malformed), switch_dir),
                ("unknown", str(unknown), switch_dir),
                ("wrong_type", object(), None),
            )

            for name, switch_path, allowed_directory in cases:
                with self.subTest(name=name), TemporaryDirectory() as workspace:
                    gate = self.gate()
                    result = write_sandbox_artifact(
                        self.request(gate),
                        workspace,
                        approval_evidence=gate,
                        write_kill_switch_path=switch_path,  # type: ignore[arg-type]
                        write_kill_switch_directory=allowed_directory,
                    )

                    self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                    self.assertFalse(result.write_attempted)
                    self.assertEqual([], list(Path(workspace).iterdir()))

    def test_authority_fields_remain_false(self):
        result = evaluate_write_kill_switch_value(WRITES_ENABLED)
        forced = WriteKillSwitchCheckResult(
            status=WRITE_KILL_SWITCH_ALLOWED,
            writes_allowed=True,
            reason="forced flags are normalized",
            source_path="/tmp/switch",
            can_approve=True,
            can_write=True,
            can_execute=True,
            can_commit=True,
            can_push=True,
            can_call_provider=True,
            can_change_gate=True,
            write_authority_granted=True,
            execution_authority_granted=True,
            provider_authority_granted=True,
        )

        for check in (result, forced):
            with self.subTest(status=check.status.value):
                self.assertFalse(check.can_approve)
                self.assertFalse(check.can_write)
                self.assertFalse(check.can_execute)
                self.assertFalse(check.can_commit)
                self.assertFalse(check.can_push)
                self.assertFalse(check.can_call_provider)
                self.assertFalse(check.can_change_gate)
                self.assertFalse(check.write_authority_granted)
                self.assertFalse(check.execution_authority_granted)
                self.assertFalse(check.provider_authority_granted)

    def test_static_no_new_capability_scan_includes_kill_switch_module(self):
        forbidden_import_prefixes = (
            "subprocess",
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
        )
        forbidden_calls = {
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "Popen",
            "eval",
            "exec",
            "__import__",
        }
        scan = scan_module(KILL_SWITCH_MODULE)

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
        records = step14.resolve_step14_core_protected_files(REPO_ROOT)
        protected = {
            record.path: record.zone
            for record in records
        }
        self.assertEqual(
            "other_inert",
            protected["runtime/safety/write_kill_switch.py"],
        )
        report = next(
            item
            for item in step14.scan_step14_import_graph(REPO_ROOT, records)
            if item.root_path == "runtime/safety/write_kill_switch.py"
        )
        self.assertEqual((), report.violations)
        self.assertEqual((), report.unresolved_imports)

    def preview(self):
        return build_artifact_preview(
            ArtifactPreviewRequest(
                target_path="reports/step15.txt",
                proposed_content=CONTENT,
                artifact_kind="text",
            )
        )

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="step-15-run",
            sandbox_request_id="step-15-sandbox-request",
            sandbox_result_id="step-15-sandbox-result",
            requested_by="human-reviewer-step-15",
            dry_run_trace_id="step-15-dry-run-trace",
            sandbox_policy_decision_id="step-15-sandbox-policy-decision",
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-step-15",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-step-15",
            reason="reviewed exact Step 15 artifact content",
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

    def request(self, gate=None):
        gate = gate or self.gate()
        nested_gate = gate.gate_result
        assert nested_gate is not None
        return create_sandbox_artifact_request(
            run_id="step-15-run",
            sandbox_request_id="step-15-sandbox-request",
            sandbox_result_id="step-15-sandbox-result",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path="reports/step15.txt",
            content_text=CONTENT,
            requested_by="human-reviewer-step-15",
            human_approved=True,
            dry_run_trace_id="step-15-dry-run-trace",
            audit_event_id=nested_gate.audit_event_id or "audit-event-step-15",
            approval_decision_id=nested_gate.approval_decision_id or "approval-decision-step-15",
            sandbox_policy_decision_id="step-15-sandbox-policy-decision",
            contract_audit_event_id=nested_gate.audit_event_id or "audit-event-step-15",
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
