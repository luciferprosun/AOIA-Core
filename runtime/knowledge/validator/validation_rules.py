"""Deterministic AOIA knowledge pack validation rules."""

from __future__ import annotations

import re

REQUIRED_FIELDS = (
    "id",
    "command",
    "description",
    "category",
    "tags",
    "risk",
    "os",
    "shell",
    "examples",
)

OPTIONAL_FIELDS = (
    "notes",
    "related_commands",
)

ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS + OPTIONAL_FIELDS)

ALLOWED_CATEGORIES = frozenset(
    (
        "archive",
        "diagnostic",
        "filesystem",
        "network",
        "package",
        "process",
        "security",
        "service",
        "system",
        "user",
    )
)

ALLOWED_RISKS = frozenset(("low", "medium", "high", "critical"))

ALLOWED_OS = frozenset(("linux", "rhel", "ubuntu", "debian", "fedora", "macos"))

ALLOWED_SHELLS = frozenset(("bash", "sh", "zsh"))

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FILENAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.json$")
TAG_RE = ID_RE
RELATED_COMMAND_RE = re.compile(r"^[a-z0-9._+-]+$")


def is_valid_identifier(value: str) -> bool:
    return bool(ID_RE.fullmatch(value))


def is_valid_filename(value: str) -> bool:
    return bool(FILENAME_RE.fullmatch(value))


def is_valid_tag(value: str) -> bool:
    return bool(TAG_RE.fullmatch(value))


def is_valid_related_command(value: str) -> bool:
    return bool(RELATED_COMMAND_RE.fullmatch(value))
