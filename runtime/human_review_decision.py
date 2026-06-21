from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from runtime.review_session_bundle import ReviewSessionBundle


HUMAN_REVIEW_DECISION = "HUMAN_REVIEW_DECISION"
HUMAN_REVIEW_DECISION_SCHEMA_VERSION = "1.0"
APPROVE_FOR_NEXT_REVIEW_STEP = "APPROVE_FOR_NEXT_REVIEW_STEP"
REJECT = "REJECT"
NEEDS_CHANGES = "NEEDS_CHANGES"
ALLOWED_DECISION_STATUSES = (
    APPROVE_FOR_NEXT_REVIEW_STEP,
    REJECT,
    NEEDS_CHANGES,
)
HUMAN_REVIEW_DECISION_BOUNDARY_TEXT = (
    "note: not an execution instruction\n"
    "note: no authority granted"
)
_DECISION_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "decision_executes_anything",
)
_BUNDLE_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "decision_created",
)


@dataclass(frozen=True)
class HumanReviewDecision:
    decision_id: str
    created_at_utc: str
    bundle_id: str
    bundle_hash: str
    decision_status: str
    human_note: str
    boundary_text: str
    decision_hash: str
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    decision_executes_anything: bool = False
    object_type: str = HUMAN_REVIEW_DECISION
    schema_version: str = HUMAN_REVIEW_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _required_text(self.decision_id, "decision_id"))
        object.__setattr__(
            self,
            "created_at_utc",
            _required_text(self.created_at_utc, "created_at_utc"),
        )
        object.__setattr__(self, "bundle_id", _required_text(self.bundle_id, "bundle_id"))
        object.__setattr__(self, "bundle_hash", _required_hash(self.bundle_hash, "bundle_hash"))
        object.__setattr__(
            self,
            "decision_status",
            _normalize_decision_status(self.decision_status),
        )
        object.__setattr__(self, "human_note", _normalize_human_note(self.human_note))
        object.__setattr__(self, "boundary_text", HUMAN_REVIEW_DECISION_BOUNDARY_TEXT)
        object.__setattr__(
            self,
            "decision_hash",
            _required_hash(self.decision_hash, "decision_hash"),
        )
        for flag_name in _DECISION_INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", HUMAN_REVIEW_DECISION)
        object.__setattr__(self, "schema_version", HUMAN_REVIEW_DECISION_SCHEMA_VERSION)

        expected_hash = _compute_decision_hash(
            decision_id=self.decision_id,
            created_at_utc=self.created_at_utc,
            bundle_id=self.bundle_id,
            bundle_hash=self.bundle_hash,
            decision_status=self.decision_status,
            human_note=self.human_note,
        )
        if self.decision_hash != expected_hash:
            raise ValueError("decision_hash verification failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "created_at_utc": self.created_at_utc,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "decision_status": self.decision_status,
            "human_note": self.human_note,
            "boundary_text": self.boundary_text,
            "decision_hash": self.decision_hash,
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "decision_executes_anything": self.decision_executes_anything,
        }


def create_human_review_decision(
    *,
    decision_id: str,
    created_at_utc: str,
    bundle: ReviewSessionBundle,
    decision_status: str,
    human_note: str = "",
) -> HumanReviewDecision:
    _verify_bundle(bundle)
    normalized_id = _required_text(decision_id, "decision_id")
    normalized_timestamp = _required_text(created_at_utc, "created_at_utc")
    normalized_status = _normalize_decision_status(decision_status)
    normalized_note = _normalize_human_note(human_note)
    return HumanReviewDecision(
        decision_id=normalized_id,
        created_at_utc=normalized_timestamp,
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        decision_status=normalized_status,
        human_note=normalized_note,
        boundary_text=HUMAN_REVIEW_DECISION_BOUNDARY_TEXT,
        decision_hash=_compute_decision_hash(
            decision_id=normalized_id,
            created_at_utc=normalized_timestamp,
            bundle_id=bundle.bundle_id,
            bundle_hash=bundle.bundle_hash,
            decision_status=normalized_status,
            human_note=normalized_note,
        ),
    )


def human_review_decision_to_dict(decision: object) -> dict[str, Any]:
    if not isinstance(decision, HumanReviewDecision):
        raise ValueError("decision must be a HumanReviewDecision")
    return decision.to_dict()


def _verify_bundle(bundle: object) -> None:
    if not isinstance(bundle, ReviewSessionBundle):
        raise ValueError("bundle must be a ReviewSessionBundle")
    if any(getattr(bundle, flag_name, None) is not False for flag_name in _BUNDLE_INERT_FLAG_NAMES):
        raise ValueError("bundle must be inert and authority-free")
    ReviewSessionBundle(
        bundle_id=bundle.bundle_id,
        created_at_utc=bundle.created_at_utc,
        snapshot_count=bundle.snapshot_count,
        snapshot_hashes=bundle.snapshot_hashes,
        boundary_text=bundle.boundary_text,
        bundle_hash=bundle.bundle_hash,
    )


def _normalize_decision_status(value: object) -> str:
    if not isinstance(value, str) or value not in ALLOWED_DECISION_STATUSES:
        raise ValueError("decision_status must be an allowed inert review status")
    return value


def _normalize_human_note(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("human_note must be a string")
    return value.strip()


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if normalized == "":
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _required_hash(value: object, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hash")
    return normalized


def _compute_decision_hash(
    *,
    decision_id: str,
    created_at_utc: str,
    bundle_id: str,
    bundle_hash: str,
    decision_status: str,
    human_note: str,
) -> str:
    payload = {
        "object_type": HUMAN_REVIEW_DECISION,
        "schema_version": HUMAN_REVIEW_DECISION_SCHEMA_VERSION,
        "decision_id": _required_text(decision_id, "decision_id"),
        "created_at_utc": _required_text(created_at_utc, "created_at_utc"),
        "bundle_id": _required_text(bundle_id, "bundle_id"),
        "bundle_hash": _required_hash(bundle_hash, "bundle_hash"),
        "decision_status": _normalize_decision_status(decision_status),
        "human_note": _normalize_human_note(human_note),
        "boundary_text": HUMAN_REVIEW_DECISION_BOUNDARY_TEXT,
        "authority_granted": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "provider_call_allowed": False,
        "artifact_write_allowed": False,
        "persistence_allowed": False,
        "decision_executes_anything": False,
    }
    semantic = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(semantic.encode("utf-8")).hexdigest()
