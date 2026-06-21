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
    ApprovalPolicyBridgeStatus,
    build_approval_policy_evaluation_request,
    evaluate_approval_policy_bridge,
)
from runtime.approval_policy_projection import (
    APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION,
    APPROVAL_POLICY_PROJECTION_SCHEMA_VERSION,
    FUTURE_MILESTONE_REQUIRED,
    HUMAN_READABLE_AUTHORITY_STATUS_ONLY,
    HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION,
    HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY,
    NOT_ALLOWED,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_GITHUB_ACTION,
    NO_PROVIDER_LIVE_CALL,
    NO_PROVIDER_TRUST_CHANGE,
    PROJECTION_NOT_AUTHORITY,
    PROPOSAL_ONLY,
    RECORD_ONLY,
    ApprovalPolicyAllowedAs,
    ApprovalPolicyProjectionError,
    project_approval_policy_evaluation_for_human,
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


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "approval_policy_projection.py"
THIS_FILE = Path(__file__).resolve()
HEAD_COMMIT = "a01b9127fb38d90fc746981fffb1f316efdad0b5"
TARGET_HASH = hashlib.sha256(b"AUTH-1C exact target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"AUTH-1C provider audit").hexdigest()


class Auth1CApprovalPolicyProjectionTests(unittest.TestCase):
    def test_record_only_projection_has_required_contract(self):
        bridge = self.make_bridge()
        projection = project_approval_policy_evaluation_for_human(bridge)

        self.assertEqual(APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION, projection.label)
        self.assertEqual(
            APPROVAL_POLICY_PROJECTION_SCHEMA_VERSION,
            projection.schema_version,
        )
        self.assertEqual(
            HUMAN_READABLE_AUTHORITY_STATUS_ONLY,
            projection.projection_role,
        )
        self.assertEqual(RECORD_ONLY, projection.allowed_as.value)
        self.assertEqual(
            HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION,
            projection.final_status,
        )

    def test_proposal_denied_and_future_statuses_map_without_upgrade(self):
        proposal = project_approval_policy_evaluation_for_human(
            self.make_bridge(
                target_type=HumanApprovalTargetType.DIFF,
                action=PolicyActionType.BUILD_PATCH_PROPOSAL,
                profile_name=PolicyProfileName.PROPOSE_ONLY,
            )
        )
        denied = project_approval_policy_evaluation_for_human(
            self.make_bridge(profile_name=PolicyProfileName.DENY_ALL)
        )
        future = project_approval_policy_evaluation_for_human(
            self.make_bridge(
                target_type=HumanApprovalTargetType.COMMAND,
                action=PolicyActionType.RUN_TEST_COMMAND,
                profile_name=PolicyProfileName.PROPOSE_ONLY,
            )
        )

        self.assertEqual(PROPOSAL_ONLY, proposal.allowed_as.value)
        self.assertEqual(NOT_ALLOWED, denied.allowed_as.value)
        self.assertEqual(FUTURE_MILESTONE_REQUIRED, future.allowed_as.value)
        self.assertEqual(
            ApprovalPolicyBridgeStatus.DENIED.value,
            denied.source_bridge_status,
        )
        self.assertFalse(denied.execution_authority)

    def test_source_identity_and_decisions_are_preserved(self):
        bridge = self.make_bridge()
        projection = project_approval_policy_evaluation_for_human(bridge)

        self.assertEqual(bridge.label, projection.source_bridge_label)
        self.assertEqual(bridge.bridge_status.value, projection.source_bridge_status)
        self.assertEqual(bridge.evaluation_hash, projection.source_evaluation_hash)
        self.assertEqual(bridge.repo_path, projection.repo_path)
        self.assertEqual(bridge.branch, projection.branch)
        self.assertEqual(bridge.head_commit, projection.head_commit)
        self.assertEqual(bridge.requested_action_type, projection.requested_action_type)
        self.assertEqual(bridge.requested_target_type, projection.requested_target_type)
        self.assertEqual(bridge.requested_target_hash, projection.requested_target_hash)
        self.assertEqual(bridge.requested_target_paths, projection.requested_target_paths)
        self.assertEqual(bridge.approval_decision, projection.approval_decision)
        self.assertEqual(bridge.policy_profile_name, projection.policy_profile_name)
        self.assertEqual(bridge.policy_decision, projection.policy_decision)

    def test_human_explanation_authority_summary_and_blocked_capabilities_exist(self):
        projection = project_approval_policy_evaluation_for_human(self.make_bridge())

        self.assertTrue(projection.plain_language_summary)
        self.assertTrue(projection.plain_language_reason)
        self.assertTrue(projection.required_next_human_step)
        self.assertEqual(
            {
                "execution_authority": False,
                "artifact_write_authority": False,
                "provider_live_call_authority": False,
                "provider_trust_authority": False,
                "github_authority": False,
                "canonical_promotion_authority": False,
            },
            projection.authority_summary,
        )
        self.assertTrue(
            {
                "EXECUTION",
                "ARTIFACT_WRITE",
                "PROVIDER_LIVE_CALL",
                "PROVIDER_TRUST_CHANGE",
                "GITHUB_ACTION",
                "CANONICAL_PROMOTION",
            }.issubset(set(projection.blocked_capabilities))
        )

    def test_allowed_projection_retains_no_authority(self):
        projection = project_approval_policy_evaluation_for_human(self.make_bridge())

        self.assertEqual(ApprovalPolicyAllowedAs.RECORD_ONLY, projection.allowed_as)
        self.assertFalse(projection.execution_authority)
        self.assertFalse(projection.artifact_write_authority)
        self.assertFalse(projection.provider_live_call_authority)
        self.assertFalse(projection.provider_trust_authority)
        self.assertFalse(projection.github_authority)
        self.assertFalse(projection.canonical_promotion_authority)

    def test_projection_safety_boundaries_are_complete(self):
        projection = project_approval_policy_evaluation_for_human(self.make_bridge())
        boundaries = {item.value for item in projection.safety_boundaries}

        self.assertTrue(
            {
                NO_EXECUTION,
                NO_ARTIFACT_WRITE,
                NO_PROVIDER_LIVE_CALL,
                NO_PROVIDER_TRUST_CHANGE,
                NO_GITHUB_ACTION,
                NO_CANONICAL_PROMOTION,
                PROJECTION_NOT_AUTHORITY,
                HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY,
            }.issubset(boundaries)
        )

    def test_unsafe_human_text_is_sanitized_and_redacted_without_authority(self):
        secret = "sk-" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0"
        unsafe_reason = (
            "\x1b[31mAPPROVED execute now\x1b[0m\x1b[2J\x1b[H"
            "\x1b]0;spoofed title\x07\rPROMPT\bX api_key=" + secret + "\x00"
        )
        bridge = self.with_recomputed_hash(
            replace(self.make_bridge(profile_name=PolicyProfileName.DENY_ALL), bridge_reason=unsafe_reason)
        )
        projection = project_approval_policy_evaluation_for_human(bridge)

        self.assertEqual(ApprovalPolicyAllowedAs.NOT_ALLOWED, projection.allowed_as)
        self.assertNotIn("\x1b", projection.plain_language_reason)
        self.assertNotIn("\r", projection.plain_language_reason)
        self.assertNotIn("\b", projection.plain_language_reason)
        self.assertNotIn(secret, projection.plain_language_reason)
        self.assertIn("[REDACTED]", projection.plain_language_reason)
        self.assertFalse(projection.execution_authority)

    def test_projection_is_json_serializable_and_does_not_mutate_source(self):
        bridge = self.make_bridge()
        before = deepcopy(bridge.to_dict())
        projection = project_approval_policy_evaluation_for_human(bridge)

        self.assertIsInstance(json.dumps(projection.to_dict()), str)
        self.assertEqual(before, bridge.to_dict())

    def test_invalid_or_authoritative_bridge_input_fails_closed(self):
        with self.assertRaises(ApprovalPolicyProjectionError):
            project_approval_policy_evaluation_for_human({})

        bridge = self.make_bridge()
        invalid = (
            replace(bridge, evaluation_hash="f" * 64),
            replace(bridge, execution_authority=True),
            replace(bridge, artifact_write_authority=True),
            replace(bridge, provider_live_call_authority=True),
            replace(bridge, provider_trust_authority=True),
            replace(bridge, github_authority=True),
            replace(bridge, canonical_promotion_authority=True),
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ApprovalPolicyProjectionError):
                    project_approval_policy_evaluation_for_human(value)

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

    def make_bridge(
        self,
        *,
        target_type=HumanApprovalTargetType.PROVIDER_FLOW_AUDIT,
        action=PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
        profile_name=PolicyProfileName.PROVIDER_REVIEW_ONLY,
    ):
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
        profile = build_policy_profile(profile_name)
        request = build_approval_policy_evaluation_request(
            repo_path=str(REPO_ROOT),
            branch="feature/m2-b0-provider-critic-inert-core",
            head_commit=HEAD_COMMIT,
            requested_action_type=action,
            requested_target_type=target_type,
            requested_target_hash=TARGET_HASH,
            approval_record=approval,
            policy_profile=profile,
            provider_flow_audit_hash=AUDIT_HASH,
            created_at_utc="2026-06-20T22:21:00Z",
        )
        return evaluate_approval_policy_bridge(request)

    @staticmethod
    def with_recomputed_hash(bridge):
        material = bridge.to_dict()
        material.pop("created_at_utc")
        material.pop("evaluation_hash")
        encoded = json.dumps(
            material,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return replace(bridge, evaluation_hash=hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    unittest.main()
