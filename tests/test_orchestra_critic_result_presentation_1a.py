from __future__ import annotations

import copy
import json
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    _gate_evidence_error,
    _gate_mapping,
)
from runtime.epistemic_orchestra.contracts import CriticOutcome
from runtime.epistemic_orchestra.session_view import (
    CRITIC_NON_AUTHORITY_LABEL,
    build_orchestra_session_view,
    serialize_orchestra_session_view,
)
from runtime.safety.approval_gate import evaluate_approval
from tests.test_orchestra_session_view_1a import _SessionHarness


def _material_critic_response(
    *,
    issue_id: str = "issue-material-1",
    issue_code: str = "MISSING_CONSTRAINT",
    summary: str = "A required bounded constraint is absent.",
    evidence: str = "The human request contains the missing constraint.",
    affected_section: str = "initial-response",
    recommended_revision: str = "Add the missing constraint without expanding scope.",
) -> str:
    return json.dumps(
        {
            "critic_outcome": CriticOutcome.MATERIAL_ISSUES_FOUND.value,
            "issues": [
                {
                    "issue_id": issue_id,
                    "issue_code": issue_code,
                    "severity": "HIGH",
                    "summary": summary,
                    "evidence": evidence,
                    "affected_section": affected_section,
                    "recommended_revision": recommended_revision,
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class OrchestraCriticResultPresentation1ATests(_SessionHarness):
    def test_material_findings_are_presented_as_non_authoritative_metadata(self) -> None:
        _preview, _snapshot, view = self._complete(
            roles=("MAIN", "CRITIC"),
            responses_by_role={"CRITIC": _material_critic_response()},
        )

        self.assertEqual(1, len(view["critic_results"]))
        critic = view["critic_results"][0]
        self.assertEqual(CRITIC_NON_AUTHORITY_LABEL, critic["presentation_label"])
        self.assertEqual(CriticOutcome.MATERIAL_ISSUES_FOUND.value, critic["critic_status"])
        self.assertFalse(critic["malformed_or_unavailable"])
        self.assertEqual(1, len(critic["findings"]))
        self.assertEqual("issue-material-1", critic["findings"][0]["finding_id"])
        self.assertEqual("MISSING_CONSTRAINT", critic["findings"][0]["category"])
        self.assertEqual("HIGH", critic["findings"][0]["severity"])
        self.assertEqual("NON_AUTHORITATIVE", critic["authority_status"])
        self.assertFalse(critic["critic_output_is_authority"])
        self.assertFalse(critic["approval_permitted"])
        self.assertFalse(critic["gate_mutation_permitted"])
        self.assertFalse(critic["human_barrier_satisfied"])
        self.assertTrue(critic["human_review_required"])
        self.assertEqual("NOT_REQUESTED", view["audit_result"]["audit_status"])
        self.assertEqual([], view["audit_result"]["auditor_identifiers"])

    def test_no_material_issue_result_is_explicit_but_never_approval(self) -> None:
        _preview, _snapshot, view = self._complete(roles=("MAIN", "CRITIC"))

        critic = view["critic_results"][0]
        self.assertEqual(
            CriticOutcome.NO_MATERIAL_ISSUE_FOUND.value,
            critic["critic_status"],
        )
        self.assertEqual([], critic["findings"])
        self.assertFalse(critic["malformed_or_unavailable"])
        for field in (
            "provider_output_is_authority",
            "provider_consensus_is_authority",
            "critic_output_is_authority",
            "audit_output_is_authority",
            "session_view_is_authority",
            "execution_permitted",
            "write_permitted",
            "dispatch_permitted",
            "provider_call_permitted",
            "approval_permitted",
            "gate_mutation_permitted",
            "human_barrier_satisfied",
        ):
            self.assertIs(critic[field], False, field)
        self.assertTrue(critic["human_review_required"])
        self.assertEqual("NON_AUTHORITATIVE", critic["authority_status"])

    def test_missing_critic_payload_is_visible_and_fails_closed(self) -> None:
        _preview, snapshot, _view = self._complete(roles=("MAIN", "CRITIC"))
        missing = replace(snapshot.completed_stage_results[1], critic_payload=None)
        damaged = replace(
            snapshot,
            completed_stage_results=(snapshot.completed_stage_results[0], missing),
        )

        view = build_orchestra_session_view(damaged).to_dict()
        critic = view["critic_results"][0]
        self.assertEqual("MISSING", critic["critic_status"])
        self.assertTrue(critic["malformed_or_unavailable"])
        self.assertIsNone(critic["report_digest"])
        self.assertIsNone(critic["critic_output_digest"])
        self.assertEqual("FAIL_CLOSED", view["evidence_status"])
        self.assertIn(
            "REVIEW_PAYLOAD_MISSING",
            view["audit_result"]["stale_or_malformed_evidence"],
        )

    def test_malformed_critic_payload_type_is_visible_and_fails_closed(self) -> None:
        _preview, snapshot, _view = self._complete(roles=("MAIN", "CRITIC"))
        malformed = copy.copy(snapshot.completed_stage_results[1])
        object.__setattr__(malformed, "critic_payload", {"critic_outcome": "forged"})
        damaged = replace(
            snapshot,
            completed_stage_results=(snapshot.completed_stage_results[0], malformed),
        )

        view = build_orchestra_session_view(damaged).to_dict()
        critic = view["critic_results"][0]
        self.assertEqual("MALFORMED", critic["critic_status"])
        self.assertTrue(critic["malformed_or_unavailable"])
        self.assertIsNone(critic["report_digest"])
        self.assertIsNone(critic["critic_output_digest"])
        self.assertEqual("FAIL_CLOSED", view["evidence_status"])
        self.assertIn(
            "REVIEW_PAYLOAD_MALFORMED",
            view["audit_result"]["stale_or_malformed_evidence"],
        )

    def test_invalid_critic_output_is_not_reinterpreted_as_no_issue(self) -> None:
        _preview, _snapshot, view = self._complete(
            roles=("MAIN", "CRITIC"),
            responses_by_role={"CRITIC": "not a strict critic JSON object"},
        )

        critic = view["critic_results"][0]
        self.assertEqual(CriticOutcome.CRITIC_OUTPUT_INVALID.value, critic["critic_status"])
        self.assertNotEqual(
            CriticOutcome.NO_MATERIAL_ISSUE_FOUND.value,
            critic["critic_status"],
        )
        self.assertTrue(critic["malformed_or_unavailable"])
        self.assertEqual("FAIL_CLOSED", view["evidence_status"])
        self.assertIn(
            CriticOutcome.CRITIC_OUTPUT_INVALID.value,
            view["audit_result"]["stale_or_malformed_evidence"],
        )

    def test_every_provider_controlled_issue_field_is_redacted_without_secret_hashes(self) -> None:
        issue_id_secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        issue_code_secret = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        summary_secret = "Bearer ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        evidence_secret = "api_key=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        section_secret = "token=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        revision_secret = "password=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        raw_response = _material_critic_response(
            issue_id=issue_id_secret,
            issue_code=issue_code_secret,
            summary=summary_secret,
            evidence=evidence_secret,
            affected_section=section_secret,
            recommended_revision=revision_secret,
        )
        _preview, snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC"),
            responses_by_role={"CRITIC": raw_response},
        )
        raw_payload = snapshot.completed_stage_results[1].critic_payload
        self.assertIsNotNone(raw_payload)

        view_object = build_orchestra_session_view(snapshot)
        view = view_object.to_dict()
        critic = view["critic_results"][0]
        finding = critic["findings"][0]
        serialized = serialize_orchestra_session_view(view_object).decode("utf-8")

        self.assertEqual("redacted-issue", finding["finding_id"])
        self.assertEqual("redacted-category", finding["category"])
        for field in ("summary", "evidence", "affected_section", "recommended_revision"):
            self.assertIn("[REDACTED_PROVIDER_SECRET]", finding[field], field)
        for secret in (
            issue_id_secret,
            issue_code_secret,
            summary_secret,
            evidence_secret,
            section_secret,
            revision_secret,
        ):
            self.assertNotIn(secret, serialized)
        self.assertIsNone(critic["report_digest"])
        self.assertIsNone(critic["critic_output_digest"])
        self.assertNotIn(raw_payload.payload_hash, serialized)
        self.assertNotIn(raw_payload.critic_output_hash, serialized)
        self.assertNotIn(snapshot.completed_stage_results[1].response_hash, serialized)
        self.assertIn(
            "REVIEW_DIGEST_WITHHELD_BY_REDACTION",
            view["audit_result"]["redaction_warnings"],
        )

    def test_critic_view_cannot_satisfy_approval_or_control_write_gate(self) -> None:
        _preview, snapshot, _view = self._complete(roles=("MAIN", "CRITIC"))
        critic = build_orchestra_session_view(snapshot).critic_results[0]

        with self.assertRaises(TypeError):
            evaluate_approval(critic)  # type: ignore[arg-type]
        gate_error = _gate_evidence_error(
            _gate_mapping(critic),
            expected_packet_hash=None,
            expected_artifact_hash="a" * 64,
        )
        self.assertIsNotNone(gate_error)
        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, gate_error[0])
        self.assertNotEqual("APPROVE", critic.to_dict().get("decision"))
        self.assertFalse(critic.approval_permitted)
        self.assertFalse(critic.gate_mutation_permitted)

    def test_web_critic_label_is_exact_and_rendering_uses_text_content(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        html = (repository_root / "web" / "index.html").read_text(encoding="utf-8")
        javascript = (repository_root / "web" / "app.js").read_text(encoding="utf-8")
        renderer = javascript.split("function renderOrchestraSessionView(payload)", 1)[1].split(
            "async function loadOrchestraSessionView()", 1
        )[0]

        self.assertIn(CRITIC_NON_AUTHORITY_LABEL, html)
        self.assertIn(CRITIC_NON_AUTHORITY_LABEL, renderer)
        self.assertIn("textContent", renderer)
        self.assertNotIn("innerHTML", renderer)
        self.assertIn("renderSafeJson", renderer)


if __name__ == "__main__":
    unittest.main()
