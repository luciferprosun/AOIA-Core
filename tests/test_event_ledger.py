from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.event_ledger import (
    GENESIS_PREV_HASH,
    append_event,
    event_ledger_path,
    read_events,
    redact_payload_secrets,
    validate_event_shape,
    verify_event_chain,
)


class FakeClock:
    def __init__(self) -> None:
        self._timestamps = [
            dt.datetime(2026, 6, 1, 17, 0, tzinfo=dt.timezone.utc),
            dt.datetime(2026, 6, 1, 17, 1, tzinfo=dt.timezone.utc),
            dt.datetime(2026, 6, 1, 17, 2, tzinfo=dt.timezone.utc),
        ]
        self._index = 0

    def __call__(self) -> dt.datetime:
        value = self._timestamps[min(self._index, len(self._timestamps) - 1)]
        self._index += 1
        return value


class EventLedgerTests(unittest.TestCase):
    def test_ledger_path_uses_aoia_home_not_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                path = event_ledger_path(project_dir)

            self.assertTrue(path.is_relative_to(aoia_home))
            self.assertFalse(path.is_relative_to(Path(__file__).resolve().parents[1] / "runtime"))
            self.assertEqual(path.name, "event_ledger.jsonl")

    def test_append_event_writes_one_jsonl_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                record = append_event(
                    "request_received",
                    "test",
                    {"prompt": "hello"},
                    project_dir=project_dir,
                    clock=FakeClock(),
                )
                lines = event_ledger_path(project_dir).read_text(encoding="utf-8").splitlines()

            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), record)
            self.assertEqual(record["prev_hash"], GENESIS_PREV_HASH)

    def test_read_events_returns_events_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            clock = FakeClock()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                first = append_event("request_received", "test", {"index": 1}, project_dir, clock)
                second = append_event("runtime_note", "test", {"index": 2}, project_dir, clock)
                events = read_events(event_ledger_path(project_dir))

            self.assertEqual([event["event_id"] for event in events], [first["event_id"], second["event_id"]])

    def test_two_event_hash_chain_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            clock = FakeClock()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                first = append_event("request_received", "test", {"index": 1}, project_dir, clock)
                second = append_event("action_result", "test", {"index": 2}, project_dir, clock)
                result = verify_event_chain(event_ledger_path(project_dir))

            self.assertEqual(second["prev_hash"], first["event_hash"])
            self.assertTrue(result.ok)
            self.assertEqual(result.entry_count, 2)
            self.assertEqual(result.terminal_hash, second["event_hash"])

    def test_invalid_event_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()

            with patch.dict("os.environ", {"AOIA_HOME": str(Path(tmp) / "aoia-home")}):
                with self.assertRaises(ValueError):
                    append_event("unknown_event", "test", {}, project_dir=project_dir, clock=FakeClock())

    def test_obvious_secret_payload_keys_are_redacted(self) -> None:
        payload = {
            "api_key": "live-key",
            "nested": {
                "password": "secret-password",
                "safe": "visible",
            },
            "items": [{"access-key": "access-secret"}],
        }

        redacted = redact_payload_secrets(payload)

        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["password"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["safe"], "visible")
        self.assertEqual(redacted["items"][0]["access-key"], "[REDACTED]")

    def test_appended_event_payload_redacts_obvious_secret_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                record = append_event(
                    "provider_response",
                    "test",
                    {"token": "abc123", "message": "ok"},
                    project_dir=project_dir,
                    clock=FakeClock(),
                )

            self.assertEqual(record["payload"]["token"], "[REDACTED]")
            self.assertEqual(record["payload"]["message"], "ok")

    def test_shell_safety_event_types_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            clock = FakeClock()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                warning = append_event(
                    "shell_safety_warning",
                    "respond_filter",
                    {"pattern": "find"},
                    project_dir,
                    clock,
                )
                high_risk = append_event(
                    "high_risk_shell_advice",
                    "respond_filter",
                    {"pattern": "rm -rf /"},
                    project_dir,
                    clock,
                )

            self.assertEqual(warning["event_type"], "shell_safety_warning")
            self.assertEqual(high_risk["event_type"], "high_risk_shell_advice")

    def test_no_source_tree_runtime_state_created(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        source_tree_ledger = repo_root / "runtime" / "state" / "event_ledger.jsonl"

        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                append_event("runtime_note", "test", {"note": "local only"}, project_dir, FakeClock())

        self.assertFalse(source_tree_ledger.exists())

    def test_validate_event_shape_rejects_bad_event_type(self) -> None:
        valid = {
            "event_id": "0" * 16,
            "timestamp_utc": "2026-06-01T17:00:00Z",
            "event_type": "not_allowed",
            "source": "test",
            "payload": {},
            "prev_hash": "0" * 64,
            "event_hash": "0" * 64,
        }

        with self.assertRaises(ValueError):
            validate_event_shape(valid)

    def test_tampered_event_payload_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aoia_home = Path(tmp) / "aoia-home"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            clock = FakeClock()

            with patch.dict("os.environ", {"AOIA_HOME": str(aoia_home)}):
                append_event("request_received", "test", {"index": 1}, project_dir, clock)
                append_event("action_result", "test", {"index": 2}, project_dir, clock)
                path = event_ledger_path(project_dir)
                events = read_events(path)
                events[1]["payload"]["index"] = 99
                path.write_text(
                    "\n".join(json.dumps(event, sort_keys=True, separators=(",", ":")) for event in events) + "\n",
                    encoding="utf-8",
                )
                result = verify_event_chain(path)

            self.assertFalse(result.ok)
            self.assertTrue(any("event_hash mismatch" in issue for issue in result.issues))

    def test_corrupt_event_line_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event_ledger.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")

            result = verify_event_chain(path)

            self.assertFalse(result.ok)
            self.assertTrue(result.issues)


if __name__ == "__main__":
    unittest.main()
