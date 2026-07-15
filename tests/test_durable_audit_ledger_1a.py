from __future__ import annotations

import ast
import fcntl
import hashlib
import json
import os
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.audit_ledger import (
    AUDIT_LEDGER_GENESIS_PREVIOUS_HASH,
    AUDIT_LEDGER_SCHEMA_VERSION,
    AuditLedgerAppendResult,
    AuditLedgerEntry,
    AuditLedgerVerificationResult,
    append_audit_entry,
    canonical_audit_json as audit_ledger_canonical_json,
    compute_audit_entry_hash,
    verify_audit_ledger,
)
from runtime.audit.durable_log import (
    DURABLE_AUDIT_SCHEMA_VERSION,
    DurableAuditAppendResult,
    DurableAuditEvent,
    DurableAuditVerificationResult,
    append_durable_audit_event,
    canonical_audit_json,
    compute_audit_event_hash,
    verify_durable_audit_log,
)
from runtime.audit.durable_audit_ledger import (
    AUDIT_LEDGER_GENESIS_PREVIOUS_HASH as STANDALONE_GENESIS_HASH,
    AUDIT_LEDGER_MAX_EVENT_TYPE_LENGTH as STANDALONE_EVENT_TYPE_LIMIT,
    AUDIT_LEDGER_SCHEMA_VERSION as STANDALONE_SCHEMA_VERSION,
    AuditLedgerAppendStatus as StandaloneAppendStatus,
    AuditLedgerEntry as StandaloneAuditLedgerEntry,
    AuditLedgerReadError as StandaloneAuditLedgerReadError,
    AuditLedgerTip as StandaloneAuditLedgerTip,
    AuditLedgerVerificationStatus as StandaloneVerificationStatus,
    append_audit_entry as append_standalone_audit_entry,
    canonical_audit_ledger_json,
    read_audit_ledger as read_standalone_audit_ledger,
    verify_audit_ledger as verify_standalone_audit_ledger,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_MODULE = REPO_ROOT / "runtime" / "audit" / "durable_log.py"
LEDGER_FILENAME = "events.jsonl"


class DurableAuditLedger1ATests(unittest.TestCase):
    def test_append_first_event_creates_genesis_bound_record(self):
        with TemporaryDirectory() as tmp:
            result = self.append(tmp, payload={"message": "first"})

            self.assertTrue(result.appended)
            self.assertFalse(result.blocking)
            self.assertIsNotNone(result.event)
            self.assertIsNone(result.previous_event_hash)
            records = self.read_records(tmp)

        self.assertEqual(1, len(records))
        self.assertEqual(DURABLE_AUDIT_SCHEMA_VERSION, records[0]["schema_version"])
        self.assertIsNone(records[0]["previous_event_hash"])
        self.assertEqual(result.event_hash, records[0]["event_hash"])

    def test_append_second_event_uses_first_event_hash_as_previous_hash(self):
        with TemporaryDirectory() as tmp:
            first = self.append(tmp, payload={"order": 1})
            second = self.append(tmp, payload={"order": 2}, created_at="2026-06-26T00:00:01Z")
            verified = self.verify(tmp)

        self.assertTrue(second.appended)
        self.assertEqual(first.event_hash, second.previous_event_hash)
        self.assertTrue(verified.valid)
        self.assertEqual(2, verified.event_count)
        self.assertEqual(second.event_hash, verified.final_event_hash)

    def test_verify_valid_empty_ledger_is_supported(self):
        with TemporaryDirectory() as tmp:
            result = self.verify(tmp)

        self.assertTrue(result.valid)
        self.assertEqual(0, result.event_count)
        self.assertIsNone(result.final_event_hash)

    def test_verify_valid_single_event_ledger(self):
        with TemporaryDirectory() as tmp:
            appended = self.append(tmp)
            result = self.verify(tmp)

        self.assertTrue(result.valid)
        self.assertEqual(1, result.event_count)
        self.assertEqual(appended.event_hash, result.final_event_hash)

    def test_verify_valid_multi_event_chain(self):
        with TemporaryDirectory() as tmp:
            first = self.append(tmp, payload={"n": 1})
            second = self.append(tmp, payload={"n": 2}, created_at="2026-06-26T00:00:01Z")
            third = self.append(tmp, payload={"n": 3}, created_at="2026-06-26T00:00:02Z")
            result = self.verify(tmp)

        self.assertTrue(first.appended)
        self.assertTrue(second.appended)
        self.assertTrue(third.appended)
        self.assertTrue(result.valid)
        self.assertEqual(3, result.event_count)
        self.assertEqual(third.event_hash, result.final_event_hash)

    def test_canonical_json_is_deterministic_independent_of_dict_order(self):
        left = {"z": [3, 2, 1], "a": {"b": True, "a": None}}
        right = {"a": {"a": None, "b": True}, "z": [3, 2, 1]}

        self.assertEqual(canonical_audit_json(left), canonical_audit_json(right))

    def test_payload_hash_is_deterministic(self):
        with TemporaryDirectory() as tmp:
            first = self.append(tmp, payload={"b": 2, "a": 1})
            second = self.append(
                tmp,
                payload={"a": 1, "b": 2},
                created_at="2026-06-26T00:00:01Z",
            )

        self.assertEqual(first.event.payload_hash, second.event.payload_hash)

    def test_event_hash_changes_when_payload_changes(self):
        first = self.event_material(payload={"value": "one"})
        second = self.event_material(payload={"value": "two"})

        self.assertNotEqual(
            compute_audit_event_hash(first),
            compute_audit_event_hash(second),
        )

    def test_event_hash_changes_when_previous_hash_changes(self):
        first = self.event_material(previous_event_hash="a" * 64)
        second = self.event_material(previous_event_hash="b" * 64)

        self.assertNotEqual(
            compute_audit_event_hash(first),
            compute_audit_event_hash(second),
        )

    def test_detect_malformed_jsonl(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / LEDGER_FILENAME).write_text("{not-json}\n", encoding="utf-8")
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "malformed JSONL")

    def test_detect_missing_required_field(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp)
            records = self.read_records(tmp)
            records[0].pop("event_type")
            self.write_records(tmp, records)
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "missing required field event_type")

    def test_detect_payload_tampering(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp)
            records = self.read_records(tmp)
            records[0]["payload"]["message"] = "tampered"
            self.write_records(tmp, records)
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "payload_hash mismatch")
        self.assertIssueContains(result, "event_hash mismatch")

    def test_detect_payload_hash_tampering(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp)
            records = self.read_records(tmp)
            records[0]["payload_hash"] = "b" * 64
            self.write_records(tmp, records)
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "payload_hash mismatch")
        self.assertIssueContains(result, "event_hash mismatch")

    def test_detect_previous_event_hash_tampering(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp)
            self.append(tmp, created_at="2026-06-26T00:00:01Z")
            records = self.read_records(tmp)
            records[1]["previous_event_hash"] = "b" * 64
            self.write_records(tmp, records)
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "previous_event_hash mismatch")
        self.assertIssueContains(result, "event_hash mismatch")

    def test_detect_event_hash_tampering(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp)
            records = self.read_records(tmp)
            records[0]["event_hash"] = "c" * 64
            self.write_records(tmp, records)
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "event_hash mismatch")

    def test_detect_broken_hash_chain(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp, payload={"n": 1})
            self.append(tmp, payload={"n": 2}, created_at="2026-06-26T00:00:01Z")
            self.append(tmp, payload={"n": 3}, created_at="2026-06-26T00:00:02Z")
            records = self.read_records(tmp)
            records[1]["event_hash"] = "d" * 64
            self.write_records(tmp, records)
            result = self.verify(tmp)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "event_hash mismatch")
        self.assertIssueContains(result, "previous_event_hash mismatch")

    def test_detect_truncation_when_expected_final_event_hash_is_supplied(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp, payload={"n": 1})
            second = self.append(tmp, payload={"n": 2}, created_at="2026-06-26T00:00:01Z")
            records = self.read_records(tmp)
            self.write_records(tmp, records[:1])
            result = self.verify(tmp, expected_final_event_hash=second.event_hash)

        self.assertFalse(result.valid)
        self.assertIssueContains(result, "truncated")

    def test_append_fails_closed_when_existing_ledger_is_tampered(self):
        with TemporaryDirectory() as tmp:
            self.append(tmp)
            records = self.read_records(tmp)
            records[0]["payload"]["message"] = "tampered"
            self.write_records(tmp, records)

            result = self.append(tmp, created_at="2026-06-26T00:00:01Z")
            records_after = self.read_records(tmp)

        self.assertFalse(result.appended)
        self.assertTrue(result.blocking)
        self.assertEqual(1, len(records_after))

    def test_reject_invalid_ledger_paths(self):
        invalid_filenames = (
            "",
            "/absolute.jsonl",
            "../escape.jsonl",
            "nested/events.jsonl",
            "nested\\events.jsonl",
            "bad\x00name.jsonl",
        )
        with TemporaryDirectory() as tmp:
            for filename in invalid_filenames:
                with self.subTest(filename=repr(filename)):
                    append_result = append_durable_audit_event(
                        ledger_dir=tmp,
                        ledger_filename=filename,
                        event_type="TEST_EVENT",
                        payload={"blocked": True},
                    )
                    verify_result = verify_durable_audit_log(
                        ledger_dir=tmp,
                        ledger_filename=filename,
                    )

                    self.assertFalse(append_result.appended)
                    self.assertTrue(append_result.blocking)
                    self.assertFalse(verify_result.valid)

    def test_reject_directory_target(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / LEDGER_FILENAME).mkdir()

            append_result = self.append(tmp)
            verify_result = self.verify(tmp)

        self.assertFalse(append_result.appended)
        self.assertFalse(verify_result.valid)
        self.assertIssueContains(verify_result, "directory")

    def test_reject_symlink_ledger_path_when_supported(self):
        with TemporaryDirectory() as tmp, TemporaryDirectory() as outside:
            target = Path(outside) / "outside.jsonl"
            target.write_text("", encoding="utf-8")
            link = Path(tmp) / LEDGER_FILENAME
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            append_result = self.append(tmp)
            verify_result = self.verify(tmp)

        self.assertFalse(append_result.appended)
        self.assertFalse(verify_result.valid)
        self.assertIssueContains(verify_result, "symlink")

    def test_authority_fields_always_false_and_ledger_is_evidence_only(self):
        with TemporaryDirectory() as tmp:
            append_result = self.append(tmp)
            verify_result = self.verify(tmp)
            forced_event = replace(
                append_result.event,
                can_approve=True,
                can_write=True,
                can_execute=True,
                can_commit=True,
                can_push=True,
                can_call_provider=True,
                can_change_gate=True,
                write_authority_granted=True,
                execution_authority_granted=True,
                provider_authority_granted=True,
            )
            forced_append = replace(
                append_result,
                can_approve=True,
                can_write=True,
                can_execute=True,
                can_commit=True,
                can_push=True,
                can_call_provider=True,
                can_change_gate=True,
                write_authority_granted=True,
                execution_authority_granted=True,
                provider_authority_granted=True,
            )
            forced_verify = replace(
                verify_result,
                can_approve=True,
                can_write=True,
                can_execute=True,
                can_commit=True,
                can_push=True,
                can_call_provider=True,
                can_change_gate=True,
                write_authority_granted=True,
                execution_authority_granted=True,
                provider_authority_granted=True,
            )

        for obj in (forced_event, forced_append, forced_verify):
            with self.subTest(obj_type=type(obj).__name__):
                self.assertFalse(obj.can_approve)
                self.assertFalse(obj.can_write)
                self.assertFalse(obj.can_execute)
                self.assertFalse(obj.can_commit)
                self.assertFalse(obj.can_push)
                self.assertFalse(obj.can_call_provider)
                self.assertFalse(obj.can_change_gate)
                self.assertFalse(obj.write_authority_granted)
                self.assertFalse(obj.execution_authority_granted)
                self.assertFalse(obj.provider_authority_granted)
                self.assertFalse(hasattr(obj, "approve"))
                self.assertFalse(hasattr(obj, "execute"))
                self.assertFalse(hasattr(obj, "dispatch"))

    def test_static_no_new_capability_scan_for_durable_audit_module(self):
        source = AUDIT_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        called_names: set[str] = set()
        called_attrs: set[tuple[str | None, str]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
                    called_attrs.add((owner, node.func.attr))

        forbidden_imports = {
            "subprocess",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "requests",
            "httpx",
            "git",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.cloud",
            "langchain",
            "litellm",
        }
        forbidden_calls = {
            ("os", "system"),
            ("subprocess", "run"),
            ("subprocess", "Popen"),
            ("subprocess", "call"),
            ("subprocess", "check_call"),
            ("subprocess", "check_output"),
            ("webbrowser", "open"),
        }
        forbidden_names = {
            "Popen",
            "exec",
            "eval",
            "dispatch",
            "install_package",
            "approval_bypass",
        }

        for module_name in imports:
            self.assertFalse(
                any(
                    module_name == forbidden
                    or module_name.startswith(forbidden + ".")
                    for forbidden in forbidden_imports
                ),
                module_name,
            )
        self.assertTrue(forbidden_calls.isdisjoint(called_attrs))
        self.assertTrue(forbidden_names.isdisjoint(called_names))

    def append(
        self,
        ledger_dir: str,
        *,
        payload=None,
        event_type: str = "TEST_EVENT",
        created_at: str = "2026-06-26T00:00:00Z",
    ) -> DurableAuditAppendResult:
        return append_durable_audit_event(
            ledger_dir=ledger_dir,
            ledger_filename=LEDGER_FILENAME,
            event_type=event_type,
            payload={"message": "fixture"} if payload is None else payload,
            created_at=created_at,
        )

    def verify(
        self,
        ledger_dir: str,
        *,
        expected_final_event_hash: str | None = None,
    ) -> DurableAuditVerificationResult:
        return verify_durable_audit_log(
            ledger_dir=ledger_dir,
            ledger_filename=LEDGER_FILENAME,
            expected_final_event_hash=expected_final_event_hash,
        )

    @staticmethod
    def read_records(ledger_dir: str) -> list[dict]:
        path = Path(ledger_dir) / LEDGER_FILENAME
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @staticmethod
    def write_records(ledger_dir: str, records: list[dict]) -> None:
        path = Path(ledger_dir) / LEDGER_FILENAME
        text = "".join(canonical_audit_json(record) + "\n" for record in records)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def event_material(
        *,
        payload=None,
        previous_event_hash: str | None = None,
    ) -> dict:
        content = {"message": "fixture"} if payload is None else payload
        payload_hash = hashlib.sha256(canonical_audit_json(content).encode("utf-8")).hexdigest()
        return {
            "schema_version": DURABLE_AUDIT_SCHEMA_VERSION,
            "event_id": "durable-audit-event-test",
            "event_type": "TEST_EVENT",
            "created_at": "2026-06-26T00:00:00Z",
            "payload_hash": payload_hash,
            "payload": content,
            "previous_event_hash": previous_event_hash,
            "can_approve": False,
            "can_write": False,
            "can_execute": False,
            "can_commit": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "write_authority_granted": False,
            "execution_authority_granted": False,
            "provider_authority_granted": False,
        }

    def assertIssueContains(self, result: DurableAuditVerificationResult, text: str) -> None:
        self.assertTrue(
            any(text in issue for issue in result.issues),
            f"expected issue containing {text!r}, got {result.issues!r}",
        )


class AuditLedger1ATests(unittest.TestCase):
    def test_append_first_entry_uses_sequence_one_and_genesis_previous_hash(self):
        with TemporaryDirectory() as tmp:
            result = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"artifact": "file.txt"},
            )
            records = self.read_records(tmp, filename="ledger.jsonl")
            verified = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

        self.assertTrue(result.appended)
        self.assertFalse(result.blocking)
        self.assertIsNotNone(result.entry)
        self.assertEqual(1, result.entry.sequence)
        self.assertIsNone(result.entry.previous_hash)
        self.assertEqual(AUDIT_LEDGER_SCHEMA_VERSION, result.entry.schema_version)
        self.assertEqual(AUDIT_LEDGER_GENESIS_PREVIOUS_HASH, records[0]["previous_hash"])
        self.assertEqual(result.entry.entry_hash, verified.final_entry_hash)

    def test_append_second_entry_chain_links_previous_entry_hash(self):
        with TemporaryDirectory() as tmp:
            first = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 1},
            )
            second = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 2},
            )
            result = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

        self.assertTrue(first.appended)
        self.assertTrue(second.appended)
        self.assertEqual(first.entry.entry_hash, second.entry.previous_hash)
        self.assertTrue(result.valid)
        self.assertEqual(2, result.event_count)
        self.assertEqual(second.entry.entry_hash, result.final_entry_hash)

    def test_append_and_verify_reject_tampered_evidence_and_previous_hash(self):
        with TemporaryDirectory() as tmp:
            append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"path": "a"},
            )
            append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"path": "b"},
            )
            records = self.read_records(tmp, filename="ledger.jsonl")
            records[1]["evidence"]["path"] = "tampered"
            self.write_records(tmp, records, filename="ledger.jsonl")
            tampered = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

            records[1]["previous_hash"] = "0" * 64
            self.write_records(tmp, records, filename="ledger.jsonl")
            previous_mismatch = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

        self.assertFalse(tampered.valid)
        self.assertTrue(any("entry_hash mismatch" in issue for issue in tampered.issues))
        self.assertFalse(previous_mismatch.valid)
        self.assertTrue(any("previous_hash mismatch" in issue for issue in previous_mismatch.issues))

    def test_detect_malformed_json_and_missing_required_field(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "ledger.jsonl").write_text("{not-json}\n", encoding="utf-8")
            malformed = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

            (Path(tmp) / "ledger.jsonl").write_text('{"schema_version":"bad"}\n', encoding="utf-8")
            missing_field = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

        self.assertFalse(malformed.valid)
        self.assertTrue(any("malformed JSONL" in issue for issue in malformed.issues))
        self.assertFalse(missing_field.valid)
        self.assertTrue(any("missing required field" in issue for issue in missing_field.issues))

    def test_truncation_is_detected_with_expected_final_hash(self):
        with TemporaryDirectory() as tmp:
            first = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 1},
            )
            second = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 2},
            )
            records = self.read_records(tmp, filename="ledger.jsonl")
            self.write_records(tmp, records[:1], filename="ledger.jsonl")

            truncated = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                expected_final_entry_hash=second.entry_hash,
            )

        self.assertFalse(truncated.valid)
        self.assertTrue(any("final hash" in issue for issue in truncated.issues))

    def test_append_fails_closed_when_expected_sequence_or_chain_tampered(self):
        with TemporaryDirectory() as tmp:
            append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 1},
            )
            append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 2},
            )
            records = self.read_records(tmp, filename="ledger.jsonl")
            records[1]["sequence"] = 10
            self.write_records(tmp, records, filename="ledger.jsonl")

            result = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"step": 3},
            )
            records_after = self.read_records(tmp, filename="ledger.jsonl")

        self.assertFalse(result.appended)
        self.assertTrue(result.blocking)
        self.assertEqual(2, len(records_after))

    def test_invalid_ledger_path_is_rejected(self):
        invalid_filenames = (
            "",
            "../escape.jsonl",
            "/absolute.jsonl",
            "nested/events.jsonl",
            "nested\\events.jsonl",
            "bad\x00name.jsonl",
            ".hidden.jsonl",
        )
        with TemporaryDirectory() as tmp:
            for filename in invalid_filenames:
                with self.subTest(filename=repr(filename)):
                    append_result = append_audit_entry(
                        ledger_dir=tmp,
                        ledger_filename=filename,
                        event_type="AUDIT_EVENT",
                        evidence={"blocked": True},
                    )
                    verify_result = verify_audit_ledger(
                        ledger_dir=tmp,
                        ledger_filename=filename,
                    )
                    self.assertFalse(append_result.appended)
                    self.assertTrue(append_result.blocking)
                    self.assertFalse(verify_result.valid)

    def test_static_no_new_capability_scan_for_audit_ledger_module(self):
        source = (Path(__file__).resolve().parents[1] / "runtime" / "audit_ledger.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports: list[str] = []
        forbidden_imports = {
            "subprocess",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "requests",
            "httpx",
            "git",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.cloud",
            "langchain",
            "litellm",
        }
        called_names: set[str] = set()
        called_attrs: set[tuple[str | None, str]] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
                    called_attrs.add((owner, node.func.attr))

        forbidden_calls = {
            ("os", "system"),
            ("subprocess", "run"),
            ("subprocess", "Popen"),
            ("subprocess", "call"),
            ("subprocess", "check_call"),
            ("subprocess", "check_output"),
            ("webbrowser", "open"),
        }
        forbidden_names = {
            "Popen",
            "exec",
            "eval",
            "dispatch",
            "install_package",
            "approval_bypass",
        }

        for module_name in imports:
            self.assertFalse(
                any(
                    module_name == forbidden
                    or module_name.startswith(forbidden + ".")
                    for forbidden in forbidden_imports
                ),
                module_name,
            )
        self.assertTrue(forbidden_calls.isdisjoint(called_attrs))
        self.assertTrue(forbidden_names.isdisjoint(called_names))

    def test_entry_structure_cannot_authorize_actions(self):
        with TemporaryDirectory() as tmp:
            result = append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"artifact": "file.txt"},
            )

        entry = result.entry
        self.assertIsNotNone(entry)
        self.assertIsInstance(entry, AuditLedgerEntry)
        self.assertIsNone(getattr(entry, "can_approve", None))
        self.assertIsNone(getattr(entry, "can_write", None))
        self.assertIsNone(getattr(entry, "can_execute", None))
        self.assertIsNone(getattr(entry, "approve", None))
        self.assertIsNone(getattr(entry, "execute", None))
        self.assertEqual(AUDIT_LEDGER_SCHEMA_VERSION, entry.schema_version)

    def test_entry_hash_is_deterministic_for_same_material(self):
        left = {
            "event_type": "AUDIT_EVENT",
            "sequence": 1,
            "previous_hash": None,
            "evidence": {"a": 1, "b": 2},
            "schema_version": AUDIT_LEDGER_SCHEMA_VERSION,
        }
        right = {
            "schema_version": AUDIT_LEDGER_SCHEMA_VERSION,
            "sequence": 1,
            "previous_hash": None,
            "event_type": "AUDIT_EVENT",
            "evidence": {"b": 2, "a": 1},
        }
        self.assertEqual(
            compute_audit_entry_hash(left),
            compute_audit_entry_hash(right),
        )
        with TemporaryDirectory() as tmp:
            append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"a": 1},
            )
            append_audit_entry(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
                event_type="AUDIT_EVENT",
                evidence={"a": 1},
            )
            records = self.read_records(tmp, filename="ledger.jsonl")
            records[1]["sequence"] = 1
            self.write_records(tmp, records, filename="ledger.jsonl")
            result = verify_audit_ledger(
                ledger_dir=tmp,
                ledger_filename="ledger.jsonl",
            )

        self.assertFalse(result.valid)
        self.assertTrue(any("sequence mismatch" in issue for issue in result.issues))

    def read_records(self, ledger_dir: str, filename: str = "events.jsonl") -> list[dict]:
        path = Path(ledger_dir) / filename
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def write_records(
        self,
        ledger_dir: str,
        records: list[dict],
        filename: str = "events.jsonl",
    ) -> None:
        path = Path(ledger_dir) / filename
        text = "".join(audit_ledger_canonical_json(record) + "\n" for record in records)
        path.write_text(text, encoding="utf-8")


