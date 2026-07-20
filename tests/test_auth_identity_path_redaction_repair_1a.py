from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace

from runtime.approval_policy_bridge import (
    ApprovalPolicyBridgeStatus,
    build_approval_policy_evaluation_request,
    evaluate_approval_policy_bridge,
)
from runtime.approval_policy_projection import (
    ApprovalPolicyProjectionError,
    project_approval_policy_evaluation_for_human,
)
from runtime.auth_chain_assembler import (
    AuthChainAssemblyStatus,
    assemble_inert_auth_chain,
)
from runtime.execution_readiness_gate import (
    ExecutionReadinessRecord,
    ExecutionReadinessRejection,
    evaluate_execution_readiness,
)
from runtime.human_approval_gate import (
    HumanApprovalDecision,
    HumanApprovalGateError,
    HumanApprovalTargetType,
    build_hash_bound_human_approval_record,
    verify_hash_bound_human_approval_record,
)
from runtime.operator_review_surface import OperatorReviewSurface
from runtime.policy_profiles import (
    PolicyActionType,
    PolicyProfileName,
    build_policy_profile,
)
from runtime.proposal_intake import create_proposal_intake
from runtime.proposal_review_packet import create_review_packet_from_proposal
from runtime.provider_flow_audit import redact_audit_text


