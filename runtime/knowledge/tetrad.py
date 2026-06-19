from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


EVIDENCE = "evidence"
CONSTRAINT = "constraint"
CAPABILITY = "capability"
AUDIT = "audit"
FACE_TYPES = frozenset({EVIDENCE, CONSTRAINT, CAPABILITY, AUDIT})


class TrustLevel(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    HUMAN_PROVIDED = "HUMAN_PROVIDED"
    SYSTEM_INTERNAL = "SYSTEM_INTERNAL"


@dataclass(frozen=True)
class TetradFace:
    face_type: str
    content: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    trust_level: TrustLevel = TrustLevel.UNTRUSTED

    def __post_init__(self) -> None:
        normalized_type = _text("face_type", self.face_type).lower()
        if normalized_type not in FACE_TYPES:
            raise ValueError("face_type must be evidence, constraint, capability, or audit")
        object.__setattr__(self, "face_type", normalized_type)
        object.__setattr__(self, "content", _text_tuple("content", self.content))
        object.__setattr__(
            self,
            "source_refs",
            _text_tuple("source_refs", self.source_refs),
        )
        object.__setattr__(self, "trust_level", TrustLevel(self.trust_level))

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_type": self.face_type,
            "content": list(self.content),
            "source_refs": list(self.source_refs),
            "trust_level": self.trust_level.value,
        }


@dataclass(frozen=True)
class TetradCore:
    conflicts: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "conflicts", _text_tuple("conflicts", self.conflicts))
        object.__setattr__(
            self,
            "open_questions",
            _text_tuple("open_questions", self.open_questions),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflicts": list(self.conflicts),
            "open_questions": list(self.open_questions),
        }


@dataclass(frozen=True)
class TetradRecord:
    evidence: TetradFace | None = None
    constraint: TetradFace | None = None
    capability: TetradFace | None = None
    audit: TetradFace | None = None
    core: TetradCore = field(default_factory=TetradCore)
    created_at: str | None = None
    tetrad_id: str = field(init=False)
    read_only: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _face("evidence", self.evidence, EVIDENCE)
        _face("constraint", self.constraint, CONSTRAINT)
        _face("capability", self.capability, CAPABILITY)
        _face("audit", self.audit, AUDIT)
        if not isinstance(self.core, TetradCore):
            raise TypeError("core must be a TetradCore")
        normalized_created_at = (
            None if self.created_at is None else _text("created_at", self.created_at)
        )
        object.__setattr__(self, "created_at", normalized_created_at)
        object.__setattr__(
            self,
            "tetrad_id",
            compute_tetrad_id(
                evidence=self.evidence,
                constraint=self.constraint,
                capability=self.capability,
                audit=self.audit,
                core=self.core,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tetrad_id": self.tetrad_id,
            "evidence": self.evidence.to_dict() if self.evidence is not None else None,
            "constraint": (
                self.constraint.to_dict() if self.constraint is not None else None
            ),
            "capability": (
                self.capability.to_dict() if self.capability is not None else None
            ),
            "audit": self.audit.to_dict() if self.audit is not None else None,
            "core": self.core.to_dict(),
            "read_only": self.read_only,
            "created_at": self.created_at,
        }


def compute_tetrad_id(
    *,
    evidence: TetradFace | None = None,
    constraint: TetradFace | None = None,
    capability: TetradFace | None = None,
    audit: TetradFace | None = None,
    core: TetradCore | None = None,
) -> str:
    semantic_json = canonical_tetrad_json(
        evidence=evidence,
        constraint=constraint,
        capability=capability,
        audit=audit,
        core=TetradCore() if core is None else core,
    )
    return hashlib.sha256(semantic_json.encode("utf-8")).hexdigest()


def canonical_tetrad_json(
    *,
    evidence: TetradFace | None = None,
    constraint: TetradFace | None = None,
    capability: TetradFace | None = None,
    audit: TetradFace | None = None,
    core: TetradCore | None = None,
) -> str:
    normalized_core = TetradCore() if core is None else core
    _face("evidence", evidence, EVIDENCE)
    _face("constraint", constraint, CONSTRAINT)
    _face("capability", capability, CAPABILITY)
    _face("audit", audit, AUDIT)
    if not isinstance(normalized_core, TetradCore):
        raise TypeError("core must be a TetradCore")
    payload = {
        "audit": audit.to_dict() if audit is not None else None,
        "capability": capability.to_dict() if capability is not None else None,
        "constraint": constraint.to_dict() if constraint is not None else None,
        "core": normalized_core.to_dict(),
        "evidence": evidence.to_dict() if evidence is not None else None,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _face(name: str, value: TetradFace | None, expected_type: str) -> None:
    if value is None:
        return
    if not isinstance(value, TetradFace):
        raise TypeError(f"{name} must be a TetradFace or None")
    if value.face_type != expected_type:
        raise ValueError(f"{name} face must have face_type={expected_type}")


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _text_tuple(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of text values")
    try:
        return tuple(_text(name, value) for value in values)
    except TypeError:
        raise