class StandaloneDurableAuditLedgerStep13Tests(unittest.TestCase):
    def test_empty_nonexistent_ledger_verifies_without_creating_a_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"

            result = verify_standalone_audit_ledger(path)
            entries = read_standalone_audit_ledger(path)

            self.assertTrue(result.valid)
            self.assertEqual(StandaloneVerificationStatus.EMPTY_VALID, result.status)
            self.assertEqual(0, result.record_count)
            self.assertEqual(0, result.last_sequence)
            self.assertEqual(STANDALONE_GENESIS_HASH, result.last_entry_hash)
            self.assertEqual((), entries)
            self.assertFalse(path.exists())

    def test_first_append_creates_sequence_one_bound_to_genesis(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"

            result = append_standalone_audit_entry(
                path,
                "PROPOSAL_RECORDED",
                {"proposal_id": "proposal-1"},
            )
            verified = verify_standalone_audit_ledger(path)

        self.assertTrue(result.appended)
        self.assertEqual(StandaloneAppendStatus.APPENDED, result.status)
        self.assertIsNotNone(result.entry)
        self.assertIsNotNone(result.tip)
        self.assertEqual(STANDALONE_SCHEMA_VERSION, result.entry.schema_version)
        self.assertEqual(1, result.entry.sequence)
        self.assertEqual(STANDALONE_GENESIS_HASH, result.entry.previous_hash)
        self.assertEqual(result.entry.entry_hash, result.tip.last_entry_hash)
        self.assertEqual(result.tip, verified.tip)

    def test_multiple_appends_create_a_valid_contiguous_hash_chain(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            results = [
                append_standalone_audit_entry(path, "EVIDENCE", {"index": index})
                for index in range(1, 4)
            ]
            entries = read_standalone_audit_ledger(path)
            verified = verify_standalone_audit_ledger(path)

        self.assertTrue(all(result.appended for result in results))
        self.assertEqual((1, 2, 3), tuple(entry.sequence for entry in entries))
        self.assertEqual(entries[0].entry_hash, entries[1].previous_hash)
        self.assertEqual(entries[1].entry_hash, entries[2].previous_hash)
        self.assertTrue(verified.valid)
        self.assertEqual(3, verified.record_count)
        self.assertEqual(entries[-1].entry_hash, verified.last_entry_hash)

    def test_identical_event_payloads_still_produce_distinct_entries(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            first = self.append(path, payload={"same": True})
            second = self.append(path, payload={"same": True})

        self.assertNotEqual(first.entry.sequence, second.entry.sequence)
        self.assertNotEqual(first.entry.previous_hash, second.entry.previous_hash)
        self.assertNotEqual(first.entry.entry_hash, second.entry.entry_hash)

    def test_payload_key_order_does_not_change_canonical_first_record(self):
        with TemporaryDirectory() as left_tmp, TemporaryDirectory() as right_tmp:
            left_path = Path(left_tmp) / "ledger.jsonl"
            right_path = Path(right_tmp) / "ledger.jsonl"
            left = self.append(left_path, payload={"z": 2, "a": {"y": 1, "x": 0}})
            right = self.append(right_path, payload={"a": {"x": 0, "y": 1}, "z": 2})

            self.assertEqual(left.entry.entry_hash, right.entry.entry_hash)
            self.assertEqual(left_path.read_bytes(), right_path.read_bytes())

    def test_unicode_is_preserved_deterministically_after_reopen(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            payload = {"message": "zażółć gęślą jaźń", "emoji": "🔒"}
            self.append(path, payload=payload)

            raw = path.read_bytes()
            reopened = read_standalone_audit_ledger(path)
            verified = verify_standalone_audit_ledger(path)

        self.assertIn("zażółć".encode("utf-8"), raw)
        self.assertNotIn(b"\\u017c", raw)
        self.assertEqual(payload, reopened[0].to_dict()["payload"])
        self.assertTrue(verified.valid)

    def test_correct_expected_tip_verifies_and_wrong_tip_fails_closed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            appended = self.append(path)
            correct = verify_standalone_audit_ledger(path, expected_tip=appended.tip)
            wrong_tip = StandaloneAuditLedgerTip(
                record_count=1,
                last_sequence=1,
                last_entry_hash="a" * 64,
            )
            wrong = verify_standalone_audit_ledger(path, expected_tip=wrong_tip)

        self.assertTrue(correct.valid)
        self.assertFalse(wrong.valid)
        self.assertEqual(StandaloneVerificationStatus.EXPECTED_TIP_MISMATCH, wrong.status)

    def test_jsonl_records_have_exact_newline_and_canonical_format(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path, payload={"b": 2, "a": 1})
            self.append(path, payload={"d": 4, "c": 3})
            raw = path.read_bytes()

        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(2, raw.count(b"\n"))
        self.assertNotIn(b"\n\n", raw)
        for encoded_line in raw.splitlines():
            line = encoded_line.decode("utf-8")
            self.assertEqual(
                canonical_audit_ledger_json(json.loads(line)),
                line,
            )
            self.assertNotIn(": ", line)
            self.assertNotIn(", ", line)

    def test_verified_entries_and_nested_payloads_are_immutable(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path, payload={"nested": [{"value": 1}]})
            entry = read_standalone_audit_ledger(path)[0]

        with self.assertRaises((AttributeError, TypeError)):
            entry.sequence = 9
        with self.assertRaises(TypeError):
            entry.payload["nested"] = ()
        self.assertIsInstance(entry.payload["nested"], tuple)
        with self.assertRaises((AttributeError, TypeError)):
            entry.payload["nested"].append("forged")

    def test_direct_entry_constructor_recalculates_and_rejects_supplied_hash(self):
        with self.assertRaises(ValueError):
            StandaloneAuditLedgerEntry(
                schema_version=STANDALONE_SCHEMA_VERSION,
                sequence=1,
                event_type="FORGED",
                payload={"approved": True},
                previous_hash=STANDALONE_GENESIS_HASH,
                entry_hash="a" * 64,
            )

    def test_payload_mutation_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path, payload={"value": "original"})
            records = self.records(path)
            records[0]["payload"]["value"] = "tampered"
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.ENTRY_HASH_MISMATCH, 1)

    def test_event_type_mutation_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            records = self.records(path)
            records[0]["event_type"] = "FORGED_APPROVAL"
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.ENTRY_HASH_MISMATCH, 1)

    def test_sequence_mutation_is_detected_before_hash_acceptance(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            records = self.records(path)
            records[0]["sequence"] = 2
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.SEQUENCE_MISMATCH, 1)

    def test_previous_hash_mutation_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            records = self.records(path)
            records[0]["previous_hash"] = "b" * 64
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.PREVIOUS_HASH_MISMATCH, 1)

    def test_entry_hash_mutation_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            records = self.records(path)
            records[0]["entry_hash"] = "c" * 64
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.ENTRY_HASH_MISMATCH, 1)

    def test_middle_record_deletion_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append_chain(path, 3)
            records = self.records(path)
            self.write_records(path, [records[0], records[2]])

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.SEQUENCE_MISMATCH, 2)

    def test_middle_record_replacement_is_detected(self):
        with TemporaryDirectory() as first_tmp, TemporaryDirectory() as second_tmp:
            path = Path(first_tmp) / "ledger.jsonl"
            other_path = Path(second_tmp) / "ledger.jsonl"
            self.append_chain(path, 3, prefix="primary")
            self.append_chain(other_path, 2, prefix="other")
            records = self.records(path)
            records[1] = self.records(other_path)[1]
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.PREVIOUS_HASH_MISMATCH, 2)

    def test_record_reordering_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append_chain(path, 3)
            records = self.records(path)
            self.write_records(path, [records[1], records[0], records[2]])

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.SEQUENCE_MISMATCH, 1)

    def test_duplicate_record_is_detected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append_chain(path, 2)
            records = self.records(path)
            self.write_records(path, [records[0], records[0], records[1]])

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.SEQUENCE_MISMATCH, 2)

    def test_unknown_and_missing_top_level_fields_are_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            original = self.records(path)[0]
            cases = []
            extra = dict(original)
            extra["approved"] = True
            cases.append(extra)
            missing = dict(original)
            missing.pop("event_type")
            cases.append(missing)

            for record in cases:
                with self.subTest(fields=sorted(record)):
                    self.write_records(path, [record])
                    result = verify_standalone_audit_ledger(path)
                    self.assert_invalid(
                        result,
                        StandaloneVerificationStatus.SCHEMA_INVALID,
                        1,
                    )

    def test_wrong_schema_version_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            records = self.records(path)
            records[0]["schema_version"] = "audit-ledger-2"
            self.write_records(path, records)

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.SCHEMA_INVALID, 1)

    def test_boolean_zero_and_negative_sequences_are_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            original = self.records(path)[0]

            for sequence in (True, 0, -1):
                with self.subTest(sequence=sequence):
                    record = dict(original)
                    record["sequence"] = sequence
                    self.write_records(path, [record])
                    result = verify_standalone_audit_ledger(path)
                    self.assert_invalid(
                        result,
                        StandaloneVerificationStatus.SCHEMA_INVALID,
                        1,
                    )

    def test_malformed_hash_encodings_are_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            original = self.records(path)[0]

            for field, value in (
                ("entry_hash", "A" * 64),
                ("entry_hash", "g" * 64),
                ("entry_hash", "a" * 63),
                ("previous_hash", 7),
            ):
                with self.subTest(field=field, value=value):
                    record = dict(original)
                    record[field] = value
                    self.write_records(path, [record])
                    result = verify_standalone_audit_ledger(path)
                    self.assert_invalid(
                        result,
                        StandaloneVerificationStatus.SCHEMA_INVALID,
                        1,
                    )

    def test_noncanonical_json_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            record = self.records(path)[0]
            noncanonical = json.dumps(
                record,
                sort_keys=True,
                separators=(", ", ": "),
                ensure_ascii=False,
                allow_nan=False,
            )
            path.write_text(noncanonical + "\n", encoding="utf-8")

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.NON_CANONICAL_JSON, 1)

    def test_malformed_json_is_rejected_and_read_raises_controlled_error(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_bytes(b"{not-json}\n")

            result = verify_standalone_audit_ledger(path)
            with self.assertRaises(StandaloneAuditLedgerReadError) as raised:
                read_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.MALFORMED_JSON, 1)
        self.assertEqual(StandaloneVerificationStatus.MALFORMED_JSON, raised.exception.verification.status)

    def test_duplicate_json_object_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            line = path.read_text(encoding="utf-8").rstrip("\n")
            duplicate = line.replace(
                '"entry_hash":',
                '"entry_hash":"' + ("0" * 64) + '","entry_hash":',
                1,
            )
            path.write_text(duplicate + "\n", encoding="utf-8")

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.MALFORMED_JSON, 1)

    def test_invalid_utf8_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_bytes(b"\xff\n")

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.INVALID_UTF8, 1)

    def test_blank_jsonl_line_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            path.write_bytes(path.read_bytes() + b"\n")

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.SCHEMA_INVALID, 2)

    def test_partial_final_json_record_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_bytes(b'{"schema_version":"audit-ledger-1a"')

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.INCOMPLETE_FINAL_LINE, 1)

    def test_complete_record_without_final_newline_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            path.write_bytes(path.read_bytes()[:-1])

            result = verify_standalone_audit_ledger(path)

        self.assert_invalid(result, StandaloneVerificationStatus.INCOMPLETE_FINAL_LINE, 1)

    def test_complete_suffix_truncation_requires_expected_tip_to_detect(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            results = self.append_chain(path, 3)
            retained_tip = results[-1].tip
            records = self.records(path)
            self.write_records(path, records[:2])

            internal = verify_standalone_audit_ledger(path)
            against_tip = verify_standalone_audit_ledger(path, expected_tip=retained_tip)

        self.assertTrue(internal.valid)
        self.assertEqual(2, internal.record_count)
        self.assertFalse(against_tip.valid)
        self.assertEqual(StandaloneVerificationStatus.TRUNCATED_LEDGER, against_tip.status)

    def test_truncation_to_empty_is_detected_against_retained_tip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            retained_tip = self.append(path).tip
            path.write_bytes(b"")

            internal = verify_standalone_audit_ledger(path)
            against_tip = verify_standalone_audit_ledger(path, expected_tip=retained_tip)

        self.assertTrue(internal.valid)
        self.assertEqual(StandaloneVerificationStatus.EMPTY_VALID, internal.status)
        self.assertEqual(StandaloneVerificationStatus.TRUNCATED_LEDGER, against_tip.status)

    def test_replacement_with_earlier_valid_copy_is_detected_against_tip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path, payload={"index": 1})
            earlier_valid_copy = path.read_bytes()
            retained_tip = self.append(path, payload={"index": 2}).tip
            path.write_bytes(earlier_valid_copy)

            internal = verify_standalone_audit_ledger(path)
            against_tip = verify_standalone_audit_ledger(path, expected_tip=retained_tip)

        self.assertTrue(internal.valid)
        self.assertEqual(StandaloneVerificationStatus.TRUNCATED_LEDGER, against_tip.status)

    def test_append_to_malformed_ledger_fails_without_changing_bytes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_bytes(b"{malformed}\n")
            before = path.read_bytes()

            result = append_standalone_audit_entry(path, "NEW_EVENT", {"value": 1})

            self.assertFalse(result.appended)
            self.assertEqual(StandaloneAppendStatus.EXISTING_LEDGER_INVALID, result.status)
            self.assertEqual(before, path.read_bytes())

    def test_append_to_tampered_ledger_fails_without_changing_bytes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            records = self.records(path)
            records[0]["payload"] = {"tampered": True}
            self.write_records(path, records)
            before = path.read_bytes()

            result = append_standalone_audit_entry(path, "NEW_EVENT", {"value": 1})

            self.assertFalse(result.appended)
            self.assertEqual(StandaloneAppendStatus.EXISTING_LEDGER_INVALID, result.status)
            self.assertEqual(before, path.read_bytes())

    def test_append_to_incomplete_ledger_fails_without_changing_bytes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            path.write_bytes(path.read_bytes()[:-1])
            before = path.read_bytes()

            result = append_standalone_audit_entry(path, "NEW_EVENT", {"value": 1})

            self.assertFalse(result.appended)
            self.assertEqual(StandaloneAppendStatus.EXISTING_LEDGER_INVALID, result.status)
            self.assertEqual(before, path.read_bytes())

    def test_unsupported_payloads_fail_before_any_file_mutation(self):
        cyclic: list[object] = []
        cyclic.append(cyclic)
        excessively_nested: object = None
        for _index in range(1_500):
            excessively_nested = [excessively_nested]
        unsupported = (
            b"bytes",
            {"set"},
            ("tuple",),
            object(),
            {1: "non-string key"},
            float("nan"),
            float("inf"),
            float("-inf"),
            cyclic,
            excessively_nested,
        )
        with TemporaryDirectory() as tmp:
            for index, payload in enumerate(unsupported):
                with self.subTest(payload_type=type(payload).__name__, index=index):
                    path = Path(tmp) / f"invalid-{index}.jsonl"
                    result = append_standalone_audit_entry(path, "EVENT", payload)
                    self.assertFalse(result.appended)
                    self.assertEqual(StandaloneAppendStatus.INVALID_PAYLOAD, result.status)
                    self.assertFalse(path.exists())

    def test_invalid_event_types_fail_before_any_file_mutation(self):
        invalid = (
            None,
            True,
            "",
            "   ",
            " surrounding ",
            "line\nbreak",
            "x" * (STANDALONE_EVENT_TYPE_LIMIT + 1),
        )
        with TemporaryDirectory() as tmp:
            for index, event_type in enumerate(invalid):
                with self.subTest(event_type=event_type):
                    path = Path(tmp) / f"invalid-event-{index}.jsonl"
                    result = append_standalone_audit_entry(path, event_type, {})
                    self.assertFalse(result.appended)
                    self.assertEqual(StandaloneAppendStatus.INVALID_EVENT_TYPE, result.status)
                    self.assertFalse(path.exists())

    def test_invalid_path_types_and_directory_target_fail_closed(self):
        for invalid_path in (None, 7, object()):
            with self.subTest(path_type=type(invalid_path).__name__):
                appended = append_standalone_audit_entry(invalid_path, "EVENT", {})
                verified = verify_standalone_audit_ledger(invalid_path)
                self.assertFalse(appended.appended)
                self.assertEqual(StandaloneAppendStatus.INVALID_PATH, appended.status)
                self.assertFalse(verified.valid)
                self.assertEqual(StandaloneVerificationStatus.INVALID_PATH, verified.status)

        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "ledger.jsonl"
            directory.mkdir()
            appended = append_standalone_audit_entry(directory, "EVENT", {})
            verified = verify_standalone_audit_ledger(directory)
            self.assertFalse(appended.appended)
            self.assertEqual(StandaloneAppendStatus.IO_ERROR, appended.status)
            self.assertEqual(StandaloneVerificationStatus.INVALID_PATH, verified.status)

    def test_symbolic_link_ledger_target_is_rejected_without_touching_target(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.jsonl"
            target.write_bytes(b"retained evidence\n")
            link = root / "ledger.jsonl"
            link.symlink_to(target)
            before = target.read_bytes()

            appended = append_standalone_audit_entry(link, "EVENT", {})
            verified = verify_standalone_audit_ledger(link)

            self.assertFalse(appended.appended)
            self.assertFalse(verified.valid)
            self.assertEqual(before, target.read_bytes())

    def test_dangling_symbolic_link_is_not_treated_as_an_empty_ledger(self):
        with TemporaryDirectory() as tmp:
            link = Path(tmp) / "ledger.jsonl"
            link.symlink_to(Path(tmp) / "missing-target.jsonl")

            verified = verify_standalone_audit_ledger(link)
            appended = append_standalone_audit_entry(link, "EVENT", {})

        self.assertFalse(verified.valid)
        self.assertEqual(StandaloneVerificationStatus.INVALID_PATH, verified.status)
        self.assertFalse(appended.appended)

    def test_append_uses_exclusive_lock_and_durability_flush(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            real_flock = fcntl.flock
            real_fsync = os.fsync
            with patch(
                "runtime.audit.durable_audit_ledger.fcntl.flock",
                wraps=real_flock,
            ) as flock_call, patch(
                "runtime.audit.durable_audit_ledger.os.fsync",
                wraps=real_fsync,
            ) as fsync_call:
                result = append_standalone_audit_entry(path, "EVENT", {})

        self.assertTrue(result.appended)
        lock_operations = [call.args[1] for call in flock_call.call_args_list]
        self.assertIn(fcntl.LOCK_EX, lock_operations)
        self.assertIn(fcntl.LOCK_UN, lock_operations)
        fsync_call.assert_called_once()

    def test_authority_looking_command_and_provider_payloads_remain_inert(self):
        payload = {
            "approved": True,
            "human_approved": True,
            "gate_result": {
                "status": "GATE_PASSED",
                "decision": "APPROVE",
                "artifact_hash": "a" * 64,
            },
            "provider_action": {
                "command": "sudo apt install curl",
                "execute": True,
            },
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            result = self.append(path, payload=payload)
            verified = verify_standalone_audit_ledger(path)
            stored = read_standalone_audit_ledger(path)[0].to_dict()["payload"]

        self.assertEqual(payload, stored)
        for evidence in (result.entry, result.tip, verified):
            self.assertIsNone(getattr(evidence, "approve", None))
            self.assertIsNone(getattr(evidence, "authorize", None))
            self.assertIsNone(getattr(evidence, "execute", None))

    def test_append_and_verify_call_no_shell_provider_or_writer(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            with patch("os.system", side_effect=AssertionError("shell forbidden")) as shell_call, patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("process forbidden"),
            ) as process_call, patch(
                "runtime.providers.gateway.run_provider_request",
                side_effect=AssertionError("provider forbidden"),
            ) as provider_call, patch(
                "runtime.safety.sandbox_artifact_runner.write_sandbox_artifact",
                side_effect=AssertionError("writer forbidden"),
            ) as writer_call:
                appended = append_standalone_audit_entry(
                    path,
                    "INERT_COMMAND",
                    {"command": "sudo apt install curl"},
                )
                verified = verify_standalone_audit_ledger(path)

        self.assertTrue(appended.appended)
        self.assertTrue(verified.valid)
        shell_call.assert_not_called()
        process_call.assert_not_called()
        provider_call.assert_not_called()
        writer_call.assert_not_called()

    def test_ledger_entry_tip_and_verification_are_not_write_authority(self):
        from runtime.human_decision_gated_artifact_write import (
            ARTIFACT_WRITTEN,
            write_artifact_after_human_gate,
        )
        from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
        from runtime.schemas.sandbox_artifact import SandboxArtifactState
        from tests.canonical_human_gate_support import canonical_gate_and_artifact_request

        canonical_gate, request = canonical_gate_and_artifact_request(
            relative_output_path="step13-ledger-authority.txt",
            content_text="ledger metadata cannot authorize this write\n",
            run_id="step-13-ledger-authority",
        )
        with TemporaryDirectory() as audit_tmp:
            ledger_path = Path(audit_tmp) / "ledger.jsonl"
            appended = self.append(ledger_path, payload={"approved": True})
            verified = verify_standalone_audit_ledger(ledger_path)
            evidence_objects = (appended.entry, appended.tip, verified)

            for evidence in evidence_objects:
                with self.subTest(evidence_type=type(evidence).__name__), TemporaryDirectory() as workspace:
                    direct = write_sandbox_artifact(
                        request,
                        workspace,
                        approval_evidence=evidence,
                    )
                    target = Path(workspace) / request.relative_output_path
                    self.assertEqual(SandboxArtifactState.BLOCKED, direct.state)
                    self.assertFalse(direct.write_completed)
                    self.assertFalse(target.exists())

            with TemporaryDirectory() as workspace:
                wrapped = write_artifact_after_human_gate(
                    gate_result=appended.tip,
                    artifact_request=request,
                    workspace_root=workspace,
                    expected_packet_hash=canonical_gate.packet_hash,
                    expected_artifact_hash=request.content_hash,
                )
                target = Path(workspace) / request.relative_output_path
                self.assertNotEqual(ARTIFACT_WRITTEN, wrapped.status)
                self.assertFalse(wrapped.artifact_write_occurred)
                self.assertFalse(target.exists())

    def test_serialized_gate_shape_does_not_recreate_process_local_provenance(self):
        from runtime.human_decision_gate_integration import HumanDecisionPreArtifactGateResult
        from runtime.safety.approval_artifact_gate import PreArtifactApprovalGateResult
        from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
        from runtime.schemas.sandbox_artifact import SandboxArtifactState
        from tests.canonical_human_gate_support import canonical_gate_and_artifact_request

        canonical_gate, request = canonical_gate_and_artifact_request(
            relative_output_path="step13-reconstructed-gate.txt",
            content_text="serialized gate provenance stays inert\n",
            run_id="step-13-reconstructed-gate",
        )
        with TemporaryDirectory() as audit_tmp:
            ledger_path = Path(audit_tmp) / "ledger.jsonl"
            self.append(ledger_path, payload=canonical_gate.to_dict())
            reconstructed_data = read_standalone_audit_ledger(ledger_path)[0].to_dict()["payload"]
            reconstructed_data["gate_result"] = PreArtifactApprovalGateResult(
                **reconstructed_data["gate_result"]
            )
            reconstructed = HumanDecisionPreArtifactGateResult(**reconstructed_data)

            with TemporaryDirectory() as workspace:
                result = write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=reconstructed,
                )
                target = Path(workspace) / request.relative_output_path
                self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
                self.assertFalse(result.write_completed)
                self.assertFalse(target.exists())

    def test_module_is_standalone_and_exposes_no_mutation_or_authority_api(self):
        import runtime.audit.durable_audit_ledger as ledger_module

        module_path = REPO_ROOT / "runtime" / "audit" / "durable_audit_ledger.py"
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    calls.add(f"{node.func.value.id}.{node.func.attr}")

        forbidden_import_prefixes = (
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "runtime.human_decision",
            "runtime.safety",
            "runtime.providers",
            "runtime.patches",
            "runtime.browser",
        )
        forbidden_calls = {
            "os.system",
            "os.popen",
            "os.getenv",
            "subprocess.run",
            "subprocess.Popen",
            "eval",
            "exec",
        }
        forbidden_public_verbs = (
            "update",
            "delete",
            "replace",
            "rewrite",
            "repair",
            "truncate",
            "clear",
            "approve",
            "authorize",
            "execute",
            "dispatch",
        )

        self.assertFalse(
            any(
                imported == forbidden or imported.startswith(forbidden + ".")
                for imported in imports
                for forbidden in forbidden_import_prefixes
            )
        )
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertFalse(
            any(
                any(verb in exported.casefold() for verb in forbidden_public_verbs)
                for exported in ledger_module.__all__
            )
        )

    def test_existing_authority_and_capability_modules_do_not_import_ledger(self):
        fixed_paths = (
            REPO_ROOT / "runtime" / "human_decision_gate_integration.py",
            REPO_ROOT / "runtime" / "human_decision_gated_artifact_write.py",
            REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py",
            REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
        )
        recursive_paths = tuple((REPO_ROOT / "runtime" / "providers").rglob("*.py")) + tuple(
            (REPO_ROOT / "runtime" / "patches").rglob("*.py")
        )
        for path in (*fixed_paths, *recursive_paths):
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("runtime.audit.durable_audit_ledger", source)
                self.assertNotIn("from runtime.audit import", source)

    def test_expected_tip_must_be_exact_metadata_type(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.append(path)
            result = verify_standalone_audit_ledger(
                path,
                expected_tip={
                    "record_count": 1,
                    "last_sequence": 1,
                    "last_entry_hash": "a" * 64,
                },
            )

        self.assertFalse(result.valid)
        self.assertEqual(StandaloneVerificationStatus.SCHEMA_INVALID, result.status)

    def append(self, path: Path, *, payload=None, event_type: str = "TEST_EVENT"):
        result = append_standalone_audit_entry(
            path,
            event_type,
            {"fixture": True} if payload is None else payload,
        )
        self.assertTrue(result.appended, result.failure_reason)
        self.assertIsNotNone(result.entry)
        self.assertIsNotNone(result.tip)
        return result

    def append_chain(self, path: Path, count: int, prefix: str = "record"):
        return [
            self.append(path, payload={"value": f"{prefix}-{index}"})
            for index in range(1, count + 1)
        ]

    @staticmethod
    def records(path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    @staticmethod
    def write_records(path: Path, records: list[dict]) -> None:
        path.write_text(
            "".join(canonical_audit_ledger_json(record) + "\n" for record in records),
            encoding="utf-8",
        )

    def assert_invalid(self, result, status, line: int | None) -> None:
        self.assertFalse(result.valid)
        self.assertEqual(status, result.status)
        self.assertEqual(line, result.failure_line)
        self.assertTrue(result.failure_reason)


if __name__ == "__main__":
    unittest.main()
