from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from runtime.human_decision_end_to_end_demo import (
    LocalApprovalArtifactDemoResult,
    run_local_approval_to_artifact_demo,
)
from runtime.local_visible_flow import (
    BLOCKED_APPROVAL_PATH,
    BLOCKED_CANDIDATE,
    FLOW_BLOCKED_REJECT,
    FLOW_COMPLETED,
    run_local_visible_flow,
)
from runtime.proposal_intake import UNTRUSTED


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "local_visible_flow.py"
CONTENT = "# M7-G approved local artifact\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class M7GLocalVisibleFlowTests(unittest.TestCase):
    def test_approve_produces_visible_flow_and_uses_existing_safe_path(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with patch(
                "runtime.local_visible_flow.run_local_approval_to_artifact_demo",
                wraps=run_local_approval_to_artifact_demo,
            ) as approval_flow:
                result = self.run_flow(
                    workspace,
                    audit_dir,
                    human_decision="APPROVE",
                )
            output = Path(result.artifact_path or "")
            written = output.read_text(encoding="utf-8")

        self.assertEqual(FLOW_COMPLETED, result.status)
        self.assertEqual(1, approval_flow.call_count)
        self.assertEqual(CONTENT, written)
        self.assertTrue(result.human_decision_captured)
        self.assertTrue(result.approval_decision_created)
        self.assertTrue(result.durable_handoff_complete)
        self.assertTrue(result.pre_artifact_gate_passed)
        self.assertTrue(result.artifact_write_occurred)
        self.assertEqual(ARTIFACT_HASH, result.artifact_hash)

    def test_visible_result_preserves_provenance_and_non_authority(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(workspace, audit_dir, human_decision="REJECT")

        payload = result.to_dict()
        self.assertTrue(result.candidate_id)
        self.assertTrue(result.candidate_hash)
        self.assertTrue(result.proposal_id)
        self.assertTrue(result.proposal_hash)
        self.assertTrue(result.review_packet_id)
        self.assertTrue(result.review_packet_hash)
        self.assertEqual("EXTERNAL_MODEL_CANDIDATE", result.proposal_source_type)
        self.assertEqual(result.candidate_id, result.proposal_source_label)
        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.model_output_trusted)
        self.assertFalse(result.provider_output_verified)
        self.assertFalse(result.evidence_created)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)
        self.assertFalse(result.execution_occurred)
        self.assertTrue(result.requires_human_review)
        self.assertIn("review_packet_hash", payload)

    def test_reject_never_writes_artifact(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(workspace, audit_dir, human_decision="REJECT")
            artifact_files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(FLOW_BLOCKED_REJECT, result.status)
        self.assertEqual("REJECT", result.decision)
        self.assertTrue(result.human_decision_captured)
        self.assertTrue(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], artifact_files)

    def test_stale_packet_binding_blocks_before_write(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                human_decision="APPROVE",
                current_review_packet_hash="c" * 64,
            )
            artifact_files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
        self.assertFalse(result.human_decision_captured)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], artifact_files)

    def test_mismatched_artifact_binding_blocks_before_write(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                human_decision="APPROVE",
                expected_artifact_hash="d" * 64,
            )
            artifact_files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
        self.assertTrue(result.human_decision_captured)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], artifact_files)

    def test_missing_durable_handoff_is_reported_blocked_without_write(self):
        blocked_demo = LocalApprovalArtifactDemoResult(
            status="BLOCKED_DURABLE_HANDOFF",
            demo_completed=False,
            decision="APPROVE",
            capture_created=True,
            approval_decision_created=True,
            durable_handoff_complete=False,
            pre_artifact_gate_passed=False,
            write_attempted=False,
            artifact_write_occurred=False,
            artifact_path=None,
            packet_hash="a" * 64,
            artifact_hash=ARTIFACT_HASH,
            provider_output_trusted=False,
            metadata_authority=False,
            blocking=True,
            reason="durable handoff unavailable",
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with patch(
                "runtime.local_visible_flow.run_local_approval_to_artifact_demo",
                return_value=blocked_demo,
            ):
                result = self.run_flow(
                    workspace,
                    audit_dir,
                    human_decision="APPROVE",
                )
            artifact_files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], artifact_files)

    def test_missing_candidate_text_fails_closed(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                human_decision="APPROVE",
                candidate_text="",
            )

        self.assertEqual(BLOCKED_CANDIDATE, result.status)
        self.assertFalse(result.human_decision_captured)
        self.assertFalse(result.artifact_write_occurred)

    def test_provider_and_structural_metadata_cannot_grant_authority(self):
        metadata = {
            "provider": "future-provider",
            "api": "custom-api",
            "model": "future-model",
            "tags": ["CANONICAL", "TAG_APPROVED"],
            "hats": ["HAT_APPROVED", "SAFE_FOR_RUNTIME"],
            "tetrads": ["TETRAD_APPROVED"],
            "cards": ["CARD_APPROVED"],
            "geometry": "GEOMETRY_SAFE",
        }
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                human_decision="REJECT",
                candidate_source="provider-claims-authority",
                metadata=metadata,
            )

        self.assertEqual(FLOW_BLOCKED_REJECT, result.status)
        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.provider_output_verified)
        self.assertFalse(result.evidence_created)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)
        self.assertFalse(result.artifact_write_occurred)

    def test_equivalent_inputs_produce_stable_candidate_proposal_and_packet_ids(self):
        with TemporaryDirectory() as workspace_a, TemporaryDirectory() as audit_a:
            first = self.run_flow(workspace_a, audit_a, human_decision="REJECT")
        with TemporaryDirectory() as workspace_b, TemporaryDirectory() as audit_b:
            second = self.run_flow(workspace_b, audit_b, human_decision="REJECT")

        self.assertEqual(first.candidate_id, second.candidate_id)
        self.assertEqual(first.candidate_hash, second.candidate_hash)
        self.assertEqual(first.proposal_id, second.proposal_id)
        self.assertEqual(first.proposal_hash, second.proposal_hash)
        self.assertEqual(first.review_packet_id, second.review_packet_id)
        self.assertEqual(first.review_packet_hash, second.review_packet_hash)

    def test_runtime_file_adds_no_provider_network_browser_or_shell_capability(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_imports = {
            "anthropic",
            "httpx",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        forbidden_calls = (
            "P" + "open(",
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            self.assertTrue(roots.isdisjoint(forbidden_imports))
        for forbidden_call in forbidden_calls:
            self.assertNotIn(forbidden_call, source)

    def run_flow(
        self,
        workspace: str,
        audit_dir: str,
        *,
        human_decision: str,
        **overrides,
    ):
        values = {
            "candidate_text": "Untrusted external candidate for local review.",
            "candidate_source": "local-external-source",
            "human_decision": human_decision,
            "workspace_root": workspace,
            "audit_dir": audit_dir,
            "artifact_relative_path": "reports/m7-g-result.md",
            "artifact_content": CONTENT,
            "human_actor": "human-reviewer-m7-g",
        }
        values.update(overrides)
        return run_local_visible_flow(**values)


if __name__ == "__main__":
    unittest.main()
