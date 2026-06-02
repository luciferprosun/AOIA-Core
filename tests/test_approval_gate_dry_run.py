from __future__ import annotations

import unittest
from pathlib import Path

from runtime.safety.approval_gate import ApprovalDecision, evaluate_approval, evaluate_command_text
from runtime.schemas.command_proposal import CommandProposal


class ApprovalGateDryRunTests(unittest.TestCase):
    def make_proposal(
        self,
        *,
        command: str,
        classification: str,
        dry_run: bool = True,
        approval_state: str | None = None,
    ) -> CommandProposal:
        return CommandProposal(
            raw_command=command,
            normalized_command=command,
            tokens=tuple(command.split()),
            classification=classification,
            approval_state=approval_state,
            reason="unit_test",
            source="test",
            created_by="tests.test_approval_gate_dry_run",
            dry_run=dry_run,
        )

    def test_safe_command_proposal_is_allowed_as_dry_run(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="ls -la", classification="safe")
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.approval_state, "not_required")
        self.assertTrue(decision.dry_run)
        self.assertFalse(decision.requires_human_review)

    def test_ambiguous_command_proposal_requires_human_review(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(
                command="echo hello && echo world",
                classification="ambiguous",
            )
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.approval_state, "requires_human_review")
        self.assertTrue(decision.requires_human_review)

    def test_dangerous_command_proposal_is_not_allowed(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="rm -rf /", classification="dangerous")
        )
        self.assertFalse(decision.allowed)
        self.assertIn(decision.approval_state, {"requires_human_review", "denied"})
        self.assertTrue(decision.requires_human_review)

    def test_unknown_command_proposal_requires_human_review(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="custom-tool --mode ???", classification="unknown")
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.approval_state, "requires_human_review")
        self.assertTrue(decision.requires_human_review)

    def test_non_dry_run_proposal_is_blocked_even_if_safe(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="ls -la", classification="safe", dry_run=False)
        )
        self.assertFalse(decision.allowed)
        self.assertIn(decision.approval_state, {"requires_human_review", "denied"})
        self.assertTrue(decision.requires_human_review)
        self.assertIn("non-dry-run", decision.reason)
        self.assertTrue(decision.dry_run)

    def test_evaluate_command_text_safe_command_returns_allowed_dry_run(self) -> None:
        decision = evaluate_command_text("ls -la")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.dry_run)
        self.assertEqual(decision.approval_state, "not_required")

    def test_evaluate_command_text_sudo_requires_review(self) -> None:
        decision = evaluate_command_text("sudo apt update")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_human_review)

    def test_evaluate_command_text_rm_rf_root_requires_review(self) -> None:
        decision = evaluate_command_text("rm -rf /")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_human_review)

    def test_approval_decision_is_data_only(self) -> None:
        decision = ApprovalDecision(
            allowed=True,
            approval_state="not_required",
            reason="shape test",
            dry_run=True,
            requires_human_review=False,
        )
        self.assertFalse(hasattr(decision, "execute"))
        self.assertFalse(hasattr(decision, "run"))
        self.assertFalse(hasattr(decision, "dispatch"))

    def test_approval_gate_source_has_no_forbidden_execution_strings(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "runtime"
            / "safety"
            / "approval_gate.py"
        ).read_text(encoding="utf-8")
        for needle in ("subprocess", "os.system", "shell=True", "eval(", "exec("):
            self.assertNotIn(needle, source)


if __name__ == "__main__":
    unittest.main()
