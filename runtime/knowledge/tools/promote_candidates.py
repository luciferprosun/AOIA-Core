from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_INDEX = PROJECT_ROOT / "knowledge" / "candidates" / "candidate_command_index.json"
SCHEMA_PATH = PROJECT_ROOT / "knowledge" / "schema" / "command.schema.json"
OUTPUT_DIR = PROJECT_ROOT / "knowledge" / "candidates"
REPORT_PATH = PROJECT_ROOT / "knowledge" / "reports" / "promotion_triage_report.md"

ACCEPT_PATH = OUTPUT_DIR / "reviewed_promotions.json"
REVIEW_PATH = OUTPUT_DIR / "review_queue.json"
REJECT_PATH = OUTPUT_DIR / "rejected_candidates.json"

REJECT_FLAGS = {
    "path_not_command",
    "probable_pdf_merge_artifact",
    "invalid_base_command",
    "likely_contamination_or_comment",
}
REVIEW_FLAGS = {
    "weak_description",
    "complex_pipeline_or_snippet",
}
REJECT_STATUSES = {"malformed", "unresolved"}
GEMINI_SOURCE = "GEMINI_EXPANSION"
CANONICAL_SOURCE_PREFIX = "runtime/knowledge/source/"
SUSPICIOUS_FORMAT_RE = re.compile(r"[“”‘’]|`{2,}|^[\"']")
MULTI_COMMAND_RE = re.compile(r"\s(\|\||&&|;|\|)\s|[`$][({]?|>>?|<")
BASE_COMMAND_RE = re.compile(r"^[A-Za-z0-9._+-]+$")

CATEGORY_MAP = {
    "Automation": "system",
    "Bash": "system",
    "File Management": "filesystem",
    "Logs": "diagnostic",
    "Networking": "network",
    "Packages": "package",
    "Processes": "process",
    "RHCSA Exam Tasks": "system",
    "SSH": "network",
    "Security": "security",
    "Storage": "filesystem",
    "Systemd": "service",
    "Users & Permissions": "user",
}


@dataclass(frozen=True)
class TriageResult:
    status: str
    reasons: tuple[str, ...]
    schema_valid: bool
    schema_errors: tuple[str, ...]
    provenance_status: str
    projected_schema_record: dict[str, Any] | None


def load_candidates(path: Path = CANDIDATE_INDEX) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("candidate_command_index.json does not contain a records list")
    return payload, records


