"""Local JSONL serialization helpers for Memory Hats tags.

This module converts PheromoneTag records to and from JSONL text. It performs
no file I/O, storage access, network access, sync, command execution, or
runtime integration.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from runtime.memory_hats.tags import PheromoneTag, ReviewStatus, TagType


_SERIALIZED_FIELDS = (
    "fingerprint_hash",
    "hat_id",
    "path",
    "tag_type",
    "normalized_trigger",
    "correction_text",
    "evidence_refs",
    "review_status",
    "seen_count",
    "hat_version",
    "created_by",
    "first_seen",
    "last_seen",
    "notes",
)

EnumT = TypeVar("EnumT", TagType, ReviewStatus)


def tag_to_jsonl_record(tag: PheromoneTag) -> dict[str, Any]:
    """Convert a tag into a JSON-compatible dictionary without mutation."""
    if not isinstance(tag, PheromoneTag):
        raise TypeError("tag must be a PheromoneTag")

    return {
        "fingerprint_hash": tag.fingerprint_hash,
        "hat_id": tag.hat_id,
        "path": tag.path,
        "tag_type": tag.tag_type.value,
        "normalized_trigger": tag.normalized_trigger,
        "correction_text": tag.correction_text,
        "evidence_refs": list(tag.evidence_refs),
        "review_status": tag.review_status.value,
        "seen_count": tag.seen_count,
        "hat_version": tag.hat_version,
        "created_by": tag.created_by,
        "first_seen": tag.first_seen,
        "last_seen": tag.last_seen,
        "notes": tag.notes,
    }


def tag_from_jsonl_record(record: dict[str, Any]) -> PheromoneTag:
    """Convert a JSONL record dictionary into a PheromoneTag."""
    if not isinstance(record, dict):
        raise TypeError("record must be a dictionary")

    missing = [field for field in _SERIALIZED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"missing required field(s): {', '.join(missing)}")

    evidence_refs = record["evidence_refs"]
    if not isinstance(evidence_refs, list):
        raise ValueError("evidence_refs must be a list")

    return PheromoneTag(
        fingerprint_hash=record["fingerprint_hash"],
        hat_id=record["hat_id"],
        path=record["path"],
        tag_type=_coerce_enum(TagType, record["tag_type"], "tag_type"),
        normalized_trigger=record["normalized_trigger"],
        correction_text=record["correction_text"],
        evidence_refs=list(evidence_refs),
        review_status=_coerce_enum(
            ReviewStatus,
            record["review_status"],
            "review_status",
        ),
        seen_count=record["seen_count"],
        hat_version=record["hat_version"],
        created_by=record["created_by"],
        first_seen=record["first_seen"],
        last_seen=record["last_seen"],
        notes=record["notes"],
    )


def export_tags_to_jsonl(tags: list[PheromoneTag]) -> str:
    """Serialize tags to JSONL text while preserving input order."""
    if not isinstance(tags, list):
        raise TypeError("tags must be a list")

    lines = [
        json.dumps(tag_to_jsonl_record(tag), sort_keys=True, separators=(",", ":"))
        for tag in tags
    ]
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def import_tags_from_jsonl(text: str) -> list[PheromoneTag]:
    """Parse JSONL text into tags, ignoring blank lines."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    tags: list[PheromoneTag] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL on line {line_number}") from exc
        try:
            tags.append(tag_from_jsonl_record(record))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid tag record on line {line_number}: {exc}") from exc
    return tags


def _coerce_enum(
    enum_type: type[EnumT],
    value: Any,
    field_name: str,
) -> EnumT:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            try:
                return enum_type[value]
            except KeyError as exc:
                raise ValueError(f"invalid {field_name}: {value}") from exc
    raise ValueError(f"invalid {field_name}: {value}")
