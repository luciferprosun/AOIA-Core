from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from tools.provenance import AppendOnlyProvenanceStore
from tools.provenance_readout import main, render_integrity_report, verify_file


class FakeClock:
    def __init__(self) -> None:
        self._timestamps = [
            datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc),
        ]
        self._index = 0

    def __call__(self) -> datetime:
        value = self._timestamps[min(self._index, len(self._timestamps) - 1)]
        self._index += 1
        return value


class ProvenanceReadoutTests(unittest.TestCase):
    def _make_store(self, tmpdir: str) -> AppendOnlyProvenanceStore:
        store = AppendOnlyProvenanceStore(Path(tmpdir), clock=FakeClock())
        store.append_event("source_ingested", {"artifact": "knowledge/a.md"})
        store.append_event("source_ingested", {"artifact": "knowledge/b.md"})
        return store

    def test_readout_reports_pass_for_valid_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)

            result, deterministic = verify_file(store.log_path)
            report = render_integrity_report(store.log_path, result, deterministic)

            self.assertIn("status: PASS", report)
            self.assertIn("total_records: 2", report)
            self.assertIn("prev_hash_continuity: PASS", report)
            self.assertIn("payload_hash_verification: PASS", report)
            self.assertIn("deterministic_verification: PASS", report)
            self.assertIn("first_failure: none", report)

    def test_readout_reports_failure_location_for_broken_prev_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            entries = store.read_all()
            entries[1]["prev_hash"] = "f" * 64
            store.log_path.write_text(
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n",
                encoding="utf-8",
            )

            result, deterministic = verify_file(store.log_path)
            report = render_integrity_report(store.log_path, result, deterministic)

            self.assertIn("status: FAIL", report)
            self.assertIn("prev_hash_continuity: FAIL", report)
            self.assertIn("payload_hash_verification: PASS", report)
            self.assertIn("first_failure: entry[1]: prev_hash mismatch", report)

    def test_cli_returns_nonzero_for_failed_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            entries = store.read_all()
            entries[0]["payload"]["artifact"] = "knowledge/tampered.md"
            store.log_path.write_text(
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main([str(store.log_path)])

            self.assertEqual(exit_code, 1)
            self.assertIn("status: FAIL", output.getvalue())
            self.assertIn("payload_hash_verification: FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
