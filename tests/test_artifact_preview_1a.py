from __future__ import annotations

import hashlib
import inspect
import unittest

from runtime import artifact_preview
from runtime.artifact_preview import (
    ArtifactPreviewFlag,
    ArtifactPreviewRequest,
    ArtifactPreviewStatus,
    build_artifact_preview,
)


class ArtifactPreview1ATests(unittest.TestCase):
    def preview(self, **changes: object):
        values = {"target_path": "runtime/example.py", "proposed_content": "new\n"}
        values.update(changes)
        return build_artifact_preview(ArtifactPreviewRequest(**values))

    def test_clean_text_preview_is_ready_and_inert(self):
        result = self.preview()
        self.assertEqual(ArtifactPreviewStatus.PREVIEW_READY, result.status)
        self.assertEqual("runtime/example.py", result.target_path)
        self.assertFalse(result.write_performed)
        self.assertFalse(result.can_write)
        self.assertFalse(result.can_execute)
        self.assertFalse(result.can_commit)
        self.assertFalse(result.can_change_gate)

    def test_hashes_and_diff_are_stable(self):
        result = self.preview(original_content="old\n")
        self.assertEqual(hashlib.sha256(b"new\n").hexdigest(), result.proposed_sha256)
        self.assertEqual(hashlib.sha256(b"old\n").hexdigest(), result.original_sha256)
        self.assertIn("-old", result.diff_preview or "")
        self.assertIn("+new", result.diff_preview or "")
        self.assertIn(ArtifactPreviewFlag.DIFF_AVAILABLE, result.flags)

    def test_no_original_has_no_diff(self):
        result = self.preview()
        self.assertIsNone(result.diff_preview)
        self.assertIn(ArtifactPreviewFlag.DIFF_NOT_AVAILABLE, result.flags)

    def test_invalid_paths_are_rejected(self):
        cases = (
            ("/etc/passwd", ArtifactPreviewFlag.ABSOLUTE_PATH_REJECTED),
            ("../secret.txt", ArtifactPreviewFlag.PATH_TRAVERSAL_DETECTED),
            ("docs/../../secret.txt", ArtifactPreviewFlag.PATH_TRAVERSAL_DETECTED),
            ("", ArtifactPreviewFlag.TARGET_PATH_REJECTED),
            ("bad\x00name", ArtifactPreviewFlag.TARGET_PATH_REJECTED),
        )
        for path, flag in cases:
            with self.subTest(path=path):
                result = self.preview(target_path=path)
                self.assertEqual(ArtifactPreviewStatus.INVALID_TARGET, result.status)
                self.assertIn(flag, result.flags)

    def test_path_normalization(self):
        result = self.preview(target_path="docs//example.md")
        self.assertEqual("docs/example.md", result.target_path)
        self.assertIn(ArtifactPreviewFlag.TARGET_PATH_NORMALIZED, result.flags)

    def test_empty_content_is_invalid_and_large_content_is_only_flagged(self):
        empty = self.preview(proposed_content="")
        self.assertEqual(ArtifactPreviewStatus.INVALID_CONTENT, empty.status)
        self.assertIn(ArtifactPreviewFlag.EMPTY_CONTENT, empty.flags)
        large = self.preview(proposed_content="x" * 1_000_001)
        self.assertIn(ArtifactPreviewFlag.LARGE_CONTENT_WARNING, large.flags)
        self.assertFalse(large.write_performed)

    def test_untrusted_provider_and_critic_warning_require_review(self):
        for changes, expected_flag in (
            ({"provider_output_trust": "UNTRUSTED"}, ArtifactPreviewFlag.PROVIDER_OUTPUT_UNTRUSTED),
            ({"critic_verdict": "BLOCK"}, ArtifactPreviewFlag.CRITIC_WARNING_PRESENT),
            ({"critic_verdict": "warning: check output"}, ArtifactPreviewFlag.CRITIC_WARNING_PRESENT),
        ):
            with self.subTest(changes=changes):
                result = self.preview(**changes)
                self.assertTrue(result.human_review_required)
                self.assertIn(expected_flag, result.flags)
                self.assertIn(ArtifactPreviewFlag.HUMAN_REVIEW_REQUIRED, result.flags)

    def test_preview_id_is_deterministic_and_diff_is_bounded(self):
        request = ArtifactPreviewRequest("README.md", "new\n" * 1000, "old\n" * 1000)
        first = build_artifact_preview(request)
        second = build_artifact_preview(request)
        self.assertEqual(first.preview_id, second.preview_id)
        self.assertLessEqual(len(first.diff_preview or ""), 12_100)
        self.assertIn("truncated", first.summary.casefold())

    def test_module_has_no_forbidden_runtime_integrations(self):
        source = inspect.getsource(artifact_preview)
        forbidden = (
            "subprocess", "os.getenv", "os.environ", "open(", ".write(",
            "requests", "urllib", "httpx", "boto3", "openai", "anthropic",
            "git ", "api_key", "evaluate_pre_artifact_approval_gate",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source.casefold())


if __name__ == "__main__":
    unittest.main()
