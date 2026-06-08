from __future__ import annotations

import unittest

import runtime.schemas.chat4_agentic_proposals as c4b


class Chat4AgenticConstraintTests(unittest.TestCase):
    def _proposal_objects(self) -> tuple[object, ...]:
        return (
            c4b.ModelResearchProposal(
                proposal_id="mrp-constraint-1",
                model_name="not-called-model",
                model_version="not-called-version",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                research_question="What should a human reviewer inspect?",
                summary_untrusted="Untrusted draft only.",
                source_candidate_ids=("source-1",),
            ),
            c4b.SourceCandidate(
                source_id="source-1",
                proposal_id="mrp-constraint-1",
                source_type="manual_reference",
                source_reference="https://example.invalid/source",
                title="Manual source reference",
                captured_utc="2026-06-08T07:00:00Z",
                capture_method="human_recorded_reference",
                content_excerpt_redacted="redacted",
                provenance_hash="sha256:not-computed-here",
            ),
            c4b.HatKnowledgeCandidate(
                candidate_id="candidate-1",
                hat_target=c4b.Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
                domain_tag="python",
                title="Candidate note",
                inert_content_text="Inert text only.",
                source_ids=("source-1",),
                model_name="not-called-model",
                created_utc="2026-06-08T07:00:00Z",
            ),
            c4b.HatUpdateProposal(
                update_id="update-1",
                target_hat=c4b.Chat4HatTarget.HAT_002_LINUX_RHCSA,
                target_record_id="record-1",
                proposed_diff_text="- old\n+ proposed",
                rationale="Human review required.",
                risk_class="review_required",
                source_ids=("source-1",),
            ),
            c4b.ContradictionReport(
                report_id="contradiction-1",
                hat_target=c4b.Chat4HatTarget.HAT_004_BROWSER_FILE_GOVERNANCE,
                record_a_id="record-a",
                record_b_id="record-b",
                contradiction_summary="Potential conflict for human review.",
                evidence_excerpt_redacted="redacted",
                severity="medium",
            ),
            c4b.GapReport(
                gap_id="gap-1",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="quoting edge case",
                suggested_source_references=("source-ref-1",),
                priority="low",
            ),
        )

    def test_no_proposal_object_permits_execution_commit_or_promotion(self) -> None:
        for proposal in self._proposal_objects():
            with self.subTest(proposal_type=type(proposal).__name__):
                self.assertEqual(c4b.Chat4ProposalStatus.DRAFT, proposal.status)
                self.assertEqual(
                    c4b.Chat4CanonicalStatus.NOT_CANONICAL,
                    proposal.canonical_status,
                )
                self.assertEqual(
                    c4b.Chat4VerificationStatus.UNVERIFIED,
                    proposal.verification_status,
                )
                self.assertTrue(proposal.human_review_required)
                self.assertFalse(proposal.execution_permitted)
                self.assertFalse(proposal.automatic_commit_permitted)

    def test_reviewer_decision_cannot_authorize_promotion_execution_or_commit(self) -> None:
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
                    "object_type": c4b.Chat4ObjectType.HAT_KNOWLEDGE_CANDIDATE,
                    "object_id": "candidate-1",
                    "reviewer_human_id": "human-reviewer",
                    "decision": "needs_revision",
                    "rationale": "C4-B cannot authorize direct action.",
                    "timestamp_utc": "2026-06-08T07:00:00Z",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    c4b.ReviewerDecision(**kwargs)

    def test_source_provenance_is_mandatory_for_hat_knowledge_candidates(self) -> None:
        with self.assertRaises(ValueError):
            c4b.HatKnowledgeCandidate(
                candidate_id="candidate-empty-source",
                hat_target=c4b.Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
                domain_tag="python",
                title="Candidate note",
                inert_content_text="Inert text only.",
                source_ids=[],
                model_name="not-called-model",
                created_utc="2026-06-08T07:00:00Z",
            )

        valid = c4b.HatKnowledgeCandidate(
            candidate_id="candidate-with-source",
            hat_target=c4b.Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
            domain_tag="python",
            title="Candidate note",
            inert_content_text="Inert text only.",
            source_ids=("source-1",),
            model_name="not-called-model",
            created_utc="2026-06-08T07:00:00Z",
        )
        self.assertEqual(("source-1",), valid.source_ids)

    def test_broad_documentation_rewrite_cannot_be_auto_approved(self) -> None:
        broad_diff = "\n".join(f"+ proposed line {index}" for index in range(81))

        with self.assertRaises(ValueError):
            c4b.HatUpdateProposal(
                update_id="broad-update",
                target_hat=c4b.Chat4HatTarget.HAT_002_LINUX_RHCSA,
                target_record_id="record-1",
                proposed_diff_text=broad_diff,
                rationale="Too broad for automatic approval.",
                risk_class="review_required",
                source_ids=("source-1",),
            )

        small = c4b.HatUpdateProposal(
            update_id="small-update",
            target_hat=c4b.Chat4HatTarget.HAT_002_LINUX_RHCSA,
            target_record_id="record-1",
            proposed_diff_text="- old\n+ proposed",
            rationale="Small proposal still needs human review.",
            risk_class="review_required",
            source_ids=("source-1",),
        )
        self.assertEqual(c4b.Chat4ProposalStatus.DRAFT, small.status)
        self.assertFalse(small.automatic_commit_permitted)

    def test_browser_outputs_remain_unverified_source_candidates(self) -> None:
        source = c4b.SourceCandidate(
            source_id="browser-source-1",
            proposal_id="mrp-browser-1",
            source_type="browser_visible_text",
            source_reference="https://example.invalid/page",
            title="Browser visible text candidate",
            captured_utc="2026-06-08T07:00:00Z",
            capture_method="h4_browser_visible_text_post_review",
            content_excerpt_redacted="redacted browser-visible text",
            provenance_hash="sha256:not-computed-here",
        )

        self.assertEqual(c4b.Chat4VerificationStatus.UNVERIFIED, source.verification_status)
        self.assertEqual(c4b.Chat4CanonicalStatus.NOT_CANONICAL, source.canonical_status)
        self.assertTrue(source.human_review_required)
        self.assertFalse(source.execution_permitted)
        self.assertFalse(source.automatic_commit_permitted)

    def test_hat_domain_separation_is_explicit_for_valid_candidates(self) -> None:
        examples = {
            c4b.Chat4HatTarget.HAT_001_BASH_SAFETY: "bash_safety",
            c4b.Chat4HatTarget.HAT_002_LINUX_RHCSA: "linux_rhcsa",
            c4b.Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE: "python",
        }

        for hat_target, domain_tag in examples.items():
            with self.subTest(hat_target=hat_target):
                candidate = c4b.HatKnowledgeCandidate(
                    candidate_id=f"candidate-{domain_tag}",
                    hat_target=hat_target,
                    domain_tag=domain_tag,
                    title="Domain-separated candidate",
                    inert_content_text="Inert text only.",
                    source_ids=("source-1",),
                    model_name="not-called-model",
                    created_utc="2026-06-08T07:00:00Z",
                )
                self.assertEqual(hat_target, candidate.hat_target)
                self.assertTrue(candidate.domain_tag.strip())

    def test_todo_empty_domain_tag_is_not_yet_rejected_by_c4b_schema(self) -> None:
        """TODO: C4-B records the limitation that empty domain_tag is currently accepted."""
        candidate = c4b.HatKnowledgeCandidate(
            candidate_id="candidate-empty-domain-tag",
            hat_target=c4b.Chat4HatTarget.HAT_003_PYTHON_KNOWLEDGE,
            domain_tag="",
            title="Candidate with current schema limitation",
            inert_content_text="Inert text only.",
            source_ids=("source-1",),
            model_name="not-called-model",
            created_utc="2026-06-08T07:00:00Z",
        )

        self.assertEqual("", candidate.domain_tag)

    def test_no_execution_like_methods_exist_on_c4b_objects(self) -> None:
        forbidden_names = {
            "run",
            "execute",
            "apply",
            "commit",
            "push",
            "write",
            "write_file",
            "open_browser",
            "call_model",
            "promote",
            "canonicalize",
        }
        objects = self._proposal_objects() + (
            c4b.ReviewerDecision(
                decision_id="decision-1",
                object_type=c4b.Chat4ObjectType.HAT_KNOWLEDGE_CANDIDATE,
                object_id="candidate-1",
                reviewer_human_id="human-reviewer",
                decision="needs_revision",
                rationale="Human review only.",
                timestamp_utc="2026-06-08T07:00:00Z",
            ),
            c4b.AuditTrailEntry(
                entry_id="audit-1",
                timestamp_utc="2026-06-08T07:00:00Z",
                actor_type="human",
                actor_id="reviewer",
                action="reviewed",
                object_type=c4b.Chat4ObjectType.AUDIT_TRAIL_ENTRY,
                object_id="object-1",
                redacted_payload_summary="redacted",
            ),
        )

        for item in objects:
            for name in forbidden_names:
                with self.subTest(object_type=type(item).__name__, name=name):
                    self.assertFalse(callable(getattr(item, name, None)))

    def test_schema_module_contains_no_forbidden_imports_or_implementation_terms(self) -> None:
        source = c4b.__loader__.get_source(c4b.__name__)
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

    def test_audit_trail_entry_remains_local_only_and_non_compliance_grade(self) -> None:
        bad_flags = {
            "local_only": False,
            "secret_redacted": False,
            "compliance_claim": "COMPLIANCE_GRADE",
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "entry_id": "audit-1",
                    "timestamp_utc": "2026-06-08T07:00:00Z",
                    "actor_type": "human",
                    "actor_id": "reviewer",
                    "action": "reviewed",
                    "object_type": c4b.Chat4ObjectType.AUDIT_TRAIL_ENTRY,
                    "object_id": "object-1",
                    "redacted_payload_summary": "redacted",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    c4b.AuditTrailEntry(**kwargs)

        valid = c4b.AuditTrailEntry(
            entry_id="audit-2",
            timestamp_utc="2026-06-08T07:00:00Z",
            actor_type="human",
            actor_id="reviewer",
            action="reviewed",
            object_type=c4b.Chat4ObjectType.AUDIT_TRAIL_ENTRY,
            object_id="object-1",
            redacted_payload_summary="redacted",
        )
        self.assertTrue(valid.local_only)
        self.assertTrue(valid.secret_redacted)
        self.assertEqual("NOT_COMPLIANCE_GRADE", valid.compliance_claim)

    def test_no_model_output_can_become_canonical_through_c4b_objects(self) -> None:
        for proposal_type in (
            c4b.ModelResearchProposal,
            c4b.SourceCandidate,
            c4b.HatKnowledgeCandidate,
            c4b.HatUpdateProposal,
            c4b.ContradictionReport,
            c4b.GapReport,
        ):
            fields = proposal_type.__dataclass_fields__
            with self.subTest(proposal_type=proposal_type.__name__):
                self.assertNotIn("canonical", fields)
                self.assertNotIn("verified", fields)

        with self.assertRaises(ValueError):
            c4b.GapReport(
                gap_id="gap-canonical",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="topic",
                suggested_source_references=("source-ref-1",),
                priority="low",
                canonical_status="CANONICAL",
            )
        with self.assertRaises(ValueError):
            c4b.GapReport(
                gap_id="gap-verified",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="topic",
                suggested_source_references=("source-ref-1",),
                priority="low",
                verification_status=True,
            )
        with self.assertRaises(ValueError):
            c4b.GapReport(
                gap_id="gap-exec",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="topic",
                suggested_source_references=("source-ref-1",),
                priority="low",
                execution_permitted=True,
            )
        with self.assertRaises(ValueError):
            c4b.GapReport(
                gap_id="gap-commit",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="topic",
                suggested_source_references=("source-ref-1",),
                priority="low",
                automatic_commit_permitted=True,
            )
        with self.assertRaises(TypeError):
            c4b.GapReport(
                gap_id="gap-extra-canonical",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="topic",
                suggested_source_references=("source-ref-1",),
                priority="low",
                canonical=True,
            )
        with self.assertRaises(TypeError):
            c4b.GapReport(
                gap_id="gap-extra-verified",
                hat_target=c4b.Chat4HatTarget.HAT_001_BASH_SAFETY,
                missing_topic="topic",
                suggested_source_references=("source-ref-1",),
                priority="low",
                verified=True,
            )


if __name__ == "__main__":
    unittest.main()
