from __future__ import annotations

import json
from pathlib import Path

from runtime.cpt.schema import ALLOWED_CANONICAL_STATUS, CriticTransformationRecord


def append_transformation_record(record: CriticTransformationRecord, audit_path: Path) -> None:
    if not isinstance(record, CriticTransformationRecord):
        raise TypeError("record must be a CriticTransformationRecord")
    if record.canonical_status not in ALLOWED_CANONICAL_STATUS:
        raise ValueError("audit records must remain DRAFT or NOT_CANONICAL")
    if not isinstance(audit_path, Path):
        raise TypeError("audit_path must be a pathlib.Path")

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=False)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
