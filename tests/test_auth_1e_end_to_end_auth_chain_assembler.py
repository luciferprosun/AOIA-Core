from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from runtime.auth_chain_assembler import (
    ASSEMBLY_NOT_AUTHORITY,
    AUTH_CHAIN_ASSEMBLED_NO_EXECUTION,
    AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION,
    DEFAULT_DENY_ON_INVALID_CHAIN,
    END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY,
    INERT_AUTH_CHAIN_ASSEMBLY,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_GITHUB_ACTION,
    NO_PROVIDER_LIVE_CALL,
    NO_PROVIDER_TRUST_CHANGE,
    REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION,
    AuthChainAssemblyStatus,
    assemble_inert_auth_chain,
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
from runtime.proposal_intake import create_proposal_intake
from runtime.proposal_review_packet import create_review_packet_from_proposal


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "auth_chain_assembler.py"
THIS_FILE = Path(__file__).resolve()
HEAD_COMMIT = "1381500e05644ef9870c3c85e57ac2c14d75422e"
TARGET_HASH = hashlib.sha256(b"AUTH-1E exact target").hexdigest()
OTHER_HASH = hashlib.sha256(b"AUTH-1E other target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"AUTH-1E provider audit").hexdigest()


class Auth1EEndToEndAuthChainAssemblerTests(unittest.TestCase):
    def test_record_only_chain_assembles_with_required_contract(self):
        result = self.assemble()

        self.assertEqual(INERT_AUTH_CHAIN_ASSEMBLY, result.label)
        self.assertEqual(AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION, result.schema_version)
        self.assertEqual(END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY, result.assembly_role)
        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY,
            result.assembly_status,
        )
        self.assertEqual(AUTH_CHAIN_ASSEMBLED_NO_EXECUTION, result.final_status)
        self.assertTrue(result.authority_status_present)

    def test_proposal_denied_and_future_chains_preserve_status(self):
        proposal = self.assemble(
            target_type=HumanApprovalTargetType.DIFF,
            action=PolicyActionType.BUILD_PATCH_PROPOSAL,
            profile_name=PolicyProfileName.PROPOSE_ONLY,
        )
        denied = self.assemble(profile_name=PolicyProfileName.DENY_ALL)
        future = self.assemble(
            target_type=HumanApprovalTargetType.COMMAND,
            action=PolicyActionType.RUN_TEST_COMMAND,
            profile_name=PolicyProfileName.PROPOSE_ONLY,
        )

        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_PROPOSAL_ONLY,
            proposal.assembly_status,
        )
        self.assertEqual(AuthChainAssemblyStatus.AUTH_CHAIN_DENIED, denied.assembly_status)
        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_REQUIRES_FUTURE_MILESTONE,
            future.assembly_status,
        )
        self.assertEqual("NOT_ALLOWED", denied.review_packet.authority_status.allowed_as)
        self.assertEqual(
            "FUTURE_MILESTONE_REQUIRED",
            future.review_packet.authority_status.allowed_as,
        )

    def test_invalid_approval_or_policy_fails_closed(self):
        approval = self.make_approval()
        policy = build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY)
        invalid_approval = self.assemble(
            approval_record=replace(approval, approval_binding_hash="f" * 64)
        )
        invalid_policy = self.assemble(
            policy_profile=replace(policy, policy_hash="f" * 64)
        )

        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
            invalid_approval.assembly_status,
        )
        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
            invalid_policy.assembly_status,
        )
        self.assertFalse(invalid_approval.authority_status_present)

    def test_request_binding_mismatches_are_denied_or_invalid(self):
        mutations = (
            {"requested_target_hash": OTHER_HASH},
            {"repo_path": "/tmp/other-repo"},
            {"branch": "feature/other"},
            {"head_commit": "a" * 40},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = self.assemble(**mutation)
                self.assertIn(
                    result.assembly_status,
                    {
                        AuthChainAssemblyStatus.AUTH_CHAIN_DENIED,
                        AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
                    },
                )
                self.assertFalse(result.execution_authority)

    def test_outside_and_forbidden_paths_are_denied(self):
        profile = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            allowed_scope=(str(REPO_ROOT / "runtime"),),
            forbidden_scope=(str(REPO_ROOT / "runtime" / "private"),),
        )
        approval = self.make_approval(target_type=HumanApprovalTargetType.DIFF)
        outside = self.assemble(
            approval_record=approval,
            policy_profile=profile,
            target_type=HumanApprovalTargetType.DIFF,
            action=PolicyActionType.BUILD_PATCH_PROPOSAL,
            requested_target_paths=(str(REPO_ROOT / "tests" / "outside.py"),),
        )
        forbidden = self.assemble(
            approval_record=approval,
            policy_profile=profile,
            target_type=HumanApprovalTargetType.DIFF,
            action=PolicyActionType.BUILD_PATCH_PROPOSAL,
            requested_target_paths=(str(REPO_ROOT / "runtime" / "private" / "blocked.py"),),
        )

        self.assertEqual(AuthChainAssemblyStatus.AUTH_CHAIN_DENIED, outside.assembly_status)
        self.assertEqual(AuthChainAssemblyStatus.AUTH_CHAIN_DENIED, forbidden.assembly_status)

    def test_source_hashes_and_authority_status_are_preserved(self):
        approval = self.make_approval()
        policy = build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY)
        result = self.assemble(approval_record=approval, policy_profile=policy)
        authority = result.review_packet.authority_status

        self.assertEqual(approval.approval_binding_hash, result.approval_binding_hash)
        self.assertEqual(policy.policy_hash, result.policy_hash)
        self.assertRegex(result.bridge_evaluation_hash, r"^[0-9a-f]{64}$")
        self.assertEqual(AUDIT_HASH, result.provider_flow_audit_hash)
        self.assertEqual(result.bridge_status, authority.source_bridge_status)
        self.assertEqual(result.bridge_evaluation_hash, authority.source_evaluation_hash)
        self.assertTrue(authority.blocked_capabilities)
        self.assertTrue(authority.required_next_human_step)

    def test_missing_sources_never_allow_chain(self):
        proposal, packet = self.make_proposal_and_packet()
        cases = (
            {"approval_record": None},
            {"policy_profile": None},
            {"base_proposal": None},
            {"base_review_packet": None},
            {
                "approval_record": None,
                "policy_profile": None,
                "base_proposal": proposal,
                "base_review_packet": packet,
            },
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                result = self.assemble(**overrides)
                self.assertEqual(
                    AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
                    result.assembly_status,
                )
                self.assertFalse(result.execution_authority)

    def test_prebuilt_intermediate_objects_cannot_bypass_required_chain(self):
        parameters = inspect.signature(assemble_inert_auth_chain).parameters
        self.assertNotIn("bridge_result", parameters)
        self.assertNotIn("human_projection", parameters)
        self.assertNotIn("review_projection", parameters)

        proposal, packet = self.make_proposal_and_packet()
        packet_alone = self.assemble(
            approval_record=None,
            policy_profile=None,
            base_proposal=proposal,
            base_review_packet=packet,
        )
        self.assertEqual(
            AuthChainAssemblyStatus.AUTH_CHAIN_INVALID,
            packet_alone.assembly_status,
        )

    def test_all_authority_flags_and_boundaries_remain_inert(self):
        result = self.assemble()
        boundaries = {item.value for item in result.safety_boundaries}

        self.assertFalse(result.execution_authority)
        self.assertFalse(result.artifact_write_authority)
        self.assertFalse(result.provider_live_call_authority)
        self.assertFalse(result.provider_trust_authority)
        self.assertFalse(result.github_authority)
        self.assertFalse(result.canonical_promotion_authority)
        self.assertTrue(
            {
                NO_EXECUTION,
                NO_ARTIFACT_WRITE,
                NO_PROVIDER_LIVE_CALL,
                NO_PROVIDER_TRUST_CHANGE,
                NO_GITHUB_ACTION,
                NO_CANONICAL_PROMOTION,
                ASSEMBLY_NOT_AUTHORITY,
                REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION,
                DEFAULT_DENY_ON_INVALID_CHAIN,
            }.issubset(boundaries)
        )

    def test_assembly_hash_is_deterministic_and_timestamp_independent(self):
        first = self.assemble(created_at_utc="2026-06-21T05:49:00Z")
        second = self.assemble(created_at_utc="2026-06-21T05:50:00Z")
        self.assertEqual(first.assembly_hash, second.assembly_hash)
        self.assertNotEqual(first.created_at_utc, second.created_at_utc)

    def test_source_hash_changes_change_assembly_hash(self):
        baseline = self.assemble()
        approval_changed = self.assemble(
            approval_record=self.make_approval(
                decision=HumanApprovalDecision.REJECTED,
            )
        )
        policy_changed = self.assemble(
            policy_profile=build_policy_profile(
                PolicyProfileName.PROVIDER_REVIEW_ONLY,
                allowed_scope=("*",),
            )
        )
        bridge_changed = self.assemble(
            target_type=HumanApprovalTargetType.DIFF,
            action=PolicyActionType.BUILD_PATCH_PROPOSAL,
            profile_name=PolicyProfileName.PROPOSE_ONLY,
        )

        self.assertNotEqual(
            baseline.approval_binding_hash,
            approval_changed.approval_binding_hash,
        )
        self.assertNotEqual(baseline.policy_hash, policy_changed.policy_hash)
        self.assertNotEqual(
            baseline.bridge_evaluation_hash,
            bridge_changed.bridge_evaluation_hash,
        )
        for changed in (approval_changed, policy_changed, bridge_changed):
            self.assertNotEqual(baseline.assembly_hash, changed.assembly_hash)

    def test_inputs_are_not_mutated_and_result_is_json_serializable(self):
        approval = self.make_approval()
        policy = build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY)
        proposal, packet = self.make_proposal_and_packet()
        before = (
            deepcopy(approval.to_dict()),
            deepcopy(policy.to_dict()),
            deepcopy(proposal.to_dict()),
            deepcopy(packet.to_dict()),
        )

        result = self.assemble(
            approval_record=approval,
            policy_profile=policy,
            base_proposal=proposal,
            base_review_packet=packet,
        )

        self.assertIsInstance(json.dumps(result.to_dict()), str)
        self.assertEqual(before[0], approval.to_dict())
        self.assertEqual(before[1], policy.to_dict())
        self.assertEqual(before[2], proposal.to_dict())
        self.assertEqual(before[3], packet.to_dict())

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

    def assemble(self, **overrides):
        proposal, packet = self.make_proposal_and_packet()
        target_type = overrides.pop(
            "target_type",
            HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
        )
        action = overrides.pop(
            "action",
            PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
        )
        profile_name = overrides.pop(
            "profile_name",
            PolicyProfileName.PROVIDER_REVIEW_ONLY,
        )
        values = {
            "repo_path": str(REPO_ROOT),
            "branch": "feature/m2-b0-provider-critic-inert-core",
            "head_commit": HEAD_COMMIT,
            "requested_action_type": action,
            "requested_target_type": target_type,
            "requested_target_hash": TARGET_HASH,
            "requested_target_paths": (),
            "approval_record": self.make_approval(target_type=target_type),
            "policy_profile": build_policy_profile(profile_name),
            "base_proposal": proposal,
            "base_review_packet": packet,
            "provider_flow_audit_hash": AUDIT_HASH,
            "created_at_utc": "2026-06-21T05:49:00Z",
        }
        values.update(overrides)
        return assemble_inert_auth_chain(**values)

    def make_approval(self, **overrides):
        values = {
            "repo_path": str(REPO_ROOT),
            "branch": "feature/m2-b0-provider-critic-inert-core",
            "head_commit": HEAD_COMMIT,
            "target_type": HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
            "target_hash": TARGET_HASH,
            "decision": HumanApprovalDecision.APPROVED,
            "provider_flow_audit_ref": "provider-g-record",
            "provider_flow_audit_hash": AUDIT_HASH,
        }
        values.update(overrides)
        return build_hash_bound_human_approval_record(**values)

    def make_proposal_and_packet(self):
        proposal = create_proposal_intake(
            title="AUTH-1E review chain",
            intent="Display inert assembled authority state.",
            summary="Inert AUTH chain review data.",
            source_type="LOCAL_AUTH_REVIEW",
            source_label="auth-1e-test",
            created_at="2026-06-21T05:47:00Z",
        )
        packet = create_review_packet_from_proposal(
            proposal=proposal,
            expected_proposal_hash=proposal.proposal_hash,
            created_at="2026-06-21T05:48:00Z",
            reviewer_label="local-human-reviewer",
            packet_purpose="AUTH-1E end-to-end review",
        )
        return proposal, packet


if __name__ == "__main__":
    unittest.main()
