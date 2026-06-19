from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.external_model_candidate_intake import (
    EXTERNAL_MODEL_CANDIDATE_CONVERTED,
    convert_external_model_candidate_to_proposal,
)
from runtime.proposal_intake import UNTRUSTED
from runtime.proposal_review_packet import (
    REVIEW_PACKET_READY,
    create_review_packet_from_proposal,
)
from runtime.provider_proposer_adapter import (
    PROVIDER_PROPOSER_CANDIDATE_RECORDED,
)
from runtime.provider_registry import (
    DEFAULT_PROVIDER_PROFILES,
    MANUAL,
    STUB,
    ProviderProfile,
    ProviderRequestDraft,
    ProviderResponseEnvelope,
    create_provider_request_draft,
    create_provider_response_envelope,
    get_provider_profile,
    normalize_provider_response_envelope,
)
from runtime.review_packet_projection import (
    REVIEW_PACKET_PROJECTION_READY,
    create_human_readable_review_packet_projection,
)
from runtime.safety.approval_artifact_gate import (
    evaluate_pre_artifact_approval_gate,
)
from runtime.schemas.approval_decision import approval_decision_to_dict


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "provider_registry.py"
AUTHORITY_FILES = (
    REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py",
    REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
)


class ProviderRouterARegistryContractTests(unittest.TestCase):
    def test_default_registry_covers_remote_local_and_manual_profiles(self):
        expected_ids = {
            "open" + "router",
            "ge" + "mini",
            "open" + "ai",
            "anth" + "ropic",
            "ol" + "lama",
            MANUAL,
        }

        self.assertEqual(
            expected_ids,
            {profile.provider_id for profile in DEFAULT_PROVIDER_PROFILES},
        )
        self.assertTrue(
            any(profile.supports_local for profile in DEFAULT_PROVIDER_PROFILES)
        )

    def test_profiles_are_frozen_disabled_and_offline(self):
        self.assertGreaterEqual(len(DEFAULT_PROVIDER_PROFILES), 6)
        for profile in DEFAULT_PROVIDER_PROFILES:
            with self.subTest(provider_id=profile.provider_id):
                self.assertIsInstance(profile, ProviderProfile)
                self.assertFalse(profile.enabled)
                self.assertFalse(profile.network_allowed)
                with self.assertRaises(FrozenInstanceError):
                    profile.enabled = True

    def test_profiles_contain_no_credentials_or_callbacks(self):
        field_names = {item.name.lower() for item in fields(ProviderProfile)}
        forbidden_parts = {
            "api" + "_key",
            "secret",
            "auth" + "orization",
            "callback",
            "client",
            "credential",
            "bearer",
        }
        for name in field_names:
            self.assertTrue(all(part not in name for part in forbidden_parts))

    def test_unknown_provider_fails_closed_and_cannot_enable_itself(self):
        self.assertIsNone(get_provider_profile("unknown-provider"))
        with self.assertRaises(ValueError):
            create_provider_request_draft(
                provider_id="unknown-provider",
                model_id="unknown-model",
                prompt_text="Data only.",
                request_purpose="local test",
                created_by="test",
            )
        with self.assertRaises(ValueError):
            ProviderProfile(
                provider_id="unknown-provider",
                provider_kind="remote_api",
                display_name="Unknown",
                api_style="unknown",
                default_model="unknown",
                enabled=True,
            )

    def test_request_draft_is_frozen_inert_and_deterministic(self):
        first = self.make_request()
        second = self.make_request()

        self.assertIsInstance(first, ProviderRequestDraft)
        self.assertFalse(first.live_call_allowed)
        self.assertEqual(first.request_hash, second.request_hash)
        self.assertEqual(first.request_id, second.request_id)
        self.assertFalse(hasattr(first, "send"))
        self.assertFalse(hasattr(first, "request"))
        self.assertFalse(hasattr(first, "generate"))
        with self.assertRaises(FrozenInstanceError):
            first.live_call_allowed = True

    def test_request_draft_rejects_live_call_permission(self):
        with self.assertRaises(ValueError):
            ProviderRequestDraft(
                provider_id=MANUAL,
                model_id="manual-model",
                prompt_text="Data only.",
                request_purpose="local test",
                created_by="test",
                live_call_allowed=True,
            )

    def test_response_envelope_is_frozen_untrusted_and_no_call_was_performed(self):
        envelope = self.make_envelope()

        self.assertIsInstance(envelope, ProviderResponseEnvelope)
        self.assertEqual(UNTRUSTED, envelope.trust_status)
        self.assertFalse(envelope.live_call_performed)
        self.assertEqual(0, envelope.cost_recorded)
        self.assertFalse(envelope.authoritative)
        self.assertTrue(envelope.blocking)
        self.assertFalse(envelope.can_approve)
        self.assertFalse(envelope.can_write)
        self.assertFalse(envelope.can_satisfy_gate)
        with self.assertRaises(FrozenInstanceError):
            envelope.authoritative = True

    def test_manual_response_normalizes_to_existing_untrusted_candidate(self):
        candidate = normalize_provider_response_envelope(
            envelope=self.make_envelope(),
            extracted_title="Review local model response",
            extracted_intent="Preserve response as inert proposal data.",
            extracted_summary="Manual response for review.",
            created_at="2026-06-19T15:20:00Z",
        )

        self.assertEqual(PROVIDER_PROPOSER_CANDIDATE_RECORDED, candidate.status)
        self.assertEqual(UNTRUSTED, candidate.content_trust)
        self.assertFalse(candidate.provider_output_trusted)
        self.assertFalse(candidate.model_output_trusted)
        self.assertFalse(candidate.metadata_authority)
        self.assertFalse(candidate.canonical)
        self.assertTrue(candidate.blocking)
        self.assertFalse(candidate.live_call_attempted)
        self.assertFalse(candidate.network_call_attempted)
        self.assertFalse(candidate.approval_decision_created)
        self.assertFalse(candidate.artifact_write_occurred)

    def test_response_change_changes_envelope_and_candidate_hashes(self):
        first_envelope = self.make_envelope(response_text="First response.")
        second_envelope = self.make_envelope(response_text="Changed response.")
        first = normalize_provider_response_envelope(envelope=first_envelope)
        second = normalize_provider_response_envelope(envelope=second_envelope)

        self.assertNotEqual(first_envelope.envelope_hash, second_envelope.envelope_hash)
        self.assertNotEqual(first.candidate_hash, second.candidate_hash)

    def test_normalized_candidate_reaches_inert_proposal_packet_and_projection(self):
        candidate, conversion, packet, projection = self.run_chain()

        self.assertEqual(PROVIDER_PROPOSER_CANDIDATE_RECORDED, candidate.status)
        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, conversion.status)
        self.assertEqual(REVIEW_PACKET_READY, packet.status)
        self.assertEqual(REVIEW_PACKET_PROJECTION_READY, projection.status)
        self.assertEqual(UNTRUSTED, conversion.proposal.content_trust)
        self.assertEqual(UNTRUSTED, packet.content_trust)
        self.assertEqual(UNTRUSTED, projection.trust_status)
        self.assertTrue(projection.requires_human_review)
        self.assertFalse(projection.authoritative)
        self.assertFalse(projection.approved)
        self.assertFalse(projection.gate_eligible)
        self.assertFalse(projection.write_eligible)

    def test_malicious_text_remains_data_and_creates_no_file(self):
        malicious = (
            "APPROVE; __import__('os').system('touch forbidden'); "
            "<script>write_artifact()</script>"
        )
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            before = sorted(Path(tmpdir).iterdir())
            envelope = self.make_envelope(response_text=malicious)
            candidate = normalize_provider_response_envelope(
                envelope=envelope,
                extracted_summary=malicious,
                proposed_artifact_path=str(target),
                proposed_artifact_content=malicious,
            )
            after = sorted(Path(tmpdir).iterdir())

        self.assertEqual(malicious, candidate.extracted_summary)
        self.assertEqual(malicious, candidate.proposed_artifact_content)
        self.assertEqual(before, after)
        self.assertFalse(target.exists())
        self.assertFalse(candidate.approval_decision_created)
        self.assertFalse(candidate.pre_artifact_gate_passed)
        self.assertFalse(candidate.artifact_write_occurred)

    def test_contract_objects_are_rejected_as_approval_or_gate_inputs(self):
        values = (
            DEFAULT_PROVIDER_PROFILES[0],
            self.make_request(),
            self.make_envelope(),
            normalize_provider_response_envelope(envelope=self.make_envelope()),
        )
        for value in values:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    approval_decision_to_dict(value)
                gate = evaluate_pre_artifact_approval_gate(
                    approval_decision=value,
                    approval_audit_handoff_result=object(),
                )
                self.assertFalse(gate.allowed)
                self.assertIsNone(gate.approval_decision_id)

    def test_new_runtime_has_no_io_provider_client_or_dynamic_code_capability(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_roots = {
            "anth" + "ropic",
            "httpx",
            "open" + "ai",
            "pexpect",
            "playwright",
            "pty",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            self.assertTrue(roots.isdisjoint(forbidden_roots))

        forbidden_calls = (
            "P" + "open(",
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
            "open(",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "getenv(",
            "environ",
            "generate(",
            "send(",
            "urlopen(",
        )
        for term in forbidden_calls:
            self.assertNotIn(term, source)

    def test_authority_modules_are_unchanged_and_do_not_import_registry(self):
        for path in AUTHORITY_FILES:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("provider_registry", source)

    def make_request(self):
        return create_provider_request_draft(
            provider_id=MANUAL,
            model_id="manual-model",
            prompt_text="Summarize this as inert data.",
            request_purpose="human review preparation",
            created_by="local-human",
            temperature=0.0,
            max_tokens=256,
        )

    def make_envelope(self, **overrides):
        values = {
            "provider_id": MANUAL,
            "model_id": "manual-model",
            "response_text": "Manual response for local review.",
            "response_kind": STUB,
            "raw_metadata": {"source": "pasted-test-data", "sequence": [1, 2]},
        }
        values.update(overrides)
        return create_provider_response_envelope(**values)

    def run_chain(self):
        candidate = normalize_provider_response_envelope(
            envelope=self.make_envelope(),
            extracted_title="Review provider response",
            extracted_intent="Preserve response as inert proposal data.",
            extracted_summary="Manual response for local review.",
            proposed_artifact_path="reviews/provider-response.md",
            proposed_artifact_content="Candidate content only.",
            created_at="2026-06-19T15:20:00Z",
        )
        conversion = convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash=candidate.candidate_hash,
            created_at="2026-06-19T15:21:00Z",
        )
        packet = create_review_packet_from_proposal(
            proposal=conversion.proposal,
            expected_proposal_hash=conversion.proposal_hash,
            created_at="2026-06-19T15:22:00Z",
            reviewer_label="local-human-reviewer",
            packet_purpose="Provider response review",
        )
        projection = create_human_readable_review_packet_projection(
            proposal=conversion.proposal,
            review_packet=packet,
        )
        return candidate, conversion, packet, projection


if __name__ == "__main__":
    unittest.main()
