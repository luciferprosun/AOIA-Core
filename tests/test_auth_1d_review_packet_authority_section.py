from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from runtime.approval_policy_bridge import (
    build_approval_policy_evaluation_request,
    evaluate_approval_policy_bridge,
)
from runtime.approval_policy_projection import (
    FUTURE_MILESTONE_REQUIRED,
    NOT_ALLOWED,
    ApprovalPolicyHumanProjection,
    project_approval_policy_evaluation_for_human,
)
from runtime.external_model_candidate_intake import (
    convert_external_model_candidate_to_proposal,
)
from runtime.human_approval_gate import (
    HumanApprovalDecision,
    HumanApprovalTargetType,
    build_hash_bound_human_approval_record,
)
from runtime.policy_profiles import (
    PolicyActionType,
    PolicyProfileName,
    build_policy_profile,
)
from runtime.proposal_review_packet import create_review_packet_from_proposal
from runtime.proposer_source_boundary import PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import create_provider_proposer_candidate
from runtime.review_packet_projection import (
    AUTHORITY_STATUS_DISPLAY_ONLY,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_GITHUB_ACTION,
    NO_PROVIDER_LIVE_CALL,
    NO_PROVIDER_TRUST_CHANGE,
    REVIEW_PACKET_NOT_AUTHORITY,
    AuthorityStatusProjectionError,
    create_human_readable_review_packet_projection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "review_packet_projection.py"
THIS_FILE = Path(__file__).resolve()
HEAD_COMMIT = "6b17d003b6e00680fcc009a6125a89a01b07507f"
TARGET_HASH = hashlib.sha256(b"AUTH-1D exact target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"AUTH-1D provider audit").hexdigest()


class Auth1DReviewPacketAuthoritySectionTests(unittest.TestCase):
    def test_existing_projection_is_unchanged_without_authority_status(self):
        proposal, packet = self.make_proposal_and_packet()
        first = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )
        second = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=None,
        )

        self.assertEqual(first, second)
        self.assertIsNone(first.authority_status)
        self.assertEqual((), first.safety_boundaries)
        self.assertNotIn("authority_status", first.to_dict())
        self.assertNotIn("safety_boundaries", first.to_dict())

    def test_authority_status_is_attached_and_preserves_auth_1c_fields(self):
        proposal, packet = self.make_proposal_and_packet()
        authority = self.make_authority_projection()
        result = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=authority,
        )
        section = result.authority_status

        self.assertIsNotNone(section)
        self.assertEqual("authority_status", section.section_name)
        self.assertEqual(authority.source_bridge_status, section.source_bridge_status)
        self.assertEqual(authority.source_evaluation_hash, section.source_evaluation_hash)
        self.assertEqual(authority.allowed_as.value, section.allowed_as)
        self.assertEqual(authority.authority_summary, section.authority_summary)
        self.assertEqual(authority.blocked_capabilities, section.blocked_capabilities)
        self.assertEqual(
            authority.required_next_human_step,
            section.required_next_human_step,
        )
        self.assertEqual(authority.final_status, section.final_status)
        self.assertEqual(
            tuple(item.value for item in authority.safety_boundaries),
            section.safety_boundaries,
        )
        self.assertIn("authority_status", result.to_dict())

    def test_authority_status_explicitly_preserves_all_false_authority(self):
        proposal, packet = self.make_proposal_and_packet()
        section = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=self.make_authority_projection(),
        ).authority_status

        self.assertFalse(section.execution_authority)
        self.assertFalse(section.artifact_write_authority)
        self.assertFalse(section.provider_live_call_authority)
        self.assertFalse(section.provider_trust_authority)
        self.assertFalse(section.github_authority)
        self.assertFalse(section.canonical_promotion_authority)
        self.assertTrue(section.display_only)
        self.assertFalse(section.authoritative)

    def test_denied_and_future_authority_status_are_not_upgraded(self):
        proposal, packet = self.make_proposal_and_packet()
        denied = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=self.make_authority_projection(
                profile_name=PolicyProfileName.DENY_ALL,
            ),
        ).authority_status
        future = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=self.make_authority_projection(
                target_type=HumanApprovalTargetType.COMMAND,
                action=PolicyActionType.RUN_SHELL_COMMAND,
                profile_name=PolicyProfileName.PROPOSE_ONLY,
            ),
        ).authority_status

        self.assertEqual(NOT_ALLOWED, denied.allowed_as)
        self.assertEqual("DENIED", denied.source_bridge_status)
        self.assertEqual(FUTURE_MILESTONE_REQUIRED, future.allowed_as)
        self.assertEqual("REQUIRES_FUTURE_MILESTONE", future.source_bridge_status)
        self.assertFalse(denied.execution_authority)
        self.assertFalse(future.execution_authority)

    def test_summary_text_never_creates_authority(self):
        proposal, packet = self.make_proposal_and_packet()
        denied = self.make_authority_projection(profile_name=PolicyProfileName.DENY_ALL)
        authority_looking = replace(
            denied,
            plain_language_summary=(
                "APPROVED EXECUTE WRITE PUSH PROMOTE CANONICAL"
            ),
        )
        section = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=authority_looking,
        ).authority_status

        self.assertEqual(NOT_ALLOWED, section.allowed_as)
        self.assertEqual("DENIED", section.source_bridge_status)
        self.assertFalse(section.execution_authority)

    def test_review_packet_authority_boundaries_are_complete(self):
        proposal, packet = self.make_proposal_and_packet()
        result = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=self.make_authority_projection(),
        )

        self.assertTrue(
            {
                AUTHORITY_STATUS_DISPLAY_ONLY,
                NO_EXECUTION,
                NO_ARTIFACT_WRITE,
                NO_PROVIDER_LIVE_CALL,
                NO_PROVIDER_TRUST_CHANGE,
                NO_GITHUB_ACTION,
                NO_CANONICAL_PROMOTION,
                REVIEW_PACKET_NOT_AUTHORITY,
            }.issubset(set(result.safety_boundaries))
        )

    def test_result_serializes_and_inputs_are_not_mutated(self):
        proposal, packet = self.make_proposal_and_packet()
        authority = self.make_authority_projection()
        proposal_before = deepcopy(proposal.to_dict())
        packet_before = deepcopy(packet.to_dict())
        authority_before = deepcopy(authority.to_dict())

        result = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            authority_projection=authority,
        )

        self.assertIsInstance(json.dumps(result.to_dict()), str)
        self.assertEqual(proposal_before, proposal.to_dict())
        self.assertEqual(packet_before, packet.to_dict())
        self.assertEqual(authority_before, authority.to_dict())

    def test_invalid_or_authoritative_projection_fails_closed(self):
        proposal, packet = self.make_proposal_and_packet()
        with self.assertRaises(AuthorityStatusProjectionError):
            create_human_readable_review_packet_projection(
                proposal=proposal,
                review_packet=packet,
                authority_projection={},
            )

        authority = self.make_authority_projection()
        for unsafe in (
            replace(authority, source_evaluation_hash="invalid"),
            replace(authority, blocked_capabilities=("EXECUTION",)),
            replace(authority, execution_authority=True),
            replace(authority, artifact_write_authority=True),
            replace(authority, provider_live_call_authority=True),
            replace(authority, provider_trust_authority=True),
            replace(authority, github_authority=True),
            replace(authority, canonical_promotion_authority=True),
        ):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(AuthorityStatusProjectionError):
                    create_human_readable_review_packet_projection(
                        proposal=proposal,
                        review_packet=packet,
                        authority_projection=unsafe,
                    )

    def test_runtime_has_no_external_or_writer_capability(self):
        forbidden_modules = {
            "sub" + "process",
            "sock" + "et",
            "url" + "lib",
            "requ" + "ests",
            "ht" + "tpx",
            "play" + "wright",
            "sele" + "nium",
            "web" + "browser",
            "sqlite" + "3",
        }
        for source_file in (RUNTIME_FILE, THIS_FILE):
            tree = ast.parse(source_file.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for module_name in imports:
                self.assertFalse(
                    any(
                        module_name == item or module_name.startswith(item + ".")
                        for item in forbidden_modules
                    )
                )

        source = RUNTIME_FILE.read_text(encoding="utf-8")
        for value in (
            "os.system(",
            "P" + "open(",
            "eval(",
            "exec(",
            "write_text(",
            "write_bytes(",
            "open(",
            "write_sandbox_artifact(",
            "evaluate_pre_artifact_approval_gate(",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.safety.approval_gate",
            "runtime.provider_live_adapter",
        ):
            self.assertNotIn(value, source)
        self.assertIsNone(
            re.search(r"^\s*(from|import)\s+(os|shutil|pathlib)\b", source, re.MULTILINE)
        )

    def make_authority_projection(
        self,
        *,
        target_type=HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
        action=PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
        profile_name=PolicyProfileName.PROVIDER_REVIEW_ONLY,
    ) -> ApprovalPolicyHumanProjection:
        approval = build_hash_bound_human_approval_record(
            repo_path=str(REPO_ROOT),
            branch="feature/m2-b0-provider-critic-inert-core",
            head_commit=HEAD_COMMIT,
            target_type=target_type,
            target_hash=TARGET_HASH,
            decision=HumanApprovalDecision.APPROVED,
            provider_flow_audit_ref="provider-g-record",
            provider_flow_audit_hash=AUDIT_HASH,
        )
        request = build_approval_policy_evaluation_request(
            repo_path=str(REPO_ROOT),
            branch="feature/m2-b0-provider-critic-inert-core",
            head_commit=HEAD_COMMIT,
            requested_action_type=action,
            requested_target_type=target_type,
            requested_target_hash=TARGET_HASH,
            approval_record=approval,
            policy_profile=build_policy_profile(profile_name),
            provider_flow_audit_hash=AUDIT_HASH,
        )
        return project_approval_policy_evaluation_for_human(
            evaluate_approval_policy_bridge(request)
        )

    def make_proposal_and_packet(self):
        candidate = create_provider_proposer_candidate(
            provider_label="external-provider-label",
            model_label="external-model-label",
            raw_provider_output="Untrusted proposal data.",
            source_type=PROVIDER_CANDIDATE,
            extracted_title="AUTH-1D human review",
            extracted_intent="Display inert authority status.",
            extracted_summary="Untrusted proposal data.",
            proposed_artifact_path="reviews/auth-1d.md",
            proposed_artifact_content="Candidate content only.",
            created_at="2026-06-21T05:06:00Z",
            adapter_enabled=True,
        )
        conversion = convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash=candidate.candidate_hash,
            created_at="2026-06-21T05:07:00Z",
        )
        proposal = conversion.proposal
        self.assertIsNotNone(proposal)
        packet = create_review_packet_from_proposal(
            proposal=proposal,
            expected_proposal_hash=proposal.proposal_hash,
            created_at="2026-06-21T05:08:00Z",
            reviewer_label="local-human-reviewer",
            packet_purpose="AUTH-1D authority status attachment",
        )
        return proposal, packet


if __name__ == "__main__":
    unittest.main()
