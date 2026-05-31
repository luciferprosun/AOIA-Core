"""Advisory RHCSA command-shape validation.

This module is local, deterministic, read-only, and non-executing. It does not
prove command safety or factual correctness, does not replace ShellCheck or
tree-sitter-bash, and is not wired into executor policy.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any


_PATTERN_PATH = (
    Path(__file__).resolve().parents[1]
    / "knowledge"
    / "grammar"
    / "command_patterns.json"
)

_REQUIRED_KEYS = {
    "status",
    "family",
    "base",
    "confidence",
    "danger",
    "reasons",
    "matched_pattern_id",
}
_STATUS_REJECT = "reject"
_STATUS_SUSPICIOUS = "suspicious"
_STATUS_FAMILY = "family"


def _result(
    *,
    status: str,
    family: str | None = None,
    base: str | None = None,
    confidence: str = "grammar_reject",
    danger: str = "unknown",
    reasons: list[str] | None = None,
    matched_pattern_id: str | None = None,
) -> dict[str, Any]:
    result = {
        "status": status,
        "family": family,
        "base": base,
        "confidence": confidence,
        "danger": danger,
        "reasons": reasons or [],
        "matched_pattern_id": matched_pattern_id,
    }
    missing = _REQUIRED_KEYS - set(result)
    if missing:
        raise RuntimeError(f"internal command grammar result missing keys: {missing}")
    return result


def _load_patterns() -> list[dict[str, Any]]:
    with _PATTERN_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("command grammar patterns must be a list")
    return data


def _pattern_by_base() -> dict[str, dict[str, Any]]:
    return {
        str(pattern.get("base")): pattern
        for pattern in _load_patterns()
        if isinstance(pattern, dict) and pattern.get("base")
    }


def _is_path_only(command: str) -> bool:
    return command.startswith(("/", "./", "../", "~")) and " " not in command.strip()


def _is_flag_only(command: str) -> bool:
    stripped = command.strip()
    return stripped.startswith("-") and " " not in stripped


def _is_variable_only(command: str) -> bool:
    return bool(re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", command.strip()))


def _is_glob_only(command: str) -> bool:
    stripped = command.strip()
    return any(ch in stripped for ch in "*?[") and " " not in stripped


def _has_shell_composition(tokens: list[str], command: str) -> bool:
    operators = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "2>>", "&"}
    if any(token in operators for token in tokens):
        return True
    return any(op in command for op in ("|", "&&", ";", ">", "<"))


def _split(command: str) -> tuple[list[str], str | None]:
    try:
        return shlex.split(command), None
    except ValueError as exc:
        return [], str(exc)


def _chmod_shape(tokens: list[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    args = [token for token in tokens[1:] if not token.startswith("-")]
    if len(args) < 2:
        return False, ["missing_mode_or_path"]
    mode = args[0]
    if re.fullmatch(r"[0-7]{3,4}", mode) or re.fullmatch(r"[ugoa]*[+-=][rwxXstugo,]+", mode):
        reasons.append("valid_chmod_mode")
    else:
        return False, ["invalid_chmod_mode"]
    return True, reasons + ["has_target"]


def _flags_allowed(tokens: list[str], allowed_flags: set[str]) -> bool:
    for token in tokens[1:]:
        if token.startswith("-") and "=" in token:
            flag = token.split("=", 1)[0]
        else:
            flag = token
        if flag.startswith("-") and flag not in allowed_flags:
            return False
    return True


def validate_command_shape(command: str) -> dict[str, Any]:
    """Return an advisory, non-executing command-shape classification."""

    if not isinstance(command, str):
        return _result(
            status=_STATUS_REJECT,
            reasons=["command_must_be_string"],
        )

    stripped = command.strip()
    if not stripped:
        return _result(status=_STATUS_REJECT, reasons=["empty_command"])
    if _is_path_only(stripped):
        return _result(status=_STATUS_REJECT, reasons=["path_only"])
    if _is_flag_only(stripped):
        return _result(status=_STATUS_REJECT, reasons=["flag_only"])
    if _is_variable_only(stripped):
        return _result(status=_STATUS_REJECT, reasons=["variable_only"])
    if _is_glob_only(stripped):
        return _result(status=_STATUS_REJECT, reasons=["glob_only"])

    tokens, error = _split(stripped)
    if error:
        return _result(
            status=_STATUS_REJECT,
            confidence="grammar_reject",
            reasons=["tokenization_error", error],
        )
    if not tokens:
        return _result(status=_STATUS_REJECT, reasons=["empty_after_tokenization"])

    composed = _has_shell_composition(tokens, stripped)
    base = tokens[0]
    patterns = _pattern_by_base()
    pattern = patterns.get(base)
    if pattern is None:
        return _result(
            status=_STATUS_SUSPICIOUS,
            base=base,
            confidence="grammar_suspicious",
            danger="unknown",
            reasons=["unknown_base"] + (["shell_composition_present"] if composed else []),
        )

    reasons = ["known_base"]
    allowed_flags = set(pattern.get("allowed_flags", []))
    subcommands = set(pattern.get("subcommands", []))
    danger = str(pattern.get("danger_default", "unknown"))

    if composed:
        return _result(
            status=_STATUS_SUSPICIOUS,
            family=str(pattern.get("family")),
            base=base,
            confidence="grammar_suspicious",
            danger=danger,
            reasons=reasons + ["shell_composition_present"],
            matched_pattern_id=str(pattern.get("id")),
        )

    if base == "chmod":
        ok, shape_reasons = _chmod_shape(tokens)
        if ok and _flags_allowed(tokens, allowed_flags):
            return _result(
                status=_STATUS_FAMILY,
                family=str(pattern.get("family")),
                base=base,
                confidence=str(pattern.get("confidence_on_match", "grammar_family")),
                danger=danger,
                reasons=reasons + shape_reasons,
                matched_pattern_id=str(pattern.get("id")),
            )
        return _result(
            status=_STATUS_SUSPICIOUS,
            family=str(pattern.get("family")),
            base=base,
            confidence="grammar_suspicious",
            danger=danger,
            reasons=reasons + shape_reasons,
            matched_pattern_id=str(pattern.get("id")),
        )

    if base == "firewall-cmd":
        if len(tokens) == 1:
            return _result(
                status=_STATUS_SUSPICIOUS,
                family=str(pattern.get("family")),
                base=base,
                confidence="grammar_partial",
                danger=danger,
                reasons=reasons + ["missing_firewall_option"],
                matched_pattern_id=str(pattern.get("id")),
            )
        if _flags_allowed(tokens, allowed_flags):
            return _result(
                status=_STATUS_FAMILY,
                family=str(pattern.get("family")),
                base=base,
                confidence=str(pattern.get("confidence_on_match", "grammar_family")),
                danger=danger,
                reasons=reasons + ["allowed_firewall_flags"],
                matched_pattern_id=str(pattern.get("id")),
            )
        return _result(
            status=_STATUS_SUSPICIOUS,
            family=str(pattern.get("family")),
            base=base,
            confidence="grammar_suspicious",
            danger=danger,
            reasons=reasons + ["unknown_firewall_flag_or_argument"],
            matched_pattern_id=str(pattern.get("id")),
        )

    if len(tokens) == 1:
        return _result(
            status="partial",
            family=str(pattern.get("family")),
            base=base,
            confidence="grammar_partial",
            danger=danger,
            reasons=reasons + ["base_only"],
            matched_pattern_id=str(pattern.get("id")),
        )

    subcommand = tokens[1]
    if subcommands and subcommand not in subcommands:
        return _result(
            status=_STATUS_SUSPICIOUS,
            family=str(pattern.get("family")),
            base=base,
            confidence="grammar_suspicious",
            danger=danger,
            reasons=reasons + ["unknown_subcommand"],
            matched_pattern_id=str(pattern.get("id")),
        )
    if not _flags_allowed(tokens, allowed_flags):
        return _result(
            status=_STATUS_SUSPICIOUS,
            family=str(pattern.get("family")),
            base=base,
            confidence="grammar_suspicious",
            danger=danger,
            reasons=reasons + ["unknown_flag"],
            matched_pattern_id=str(pattern.get("id")),
        )

    return _result(
        status=_STATUS_FAMILY,
        family=str(pattern.get("family")),
        base=base,
        confidence=str(pattern.get("confidence_on_match", "grammar_family")),
        danger=danger,
        reasons=reasons + ["known_subcommand"],
        matched_pattern_id=str(pattern.get("id")),
    )
