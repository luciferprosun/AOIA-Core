#!/usr/bin/env python3
"""Read-only duplicate/conflict scan for Python knowledge JSONL records."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[5]
PYTHON_ROOT = PROJECT_ROOT / "knowledge" / "languages" / "python"
OUTPUT_DIR = PYTHON_ROOT / "audits" / "duplicate_conflict_scan"
RESULTS_PATH = OUTPUT_DIR / "H21_DUPLICATE_CONFLICT_SCAN_RESULTS.json"
SUMMARY_PATH = OUTPUT_DIR / "H21_DUPLICATE_CONFLICT_SCAN_SUMMARY.md"

DANGEROUS_TERMS = {
    "eval",
    "exec",
    "compile",
    "importlib.import_module",
    "__import__",
    "open",
    "input",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "pickle.load",
    "pickle.loads",
    "subprocess.run",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "pathlib.path.unlink",
    "tempfile.mktemp",
}

RISK_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records, scanned_paths, templates_skipped = collect_records()
    report = build_report(records, scanned_paths, templates_skipped)
    RESULTS_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(report), encoding="utf-8")
    print(f"H21 duplicate/conflict scan complete: {report['total_records']} records")
    print(f"Results: {RESULTS_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


def collect_records() -> tuple[list[dict[str, Any]], list[Path], int]:
    paths = find_jsonl_paths()
    records: list[dict[str, Any]] = []
    templates_skipped = 0
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if is_template_record(record):
                templates_skipped += 1
                continue
            record["_path"] = str(path.relative_to(PROJECT_ROOT))
            record["_line"] = line_number
            records.append(record)
    return records, paths, templates_skipped


def find_jsonl_paths() -> list[Path]:
    candidates: list[Path] = []
    explicit = [PYTHON_ROOT / "examples.jsonl"]
    for path in explicit:
        if path.exists():
            candidates.append(path)
    for pattern in (
        "reference/*.jsonl",
        "advisory/**/*.jsonl",
        "official_docs_crosscheck/**/*.jsonl",
    ):
        candidates.extend(PYTHON_ROOT.glob(pattern))
    return sorted({path.resolve() for path in candidates})


def is_template_record(record: dict[str, Any]) -> bool:
    return (
        record.get("status") == "template_only"
        or record.get("review_status") == "template_only"
        or str(record.get("id", "")).startswith("template_")
        or "template_discrepancy" in str(record.get("id", ""))
    )


def build_report(records: list[dict[str, Any]], scanned_paths: list[Path], templates_skipped: int) -> dict[str, Any]:
    duplicate_ids = duplicates(records, lambda record: str(record.get("id", "")))
    duplicate_terms = duplicates(records, term_key)
    duplicate_titles = duplicates(records, lambda record: normalize_text(str(record.get("title", ""))))
    duplicate_unsafe = duplicates(
        records,
        lambda record: normalize_code(str(record.get("unsafe_or_wrong_pattern", ""))),
    )
    duplicate_corrected = duplicates(
        records,
        lambda record: normalize_code(str(record.get("corrected_pattern", ""))),
    )

    review_conflicts = field_conflicts(records, ("id", "term"), "review_status")
    promotion_conflicts = field_conflicts(records, ("id", "term"), "promotion_status")
    execution_conflicts = field_conflicts(records, ("id", "term"), "execution_policy")
    status_conflicts = review_conflicts + promotion_conflicts
    policy_conflicts = execution_conflicts

    dangerous_low_risk_records = [summary(record) for record in records if is_dangerous_low_risk(record)]
    premature_promotions = [
        summary(record)
        for record in records
        if record.get("review_status") == "promoted" or record.get("promotion_status") == "promoted_to_advisory"
    ]
    official_docs_checked_without_gate = [
        summary(record)
        for record in records
        if record.get("review_status") == "official_docs_checked"
    ]
    safe_to_execute_records = [
        summary(record)
        for record in records
        if record.get("execution_policy") == "safe_to_execute_in_test_sandbox"
    ]
    missing_source_refs = [summary(record) for record in records if expects_source_ref(record) and not record.get("source_ref")]

    return {
        "scanned_files": len(scanned_paths),
        "scanned_file_paths": [str(path.relative_to(PROJECT_ROOT)) for path in scanned_paths],
        "total_records": len(records),
        "templates_skipped": templates_skipped,
        "duplicate_ids": duplicate_ids,
        "duplicate_terms": duplicate_terms,
        "duplicate_titles": duplicate_titles,
        "duplicate_unsafe_patterns": duplicate_unsafe,
        "duplicate_corrected_patterns": duplicate_corrected,
        "status_conflicts": status_conflicts,
        "policy_conflicts": policy_conflicts,
        "dangerous_low_risk_records": dangerous_low_risk_records,
        "premature_promotions": premature_promotions,
        "official_docs_checked_without_gate": official_docs_checked_without_gate,
        "safe_to_execute_records": safe_to_execute_records,
        "missing_source_refs": missing_source_refs,
    }


def duplicates(records: list[dict[str, Any]], key_func) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = key_func(record)
        if key:
            grouped[key].append(record)
    return [
        {"key": key, "records": [summary(record) for record in values]}
        for key, values in sorted(grouped.items())
        if len(values) > 1
    ]


def term_key(record: dict[str, Any]) -> str:
    term = normalize_text(str(record.get("term", "")))
    if not term:
        return ""
    scope = normalize_text(
        str(
            record.get("domain")
            or record.get("category")
            or record.get("target_doc_category")
            or record.get("subdomain")
            or "unknown"
        )
    )
    return f"{scope}:{term}"


def field_conflicts(records: list[dict[str, Any]], identity_fields: tuple[str, ...], field: str) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for identity_field in identity_fields:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            identity = normalize_text(str(record.get(identity_field, "")))
            if identity and field in record:
                grouped[f"{identity_field}:{identity}"].append(record)
        for identity, values in sorted(grouped.items()):
            observed = sorted({str(record.get(field)) for record in values if field in record})
            if len(observed) > 1:
                conflicts.append(
                    {
                        "identity": identity,
                        "field": field,
                        "values": observed,
                        "records": [summary(record) for record in values],
                    }
                )
    return conflicts


def is_dangerous_low_risk(record: dict[str, Any]) -> bool:
    if "risk_level" not in record:
        return False
    risk = str(record.get("risk_level", "low"))
    if RISK_ORDER.get(risk, 0) >= RISK_ORDER["high"]:
        return False
    text = " ".join(
        str(record.get(field, "")).lower()
        for field in ("id", "title", "term", "unsafe_or_wrong_pattern", "corrected_pattern", "safety_notes")
    )
    return any(term in text for term in DANGEROUS_TERMS)


def expects_source_ref(record: dict[str, Any]) -> bool:
    path = str(record.get("_path", ""))
    if "official_docs_crosscheck/" in path:
        return False
    return (
        path.endswith(".jsonl")
        and (
            "/reference/" in path
            or "/advisory/" in path
            or path.endswith("knowledge/languages/python/examples.jsonl")
        )
        and "source_ref" in record
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_code(value: str) -> str:
    normalized = normalize_text(value)
    normalized = normalized.replace('"', "").replace("'", "").replace("`", "")
    normalized = re.sub(r"\s*([(),.=:\[\]{}])\s*", r"\1", normalized)
    return normalized


def summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "term": record.get("term"),
        "title": record.get("title"),
        "review_status": record.get("review_status"),
        "promotion_status": record.get("promotion_status"),
        "execution_policy": record.get("execution_policy"),
        "risk_level": record.get("risk_level"),
        "path": record.get("_path"),
        "line": record.get("_line"),
    }


def render_summary(report: dict[str, Any]) -> str:
    lines = [
        "# H21 Duplicate Conflict Scan Summary",
        "",
        "This scan is read-only. It does not merge, delete, promote, or execute records.",
        "",
        "## Counts",
        f"- scanned_files: {report['scanned_files']}",
        f"- total_records: {report['total_records']}",
        f"- templates_skipped: {report['templates_skipped']}",
        f"- duplicate_ids: {len(report['duplicate_ids'])}",
        f"- duplicate_terms: {len(report['duplicate_terms'])}",
        f"- duplicate_titles: {len(report['duplicate_titles'])}",
        f"- duplicate_unsafe_patterns: {len(report['duplicate_unsafe_patterns'])}",
        f"- duplicate_corrected_patterns: {len(report['duplicate_corrected_patterns'])}",
        f"- status_conflicts: {len(report['status_conflicts'])}",
        f"- policy_conflicts: {len(report['policy_conflicts'])}",
        f"- dangerous_low_risk_records: {len(report['dangerous_low_risk_records'])}",
        f"- premature_promotions: {len(report['premature_promotions'])}",
        f"- official_docs_checked_without_gate: {len(report['official_docs_checked_without_gate'])}",
        f"- safe_to_execute_records: {len(report['safe_to_execute_records'])}",
        f"- missing_source_refs: {len(report['missing_source_refs'])}",
        "",
        "## Notes",
        "- Findings are audit results, not automatic failures.",
        "- Template-only discrepancy records are skipped.",
        "- Examples and corrected patterns are treated as inert strings only.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