def triage_record(record: dict[str, Any], schema: dict[str, Any] | None = None) -> TriageResult:
    reasons: list[str] = []
    command = str(record.get("command", "")).strip()
    description = str(record.get("description", "")).strip()
    status = str(record.get("status", "")).strip()
    category = str(record.get("category", "")).strip()
    quality_flags = _string_list(record.get("quality_flags", []))
    source_files = _string_list(record.get("source_files", []))

    if not command:
        reasons.append("empty_command")
    if status in REJECT_STATUSES:
        reasons.append(status)
    for flag in quality_flags:
        if flag in REJECT_FLAGS:
            reasons.append(flag)
    if _is_corrupted_provenance(record):
        reasons.append("corrupted_provenance")
    elif not str(record.get("canonical_source", "")).strip():
        reasons.append("missing_canonical_source")
    elif not str(record.get("canonical_source", "")).startswith(CANONICAL_SOURCE_PREFIX):
        reasons.append("partial_provenance")
    if GEMINI_SOURCE in source_files or category == "Gemini Expansion Additions":
        reasons.append("gemini_expansion_addition")
    if not _has_source_line(record):
        reasons.append("partial_provenance")
    if not _has_source_page(record):
        reasons.append("missing_source_page")
    if any(flag in REVIEW_FLAGS for flag in quality_flags):
        reasons.extend(flag for flag in quality_flags if flag in REVIEW_FLAGS)
    if _duplicate_ambiguous(record):
        reasons.append("duplicate_ambiguity")
    if _multi_command_ambiguous(command):
        reasons.append("multi_command_ambiguity")
    if _suspicious_format(command):
        reasons.append("suspicious_formatting")
    if not _valid_command_syntax(command):
        reasons.append("suspicious_formatting")
    if _weak_description(description):
        reasons.append("weak_description")

    projected = project_to_schema(record)
    schema_errors = tuple(validate_projected_schema(projected, schema))
    schema_valid = not schema_errors
    if schema_errors:
        reasons.append("schema_invalid")

    unique_reasons = tuple(dict.fromkeys(reasons))
    reject_reasons = {
        "malformed",
        "unresolved",
        "path_not_command",
        "probable_pdf_merge_artifact",
        "invalid_base_command",
        "likely_contamination_or_comment",
        "empty_command",
        "corrupted_provenance",
        "missing_canonical_source",
    }
    review_reasons = {
        "weak_description",
        "complex_pipeline_or_snippet",
        "uncertain_alias_mapping",
        "duplicate_ambiguity",
        "missing_source_page",
        "gemini_expansion_addition",
        "partial_provenance",
        "suspicious_formatting",
        "multi_command_ambiguity",
        "schema_invalid",
    }

    if any(reason in reject_reasons for reason in unique_reasons):
        triage_status = "REJECT"
    elif any(reason in review_reasons for reason in unique_reasons):
        triage_status = "REVIEW"
    else:
        triage_status = "ACCEPT"

    if triage_status == "ACCEPT" and (
        not schema_valid
        or not _has_source_line(record)
        or not _has_source_page(record)
        or not str(record.get("canonical_source", "")).strip()
        or quality_flags
        or status != "candidate"
    ):
        triage_status = "REVIEW"
        unique_reasons = tuple(dict.fromkeys((*unique_reasons, "accept_safety_downgrade")))

    return TriageResult(
        status=triage_status,
        reasons=unique_reasons,
        schema_valid=schema_valid,
        schema_errors=schema_errors,
        provenance_status=_provenance_status(record),
        projected_schema_record=projected if schema_valid else None,
    )


def project_to_schema(record: dict[str, Any]) -> dict[str, Any]:
    command = str(record.get("command", "")).strip()
    base_command = str(record.get("base_command", "")).strip() or command.split()[0] if command else ""
    category = CATEGORY_MAP.get(str(record.get("category", "")).strip(), "system")
    examples = record.get("examples", [])
    if not isinstance(examples, list):
        examples = []
    projected_examples = [
        {
            "input": str(example).strip(),
            "expected_effect": str(record.get("description", "")).strip()[:240] or "Candidate command example.",
        }
        for example in examples
        if str(example).strip()
    ]
    tags = [category, _slug(base_command)]
    source_tags = [_slug(item) for item in _string_list(record.get("source_files", [])) if item]
    tags.extend(source_tags[:3])
    return {
        "id": _slug(command)[:80].strip("-") or "invalid",
        "command": command,
        "description": str(record.get("description", "")).strip()[:240],
        "category": category,
        "tags": _unique([tag for tag in tags if tag]),
        "risk": _risk_for(command),
        "os": ["linux", "rhel"],
        "shell": ["bash"],
        "examples": projected_examples,
        "notes": f"Candidate status: {record.get('status', '')}; source_line: {record.get('source_line', '')}",
        "related_commands": _unique([base_command]) if base_command else [],
    }


