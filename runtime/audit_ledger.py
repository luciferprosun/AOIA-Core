from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

AUDIT_LEDGER_SCHEMA_VERSION = "AOIA_AUDIT_LEDGER_1A"
AUDIT_LEDGER_GENESIS_PREVIOUS_HASH = None

_REQUIRED_FIELDS = {
    "schema_version",
    "sequence",
    "previous_hash",
    "event_type",
    "evidence",
    "entry_hash",
}


@dataclass(frozen=True)
class AuditLedgerEntry:
    schema_version: str
    sequence: int
    previous_hash: str | None
    event_type: str
    evidence: Mapping[str, Any]
    entry_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text(self.schema_version, "schema_version"))
        object.__setattr__(self, "sequence", _positive_int(self.sequence, "sequence"))
        if self.previous_hash is not None:
            object.__setattr__(self, "previous_hash", _full_hash(self.previous_hash, "previous_hash"))
        elif self.sequence != 1:
            raise ValueError("previous_hash must be present for sequence > 1")
        object.__setattr__(self, "event_type", _text(self.event_type, "event_type"))
        object.__setattr__(self, "evidence", _freeze_evidence(self.evidence))
        object.__setattr__(self, "entry_hash", _full_hash(self.entry_hash, "entry_hash"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sequence": self.sequence,
            "previous_hash": self.previous_hash,
            "event_type": self.event_type,
            "evidence": self.evidence,
            "entry_hash": self.entry_hash,
        }


@dataclass(frozen=True)
class AuditLedgerAppendResult:
    appended: bool
    blocking: bool
    ledger_path: str | None
    entry: AuditLedgerEntry | None
    entry_hash: str | None
    sequence: int | None
    previous_hash: str | None
    reason: str


@dataclass(frozen=True)
class AuditLedgerVerificationResult:
    valid: bool
    blocking: bool
    ledger_path: str | None
    event_count: int
    final_entry_hash: str | None
    issues: tuple[str, ...]


def canonical_audit_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def compute_audit_entry_hash(
    entry_material: Mapping[str, Any] | AuditLedgerEntry,
) -> str:
    if isinstance(entry_material, AuditLedgerEntry):
        material = entry_material.to_dict()
    elif isinstance(entry_material, Mapping):
        material = dict(entry_material)
    else:
        raise TypeError("entry_material must be a mapping or AuditLedgerEntry")

    material = dict(material)
    material.pop("entry_hash", None)
    return _sha256(canonical_audit_json(material))


def append_audit_entry(
    *,
    ledger_dir: str | Path,
    ledger_filename: str,
    event_type: str,
    evidence: Mapping[str, Any],
) -> AuditLedgerAppendResult:
    try:
        ledger_path = _resolve_ledger_path(ledger_dir=ledger_dir, ledger_filename=ledger_filename, create_dir=True)
        verified = verify_audit_ledger(ledger_dir=ledger_dir, ledger_filename=ledger_filename)
        if not verified.valid:
            return AuditLedgerAppendResult(
                appended=False,
                blocking=True,
                ledger_path=str(ledger_path),
                entry=None,
                entry_hash=None,
                sequence=None,
                previous_hash=None,
                reason="existing ledger failed verification",
            )

        sequence = verified.event_count + 1
        material: dict[str, Any] = {
            "schema_version": AUDIT_LEDGER_SCHEMA_VERSION,
            "sequence": sequence,
            "previous_hash": verified.final_entry_hash,
            "event_type": event_type,
            "evidence": _freeze_evidence(evidence),
        }
        entry = AuditLedgerEntry(
            **material,
            entry_hash=compute_audit_entry_hash(material),
        )

        if not ledger_path.exists():
            ledger_path.touch(mode=0o600)
        if not ledger_path.is_file():
            return AuditLedgerAppendResult(
                appended=False,
                blocking=True,
                ledger_path=str(ledger_path),
                entry=None,
                entry_hash=None,
                sequence=None,
                previous_hash=None,
                reason="ledger path is not a regular file",
            )

        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_audit_json(entry.to_dict()) + "\n")

        return AuditLedgerAppendResult(
            appended=True,
            blocking=False,
            ledger_path=str(ledger_path),
            entry=entry,
            entry_hash=entry.entry_hash,
            sequence=entry.sequence,
            previous_hash=entry.previous_hash,
            reason="audit ledger entry appended",
        )
    except Exception as exc:
        return AuditLedgerAppendResult(
            appended=False,
            blocking=True,
            ledger_path=None,
            entry=None,
            entry_hash=None,
            sequence=None,
            previous_hash=None,
            reason=str(exc),
        )


