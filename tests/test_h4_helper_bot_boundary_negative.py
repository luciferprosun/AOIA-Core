"""
RED-1-C diagnostic negative boundary tests.
These tests do not implement helper bots.
They check whether helper-bot-style proposal data can reach dangerous surfaces.
If a dangerous surface is reachable, the test should expose the gap.
This task must not patch runtime code.
"""

from __future__ import annotations

import builtins
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.provider_audit import ProviderAuditEvent
from runtime.schemas.chat4_agentic_proposals import (
    Chat4CanonicalStatus,
    Chat4HatTarget,
    Chat4VerificationStatus,
    HatKnowledgeCandidate,
    HatUpdateProposal,
)


def helper_bot_proposal() -> dict[str, object]:
    return {
        "source": "helper_bot",
        "execution_permitted": False,
        "human_review_required": True,
        "canonical": False,
        "canonical_status": "NOT_CANONICAL",
        "provider_output_trusted": False,
        "requested_action": "shell_execute",
        "command": "sudo apt install curl",
    }


def helper_hat_update_proposal() -> HatUpdateProposal:
    return HatUpdateProposal(
        update_id="red1c-update-1",
        target_hat=Chat4HatTarget.HAT_001_BASH_SAFETY,
        target_record_id="record-1",
        proposed_diff_text="+ helper-bot draft only; not executable",
        rationale="Diagnostic proposal construction only.",
        risk_class="review_required",
        source_ids=("source-1",),
    )


class H4HelperBotBoundaryNegativeTests(unittest.TestCase):
    def test_helper_bot_proposal_fixture_is_explicitly_non_executing(self) -> None:
        proposal = helper_bot_proposal()

        self.assertEqual("helper_bot", proposal["source"])
        self.assertFalse(proposal["execution_permitted"])
        self.assertTrue(proposal["human_review_required"])
        self.assertFalse(proposal["canonical"])
        self.assertEqual("NOT_CANONICAL", proposal["canonical_status"])
        self.assertFalse(proposal["provider_output_trusted"])
        self.assertEqual("shell_execute", proposal["requested_action"])
        self.assertEqual("sudo apt install curl", proposal["command"])

    def test_no_direct_shell_execution_from_helper_bot_schema_construction(self) -> None:
        with patch.object(subprocess, "run") as run_mock, patch.object(os, "system") as system_mock:
            proposal = helper_bot_proposal()
            schema_object = helper_hat_update_proposal()

        self.assertEqual("sudo apt install curl", proposal["command"])
        self.assertFalse(schema_object.execution_permitted)
        run_mock.assert_not_called()
        system_mock.assert_not_called()

    def test_provider_audit_rejects_trusted_output_or_canonical_promotion(self) -> None:
        base = {
            "event_id": "red1c-provider-audit",
            "timestamp_utc": "2026-06-09T12:00:00Z",
            "provider_id": "helper-bot",
            "model_id": "not-called",
            "status": "CALL_BLOCKED",
            "reason": "diagnostic boundary check",
        }

        with self.assertRaises(ValueError):
            ProviderAuditEvent(**base, provider_output_trusted=True)

        with self.assertRaises(ValueError):
            ProviderAuditEvent(**base, canonical_promotion_triggered=True)

    def test_browser_web_reader_modules_are_not_imported_for_helper_bot_proposal_data(self) -> None:
        browser_modules = {
            "runtime.tools.browser_tools",
            "runtime.tools.web_reader",
            "runtime.tools.browser",
            "playwright",
            "selenium",
        }
        before = browser_modules.intersection(sys.modules)

        proposal = helper_bot_proposal()
        schema_object = helper_hat_update_proposal()

        after = browser_modules.intersection(sys.modules)
        exposed_browser_file = Path("runtime/tools/browser_tools.py").exists()
        exposed_web_reader_file = Path("runtime/tools/web_reader.py").exists()

        self.assertFalse(before, f"browser modules already imported before diagnostic check: {sorted(before)}")
        self.assertFalse(after, f"helper-bot proposal data imported browser modules: {sorted(after)}")
        self.assertEqual("helper_bot", proposal["source"])
        self.assertFalse(schema_object.execution_permitted)
        self.assertTrue(
            exposed_browser_file or exposed_web_reader_file,
            "expected RED-1 exposed browser/web-reader surface files to remain visible for audit",
        )

    def test_file_write_delete_primitives_are_not_touched_by_helper_bot_proposal_data(self) -> None:
        with (
            patch.object(Path, "write_text") as write_text_mock,
            patch.object(Path, "unlink") as unlink_mock,
            patch.object(shutil, "move") as move_mock,
            patch.object(shutil, "rmtree") as rmtree_mock,
            patch.object(builtins, "open") as open_mock,
        ):
            proposal = helper_bot_proposal()
            schema_object = helper_hat_update_proposal()

        self.assertFalse(proposal["execution_permitted"])
        self.assertFalse(schema_object.automatic_commit_permitted)
        write_text_mock.assert_not_called()
        unlink_mock.assert_not_called()
        move_mock.assert_not_called()
        rmtree_mock.assert_not_called()
        open_mock.assert_not_called()

    def test_canonical_promotion_is_rejected_or_remains_not_canonical(self) -> None:
        proposal = HatKnowledgeCandidate(
            candidate_id="red1c-candidate-1",
            hat_target=Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
            domain_tag="python",
            title="Helper-bot draft candidate",
            inert_content_text="Draft text only.",
            source_ids=("source-1",),
            model_name="not-called",
            created_utc="2026-06-09T12:00:00Z",
        )

        self.assertFalse(proposal.execution_permitted)
        self.assertTrue(proposal.human_review_required)
        self.assertEqual(Chat4CanonicalStatus.NOT_CANONICAL, proposal.canonical_status)
        self.assertEqual(Chat4VerificationStatus.UNVERIFIED, proposal.verification_status)

        with self.assertRaises(ValueError):
            HatKnowledgeCandidate(
                candidate_id="red1c-candidate-2",
                hat_target=Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
                domain_tag="python",
                title="Invalid promoted helper-bot draft",
                inert_content_text="Draft text only.",
                source_ids=("source-1",),
                model_name="not-called",
                created_utc="2026-06-09T12:00:00Z",
                canonical_status="CANONICAL",
            )

    def test_no_git_mutation_from_helper_bot_schema_construction(self) -> None:
        with patch.object(subprocess, "run") as run_mock:
            proposal = helper_bot_proposal()
            schema_object = helper_hat_update_proposal()

        self.assertFalse(proposal["execution_permitted"])
        self.assertFalse(schema_object.automatic_commit_permitted)
        run_mock.assert_not_called()
        attempted_commands = [
            " ".join(str(part) for part in call.args[0])
            for call in run_mock.call_args_list
            if call.args and isinstance(call.args[0], (list, tuple))
        ]
        self.assertFalse(
            any(command.startswith(("git add", "git commit", "git push")) for command in attempted_commands),
            f"helper-bot proposal path attempted git mutation: {attempted_commands}",
        )


if __name__ == "__main__":
    unittest.main()
