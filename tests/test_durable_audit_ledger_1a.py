from __future__ import annotations

import ast
import hashlib
import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

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
if __name__ == "__main__":
    unittest.main()
