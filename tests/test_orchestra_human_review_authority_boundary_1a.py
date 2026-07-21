from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    _gate_evidence_error,
)
from runtime.epistemic_orchestra.human_review_workspace import (
    OrchestraHumanReviewWorkspace,
    OrchestraHumanReviewWorkspaceError,
    build_orchestra_human_review_workspace,
)
from runtime.epistemic_orchestra.session_view import build_orchestra_session_view
from runtime.human_approval_gate import (
    HumanApprovalGateError,
    verify_hash_bound_human_approval_record,
)
from runtime.providers.user_connections import UserProviderStore
from runtime.safety.approval_gate import evaluate_approval
from tests.test_orchestra_session_view_1a import _SessionHarness


class OrchestraHumanReviewAuthorityBoundary1ATests(_SessionHarness):
    def _workspace(self, preview_payload):
        view = self.service._build_orchestra_session_view_for_read(
            self._session_id(preview_payload)
        )
        return build_orchestra_human_review_workspace(view)

    def test_every_workspace_layer_remains_explicitly_non_authoritative(self) -> None:
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC", "AUDITOR", "AUDITOR", "SYNTHESIZER")
        )
        workspace = self._workspace(preview)
        values = (
            workspace,
            *workspace.candidates,
            *workspace.pair_comparisons,
            workspace.agreement_overview,
            *workspace.critic_results,
            workspace.audit_result,
        )
        false_fields = (
            "provider_output_is_authority",
            "provider_consensus_is_authority",
            "critic_output_is_authority",
            "audit_output_is_authority",
            "execution_permitted",
            "write_permitted",
            "dispatch_permitted",
            "provider_call_permitted",
            "approval_permitted",
            "gate_mutation_permitted",
            "human_barrier_satisfied",
        )
        for value in values:
            with self.subTest(type=type(value).__name__):
                self.assertEqual("NON_AUTHORITATIVE", value.authority_status)
                self.assertTrue(value.human_review_required)
                for field in false_fields:
                    self.assertIs(getattr(value, field), False, field)
        self.assertFalse(workspace.agreement_is_authority)
        self.assertFalse(workspace.candidate_selection_is_authority)

    def test_workspace_consensus_critic_and_audit_cannot_satisfy_any_gate(self) -> None:
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC", "AUDITOR", "AUDITOR", "SYNTHESIZER")
        )
        workspace = self._workspace(preview)
        payloads = (
            workspace.to_dict(),
            workspace.agreement_overview.to_dict(),
            workspace.critic_results[0].to_dict(),
            workspace.audit_result.to_dict(),
        )
        for payload in payloads:
            with self.subTest(schema=payload.get("schema_version")):
                with self.assertRaises(HumanApprovalGateError):
                    verify_hash_bound_human_approval_record(payload)  # type: ignore[arg-type]
                gate_error = _gate_evidence_error(
                    payload,
                    expected_packet_hash=None,
                    expected_artifact_hash="a" * 64,
                )
                self.assertIsNotNone(gate_error)
                self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, gate_error[0])
        with self.assertRaises(TypeError):
            evaluate_approval(workspace)  # type: ignore[arg-type]

    def test_forged_approval_winner_and_selected_answer_fields_fail_closed(self) -> None:
        preview = self._create_preview()
        workspace = self._workspace(preview)
        for forged_field, forged_value in (
            ("approved", True),
            ("winner", workspace.candidates[0].candidate_id),
            ("selected_final_answer", "forged answer"),
        ):
            forged = workspace.to_dict()
            forged[forged_field] = forged_value
            with self.subTest(field=forged_field):
                with self.assertRaises(TypeError):
                    OrchestraHumanReviewWorkspace(**forged)  # type: ignore[arg-type]
                with self.assertRaises(OrchestraHumanReviewWorkspaceError):
                    build_orchestra_human_review_workspace(forged)  # type: ignore[arg-type]

    def test_opening_consumed_workspace_cannot_replay_plan_or_call_provider(self) -> None:
        preview, _snapshot, _view = self._complete(("MAIN", "CRITIC"))
        session_id = self._session_id(preview)
        calls_after_run = tuple(self.fake_invoker.calls)
        issued_before = dict(self.service._issued_previews)
        snapshots_before = dict(self.service._session_snapshots)
        registry_before = (
            dict(self.service.session_registry._issued_confirmations),
            dict(self.service.session_registry._claimed_confirmations),
            dict(self.service.session_registry._issued_stage_authorizations),
            dict(self.service.session_registry._consumed_stage_authorizations),
        )

        first = self.service.get_orchestra_human_review_workspace(session_id)
        second = self.service.get_orchestra_human_review_workspace(session_id)

        self.assertEqual(first, second)
        self.assertEqual(calls_after_run, tuple(self.fake_invoker.calls))
        self.assertEqual(issued_before, self.service._issued_previews)
        self.assertEqual(snapshots_before, self.service._session_snapshots)
        self.assertEqual(
            registry_before,
            (
                self.service.session_registry._issued_confirmations,
                self.service.session_registry._claimed_confirmations,
                self.service.session_registry._issued_stage_authorizations,
                self.service.session_registry._consumed_stage_authorizations,
            ),
        )
        with self.assertRaisesRegex(ValueError, "missing, foreign, or consumed"):
            self._run_preview(preview)
        self.assertEqual(calls_after_run, tuple(self.fake_invoker.calls))

    def test_opening_expired_workspace_neither_extends_nor_mutates_plan(self) -> None:
        preview = self._create_preview()
        session_id = self._session_id(preview)
        snapshot = self._snapshot(preview)
        expires_at = snapshot.preview.expires_at_epoch
        self.clock.advance(301)

        first = self.service.get_orchestra_human_review_workspace(session_id)
        second = self.service.get_orchestra_human_review_workspace(session_id)

        self.assertEqual(first, second)
        self.assertEqual("EXPIRED", first["session_state"])
        self.assertEqual(3, first["withheld_response_count"])
        self.assertIs(snapshot, self._snapshot(preview))
        self.assertEqual("NOT_EXECUTED", snapshot.session_state)
        self.assertTrue(snapshot.plan_available)
        self.assertEqual(expires_at, snapshot.preview.expires_at_epoch)
        self.assertEqual([], self.fake_invoker.calls)

    def test_workspace_read_does_not_write_files_or_mutate_source_session(self) -> None:
        preview = self._create_preview()
        session_id = self._session_id(preview)
        snapshot = self._snapshot(preview)
        snapshot_before = copy.deepcopy(snapshot)
        config_before = self.store.config_path.read_bytes()
        secret_path = self.store.secrets_root / "session-view-connection.key"
        secret_before = secret_path.read_bytes()

        with patch.object(
            UserProviderStore,
            "_write_atomic_regular_file",
            side_effect=AssertionError("human review GET attempted a filesystem write"),
        ) as writer, patch.object(
            UserProviderStore,
            "read_credential",
            side_effect=AssertionError("human review GET attempted to read a credential"),
        ) as credential_reader:
            payload = self.service.get_orchestra_human_review_workspace(session_id)

        self.assertEqual(snapshot_before, snapshot)
        self.assertIs(snapshot, self._snapshot(preview))
        self.assertEqual(config_before, self.store.config_path.read_bytes())
        self.assertEqual(secret_before, secret_path.read_bytes())
        self.assertFalse(payload["write_permitted"])
        writer.assert_not_called()
        credential_reader.assert_not_called()

    def test_mismatched_hash_evidence_is_withheld_without_gate_mutation(self) -> None:
        _preview, snapshot, _view = self._complete(("MAIN", "CRITIC"))
        mismatched = copy.deepcopy(snapshot)
        object.__setattr__(
            mismatched.completed_stage_results[1],
            "response_hash",
            "0" * 64,
        )
        session_view = build_orchestra_session_view(mismatched)
        workspace = build_orchestra_human_review_workspace(session_view)

        self.assertEqual("FAIL_CLOSED", session_view.evidence_status)
        self.assertEqual(2, workspace.withheld_response_count)
        self.assertTrue(
            all(item.evidence_validity_status == "INVALID_FAIL_CLOSED" for item in workspace.candidates)
        )
        self.assertFalse(workspace.gate_mutation_permitted)
        self.assertFalse(workspace.approval_permitted)

    def test_workspace_performs_no_retry_or_fallback_after_provider_failure(self) -> None:
        self.fake_invoker.fail_role = "CRITIC"
        preview = self._create_preview()
        self.assertFalse(self._run_preview(preview)["ok"])
        calls_after_run = tuple(self.fake_invoker.calls)

        first = self.service.get_orchestra_human_review_workspace(
            self._session_id(preview)
        )
        second = self.service.get_orchestra_human_review_workspace(
            self._session_id(preview)
        )

        self.assertEqual(first, second)
        self.assertEqual(calls_after_run, tuple(self.fake_invoker.calls))
        self.assertEqual(2, len(calls_after_run))
        self.assertFalse(first["provider_call_permitted"])


if __name__ == "__main__":
    unittest.main()
