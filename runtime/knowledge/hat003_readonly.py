"""Read-only status and validation helpers for Hat 003 draft artifacts."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HAT003_RELATIVE_ROOT = Path("knowledge") / "hats" / "hat_003_python"

MACHINE_READABLE_FILES = {
    "source_atlas": Path("machine_readable") / "source_atlas.json",
    "knowledge_cards_thinned": Path("machine_readable") / "knowledge_cards_thinned_draft.jsonl",
    "knowledge_card_quarantine_index": Path("machine_readable") / "knowledge_card_quarantine_index.json",
    "validation_rules_normalized": Path("machine_readable") / "validation_rules_normalized_draft.json",
    "corpus_cases_normalized": Path("machine_readable") / "corpus_cases_normalized_draft.json",
    "retrieval_index": Path("machine_readable") / "retrieval_index_draft.json",
}

SCHEMA_FILES = (
    "knowledge_card.schema.json",
    "validation_rule.schema.json",
    "corpus_case.schema.json",
    "source_atlas_entry.schema.json",
    "retrieval_index_entry.schema.json",
)

AUDIT_REPORTS = (
    "H3_A_INVENTORY_QUARANTINE_AUDIT.md",
    "H3_B_SCHEMA_NORMALIZATION_REPORT.md",
    "H3_C_SOURCE_ATLAS_HARDENING_REPORT.md",
    "H3_D_CARD_THINNING_QUARANTINE_REPORT.md",
    "H3_E_VALIDATION_RULE_NORMALIZATION_REPORT.md",
    "H3_F_CORPUS_CASE_NORMALIZATION_REPORT.md",
    "H3_G_RETRIEVAL_INDEX_REBUILD_REPORT.md",
    "H3_H_REVIEWER_READY_CLOSURE_REPORT.md",
)


@dataclass(frozen=True)
class Hat003ValidationReport:
    ok: bool
    status: dict[str, Any] | None
    problems: tuple[str, ...]


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def hat003_root(project_root: Path | None = None) -> Path:
    root = default_project_root() if project_root is None else Path(project_root)
    return root / HAT003_RELATIVE_ROOT


def load_hat003_status(project_root: Path | None = None) -> dict[str, Any]:
    root = hat003_root(project_root)
    artifacts = _load_artifacts(root)
    counts = {
        "source_atlas": len(artifacts["source_atlas"]),
        "knowledge_cards_thinned": len(artifacts["knowledge_cards_thinned"]),
        "knowledge_card_quarantine_index": len(artifacts["knowledge_card_quarantine_index"]["cards"]),
        "validation_rules_normalized": len(artifacts["validation_rules_normalized"]["records"]),
        "corpus_cases_normalized": len(artifacts["corpus_cases_normalized"]["records"]),
        "retrieval_index": len(artifacts["retrieval_index"]),
    }
    retrieval_kind_counts = dict(
        sorted(Counter(entry.get("kind", "") for entry in artifacts["retrieval_index"]).items())
    )
    return {
        "hat_id": "hat_003_python",
        "status": "DRAFT",
        "canonical": False,
        "source_verification_status": "UNVERIFIED",
        "execution_permitted": False,
        "human_review_required": True,
        "read_only": True,
        "runtime_integration": "loader_status_validator_only",
        "runtime_routing_enabled": False,
        "root": str(root),
        "counts": counts,
        "retrieval_kind_counts": retrieval_kind_counts,
        "schema_files": list(SCHEMA_FILES),
        "audit_reports": list(AUDIT_REPORTS),
    }


def validate_hat003_read_only(project_root: Path | None = None) -> Hat003ValidationReport:
    root = hat003_root(project_root)
    problems: list[str] = []

    for relative_path in MACHINE_READABLE_FILES.values():
        _require_file(root / relative_path, problems)
    for filename in SCHEMA_FILES:
        _require_file(root / "schemas" / filename, problems)
    for filename in AUDIT_REPORTS:
        _require_file(root / "audits" / filename, problems)

    try:
        artifacts = _load_artifacts(root)
        status = load_hat003_status(project_root)
    except (KeyError, OSError, json.JSONDecodeError, TypeError) as exc:
        problems.append(f"failed to load Hat 003 artifacts: {exc}")
        return Hat003ValidationReport(False, None, tuple(problems))

    _validate_counts(status, problems)
    _validate_governance(
        "knowledge_cards_thinned",
        artifacts["knowledge_cards_thinned"],
        problems,
    )
    _validate_governance(
        "validation_rules_normalized",
        [record["governance"] for record in artifacts["validation_rules_normalized"]["records"]],
        problems,
    )
    _validate_governance(
        "corpus_cases_normalized",
        [record["governance"] for record in artifacts["corpus_cases_normalized"]["records"]],
        problems,
    )
    _validate_governance("source_atlas", artifacts["source_atlas"], problems)
    _validate_governance("retrieval_index", artifacts["retrieval_index"], problems)
    _validate_retrieval_index(artifacts["retrieval_index"], problems)

    return Hat003ValidationReport(not problems, status, tuple(problems))


def _load_artifacts(root: Path) -> dict[str, Any]:
    return {
        "source_atlas": _load_json(root / MACHINE_READABLE_FILES["source_atlas"]),
        "knowledge_cards_thinned": _load_jsonl(root / MACHINE_READABLE_FILES["knowledge_cards_thinned"]),
        "knowledge_card_quarantine_index": _load_json(
            root / MACHINE_READABLE_FILES["knowledge_card_quarantine_index"]
        ),
        "validation_rules_normalized": _load_json(
            root / MACHINE_READABLE_FILES["validation_rules_normalized"]
        ),
        "corpus_cases_normalized": _load_json(root / MACHINE_READABLE_FILES["corpus_cases_normalized"]),
        "retrieval_index": _load_json(root / MACHINE_READABLE_FILES["retrieval_index"]),
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Any]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _require_file(path: Path, problems: list[str]) -> None:
    if not path.is_file():
        problems.append(f"missing required file: {path}")


def _validate_counts(status: dict[str, Any], problems: list[str]) -> None:
    counts = status["counts"]
    if counts["knowledge_card_quarantine_index"] != counts["knowledge_cards_thinned"]:
        problems.append("quarantine card count does not match thinned card count")

    retrieval_total = sum(status["retrieval_kind_counts"].values())
    if retrieval_total != counts["retrieval_index"]:
        problems.append("retrieval kind counts do not match retrieval index count")

    source_total = (
        counts["knowledge_cards_thinned"]
        + counts["validation_rules_normalized"]
        + counts["corpus_cases_normalized"]
        + counts["source_atlas"]
    )
    if source_total != counts["retrieval_index"]:
        problems.append("retrieval index count does not match source artifact total")


def _validate_governance(name: str, records: list[dict[str, Any]], problems: list[str]) -> None:
    for index, record in enumerate(records):
        label = record.get("id") or record.get("card_id") or record.get("rule_id") or record.get("case_id")
        label = label or record.get("source_id") or f"{name}[{index}]"
        if record.get("status") != "DRAFT":
            problems.append(f"{label}: status is not DRAFT")
        if record.get("canonical") is not False:
            problems.append(f"{label}: canonical flag is not false")
        if record.get("source_verification_status") != "UNVERIFIED":
            problems.append(f"{label}: source verification status is not UNVERIFIED")
        if record.get("execution_permitted") is not False:
            problems.append(f"{label}: execution permission is not false")
        if record.get("human_review_required") is not True:
            problems.append(f"{label}: human review requirement is not true")


def _validate_retrieval_index(records: list[dict[str, Any]], problems: list[str]) -> None:
    seen_ids: set[str] = set()
    allowed_kinds = {"knowledge_card", "validation_rule", "corpus_case", "source_atlas_entry"}
    required_fields = {
        "id",
        "kind",
        "title",
        "text",
        "status",
        "canonical",
        "source_verification_status",
        "card_deepening_status",
        "execution_permitted",
        "human_review_required",
    }
    for record in records:
        record_id = str(record.get("id", ""))
        if set(record) != required_fields:
            problems.append(f"{record_id}: retrieval entry field set changed")
        if record_id in seen_ids:
            problems.append(f"{record_id}: duplicate retrieval id")
        seen_ids.add(record_id)
        if record.get("kind") not in allowed_kinds:
            problems.append(f"{record_id}: unsupported retrieval kind")
        if not str(record.get("title", "")).strip():
            problems.append(f"{record_id}: missing retrieval title")
        if not str(record.get("text", "")).strip():
            problems.append(f"{record_id}: missing retrieval text")
