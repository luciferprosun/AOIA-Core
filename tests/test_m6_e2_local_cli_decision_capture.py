from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import unittest

from runtime.human_decision_capture_cli import (
    EXIT_CAPTURED_APPROVE,
    EXIT_CAPTURED_REJECT,
    EXIT_INVALID_INPUT,
    EXIT_STALE_OR_MISMATCHED,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "runtime" / "human_decision_capture_cli.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
ARTIFACT_HASH = "b" * 64


class M6E2LocalCLIDecisionCaptureTests(unittest.TestCase):
    def test_explicit_approve_with_matching_hashes(self):
        exit_code, payload = self.invoke("--decision", "APPROVE")

        self.assertEqual(EXIT_CAPTURED_APPROVE, exit_code)
        self.assertEqual("CAPTURED_APPROVE", payload["outcome_state"])
        self.assertEqual("APPROVE", payload["decision"])
        self.assertTrue(payload["decision_captured"])

    def test_explicit_reject_is_visible_and_blocking(self):
        exit_code, payload = self.invoke("--decision", "REJECT")

        self.assertEqual(EXIT_CAPTURED_REJECT, exit_code)
        self.assertEqual("CAPTURED_REJECT", payload["outcome_state"])
        self.assertEqual("REJECT", payload["decision"])
        self.assertTrue(payload["blocking"])
        self.assertIn("REJECT is blocking", payload["messages"])

    def test_missing_decision_fails_without_default_approve(self):
        exit_code, payload = self.invoke()

        self.assertEqual(EXIT_INVALID_INPUT, exit_code)
        self.assertFalse(payload["decision_captured"])
        self.assertNotEqual("CAPTURED_APPROVE", payload["outcome_state"])

    def test_unknown_decisions_fail(self):
        for decision in ("YES", "OK", "ACCEPT", "TRUE", "CANONICAL", "SAFE_FOR_RUNTIME"):
            with self.subTest(decision=decision):
                exit_code, payload = self.invoke("--decision", decision)
                self.assertEqual(EXIT_INVALID_INPUT, exit_code)
                self.assertFalse(payload["decision_captured"])

    def test_missing_packet_hash_fails(self):
        exit_code, payload = self.invoke_raw("--decision", "APPROVE")

        self.assertEqual(EXIT_INVALID_INPUT, exit_code)
        self.assertFalse(payload["decision_captured"])

    def test_stale_packet_hash_blocks(self):
        exit_code, payload = self.invoke(
            "--decision",
            "APPROVE",
            current_packet_hash="c" * 64,
        )

        self.assertEqual(EXIT_STALE_OR_MISMATCHED, exit_code)
        self.assertEqual("BLOCKED_STALE_OR_MISMATCHED_PACKET", payload["outcome_state"])
        self.assertTrue(payload["blocking"])

    def test_stale_artifact_hash_blocks(self):
        exit_code, payload = self.invoke(
            "--decision",
            "APPROVE",
            extra_args=(
                "--displayed-artifact-hash",
                ARTIFACT_HASH,
                "--current-artifact-hash",
                "c" * 64,
            ),
        )

        self.assertEqual(EXIT_STALE_OR_MISMATCHED, exit_code)
        self.assertEqual("BLOCKED_STALE_OR_MISMATCHED_PACKET", payload["outcome_state"])

    def test_successful_and_blocked_output_is_json(self):
        cases = (
            self.invoke("--decision", "APPROVE"),
            self.invoke("--decision", "REJECT"),
            self.invoke("--decision", "APPROVE", current_packet_hash="c" * 64),
            self.invoke(),
        )

        for _, payload in cases:
            self.assertIsInstance(payload, dict)

    def test_output_preserves_non_authority_boundaries(self):
        for decision in ("APPROVE", "REJECT"):
            with self.subTest(decision=decision):
                _, payload = self.invoke("--decision", decision)
                self.assertEqual("HumanDecisionCaptureIntent", payload["result_type"])
                self.assertFalse(payload["is_approval_authority"])
                self.assertTrue(payload["approval_decision_required"])
                self.assertEqual("REQUIRED_NOT_CREATED", payload["approval_decision_status"])
                self.assertTrue(payload["durable_audit_handoff_required"])
                self.assertFalse(payload["pre_artifact_gate_passed"])
                self.assertFalse(payload["artifact_write_occurred"])
                self.assertIn("not approval authority", payload["authority_notice"].lower())

    def test_cli_has_no_gate_handoff_or_write_calls(self):
        source = CLI.read_text(encoding="utf-8")
        forbidden_terms = (
            "evaluate_pre_artifact_approval_gate",
            "append_audit_event_jsonl",
            "write_sandbox_artifact",
            "gated_durable_artifact",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "open(",
        )
        for term in forbidden_terms:
            self.assertNotIn(term, source)

    def test_cli_has_no_external_integration_or_dangerous_imports(self):
        forbidden_imports = (
            "sub" + "process",
            "url" + "lib",
            "sock" + "et",
            "web" + "browser",
            "play" + "wright",
            "sele" + "nium",
            "requ" + "ests",
            "ht" + "tpx",
        )
        for path in (CLI, THIS_FILE):
            source = path.read_text(encoding="utf-8")
            for module_name in forbidden_imports:
                self.assertIsNone(
                    re.search(rf"^\s*(from|import)\s+{re.escape(module_name)}\b", source, re.MULTILINE)
                )
            self.assertIsNone(re.search(r"\bos\s*\.\s*system\s*\(", source))
            self.assertNotIn("P" + "open", source)

        cli_source = CLI.read_text(encoding="utf-8").lower()
        forbidden_paths = (
            "pro" + "vider",
            "mo" + "del",
            "g" + "pt",
            "open" + "ai",
            "anth" + "ropic",
            "gem" + "ini",
            "g" + "cloud",
        )
        for term in forbidden_paths:
            self.assertNotIn(term, cli_source)

    def test_cli_exposes_no_metadata_authority_input(self):
        source = CLI.read_text(encoding="utf-8")
        self.assertNotIn("--metadata", source)
        self.assertNotIn("--tags", source)
        self.assertNotIn("--hats", source)
        self.assertNotIn("--tetrads", source)
        self.assertNotIn("--geometry", source)

    def invoke(
        self,
        *decision_args: str,
        current_packet_hash: str = PACKET_HASH,
        extra_args: tuple[str, ...] = (),
    ) -> tuple[int, dict[str, object]]:
        return self.invoke_raw(
            *decision_args,
            "--displayed-packet-hash",
            PACKET_HASH,
            "--current-packet-hash",
            current_packet_hash,
            *extra_args,
        )

    def invoke_raw(self, *args: str) -> tuple[int, dict[str, object]]:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(args)
        payload = json.loads(output.getvalue())
        return exit_code, payload


if __name__ == "__main__":
    unittest.main()
