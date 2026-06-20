from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.human_approval_gate import (
    HASH_BOUND_DECISION_ONLY,
    HASH_BOUND_HUMAN_APPROVAL_RECORD,
    HUMAN_APPROVAL_SCHEMA_VERSION,
    HUMAN_DECISION_RECORDED_NO_EXECUTION,
    HUMAN_DECISION_RECORD_ONLY,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_EXECUTION_AUTHORITY,
    NO_GITHUB_ACTION,
    NO_PROVIDER_TRUST_CHANGE,
    SUMMARY_NOT_AUTHORITY,
    HashBoundHumanApprovalRecord,
    HumanApprovalDecision,
    HumanApprovalGateError,
    HumanApprovalTargetType,
    build_hash_bound_human_approval_record,
    compute_approval_binding_hash,
    verify_hash_bound_human_approval_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "human_approval_gate.py"
THIS_FILE = Path(__file__).resolve()
TARGET_HASH = hashlib.sha256(b"exact reviewed target").hexdigest()
AUDIT_HASH = hashlib.sha256(b"provider flow audit").hexdigest()
HEAD_COMMIT = "16e2233b53ea54661d23369ce7fadc982681ec28"


class ApprovalG0HashBoundHumanApprovalTests(unittest.TestCase):
    def test_valid_record_has_required_contract_and_is_json_serializable(self):
        record = self.make_record()
        verification = verify_hash_bound_human_approval_record(record)

        self.assertIsInstance(record, HashBoundHumanApprovalRecord)
        self.assertEqual(HASH_BOUND_HUMAN_APPROVAL_RECORD, record.label)
        self.assertEqual(HUMAN_APPROVAL_SCHEMA_VERSION, record.schema_version)
        self.assertEqual(HUMAN_DECISION_RECORD_ONLY, record.approval_role)
        self.assertEqual(NO_EXECUTION_AUTHORITY, record.approval_scope)
        self.assertEqual(HUMAN_DECISION_RECORDED_NO_EXECUTION, record.final_status)
        self.assertTrue(verification.valid)
        self.assertIsInstance(json.dumps(record.to_dict()), str)
        self.assertIsInstance(json.dumps(verification.to_dict()), str)

    def test_all_decisions_are_accepted_and_invalid_decision_fails_closed(self):
        for decision in HumanApprovalDecision:
            with self.subTest(decision=decision):
                record = self.make_record(decision=decision)
                self.assertEqual(decision, record.decision)
                self.assertTrue(verify_hash_bound_human_approval_record(record).valid)

        with self.assertRaises(HumanApprovalGateError):
            self.make_record(decision="AUTO_APPROVED")
        with self.assertRaises(HumanApprovalGateError):
            self.make_record(target_type="AUTONOMOUS_ACTION")

    def test_target_hash_is_required_and_must_be_sha256(self):
        for invalid in (None, "", "abc", "A" * 64, "g" * 64):
            with self.subTest(invalid=invalid):
                with self.assertRaises(HumanApprovalGateError):
                    self.make_record(target_hash=invalid)

        with self.assertRaises(HumanApprovalGateError):
            build_hash_bound_human_approval_record(
                repo_path=str(REPO_ROOT),
                branch="feature/test",
                head_commit=HEAD_COMMIT,
                target_type=HumanApprovalTargetType.DIFF,
                target_hash="",
                target_summary="summary only cannot authorize",
                decision=HumanApprovalDecision.APPROVED,
            )

    def test_binding_hash_is_deterministic_and_ignores_metadata(self):
        first = self.make_record(
            created_at_utc="2026-06-20T21:22:00Z",
            target_summary="first summary",
            reason="first reason",
        )
        second = self.make_record(
            created_at_utc="2026-06-20T21:23:00Z",
            target_summary="different summary",
            reason="different reason",
        )

        self.assertEqual(first.approval_binding_hash, second.approval_binding_hash)
        self.assertEqual(first.approval_id, second.approval_id)
        self.assertNotEqual(first.created_at_utc, second.created_at_utc)
        self.assertTrue(verify_hash_bound_human_approval_record(first).valid)
        self.assertTrue(
            verify_hash_bound_human_approval_record(
                replace(first, target_summary="non-authoritative summary changed")
            ).valid
        )

    def test_compute_binding_hash_matches_record(self):
        record = self.make_record()
        computed = compute_approval_binding_hash(
            repo_path=record.repo_path,
            branch=record.branch,
            head_commit=record.head_commit,
            target_type=record.target_type,
            target_hash=record.target_hash,
            allowed_scope=record.allowed_scope,
            forbidden_scope=record.forbidden_scope,
            decision=record.decision,
            provider_flow_audit_ref=record.provider_flow_audit_ref,
            provider_flow_audit_hash=record.provider_flow_audit_hash,
        )

        self.assertEqual(record.approval_binding_hash, computed)

    def test_every_authoritative_binding_change_invalidates_verification(self):
        record = self.make_record()
        mutations = (
            replace(
                record,
                target_hash=record.target_hash[:-1]
                + ("0" if record.target_hash[-1] != "0" else "1"),
            ),
            replace(record, repo_path="/tmp/other-repo"),
            replace(record, branch="feature/other"),
            replace(record, head_commit="a" * 40),
            replace(record, target_type=HumanApprovalTargetType.PLAN),
            replace(record, allowed_scope=("review", "extra")),
            replace(record, forbidden_scope=("execute", "network")),
            replace(record, decision=HumanApprovalDecision.REJECTED),
            replace(record, provider_flow_audit_ref="provider-g-other"),
            replace(record, provider_flow_audit_hash="e" * 64),
            replace(record, repo_path=record.repo_path + "\x1b[31m"),
        )

        for mutated in mutations:
            with self.subTest(mutated=mutated):
                with self.assertRaises(HumanApprovalGateError):
                    verify_hash_bound_human_approval_record(mutated)

    def test_all_safety_boundaries_and_authorities_remain_inert_when_approved(self):
        record = self.make_record(decision=HumanApprovalDecision.APPROVED)
        boundaries = {item.value for item in record.safety_boundaries}

        self.assertTrue(
            {
                NO_EXECUTION,
                NO_ARTIFACT_WRITE,
                NO_PROVIDER_TRUST_CHANGE,
                NO_CANONICAL_PROMOTION,
                NO_GITHUB_ACTION,
                HASH_BOUND_DECISION_ONLY,
                SUMMARY_NOT_AUTHORITY,
            }.issubset(boundaries)
        )
        self.assertFalse(record.execution_authority)
        self.assertFalse(record.artifact_write_authority)
        self.assertFalse(record.provider_trust_authority)
        self.assertFalse(record.canonical_promotion_authority)
        self.assertFalse(record.github_authority)

    def test_authority_or_boundary_mutation_fails_closed(self):
        record = self.make_record()
        mutations = (
            replace(record, execution_authority=True),
            replace(record, artifact_write_authority=True),
            replace(record, provider_trust_authority=True),
            replace(record, canonical_promotion_authority=True),
            replace(record, github_authority=True),
            replace(record, approval_scope="EXECUTION_AUTHORITY"),
            replace(record, safety_boundaries=record.safety_boundaries[:-1]),
        )
        for mutated in mutations:
            with self.subTest(mutated=mutated):
                with self.assertRaises(HumanApprovalGateError):
                    verify_hash_bound_human_approval_record(mutated)

    def test_summary_and_reason_are_sanitized_and_credentials_are_redacted(self):
        mock_key = "sk-" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0"
        record = self.make_record(
            target_summary="\x1b[31mSummary\x1b[0m\rSPOOF\bX api_key=" + mock_key,
            reason="\x1b[2JReviewed token=" + mock_key + "\x00",
            known_secrets=(mock_key,),
        )

        persisted = json.dumps(record.to_dict())
        self.assertNotIn("\x1b", record.target_summary)
        self.assertNotIn("\r", record.target_summary)
        self.assertNotIn("\b", record.target_summary)
        self.assertNotIn(mock_key, persisted)
        self.assertIn("[REDACTED]", record.target_summary)
        self.assertIn("[REDACTED]", record.reason)

    def test_no_raw_provider_output_or_execution_capability_is_present(self):
        record = self.make_record(target_summary="reviewed bounded target")
        record_keys = set(record.to_dict())
        forbidden_payload_fields = {
            "provider_output",
            "raw_provider_output",
            "raw_payload",
            "encrypted_raw_payload",
        }
        self.assertTrue(record_keys.isdisjoint(forbidden_payload_fields))

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
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module)
            for module_name in imported:
                self.assertFalse(
                    any(
                        module_name == item or module_name.startswith(item + ".")
                        for item in forbidden_modules
                    )
                )

        runtime_source = RUNTIME_FILE.read_text(encoding="utf-8")
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
        for call in forbidden_calls:
            self.assertNotIn(call, runtime_source)

    def test_original_input_collections_are_not_mutated(self):
        allowed = ["review", "inspect"]
        forbidden = ["execute", "write"]
        before_allowed = list(allowed)
        before_forbidden = list(forbidden)

        record = self.make_record(
            allowed_scope=allowed,
            forbidden_scope=forbidden,
        )

        self.assertEqual(before_allowed, allowed)
        self.assertEqual(before_forbidden, forbidden)
        self.assertEqual(("inspect", "review"), record.allowed_scope)
        self.assertEqual(("execute", "write"), record.forbidden_scope)

    def test_record_verifier_rejects_invalid_type_and_unsanitized_metadata(self):
        with self.assertRaises(HumanApprovalGateError):
            verify_hash_bound_human_approval_record({})

        record = self.make_record()
        with self.assertRaises(HumanApprovalGateError):
            verify_hash_bound_human_approval_record(
                replace(record, reason="unsafe\x1b[31mreason")
            )

    def test_runtime_source_has_no_external_or_artifact_writer_imports(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        forbidden_import_patterns = (
            "runtime.safety.approval_gate",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.safety.gated_durable_artifact_flow",
            "runtime.provider_live_adapter",
        )
        for pattern in forbidden_import_patterns:
            self.assertNotIn(pattern, source)
        self.assertIsNone(
            re.search(r"^\s*(from|import)\s+(os|shutil|pathlib)\b", source, re.MULTILINE)
        )

    def make_record(self, **overrides):
        values = {
            "repo_path": str(REPO_ROOT),
            "branch": "feature/m2-b0-provider-critic-inert-core",
            "head_commit": HEAD_COMMIT,
            "target_type": HumanApprovalTargetType.DIFF,
            "target_hash": TARGET_HASH,
            "target_summary": "reviewed exact diff",
            "allowed_scope": ("review",),
            "forbidden_scope": ("execute", "artifact-write"),
            "decision": HumanApprovalDecision.APPROVED,
            "human_reviewer_ref": "local-reviewer",
            "reason": "reviewed exact target hash",
            "provider_flow_audit_ref": "provider-g-record",
            "provider_flow_audit_hash": AUDIT_HASH,
            "created_at_utc": "2026-06-20T21:22:00Z",
        }
        values.update(overrides)
        return build_hash_bound_human_approval_record(**values)


if __name__ == "__main__":
    unittest.main()
