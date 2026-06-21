from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest
from copy import deepcopy
from dataclasses import fields, replace
from pathlib import Path

from runtime.auth_chain_assembler import assemble_inert_auth_chain
from runtime.execution_readiness_gate import (
    INERT_PROPOSAL_REVIEW_READY,
    INERT_RECORD_REVIEW_READY,
    ExecutionReadinessRecord,
    ExecutionReadinessRejection,
    evaluate_execution_readiness,
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
RUNTIME_FILE = REPO_ROOT / "runtime" / "execution_readiness_gate.py"
THIS_FILE = Path(__file__).resolve()
HEAD_COMMIT = "247f5ad72cfc42a821df2817c28e0088aae2a6fe"
TARGET_HASH = hashlib.sha256(b"AUTH-1F exact target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"AUTH-1F provider audit").hexdigest()


class Auth1FExecutionReadinessGateTests(unittest.TestCase):
    def test_record_only_chain_returns_inert_record(self):
        result = evaluate_execution_readiness(self.assemble())

        self.assertIsInstance(result, ExecutionReadinessRecord)
        self.assertEqual(INERT_RECORD_REVIEW_READY, result.readiness_status)
        self.assertIn("not an instruction to execute", result.inert_note)

    def test_proposal_only_chain_returns_inert_record(self):
        assembly = self.assemble(
            target_type=HumanApprovalTargetType.DIFF,
            action=PolicyActionType.BUILD_PATCH_PROPOSAL,
            profile_name=PolicyProfileName.PROPOSE_ONLY,
        )
        result = evaluate_execution_readiness(assembly)

        self.assertIsInstance(result, ExecutionReadinessRecord)
        self.assertEqual(INERT_PROPOSAL_REVIEW_READY, result.readiness_status)

    def test_every_capability_flag_is_hardcoded_false(self):
        outputs = (
            evaluate_execution_readiness(self.assemble()),
            evaluate_execution_readiness(self.assemble(profile_name=PolicyProfileName.DENY_ALL)),
            evaluate_execution_readiness(None),
        )
        expected = {
            "execution_allowed",
            "dispatch_allowed",
            "artifact_write_allowed",
            "provider_call_allowed",
            "github_action_allowed",
        }
        for output in outputs:
            names = {item.name for item in fields(output) if item.name.endswith("_allowed")}
            self.assertEqual(expected, names)
            self.assertTrue(all(getattr(output, name) is False for name in names))

    def test_denied_and_future_milestone_chains_are_rejected(self):
        denied = evaluate_execution_readiness(
            self.assemble(profile_name=PolicyProfileName.DENY_ALL)
        )
        future = evaluate_execution_readiness(
            self.assemble(
                target_type=HumanApprovalTargetType.COMMAND,
                action=PolicyActionType.RUN_TEST_COMMAND,
                profile_name=PolicyProfileName.PROPOSE_ONLY,
            )
        )

        self.assertIsInstance(denied, ExecutionReadinessRejection)
        self.assertIsInstance(future, ExecutionReadinessRejection)
        self.assertIn("denied", denied.rejection_reason)
        self.assertIn("future milestone", future.rejection_reason)

    def test_invalid_malformed_or_incomplete_chain_fails_closed(self):
        valid = self.assemble()
        cases = (
            None,
            {},
            replace(valid, assembly_hash=""),
            replace(valid, assembly_hash=None),
            replace(valid, assembly_hash="f" * 64),
            replace(valid, assembly_status="AUTH_CHAIN_RECORD_ONLY"),
            replace(valid, safety_boundaries=()),
            replace(valid, execution_authority=True),
        )
        for assembly in cases:
            with self.subTest(assembly=type(assembly).__name__):
                result = evaluate_execution_readiness(assembly)
                self.assertIsInstance(result, ExecutionReadinessRejection)
                self.assertFalse(result.execution_allowed)

    def test_hash_is_deterministic_and_assembly_is_preserved(self):
        assembly = self.assemble()
        before = deepcopy(assembly.to_dict())

        first = evaluate_execution_readiness(assembly)
        second = evaluate_execution_readiness(assembly)

        self.assertEqual(assembly.assembly_hash, first.assembly_hash)
        self.assertEqual(first.readiness_hash, second.readiness_hash)
        self.assertRegex(first.readiness_hash, r"^[0-9a-f]{64}$")
        self.assertEqual(before, assembly.to_dict())
        self.assertIsInstance(json.dumps(first.to_dict()), str)

    def test_rejection_hash_is_deterministic(self):
        first = evaluate_execution_readiness(None)
        second = evaluate_execution_readiness(None)
        self.assertEqual(first.rejection_hash, second.rejection_hash)
        self.assertRegex(first.rejection_hash, r"^[0-9a-f]{64}$")

    def test_output_type_and_field_names_do_not_claim_action_authority(self):
        outputs = (ExecutionReadinessRecord, ExecutionReadinessRejection)
        forbidden = ("permission", "grant", "authorization")
        forbidden_type_suffix = "instruction"
        for output_type in outputs:
            self.assertTrue(
                all(value not in output_type.__name__.lower() for value in forbidden)
            )
            self.assertNotIn(forbidden_type_suffix, output_type.__name__.lower())
            for item in fields(output_type):
                lowered = item.name.lower()
                self.assertTrue(all(value not in lowered for value in forbidden))
                self.assertNotIn(forbidden_type_suffix, lowered)

    def test_runtime_has_no_external_or_action_capability(self):
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
            "runtime.provider_live_adapter",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.safety.approval_gate",
            "open" + "router",
        ):
            self.assertNotIn(value.lower(), source.lower())
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
            "created_at_utc": "2026-06-21T06:13:00Z",
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
            title="AUTH-1F readiness review",
            intent="Classify the inert AUTH chain for terminal review.",
            summary="No action authority is created.",
            source_type="LOCAL_AUTH_REVIEW",
            source_label="auth-1f-test",
            created_at="2026-06-21T06:11:00Z",
        )
        packet = create_review_packet_from_proposal(
            proposal=proposal,
            expected_proposal_hash=proposal.proposal_hash,
            created_at="2026-06-21T06:12:00Z",
            reviewer_label="local-human-reviewer",
            packet_purpose="AUTH-1F readiness review",
        )
        return proposal, packet


if __name__ == "__main__":
    unittest.main()
