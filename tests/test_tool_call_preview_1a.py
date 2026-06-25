from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.schemas.tool_call_preview import (
    ToolCallPreviewFlag,
    ToolCallPreviewRequest,
    ToolCallPreviewStatus,
    build_tool_call_preview,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_CALL_PREVIEW = REPO_ROOT / "runtime" / "schemas" / "tool_call_preview.py"


class ToolCallPreview1ATests(unittest.TestCase):
    def test_basic_preview_is_created_deterministically(self):
        first = self.preview()
        second = self.preview()

        self.assertEqual(first.preview_hash, second.preview_hash)
        self.assertEqual(first.preview_id, second.preview_id)
        self.assertEqual("tool-call-preview-" + first.preview_hash[:24], first.preview_id)
        self.assertEqual("AOIA_TOOL_CALL_PREVIEW_1A", first.schema_version)
        self.assertEqual("candidate.tool", first.proposed_tool_name)
        self.assertEqual({"path": "README.md"}, first.proposed_arguments)
        self.assertEqual(ToolCallPreviewStatus.REVIEW_REQUIRED, first.status)
        self.assertIn(ToolCallPreviewFlag.UNKNOWN_TOOL_NAME, first.flags)

    def test_different_arguments_change_argument_and_preview_hashes(self):
        first = self.preview(arguments={"path": "README.md"})
        second = self.preview(arguments={"path": "docs/example.md"})

        self.assertNotEqual(first.argument_hash, second.argument_hash)
        self.assertNotEqual(first.preview_hash, second.preview_hash)
        self.assertNotEqual(first.preview_id, second.preview_id)

    def test_arguments_are_inert_data_only(self):
        preview = self.preview(arguments={"command": "echo only data", "count": 2})

        self.assertEqual({"command": "echo only data", "count": 2}, preview.proposed_arguments)
        self.assertFalse(preview.tool_called)
        self.assert_all_authority_false(preview)

    def test_unknown_plain_tool_name_is_review_required_not_executable(self):
        preview = self.preview(tool_name="unknown_plain_tool")

        self.assertEqual(ToolCallPreviewStatus.REVIEW_REQUIRED, preview.status)
        self.assertIn(ToolCallPreviewFlag.UNKNOWN_TOOL_NAME, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_empty_tool_name_is_invalid(self):
        preview = self.preview(tool_name="")

        self.assertEqual(ToolCallPreviewStatus.INVALID_TOOL_NAME, preview.status)
        self.assertIn(ToolCallPreviewFlag.UNSAFE_TOOL_NAME, preview.flags)
        self.assert_all_authority_false(preview)

    def test_dangerous_tool_names_are_blocked_or_flagged(self):
        unsafe_names = (
            "rm -rf /",
            "../tool",
            "/bin/sh",
            "python -c",
            "curl http://example.com",
        )
        for tool_name in unsafe_names:
            with self.subTest(tool_name=tool_name):
                preview = self.preview(tool_name=tool_name)

                self.assertEqual(ToolCallPreviewStatus.BLOCKED_UNSAFE_TOOL_NAME, preview.status)
                self.assertIn(ToolCallPreviewFlag.UNSAFE_TOOL_NAME, preview.flags)
                self.assertTrue(preview.human_review_required)
                self.assert_all_authority_false(preview)

    def test_suspicious_arguments_are_flagged_not_executed(self):
        suspicious_values = (
            "rm -rf",
            "curl",
            "wget",
            "subprocess",
            "os.system",
            "$OPENAI_API_KEY",
            "api_key",
            "secret",
            "token",
        )
        for value in suspicious_values:
            with self.subTest(value=value):
                preview = self.preview(arguments={"value": value})

                self.assertIn(ToolCallPreviewFlag.SUSPICIOUS_ARGUMENTS, preview.flags)
                self.assertTrue(preview.human_review_required)
                self.assert_all_authority_false(preview)

    def test_untrusted_provider_output_requires_review(self):
        preview = self.preview(provider_output_trust="UNTRUSTED_PROVIDER_OUTPUT")

        self.assertIn(ToolCallPreviewFlag.PROVIDER_OUTPUT_UNTRUSTED, preview.flags)
        self.assertIn(ToolCallPreviewFlag.HUMAN_REVIEW_REQUIRED, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_critic_warning_block_reject_requires_review(self):
        for verdict in ("warning: check", "BLOCK this", "reject suggested"):
            with self.subTest(verdict=verdict):
                preview = self.preview(critic_verdict=verdict)

                self.assertIn(ToolCallPreviewFlag.CRITIC_WARNING_PRESENT, preview.flags)
                self.assertTrue(preview.human_review_required)
                self.assert_all_authority_false(preview)

    def test_authority_claims_cannot_enable_authority_fields(self):
        preview = self.preview(
            authority_claims={
                "can_execute": True,
                "tool_allowed": True,
                "approval_granted": True,
            }
        )
        replaced = replace(
            preview,
            tool_called=True,
            can_call_tool=True,
            can_execute=True,
            can_write=True,
            can_commit=True,
            can_change_approval_gate=True,
            can_change_policy=True,
            can_access_network=True,
            can_read_env=True,
            can_load_api_key=True,
        )

        self.assertIn(ToolCallPreviewFlag.SUSPICIOUS_AUTHORITY_CLAIM, preview.flags)
        self.assert_all_authority_false(preview)
        self.assert_all_authority_false(replaced)

    def test_source_action_proposal_metadata_is_not_authority(self):
        preview = self.preview(
            source_action_proposal_id="action-proposal-example",
            source_action_proposal_hash="a" * 64,
        )

        self.assertEqual("action-proposal-example", preview.source_action_proposal_id)
        self.assertEqual("a" * 64, preview.source_action_proposal_hash)
        self.assertIn(ToolCallPreviewFlag.ACTION_PROPOSAL_METADATA_ONLY, preview.flags)
        self.assert_all_authority_false(preview)

    def test_malformed_arguments_are_invalid_and_inert(self):
        preview = self.preview(arguments={"bad": object()})

        self.assertEqual(ToolCallPreviewStatus.INVALID_ARGUMENTS, preview.status)
        self.assertIn(ToolCallPreviewFlag.SUSPICIOUS_ARGUMENTS, preview.flags)
        self.assertEqual({}, preview.proposed_arguments)
        self.assert_all_authority_false(preview)

    def test_no_filesystem_writes_occur(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            _preview = self.preview(arguments={"path": str(Path(workspace) / "result.txt")})
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_static_forbidden_imports_and_capabilities(self):
        forbidden_modules = {
            "subprocess",
            "os",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "http.client",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "git",
            "dotenv",
            "runtime.tool_registry",
            "runtime.intent_router",
            "runtime.tool_call_preview_dispatcher",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.human_decision_gate_integration",
        }
        forbidden_text = (
            "subprocess",
            "os.system",
            "popen",
            "socket",
            "requests",
            "urllib",
            "http.client",
            "open(",
            ".write(",
            "shutil",
            "webbrowser",
            "playwright",
            "selenium",
            "os.environ",
            "getenv(",
        )
        source = TOOL_CALL_PREVIEW.read_text(encoding="utf-8")
        lowered = source.casefold()
        for term in forbidden_text:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for module_name in imports:
            with self.subTest(module_name=module_name):
                self.assertFalse(
                    any(
                        module_name == forbidden
                        or module_name.startswith(forbidden + ".")
                        for forbidden in forbidden_modules
                    )
                )

    def test_no_registry_dispatch_provider_or_action_mutation_terms(self):
        source = TOOL_CALL_PREVIEW.read_text(encoding="utf-8").casefold()
        forbidden_terms = (
            "toolregistry",
            "tool_registry",
            "intentrouter",
            "intent_router",
            "dispatcher",
            "dispatch(",
            "call_provider",
            "controlled_writer",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def preview(
        self,
        *,
        tool_name: str = "candidate.tool",
        arguments=None,
        provider_output_trust: str | None = None,
        critic_verdict: str | None = None,
        source_action_proposal_id: str | None = None,
        source_action_proposal_hash: str | None = None,
        authority_claims=None,
    ):
        return build_tool_call_preview(
            ToolCallPreviewRequest(
                proposed_tool_name=tool_name,
                proposed_tool_namespace="candidate",
                proposed_arguments={"path": "README.md"} if arguments is None else arguments,
                source_action_proposal_id=source_action_proposal_id,
                source_action_proposal_hash=source_action_proposal_hash,
                provider_output_trust=provider_output_trust,
                critic_verdict=critic_verdict,
                authority_claims=authority_claims,
            )
        )

    def assert_all_authority_false(self, preview):
        authority_fields = (
            "tool_called",
            "can_call_tool",
            "can_execute",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        )
        for field_name in authority_fields:
            with self.subTest(field_name=field_name):
                self.assertFalse(getattr(preview, field_name))


if __name__ == "__main__":
    unittest.main()
