from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProvenanceVerificationResult:
    ok: bool
    entry_count: int
    terminal_hash: str
    issues: tuple[str, ...]


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


def verify_provenance_chain(source: Path | Iterable[dict[str, Any]]) -> ProvenanceVerificationResult:
    entries = load_provenance_entries(source) if isinstance(source, Path) else list(source)
    issues: list[str] = []
    previous_hash = GENESIS_PREV_HASH
    terminal_hash = GENESIS_PREV_HASH

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(f"entry[{index}]: not a dictionary")
            continue

        timestamp = entry.get("timestamp")
        event_type = entry.get("event_type")
        payload = entry.get("payload")
        stored_payload_hash = entry.get("payload_hash")
        stored_prev_hash = entry.get("prev_hash")
        stored_entry_hash = entry.get("entry_hash")

        if index == 0 and stored_prev_hash != GENESIS_PREV_HASH:
            issues.append(f"entry[{index}]: first entry prev_hash must be genesis")
        elif index > 0 and stored_prev_hash != previous_hash:
            issues.append(f"entry[{index}]: prev_hash mismatch")

        if not isinstance(payload, dict):
            issues.append(f"entry[{index}]: payload is not a dictionary")
            computed_payload_hash = ""
        else:
            computed_payload_hash = hash_payload(payload)
            if stored_payload_hash != computed_payload_hash:
                issues.append(f"entry[{index}]: payload_hash mismatch")

        if not isinstance(timestamp, str) or not timestamp.strip():
            issues.append(f"entry[{index}]: missing timestamp")
        if not isinstance(event_type, str) or not event_type.strip():
            issues.append(f"entry[{index}]: missing event_type")
        if not isinstance(stored_prev_hash, str) or not stored_prev_hash.strip():
            issues.append(f"entry[{index}]: missing prev_hash")
        if not isinstance(stored_entry_hash, str) or not stored_entry_hash.strip():
            issues.append(f"entry[{index}]: missing entry_hash")

        if (
            isinstance(timestamp, str)
            and timestamp.strip()
            and isinstance(event_type, str)
            and event_type.strip()
            and isinstance(stored_prev_hash, str)
            and stored_prev_hash.strip()
            and computed_payload_hash
        ):
            expected_entry_hash = hash_entry(
                timestamp,
                event_type.strip(),
                computed_payload_hash,
                stored_prev_hash,
            )
            if isinstance(stored_entry_hash, str) and stored_entry_hash.strip() != expected_entry_hash:
                issues.append(f"entry[{index}]: entry_hash mismatch")
            terminal_hash = expected_entry_hash
            previous_hash = expected_entry_hash
        elif isinstance(stored_entry_hash, str) and stored_entry_hash.strip():
            terminal_hash = stored_entry_hash.strip()
            previous_hash = stored_entry_hash.strip()

    return ProvenanceVerificationResult(
        ok=not issues,
        entry_count=len(entries),
        terminal_hash=terminal_hash,
        issues=tuple(issues),
    )
