"""Read-only knowledge-profile registry.

Builds the profile list from real, on-disk repository assets only. It
never invents a working knowledge source when no index exists, and it
never writes, rebuilds, or mutates anything.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path

NONE_PROFILE_ID = "none"


@dataclass(frozen=True)
class KnowledgeProfile:
    id: str
    display_name: str
    description: str
    source_type: str
    document_count: int | None
    last_build_date: str | None
    authoritative: bool = False  # always False: knowledge is evidence, never authority


NONE_PROFILE = KnowledgeProfile(
    id=NONE_PROFILE_ID,
    display_name="None",
    description="No local knowledge attached. The model answers from conversation context only.",
    source_type="none",
    document_count=None,
    last_build_date=None,
)

_LINUX_CANONICAL_RELATIVE_PATH = Path("runtime/knowledge/canonical/rhcsa_commands.json")


def _linux_profile(repo_root: Path) -> KnowledgeProfile | None:
    canonical_path = repo_root / _LINUX_CANONICAL_RELATIVE_PATH
    if not canonical_path.is_file():
        return None
    document_count: int | None = None
    try:
        payload = json.loads(canonical_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            document_count = len(payload)
    except (OSError, json.JSONDecodeError):
        document_count = None

    try:
        mtime = canonical_path.stat().st_mtime
        last_build_date = _dt.datetime.fromtimestamp(mtime, tz=_dt.timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        last_build_date = None

    return KnowledgeProfile(
        id="linux_unix",
        display_name="Linux / UNIX Knowledge",
        description=(
            "Local read-only RHCSA/Linux administration knowledge library "
            "(runtime/knowledge/). Evidence only — not authoritative, not "
            "an execution permission."
        ),
        source_type="local_read_only_index",
        document_count=document_count,
        last_build_date=last_build_date,
    )


def discover_profiles(repo_root: Path) -> list[KnowledgeProfile]:
    """Return the available knowledge profiles, always starting with
    ``NONE_PROFILE``. Only includes a profile if its backing file actually
    exists on disk."""
    profiles: list[KnowledgeProfile] = [NONE_PROFILE]
    linux_profile = _linux_profile(repo_root)
    if linux_profile is not None:
        profiles.append(linux_profile)
    return profiles


def find_profile(profiles: list[KnowledgeProfile], profile_id: str) -> KnowledgeProfile:
    for profile in profiles:
        if profile.id == profile_id:
            return profile
    return NONE_PROFILE
