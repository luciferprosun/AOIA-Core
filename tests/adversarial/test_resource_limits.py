from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.sandbox_artifact_runner import MAX_SANDBOX_ARTIFACT_BYTES, write_sandbox_artifact
from runtime.safety.sandbox_workspace import MAX_ARTIFACT_FILENAME_BYTES, MAX_ARTIFACT_PATH_DEPTH
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactState,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


class ArtifactResourceLimitsAdversarialTests(unittest.TestCase):
    def make_request(self, relative_output_path: str, content_text: str = "safe artifact\n") -> SandboxArtifactRequest:
        return create_sandbox_artifact_request(
            run_id="adversarial-resource-limits",
            sandbox_request_id="sandbox-request-resource-limits",
            sandbox_result_id="sandbox-result-resource-limits",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path=relative_output_path,
            content_text=content_text,
            requested_by="unit-test",
            human_approved=True,
            dry_run_trace_id="trace-resource-limits",
            audit_event_id="audit-resource-limits",
        )

    def test_max_artifact_size_accepted_at_exact_limit(self) -> None:
        content = "x" * MAX_SANDBOX_ARTIFACT_BYTES
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request("exact-limit.md", content), workspace)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)
            self.assertEqual(result.bytes_written, MAX_SANDBOX_ARTIFACT_BYTES)

    def test_artifact_size_one_byte_over_limit_rejected_before_write(self) -> None:
        content = "x" * (MAX_SANDBOX_ARTIFACT_BYTES + 1)
        with TemporaryDirectory() as workspace:
            target = Path(workspace) / "over-limit.md"

            result = write_sandbox_artifact(self.make_request("over-limit.md", content), workspace)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(result.write_attempted)
            self.assertFalse(target.exists())

    def test_max_path_depth_accepted_at_exact_limit(self) -> None:
        relative_path = "/".join(["d"] * (MAX_ARTIFACT_PATH_DEPTH - 1) + ["result.md"])
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request(relative_path), workspace)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)

    def test_path_depth_one_over_limit_rejected(self) -> None:
        relative_path = "/".join(["d"] * MAX_ARTIFACT_PATH_DEPTH + ["result.md"])
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request(relative_path), workspace)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertIn("artifact path depth exceeds limit", result.blocked_reason)

    def test_max_filename_byte_length_accepted_at_exact_limit(self) -> None:
        suffix = ".md"
        filename = "a" * (MAX_ARTIFACT_FILENAME_BYTES - len(suffix.encode("utf-8"))) + suffix
        self.assertEqual(len(filename.encode("utf-8")), MAX_ARTIFACT_FILENAME_BYTES)
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request(filename), workspace)

            self.assertEqual(result.state, SandboxArtifactState.WRITTEN)

    def test_filename_one_byte_over_limit_rejected(self) -> None:
        suffix = ".md"
        filename = "a" * (MAX_ARTIFACT_FILENAME_BYTES - len(suffix.encode("utf-8")) + 1) + suffix
        self.assertEqual(len(filename.encode("utf-8")), MAX_ARTIFACT_FILENAME_BYTES + 1)
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request(filename), workspace)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertIn("artifact filename exceeds byte limit", result.blocked_reason)

    def test_deeply_nested_path_is_rejected_without_creating_partial_files(self) -> None:
        relative_path = "/".join(["deep"] * 128 + ["result.md"])
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request(relative_path), workspace)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_large_payload_rejection_does_not_create_partial_files(self) -> None:
        content = "x" * (MAX_SANDBOX_ARTIFACT_BYTES * 2)
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(self.make_request("large.md", content), workspace)

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(any(Path(workspace).iterdir()))


if __name__ == "__main__":
    unittest.main()
