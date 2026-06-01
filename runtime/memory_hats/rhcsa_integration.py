"""Narrow RHCSA grammar advisory lookup integration for Memory Hats.

This module maps command strings to local Memory Hat paths and looks up existing
advisory tags. It does not execute commands, call shells, mutate stores during
lookup, inject prompts, or integrate with executor/router/provider code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from runtime.memory_hats.advisory import AdvisoryWarning, advisory_from_tag
from runtime.memory_hats.dedup import normalize_trigger
from runtime.memory_hats.leaf_routes import build_leaf_path, slugify_path_component
from runtime.memory_hats.storage import SQLiteTagStore
from runtime.memory_hats.tags import PheromoneTag, ReviewStatus, TagType


DEFAULT_RHCSA_HAT_ID = "linux_rhcsa"
DEFAULT_PRIMARY_VEIN = "command_grammar"
DEFAULT_SECONDARY_VEIN = "unsupported_linux_command"

_ACTIVE_STATUS_ORDER = (ReviewStatus.CONFIRMED, ReviewStatus.CANDIDATE)
_SAFE_READ_ONLY_STATUSES = {"exact", "family", "partial"}
_LOOKUP_STATUSES = {"suspicious", "reject", "unsupported", "unknown", "partial"}
_NON_READ_ONLY_DANGERS = {
    "state_change",
    "privileged",
    "destructive",
    "critical",
    "unknown",
}


def command_to_memory_hat_path(
    command: str,
    hat_id: str = DEFAULT_RHCSA_HAT_ID,
    primary_vein: str = DEFAULT_PRIMARY_VEIN,
    secondary_vein: str = DEFAULT_SECONDARY_VEIN,
) -> str:
    """Build the deterministic Memory Hat leaf path for a command string."""
    normalized = normalize_trigger(command)
    micro_vein = slugify_path_component(normalized)
    return build_leaf_path(hat_id, primary_vein, secondary_vein, micro_vein)


def lookup_advisory_for_command(
    command: str,
    store: SQLiteTagStore,
    tag_type: TagType = TagType.UNSUPPORTED_LINUX_COMMAND,
    hat_id: str = DEFAULT_RHCSA_HAT_ID,
    primary_vein: str = DEFAULT_PRIMARY_VEIN,
    secondary_vein: str = DEFAULT_SECONDARY_VEIN,
) -> AdvisoryWarning | None:
    """Return an advisory warning for an existing matching local tag."""
    normalized = normalize_trigger(command)
    path = command_to_memory_hat_path(
        command,
        hat_id=hat_id,
        primary_vein=primary_vein,
        secondary_vein=secondary_vein,
    )
    matches = [
        tag
        for tag in store.get_by_path(path)
        if tag.hat_id == hat_id
        and tag.tag_type == tag_type
        and tag.normalized_trigger == normalized
    ]

    for review_status in _ACTIVE_STATUS_ORDER:
        best = _first_by_status(matches, review_status)
        if best is not None:
            return advisory_from_tag(best)

    return None


def lookup_advisory_for_grammar_result(
    command: str,
    grammar_status: str,
    grammar_danger: str | None,
    store: SQLiteTagStore,
) -> AdvisoryWarning | None:
    """Use a grammar classifier result to decide whether to attempt lookup."""
    status = _label(grammar_status)
    danger = _label(grammar_danger)

    if status in _SAFE_READ_ONLY_STATUSES and danger == "read_only":
        return None
    if status in _LOOKUP_STATUSES:
        return lookup_advisory_for_command(command, store)
    if danger in _NON_READ_ONLY_DANGERS:
        return lookup_advisory_for_command(command, store)

    return None


def validate_and_lookup_advisory(
    command: str,
    store: SQLiteTagStore,
    validator: Callable[[str], Any] | None = None,
) -> AdvisoryWarning | None:
    """Optionally classify a command before local advisory lookup.

    The validator is an explicit pure classifier callback. No validator is
    imported or called implicitly.
    """
    if validator is None:
        return lookup_advisory_for_command(command, store)

    result = validator(command)
    status = _result_value(result, "status")
    danger = _result_value(result, "danger")
    return lookup_advisory_for_grammar_result(command, status, danger, store)


def _first_by_status(
    tags: list[PheromoneTag],
    review_status: ReviewStatus,
) -> PheromoneTag | None:
    for tag in sorted(tags, key=lambda item: item.fingerprint_hash):
        if tag.review_status == review_status:
            return tag
    return None


def _label(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip().lower()


def _result_value(result: Any, key: str) -> str | None:
    if isinstance(result, dict):
        value = result.get(key)
    else:
        value = getattr(result, key, None)
    if value is None:
        return None
    return str(value)
