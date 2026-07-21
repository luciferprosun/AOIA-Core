from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError, replace

from runtime.epistemic_orchestra.human_review_workspace import (
    HUMAN_COMPARISON_WARNING,
    MAXIMUM_COMPARISON_RESPONSE_CHARACTERS,
    OrchestraHumanReviewWorkspaceError,
    build_orchestra_human_review_workspace,
    serialize_orchestra_human_review_workspace,
)
from runtime.epistemic_orchestra.session_view import build_orchestra_session_view
from tests.test_orchestra_session_view_1a import _SessionHarness


class OrchestraHumanReviewWorkspace1ATests(_SessionHarness):
    def _workspace_model(self, preview_payload):
        session_view = self.service._build_orchestra_session_view_for_read(
            self._session_id(preview_payload)
        )
        return build_orchestra_human_review_workspace(session_view)

    def test_workspace_is_deterministic_frozen_and_uses_session_creation_time(self) -> None:
        preview, snapshot, _view = self._complete()
        source = self.service._build_orchestra_session_view_for_read(
            self._session_id(preview)
        )
        first = build_orchestra_human_review_workspace(source)
        second = build_orchestra_human_review_workspace(source)

        self.assertEqual(first, second)
        self.assertEqual(
            serialize_orchestra_human_review_workspace(first),
            serialize_orchestra_human_review_workspace(second),
        )
        self.assertEqual(first.comparison_snapshot_digest, second.comparison_snapshot_digest)
        self.assertEqual(snapshot.created_at_epoch, first.created_at_epoch)
        self.assertEqual(source.session_digest, first.session_digest)
        self.assertNotIn("updated_at_epoch", first.to_dict())
        with self.assertRaises(FrozenInstanceError):
            first.session_state = "FAILED"  # type: ignore[misc]

    def test_candidate_order_is_stable_across_operator_insertion_order(self) -> None:
        ordered = self._create_preview(reverse=False)
        reversed_input = self._create_preview(reverse=True)
        ordered_candidates = self._workspace_model(ordered).candidates
        reversed_candidates = self._workspace_model(reversed_input).candidates

        ordered_identity = tuple(
            (item.ordering_index, item.role_identifier, item.model_profile_id)
            for item in ordered_candidates
        )
        reversed_identity = tuple(
            (item.ordering_index, item.role_identifier, item.model_profile_id)
            for item in reversed_candidates
        )
        self.assertEqual(ordered_identity, reversed_identity)
        self.assertEqual(
            (
                (0, "MAIN", "session-model-0"),
                (1, "CRITIC", "session-model-1"),
                (2, "AUDITOR", "session-model-2"),
            ),
            ordered_identity,
        )

    def test_complete_partial_failed_and_incomplete_roles_remain_visible(self) -> None:
        preview, _snapshot, _view = self._complete()
        complete = self._workspace_model(preview)
        self.assertEqual(3, complete.configured_role_count)
        self.assertEqual(3, complete.completed_response_count)
        self.assertEqual(0, complete.failed_response_count)
        self.assertEqual(0, complete.incomplete_response_count)
        self.assertEqual(
            ("AVAILABLE", "AVAILABLE", "AVAILABLE"),
            tuple(item.presentation_status for item in complete.candidates),
        )

        self.fake_invoker.fail_role = "CRITIC"
        partial_preview = self._create_preview()
        self.assertFalse(self._run_preview(partial_preview)["ok"])
        partial = self._workspace_model(partial_preview)
        self.assertEqual(1, partial.completed_response_count)
        self.assertEqual(1, partial.failed_response_count)
        self.assertEqual(1, partial.incomplete_response_count)
        self.assertEqual(
            ("AVAILABLE", "FAILED", "INCOMPLETE"),
            tuple(item.presentation_status for item in partial.candidates),
        )
        self.assertEqual(3, len(partial.candidates))

    def test_large_sanitized_response_is_bounded_and_explicitly_truncated(self) -> None:
        long_response = "readable comparison line\n" * 1_000
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC"),
            responses_by_role={"MAIN": long_response},
        )
        candidate = self._workspace_model(preview).candidates[0]

        self.assertEqual("TRUNCATED", candidate.presentation_status)
        self.assertEqual("TRUNCATED_FOR_COMPARISON", candidate.truncation_status)
        self.assertEqual(
            MAXIMUM_COMPARISON_RESPONSE_CHARACTERS,
            candidate.presented_response_character_count,
        )
        self.assertEqual(len(long_response), candidate.source_response_character_count)
        self.assertIsNotNone(candidate.response_digest)
        self.assertNotEqual(candidate.response_digest, candidate.presented_response_digest)

    def test_secret_like_provider_text_remains_redacted_in_workspace_serialization(self) -> None:
        secret = "sk-or-v1-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC"),
            responses_by_role={"MAIN": f"Unsafe value {secret} must not escape."},
        )
        workspace = self._workspace_model(preview)
        serialized = serialize_orchestra_human_review_workspace(workspace).decode("utf-8")

        self.assertNotIn(secret, serialized)
        self.assertIn("[REDACTED_PROVIDER_SECRET]", serialized)
        self.assertEqual(
            "REDACTED_OR_SANITIZED",
            workspace.candidates[0].redaction_status,
        )

    def test_malformed_review_evidence_withholds_responses_fail_closed(self) -> None:
        _preview, snapshot, _view = self._complete()
        results = snapshot.completed_stage_results
        malformed_snapshot = replace(
            snapshot,
            completed_stage_results=(
                results[0],
                replace(results[1], critic_payload="malformed-review-evidence"),
                results[2],
            ),
        )
        session_view = build_orchestra_session_view(malformed_snapshot)
        workspace = build_orchestra_human_review_workspace(session_view)

        self.assertEqual("FAIL_CLOSED", session_view.evidence_status)
        self.assertEqual(3, workspace.withheld_response_count)
        self.assertEqual(3, workspace.invalid_evidence_candidate_count)
        self.assertTrue(
            all(item.response_text is None for item in workspace.candidates)
        )
        self.assertTrue(
            all(
                item.presentation_status == "WITHHELD_FAIL_CLOSED"
                for item in workspace.candidates
            )
        )
        self.assertIn("RESPONSES_WITHHELD_FAIL_CLOSED", workspace.evidence_status_summary)

    def test_candidate_evidence_links_only_sanitized_critic_and_audit_hashes(self) -> None:
        preview, _snapshot, _view = self._complete()
        workspace = self._workspace_model(preview)
        critic_candidate = workspace.candidates[1]
        main_candidate = workspace.candidates[0]

        self.assertTrue(critic_candidate.critic_report_references)
        self.assertFalse(main_candidate.critic_report_references)
        self.assertTrue(all(item.audit_report_references for item in workspace.candidates))
        self.assertIn(
            workspace.audit_result.audit_digest,
            main_candidate.audit_report_references,
        )

    def test_workspace_contains_exact_review_warning_and_no_decision_fields(self) -> None:
        preview = self._create_preview()
        workspace = self._workspace_model(preview)
        payload = workspace.to_dict()

        self.assertEqual(HUMAN_COMPARISON_WARNING, payload["human_comparison_warning"])
        serialized = json.dumps(payload, sort_keys=True)
        for forbidden in (
            '"winner"',
            '"selected_final_answer"',
            '"approved_response"',
            '"approval_token"',
        ):
            self.assertNotIn(forbidden, serialized)
        with self.assertRaises(OrchestraHumanReviewWorkspaceError):
            build_orchestra_human_review_workspace(payload)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
