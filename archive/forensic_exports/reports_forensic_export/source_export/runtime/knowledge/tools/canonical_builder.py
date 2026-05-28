"""Build deterministic canonical RHCSA command entries from parsed sections."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "parsed" / "rhcsa_sections.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_RISK = "unclassified"

WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/canonical_builder.py [sections_json]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        report = build_canonical(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA canonical command build complete")
    print(f"canonical_entries_created={report['canonical_entries_created']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={output_path}")
    return 0


def build_canonical(input_path: Path, output_path: Path) -> dict[str, int]:
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.stat().st_size == 0:
        raise RuntimeError(f"input file is empty: {input_path}")

    try:
        sections = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(sections, list):
        raise RuntimeError("parsed sections file must contain a JSON array")

    entries: list[dict[str, Any]] = []
    seen_commands: set[str] = set()
    duplicates_removed = 0
    malformed_entries_skipped = 0

    for section_index, section in enumerate(sections):
        if not isinstance(section, dict):
            print(f"WARN: skipped malformed section at index {section_index}")
            malformed_entries_skipped += 1
            continue

        source_section = normalize_text(section.get("section", ""))
        commands = section.get("commands")
        examples = section.get("examples", [])

        if not source_section or not isinstance(commands, list):
            print(f"WARN: skipped malformed section at index {section_index}")
            malformed_entries_skipped += 1
            continue

        section_examples = normalize_examples(examples)

        for command_index, raw_command in enumerate(commands):
            command = normalize_text(raw_command)
            if not command:
                print(
                    "WARN: skipped malformed command "
                    f"at section_index={section_index} command_index={command_index}"
                )
                malformed_entries_skipped += 1
                continue

            if command in seen_commands:
                duplicates_removed += 1
                continue

            entry = {
                "command": command,
                "category": source_section,
                "risk": DEFAULT_RISK,
                "description": "",
                "examples": select_examples(command, section_examples),
                "source_section": source_section,
            }

            validation_error = validate_entry(entry)
            if validation_error:
                print(
                    "WARN: skipped malformed entry "
                    f"at section_index={section_index} command_index={command_index}: "
                    f"{validation_error}"
                )
                malformed_entries_skipped += 1
                continue

            entries.append(entry)
            seen_commands.add(command)

    if not entries:
        raise RuntimeError("no canonical entries created")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "canonical_entries_created": len(entries),
        "duplicates_removed": duplicates_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_examples(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        example = normalize_text(item)
        if example and example not in seen:
            normalized.append(example)
            seen.add(example)
    return normalized


def select_examples(command: str, section_examples: list[str]) -> list[str]:
    matches = [example for example in section_examples if example == command]
    return matches if matches else []


def validate_entry(entry: dict[str, Any]) -> str | None:
    if not entry.get("command"):
        return "command field required"
    if not entry.get("category"):
        return "category field required"
    if not entry.get("risk"):
        return "risk field required"
    if not isinstance(entry.get("examples"), list):
        return "examples must be an array"
    if not entry.get("source_section"):
        return "source_section field required"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
