from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable


GENESIS_PREV_HASH = "0" * 64


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def hash_entry(timestamp: str, event_type: str, payload_hash: str, prev_hash: str) -> str:
    return hashlib.sha256(
        _canonical_json(
            {
                "timestamp": timestamp,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "prev_hash": prev_hash,
            }
        ).encode("utf-8")
    ).hexdigest()


def load_provenance_entries(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


class AppendOnlyProvenanceStore:
    """Minimal append-only provenance ledger with SHA-256 chaining."""

    def __init__(self, root_dir: Path, clock: Callable[[], dt.datetime] | None = None) -> None:
        self.root_dir = root_dir
        self.provenance_dir = root_dir / "provenance"
        self.log_path = self.provenance_dir / "provenance_log.jsonl"
        self._clock = clock or dt.datetime.now
        self.provenance_dir.mkdir(parents=True, exist_ok=True)

    def read_all(self) -> list[dict[str, Any]]:
        return load_provenance_entries(self.log_path)

    def latest_hash(self) -> str:
        entries = self.read_all()
        if not entries:
            return GENESIS_PREV_HASH
        return str(entries[-1].get("entry_hash", GENESIS_PREV_HASH))

    def append_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("Provenance event_type must be a non-empty string")
        if not isinstance(payload, dict):
            raise TypeError("Provenance payload must be a dictionary")

        payload_hash = hash_payload(payload)
        prev_hash = self.latest_hash()
        timestamp = self._clock().isoformat()
        record = {
            "timestamp": timestamp,
            "event_type": event_type.strip(),
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
            "entry_hash": hash_entry(timestamp, event_type.strip(), payload_hash, prev_hash),
            "payload": payload,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def append_many(self, events: Iterable[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for event_type, payload in events:
            records.append(self.append_event(event_type, payload))
        return records
