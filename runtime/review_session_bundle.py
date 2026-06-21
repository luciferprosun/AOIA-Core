from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from runtime.review_session_snapshot import ReviewSessionSnapshot


REVIEW_SESSION_BUNDLE = "REVIEW_SESSION_BUNDLE"
REVIEW_SESSION_BUNDLE_SCHEMA_VERSION = "1.0"
REVIEW_SESSION_BUNDLE_BOUNDARY_TEXT = (
    "note: not an execution instruction\n"
    "note: no authority granted"
)
_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "decision_created",
)


@dataclass(frozen=True)
class ReviewSessionBundle:
    bundle_id: str
    created_at_utc: str
    snapshot_count: int
    snapshot_hashes: tuple[str, ...]
    boundary_text: str
    bundle_hash: str
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    decision_created: bool = False
    object_type: str = REVIEW_SESSION_BUNDLE
    schema_version: str = REVIEW_SESSION_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        normalized_hashes = _normalize_snapshot_hashes(self.snapshot_hashes)
        object.__setattr__(self, "bundle_id", _required_text(self.bundle_id, "bundle_id"))
        object.__setattr__(
            self,
            "created_at_utc",
            _required_text(self.created_at_utc, "created_at_utc"),
        )
        object.__setattr__(self, "snapshot_count", len(normalized_hashes))
        object.__setattr__(self, "snapshot_hashes", normalized_hashes)
        object.__setattr__(self, "boundary_text", REVIEW_SESSION_BUNDLE_BOUNDARY_TEXT)
        object.__setattr__(self, "bundle_hash", _required_text(self.bundle_hash, "bundle_hash"))
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", REVIEW_SESSION_BUNDLE)
        object.__setattr__(self, "schema_version", REVIEW_SESSION_BUNDLE_SCHEMA_VERSION)

        expected_hash = _compute_bundle_hash(
            bundle_id=self.bundle_id,
            created_at_utc=self.created_at_utc,
            snapshot_hashes=normalized_hashes,
        )
        if self.bundle_hash != expected_hash:
            raise ValueError("bundle_hash verification failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "created_at_utc": self.created_at_utc,
            "snapshot_count": self.snapshot_count,
            "snapshot_hashes": list(self.snapshot_hashes),
            "boundary_text": self.boundary_text,
            "bundle_hash": self.bundle_hash,
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "decision_created": self.decision_created,
        }


def create_review_session_bundle(
    *,
    bundle_id: str,
    created_at_utc: str,
    snapshots: Sequence[ReviewSessionSnapshot],
) -> ReviewSessionBundle:
    normalized_id = _required_text(bundle_id, "bundle_id")
    normalized_timestamp = _required_text(created_at_utc, "created_at_utc")
    snapshot_hashes = _snapshot_hashes_from(snapshots)
    return ReviewSessionBundle(
        bundle_id=normalized_id,
        created_at_utc=normalized_timestamp,
        snapshot_count=len(snapshot_hashes),
        snapshot_hashes=snapshot_hashes,
        boundary_text=REVIEW_SESSION_BUNDLE_BOUNDARY_TEXT,
        bundle_hash=_compute_bundle_hash(
            bundle_id=normalized_id,
            created_at_utc=normalized_timestamp,
            snapshot_hashes=snapshot_hashes,
        ),
    )


def review_session_bundle_to_dict(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, ReviewSessionBundle):
        raise ValueError("bundle must be a ReviewSessionBundle")
    return bundle.to_dict()


def _snapshot_hashes_from(
    snapshots: Sequence[ReviewSessionSnapshot],
) -> tuple[str, ...]:
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        raise ValueError("snapshots must be a non-empty sequence")
    if len(snapshots) == 0:
        raise ValueError("snapshots must be a non-empty sequence")

    snapshot_hashes: list[str] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, ReviewSessionSnapshot):
            raise ValueError("snapshots must contain ReviewSessionSnapshot records")
        if any(getattr(snapshot, flag_name, None) is not False for flag_name in _INERT_FLAG_NAMES):
            raise ValueError("snapshots must be inert and authority-free")
        _verify_snapshot(snapshot)
        snapshot_hashes.append(_required_text(snapshot.snapshot_hash, "snapshot_hash"))
    return tuple(snapshot_hashes)


def _verify_snapshot(snapshot: ReviewSessionSnapshot) -> None:
    ReviewSessionSnapshot(
        snapshot_id=snapshot.snapshot_id,
        created_at_utc=snapshot.created_at_utc,
        source_milestone=snapshot.source_milestone,
        source_head=snapshot.source_head,
        review_surface_text=snapshot.review_surface_text,
        summary_fields=snapshot.summary_fields,
        snapshot_hash=snapshot.snapshot_hash,
    )


def _normalize_snapshot_hashes(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or len(value) == 0:
        raise ValueError("snapshot_hashes must be a non-empty tuple or list")
    return tuple(_required_text(item, "snapshot_hash") for item in value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if normalized == "":
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _compute_bundle_hash(
    *,
    bundle_id: str,
    created_at_utc: str,
    snapshot_hashes: object,
) -> str:
    normalized_hashes = _normalize_snapshot_hashes(snapshot_hashes)
    payload = {
        "object_type": REVIEW_SESSION_BUNDLE,
        "schema_version": REVIEW_SESSION_BUNDLE_SCHEMA_VERSION,
        "bundle_id": _required_text(bundle_id, "bundle_id"),
        "created_at_utc": _required_text(created_at_utc, "created_at_utc"),
        "snapshot_count": len(normalized_hashes),
        "snapshot_hashes": normalized_hashes,
        "boundary_text": REVIEW_SESSION_BUNDLE_BOUNDARY_TEXT,
        "authority_granted": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "provider_call_allowed": False,
        "artifact_write_allowed": False,
        "persistence_allowed": False,
        "decision_created": False,
    }
    semantic = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(semantic.encode("utf-8")).hexdigest()
