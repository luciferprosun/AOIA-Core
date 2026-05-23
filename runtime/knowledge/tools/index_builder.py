"""Build a deterministic local keyword index for canonical RHCSA commands."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "index" / "command_index.json"

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_./$~{}*?+-]+")
WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/index_builder.py [canonical_json]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        report = build_index(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA deterministic keyword index build complete")
    print(f"keywords_indexed={report['keywords_indexed']}")
    print(f"commands_indexed={report['commands_indexed']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={output_path}")
    return 0


def build_index(input_path: Path, output_path: Path) -> dict[str, int]:
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.stat().st_size == 0:
        raise RuntimeError(f"input file is empty: {input_path}")

    try:
        entries = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(entries, list):
        raise RuntimeError("canonical command file must contain a JSON array")

    index: dict[str, set[str]] = defaultdict(set)
    malformed_entries_skipped = 0
    duplicate_links_removed = 0
    unique_commands: set[str] = set()

    for entry_index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(f"WARN: skipped malformed entry at index {entry_index}")
            malformed_entries_skipped += 1
            continue

        command = normalize_text(entry.get("command"))
        category = normalize_text(entry.get("category"))
        if not command or not category:
            print(f"WARN: skipped malformed entry at index {entry_index}")
            malformed_entries_skipped += 1
            continue

        unique_commands.add(command)
        keywords = sorted(tokenize(category) | tokenize(command))
        if not keywords:
            print(f"WARN: skipped entry with no keywords at index {entry_index}")
            malformed_entries_skipped += 1
            continue

        for keyword in keywords:
            before = len(index[keyword])
            index[keyword].add(command)
            if len(index[keyword]) == before:
                duplicate_links_removed += 1

    if not index:
        raise RuntimeError("no index entries created")

    deterministic_index = {
        keyword: sorted(commands)
        for keyword, commands in sorted(index.items(), key=lambda item: item[0])
    }
    validate_index(deterministic_index)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(deterministic_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "keywords_indexed": len(deterministic_index),
        "commands_indexed": len(unique_commands),
        "duplicates_removed": duplicate_links_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_RE.finditer(value.lower()):
        token = match.group(0).strip(".,:;()[]{}\"'")
        if token:
            tokens.add(token)
    return tokens


def validate_index(index: dict[str, list[str]]) -> None:
    previous_key = ""
    for key, commands in index.items():
        if previous_key and key < previous_key:
            raise RuntimeError("index keys are not sorted")
        previous_key = key
        if not isinstance(commands, list):
            raise RuntimeError(f"invalid command list for keyword: {key}")
        if len(commands) != len(set(commands)):
            raise RuntimeError(f"duplicate commands found for keyword: {key}")
        if commands != sorted(commands):
            raise RuntimeError(f"commands are not sorted for keyword: {key}")


if __name__ == "__main__":
    raise SystemExit(main())
