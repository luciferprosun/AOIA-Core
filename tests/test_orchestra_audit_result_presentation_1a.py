from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    _gate_evidence_error,
)
from runtime.epistemic_orchestra.canonical import canonical_sha256
from runtime.epistemic_orchestra.session_view import (
    AUDIT_EVIDENCE_ONLY_LABEL,
    HUMAN_REVIEW_WARNING,
    build_orchestra_session_view,
)
from runtime.human_approval_gate import (
    HumanApprovalGateError,
    verify_hash_bound_human_approval_record,
)
from tests.test_orchestra_session_view_1a import _SessionHarness


ROOT = Path(__file__).resolve().parents[1]

MATERIAL_AUDIT_REPORT = json.dumps(
    {
        "critic_outcome": "MATERIAL_ISSUES_FOUND",
        "issues": [
            {
                "issue_id": "AUDIT-ISSUE-1",
                "issue_code": "MISSING-EVIDENCE",
                "severity": "HIGH",
                "summary": "One material evidence reference is missing.",
                "evidence": "The draft asserts completion without the referenced record.",
                "affected_section": "completion-claim",
                "recommended_revision": "Add the exact evidence reference or remove the claim.",
            }
        ],
    },
    sort_keys=True,
    separators=(",", ":"),
)


class OrchestraAuditResultPresentation1ATests(_SessionHarness):
    def test_auditor_findings_digest_and_evidence_are_presented_deterministically(self) -> None:
        _preview, snapshot, view = self._complete(
            responses_by_role={"AUDITOR": MATERIAL_AUDIT_REPORT}
        )
        audit = view["audit_result"]
        auditor_result = snapshot.completed_stage_results[2]
        auditor_payload = auditor_result.critic_payload

        self.assertEqual(AUDIT_EVIDENCE_ONLY_LABEL, audit["presentation_label"])
        self.assertEqual("FINDINGS_PRESENT", audit["audit_status"])
        self.assertEqual(["session-model-2"], audit["auditor_identifiers"])
        self.assertEqual(["MATERIAL_ISSUES_FOUND"], audit["auditor_statuses"])
        self.assertEqual(1, len(audit["findings"]))
        finding = audit["findings"][0]
        self.assertEqual("AUDITOR", finding["source_kind"])
        self.assertEqual("AUDIT-ISSUE-1", finding["finding_id"])
        self.assertEqual("MISSING-EVIDENCE", finding["category"])
        self.assertEqual("HIGH", finding["severity"])
        self.assertEqual(
            auditor_payload.source_revision_hash,
            finding["source_revision_hash"],
        )
        self.assertIn(auditor_payload.payload_hash, audit["evidence_references"])
        self.assertIn(auditor_payload.critic_output_hash, audit["evidence_references"])

        material = dict(audit)
        digest = material.pop("audit_digest")
        self.assertEqual(canonical_sha256(material), digest)
        self.assertEqual(
            audit,
            build_orchestra_session_view(snapshot).audit_result.to_dict(),
        )

    def test_partial_provider_failure_is_visible_and_view_does_not_retry_or_fallback(self) -> None:
        self.fake_invoker.fail_model_profile_id = "session-model-2"
        preview = self._create_preview(("MAIN", "CRITIC", "AUDITOR"))
        run_result = self._run_preview(preview)
        calls_after_run = tuple(self.fake_invoker.calls)

        self.assertFalse(run_result["ok"])
        self.assertFalse(run_result["automatic_retry_used"])
        self.assertFalse(run_result["automatic_fallback_used"])
        self.assertEqual(
            (
                ("session-model-0", "MAIN"),
                ("session-model-1", "CRITIC"),
                ("session-model-2", "AUDITOR"),
            ),
            calls_after_run,
        )

        first = self._view(preview)
        second = self._view(preview)
        audit = first["audit_result"]
        self.assertEqual("PARTIAL", first["session_state"])
        self.assertEqual(
            ["COMPLETED", "COMPLETED", "FAILED"],
            [item["invocation_status"] for item in first["role_results"]],
        )
        self.assertEqual(
            ["ROLE_2_AUDITOR_MISSING"],
            audit["missing_role_outputs"],
        )
        self.assertEqual(
            ["ROLE_2_AUDITOR_PROVIDER_FAILURE"],
            audit["provider_failures"],
        )
        self.assertIn(
            "ROLE_2_AUDITOR_PROVIDER_FAILURE",
            audit["detected_inconsistencies"],
        )
        self.assertEqual(first, second)
        self.assertEqual(calls_after_run, tuple(self.fake_invoker.calls))

    def test_hash_mismatch_and_malformed_review_evidence_fail_closed(self) -> None:
        _preview, snapshot, _view = self._complete()
        results = snapshot.completed_stage_results

        foreign_payload_result = replace(
            results[2],
            critic_payload=results[1].critic_payload,
        )
        stale_snapshot = replace(
            snapshot,
            completed_stage_results=(results[0], results[1], foreign_payload_result),
        )
        stale_view = build_orchestra_session_view(stale_snapshot).to_dict()
        stale_audit = stale_view["audit_result"]
        self.assertEqual("FAIL_CLOSED", stale_audit["audit_status"])
        self.assertIn(
            "REVIEW_PAYLOAD_BINDING_MISMATCH",
            stale_audit["hash_mismatches"],
        )
        self.assertEqual("FAIL_CLOSED", stale_view["evidence_status"])

        malformed_result = replace(results[2], critic_payload="malformed-audit-report")
        malformed_snapshot = replace(
            snapshot,
            completed_stage_results=(results[0], results[1], malformed_result),
        )
        malformed_view = build_orchestra_session_view(malformed_snapshot).to_dict()
        malformed_audit = malformed_view["audit_result"]
        self.assertEqual("FAIL_CLOSED", malformed_audit["audit_status"])
        self.assertIn(
            "REVIEW_PAYLOAD_MALFORMED",
            malformed_audit["stale_or_malformed_evidence"],
        )
        self.assertEqual("MALFORMED", malformed_audit["auditor_statuses"][0])
        self.assertEqual("FAIL_CLOSED", malformed_view["evidence_status"])

    def test_redaction_or_terminal_sanitization_is_an_explicit_audit_warning(self) -> None:
        unsafe_main = "Untrusted draft\x1b[31m with terminal control content."
        _preview, _snapshot, view = self._complete(
            responses_by_role={"MAIN": unsafe_main}
        )
        main = view["role_results"][0]
        audit = view["audit_result"]
        rendered = json.dumps(view, sort_keys=True)

        self.assertNotIn("\x1b", rendered)
        self.assertTrue(main["redaction_or_sanitization_applied"])
        self.assertIsNone(main["response_digest"])
        self.assertIn(
            "PROVIDER_DISPLAY_REDACTED_OR_SANITIZED",
            audit["redaction_warnings"],
        )
        self.assertEqual("FINDINGS_PRESENT", audit["audit_status"])

    def test_audit_metadata_cannot_be_human_approval_or_control_write_gate_evidence(self) -> None:
        _preview, _snapshot, view = self._complete(
            responses_by_role={"AUDITOR": MATERIAL_AUDIT_REPORT}
        )
        audit = view["audit_result"]

        for name in (
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
            self.assertIs(audit[name], False, name)
        self.assertEqual("NON_AUTHORITATIVE", audit["authority_status"])
        self.assertTrue(audit["human_review_required"])
        with self.assertRaises(HumanApprovalGateError):
            verify_hash_bound_human_approval_record(audit)  # type: ignore[arg-type]
        gate_error = _gate_evidence_error(
            audit,
            expected_packet_hash=None,
            expected_artifact_hash="a" * 64,
        )
        self.assertIsNotNone(gate_error)
        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, gate_error[0])

    def test_two_auditors_agreeing_in_five_model_session_never_become_authority(self) -> None:
        roles = ("MAIN", "CRITIC", "AUDITOR", "AUDITOR", "SYNTHESIZER")
        _preview, _snapshot, view = self._complete(roles)
        audit = view["audit_result"]

        self.assertEqual(
            ["session-model-2", "session-model-3"],
            audit["auditor_identifiers"],
        )
        self.assertEqual(
            ["NO_MATERIAL_ISSUE_FOUND", "NO_MATERIAL_ISSUE_FOUND"],
            audit["auditor_statuses"],
        )
        self.assertEqual("CLEAN", audit["audit_status"])
        self.assertEqual(5, view["completed_role_count"])
        self.assertIs(view["provider_consensus_is_authority"], False)
        self.assertIs(view["approval_permitted"], False)
        self.assertIs(view["gate_mutation_permitted"], False)
        self.assertIs(view["human_barrier_satisfied"], False)
        self.assertTrue(view["human_review_required"])
        gate_error = _gate_evidence_error(
            view,
            expected_packet_hash=None,
            expected_artifact_hash="b" * 64,
        )
        self.assertIsNotNone(gate_error)

    def test_web_interface_has_exact_labels_and_only_explicit_read_action(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("AUDIT RESULT — EVIDENCE ONLY", html)
        self.assertIn(HUMAN_REVIEW_WARNING, html)
        self.assertIn('id="load-orchestra-session"', html)
        self.assertIn(
            'elements.loadOrchestraSession.addEventListener("click", loadOrchestraSessionView)',
            script,
        )
        self.assertNotIn("setInterval(", script)
        load_start = script.index("async function loadOrchestraSessionView()")
        load_end = script.index("async function runOrchestra()", load_start)
        read_function = script[load_start:load_end]
        self.assertIn("/api/orchestra/sessions/", read_function)
        self.assertNotIn('method: "POST"', read_function)
        self.assertNotIn("/api/orchestra/run", read_function)
        self.assertNotIn("/api/orchestra/preview", read_function)
        self.assertNotIn("provider-connections/test", read_function)
        self.assertNotIn("setTimeout(", read_function)


if __name__ == "__main__":
    unittest.main()