def verify_audit_ledger(
    *,
    ledger_dir: str | Path,
    ledger_filename: str,
    expected_final_entry_hash: str | None = None,
) -> AuditLedgerVerificationResult:
    try:
        ledger_path = _resolve_ledger_path(ledger_dir=ledger_dir, ledger_filename=ledger_filename, create_dir=False)
    except Exception as exc:
        return AuditLedgerVerificationResult(
            valid=False,
            blocking=True,
            ledger_path=None,
            event_count=0,
            final_entry_hash=None,
            issues=(str(exc),),
        )

    if not ledger_path.exists():
        if expected_final_entry_hash is not None:
            return AuditLedgerVerificationResult(
                valid=False,
                blocking=True,
                ledger_path=str(ledger_path),
                event_count=0,
                final_entry_hash=None,
                issues=("audit ledger is missing expected final entry",),
            )
        return AuditLedgerVerificationResult(
            valid=True,
            blocking=False,
            ledger_path=str(ledger_path),
            event_count=0,
            final_entry_hash=None,
            issues=(),
        )

    if ledger_path.is_symlink():
        return AuditLedgerVerificationResult(
            valid=False,
            blocking=True,
            ledger_path=str(ledger_path),
            event_count=0,
            final_entry_hash=None,
            issues=("audit ledger path is a symlink",),
        )

    if not ledger_path.is_file():
        return AuditLedgerVerificationResult(
            valid=False,
            blocking=True,
            ledger_path=str(ledger_path),
            event_count=0,
            final_entry_hash=None,
            issues=("audit ledger path is not a regular file",),
        )

    issues: list[str] = []
    expected_sequence = 1
    expected_previous_hash: str | None = AUDIT_LEDGER_GENESIS_PREVIOUS_HASH
    final_hash: str | None = None
    event_count = 0
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return AuditLedgerVerificationResult(
            valid=False,
            blocking=True,
            ledger_path=str(ledger_path),
            event_count=0,
            final_entry_hash=None,
            issues=(str(exc),),
        )

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        event_count += 1
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            issues.append(f"line {line_number}: malformed JSONL")
            continue

        if not isinstance(decoded, dict):
            issues.append(f"line {line_number}: entry must be JSON object")
            continue

        missing = sorted(_REQUIRED_FIELDS - set(decoded))
        if missing:
            issues.append(f"line {line_number}: missing required field {missing[0]}")
            continue

        try:
            entry = AuditLedgerEntry(
                schema_version=decoded.get("schema_version"),
                sequence=decoded.get("sequence"),
                previous_hash=decoded.get("previous_hash"),
                event_type=decoded.get("event_type"),
                evidence=decoded.get("evidence"),
                entry_hash=decoded.get("entry_hash"),
            )
        except Exception as exc:
            issues.append(f"line {line_number}: invalid entry structure: {exc}")
            continue

        if entry.schema_version != AUDIT_LEDGER_SCHEMA_VERSION:
            issues.append(f"line {line_number}: invalid schema_version")

        if entry.sequence != expected_sequence:
            issues.append(f"line {line_number}: sequence mismatch")

        if entry.previous_hash != expected_previous_hash:
            issues.append(f"line {line_number}: previous_hash mismatch")

        expected_entry_hash = compute_audit_entry_hash(entry)
        if entry.entry_hash != expected_entry_hash:
            issues.append(f"line {line_number}: entry_hash mismatch")

        expected_previous_hash = entry.entry_hash
        expected_sequence += 1
        final_hash = entry.entry_hash

    if expected_final_entry_hash is not None:
        expected_final = _full_hash(expected_final_entry_hash, "expected_final_entry_hash")
        if final_hash != expected_final:
            issues.append("audit ledger truncated or final hash mismatch")

    return AuditLedgerVerificationResult(
        valid=not issues,
        blocking=bool(issues),
        ledger_path=str(ledger_path),
        event_count=event_count,
        final_entry_hash=final_hash,
        issues=tuple(issues),
    )


def _resolve_ledger_path(
    *,
    ledger_dir: str | Path,
    ledger_filename: str,
    create_dir: bool,
) -> Path:
    directory = Path(ledger_dir)
    if not isinstance(ledger_dir, (str, Path)):
        raise TypeError("ledger_dir must be a string or Path")
    if not str(directory).strip():
        raise ValueError("ledger directory must be explicit")
    if directory.is_absolute() is False:
        raise ValueError("ledger directory must be absolute")
    if directory.exists() and directory.is_symlink():
        raise ValueError("ledger directory must not be a symlink")
    if create_dir:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.exists() or not directory.is_dir():
        raise ValueError("ledger directory must exist")
    filename = _ledger_filename(ledger_filename)
    candidate = directory / filename
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("ledger path must not be a symlink")
    if candidate.exists() and candidate.is_dir():
        raise ValueError("ledger path is a directory")
    return candidate


def _ledger_filename(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("ledger_filename must be a string")
    filename = value.strip()
    if not filename:
        raise ValueError("ledger filename must not be empty")
    if "\x00" in filename:
        raise ValueError("ledger filename must not contain null bytes")
    if "/" in filename or "\\" in filename:
        raise ValueError("ledger filename must not include directories")
    if filename in {"", ".", ".."}:
        raise ValueError("ledger filename must be a base file name")
    if filename.startswith("."):
        raise ValueError("ledger filename must be an explicit local file name")
    return filename


def _full_hash(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a SHA-256 hex string")
    text = value.strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{field_name} must be a SHA-256 hex string")
    return text


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty text")
    return text


def _positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{field_name} must be int")
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be int")
    if value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _freeze_evidence(evidence: Mapping[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise TypeError("evidence must be a mapping")
    frozen = dict(evidence)
    # Ensure deterministic, JSON-serializable evidence snapshot.
    canonical_audit_json(frozen)
    return frozen


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