def validate_projected_schema(projected: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    required = schema.get("required", [])
    for key in required:
        if key not in projected:
            errors.append(f"missing_required:{key}")
    if not re.match(schema["properties"]["id"]["pattern"], projected.get("id", "")):
        errors.append("invalid_id")
    if not projected.get("command"):
        errors.append("invalid_command")
    description = projected.get("description", "")
    if not description or len(description) > 240:
        errors.append("invalid_description")
    if projected.get("category") not in schema["properties"]["category"]["enum"]:
        errors.append("invalid_category")
    if projected.get("risk") not in schema["properties"]["risk"]["enum"]:
        errors.append("invalid_risk")
    if not _valid_enum_list(projected.get("os"), schema["properties"]["os"]["items"]["enum"]):
        errors.append("invalid_os")
    if not _valid_enum_list(projected.get("shell"), schema["properties"]["shell"]["items"]["enum"]):
        errors.append("invalid_shell")
    tags = projected.get("tags", [])
    if not isinstance(tags, list) or not tags:
        errors.append("invalid_tags")
    else:
        for tag in tags:
            if not re.match(schema["properties"]["tags"]["items"]["pattern"], str(tag)):
                errors.append("invalid_tag")
                break
    examples = projected.get("examples", [])
    if not isinstance(examples, list) or not examples:
        errors.append("invalid_examples")
    else:
        for example in examples:
            if not isinstance(example, dict) or not example.get("input") or not example.get("expected_effect"):
                errors.append("invalid_example")
                break
    return errors


def triage_all(records: list[dict[str, Any]], schema: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    buckets = {"ACCEPT": [], "REVIEW": [], "REJECT": []}
    for index, record in enumerate(records):
        result = triage_record(record, schema)
        enriched = {
            "triage_status": result.status,
            "triage_reasons": list(result.reasons),
            "schema_valid": result.schema_valid,
            "schema_errors": list(result.schema_errors),
            "provenance_status": result.provenance_status,
            "projected_schema_record": result.projected_schema_record,
            "original_record": record,
            "status_history": [
                {
                    "stage": "candidate_loader",
                    "status": record.get("status", ""),
                    "quality_flags": record.get("quality_flags", []),
                },
                {
                    "stage": "candidate_triage_v1",
                    "status": result.status,
                    "reasons": list(result.reasons),
                },
            ],
            "triage_index": index,
        }
        buckets[result.status].append(enriched)
    return buckets


def write_outputs(buckets: dict[str, list[dict[str, Any]]], source_payload: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": "1.0",
        "triage": "candidate_promotion_triage_v1",
        "source": source_payload.get("source", ""),
        "canonical_source": source_payload.get("canonical_source", ""),
        "promotion_status": "triage_only_no_canonical_writes",
    }
    _write_json(ACCEPT_PATH, {**metadata, "records": buckets["ACCEPT"]})
    _write_json(REVIEW_PATH, {**metadata, "records": buckets["REVIEW"]})
    _write_json(REJECT_PATH, {**metadata, "records": buckets["REJECT"]})


def build_report(buckets: dict[str, list[dict[str, Any]]], records: list[dict[str, Any]]) -> str:
    all_triaged = buckets["ACCEPT"] + buckets["REVIEW"] + buckets["REJECT"]
    reason_counts = Counter(reason for item in all_triaged for reason in item["triage_reasons"])
    reject_reason_counts = Counter(reason for item in buckets["REJECT"] for reason in item["triage_reasons"])
    gemini_count = sum(1 for item in all_triaged if "gemini_expansion_addition" in item["triage_reasons"])
    unresolved_provenance = sum(
        1 for item in all_triaged
        if item["provenance_status"] != "complete"
    )
    schema_invalid = sum(1 for item in all_triaged if not item["schema_valid"])
    lines = [
        "# Candidate Promotion Triage Report",
        "",
        "This report is triage-only. No canonical index files were modified.",
        "",
        "## Summary",
        "",
        f"- Total candidates processed: {len(records)}",
        f"- ACCEPT: {len(buckets['ACCEPT'])}",
        f"- REVIEW: {len(buckets['REVIEW'])}",
        f"- REJECT: {len(buckets['REJECT'])}",
        f"- Gemini additions isolated: {gemini_count}",
        f"- Unresolved provenance count: {unresolved_provenance}",
        f"- Schema-invalid projected records: {schema_invalid}",
        "",
        "## Contamination Reasons",
        "",
    ]
    contamination = {
        reason: reason_counts.get(reason, 0)
        for reason in (
            "path_not_command",
            "probable_pdf_merge_artifact",
            "invalid_base_command",
            "likely_contamination_or_comment",
            "suspicious_formatting",
            "multi_command_ambiguity",
            "gemini_expansion_addition",
        )
    }
    lines.extend(f"- {reason}: {count}" for reason, count in contamination.items())
    lines.extend(["", "## Most Common Rejection Reasons", ""])
    for reason, count in reject_reason_counts.most_common(12):
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Schema Validation Summary", ""])
    lines.append("Candidate records were projected into `command.schema.json` shape for validation.")
    lines.append("Broken records were not silently repaired; schema failures stayed in REVIEW or REJECT.")
    lines.extend(["", "## Recommended Manual Review Priorities", ""])
    lines.extend(
        [
            "1. Review `review_queue.json` entries with `gemini_expansion_addition` first; do not auto-promote.",
            "2. Review duplicate ambiguity against canonical/index records before accepting.",
            "3. Review weak descriptions and missing source pages against the canonical PDF.",
            "4. Reject or rewrite suspicious snippets only after independent source verification.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_triage(
    candidate_path: Path = CANDIDATE_INDEX,
    schema_path: Path = SCHEMA_PATH,
    write: bool = True,
) -> dict[str, Any]:
    source_payload, records = load_candidates(candidate_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    buckets = triage_all(records, schema)
    if write:
        write_outputs(buckets, source_payload)
        REPORT_PATH.write_text(build_report(buckets, records), encoding="utf-8")
    return {
        "processed": len(records),
        "accept": len(buckets["ACCEPT"]),
        "review": len(buckets["REVIEW"]),
        "reject": len(buckets["REJECT"]),
        "gemini_isolated": sum(
            1
            for item in buckets["ACCEPT"] + buckets["REVIEW"] + buckets["REJECT"]
            if "gemini_expansion_addition" in item["triage_reasons"]
        ),
        "buckets": buckets,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _has_source_line(record: dict[str, Any]) -> bool:
    return isinstance(record.get("source_line"), int) and record["source_line"] > 0


def _has_source_page(record: dict[str, Any]) -> bool:
    return isinstance(record.get("source_page"), int) and record["source_page"] > 0


def _is_corrupted_provenance(record: dict[str, Any]) -> bool:
    return "canonical_source" in record and not isinstance(record.get("canonical_source"), str)


def _provenance_status(record: dict[str, Any]) -> str:
    if _is_corrupted_provenance(record) or not str(record.get("canonical_source", "")).strip():
        return "missing_or_corrupt"
    if _has_source_line(record) and _has_source_page(record):
        return "complete"
    return "partial"


def _duplicate_ambiguous(record: dict[str, Any]) -> bool:
    duplicate_type = str(record.get("duplicate_type", "")).strip()
    status = str(record.get("status", "")).strip()
    return bool(duplicate_type) or status == "duplicate_existing"


def _multi_command_ambiguous(command: str) -> bool:
    return bool(MULTI_COMMAND_RE.search(command))


def _suspicious_format(command: str) -> bool:
    return bool(SUSPICIOUS_FORMAT_RE.search(command))


def _valid_command_syntax(command: str) -> bool:
    if not command:
        return False
    if command.startswith("/"):
        return False
    if any(char in command for char in ("\n", "\r", "\x00")):
        return False
    base = command.split()[0]
    return bool(BASE_COMMAND_RE.match(base))


def _weak_description(description: str) -> bool:
    normalized = description.strip().lower()
    return len(normalized) < 8 or normalized in {"sekcja komend", "safe", "caution", "command"}


def _risk_for(command: str) -> str:
    lowered = command.lower()
    if "rm -rf" in lowered or "mkfs" in lowered or "wipefs" in lowered:
        return "critical"
    if any(token in lowered for token in (" delete", " remove", "lvreduce", "dd ")):
        return "high"
    return "medium"


def _valid_enum_list(value: Any, allowed: list[str]) -> bool:
    return isinstance(value, list) and bool(value) and all(item in allowed for item in value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage candidate Linux command records without canonical promotion.")
    parser.add_argument("--candidate-index", type=Path, default=CANDIDATE_INDEX)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    args = parser.parse_args()
    result = run_triage(args.candidate_index, args.schema, write=True)
    print(
        "Processed {processed} candidates: ACCEPT={accept}, REVIEW={review}, REJECT={reject}, Gemini isolated={gemini_isolated}".format(
            **result
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
