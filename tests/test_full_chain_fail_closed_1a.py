from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

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
    ARTIFACT_WRITTEN,
    BLOCKED_CONTROLLED_WRITE,
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    BLOCKED_WRITE_KILL_SWITCH,
)
from runtime.providers.contracts import DRY_RUN_PREVIEW, UNTRUSTED, ProviderRuntimeResult
from runtime.providers.critic import critique_provider_result
from runtime.safety.workspace_guard import validate_workspace_target_path
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED, evaluate_write_kill_switch_value
from runtime.schemas.sandbox_artifact import (
    SANDBOX_ARTIFACT_CONTRACT_VERSION,
    SandboxArtifactState,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_HASH = "a" * 64
OTHER_PACKET_HASH = "b" * 64
CONTENT = "# Full chain controlled artifact\n"
OTHER_CONTENT = "# Replayed artifact content\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
OTHER_ARTIFACT_HASH = hashlib.sha256(OTHER_CONTENT.encode("utf-8")).hexdigest()
TARGET_PATH = "reports/full-chain.txt"
RUNTIME_CHAIN_FILES = (
    REPO_ROOT / "runtime" / "providers" / "contracts.py",
    REPO_ROOT / "runtime" / "providers" / "critic.py",
    REPO_ROOT / "runtime" / "artifact_preview.py",
    REPO_ROOT / "runtime" / "control_write.py",
    REPO_ROOT / "runtime" / "human_decision_gated_artifact_write.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
    REPO_ROOT / "runtime" / "safety" / "write_kill_switch.py",
    REPO_ROOT / "runtime" / "safety" / "workspace_guard.py",
)


class FullChainFailClosed1ATests(unittest.TestCase):
    def test_happy_path_controlled_write_baseline_uses_all_safety_preconditions(self):
        provider_result = self.provider_result()
        critic = critique_provider_result(provider_result)
        preview = self.preview(critic=critic)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            workspace_guard = validate_workspace_target_path(workspace, preview.target_path)
            kill_switch = evaluate_write_kill_switch_value(WRITES_ENABLED)

            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]
            written = files[0]

            self.assertEqual(ARTIFACT_WRITTEN, result.status)
            self.assertEqual(1, len(files))
            self.assertEqual(CONTENT, written.read_text(encoding="utf-8"))
            self.assertEqual(preview.proposed_sha256, hashlib.sha256(written.read_bytes()).hexdigest())
            self.assertEqual(Path(workspace).resolve(), Path(result.artifact_path or "").resolve().parents[1])
            self.assertTrue(workspace_guard.allowed)
            self.assertTrue(kill_switch.writes_allowed)

        self.assertEqual(UNTRUSTED, provider_result.trust_status)
        self.assertFalse(critic.can_approve)
        self.assertFalse(critic.can_write)
        self.assertFalse(critic.can_execute)
        self.assertFalse(preview.write_performed)
        self.assertFalse(preview.can_write)
        self.assertFalse(kill_switch.can_write)
        self.assertFalse(kill_switch.write_authority_granted)
        self.assertFalse(workspace_guard.can_write)
        self.assertFalse(workspace_guard.write_authority_granted)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.metadata_authority)

    def test_missing_provider_critic_metadata_is_advisory_and_cannot_satisfy_gate_authority(self):
        preview = self.preview(provider_id=None, model_id=None, critic=None)
        forged_metadata_gate = {
            "decision": "APPROVE",
            "provider": "APPROVED",
            "critic": "SAFE",
            "metadata_authority": True,
            "provider_output_trusted": True,
        }

        result = self.run_chain(preview=preview, gate_result=forged_metadata_gate)

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.metadata_authority)

    def test_preview_failures_block_chain_before_write(self):
        cases = {
            "preview_status_not_ready": replace(
                self.preview(),
                status=ArtifactPreviewStatus.BLOCKED_BY_POLICY,
            ),
            "malformed_preview_hash": self.preview_with(proposed_sha256="not-a-sha256"),
            "preview_target_path_mismatch_to_traversal": self.preview_with(target_path="../escape.txt"),
            "forged_preview_authority_flag": self.preview_with(can_write=True),
        }

        for name, preview in cases.items():
            with self.subTest(name=name):
                result = self.run_chain(preview=preview)

                self.assertTrue(result.blocking)
                self.assertFalse(result.artifact_write_occurred)
                self.assertIn(result.status, {CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, BLOCKED_CONTROLLED_WRITE})

        mismatch = self.run_chain(proposed_content_text="changed after preview\n")
        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, mismatch.status)
        self.assertFalse(mismatch.artifact_write_occurred)

    def test_human_gate_failures_block_chain_before_write(self):
        valid_gate = self.gate().to_dict()
        cases = {
            "missing_gate_evidence": ({}, CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE),
            "decision_reject": (self.gate(decision="REJECT").to_dict(), CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE),
            "decision_missing": ({**valid_gate, "decision": None}, CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE),
            "approval_decision_id_missing": (
                self.gate_with_nested(approval_decision_id=""),
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
            "audit_event_id_missing": (
                self.gate_with_nested(audit_event_id=""),
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
            "durable_handoff_missing": (
                {**valid_gate, "durable_handoff_complete": False},
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
            "pre_artifact_gate_not_passed": (
                {**valid_gate, "pre_artifact_gate_passed": False},
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
            "metadata_authority_true": (
                {**valid_gate, "metadata_authority": True},
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
            "provider_output_trusted_true": (
                {**valid_gate, "provider_output_trusted": True},
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
            "artifact_write_occurred_true": (
                {**valid_gate, "artifact_write_occurred": True},
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            ),
        }

        for name, (gate_result, expected_status) in cases.items():
            with self.subTest(name=name):
                result = self.run_chain(gate_result=gate_result)

                self.assertEqual(expected_status, result.status)
                self.assertFalse(result.artifact_write_occurred)
                self.assertIn("gate", result.reason.casefold())

    def test_hash_binding_failures_block_chain(self):
        old_gate = self.gate().to_dict()
        replay_preview = self.preview(proposed_content=OTHER_CONTENT)
        cases = {
            "expected_packet_hash_mismatch": (
                {"expected_packet_hash": OTHER_PACKET_HASH},
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
            "expected_artifact_hash_mismatch": (
                {"expected_artifact_hash": OTHER_ARTIFACT_HASH},
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
            "proposed_content_changed_after_preview": (
                {"proposed_content_text": "changed after preview\n"},
                CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
            ),
            "stale_replayed_gate_for_different_artifact_hash": (
                {
                    "preview": replay_preview,
                    "proposed_content_text": OTHER_CONTENT,
                    "gate_result": old_gate,
                    "expected_artifact_hash": OTHER_ARTIFACT_HASH,
                },
                BLOCKED_STALE_OR_MISMATCHED_STATE,
            ),
        }

        for name, (kwargs, expected_status) in cases.items():
            with self.subTest(name=name):
                result = self.run_chain(**kwargs)

                self.assertEqual(expected_status, result.status)
                self.assertFalse(result.artifact_write_occurred)

    def test_kill_switch_failures_block_chain_even_with_valid_gate_and_hashes(self):
        with TemporaryDirectory() as switch_dir, TemporaryDirectory() as outside:
            switch_root = Path(switch_dir)
            cases: dict[str, tuple[Path, str | None]] = {
                "disabled": (self.write_switch(switch_dir, WRITES_DISABLED), None),
                "missing": (switch_root / "missing.state", None),
                "malformed": (self.write_switch(switch_dir, WRITES_ENABLED + "\n" + WRITES_DISABLED), None),
            }
            symlink_path = switch_root / "linked.state"
            real_outside = Path(outside) / "outside.state"
            real_outside.write_text(WRITES_ENABLED, encoding="utf-8")
            try:
                symlink_path.symlink_to(real_outside)
            except (OSError, NotImplementedError) as exc:
                symlink_path = None
                symlink_error = exc
            else:
                symlink_error = None
                cases["unsafe_symlink"] = (symlink_path, None)

            for name, (switch_path, _) in cases.items():
                with self.subTest(name=name):
                    result = self.run_chain(
                        switch_path=str(switch_path),
                        switch_dir=switch_dir,
                    )

                    self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
                    self.assertFalse(result.artifact_write_occurred)
                    self.assertIn("kill-switch", result.reason)

            if symlink_path is None:
                self.assertIsNotNone(symlink_error)

    def test_workspace_guard_failures_block_chain_and_do_not_write_outside_workspace(self):
        path_cases = {
            "absolute_target_path": "/tmp/full-chain-escape.txt",
            "parent_traversal": "../escape.txt",
            "backslash_traversal": "..\\escape.txt",
            "dot_git_path": ".git/config.txt",
        }
        for name, target_path in path_cases.items():
            with self.subTest(name=name):
                result = self.run_chain(preview=self.preview(target_path=target_path))

                self.assertTrue(result.blocking)
                self.assertFalse(result.artifact_write_occurred)
                self.assertIn(result.status, {CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, BLOCKED_CONTROLLED_WRITE})

        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            symlink_target = Path(workspace) / TARGET_PATH
            symlink_target.parent.mkdir(parents=True)
            parent_link = Path(workspace) / "linked-parent"
            directory_target = Path(workspace) / "directory.txt"
            directory_target.mkdir()
            try:
                symlink_target.symlink_to(Path(outside) / "target.txt")
                parent_link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            cases = {
                "symlink_target": (workspace, self.preview(target_path=TARGET_PATH)),
                "parent_symlink": (workspace, self.preview(target_path="linked-parent/result.txt")),
                "directory_target": (workspace, self.preview(target_path="directory.txt")),
                "workspace_escape": (workspace, self.preview(target_path="linked-parent/escape.txt")),
            }

            for name, (case_workspace, preview) in cases.items():
                with self.subTest(name=name):
                    result = self.run_chain(preview=preview, workspace=case_workspace)

                    self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
                    self.assertFalse(result.artifact_write_occurred)
                    self.assertFalse((Path(outside) / "target.txt").exists())
                    self.assertFalse((Path(outside) / "result.txt").exists())
                    self.assertFalse((Path(outside) / "escape.txt").exists())

    def test_direct_sandbox_bypass_remains_blocked_unless_existing_lower_contract_is_complete(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            valid_gate = self.gate()
            valid_request = self.sandbox_request(gate_result=valid_gate)
            forged_cases = {
                "missing_human_approval": replace(valid_request, human_approved=False),
                "missing_write_contract": replace(valid_request, artifact_write_allowed=False),
                "missing_audit": replace(valid_request, audit_event_id="", contract_audit_event_id=""),
                "invalid_contract_version": replace(valid_request, artifact_contract_version="FORGED"),
                "invalid_path": replace(valid_request, relative_output_path="../escape.txt"),
            }

            for name, request in forged_cases.items():
                with self.subTest(name=name):
                    result = write_sandbox_artifact(
                        request,
                        workspace,
                        write_kill_switch_path=str(switch_path),
                        write_kill_switch_directory=switch_dir,
                    )

                    self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                    self.assertFalse(result.write_completed)

            valid_result = write_sandbox_artifact(
                valid_request,
                workspace,
                approval_evidence=valid_gate,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(SandboxArtifactState.WRITTEN, valid_result.state)
        self.assertTrue(valid_result.write_completed)
        self.assertEqual(valid_request.content_hash, valid_result.content_hash)

    def test_stage_specific_failure_locality_uses_current_stable_status_and_reason(self):
        cases = {
            "preview": (self.run_chain(preview=replace(self.preview(), status=ArtifactPreviewStatus.BLOCKED_BY_POLICY)), "preview"),
            "gate": (self.run_chain(gate_result={}), "gate"),
            "hash": (self.run_chain(proposed_content_text="changed\n"), "hash"),
            "kill_switch": (
                self.run_chain_with_switch_value(WRITES_DISABLED),
                "kill-switch",
            ),
            "workspace": (
                self.run_chain(preview=self.preview(target_path="linked-parent/result.txt"), prepare_parent_symlink=True),
                "symlink",
            ),
        }

        expected_status = {
            "preview": CONTROL_WRITE_BLOCKED_INVALID_PREVIEW,
            "gate": CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            "hash": CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
            "kill_switch": BLOCKED_WRITE_KILL_SWITCH,
            "workspace": BLOCKED_CONTROLLED_WRITE,
        }
        for name, (result, reason_fragment) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(expected_status[name], result.status)
                self.assertFalse(result.artifact_write_occurred)
                self.assertIn(reason_fragment, result.reason.casefold())

    def test_no_new_capability_scan_for_full_chain_integration_scope(self):
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

        for path in (*RUNTIME_CHAIN_FILES, Path(__file__).resolve()):
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                scan = scan_module(path)
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

    def provider_result(self) -> ProviderRuntimeResult:
        return ProviderRuntimeResult(
            provider_id="mock_chat",
            model_id="mock-model",
            mode="dry_run",
            status=DRY_RUN_PREVIEW,
            redacted_request_preview="mock provider preview for full chain test",
            response_text=CONTENT,
            trust_status=UNTRUSTED,
        )

    def preview(
        self,
        *,
        target_path: str = TARGET_PATH,
        proposed_content: str = CONTENT,
        provider_id: str | None = "mock_chat",
        model_id: str | None = "mock-model",
        critic: Any | None = None,
    ):
        if critic is None and provider_id is not None:
            critic = critique_provider_result(self.provider_result())
        return build_artifact_preview(
            ArtifactPreviewRequest(
                target_path=target_path,
                proposed_content=proposed_content,
                artifact_kind="text",
                provider_id=provider_id,
                model_id=model_id,
                provider_output_trust=UNTRUSTED if provider_id is not None else None,
                critic_verdict=critic.verdict if critic is not None else None,
            )
        )

    def preview_with(self, **changes):
        preview = self.preview()
        for field_name, value in changes.items():
            object.__setattr__(preview, field_name, value)
        return preview

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="full-chain-run",
            sandbox_request_id="full-chain-sandbox-request",
            sandbox_result_id="full-chain-sandbox-result",
            requested_by="human-reviewer-full-chain",
            dry_run_trace_id="full-chain-dry-run",
            sandbox_policy_decision_id="full-chain-policy-decision",
        )

    def gate(
        self,
        *,
        decision: str = "APPROVE",
        packet_hash: str = PACKET_HASH,
        artifact_hash: str = ARTIFACT_HASH,
    ):
        capture = capture_human_decision_intent(
            decision=decision,
            packet_id="packet-full-chain",
            displayed_packet_hash=packet_hash,
            current_packet_hash=packet_hash,
            displayed_artifact_hash=artifact_hash,
            current_artifact_hash=artifact_hash,
            human_actor="human-reviewer-full-chain",
            reason="reviewed exact full chain artifact",
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

    def gate_with_nested(self, **nested_changes) -> dict[str, Any]:
        gate = self.gate().to_dict()
        nested = dict(gate["gate_result"])
        nested.update(nested_changes)
        gate["gate_result"] = nested
        return gate

    def sandbox_request(self, *, gate_result=None):
        nested_gate = (gate_result or self.gate()).gate_result
        assert nested_gate is not None
        return create_sandbox_artifact_request(
            run_id="full-chain-run",
            sandbox_request_id="full-chain-sandbox-request",
            sandbox_result_id="full-chain-sandbox-result",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path=TARGET_PATH,
            content_text=CONTENT,
            requested_by="human-reviewer-full-chain",
            human_approved=True,
            dry_run_trace_id="full-chain-dry-run",
            audit_event_id=nested_gate.audit_event_id or "audit-event-full-chain",
            notes="full chain direct sandbox contract",
            artifact_contract_version=SANDBOX_ARTIFACT_CONTRACT_VERSION,
            artifact_write_allowed=True,
            approval_decision_id=nested_gate.approval_decision_id or "approval-decision-full-chain",
            sandbox_policy_decision_id="full-chain-policy-decision",
            sandbox_result_state="NOT_IMPLEMENTED",
            contract_audit_event_id=nested_gate.audit_event_id or "audit-event-full-chain",
        )

    def run_chain(
        self,
        *,
        preview=None,
        proposed_content_text: str = CONTENT,
        gate_result: Any | None = None,
        expected_packet_hash: str | None = PACKET_HASH,
        expected_artifact_hash: str | None = ARTIFACT_HASH,
        switch_path: str | None = None,
        switch_dir: str | None = None,
        workspace: str | None = None,
        prepare_parent_symlink: bool = False,
    ):
        if workspace is not None:
            return self._run_chain_in_workspace(
                workspace=workspace,
                preview=preview,
                proposed_content_text=proposed_content_text,
                gate_result=gate_result,
                expected_packet_hash=expected_packet_hash,
                expected_artifact_hash=expected_artifact_hash,
                switch_path=switch_path,
                switch_dir=switch_dir,
            )

        with TemporaryDirectory() as temp_workspace, TemporaryDirectory() as outside:
            if prepare_parent_symlink:
                link = Path(temp_workspace) / "linked-parent"
                try:
                    link.symlink_to(Path(outside), target_is_directory=True)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlink creation not supported here: {exc}")
            return self._run_chain_in_workspace(
                workspace=temp_workspace,
                preview=preview,
                proposed_content_text=proposed_content_text,
                gate_result=gate_result,
                expected_packet_hash=expected_packet_hash,
                expected_artifact_hash=expected_artifact_hash,
                switch_path=switch_path,
                switch_dir=switch_dir,
            )

    def _run_chain_in_workspace(
        self,
        *,
        workspace: str,
        preview,
        proposed_content_text: str,
        gate_result: Any | None,
        expected_packet_hash: str | None,
        expected_artifact_hash: str | None,
        switch_path: str | None,
        switch_dir: str | None,
    ):
        if switch_path is None:
            with TemporaryDirectory() as temp_switch_dir:
                enabled = self.write_switch(temp_switch_dir, WRITES_ENABLED)
                return write_preview_artifact_after_human_gate(
                    preview=preview or self.preview(),
                    proposed_content_text=proposed_content_text,
                    workspace_root=workspace,
                    gate_result=self.gate() if gate_result is None else gate_result,
                    context=self.context(),
                    expected_packet_hash=expected_packet_hash,
                    expected_artifact_hash=expected_artifact_hash,
                    write_kill_switch_path=str(enabled),
                    write_kill_switch_directory=temp_switch_dir,
                )
        return write_preview_artifact_after_human_gate(
            preview=preview or self.preview(),
            proposed_content_text=proposed_content_text,
            workspace_root=workspace,
            gate_result=self.gate() if gate_result is None else gate_result,
            context=self.context(),
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=expected_artifact_hash,
            write_kill_switch_path=switch_path,
            write_kill_switch_directory=switch_dir,
        )

    def run_chain_with_switch_value(self, switch_value: str):
        with TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, switch_value)
            return self.run_chain(switch_path=str(switch_path), switch_dir=switch_dir)

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
