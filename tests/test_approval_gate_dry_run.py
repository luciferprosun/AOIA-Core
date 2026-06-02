from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.safety import approval_gate
from runtime.safety.approval_gate import evaluate_approval
from runtime.schemas.approval_decision import ApprovalDecision
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
        proposal = self.make_proposal(command="ls -la", classification="safe")
        before = proposal.to_dict()
        decision = evaluate_approval(
            proposal
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.approval_state, "not_required")
        self.assertTrue(decision.dry_run)
        self.assertFalse(decision.requires_human_review)
        self.assertFalse(decision.execution_permitted)
        self.assertEqual(before, proposal.to_dict())

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
        self.assertFalse(decision.execution_permitted)

    def test_dangerous_command_proposal_is_not_allowed(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="rm -rf /", classification="dangerous")
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.approval_state, "requires_human_review")
        self.assertTrue(decision.requires_human_review)
        self.assertFalse(decision.execution_permitted)

    def test_unknown_command_proposal_requires_human_review(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="custom-tool --mode ???", classification="unknown")
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.approval_state, "requires_human_review")
        self.assertTrue(decision.requires_human_review)
        self.assertFalse(decision.execution_permitted)

    def test_non_dry_run_proposal_is_blocked_even_if_safe(self) -> None:
        decision = evaluate_approval(
            self.make_proposal(command="ls -la", classification="safe", dry_run=False)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.approval_state, "requires_human_review")
        self.assertTrue(decision.requires_human_review)
        self.assertIn("non-dry-run", decision.reason)
        self.assertFalse(decision.dry_run)
        self.assertFalse(decision.execution_permitted)

    def test_invalid_classification_is_treated_as_requires_review(self) -> None:
        proposal = self.make_proposal(command="ls -la", classification="safe")
        object.__setattr__(proposal, "classification", "not-a-real-label")
        decision = evaluate_approval(proposal)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.approval_state, "requires_human_review")
        self.assertTrue(decision.requires_human_review)
        self.assertFalse(decision.execution_permitted)
        self.assertIn("unknown or invalid classification", decision.reason)

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
        self.assertFalse(decision.execution_permitted)

    def test_approval_decision_is_frozen(self) -> None:
        decision = ApprovalDecision(
            allowed=True,
            approval_state="not_required",
            reason="shape test",
            dry_run=True,
            requires_human_review=False,
        )
        with self.assertRaises(FrozenInstanceError):
            decision.allowed = False

    def test_approval_decision_rejects_execution_permitted_true(self) -> None:
        with self.assertRaises(ValueError):
            ApprovalDecision(
                allowed=False,
                approval_state="requires_human_review",
                reason="shape test",
                dry_run=True,
                requires_human_review=True,
                execution_permitted=True,
            )

    def test_evaluate_approval_rejects_invalid_types(self) -> None:
        for value in (None, {}, "ls -la"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    evaluate_approval(value)

    def test_approval_gate_does_not_expose_evaluate_command_text(self) -> None:
        self.assertFalse(hasattr(approval_gate, "evaluate_command_text"))

    def test_approval_gate_source_has_no_forbidden_strings_or_bash_parser(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "runtime"
            / "safety"
            / "approval_gate.py"
        ).read_text(encoding="utf-8")
        for needle in (
            "subprocess",
            "os.system",
            "shell=True",
            "eval(",
            "exec(",
            "importlib",
            "requests",
            "socket",
            "bash_parser",
            "shlex",
        ):
            self.assertNotIn(needle, source)

    def test_approval_decision_schema_source_has_no_forbidden_strings(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "runtime"
            / "schemas"
            / "approval_decision.py"
        ).read_text(encoding="utf-8")
        for needle in (
            "subprocess",
            "os.system",
            "shell=True",
            "eval(",
            "exec(",
            "importlib",
            "requests",
            "socket",
        ):
            self.assertNotIn(needle, source)


if __name__ == "__main__":
    unittest.main()
