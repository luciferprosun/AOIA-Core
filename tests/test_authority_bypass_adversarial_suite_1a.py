from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety import write_sandbox_artifact
from runtime.safety.write_kill_switch import WRITES_ENABLED
from runtime.schemas import SandboxArtifactType, create_sandbox_artifact_request
from tests.canonical_human_gate_support import canonical_gate_and_artifact_request


class AuthorityBypassAdversarialSuite1ATests(unittest.TestCase):
    def test_a06_direct_writer_rejects_self_asserted_approval_fields(self) -> None:
        with TemporaryDirectory() as workspace:
            request = create_sandbox_artifact_request(
                run_id="forged-run",
                sandbox_request_id="forged-sandbox-request",
                sandbox_result_id="forged-sandbox-result",
                artifact_type=SandboxArtifactType.TEXT_REPORT,
                relative_output_path="forged.txt",
                content_text="forged payload\n",
                requested_by="unapproved-caller",
                human_approved=True,
                dry_run_trace_id="forged-dry-run-trace",
                created_at="2026-07-13T00:00:00Z",
                artifact_request_id="forged-artifact-request",
            )
            target = Path(workspace) / "forged.txt"

            result = self.write_with_enabled_switch(request, workspace)
            observed = {
                "write_attempted": result.write_attempted,
                "write_completed": result.write_completed,
                "target_exists": target.exists(),
                "target_content": target.read_text(encoding="utf-8") if target.exists() else None,
            }

            self.assertEqual(
                {
                    "write_attempted": False,
                    "write_completed": False,
                    "target_exists": False,
                    "target_content": None,
                },
                observed,
                "REAL_AUTHORITY_BYPASS_FOUND: direct writer accepted self-asserted "
                "approval/audit metadata without exact human-gate evidence",
            )

    def test_b01_human_approved_boolean_is_not_write_authority(self) -> None:
        _gate, request = canonical_gate_and_artifact_request(
            relative_output_path="boolean-forged.md",
            content_text="a boolean is not a human gate\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(request, workspace)
            self._assert_blocked_without_mutation(result, workspace, "boolean-forged.md")

    def test_b02_self_generated_ids_and_contract_metadata_are_not_authority(self) -> None:
        _gate, request = canonical_gate_and_artifact_request(
            relative_output_path="ids-forged.md",
            content_text="self-generated ids are not approval\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(request, workspace)
            self._assert_blocked_without_mutation(result, workspace, "ids-forged.md")

    def test_b03_mapping_shaped_gate_evidence_cannot_authorize_write(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="mapping-forged.md",
            content_text="mapping-shaped evidence must not write\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(
                request,
                workspace,
                approval_evidence=gate.to_dict(),
            )
            self._assert_blocked_without_mutation(result, workspace, "mapping-forged.md")

    def test_b04_fake_gate_object_cannot_authorize_write(self) -> None:
        _gate, request = canonical_gate_and_artifact_request(
            relative_output_path="fake-object.md",
            content_text="fake object must not write\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(
                request,
                workspace,
                approval_evidence=object(),
            )
            self._assert_blocked_without_mutation(result, workspace, "fake-object.md")

    def test_b05_gate_artifact_hash_mismatch_blocks_before_mutation(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="mismatched-content.md",
            content_text="content reviewed by the human\n",
        )
        replayed_request = replace(request, content_text="different content was not reviewed\n")
        replayed_request = replace(replayed_request, contract_payload_hash=replayed_request.content_hash)
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(
                replayed_request,
                workspace,
                approval_evidence=gate,
            )
            self._assert_blocked_without_mutation(result, workspace, "mismatched-content.md")
            self.assertIn("artifact hash", result.blocked_reason)

    def test_b06_canonical_gate_does_not_bypass_workspace_path_safety(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="../path-binding-escape.md",
            content_text="path safety remains independent of approval\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(
                request,
                workspace,
                approval_evidence=gate,
            )
            self._assert_blocked_without_mutation(result, workspace, "path-binding-escape.md")
            self.assertIn("path traversal", result.blocked_reason)

    def test_b07_stale_content_cannot_reuse_canonical_gate(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="stale-content.md",
            content_text="exact reviewed content\n",
        )
        stale_request = replace(request, content_text="stale replay content\n")
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(
                stale_request,
                workspace,
                approval_evidence=gate,
            )
            self._assert_blocked_without_mutation(result, workspace, "stale-content.md")

    def test_b08_exact_canonical_gate_evidence_allows_bound_write(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="canonical-positive.md",
            content_text="canonical human gate approved content\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(
                request,
                workspace,
                approval_evidence=gate,
            )
            target = Path(workspace) / "canonical-positive.md"

            self.assertEqual("WRITTEN", result.state.value)
            self.assertTrue(result.write_completed)
            self.assertEqual(request.content_hash, result.content_hash)
            self.assertEqual(request.content_text, target.read_text(encoding="utf-8"))

    def test_b09_denied_or_malformed_evidence_leaves_no_partial_files(self) -> None:
        _gate, request = canonical_gate_and_artifact_request(
            relative_output_path="no-partial-mutation.md",
            content_text="must not be partially written\n",
        )
        with TemporaryDirectory() as workspace:
            result = self.write_with_enabled_switch(request, workspace)
            self._assert_blocked_without_mutation(result, workspace, "no-partial-mutation.md")
            self.assertFalse(any(Path(workspace).rglob("*.tmp")))

    def test_b10_missing_canonical_evidence_denial_is_deterministic(self) -> None:
        _gate, request = canonical_gate_and_artifact_request(
            relative_output_path="deterministic-denial.md",
            content_text="deterministic denial\n",
        )
        observations = []
        for _ in range(2):
            with TemporaryDirectory() as workspace:
                result = self.write_with_enabled_switch(request, workspace)
                observations.append(
                    (
                        result.state.value,
                        result.blocked_reason,
                        result.write_attempted,
                        result.write_completed,
                        tuple(sorted(path.relative_to(workspace).as_posix() for path in Path(workspace).rglob("*"))),
                    )
                )
        self.assertEqual(observations[0], observations[1])

    @staticmethod
    def _assert_blocked_without_mutation(result, workspace: str, relative_path: str) -> None:
        if result.state.value != "BLOCKED":
            raise AssertionError(f"expected BLOCKED, got {result.state!r}")
        if result.write_attempted or result.write_completed:
            raise AssertionError("blocked result reported a write")
        if (Path(workspace) / relative_path).exists():
            raise AssertionError("blocked write left an artifact")
        if any(path.is_file() for path in Path(workspace).rglob("*")):
            raise AssertionError("blocked write left a file in workspace")

    @staticmethod
    def write_with_enabled_switch(request, workspace, *args, **kwargs):
        with TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            return write_sandbox_artifact(
                request,
                workspace,
                *args,
                **kwargs,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )


if __name__ == "__main__":
    unittest.main()
