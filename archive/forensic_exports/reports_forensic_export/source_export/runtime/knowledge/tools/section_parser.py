"""Deterministic structural parser for RHCSA raw extracted text."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "knowledge" / "raw" / "rhcsa_raw.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "parsed" / "rhcsa_sections.json"

SECTION_RE = re.compile(r"^\s*\D*\s*(\d{1,2})\.\s+(.+?)\s+(\d+)\s+komend\s*$")
PAGE_FOOTER_RE = re.compile(r"^\s*Biblioteka komend RHCSA\s+Strona\s+\d+\s*$")
HEADER_RE = re.compile(r"^\s*RHCSA COMMAND LIBRARY\s+RHCSA 9\s+\|\s+Red Hat Certified System Administrator\s*$")
COMMAND_TOKEN_RE = re.compile(r"^[a-zA-Z0-9_./$~{}*?+-][^\s]{0,80}$")
SPLIT_RE = re.compile(r"\s{2,}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("ERROR: usage: python3 knowledge/tools/section_parser.py [raw_text_file]")
        return 2

    input_path = Path(args[0]).resolve() if args else DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    try:
        report = parse_file(input_path, output_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: RHCSA section parsing complete")
    print(f"sections_found={report['sections_found']}")
    print(f"commands_detected={report['commands_detected']}")
    print(f"malformed_blocks_skipped={report['malformed_blocks_skipped']}")
    print(f"output_path={output_path}")
    return 0


def parse_file(input_path: Path, output_path: Path) -> dict[str, int]:
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise RuntimeError(f"input path is not a file: {input_path}")
    if input_path.stat().st_size == 0:
        raise RuntimeError(f"input file is empty: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8")
    sections, malformed_blocks = parse_sections(raw_text.splitlines())
    validate_sections(sections)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(sections, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not output_path.exists():
        raise RuntimeError(f"output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"output file is empty: {output_path}")

    commands_detected = sum(len(section["commands"]) for section in sections)
    return {
        "sections_found": len(sections),
        "commands_detected": commands_detected,
        "malformed_blocks_skipped": malformed_blocks,
    }


def parse_sections(lines: list[str]) -> tuple[list[dict[str, Any]], int]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    malformed_blocks = 0

    for line in lines:
        cleaned = line.strip()
        if should_skip_line(cleaned):
            continue

        section_match = SECTION_RE.match(cleaned)
        if section_match:
            section_name = normalize_section_name(section_match.group(2))
            if not section_name:
                malformed_blocks += 1
                current = None
                continue
            current = {"section": section_name, "commands": [], "examples": []}
            sections.append(current)
            continue

        if current is None:
            continue

        command_candidates = extract_command_candidates(line)
        if not command_candidates:
            continue

        for command in command_candidates:
            if command not in current["commands"]:
                current["commands"].append(command)
                current["examples"].append(command)

    return sections, malformed_blocks


def should_skip_line(cleaned: str) -> bool:
    if not cleaned:
        return True
    if cleaned == "\x0c":
        return True
    if PAGE_FOOTER_RE.match(cleaned):
        return True
    if HEADER_RE.match(cleaned):
        return True
    if cleaned.startswith("Spis Tre"):
        return True
    return False


def normalize_section_name(value: str) -> str:
    normalized = " ".join(value.split())
    return normalized.strip(" -")


def extract_command_candidates(line: str) -> list[str]:
    parts = [part.strip() for part in SPLIT_RE.split(line.rstrip()) if part.strip()]
    if len(parts) < 2:
        return []

    candidates: list[str] = []
    for index in range(0, len(parts), 2):
        token = parts[index]
        if is_command_like(token):
            candidates.append(token)
    return candidates


def is_command_like(value: str) -> bool:
    if len(value) > 90:
        return False
    if " " in value and not allowed_command_with_space(value):
        return False
    first = value.split()[0]
    if not COMMAND_TOKEN_RE.match(first):
        return False
    if value.endswith("."):
        return False
    return True


def allowed_command_with_space(value: str) -> bool:
    first = value.split()[0]
    return first in {
        "alias",
        "awk",
        "cat",
        "cd",
        "chmod",
        "chown",
        "cp",
        "dnf",
        "echo",
        "find",
        "firewall-cmd",
        "grep",
        "ip",
        "journalctl",
        "ls",
        "mkdir",
        "mount",
        "nmcli",
        "podman",
        "restorecon",
        "rm",
        "rpm",
        "rsync",
        "semanage",
        "setsebool",
        "ssh",
        "systemctl",
        "tar",
        "touch",
        "useradd",
        "usermod",
        "vim",
    }


def validate_sections(sections: list[dict[str, Any]]) -> None:
    if not sections:
        raise RuntimeError("no sections detected")
    for index, section in enumerate(sections):
        name = section.get("section")
        if not isinstance(name, str) or not name.strip():
            raise RuntimeError(f"empty section name at index {index}")
        if not isinstance(section.get("commands"), list):
            raise RuntimeError(f"invalid commands list at index {index}")
        if not isinstance(section.get("examples"), list):
            raise RuntimeError(f"invalid examples list at index {index}")


if __name__ == "__main__":
    raise SystemExit(main())
