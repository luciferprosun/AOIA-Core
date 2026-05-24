#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, OrderedDict, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
SOURCE_TEXT = KNOWLEDGE_ROOT / "extracted" / "linux_master_library_v1.txt"
CANONICAL_JSON = KNOWLEDGE_ROOT / "canonical" / "rhcsa_commands.json"
COMMAND_INDEX_JSON = KNOWLEDGE_ROOT / "index" / "command_index.json"
CANDIDATES_DIR = KNOWLEDGE_ROOT / "candidates"
REPORTS_DIR = KNOWLEDGE_ROOT / "reports"
CANDIDATE_JSON = CANDIDATES_DIR / "candidate_command_index.json"
CANDIDATE_CSV = CANDIDATES_DIR / "candidate_commands.csv"
DEDUP_REPORT = REPORTS_DIR / "deduplication_report.md"
QUALITY_REPORT = REPORTS_DIR / "parsing_quality_report.md"
CATEGORY_REPORT = REPORTS_DIR / "category_distribution.md"

CANONICAL_SOURCE = "runtime/knowledge/source/linux_master_library_v1.pdf"
ENTRY_RE = re.compile(r"^\s*(1\.(?:[4-9]|1[0-8])\.(\d+))\s+(.+?)\s*$")
SECTION_RE = re.compile(r"^\s*1\.(?:[4-9]|1[0-8])\s+([A-Z][A-Za-z &/]+)\s*$")
TOC_RE = re.compile(r"^\s*(1\.(?:[4-9]|1[0-8])\.(\d+))\s+(.+?)\s+(?:(?:\.\s*){3,})\s+(\d+)\s*$")

SECTION_BY_NUMBER = {
    "1.4": "File Management",
    "1.5": "Users & Permissions",
    "1.6": "Networking",
    "1.7": "Storage",
    "1.8": "Systemd",
    "1.9": "Processes",
    "1.10": "Bash",
    "1.11": "SSH",
    "1.12": "Logs",
    "1.13": "Security",
    "1.14": "Packages",
    "1.15": "Automation",
    "1.16": "RHCSA Exam Tasks",
    "1.17": "Sources",
    "1.18": "Gemini Expansion Additions",
}

NOISE_PHRASES = {
    "aoia",
    "do not",
    "kernel logic",
    "memory.py",
    "planner systems",
    "runtime",
    "without symlink",
    "bypassing",
    "when $var unset",
}


@dataclass(frozen=True)
class CandidateRecord:
    command: str
    command_key: str
    base_command: str
    category: str
    description: str
    examples: list[str]
    source_line: int
    source_page: int | None
    canonical_source: str
    source_files: list[str]
    status: str
    duplicate_type: str
    duplicate_of: str
    quality_flags: list[str]
    confidence: str


def normalize_text(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9_+./$|<>*;:=-]+", " ", normalized).strip()


