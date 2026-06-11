from __future__ import annotations

import json
from pathlib import Path

from runtime.cpt.schema import ALLOWED_CANONICAL_STATUS, CriticTransformationRecord


def append_transformation_record(record: CriticTransformationRecord, audit_path: Path) -> None:
    validated_record = _validate_record_for_audit(record)
    _validate_audit_path(audit_path)

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(validated_record.to_dict(), sort_keys=True, ensure_ascii=False)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _validate_record_for_audit(record: CriticTransformationRecord) -> CriticTransformationRecord:
    if not isinstance(record, CriticTransformationRecord):
        raise TypeError("record must be a CriticTransformationRecord")
    if record.canonical_status not in ALLOWED_CANONICAL_STATUS:
        raise ValueError("audit records must remain DRAFT or NOT_CANONICAL")
    return CriticTransformationRecord(**record.to_dict())


def _validate_audit_path(audit_path: Path) -> None:
    if not isinstance(audit_path, Path):
        raise TypeError("audit_path must be a pathlib.Path")
    if ".." in audit_path.parts:
        raise ValueError("audit_path must not contain parent-directory traversal")
    if audit_path.exists() and audit_path.is_dir():
        raise ValueError("audit_path must be a file path, not a directory")
