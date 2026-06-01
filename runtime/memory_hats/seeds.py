"""Local seed/example tags for the Memory Hats prototype.

Seed tags are local, advisory examples only. This module does not auto-load
them into runtime state, execute commands, contact networks, or define global
trusted tag packs.
"""

from __future__ import annotations

from pathlib import Path

from runtime.memory_hats.jsonl import import_tags_from_jsonl
from runtime.memory_hats.storage import SQLiteTagStore
from runtime.memory_hats.tags import PheromoneTag


LINUX_RHCSA_SEED_TAGS_PATH = (
    Path(__file__).resolve().parents[1]
    / "knowledge"
    / "memory_hats"
    / "linux_rhcsa_seed_tags.jsonl"
)


def load_linux_rhcsa_seed_tags() -> list[PheromoneTag]:
    """Load bundled local Linux/RHCSA seed tags without writing to storage."""
    text = LINUX_RHCSA_SEED_TAGS_PATH.read_text(encoding="utf-8")
    return import_tags_from_jsonl(text)


def import_seed_tags_into_store(
    store: SQLiteTagStore,
    tags: list[PheromoneTag],
) -> int:
    """Insert seed tags into a store and return the number processed.

    Duplicate handling is delegated to SQLiteTagStore.insert_tag, which is
    idempotent by fingerprint.
    """
    processed = 0
    for tag in tags:
        store.insert_tag(tag)
        processed += 1
    return processed
