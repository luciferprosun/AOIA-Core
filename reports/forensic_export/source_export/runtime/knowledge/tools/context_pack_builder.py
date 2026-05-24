"""Build deterministic static context packs from the RHCSA keyword index."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = PROJECT_ROOT / "knowledge" / "index" / "command_index.json"
DEFAULT_COMMANDS = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "context" / "context_pack.json"
DEFAULT_QUERIES = ("network ports",)

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_./$~{}*?+-]+")
WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    queries = [normalize_text(query) for query in args] if args else list(DEFAULT_QUERIES)
    queries = [query for query in queries if query]
    if not queries:
        print("ERROR: at least one non-empty query is required")
        return 2

    try:
        report = build_context_packs(DEFAULT_INDEX, DEFAULT_COMMANDS, DEFAULT_OUTPUT, queries)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA deterministic context pack build complete")
    print(f"context_packs_generated={report['context_packs_generated']}")
    print(f"matched_keywords={report['matched_keywords']}")
    print(f"matched_commands={report['matched_commands']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={DEFAULT_OUTPUT}")
    return 0


def build_context_packs(
    index_path: Path,
    commands_path: Path,
    output_path: Path,
    queries: list[str],
) -> dict[str, int]:
    index = load_json_object(index_path, "command index")
    canonical_entries = load_json_array(commands_path, "canonical commands")
    command_map, malformed_entries_skipped = build_command_map(canonical_entries)

    context_packs: list[dict[str, Any]] = []
    total_matched_keywords = 0
    total_matched_commands = 0
    total_duplicates_removed = 0

    for query in queries:
        pack, duplicates_removed = build_context_pack(query, index, command_map)
        context_packs.append(pack)
        total_matched_keywords += len(pack["matched_keywords"])
        total_matched_commands += len(pack["matched_commands"])
        total_duplicates_removed += duplicates_removed

    validate_context_packs(context_packs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(context_packs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "context_packs_generated": len(context_packs),
        "matched_keywords": total_matched_keywords,
        "matched_commands": total_matched_commands,
        "duplicates_removed": total_duplicates_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    data = load_json(path, label)
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} must contain a JSON object")
    return data


def load_json_array(path: Path, label: str) -> list[Any]:
    data = load_json(path, label)
    if not isinstance(data, list):
        raise RuntimeError(f"{label} must contain a JSON array")
    return data


def load_json(path: Path, label: str) -> Any:
    if not path.exists():
        raise RuntimeError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"{label} path is not a file: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"{label} file is empty: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} invalid JSON: {exc.msg}") from exc


def build_command_map(entries: list[Any]) -> tuple[dict[str, dict[str, Any]], int]:
    command_map: dict[str, dict[str, Any]] = {}
    malformed_entries_skipped = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(f"WARN: skipped malformed canonical entry at index {index}")
            malformed_entries_skipped += 1
            continue
        command = normalize_text(entry.get("command"))
        if not command:
            print(f"WARN: skipped canonical entry without command at index {index}")
            malformed_entries_skipped += 1
            continue
        command_map[command] = entry
    return command_map, malformed_entries_skipped


def build_context_pack(
    query: str,
    index: dict[str, Any],
    command_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    query_tokens = sorted(tokenize(query))
    matched_keywords = [token for token in query_tokens if token in index]

    matched_commands: list[dict[str, Any]] = []
    seen_commands: set[str] = set()
    duplicates_removed = 0

    for keyword in matched_keywords:
        commands = index.get(keyword, [])
        if not isinstance(commands, list):
            print(f"WARN: skipped malformed command list for keyword: {keyword}")
            continue
        for raw_command in commands:
            command = normalize_text(raw_command)
            if not command:
                print(f"WARN: skipped malformed command for keyword: {keyword}")
                continue
            if command in seen_commands:
                duplicates_removed += 1
                continue

            entry = command_map.get(command)
            if not entry:
                print(f"WARN: skipped command missing canonical entry: {command}")
                continue

            matched_commands.append(
                {
                    "command": command,
                    "description": normalize_text(entry.get("description")),
                    "examples": normalize_examples(entry.get("examples")),
                    "source_section": normalize_text(entry.get("source_section")),
                }
            )
            seen_commands.add(command)

    return (
        {
            "query": query,
            "matched_keywords": matched_keywords,
            "matched_commands": matched_commands,
        },
        duplicates_removed,
    )


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_examples(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    examples: list[str] = []
    seen: set[str] = set()
    for item in value:
        example = normalize_text(item)
        if example and example not in seen:
            examples.append(example)
            seen.add(example)
    return examples


def tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_RE.finditer(value.lower()):
        token = match.group(0).strip(".,:;()[]{}\"'")
        if token:
            tokens.add(token)
    return tokens


def validate_context_packs(context_packs: list[dict[str, Any]]) -> None:
    for index, pack in enumerate(context_packs):
        if not pack.get("query"):
            raise RuntimeError(f"context pack at index {index} has empty query")
        keywords = pack.get("matched_keywords")
        if not isinstance(keywords, list) or keywords != sorted(keywords):
            raise RuntimeError(f"context pack at index {index} has invalid keyword order")
        commands = pack.get("matched_commands")
        if not isinstance(commands, list):
            raise RuntimeError(f"context pack at index {index} has invalid matched_commands")
        command_names = [entry.get("command") for entry in commands if isinstance(entry, dict)]
        if len(command_names) != len(set(command_names)):
            raise RuntimeError(f"context pack at index {index} has duplicate commands")


if __name__ == "__main__":
    raise SystemExit(main())
