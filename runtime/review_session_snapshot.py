from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


REVIEW_SESSION_SNAPSHOT = "REVIEW_SESSION_SNAPSHOT"
REVIEW_SESSION_SNAPSHOT_SCHEMA_VERSION = "1.0"
_NOT_AN_EXECUTION_INSTRUCTION = "not an execution instruction"
_NO_AUTHORITY_GRANTED = "no authority granted"


@dataclass(frozen=True)
class ReviewSessionSnapshot:
    snapshot_id: str
    created_at_utc: str
    source_milestone: str
    source_head: str
    review_surface_text: str
    summary_fields: Mapping[str, bool | str]
    snapshot_hash: str
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    decision_created: bool = False
    object_type: str = REVIEW_SESSION_SNAPSHOT
    schema_version: str = REVIEW_SESSION_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        normalized_summary = _normalize_summary_fields(self.summary_fields)
        normalized_surface = _normalize_review_surface_text(self.review_surface_text)
        object.__setattr__(self, "snapshot_id", _required_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(
            self,
            "created_at_utc",
            _required_text(self.created_at_utc, "created_at_utc"),
        )
        object.__setattr__(
            self,
            "source_milestone",
            _required_text(self.source_milestone, "source_milestone"),
        )
        object.__setattr__(self, "source_head", _required_text(self.source_head, "source_head"))
        object.__setattr__(self, "review_surface_text", normalized_surface)
        object.__setattr__(self, "summary_fields", MappingProxyType(normalized_summary))
        object.__setattr__(self, "snapshot_hash", _required_text(self.snapshot_hash, "snapshot_hash"))
        object.__setattr__(self, "authority_granted", False)
        object.__setattr__(self, "execution_allowed", False)
        object.__setattr__(self, "dispatch_allowed", False)
        object.__setattr__(self, "provider_call_allowed", False)
        object.__setattr__(self, "artifact_write_allowed", False)
        object.__setattr__(self, "persistence_allowed", False)
        object.__setattr__(self, "decision_created", False)
        object.__setattr__(self, "object_type", REVIEW_SESSION_SNAPSHOT)
        object.__setattr__(
            self,
            "schema_version",
            REVIEW_SESSION_SNAPSHOT_SCHEMA_VERSION,
        )
        expected_hash = _compute_snapshot_hash(
            snapshot_id=self.snapshot_id,
            created_at_utc=self.created_at_utc,
            source_milestone=self.source_milestone,
            source_head=self.source_head,
            review_surface_text=self.review_surface_text,
            summary_fields=normalized_summary,
        )
        if self.snapshot_hash != expected_hash:
            raise ValueError("snapshot_hash verification failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "created_at_utc": self.created_at_utc,
            "source_milestone": self.source_milestone,
            "source_head": self.source_head,
            "review_surface_text": self.review_surface_text,
            "summary_fields": dict(self.summary_fields),
            "snapshot_hash": self.snapshot_hash,
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "decision_created": self.decision_created,
        }


def create_review_session_snapshot(
    *,
    snapshot_id: str,
    created_at_utc: str,
    source_milestone: str,
    source_head: str,
    review_surface_text: str,
    summary_fields: Mapping[str, bool | str],
) -> ReviewSessionSnapshot:
    normalized_summary = _normalize_summary_fields(summary_fields)
    normalized_surface = _normalize_review_surface_text(review_surface_text)
    return ReviewSessionSnapshot(
        snapshot_id=_required_text(snapshot_id, "snapshot_id"),
        created_at_utc=_required_text(created_at_utc, "created_at_utc"),
        source_milestone=_required_text(source_milestone, "source_milestone"),
        source_head=_required_text(source_head, "source_head"),
        review_surface_text=normalized_surface,
        summary_fields=normalized_summary,
        snapshot_hash=_compute_snapshot_hash(
            snapshot_id=snapshot_id,
            created_at_utc=created_at_utc,
            source_milestone=source_milestone,
            source_head=source_head,
            review_surface_text=normalized_surface,
            summary_fields=normalized_summary,
        ),
    )


def snapshot_to_dict(snapshot: object) -> dict[str, Any]:
    if not isinstance(snapshot, ReviewSessionSnapshot):
        raise ValueError("snapshot must be a ReviewSessionSnapshot")
    return snapshot.to_dict()


def _normalize_summary_fields(value: Mapping[str, bool | str]) -> dict[str, bool | str]:
    if not isinstance(value, Mapping):
        raise ValueError("summary_fields must be a mapping")
    normalized: dict[str, bool | str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key.strip() == "":
            raise ValueError("summary_fields keys must be non-empty strings")
        if isinstance(item, bool):
            normalized[key] = item
            continue
        if isinstance(item, str) and item.strip() != "":
            normalized[key] = item
            continue
        raise ValueError("summary_fields values must be bool or non-empty str")
    return normalized


def _normalize_review_surface_text(value: str) -> str:
    normalized = _required_text(value, "review_surface_text")
    if _NOT_AN_EXECUTION_INSTRUCTION not in normalized.lower():
        normalized = f"{normalized}\nnote: {_NOT_AN_EXECUTION_INSTRUCTION}"
    if _NO_AUTHORITY_GRANTED not in normalized.lower():
        normalized = f"{normalized}\nnote: {_NO_AUTHORITY_GRANTED}"
    return normalized


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if normalized == "":
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _compute_snapshot_hash(
    *,
    snapshot_id: str,
    created_at_utc: str,
    source_milestone: str,
    source_head: str,
    review_surface_text: str,
    summary_fields: Mapping[str, bool | str],
) -> str:
    payload = {
        "object_type": REVIEW_SESSION_SNAPSHOT,
        "schema_version": REVIEW_SESSION_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": _required_text(snapshot_id, "snapshot_id"),
        "created_at_utc": _required_text(created_at_utc, "created_at_utc"),
        "source_milestone": _required_text(source_milestone, "source_milestone"),
        "source_head": _required_text(source_head, "source_head"),
        "review_surface_text": _normalize_review_surface_text(review_surface_text),
        "summary_fields": _normalize_summary_fields(summary_fields),
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
