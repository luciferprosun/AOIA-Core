"""Standalone Leaf-Vein path helpers for Memory Hats.

This module only builds and validates deterministic materialized paths. It does
not perform storage, command execution, runtime routing, or SQLite queries.
"""

from __future__ import annotations

import re

_UNSUPPORTED_COMPONENT_CHARS = re.compile(r"[^a-z0-9_-]+")
_REPEATED_UNDERSCORES = re.compile(r"_+")


def slugify_path_component(value: str) -> str:
    """Normalize one Leaf-Vein path component into a conservative slug."""
    if not isinstance(value, str):
        raise TypeError("path component must be a string")

    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = _UNSUPPORTED_COMPONENT_CHARS.sub("_", normalized)
    normalized = _REPEATED_UNDERSCORES.sub("_", normalized)
    return normalized.strip("_")


def build_leaf_path(
    hat_id: str,
    primary_vein: str,
    secondary_vein: str,
    micro_vein: str,
) -> str:
    """Build a canonical four-segment Leaf-Vein materialized path."""
    components = [
        slugify_path_component(hat_id),
        slugify_path_component(primary_vein),
        slugify_path_component(secondary_vein),
        slugify_path_component(micro_vein),
    ]
    if any(component == "" for component in components):
        raise ValueError("leaf path components must not be empty")

    return "/".join(components)


def parse_leaf_path(path: str) -> dict[str, str]:
    """Parse and validate a canonical four-segment Leaf-Vein path."""
    if not isinstance(path, str):
        raise TypeError("leaf path must be a string")
    if path.startswith("/"):
        raise ValueError("leaf path must not start with '/'")

    components = path.split("/")
    if len(components) != 4:
        raise ValueError("leaf path must have exactly four components")
    if any(component == "" for component in components):
        raise ValueError("leaf path components must not be empty")
    if any(slugify_path_component(component) != component for component in components):
        raise ValueError("leaf path components must be canonical slugs")

    return {
        "hat_id": components[0],
        "primary_vein": components[1],
        "secondary_vein": components[2],
        "micro_vein": components[3],
    }


def parent_leaf_path(path: str) -> str:
    """Return the parent path containing hat, primary vein, and secondary vein."""
    parse_leaf_path(path)
    return "/".join(path.split("/")[:3])


def is_valid_leaf_path(path: str) -> bool:
    """Return whether a value is a valid canonical Leaf-Vein path."""
    try:
        parse_leaf_path(path)
    except (TypeError, ValueError):
        return False
    return True


def path_matches_prefix(path: str, prefix: str) -> bool:
    """Return True for exact segment-prefix matches only."""
    if not is_valid_leaf_path(path) or not isinstance(prefix, str):
        return False
    if prefix.startswith("/"):
        return False

    prefix_components = prefix.split("/")
    path_components = path.split("/")
    if not 1 <= len(prefix_components) <= len(path_components):
        return False
    if any(component == "" for component in prefix_components):
        return False
    if any(
        slugify_path_component(component) != component
        for component in prefix_components
    ):
        return False

    return path_components[: len(prefix_components)] == prefix_components
