from __future__ import annotations

import unittest
from dataclasses import fields, replace

from runtime.epistemic_orchestra.canonical import exact_text_sha256
from runtime.epistemic_orchestra.human_review_workspace import (
    DESCRIPTIVE_AGREEMENT_LABEL,
    build_agreement_overview,
    build_orchestra_human_review_workspace,
    compare_response_candidates,
    normalize_response_text,
)
from tests.test_orchestra_session_view_1a import _SessionHarness


class OrchestraFinalResponseComparison1ATests(_SessionHarness):
    def _workspace(self, preview_payload):
        view = self.service._build_orchestra_session_view_for_read(
            self._session_id(preview_payload)
        )
        return build_orchestra_human_review_workspace(view)

    @staticmethod
    def _candidate_with_text(source, *, candidate_id: str, index: int, text: str):
        return replace(
            source,
            candidate_id=candidate_id,
            candidate_digest="",
            ordering_index=index,
            response_text=text,
            normalized_response_text=normalize_response_text(text),
            response_digest=exact_text_sha256(text),
            presented_response_digest=exact_text_sha256(text),
            source_response_character_count=len(text),
            presented_response_character_count=len(text),
            presented_response_line_count=len(text.split("\n")),
            presentation_status="AVAILABLE",
            truncation_status="NOT_TRUNCATED",
            evidence_validity_status="VALID_NON_AUTHORITATIVE",
        )

    def test_exact_and_normalized_equality_are_separate_descriptive_fields(self) -> None:
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC", "SYNTHESIZER"),
            responses_by_role={
                "MAIN": "Alpha  beta\nGamma   ",
                "SYNTHESIZER": "Alpha beta\nGamma",
            },
        )
        workspace = self._workspace(preview)
        main = workspace.candidates[0]
        synthesizer = workspace.candidates[2]
        comparison = compare_response_candidates(main, synthesizer)

        self.assertTrue(comparison.comparison_available)
        self.assertFalse(comparison.exact_text_equal)
        self.assertTrue(comparison.normalized_text_equal)
        self.assertTrue(comparison.casefolded_normalized_text_equal)
        self.assertFalse(comparison.response_digest_equal)
        self.assertFalse(comparison.agreement_is_authority)

    def test_pair_comparison_is_symmetric_except_for_explicit_orientation(self) -> None:
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC", "SYNTHESIZER"),
            responses_by_role={
                "MAIN": "shared\nmain only",
                "SYNTHESIZER": "shared\nsynth only",
            },
        )
        workspace = self._workspace(preview)
        candidate_a = workspace.candidates[0]
        candidate_b = workspace.candidates[2]
        forward = compare_response_candidates(candidate_a, candidate_b)
        reverse = compare_response_candidates(candidate_b, candidate_a)

        self.assertEqual(forward.exact_text_equal, reverse.exact_text_equal)
        self.assertEqual(forward.normalized_text_equal, reverse.normalized_text_equal)
        self.assertEqual(forward.common_normalized_lines, reverse.common_normalized_lines)
        self.assertEqual(
            forward.candidate_a_only_normalized_lines,
            reverse.candidate_b_only_normalized_lines,
        )
        self.assertEqual(
            forward.candidate_b_only_normalized_lines,
            reverse.candidate_a_only_normalized_lines,
        )
        self.assertEqual(("main only",), forward.candidate_a_only_normalized_lines)
        self.assertEqual(("synth only",), forward.candidate_b_only_normalized_lines)
        self.assertNotEqual(forward.comparison_digest, reverse.comparison_digest)

    def test_same_inputs_have_same_digest_and_different_inputs_change_digest(self) -> None:
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC", "SYNTHESIZER")
        )
        workspace = self._workspace(preview)
        candidate_a = workspace.candidates[0]
        candidate_b = workspace.candidates[2]
        first = compare_response_candidates(candidate_a, candidate_b)
        second = compare_response_candidates(candidate_a, candidate_b)
        changed_b = self._candidate_with_text(
            candidate_b,
            candidate_id="role-2-synthesizer-changed",
            index=2,
            text="A different bounded draft.",
        )
        changed = compare_response_candidates(candidate_a, changed_b)

        self.assertEqual(first, second)
        self.assertEqual(first.comparison_digest, second.comparison_digest)
        self.assertNotEqual(first.comparison_digest, changed.comparison_digest)

    def test_missing_failed_and_invalid_candidates_are_not_comparable(self) -> None:
        self.fake_invoker.fail_role = "CRITIC"
        preview = self._create_preview()
        self.assertFalse(self._run_preview(preview)["ok"])
        workspace = self._workspace(preview)

        completed_to_failed = compare_response_candidates(
            workspace.candidates[0], workspace.candidates[1]
        )
        failed_to_incomplete = compare_response_candidates(
            workspace.candidates[1], workspace.candidates[2]
        )
        self.assertFalse(completed_to_failed.comparison_available)
        self.assertTrue(completed_to_failed.candidate_b_missing_response)
        self.assertFalse(failed_to_incomplete.comparison_available)
        self.assertTrue(failed_to_incomplete.candidate_a_missing_response)
        self.assertTrue(failed_to_incomplete.candidate_b_missing_response)

    def test_agreement_overview_uses_only_neutral_states(self) -> None:
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC", "SYNTHESIZER")
        )
        base = self._workspace(preview).candidates[0]
        one = self._candidate_with_text(
            base, candidate_id="role-0-main-a", index=0, text="same"
        )
        two = self._candidate_with_text(
            base, candidate_id="role-1-critic-b", index=1, text="same"
        )
        three = self._candidate_with_text(
            base, candidate_id="role-2-auditor-c", index=2, text="different"
        )

        self.assertEqual(
            "NO_COMPARABLE_RESPONSES", build_agreement_overview(()).agreement_state
        )
        self.assertEqual(
            "ONE_COMPARABLE_RESPONSE", build_agreement_overview((one,)).agreement_state
        )
        self.assertEqual(
            "ALL_EXACTLY_EQUAL", build_agreement_overview((one, two)).agreement_state
        )
        partial = build_agreement_overview((one, two, three))
        self.assertEqual("PARTIAL_EXACT_MATCH", partial.agreement_state)
        self.assertEqual(DESCRIPTIVE_AGREEMENT_LABEL, partial.presentation_label)
        self.assertFalse(partial.provider_consensus_is_authority)
        self.assertFalse(partial.agreement_is_authority)
        self.assertEqual(
            "RESPONSES_DIFFER", build_agreement_overview((one, three)).agreement_state
        )

    def test_workspace_contains_every_oriented_pair_in_stable_order(self) -> None:
        preview = self._create_preview()
        workspace = self._workspace(preview)
        identities = tuple(
            (item.candidate_a_id, item.candidate_b_id)
            for item in workspace.pair_comparisons
        )
        candidate_ids = tuple(item.candidate_id for item in workspace.candidates)
        expected = tuple(
            (left, right)
            for left in candidate_ids
            for right in candidate_ids
            if left != right
        )
        self.assertEqual(expected, identities)
        self.assertEqual(6, len(identities))

    def test_comparison_contract_has_no_ranking_or_winner_fields(self) -> None:
        field_names = {item.name for item in fields(type(
            self._workspace(self._create_preview()).pair_comparisons[0]
        ))}
        for forbidden in (
            "winner",
            "recommended_candidate",
            "accepted_response",
            "approved_response",
            "authority_level",
            "execution_recommendation",
            "correctness_score",
            "truth_score",
            "provider_reputation",
        ):
            self.assertNotIn(forbidden, field_names)


if __name__ == "__main__":
    unittest.main()
