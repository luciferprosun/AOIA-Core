from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.provenance import AppendOnlyProvenanceStore, verify_provenance_chain


class FakeClock:
    def __init__(self, timestamps: list[datetime]) -> None:
        self._timestamps = timestamps
        self._index = 0

    def __call__(self) -> datetime:
        value = self._timestamps[min(self._index, len(self._timestamps) - 1)]
        self._index += 1
        return value


class ProvenanceVerificationTests(unittest.TestCase):
    def _make_store(self, tmpdir: str) -> AppendOnlyProvenanceStore:
        timestamps = [
            datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc),
            datetime(2026, 5, 26, 12, 0, 2, tzinfo=timezone.utc),
        ]
        return AppendOnlyProvenanceStore(Path(tmpdir), clock=FakeClock(timestamps))

    def _write_chain(self, store: AppendOnlyProvenanceStore) -> list[dict[str, object]]:
        store.append_event("source_ingested", {"artifact": "knowledge/a.md"})
        store.append_event("source_ingested", {"artifact": "knowledge/b.md"})
        store.append_event("source_ingested", {"artifact": "knowledge/c.md"})
        return store.read_all()

    def test_valid_chain_verifies_successfully(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            self._write_chain(store)

            result = verify_provenance_chain(store.log_path)

            self.assertTrue(result.ok)
            self.assertEqual(result.entry_count, 3)
            self.assertEqual(result.issues, ())

    def test_broken_prev_hash_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            self._write_chain(store)

            entries = store.read_all()
            entries[1]["prev_hash"] = "f" * 64
            store.log_path.write_text(
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n",
                encoding="utf-8",
            )

            result = verify_provenance_chain(store.log_path)

            self.assertFalse(result.ok)
            self.assertTrue(any("prev_hash mismatch" in issue for issue in result.issues))

    def test_modified_payload_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            self._write_chain(store)

            entries = store.read_all()
            entries[0]["payload"]["artifact"] = "knowledge/tampered.md"
            store.log_path.write_text(
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n",
                encoding="utf-8",
            )

            result = verify_provenance_chain(store.log_path)

            self.assertFalse(result.ok)
            self.assertTrue(any("payload_hash mismatch" in issue for issue in result.issues))

    def test_missing_entry_linkage_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            entries = self._write_chain(store)
            trimmed = [entries[0], entries[2]]
            store.log_path.write_text(
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in trimmed) + "\n",
                encoding="utf-8",
            )

            result = verify_provenance_chain(store.log_path)

            self.assertFalse(result.ok)
            self.assertTrue(any("prev_hash mismatch" in issue for issue in result.issues))

    def test_empty_chain_handled_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)

            result = verify_provenance_chain(store.log_path)

            self.assertTrue(result.ok)
            self.assertEqual(result.entry_count, 0)

    def test_verification_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            self._write_chain(store)

            result_a = verify_provenance_chain(store.log_path)
            result_b = verify_provenance_chain(store.log_path)

            self.assertEqual(result_a, result_b)

    def test_verification_does_not_mutate_provenance_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp)
            original_entries = self._write_chain(store)
            snapshot = json.loads(json.dumps(original_entries))
            before = store.log_path.read_text(encoding="utf-8")

            result = verify_provenance_chain(original_entries)

            after = store.log_path.read_text(encoding="utf-8")
            self.assertTrue(result.ok)
            self.assertEqual(original_entries, snapshot)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
