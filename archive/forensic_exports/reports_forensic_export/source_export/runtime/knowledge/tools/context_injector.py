"""Build static deterministic helper context from RHCSA context packs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTEXT_PACK = PROJECT_ROOT / "knowledge" / "context" / "context_pack.json"
DEFAULT_CANONICAL = PROJECT_ROOT / "knowledge" / "canonical" / "rhcsa_commands.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "injection" / "injected_context.json"
SOURCE_NAME = "RHCSA knowledge pack"

WHITESPACE_RE = re.compile(r"\s+")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        print("ERROR: usage: python3 knowledge/tools/context_injector.py")
        return 2

    try:
        report = build_injected_context(DEFAULT_CONTEXT_PACK, DEFAULT_CANONICAL, DEFAULT_OUTPUT)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA deterministic context injection build complete")
    print(f"injected_contexts_generated={report['injected_contexts_generated']}")
    print(f"commands_injected={report['commands_injected']}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"malformed_entries_skipped={report['malformed_entries_skipped']}")
    print(f"output_path={DEFAULT_OUTPUT}")
    return 0


def build_injected_context(
    context_pack_path: Path,
    canonical_path: Path,
    output_path: Path,
) -> dict[str, int]:
    context_packs = load_json_array(context_pack_path, "context pack")
    canonical_entries = load_json_array(canonical_path, "canonical commands")
    canonical_commands, malformed_canonical = load_canonical_commands(canonical_entries)

    injected_contexts: list[dict[str, Any]] = []
    total_commands_injected = 0
    total_duplicates_removed = 0
    malformed_entries_skipped = malformed_canonical

    for pack_index, pack in enumerate(context_packs):
        if not isinstance(pack, dict):
            print(f"WARN: skipped malformed context pack at index {pack_index}")
            malformed_entries_skipped += 1
            continue

        query = normalize_text(pack.get("query"))
        matched_commands = pack.get("matched_commands")
        if not query or not isinstance(matched_commands, list):
            print(f"WARN: skipped malformed context pack at index {pack_index}")
            malformed_entries_skipped += 1
            continue

        static_context: list[str] = []
        seen_commands: set[str] = set()

        for command_index, command_entry in enumerate(matched_commands):
            if not isinstance(command_entry, dict):
                print(
                    "WARN: skipped malformed matched command "
                    f"at pack_index={pack_index} command_index={command_index}"
                )
                malformed_entries_skipped += 1
                continue

            command = normalize_text(command_entry.get("command"))
            if not command:
                print(
                    "WARN: skipped matched command without command field "
                    f"at pack_index={pack_index} command_index={command_index}"
                )
                malformed_entries_skipped += 1
                continue

            if command in seen_commands:
                total_duplicates_removed += 1
                continue

            if command not in canonical_commands:
                print(f"WARN: skipped command missing from canonical pack: {command}")
                malformed_entries_skipped += 1
                continue

            static_context.append(f"Use: {command}")
            seen_commands.add(command)

        injected = {
            "query": query,
            "static_context": static_context,
            "source": SOURCE_NAME,
        }
        validate_injected_context(injected, pack_index)
        injected_contexts.append(injected)
        total_commands_injected += len(static_context)

    if not injected_contexts:
        raise RuntimeError("no injected contexts generated")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(injected_contexts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    return {
        "injected_contexts_generated": len(injected_contexts),
        "commands_injected": total_commands_injected,
        "duplicates_removed": total_duplicates_removed,
        "malformed_entries_skipped": malformed_entries_skipped,
    }


def load_json_array(path: Path, label: str) -> list[Any]:
    if not path.exists():
        raise RuntimeError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"{label} path is not a file: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"{label} file is empty: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} invalid JSON: {exc.msg}") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"{label} must contain a JSON array")
    return data


def load_canonical_commands(entries: list[Any]) -> tuple[set[str], int]:
    commands: set[str] = set()
    malformed_entries = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(f"WARN: skipped malformed canonical entry at index {index}")
            malformed_entries += 1
            continue
        command = normalize_text(entry.get("command"))
        if not command:
            print(f"WARN: skipped canonical entry without command at index {index}")
            malformed_entries += 1
            continue
        commands.add(command)
    return commands, malformed_entries


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def validate_injected_context(context: dict[str, Any], index: int) -> None:
    if not context.get("query"):
        raise RuntimeError(f"injected context at index {index} has empty query")
    static_context = context.get("static_context")
    if not isinstance(static_context, list):
        raise RuntimeError(f"injected context at index {index} has invalid static_context")
    if len(static_context) != len(set(static_context)):
        raise RuntimeError(f"injected context at index {index} has duplicate command injections")
    for item in static_context:
        if not isinstance(item, str) or not item.startswith("Use: "):
            raise RuntimeError(f"injected context at index {index} has malformed injection")
    if context.get("source") != SOURCE_NAME:
        raise RuntimeError(f"injected context at index {index} has invalid source")


if __name__ == "__main__":
    raise SystemExit(main())