def normalize_command(value: str) -> str:
    value = value.replace("‘", "'").replace("’", "'").replace("`", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+\d+$", "", value).strip()
    return value


def command_key(command: str) -> str:
    command = normalize_command(command)
    if " " not in command:
        return command.lower()
    base, rest = command.split(" ", 1)
    return f"{base.lower()} {rest}"


def base_command(command: str) -> str:
    command = normalize_command(command)
    command = re.sub(r"^(sudo|time|watch|timeout)\s+", "", command)
    return command.split(" ", 1)[0].lower() if command else ""


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_existing_sets() -> tuple[set[str], set[str]]:
    canonical_payload = read_json(CANONICAL_JSON, [])
    canonical_keys: set[str] = set()
    if isinstance(canonical_payload, list):
        for item in canonical_payload:
            if isinstance(item, dict) and item.get("command"):
                canonical_keys.add(command_key(str(item["command"])))

    command_index_payload = read_json(COMMAND_INDEX_JSON, {})
    index_keys: set[str] = set()
    if isinstance(command_index_payload, dict):
        for key, values in command_index_payload.items():
            index_keys.add(command_key(str(key)))
            if isinstance(values, list):
                for value in values:
                    index_keys.add(command_key(str(value)))
    return canonical_keys, index_keys


def parse_toc_pages(lines: list[str]) -> dict[str, int]:
    pages: dict[str, int] = {}
    for line in lines:
        if line.strip().startswith("1       FINAL MASTER"):
            break
        match = TOC_RE.match(line.replace("\f", ""))
        if match:
            pages[match.group(1)] = int(match.group(4))
    return pages


def section_for_entry(entry_id: str, fallback: str) -> str:
    prefix = ".".join(entry_id.split(".")[:2])
    return SECTION_BY_NUMBER.get(prefix, fallback or "Unclassified")


def strip_toc_dots(text: str) -> str:
    text = re.sub(r"\s+\.{3,}.*$", "", text).strip()
    return normalize_command(text)


def is_source_line(line: str) -> bool:
    return line.strip().startswith("Sources:")


def parse_sources(line: str) -> list[str]:
    raw = line.split(":", 1)[1] if ":" in line else ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def is_probable_example(line: str, command: str) -> bool:
    text = line.strip()
    if not text or text.startswith("Sources:"):
        return False
    if text.startswith("•") or re.match(r"^\d+(\.\d+)*\s", text):
        return False
    if len(text) > 180:
        return False
    first = text.split()[0] if text.split() else ""
    return first == base_command(command) or text == command


def quality_flags(command: str, description: str) -> list[str]:
    flags: list[str] = []
    normalized = normalize_text(command)
    base = base_command(command)
    if not command:
        flags.append("empty_command")
    if not base or not re.match(r"^[a-z0-9_.$/{[(+-][a-z0-9_.$/{[(+-]*$", base):
        flags.append("invalid_base_command")
    if len(command) > 120:
        flags.append("too_long")
    if any(phrase in normalized for phrase in NOISE_PHRASES):
        flags.append("likely_contamination_or_comment")
    if command.count("|") > 2 or command.count(";") > 2:
        flags.append("complex_pipeline_or_snippet")
    if command.startswith(("/", "~")):
        flags.append("path_not_command")
    if description.lower() in {"sekcja komend", "dangerous mistakes"}:
        flags.append("weak_description")
    if re.search(r"\b(file|regularnego|kadej|grup|planner|logic)\b", normalized) and base in {"file", "touch", "type"}:
        flags.append("probable_pdf_merge_artifact")
    return list(dict.fromkeys(flags))


def confidence_for(flags: list[str], duplicate_type: str) -> str:
    severe = {"empty_command", "invalid_base_command", "path_not_command", "too_long"}
    if severe.intersection(flags):
        return "none"
    if "likely_contamination_or_comment" in flags or "probable_pdf_merge_artifact" in flags:
        return "low"
    if duplicate_type:
        return "high"
    if "weak_description" in flags or "complex_pipeline_or_snippet" in flags:
        return "medium"
    return "high"


def status_for(flags: list[str], duplicate_type: str) -> str:
    severe = {"empty_command", "invalid_base_command", "path_not_command", "too_long"}
    if severe.intersection(flags):
        return "malformed"
    if "likely_contamination_or_comment" in flags or "probable_pdf_merge_artifact" in flags:
        return "unresolved"
    if duplicate_type:
        return "duplicate_existing"
    return "candidate"


def parse_entries(lines: list[str], page_by_entry: dict[str, int]) -> list[dict[str, Any]]:
    body_start = 0
    for index, line in enumerate(lines):
        if line.strip().startswith("1       FINAL MASTER"):
            body_start = index
            break

    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_category = ""

    def flush() -> None:
        nonlocal current
        if current is not None:
            entries.append(current)
            current = None

    for source_line, raw in enumerate(lines[body_start:], start=body_start + 1):
        line = raw.replace("\f", "").rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        section_match = SECTION_RE.match(stripped)
        if section_match:
            current_category = section_match.group(1).strip()
            continue
        match = ENTRY_RE.match(stripped)
        if match:
            entry_id = match.group(1)
            command = strip_toc_dots(match.group(3))
            if command in SECTION_BY_NUMBER.values():
                continue
            flush()
            current = {
                "entry_id": entry_id,
                "command": command,
                "category": section_for_entry(entry_id, current_category),
                "description_lines": [],
                "examples": [],
                "sources": [],
                "source_line": source_line,
                "source_page": page_by_entry.get(entry_id),
            }
            continue
        if current is None:
            continue
        if is_source_line(stripped):
            current["sources"].extend(parse_sources(stripped))
            continue
        if is_probable_example(stripped, current["command"]):
            current["examples"].append(stripped)
        elif len(current["description_lines"]) < 3:
            current["description_lines"].append(stripped)

    flush()
    return entries


def build_candidates(raw_entries: list[dict[str, Any]], canonical_keys: set[str], index_keys: set[str]) -> list[CandidateRecord]:
    seen: OrderedDict[str, int] = OrderedDict()
    records: list[CandidateRecord] = []
    for entry in raw_entries:
        command = normalize_command(str(entry["command"]))
        key = command_key(command)
        base = base_command(command)
        duplicate_types: list[str] = []
        duplicate_of = ""
        if key in canonical_keys:
            duplicate_types.append("canonical")
            duplicate_of = command
        if key in index_keys:
            duplicate_types.append("command_index")
            duplicate_of = duplicate_of or command
        if key in seen:
            duplicate_types.append("candidate_internal")
            duplicate_of = duplicate_of or records[seen[key]].command

        description = " ".join(str(item).strip() for item in entry["description_lines"] if str(item).strip())
        flags = quality_flags(command, description)
        duplicate_type = "+".join(duplicate_types)
        status = status_for(flags, duplicate_type)
        confidence = confidence_for(flags, duplicate_type)

        record = CandidateRecord(
            command=command,
            command_key=key,
            base_command=base,
            category=str(entry["category"]),
            description=description,
            examples=list(dict.fromkeys(entry["examples"])),
            source_line=int(entry["source_line"]),
            source_page=entry["source_page"],
            canonical_source=CANONICAL_SOURCE,
            source_files=list(dict.fromkeys(entry["sources"])),
            status=status,
            duplicate_type=duplicate_type,
            duplicate_of=duplicate_of,
            quality_flags=flags,
            confidence=confidence,
        )
        if key not in seen:
            seen[key] = len(records)
        records.append(record)
    return records


def write_json(records: list[CandidateRecord], stats: dict[str, Any]) -> None:
    payload = {
        "schema_version": "1.0",
        "source": str(SOURCE_TEXT.relative_to(PROJECT_ROOT)),
        "canonical_source": CANONICAL_SOURCE,
        "promotion_status": "candidates_only",
        "stats": stats,
        "records": [asdict(record) for record in records],
    }
    CANDIDATE_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(records: list[CandidateRecord]) -> None:
    with CANDIDATE_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "command",
            "command_key",
            "base_command",
            "category",
            "description",
            "examples",
            "source_line",
            "source_page",
            "canonical_source",
            "source_files",
            "status",
            "duplicate_type",
            "duplicate_of",
            "quality_flags",
            "confidence",
        ])
        for record in records:
            writer.writerow([
                record.command,
                record.command_key,
                record.base_command,
                record.category,
                record.description,
                " | ".join(record.examples),
                record.source_line,
                record.source_page or "",
                record.canonical_source,
                " | ".join(record.source_files),
                record.status,
                record.duplicate_type,
                record.duplicate_of,
                " | ".join(record.quality_flags),
                record.confidence,
            ])


