"""Deterministic local validator for AOIA knowledge packs."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .validation_rules import (
        ALLOWED_CATEGORIES,
        ALLOWED_FIELDS,
        ALLOWED_OS,
        ALLOWED_RISKS,
        ALLOWED_SHELLS,
        REQUIRED_FIELDS,
        is_valid_filename,
        is_valid_identifier,
        is_valid_related_command,
        is_valid_tag,
    )
except ImportError:  # Allows direct execution: python knowledge/validator/validator.py knowledge/
    from validation_rules import (  # type: ignore
        ALLOWED_CATEGORIES,
        ALLOWED_FIELDS,
        ALLOWED_OS,
        ALLOWED_RISKS,
        ALLOWED_SHELLS,
        REQUIRED_FIELDS,
        is_valid_filename,
        is_valid_identifier,
        is_valid_related_command,
        is_valid_tag,
    )


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    checked_files: int
    message: str


def discover_entry_files(root: Path) -> list[Path]:
    """Return knowledge entry files in stable order."""
    examples_dir = root / "examples"
    search_root = examples_dir if examples_dir.is_dir() else root
    return sorted(path for path in search_root.rglob("*.json") if path.is_file())


def validate_path(root: str | Path) -> ValidationReport:
    root_path = Path(root)
    if not root_path.exists():
        return ValidationReport(False, 0, f"root does not exist: {root_path}")
    if not root_path.is_dir():
        return ValidationReport(False, 0, f"root is not a directory: {root_path}")

    files = discover_entry_files(root_path)
    if not files:
        return ValidationReport(False, 0, f"no knowledge entry files found: {root_path}")

    seen_commands: dict[str, Path] = {}
    checked = 0

    for path in files:
        checked += 1
        file_error = validate_filename(path)
        if file_error:
            return ValidationReport(False, checked, f"{path}: {file_error}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return ValidationReport(False, checked, f"{path}: invalid JSON: {exc.msg}")

        entry_error = validate_entry(data)
        if entry_error:
            return ValidationReport(False, checked, f"{path}: {entry_error}")

        command = data["command"]
        if command in seen_commands:
            return ValidationReport(
                False,
                checked,
                f"{path}: duplicate command '{command}' also defined in {seen_commands[command]}",
            )
        seen_commands[command] = path

    return ValidationReport(True, checked, f"validated {checked} knowledge entry file(s)")


def validate_filename(path: Path) -> str | None:
    if not is_valid_filename(path.name):
        return "invalid filename; expected lowercase kebab-case .json"
    return None


def validate_entry(data: Any) -> str | None:
    if not isinstance(data, dict):
        return "entry must be a JSON object"

    unknown_fields = sorted(set(data) - ALLOWED_FIELDS)
    if unknown_fields:
        return f"unknown field(s): {', '.join(unknown_fields)}"

    for field in REQUIRED_FIELDS:
        if field not in data:
            return f"missing required field: {field}"

    scalar_error = validate_scalar_fields(data)
    if scalar_error:
        return scalar_error

    list_error = validate_list_fields(data)
    if list_error:
        return list_error

    examples_error = validate_examples(data["examples"])
    if examples_error:
        return examples_error

    optional_error = validate_optional_fields(data)
    if optional_error:
        return optional_error

    return None


def validate_scalar_fields(data: dict[str, Any]) -> str | None:
    if not isinstance(data["id"], str) or not is_valid_identifier(data["id"]):
        return "invalid id; expected lowercase kebab-case"
    if not isinstance(data["command"], str) or not data["command"].strip():
        return "invalid command; expected non-empty string"
    if not isinstance(data["description"], str) or not data["description"].strip():
        return "invalid description; expected non-empty string"
    if len(data["description"]) > 240:
        return "invalid description; maximum length is 240"
    if data["category"] not in ALLOWED_CATEGORIES:
        return f"invalid category: {data['category']}"
    if data["risk"] not in ALLOWED_RISKS:
        return f"invalid risk: {data['risk']}"
    return None


def validate_list_fields(data: dict[str, Any]) -> str | None:
    tag_error = validate_string_list("tags", data["tags"])
    if tag_error:
        return tag_error
    for tag in data["tags"]:
        if not is_valid_tag(tag):
            return f"invalid tag: {tag}"

    os_error = validate_string_list("os", data["os"])
    if os_error:
        return os_error
    for os_name in data["os"]:
        if os_name not in ALLOWED_OS:
            return f"invalid os: {os_name}"

    shell_error = validate_string_list("shell", data["shell"])
    if shell_error:
        return shell_error
    for shell_name in data["shell"]:
        if shell_name not in ALLOWED_SHELLS:
            return f"invalid shell: {shell_name}"

    return None


def validate_string_list(name: str, value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return f"invalid {name}; expected non-empty array"
    if any(not isinstance(item, str) or not item for item in value):
        return f"invalid {name}; expected non-empty strings"
    if len(set(value)) != len(value):
        return f"invalid {name}; duplicate values are not allowed"
    return None


def validate_examples(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return "invalid examples; expected non-empty array"
    for index, example in enumerate(value):
        if not isinstance(example, dict):
            return f"invalid examples[{index}]; expected object"
        unknown_fields = sorted(set(example) - {"input", "expected_effect"})
        if unknown_fields:
            return f"invalid examples[{index}]; unknown field(s): {', '.join(unknown_fields)}"
        if "input" not in example:
            return f"invalid examples[{index}]; missing input"
        if "expected_effect" not in example:
            return f"invalid examples[{index}]; missing expected_effect"
        if not isinstance(example["input"], str) or not example["input"].strip():
            return f"invalid examples[{index}].input; expected non-empty string"
        effect = example["expected_effect"]
        if not isinstance(effect, str) or not effect.strip():
            return f"invalid examples[{index}].expected_effect; expected non-empty string"
        if len(effect) > 240:
            return f"invalid examples[{index}].expected_effect; maximum length is 240"
    return None


def validate_optional_fields(data: dict[str, Any]) -> str | None:
    if "notes" in data:
        if not isinstance(data["notes"], str):
            return "invalid notes; expected string"
        if len(data["notes"]) > 500:
            return "invalid notes; maximum length is 500"
    if "related_commands" in data:
        error = validate_string_list("related_commands", data["related_commands"])
        if error:
            return error
        for command in data["related_commands"]:
            if not is_valid_related_command(command):
                return f"invalid related command: {command}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python validator.py knowledge/")
        return 2

    report = validate_path(args[0])
    status = "OK" if report.ok else "ERROR"
    print(f"{status}: {report.message}")
    print(f"checked_files={report.checked_files}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
