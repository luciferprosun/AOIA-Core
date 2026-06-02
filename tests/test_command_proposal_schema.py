from __future__ import annotations

import unittest
from pathlib import Path
import re

from runtime.schemas.command_proposal import CommandProposal, CommandRiskLevel


class CommandProposalSchemaTests(unittest.TestCase):
    def test_valid_proposal_can_be_created(self) -> None:
        proposal = CommandProposal(
            command="git status",
            risk_level=CommandRiskLevel.SAFE,
            reason="Read-only example",
            requires_human_approval=False,
            source="unit_test",
            created_by="test_case",
        )
        self.assertEqual(proposal.command, "git status")
        self.assertEqual(proposal.risk_level, CommandRiskLevel.SAFE)
        self.assertIsInstance(proposal.proposal_id, str)

    def test_invalid_empty_command_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CommandProposal(
                command="",
                risk_level=CommandRiskLevel.UNKNOWN,
                reason="missing",
                requires_human_approval=False,
                source="unit_test",
                created_by="test_case",
            )

    def test_invalid_risk_level_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CommandProposal(
                command="git status",
                risk_level="NOT_A_LEVEL",
                reason="bad level",
                requires_human_approval=False,
                source="unit_test",
                created_by="test_case",
            )

    def test_metadata_must_be_mapping(self) -> None:
        with self.assertRaises(TypeError):
            CommandProposal(
                command="git status",
                risk_level=CommandRiskLevel.SAFE,
                reason="bad metadata",
                requires_human_approval=False,
                source="unit_test",
                created_by="test_case",
                metadata=["not", "a", "mapping"],
            )

    def test_to_dict_from_dict_round_trip_works(self) -> None:
        original = CommandProposal(
            command="chmod -R 777 /var/www",
            risk_level=CommandRiskLevel.AMBIGUOUS,
            reason="Needs review",
            requires_human_approval=True,
            source="unit_test",
            created_by="test_case",
            metadata={"ticket": "GT-RUNTIME-7B"},
            proposal_id="fixed-id",
        )
        restored = CommandProposal.from_dict(original.to_dict())
        self.assertEqual(restored.to_dict(), original.to_dict())

    def test_requires_human_approval_remains_explicit(self) -> None:
        proposal = CommandProposal(
            command="git status",
            risk_level=CommandRiskLevel.SAFE,
            reason="read-only",
            requires_human_approval=True,
            source="unit_test",
            created_by="test_case",
        )
        self.assertTrue(proposal.is_approval_required())

    def test_dangerous_proposal_requires_approval_in_example(self) -> None:
        proposal = CommandProposal(
            command="rm -rf /",
            risk_level=CommandRiskLevel.DANGEROUS,
            reason="destructive pattern",
            requires_human_approval=True,
            source="unit_test",
            created_by="test_case",
        )
        self.assertTrue(proposal.is_approval_required())

    def test_no_execution_methods_exist(self) -> None:
        proposal = CommandProposal(
            command="git status",
            risk_level=CommandRiskLevel.SAFE,
            reason="read-only",
            requires_human_approval=False,
            source="unit_test",
            created_by="test_case",
        )
        self.assertFalse(hasattr(proposal, "execute"))
        self.assertFalse(hasattr(proposal, "run"))
        self.assertFalse(hasattr(proposal, "dispatch"))
        self.assertFalse(hasattr(proposal, "apply"))

    def test_module_source_does_not_contain_forbidden_execution_strings(self) -> None:
        module_path = Path(__file__).resolve().parents[1] / "runtime" / "schemas" / "command_proposal.py"
        source = module_path.read_text(encoding="utf-8")
        forbidden_patterns = (
            r"\bsubprocess\b",
            r"\bos\.system\b",
            r"\bshell_tools\b",
            r"\bexecutor\b",
            r"\bpty\b",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, source))


if __name__ == "__main__":
    unittest.main()