SOURCE_WORKTREE_PATH = (
    "/home/l/AOIA_PRODUCTION/worktrees/AOIA-Core-knowledge-provider-bridge-1a"
)
ORCHESTRA_WORKTREE_PATH = (
    "/home/l/AOIA_PRODUCTION/worktrees/"
    "AOIA-Core-epistemic-orchestra-contracts-cpt-1a"
)
LONG_BRANCH = "feature/epistemic-orchestra-contracts-cpt-1a"
HEAD_COMMIT = "33dfeb52263a50e23aa7edabdaab1fc47e60c9b9"
TARGET_HASH = hashlib.sha256(b"AUTH identity path repair target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"AUTH identity path repair audit").hexdigest()


class AuthIdentityPathRedactionRepairTests(unittest.TestCase):
    def test_required_human_readable_identities_remain_byte_exact(self):
        values = (
            SOURCE_WORKTREE_PATH,
            ORCHESTRA_WORKTREE_PATH,
            "feature/knowledge-provider-bridge-1a",
            LONG_BRANCH,
            "human-readable-lowercase-repository-identity-component-2026-1a",
            "AOIA-Core-Human-Readable-Identity-Repair-1A",
            hashlib.sha256(b"preserved hash identity").hexdigest(),
            "/srv/AOIA_TEAM/repositories/long-readable-repository-name-2026-1a",
        )

        for value in values:
            with self.subTest(value=value):
                self.assertEqual(value, redact_audit_text(value))

    def test_explicit_credentials_remain_redacted(self):
        credentials = (
            "sk-or-v1-" + "A1b2C3d4E5f6G7h8I9j0" * 2,
            "sk-" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0",
            "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1L2M3N4",
            "gho_" + "B2c3D4e5F6g7H8i9J0k1L2m3N4O5",
            "ghu_" + "C3d4E5f6G7h8I9j0K1l2M3n4O5P6",
            "ghs_" + "D4e5F6g7H8i9J0k1L2m3N4o5P6Q7",
            "ghr_" + "E5f6G7h8I9j0K1l2M3n4O5p6Q7R8",
            "github_pat_" + "F6g7H8i9J0k1L2m3N4o5P6q7R8S9",
            "Bearer AbCdEf0123456789.AbCdEf0123456789",
        )

        for credential in credentials:
            with self.subTest(credential=credential[:12]):
                redacted = redact_audit_text("prefix " + credential + " suffix")
                self.assertNotIn(credential, redacted)
                self.assertIn("[REDACTED]", redacted)

    def test_secret_assignments_and_known_secrets_remain_redacted(self):
        assignments = (
            "token=opaque-secret-value-1234567890",
            "api_key=opaque-secret-value-1234567890",
            "password=opaque-secret-value-1234567890",
            "authorization=opaque-secret-value-1234567890",
        )
        for assignment in assignments:
            with self.subTest(assignment=assignment.split("=", 1)[0]):
                self.assertEqual(
                    assignment.split("=", 1)[0] + "=[REDACTED]",
                    redact_audit_text(assignment),
                )

        known_secret = "caller-supplied-known-secret-value-9876543210"
        redacted = redact_audit_text(
            "before/" + known_secret + "/after",
            known_secrets=(known_secret,),
        )
        self.assertEqual("before/[REDACTED]/after", redacted)

    def test_opaque_high_entropy_candidates_remain_redacted(self):
        candidates = (
            "Ab9+/Cd8Ef7Gh6Ij5Kl4Mn3Op2Qr1St0Uv9Wx8Yz7Ab6Cd5Ef4Gh3==",
            "QWxhZGRpbjpvcGVuIHNlc2FtZV9xN3ZQMi14UjlLbTR6VDg",
            "QWxhZGRpbjpvcGVuU2VzYW1lVG9rZW4xMjM0NTY3ODkw",
            "qN7_vP2-xR9_Km4-zT8_Bc6-yH3_Wf5-aJ1_Ls0-Qe9_Rt4",
            "AbCdGh-IjKlMn-OpQrSt-UvWxYz-AbCdGh-IjKlMn-OpQrSt",
        )

        for candidate in candidates:
            with self.subTest(candidate=candidate[:12]):
                self.assertEqual("[REDACTED]", redact_audit_text(candidate))

    def test_readable_path_preserves_text_around_explicit_secret_segment(self):
        secret = "sk-" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6"
        prefix = "/srv/AOIA_TEAM/worktrees/Human-Readable-Repository-Identity-1A"
        source = prefix + "/" + secret + "/metadata"
        expected = prefix + "/[REDACTED]/metadata"

        self.assertEqual(expected, redact_audit_text(source))
        self.assertEqual(expected, redact_audit_text(expected))

    def test_redaction_is_idempotent(self):
        known_secret = "known-secret-material-for-idempotence-123456"
        values = (
            SOURCE_WORKTREE_PATH,
            "token=opaque-secret-value-1234567890",
            "Bearer AbCdEf0123456789.AbCdEf0123456789",
            "QWxhZGRpbjpvcGVuU2VzYW1lVG9rZW4xMjM0NTY3ODkw",
            "/srv/repository/" + known_secret + "/metadata",
        )
        for value in values:
            with self.subTest(value=value[:24]):
                first = redact_audit_text(value, known_secrets=(known_secret,))
                second = redact_audit_text(first, known_secrets=(known_secret,))
                self.assertEqual(first, second)

    def test_long_identity_survives_complete_inert_auth_chain(self):
        first_approval = self.make_approval()
        second_approval = self.make_approval()
        request = self.make_bridge_request(first_approval)
        bridge = evaluate_approval_policy_bridge(request)
        projection = project_approval_policy_evaluation_for_human(bridge)
        assembly = self.make_assembly(first_approval)
        readiness = evaluate_execution_readiness(assembly)
        surface = OperatorReviewSurface.summary_fields(readiness)

        self.assertEqual(request.repo_path, first_approval.repo_path)
        self.assertEqual(SOURCE_WORKTREE_PATH, first_approval.repo_path)
        self.assertEqual(first_approval.repo_path, bridge.repo_path)
        self.assertEqual(bridge.repo_path, projection.repo_path)
        self.assertNotIn("[REDACTED]", first_approval.repo_path)
        self.assertNotIn("[REDACTED]", bridge.branch)
        self.assertEqual(
            first_approval.approval_binding_hash,
            second_approval.approval_binding_hash,
        )
        self.assertEqual(
            first_approval.approval_binding_hash,
            request.approval_binding_hash,
        )
        self.assertEqual(
            request.approval_binding_hash,
            bridge.approval_binding_hash,
        )
        self.assertTrue(verify_hash_bound_human_approval_record(first_approval).valid)
        self.assertEqual(
            ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY,
            bridge.bridge_status,
        )
        self.assertEqual(bridge.evaluation_hash, projection.source_evaluation_hash)
        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY,
            assembly.assembly_status,
        )
        self.assertEqual(
            first_approval.approval_binding_hash,
            assembly.approval_binding_hash,
        )
        self.assertEqual(bridge.evaluation_hash, assembly.bridge_evaluation_hash)
        self.assertEqual(bridge.repo_path, assembly.repo_path)
        self.assertIsInstance(readiness, ExecutionReadinessRecord)
        self.assertEqual(assembly.assembly_hash, readiness.assembly_hash)
        self.assertTrue(surface["reviewable"])
        self.assertEqual("EXECUTION_READINESS_RECORD", surface["object_type"])
        self.assertEqual(readiness.readiness_hash, surface["surface_hash"])
        for value in (
            assembly.execution_authority,
            assembly.artifact_write_authority,
            assembly.provider_live_call_authority,
            assembly.github_authority,
            readiness.execution_allowed,
            readiness.dispatch_allowed,
            readiness.artifact_write_allowed,
            readiness.provider_call_allowed,
            readiness.github_action_allowed,
        ):
            self.assertFalse(value)

    def test_changed_identity_evidence_still_fails_closed(self):
        mutations = (
            {"repo_path": SOURCE_WORKTREE_PATH + "-other"},
            {"branch": LONG_BRANCH + "-other"},
            {"head_commit": "a" * 40},
            {"requested_target_hash": "b" * 64},
        )
        for mutation in mutations:
            with self.subTest(mutation=tuple(mutation)):
                assembly = self.make_assembly(self.make_approval(), **mutation)
                readiness = evaluate_execution_readiness(assembly)
                self.assertNotEqual(
                    AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY,
                    assembly.assembly_status,
                )
                self.assertFalse(assembly.execution_authority)
                self.assertIsInstance(readiness, ExecutionReadinessRejection)
                self.assertFalse(readiness.execution_allowed)

    def test_unsafe_identity_text_is_sanitized_or_rejected(self):
        control_path = SOURCE_WORKTREE_PATH + "\x1b[31m"
        control_approval = self.make_approval(repo_path=control_path)
        self.assertEqual(SOURCE_WORKTREE_PATH, control_approval.repo_path)
        self.assertNotEqual(control_path, control_approval.repo_path)
        self.assertNotEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY,
            self.make_assembly(control_approval, repo_path=control_path).assembly_status,
        )

        assignment_path = SOURCE_WORKTREE_PATH + "/token=unsafe-secret-value"
        assignment_approval = self.make_approval(repo_path=assignment_path)
        self.assertNotEqual(assignment_path, assignment_approval.repo_path)
        self.assertIn("[REDACTED]", assignment_approval.repo_path)

        provider_key = "sk-" + "Q1w2E3r4T5y6U7i8O9p0A1s2D3f4"
        unsafe_branch = "feature/" + provider_key
        branch_approval = self.make_approval(branch=unsafe_branch)
        self.assertNotEqual(unsafe_branch, branch_approval.branch)
        self.assertIn("[REDACTED]", branch_approval.branch)

        known_secret = "known-scope-secret-value-1234567890"
        scope_approval = self.make_approval(
            allowed_scope=("/srv/review/" + known_secret,),
            known_secrets=(known_secret,),
        )
        self.assertNotIn(known_secret, scope_approval.allowed_scope[0])
        self.assertIn("[REDACTED]", scope_approval.allowed_scope[0])

        with self.assertRaises(HumanApprovalGateError):
            self.make_approval(repo_path="")
        with self.assertRaises(HumanApprovalGateError):
            self.make_approval(branch="")

        unsafe_bridge = replace(
            self.make_bridge(self.make_approval()),
            repo_path=control_path,
        )
        with self.assertRaises(ApprovalPolicyProjectionError):
            project_approval_policy_evaluation_for_human(unsafe_bridge)

    @staticmethod
    def make_approval(**overrides):
        values = {
            "repo_path": SOURCE_WORKTREE_PATH,
            "branch": LONG_BRANCH,
            "head_commit": HEAD_COMMIT,
            "target_type": HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
            "target_hash": TARGET_HASH,
            "decision": HumanApprovalDecision.APPROVED,
            "provider_flow_audit_ref": "provider-g-auth-identity-repair",
            "provider_flow_audit_hash": AUDIT_HASH,
        }
        values.update(overrides)
        return build_hash_bound_human_approval_record(**values)

    @staticmethod
    def make_bridge(approval):
        return evaluate_approval_policy_bridge(
            AuthIdentityPathRedactionRepairTests.make_bridge_request(approval)
        )

    @staticmethod
    def make_bridge_request(approval):
        profile = build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY)
        return build_approval_policy_evaluation_request(
            repo_path=SOURCE_WORKTREE_PATH,
            branch=LONG_BRANCH,
            head_commit=HEAD_COMMIT,
            requested_action_type=PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
            requested_target_type=HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
            requested_target_hash=TARGET_HASH,
            requested_target_paths=(),
            approval_record=approval,
            policy_profile=profile,
            provider_flow_audit_hash=AUDIT_HASH,
            created_at_utc="2026-07-20T14:42:00Z",
        )

    @staticmethod
    def make_assembly(approval, **overrides):
        proposal = create_proposal_intake(
            title="AUTH identity path repair review",
            intent="Review byte-exact inert AUTH identity evidence.",
            summary="No execution or write authority is created.",
            source_type="LOCAL_AUTH_REVIEW",
            source_label="auth-identity-path-repair-1a",
            created_at="2026-07-20T14:40:00Z",
        )
        packet = create_review_packet_from_proposal(
            proposal=proposal,
            expected_proposal_hash=proposal.proposal_hash,
            created_at="2026-07-20T14:41:00Z",
            reviewer_label="local-human-reviewer",
            packet_purpose="AUTH identity path repair review",
        )
        values = {
            "repo_path": SOURCE_WORKTREE_PATH,
            "branch": LONG_BRANCH,
            "head_commit": HEAD_COMMIT,
            "requested_action_type": (
                PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD
            ),
            "requested_target_type": HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
            "requested_target_hash": TARGET_HASH,
            "requested_target_paths": (),
            "approval_record": approval,
            "policy_profile": build_policy_profile(
                PolicyProfileName.PROVIDER_REVIEW_ONLY
            ),
            "base_proposal": proposal,
            "base_review_packet": packet,
            "provider_flow_audit_hash": AUDIT_HASH,
            "created_at_utc": "2026-07-20T14:42:00Z",
        }
        values.update(overrides)
        return assemble_inert_auth_chain(**values)


if __name__ == "__main__":
    unittest.main()
