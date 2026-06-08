from __future__ import annotations

import unittest
from pathlib import Path

from runtime.schemas.chat4_agentic_proposals import (
    AuditTrailEntry,
    Chat4CanonicalStatus,
    Chat4HatTarget,
    Chat4ObjectType,
    Chat4ProposalStatus,
    Chat4VerificationStatus,
    ContradictionReport,
    GapReport,
    HatKnowledgeCandidate,
    HatUpdateProposal,
    ModelResearchProposal,
    ReviewerDecision,
    SourceCandidate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "runtime" / "schemas" / "chat4_agentic_proposals.py"
REPORT_PATH = PROJECT_ROOT / "docs" / "audit" / "CHAT4_INERT_PROPOSAL_SCHEMA_DEFINITION.md"


class Chat4AgenticProposalTests(unittest.TestCase):
    def _assert_common_inert_defaults(self, proposal: object) -> None:
        self.assertEqual(Chat4ProposalStatus.DRAFT, proposal.status)
        self.assertEqual(Chat4CanonicalStatus.NOT_CANONICAL, proposal.canonical_status)
        self.assertEqual(Chat4VerificationStatus.UNVERIFIED, proposal.verification_status)
        self.assertTrue(proposal.human_review_required)
        self.assertFalse(proposal.execution_permitted)
        self.assertFalse(proposal.automatic_commit_permitted)

    def test_model_research_proposal_defaults_are_inert(self) -> None:
        proposal = ModelResearchProposal(
            proposal_id="mrp-1",
            model_name="helper-model-name",
            model_version="not-called",
            hat_target=Chat4HatTarget.HAT_001_BASH_SAFETY,
            research_question="What source should a human review?",
            summary_untrusted="Untrusted model draft.",
            source_candidate_ids=("source-1",),
        )

        self._assert_common_inert_defaults(proposal)

    def test_source_candidate_defaults_are_inert(self) -> None:
        proposal = SourceCandidate(
            source_id="source-1",
            proposal_id="mrp-1",
            source_type="manual_url_reference",
            source_reference="https://example.invalid/reference",
            title="Candidate source",
            captured_utc="2026-06-08T06:00:00Z",
            capture_method="human_recorded_reference",
            content_excerpt_redacted="redacted excerpt",
            provenance_hash="sha256:not-computed-here",
        )

        self._assert_common_inert_defaults(proposal)

    def test_hat_knowledge_candidate_defaults_are_inert(self) -> None:
        proposal = HatKnowledgeCandidate(
            candidate_id="candidate-1",
            hat_target=Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
            domain_tag="python",
            title="Candidate Python note",
            inert_content_text="Text only; no execution.",
            source_ids=("source-1",),
            model_name="helper-model-name",
            created_utc="2026-06-08T06:00:00Z",
        )

        self._assert_common_inert_defaults(proposal)

    def test_hat_update_proposal_defaults_are_inert(self) -> None:
        proposal = HatUpdateProposal(
            update_id="update-1",
            target_hat=Chat4HatTarget.HAT_002_LINUX_RHCSA,
            target_record_id="record-1",
            proposed_diff_text="- old text\n+ proposed text",
            rationale="Human should review possible wording update.",
            risk_class="review_required",
            source_ids=("source-1",),
        )

        self._assert_common_inert_defaults(proposal)

    def test_contradiction_report_defaults_are_inert(self) -> None:
        proposal = ContradictionReport(
            report_id="contradiction-1",
            hat_target=Chat4HatTarget.HAT_004_BROWSER_FILE_GOVERNANCE,
            record_a_id="record-a",
            record_b_id="record-b",
            contradiction_summary="Possible policy conflict for human review.",
            evidence_excerpt_redacted="redacted evidence",
            severity="medium",
        )

        self._assert_common_inert_defaults(proposal)

    def test_gap_report_defaults_are_inert(self) -> None:
        proposal = GapReport(
            gap_id="gap-1",
            hat_target=Chat4HatTarget.HAT_001_BASH_SAFETY,
            missing_topic="shell quoting edge case",
            suggested_source_references=("source-ref-1",),
            priority="low",
        )

        self._assert_common_inert_defaults(proposal)

    def test_common_inert_overrides_are_rejected(self) -> None:
        bad_kwargs = {
            "status": Chat4ProposalStatus.UNDER_REVIEW,
            "canonical_status": Chat4CanonicalStatus.NOT_CANONICAL.value,
            "verification_status": Chat4VerificationStatus.HUMAN_REVIEWED,
            "human_review_required": False,
            "execution_permitted": True,
            "automatic_commit_permitted": True,
        }
        for field, value in bad_kwargs.items():
            with self.subTest(field=field):
                kwargs = {
                    "gap_id": "gap-1",
                    "hat_target": Chat4HatTarget.HAT_001_BASH_SAFETY,
                    "missing_topic": "topic",
                    "suggested_source_references": ("source-ref-1",),
                    "priority": "low",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    GapReport(**kwargs)

    def test_hat_knowledge_candidate_rejects_empty_source_ids(self) -> None:
        with self.assertRaises(ValueError):
            HatKnowledgeCandidate(
                candidate_id="candidate-1",
                hat_target=Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
                domain_tag="python",
                title="Candidate Python note",
                inert_content_text="Text only.",
                source_ids=(),
                model_name="helper-model-name",
                created_utc="2026-06-08T06:00:00Z",
            )

    def test_hat_update_proposal_rejects_broad_diffs_over_eighty_lines(self) -> None:
        broad_diff = "\n".join(f"+ line {index}" for index in range(81))

        with self.assertRaises(ValueError):
            HatUpdateProposal(
                update_id="update-1",
                target_hat=Chat4HatTarget.HAT_002_LINUX_RHCSA,
                target_record_id="record-1",
                proposed_diff_text=broad_diff,
                rationale="Too broad for C4-B proposal shape.",
                risk_class="review_required",
                source_ids=("source-1",),
            )

    def test_reviewer_decision_rejects_authority_flags(self) -> None:
        bad_flags = {
            "promotion_allowed": True,
            "execution_authorized": True,
            "commit_authorized": True,
            "human_reviewed": False,
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "decision_id": "decision-1",
                    "object_type": Chat4ObjectType.HAT_KNOWLEDGE_CANDIDATE,
                    "object_id": "candidate-1",
                    "reviewer_human_id": "human-reviewer",
                    "decision": "needs_revision",
                    "rationale": "C4-B does not authorize direct action.",
                    "timestamp_utc": "2026-06-08T06:00:00Z",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    ReviewerDecision(**kwargs)

    def test_audit_trail_entry_rejects_nonlocal_or_unredacted_or_compliance_claims(self) -> None:
        bad_flags = {
            "local_only": False,
            "secret_redacted": False,
            "compliance_claim": "COMPLIANCE_GRADE",
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "entry_id": "audit-1",
                    "timestamp_utc": "2026-06-08T06:00:00Z",
                    "actor_type": "human",
                    "actor_id": "reviewer",
                    "action": "reviewed",
                    "object_type": Chat4ObjectType.AUDIT_TRAIL_ENTRY,
                    "object_id": "object-1",
                    "redacted_payload_summary": "redacted",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    AuditTrailEntry(**kwargs)

    def test_reviewer_decision_and_audit_trail_defaults_are_inert(self) -> None:
        decision = ReviewerDecision(
            decision_id="decision-1",
            object_type=Chat4ObjectType.HAT_KNOWLEDGE_CANDIDATE,
            object_id="candidate-1",
            reviewer_human_id="human-reviewer",
            decision="needs_revision",
            rationale="Human review only.",
            timestamp_utc="2026-06-08T06:00:00Z",
        )
        entry = AuditTrailEntry(
            entry_id="audit-1",
            timestamp_utc="2026-06-08T06:00:00Z",
            actor_type="human",
            actor_id="reviewer",
            action="reviewed",
            object_type=Chat4ObjectType.AUDIT_TRAIL_ENTRY,
            object_id="object-1",
            redacted_payload_summary="redacted",
        )

        self.assertFalse(decision.promotion_allowed)
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.commit_authorized)
        self.assertTrue(decision.human_reviewed)
        self.assertTrue(entry.local_only)
        self.assertTrue(entry.secret_redacted)
        self.assertEqual("NOT_COMPLIANCE_GRADE", entry.compliance_claim)

    def test_schema_module_contains_no_forbidden_imports_or_method_names(self) -> None:
        source = SCHEMA_PATH.read_text(encoding="utf-8")
        forbidden_patterns = (
            "subprocess",
            "os.system",
            "requests",
            "urllib",
            "httpx",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "google",
            "browser_tools",
            "web_reader",
            "executor",
            "shell_tools",
            "def run",
            "def execute",
            "def commit",
            "def push",
            "def write_file",
            "def open_browser",
            "def call_model",
            "def promote",
            "def canonicalize",
        )

        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)

    def test_schema_definition_report_exists_and_states_non_implementation(self) -> None:
        text = REPORT_PATH.read_text(encoding="utf-8")

        self.assertIn("C4-B defines inert helper-model proposal schemas only.", text)
        self.assertIn("C4-B does not implement helper bots.", text)
        self.assertIn("C4-B does not call Gemini, APIs, or models.", text)
        self.assertIn("C4-B does not launch a browser.", text)
        self.assertIn("C4-B does not execute shell commands.", text)


if __name__ == "__main__":
    unittest.main()
