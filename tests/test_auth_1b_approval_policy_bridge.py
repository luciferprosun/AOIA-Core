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
    APPROVAL_NOT_EXECUTION_AUTHORITY,
    APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION,
    APPROVAL_POLICY_EVALUATED_NO_EXECUTION,
    APPROVAL_POLICY_EVALUATION_BRIDGE,
    DEFAULT_DENY,
    HASH_MATCH_REQUIRED,
    INERT_APPROVAL_POLICY_EVALUATOR,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_GITHUB_ACTION,
    NO_PROVIDER_LIVE_CALL,
    NO_PROVIDER_TRUST_CHANGE,
    POLICY_NOT_EXECUTION_AUTHORITY,
    ApprovalPolicyBridgeError,
    ApprovalPolicyBridgeStatus,
    build_approval_policy_evaluation_request,
    evaluate_approval_policy_bridge,
)
from runtime.human_approval_gate import (
    HumanApprovalDecision,
    HumanApprovalTargetType,
    build_hash_bound_human_approval_record,
)
from runtime.policy_profiles import (
    PolicyActionType,
    PolicyDecision,
    PolicyProfileName,
    build_policy_profile,
)
from runtime.provider_controlled_flow import run_mock_provider_controlled_flow
from runtime.provider_critic_review import review_provider_controlled_flow
from runtime.provider_flow_audit import build_provider_flow_audit_record
from runtime.provider_live_adapter import DefaultOffProviderAdapter, LiveProviderAdapterRequest
from runtime.provider_request_flow import ProviderRequest, decide_mock_provider_request
from runtime.provider_review_projection import build_provider_review_projection


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "approval_policy_bridge.py"
THIS_FILE = Path(__file__).resolve()
HEAD_COMMIT = "13bb450ee3000e32f8a1c51e0d6f10e042c7452a"
TARGET_HASH = hashlib.sha256(b"exact bridge target").hexdigest()
OTHER_HASH = hashlib.sha256(b"different bridge target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"provider flow audit").hexdigest()


class Auth1BApprovalPolicyBridgeTests(unittest.TestCase):
    def test_matching_approved_record_policy_is_allowed_record_only(self):
        result = self.evaluate_record_action()

        self.assertEqual(APPROVAL_POLICY_EVALUATION_BRIDGE, result.label)
        self.assertEqual(APPROVAL_POLICY_BRIDGE_SCHEMA_VERSION, result.schema_version)
        self.assertEqual(INERT_APPROVAL_POLICY_EVALUATOR, result.bridge_role)
        self.assertEqual(ApprovalPolicyBridgeStatus.ALLOWED_RECORD_ONLY, result.bridge_status)
        self.assertEqual(PolicyDecision.ALLOW_RECORD_ONLY.value, result.policy_decision)
        self.assertEqual(APPROVAL_POLICY_EVALUATED_NO_EXECUTION, result.final_status)

    def test_matching_approved_record_policy_is_allowed_proposal_only(self):
        approval = self.make_approval(target_type=HumanApprovalTargetType.DIFF)
        profile = build_policy_profile(PolicyProfileName.PROPOSE_ONLY)
        result = self.evaluate(
            approval_record=approval,
            policy_profile=profile,
            requested_action_type=PolicyActionType.BUILD_PATCH_PROPOSAL,
            requested_target_type=HumanApprovalTargetType.DIFF,
        )

        self.assertEqual(ApprovalPolicyBridgeStatus.ALLOWED_PROPOSAL_ONLY, result.bridge_status)
        self.assertEqual(PolicyDecision.ALLOW_PROPOSAL_ONLY.value, result.policy_decision)

    def test_rejected_and_needs_changes_decisions_deny(self):
        for decision in (
            HumanApprovalDecision.REJECTED,
            HumanApprovalDecision.NEEDS_CHANGES,
        ):
            with self.subTest(decision=decision):
                approval = self.make_approval(decision=decision)
                result = self.evaluate_record_action(approval_record=approval)
                self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, result.bridge_status)
                self.assertFalse(result.execution_authority)

    def test_missing_approval_or_policy_denies(self):
        missing_approval = self.evaluate_record_action(approval_record=None)
        missing_policy = self.evaluate_record_action(policy_profile=None)
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, missing_approval.bridge_status)
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, missing_policy.bridge_status)

    def test_invalid_or_mismatched_approval_binding_denies(self):
        approval = self.make_approval()
        invalid_record = replace(approval, approval_binding_hash="f" * 64)
        invalid = self.evaluate_record_action(approval_record=invalid_record)
        mismatched = self.evaluate_record_action(
            approval_record=approval,
            approval_binding_hash="e" * 64,
        )
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, invalid.bridge_status)
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, mismatched.bridge_status)

    def test_target_hash_invalid_or_mismatched_denies(self):
        invalid = self.evaluate_record_action(requested_target_hash="not-a-hash")
        mismatched = self.evaluate_record_action(requested_target_hash=OTHER_HASH)
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, invalid.bridge_status)
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, mismatched.bridge_status)

    def test_repo_branch_head_and_target_type_mismatch_deny(self):
        mutations = (
            {"repo_path": "/tmp/other-repo"},
            {"branch": "feature/other"},
            {"head_commit": "a" * 40},
            {"requested_target_type": HumanApprovalTargetType.PLAN},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = self.evaluate_record_action(**mutation)
                self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, result.bridge_status)

    def test_requested_path_outside_or_forbidden_scope_denies(self):
        profile = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            allowed_scope=(str(REPO_ROOT / "runtime"),),
            forbidden_scope=(str(REPO_ROOT / "runtime" / "private"),),
        )
        approval = self.make_approval(target_type=HumanApprovalTargetType.DIFF)
        outside = self.evaluate(
            approval_record=approval,
            policy_profile=profile,
            requested_action_type=PolicyActionType.BUILD_PATCH_PROPOSAL,
            requested_target_type=HumanApprovalTargetType.DIFF,
            requested_target_paths=(str(REPO_ROOT / "tests" / "outside.py"),),
        )
        forbidden = self.evaluate(
            approval_record=approval,
            policy_profile=profile,
            requested_action_type=PolicyActionType.BUILD_PATCH_PROPOSAL,
            requested_target_type=HumanApprovalTargetType.DIFF,
            requested_target_paths=(str(REPO_ROOT / "runtime" / "private" / "blocked.py"),),
        )
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, outside.bridge_status)
        self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, forbidden.bridge_status)

    def test_unknown_action_or_policy_and_explicit_policy_deny(self):
        unknown_action = self.evaluate_record_action(requested_action_type="UNKNOWN_ACTION")
        unknown_policy = self.evaluate_record_action(policy_profile="UNKNOWN_PROFILE")
        policy_deny = self.evaluate_record_action(
            policy_profile=build_policy_profile(PolicyProfileName.DENY_ALL)
        )
        invalid_policy_hash = self.evaluate_record_action(
            policy_profile=replace(
                build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY),
                policy_hash="f" * 64,
            )
        )
        for result in (
            unknown_action,
            unknown_policy,
            policy_deny,
            invalid_policy_hash,
        ):
            self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, result.bridge_status)

    def test_future_milestone_does_not_grant_authority(self):
        approval = self.make_approval(target_type=HumanApprovalTargetType.COMMAND)
        result = self.evaluate(
            approval_record=approval,
            policy_profile=build_policy_profile(PolicyProfileName.PROPOSE_ONLY),
            requested_action_type=PolicyActionType.RUN_SHELL_COMMAND,
            requested_target_type=HumanApprovalTargetType.COMMAND,
        )
        self.assertEqual(
            ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE,
            result.bridge_status,
        )
        self.assertFalse(result.execution_authority)

    def test_approval_provider_audit_or_policy_presence_alone_never_executes(self):
        approval_only = self.evaluate_record_action(policy_profile=None)
        policy_only = self.evaluate_record_action(approval_record=None)
        audit_only = self.evaluate_record_action(
            approval_record=None,
            provider_flow_audit_hash=AUDIT_HASH,
        )
        for result in (approval_only, policy_only, audit_only):
            self.assertEqual(ApprovalPolicyBridgeStatus.DENIED, result.bridge_status)
            self.assertFalse(result.execution_authority)

    def test_every_operational_action_is_denied_or_future_only(self):
        operational = (
            PolicyActionType.CALL_LIVE_PROVIDER,
            PolicyActionType.WRITE_FILE,
            PolicyActionType.WRITE_ARTIFACT,
            PolicyActionType.RUN_SHELL_COMMAND,
            PolicyActionType.RUN_TEST_COMMAND,
            PolicyActionType.GIT_COMMIT,
            PolicyActionType.GITHUB_PUSH,
            PolicyActionType.GITHUB_PR,
            PolicyActionType.PROMOTE_CANONICAL_KNOWLEDGE,
        )
        approval = self.make_approval(target_type=HumanApprovalTargetType.OTHER)
        for action in operational:
            with self.subTest(action=action):
                result = self.evaluate(
                    approval_record=approval,
                    policy_profile=build_policy_profile(PolicyProfileName.PROPOSE_ONLY),
                    requested_action_type=action,
                    requested_target_type=HumanApprovalTargetType.OTHER,
                )
                self.assertIn(
                    result.bridge_status,
                    {
                        ApprovalPolicyBridgeStatus.DENIED,
                        ApprovalPolicyBridgeStatus.REQUIRES_FUTURE_MILESTONE,
                    },
                )
                self.assertFalse(result.execution_authority)
                self.assertFalse(result.artifact_write_authority)
                self.assertFalse(result.provider_live_call_authority)
                self.assertFalse(result.provider_trust_authority)
                self.assertFalse(result.github_authority)
                self.assertFalse(result.canonical_promotion_authority)

    def test_allowed_result_has_all_boundaries_and_no_authority(self):
        result = self.evaluate_record_action()
        boundaries = {item.value for item in result.safety_boundaries}
        self.assertTrue(
            {
                NO_EXECUTION,
                NO_ARTIFACT_WRITE,
                NO_PROVIDER_LIVE_CALL,
                NO_PROVIDER_TRUST_CHANGE,
                NO_GITHUB_ACTION,
                NO_CANONICAL_PROMOTION,
                APPROVAL_NOT_EXECUTION_AUTHORITY,
                POLICY_NOT_EXECUTION_AUTHORITY,
                HASH_MATCH_REQUIRED,
                DEFAULT_DENY,
            }.issubset(boundaries)
        )
        self.assertFalse(result.execution_authority)
        self.assertFalse(result.artifact_write_authority)
        self.assertFalse(result.provider_live_call_authority)
        self.assertFalse(result.provider_trust_authority)
        self.assertFalse(result.github_authority)
        self.assertFalse(result.canonical_promotion_authority)

    def test_evaluation_hash_is_deterministic_and_timestamp_independent(self):
        first = self.evaluate_record_action(created_at_utc="2026-06-20T22:08:00Z")
        second = self.evaluate_record_action(created_at_utc="2026-06-20T22:09:00Z")
        self.assertEqual(first.evaluation_hash, second.evaluation_hash)
        self.assertNotEqual(first.created_at_utc, second.created_at_utc)

    def test_semantic_changes_change_evaluation_hash(self):
        baseline = self.evaluate_record_action()
        action_changed = self.evaluate_record_action(
            requested_action_type=PolicyActionType.READ_CONTEXT
        )
        rejected = self.evaluate_record_action(
            approval_record=self.make_approval(decision=HumanApprovalDecision.REJECTED)
        )
        profile_changed = self.evaluate_record_action(
            policy_profile=build_policy_profile(PolicyProfileName.DENY_ALL)
        )
        policy_hash_changed = self.evaluate_record_action(
            policy_profile=replace(
                build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY),
                policy_hash="f" * 64,
            )
        )
        for changed in (
            action_changed,
            rejected,
            profile_changed,
            policy_hash_changed,
        ):
            self.assertNotEqual(baseline.evaluation_hash, changed.evaluation_hash)

    def test_result_serializes_and_inputs_are_not_mutated(self):
        approval = self.make_approval()
        profile = build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY)
        approval_before = deepcopy(approval.to_dict())
        profile_before = deepcopy(profile.to_dict())
        result = self.evaluate_record_action(
            approval_record=approval,
            policy_profile=profile,
        )
        self.assertIsInstance(json.dumps(result.to_dict()), str)
        self.assertEqual(approval_before, approval.to_dict())
        self.assertEqual(profile_before, profile.to_dict())

    def test_provider_g_record_is_not_mutated(self):
        provider_record = self.make_provider_g_record()
        before = deepcopy(provider_record.to_dict())
        approval = self.make_approval(
            provider_flow_audit_hash=provider_record.content_hash,
        )
        self.evaluate_record_action(
            approval_record=approval,
            provider_flow_audit_hash=provider_record.content_hash,
        )
        self.assertEqual(before, provider_record.to_dict())

    def test_malformed_request_fails_closed(self):
        with self.assertRaises(ApprovalPolicyBridgeError):
            build_approval_policy_evaluation_request(
                repo_path=str(REPO_ROOT),
                branch="",
                head_commit=HEAD_COMMIT,
                requested_action_type=PolicyActionType.READ_CONTEXT,
                requested_target_type=HumanApprovalTargetType.OTHER,
                requested_target_hash=TARGET_HASH,
                approval_record=None,
                policy_profile=None,
            )
        with self.assertRaises(ApprovalPolicyBridgeError):
            evaluate_approval_policy_bridge({})

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
        forbidden_calls = (
            "os.system(",
            "P" + "open(",
            "eval(",
            "exec(",
            "write_text(",
            "write_bytes(",
            "open(",
            "write_sandbox_artifact(",
            "evaluate_pre_artifact_approval_gate(",
        )
        forbidden_imports = (
            "runtime.safety.sandbox_artifact_runner",
            "runtime.safety.approval_gate",
            "runtime.provider_live_adapter",
        )
        for value in (*forbidden_calls, *forbidden_imports):
            self.assertNotIn(value, source)
        self.assertIsNone(
            re.search(r"^\s*(from|import)\s+(os|shutil|pathlib)\b", source, re.MULTILINE)
        )

    def evaluate_record_action(self, **overrides):
        values = {
            "approval_record": self.make_approval(),
            "policy_profile": build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY),
            "requested_action_type": PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
            "requested_target_type": HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
        }
        values.update(overrides)
        return self.evaluate(**values)

    def evaluate(self, **overrides):
        values = {
            "repo_path": str(REPO_ROOT),
            "branch": "feature/m2-b0-provider-critic-inert-core",
            "head_commit": HEAD_COMMIT,
            "requested_action_type": PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
            "requested_target_type": HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
            "requested_target_hash": TARGET_HASH,
            "requested_target_paths": (),
            "approval_record": self.make_approval(),
            "policy_profile": build_policy_profile(PolicyProfileName.PROVIDER_REVIEW_ONLY),
            "provider_flow_audit_hash": AUDIT_HASH,
            "created_at_utc": "2026-06-20T22:08:00Z",
        }
        values.update(overrides)
        request = build_approval_policy_evaluation_request(**values)
        return evaluate_approval_policy_bridge(request)

    def make_approval(self, **overrides):
        values = {
            "repo_path": str(REPO_ROOT),
            "branch": "feature/m2-b0-provider-critic-inert-core",
            "head_commit": HEAD_COMMIT,
            "target_type": HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
            "target_hash": TARGET_HASH,
            "decision": HumanApprovalDecision.APPROVED,
            "allowed_scope": ("record",),
            "forbidden_scope": ("execute", "write"),
            "provider_flow_audit_ref": "provider-g-record",
            "provider_flow_audit_hash": AUDIT_HASH,
        }
        values.update(overrides)
        return build_hash_bound_human_approval_record(**values)

    def make_provider_g_record(self):
        request = ProviderRequest(
            provider_id="openrouter",
            task_text="Create inert bridge audit context.",
            purpose="AUTH-1B immutability test",
            caller_label="auth-1b-test",
            live_call_requested=False,
            metadata={"mode": "caller-supplied-output"},
        )
        decision = decide_mock_provider_request(request)
        flow = run_mock_provider_controlled_flow(
            request=request,
            registry_decision=decision,
            model_label="mock-auth-1b-model",
            mock_response_text="Deterministic inert provider output.",
        )
        critic = review_provider_controlled_flow(flow)
        live = DefaultOffProviderAdapter().evaluate(
            adapter_request=LiveProviderAdapterRequest(
                request=request,
                model_label="future-auth-1b-model",
                manual_live_call_requested=False,
                adapter_metadata={"mode": "default-off"},
            ),
            registry_decision=decision,
            budget_limit=None,
        )
        projection = build_provider_review_projection(
            controlled_flow=flow,
            critic_review=critic,
            live_adapter_status=live,
        )
        return build_provider_flow_audit_record(projection)


if __name__ == "__main__":
    unittest.main()
