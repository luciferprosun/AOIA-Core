from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.policy_profiles import (
    AOIA_POLICY_PROFILE,
    DEFAULT_DENY,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_GITHUB_ACTION,
    NO_LIVE_PROVIDER_CALL,
    POLICY_SCHEMA_VERSION,
    PROPOSAL_OR_RECORD_ONLY,
    PolicyActionType,
    PolicyDecision,
    PolicyProfile,
    PolicyProfileError,
    PolicyProfileName,
    build_policy_profile,
    evaluate_policy_action,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "policy_profiles.py"
THIS_FILE = Path(__file__).resolve()
HEAD_COMMIT = "d3d405e706287518f7e9f8de23af5c1d649f00ec"
TARGET_HASH = hashlib.sha256(b"policy target").hexdigest()
APPROVAL_HASH = hashlib.sha256(b"approval binding").hexdigest()
AUDIT_HASH = hashlib.sha256(b"provider audit").hexdigest()


class PolicyH0DefaultDenyProfilesTests(unittest.TestCase):
    def test_all_required_profiles_exist_with_default_deny_schema(self):
        for name in PolicyProfileName:
            with self.subTest(name=name):
                profile = build_policy_profile(name)
                self.assertIsInstance(profile, PolicyProfile)
                self.assertEqual(AOIA_POLICY_PROFILE, profile.label)
                self.assertEqual(POLICY_SCHEMA_VERSION, profile.schema_version)
                self.assertEqual(name, profile.profile_name)
                self.assertEqual(PolicyDecision.DENY, profile.default_decision)
                self.assertRegex(profile.policy_hash, r"^[0-9a-f]{64}$")
                self.assertFalse(profile.execution_authority)
                self.assertFalse(profile.artifact_write_authority)
                self.assertFalse(profile.provider_live_call_authority)
                self.assertFalse(profile.github_authority)
                self.assertFalse(profile.canonical_promotion_authority)

        self.assertEqual(
            {
                PolicyProfileName.DENY_ALL,
                PolicyProfileName.READ_ONLY,
                PolicyProfileName.PROPOSE_ONLY,
                PolicyProfileName.PROVIDER_REVIEW_ONLY,
                PolicyProfileName.HUMAN_APPROVAL_RECORD_ONLY,
            },
            set(PolicyProfileName),
        )

    def test_unknown_profile_and_action_default_to_deny(self):
        fallback = build_policy_profile("UNKNOWN_PROFILE")
        self.assertEqual(PolicyProfileName.DENY_ALL, fallback.profile_name)

        unknown_profile = self.evaluate("READ_CONTEXT", profile_name="UNKNOWN_PROFILE")
        unknown_action = self.evaluate("UNKNOWN_ACTION")
        self.assertEqual(PolicyDecision.DENY, unknown_profile.decision)
        self.assertEqual(PolicyDecision.DENY, unknown_action.decision)
        self.assertFalse(unknown_profile.allowed)
        self.assertFalse(unknown_action.allowed)

    def test_malformed_input_fails_closed(self):
        malformed = (
            {"repo_path": "relative/repo"},
            {"branch": ""},
            {"head_commit": "not-a-commit"},
            {"target_paths": "runtime/file.py"},
            {"target_hash": "bad-hash"},
            {"approval_binding_hash": "bad-hash"},
            {"provider_flow_audit_hash": "bad-hash"},
        )
        for override in malformed:
            with self.subTest(override=override):
                with self.assertRaises(PolicyProfileError):
                    self.evaluate("READ_CONTEXT", **override)

    def test_policy_hash_is_deterministic_and_timestamp_independent(self):
        first = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            created_at_utc="2026-06-20T21:47:00Z",
        )
        second = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            created_at_utc="2026-06-20T21:48:00Z",
        )
        self.assertEqual(first.policy_hash, second.policy_hash)
        self.assertNotEqual(first.created_at_utc, second.created_at_utc)

    def test_semantic_policy_changes_change_policy_hash(self):
        baseline = build_policy_profile(PolicyProfileName.PROPOSE_ONLY)
        profile_name_changed = build_policy_profile(PolicyProfileName.READ_ONLY)
        allowed_changed = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            allowed_action_types=(PolicyActionType.BUILD_ACTION_PROPOSAL,),
        )
        denied_changed = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            denied_action_types=self.future_actions(),
        )
        allowed_scope_changed = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            allowed_scope=(str(REPO_ROOT),),
        )
        forbidden_scope_changed = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            forbidden_scope=(str(REPO_ROOT / "private"),),
        )

        for changed in (
            profile_name_changed,
            allowed_changed,
            denied_changed,
            allowed_scope_changed,
            forbidden_scope_changed,
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(baseline.policy_hash, changed.policy_hash)

    def test_deny_all_denies_reads_and_proposals(self):
        for action in (
            PolicyActionType.READ_CONTEXT,
            PolicyActionType.BUILD_ACTION_PROPOSAL,
        ):
            result = self.evaluate(action, profile_name=PolicyProfileName.DENY_ALL)
            self.assertEqual(PolicyDecision.DENY, result.decision)
            self.assertFalse(result.allowed)

    def test_read_only_allows_reads_and_denies_operations(self):
        for action in (
            PolicyActionType.READ_CONTEXT,
            PolicyActionType.READ_REPO_METADATA,
        ):
            result = self.evaluate(action, profile_name=PolicyProfileName.READ_ONLY)
            self.assertTrue(result.allowed)
            self.assertEqual(PolicyDecision.ALLOW_RECORD_ONLY, result.decision)

        for action in (
            PolicyActionType.WRITE_FILE,
            PolicyActionType.RUN_TEST_COMMAND,
            PolicyActionType.GITHUB_PUSH,
        ):
            self.assertFalse(
                self.evaluate(action, profile_name=PolicyProfileName.READ_ONLY).allowed
            )

    def test_propose_only_allows_proposals_and_denies_real_operations(self):
        for action in (
            PolicyActionType.BUILD_ACTION_PROPOSAL,
            PolicyActionType.BUILD_PATCH_PROPOSAL,
        ):
            result = self.evaluate(action)
            self.assertTrue(result.allowed)
            self.assertTrue(result.proposal_only)
            self.assertEqual(PolicyDecision.ALLOW_PROPOSAL_ONLY, result.decision)
            self.assertFalse(result.execution_authority)
            self.assertFalse(result.artifact_write_authority)
            self.assertFalse(result.provider_live_call_authority)
            self.assertFalse(result.github_authority)
            self.assertFalse(result.canonical_promotion_authority)

        for action in (
            PolicyActionType.WRITE_FILE,
            PolicyActionType.RUN_SHELL_COMMAND,
            PolicyActionType.RUN_TEST_COMMAND,
            PolicyActionType.GIT_COMMIT,
            PolicyActionType.GITHUB_PR,
        ):
            self.assertFalse(self.evaluate(action).allowed)

    def test_record_only_profiles_allow_only_their_record(self):
        provider = self.evaluate(
            PolicyActionType.BUILD_PROVIDER_FLOW_AUDIT_RECORD,
            profile_name=PolicyProfileName.PROVIDER_REVIEW_ONLY,
        )
        approval = self.evaluate(
            PolicyActionType.BUILD_HUMAN_APPROVAL_RECORD,
            profile_name=PolicyProfileName.HUMAN_APPROVAL_RECORD_ONLY,
        )
        self.assertTrue(provider.allowed)
        self.assertTrue(provider.record_only)
        self.assertTrue(approval.allowed)
        self.assertTrue(approval.record_only)
        self.assertFalse(
            self.evaluate(
                PolicyActionType.CALL_LIVE_PROVIDER,
                profile_name=PolicyProfileName.PROVIDER_REVIEW_ONLY,
            ).allowed
        )
        for action in (PolicyActionType.WRITE_FILE, PolicyActionType.WRITE_ARTIFACT):
            self.assertFalse(
                self.evaluate(
                    action,
                    profile_name=PolicyProfileName.HUMAN_APPROVAL_RECORD_ONLY,
                ).allowed
            )

    def test_every_profile_denies_all_future_capability_actions(self):
        for profile_name in PolicyProfileName:
            for action in self.future_actions():
                with self.subTest(profile_name=profile_name, action=action):
                    result = self.evaluate(action, profile_name=profile_name)
                    self.assertFalse(result.allowed)
                    self.assertFalse(result.execution_authority)
                    self.assertFalse(result.artifact_write_authority)
                    self.assertFalse(result.provider_live_call_authority)
                    self.assertFalse(result.github_authority)
                    self.assertFalse(result.canonical_promotion_authority)

    def test_hash_presence_alone_never_allows_execution(self):
        for hash_field in ("approval_binding_hash", "provider_flow_audit_hash"):
            result = self.evaluate(
                PolicyActionType.RUN_SHELL_COMMAND,
                **{hash_field: APPROVAL_HASH if hash_field.startswith("approval") else AUDIT_HASH},
            )
            self.assertFalse(result.allowed)
            self.assertTrue(result.future_milestone_required)
            self.assertFalse(result.execution_authority)

    def test_allowed_and_forbidden_scope_checks_fail_closed(self):
        profile = build_policy_profile(
            PolicyProfileName.PROPOSE_ONLY,
            allowed_scope=(str(REPO_ROOT / "runtime"),),
            forbidden_scope=(str(REPO_ROOT / "runtime" / "private"),),
        )
        inside = self.evaluate(
            PolicyActionType.BUILD_PATCH_PROPOSAL,
            profile_name=profile,
            target_paths=(str(REPO_ROOT / "runtime" / "safe.py"),),
        )
        outside = self.evaluate(
            PolicyActionType.BUILD_PATCH_PROPOSAL,
            profile_name=profile,
            target_paths=(str(REPO_ROOT / "tests" / "outside.py"),),
        )
        forbidden = self.evaluate(
            PolicyActionType.BUILD_PATCH_PROPOSAL,
            profile_name=profile,
            target_paths=(str(REPO_ROOT / "runtime" / "private" / "blocked.py"),),
        )

        self.assertTrue(inside.allowed)
        self.assertFalse(outside.allowed)
        self.assertFalse(outside.allowed_scope_match)
        self.assertFalse(forbidden.allowed)
        self.assertTrue(forbidden.forbidden_scope_match)

    def test_profile_boundaries_and_result_are_json_serializable(self):
        profile = build_policy_profile(PolicyProfileName.PROPOSE_ONLY)
        boundaries = {item.value for item in profile.policy_boundaries}
        self.assertTrue(
            {
                DEFAULT_DENY,
                NO_EXECUTION,
                NO_ARTIFACT_WRITE,
                NO_LIVE_PROVIDER_CALL,
                NO_GITHUB_ACTION,
                NO_CANONICAL_PROMOTION,
                PROPOSAL_OR_RECORD_ONLY,
            }.issubset(boundaries)
        )
        result = self.evaluate(
            PolicyActionType.BUILD_ACTION_PROPOSAL,
            target_hash=TARGET_HASH,
        )
        self.assertIsInstance(json.dumps(profile.to_dict()), str)
        self.assertIsInstance(json.dumps(result.to_dict()), str)

    def test_tampered_profile_or_authority_claim_fails_closed(self):
        profile = build_policy_profile(PolicyProfileName.PROPOSE_ONLY)
        mutations = (
            replace(profile, execution_authority=True),
            replace(profile, artifact_write_authority=True),
            replace(profile, provider_live_call_authority=True),
            replace(profile, github_authority=True),
            replace(profile, canonical_promotion_authority=True),
            replace(profile, policy_hash="f" * 64),
            replace(profile, policy_boundaries=(DEFAULT_DENY,)),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(PolicyProfileError):
                    self.evaluate(PolicyActionType.READ_CONTEXT, profile_name=mutation)

    def test_runtime_has_no_external_or_artifact_writer_capability(self):
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
            "runtime.human_approval_gate",
            "runtime.provider_flow_audit",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.safety.approval_gate",
        )
        for value in (*forbidden_calls, *forbidden_imports):
            self.assertNotIn(value, source)
        self.assertIsNone(
            re.search(r"^\s*(from|import)\s+(os|shutil|pathlib)\b", source, re.MULTILINE)
        )

    def evaluate(self, action_type, **overrides):
        values = {
            "profile_name": PolicyProfileName.PROPOSE_ONLY,
            "action_type": action_type,
            "repo_path": str(REPO_ROOT),
            "branch": "feature/m2-b0-provider-critic-inert-core",
            "head_commit": HEAD_COMMIT,
            "target_paths": (),
        }
        values.update(overrides)
        return evaluate_policy_action(**values)

    @staticmethod
    def future_actions():
        return (
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


if __name__ == "__main__":
    unittest.main()
