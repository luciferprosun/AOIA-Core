from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from runtime_paths import runtime_state_dir


GENESIS_PREV_HASH = "0" * 64
ALLOWED_EVENT_TYPES = {
    "request_received",
    "route_decision",
    "retrieval_hit",
    "retrieval_miss",
    "action_proposed",
    "action_result",
    "provider_response",
    "shell_safety_warning",
    "high_risk_shell_advice",
    "runtime_note",
}
SENSITIVE_KEY_NAMES = {
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "private_key",
    "privatekey",
    "access_key",
    "accesskey",
    "client_secret",
    "clientsecret",
}
HEX_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalize_key(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def redact_payload_secrets(payload: Any) -> Any:
    """Return a JSON-safe payload with obvious secret values redacted."""
    if isinstance(payload, dict):
        redacted: dict[Any, Any] = {}
        for key, value in payload.items():
            normalized = _normalize_key(key)
            if normalized in SENSITIVE_KEY_NAMES:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_payload_secrets(value)
        return redacted
    if isinstance(payload, list):
        return [redact_payload_secrets(item) for item in payload]
    if isinstance(payload, tuple):
        return [redact_payload_secrets(item) for item in payload]
    return payload


def event_ledger_path(project_dir: Path | None = None) -> Path:
    """Return the append-only ledger path under the local AOIA runtime state tree."""
    base_project_dir = project_dir or Path(__file__).resolve().parents[1]
    ledger_dir = runtime_state_dir(base_project_dir) / "state"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    return ledger_dir / "event_ledger.jsonl"


def _timestamp_utc_text(clock: Callable[[], dt.datetime] | None = None) -> str:
    value = (clock or (lambda: dt.datetime.now(dt.timezone.utc)))()
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _event_hash(record: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def validate_event_shape(event: dict[str, Any]) -> dict[str, Any]:
    """Validate the prototype event schema and return a normalized copy."""
    if not isinstance(event, dict):
        raise TypeError("Event must be a dictionary.")

    required_fields = (
        "event_id",
        "timestamp_utc",
        "event_type",
        "source",
        "payload",
        "prev_hash",
        "event_hash",
    )
    normalized = dict(event)
    for field in required_fields:
        if field not in normalized:
            raise ValueError(f"Missing required event field: {field}")

    event_id = str(normalized["event_id"]).strip()
    timestamp_utc = str(normalized["timestamp_utc"]).strip()
    event_type = str(normalized["event_type"]).strip()
    source = str(normalized["source"]).strip()
    prev_hash = str(normalized["prev_hash"]).strip()
    event_hash = str(normalized["event_hash"]).strip()

    if not event_id:
        raise ValueError("event_id must be a non-empty string")
    if not timestamp_utc:
        raise ValueError("timestamp_utc must be a non-empty string")
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"Unsupported event_type: {event_type}")
    if not source:
        raise ValueError("source must be a non-empty string")
    if not HEX_HASH_RE.fullmatch(prev_hash):
        raise ValueError("prev_hash must be a 64-character hex string")
    if not HEX_HASH_RE.fullmatch(event_hash):
        raise ValueError("event_hash must be a 64-character hex string")

    try:
        parsed_timestamp = dt.datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp_utc must be an ISO 8601 timestamp") from exc
    if parsed_timestamp.tzinfo is None:
        raise ValueError("timestamp_utc must be timezone-aware")

    payload = normalized["payload"]
    try:
        _canonical_json(payload)
    except TypeError as exc:
        raise TypeError("payload must be JSON serializable") from exc

    if event_id != event_hash[:16]:
        raise ValueError("event_id must match the event_hash prefix")

    return normalized


def read_events(ledger_path: Path) -> list[dict[str, Any]]:
    """Read a JSONL ledger in append order."""
    if not ledger_path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Line {line_number}: invalid JSON") from exc
        if not isinstance(entry, dict):
            raise ValueError(f"Line {line_number}: event must be a JSON object")
        events.append(entry)
    return events


def append_event(
    event_type: str,
    source: str,
    payload: Any,
    project_dir: Path | None = None,
    clock: Callable[[], dt.datetime] | None = None,
) -> dict[str, Any]:
    """Append one ledger event in deterministic JSONL form."""
    event_type_text = str(event_type).strip()
    source_text = str(source).strip()
    if event_type_text not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"Unsupported event_type: {event_type_text}")
    if not source_text:
        raise ValueError("source must be a non-empty string")

    ledger_path = event_ledger_path(project_dir)
    prev_hash = GENESIS_PREV_HASH
    existing_events = read_events(ledger_path)
    if existing_events:
        last_event = validate_event_shape(existing_events[-1])
        prev_hash = last_event["event_hash"]

    safe_payload = redact_payload_secrets(payload)
    base_record = {
        "timestamp_utc": _timestamp_utc_text(clock),
        "event_type": event_type_text,
        "source": source_text,
        "payload": safe_payload,
        "prev_hash": prev_hash,
    }
    event_hash = _event_hash(base_record)
    record = {
        "event_id": event_hash[:16],
        **base_record,
        "event_hash": event_hash,
    }
    validate_event_shape(record)

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(record) + "\n")
    return record


@dataclass(frozen=True)
class EventLedgerVerificationResult:
    ok: bool
    entry_count: int
    terminal_hash: str
    issues: tuple[str, ...]


def verify_event_chain(source: Path | Iterable[dict[str, Any]]) -> EventLedgerVerificationResult:
    """Verify the append-only chain for a ledger path or an in-memory sequence."""
    try:
        events = read_events(source) if isinstance(source, Path) else list(source)
    except Exception as exc:  # pragma: no cover - defensive path exercised by tamper tests
        return EventLedgerVerificationResult(
            ok=False,
            entry_count=0,
            terminal_hash=GENESIS_PREV_HASH,
            issues=(str(exc),),
        )

    issues: list[str] = []
    previous_hash = GENESIS_PREV_HASH
    terminal_hash = GENESIS_PREV_HASH

    for index, entry in enumerate(events):
        try:
            normalized = validate_event_shape(entry)
        except Exception as exc:
            issues.append(f"entry[{index}]: {exc}")
            continue

        expected_base = {
            "timestamp_utc": normalized["timestamp_utc"],
            "event_type": normalized["event_type"],
            "source": normalized["source"],
            "payload": normalized["payload"],
            "prev_hash": normalized["prev_hash"],
        }
        expected_hash = _event_hash(expected_base)

        if index == 0 and normalized["prev_hash"] != GENESIS_PREV_HASH:
            issues.append(f"entry[{index}]: first entry prev_hash must be genesis")
        elif index > 0 and normalized["prev_hash"] != previous_hash:
            issues.append(f"entry[{index}]: prev_hash mismatch")

        if normalized["event_hash"] != expected_hash:
            issues.append(f"entry[{index}]: event_hash mismatch")
        if normalized["event_id"] != expected_hash[:16]:
            issues.append(f"entry[{index}]: event_id mismatch")

        previous_hash = normalized["event_hash"]
        terminal_hash = normalized["event_hash"]

    return EventLedgerVerificationResult(
        ok=not issues,
        entry_count=len(events),
        terminal_hash=terminal_hash,
        issues=tuple(issues),
    )
