from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.action_proposal_policy import (
    ActionProposalExecutionBlockedError,
    ProviderGeneratedActionBlockedError,
    assert_action_proposal_cannot_execute,
    assert_action_proposal_is_inert,
)
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalRisk,
    ActionProposalRiskFlag,
    ActionProposalSourceTrust,
    ActionProposalStatus,
    ActionProposalType,
    build_action_proposal,
    create_inert_action_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTION_PROPOSAL = REPO_ROOT / "runtime" / "schemas" / "action_proposal.py"


class ActionProposal1ATests(unittest.TestCase):
    def test_existing_m3_action_proposal_api_still_works(self):
        proposal = create_inert_action_proposal(
            proposal_type=ActionProposalType.SHELL_COMMAND,
            title="Legacy shell proposal",
            description="Legacy API remains inert.",
            proposed_by="test",
            exact_payload="echo data-only",
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(ActionProposalType.SHELL_COMMAND, proposal.proposal_type)
        self.assertEqual(ActionProposalRisk.FORBIDDEN, proposal.risk)
        self.assertFalse(proposal.execution_permitted)
        self.assertFalse(proposal.execution_implemented)
        with self.assertRaises(ActionProposalExecutionBlockedError):
            assert_action_proposal_cannot_execute(proposal)

    def test_step11_api_fields_exist_and_are_deterministic(self):
        first = self.build_file_write()
        second = self.build_file_write()

        self.assertEqual(first.proposal_hash, second.proposal_hash)
        self.assertEqual(first.proposal_id, second.proposal_id)
        self.assertEqual("action-proposal-" + first.proposal_hash[:24], first.proposal_id)
        self.assertEqual("AOIA_ACTION_PROPOSAL_1A", first.schema_version)
        self.assertEqual(ActionProposalStatus.PROPOSAL_READY, first.status)
        self.assertEqual(ActionProposalKind.FILE_WRITE, first.action_kind)
        self.assertEqual(("docs/example.md",), first.target_refs)
        self.assertEqual({"content": "hello"}, first.normalized_arguments)
        self.assertTrue(first.human_review_required)

    def test_candidate_tool_id_is_opaque_metadata_only(self):
        proposal = self.build_file_write(candidate_tool_id="provider_made_up_tool_xyz")

        self.assertEqual("provider_made_up_tool_xyz", proposal.candidate_tool_id)
        self.assertFalse(proposal.execution_permitted)
        self.assertFalse(proposal.execution_implemented)
        self.assertFalse(proposal.human_approved)
        self.assert_no_authority_methods(proposal)

    def test_provider_untrusted_source_is_metadata_only_and_review_required(self):
        proposal = self.build_file_write(source_trust=ActionProposalSourceTrust.PROVIDER_UNTRUSTED)

        self.assertEqual(ActionProposalSourceTrust.PROVIDER_UNTRUSTED, proposal.source_trust)
        self.assertIn(ActionProposalRiskFlag.PROVIDER_OUTPUT_UNTRUSTED, proposal.risk_flags)
        self.assertIn(ActionProposalRiskFlag.HUMAN_REVIEW_REQUIRED, proposal.risk_flags)
        self.assertTrue(proposal.provider_generated)
        self.assertFalse(proposal.human_approved)
        with self.assertRaises(ProviderGeneratedActionBlockedError):
            assert_action_proposal_is_inert(proposal)

    def test_file_write_gets_filesystem_flags_but_cannot_write(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            proposal = self.build_file_write(target_refs=("runtime/example.py",))
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)
        self.assertIn(ActionProposalRiskFlag.FILESYSTEM_WRITE, proposal.risk_flags)
        self.assertIn(ActionProposalRiskFlag.MUTATING_ACTION, proposal.risk_flags)
        self.assertFalse(proposal.execution_permitted)
        self.assert_no_authority_methods(proposal)

    def test_shell_command_and_test_run_get_process_flags_but_cannot_execute(self):
        for action_kind in (ActionProposalKind.SHELL_COMMAND, ActionProposalKind.TEST_RUN):
            with self.subTest(action_kind=action_kind):
                proposal = build_action_proposal(
                    ActionProposalRequest(
                        action_kind=action_kind,
                        target_refs=("tests/example.py",),
                        arguments={"command": "python -m unittest"},
                        source_trust=ActionProposalSourceTrust.USER_SUPPLIED,
                    )
                )

                self.assertIn(ActionProposalRiskFlag.PROCESS_EXECUTION, proposal.risk_flags)
                self.assertFalse(proposal.execution_permitted)
                with self.assertRaises(ActionProposalExecutionBlockedError):
                    assert_action_proposal_cannot_execute(proposal)

    def test_git_commit_and_push_are_separate_metadata_kinds(self):
        commit = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.GIT_COMMIT,
                target_refs=("runtime/example.py",),
                arguments={"message": "commit"},
            )
        )
        push = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.GIT_PUSH,
                target_refs=("runtime/example.py",),
                arguments={"remote": "origin"},
            )
        )

        self.assertEqual(ActionProposalKind.GIT_COMMIT, commit.action_kind)
        self.assertEqual(ActionProposalKind.GIT_PUSH, push.action_kind)
        self.assertNotEqual(commit.proposal_hash, push.proposal_hash)
        self.assertIn(ActionProposalRiskFlag.GIT_OPERATION, commit.risk_flags)
        self.assertIn(ActionProposalRiskFlag.GIT_OPERATION, push.risk_flags)
        self.assert_no_authority_methods(commit)
        self.assert_no_authority_methods(push)

    def test_package_install_and_browser_actions_are_not_yet_governed_metadata(self):
        cases = (
            (
                ActionProposalKind.PACKAGE_INSTALL,
                (ActionProposalRiskFlag.PACKAGE_INSTALL, ActionProposalRiskFlag.NETWORK_RELATED),
            ),
            (
                ActionProposalKind.BROWSER_ACTION,
                (ActionProposalRiskFlag.BROWSER_RELATED, ActionProposalRiskFlag.NOT_YET_GOVERNED),
            ),
        )
        for action_kind, expected_flags in cases:
            with self.subTest(action_kind=action_kind):
                proposal = build_action_proposal(
                    ActionProposalRequest(
                        action_kind=action_kind,
                        target_refs=("README.md",),
                        arguments={"name": "data-only"},
                    )
                )

                for flag in expected_flags:
                    self.assertIn(flag, proposal.risk_flags)
                self.assertFalse(proposal.execution_permitted)
                self.assert_no_authority_methods(proposal)

    def test_unknown_action_kind_is_unsupported_review_required_metadata(self):
        proposal = build_action_proposal(
            ActionProposalRequest(
                action_kind="made_up_action",
                target_refs=("README.md",),
                arguments={"x": 1},
            )
        )

        self.assertEqual(ActionProposalStatus.UNSUPPORTED_ACTION_KIND, proposal.status)
        self.assertEqual(ActionProposalKind.UNKNOWN, proposal.action_kind)
        self.assertIn(ActionProposalRiskFlag.UNKNOWN_ACTION_KIND, proposal.risk_flags)
        self.assertIn(ActionProposalRiskFlag.HUMAN_REVIEW_REQUIRED, proposal.risk_flags)

    def test_invalid_targets_fail_closed_as_metadata(self):
        invalid_targets = (
            "/etc/passwd",
            "../secret.txt",
            "docs/../../secret.txt",
            "",
            "bad\x00path",
        )
        for target in invalid_targets:
            with self.subTest(target=target):
                proposal = self.build_file_write(target_refs=(target,))

                self.assertEqual(ActionProposalStatus.INVALID_TARGET, proposal.status)
                self.assertIn(ActionProposalRiskFlag.INVALID_TARGET, proposal.risk_flags)
                self.assertFalse(proposal.execution_permitted)
                self.assertFalse(proposal.human_approved)

    def test_malformed_arguments_fail_closed(self):
        proposal = build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=("README.md",),
                arguments={"bad": object()},
            )
        )

        self.assertEqual(ActionProposalStatus.MALFORMED_REQUEST, proposal.status)
        self.assertEqual({}, proposal.normalized_arguments)
        self.assertIn(ActionProposalRiskFlag.HUMAN_REVIEW_REQUIRED, proposal.risk_flags)

    def test_import_has_no_side_effect_filesystem_writes(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            __import__("runtime.schemas.action_proposal")
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
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "git",
            "runtime.tool_registry",
            "runtime.intent_router",
            "runtime.tool_call_preview",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.human_decision_gate_integration",
        }
        forbidden_call_terms = (
            "open(",
            ".write(",
            "system(",
            "popen(",
            "eval(",
            "exec(",
            "os.environ",
            "getenv(",
        )
        source = ACTION_PROPOSAL.read_text(encoding="utf-8")
        lowered = source.casefold()
        for term in forbidden_call_terms:
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

    def build_file_write(
        self,
        *,
        candidate_tool_id: str | None = "candidate.writer",
        source_trust: ActionProposalSourceTrust = ActionProposalSourceTrust.USER_SUPPLIED,
        target_refs: tuple[str, ...] = ("docs/example.md",),
    ):
        return build_action_proposal(
            ActionProposalRequest(
                action_kind=ActionProposalKind.FILE_WRITE,
                target_refs=target_refs,
                arguments={"content": "hello"},
                candidate_tool_id=candidate_tool_id,
                source_trust=source_trust,
                proposed_by="human",
                summary="Propose a file write.",
            )
        )

    def assert_no_authority_methods(self, proposal):
        forbidden_methods = (
            "execute",
            "run",
            "write",
            "commit",
            "push",
            "install",
            "approve",
            "allow",
            "deny",
            "route",
            "preview",
            "call_provider",
        )
        for method_name in forbidden_methods:
            with self.subTest(method_name=method_name):
                self.assertFalse(callable(getattr(proposal, method_name, None)))


if __name__ == "__main__":
    unittest.main()
