from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.provenance import (
    GENESIS_PREV_HASH,
    AppendOnlyProvenanceStore,
    hash_payload,
)


class FakeClock:
    def __init__(self, timestamps: list[datetime]) -> None:
        self._timestamps = timestamps
        self._index = 0

    def __call__(self) -> datetime:
        if self._index >= len(self._timestamps):
            return self._timestamps[-1]
        value = self._timestamps[self._index]
        self._index += 1
        return value


class AppendOnlyProvenanceTests(unittest.TestCase):
    def _make_store(self, tmpdir: str, timestamps: list[datetime]) -> AppendOnlyProvenanceStore:
        return AppendOnlyProvenanceStore(Path(tmpdir), clock=FakeClock(timestamps))

    def test_provenance_append_creates_new_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp, [datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc)])

            record = store.append_event("source_ingested", {"artifact": "knowledge/a.md"})

            self.assertTrue(store.log_path.exists())
            self.assertEqual(len(store.read_all()), 1)
            self.assertEqual(record["event_type"], "source_ingested")

    def test_prev_hash_links_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(
                tmp,
                [
                    datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
                    datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc),
                ],
            )

            first = store.append_event("source_ingested", {"artifact": "knowledge/a.md"})
            second = store.append_event("source_ingested", {"artifact": "knowledge/b.md"})

            self.assertEqual(first["prev_hash"], GENESIS_PREV_HASH)
            self.assertEqual(second["prev_hash"], first["entry_hash"])

    def test_first_entry_handles_empty_chain_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp, [datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc)])

            record = store.append_event("source_ingested", {"artifact": "knowledge/a.md"})

            self.assertEqual(record["prev_hash"], GENESIS_PREV_HASH)

    def test_append_preserves_previous_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(
                tmp,
                [
                    datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
                    datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc),
                ],
            )

            first = store.append_event("source_ingested", {"artifact": "knowledge/a.md"})
            store.append_event("source_ingested", {"artifact": "knowledge/b.md"})

            entries = store.read_all()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["entry_hash"], first["entry_hash"])
            self.assertEqual(entries[0]["payload"]["artifact"], "knowledge/a.md")

    def test_overwriting_through_standard_append_api_is_impossible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(
                tmp,
                [
                    datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
                    datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc),
                ],
            )

            original = store.append_event("source_ingested", {"artifact": "knowledge/a.md"})
            store.append_event("source_ingested", {"artifact": "knowledge/a.md"})

            entries = store.read_all()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["entry_hash"], original["entry_hash"])
            self.assertEqual(entries[0]["payload_hash"], original["payload_hash"])

    def test_payload_hash_changes_when_payload_changes(self) -> None:
        payload_a = {"artifact": "knowledge/a.md"}
        payload_b = {"artifact": "knowledge/b.md"}

        self.assertNotEqual(hash_payload(payload_a), hash_payload(payload_b))

    def test_invalid_payload_does_not_partially_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._make_store(tmp, [datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc)])

            with self.assertRaises(TypeError):
                store.append_event("source_ingested", None)  # type: ignore[arg-type]

            self.assertFalse(store.log_path.exists())

    def test_append_sequence_produces_deterministic_chain_structure(self) -> None:
        timestamps = [
            datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc),
            datetime(2026, 5, 26, 12, 0, 2, tzinfo=timezone.utc),
        ]

        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            store_a = self._make_store(tmp_a, list(timestamps))
            store_b = self._make_store(tmp_b, list(timestamps))

            payloads = [
                ("source_ingested", {"artifact": "knowledge/a.md"}),
                ("source_ingested", {"artifact": "knowledge/b.md"}),
                ("source_ingested", {"artifact": "knowledge/c.md"}),
            ]

            records_a = store_a.append_many(payloads)
            records_b = store_b.append_many(payloads)

            self.assertEqual(
                [
                    (item["event_type"], item["payload_hash"], item["prev_hash"])
                    for item in records_a
                ],
                [
                    (item["event_type"], item["payload_hash"], item["prev_hash"])
                    for item in records_b
                ],
            )


if __name__ == "__main__":
    unittest.main()