def stats_for(records: list[CandidateRecord], raw_entries: list[dict[str, Any]]) -> dict[str, Any]:
    unique_keys = {record.command_key for record in records}
    duplicates_existing = [record for record in records if "canonical" in record.duplicate_type or "command_index" in record.duplicate_type]
    malformed = [record for record in records if record.status in {"malformed", "unresolved"}]
    return {
        "total_parsed_entries": len(raw_entries),
        "total_candidate_records": len(records),
        "total_unique_candidate_commands": len(unique_keys),
        "duplicates_against_existing": len(duplicates_existing),
        "malformed_unresolved_entries": len(malformed),
        "candidate_only_entries": sum(1 for record in records if record.status == "candidate"),
        "internal_candidate_duplicates": sum(1 for record in records if "candidate_internal" in record.duplicate_type),
    }


def write_reports(records: list[CandidateRecord], stats: dict[str, Any]) -> None:
    category_counts = Counter(record.category for record in records)
    status_counts = Counter(record.status for record in records)
    duplicate_counts = Counter(record.duplicate_type or "new_candidate" for record in records)
    flag_counts = Counter(flag for record in records for flag in record.quality_flags)

    DEDUP_REPORT.write_text(
        "\n".join([
            "# Candidate Deduplication Report",
            "",
            f"- Total parsed entries: {stats['total_parsed_entries']}",
            f"- Total unique candidate commands: {stats['total_unique_candidate_commands']}",
            f"- Duplicates against existing canonical/index: {stats['duplicates_against_existing']}",
            f"- Internal candidate duplicates: {stats['internal_candidate_duplicates']}",
            "",
            "## Duplicate Type Counts",
            "",
            *[f"- {key}: {value}" for key, value in sorted(duplicate_counts.items())],
            "",
            "## Sample Existing Duplicates",
            "",
            *[
                f"- `{record.command}` -> {record.duplicate_type}"
                for record in records
                if record.status == "duplicate_existing"
            ][:50],
            "",
            "Canonical runtime files were not modified.",
        ]) + "\n",
        encoding="utf-8",
    )

    QUALITY_REPORT.write_text(
        "\n".join([
            "# Candidate Parsing Quality Report",
            "",
            f"- Total parsed entries: {stats['total_parsed_entries']}",
            f"- Candidate records written: {stats['total_candidate_records']}",
            f"- Malformed or unresolved entries: {stats['malformed_unresolved_entries']}",
            "",
            "## Status Counts",
            "",
            *[f"- {key}: {value}" for key, value in sorted(status_counts.items())],
            "",
            "## Quality Flag Counts",
            "",
            *([f"- {key}: {value}" for key, value in sorted(flag_counts.items())] or ["- none: 0"]),
            "",
            "## Sample Malformed/Unresolved Entries",
            "",
            *[
                f"- line {record.source_line}: `{record.command}` ({', '.join(record.quality_flags)})"
                for record in records
                if record.status in {"malformed", "unresolved"}
            ][:80],
            "",
            "No command rows were promoted to canonical indexes.",
        ]) + "\n",
        encoding="utf-8",
    )

    CATEGORY_REPORT.write_text(
        "\n".join([
            "# Candidate Category Distribution",
            "",
            *[f"- {category}: {count}" for category, count in sorted(category_counts.items())],
            "",
            "## By Status",
            "",
            *[f"- {status}: {count}" for status, count in sorted(status_counts.items())],
        ]) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = SOURCE_TEXT.read_text(encoding="utf-8", errors="replace").splitlines()
    canonical_keys, index_keys = load_existing_sets()
    page_by_entry = parse_toc_pages(lines)
    raw_entries = parse_entries(lines, page_by_entry)
    records = build_candidates(raw_entries, canonical_keys, index_keys)
    stats = stats_for(records, raw_entries)
    write_json(records, stats)
    write_csv(records)
    write_reports(records, stats)
    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"candidate_json={CANDIDATE_JSON.relative_to(PROJECT_ROOT)}")
    print(f"candidate_csv={CANDIDATE_CSV.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
