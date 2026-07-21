"""Deterministic, non-secret model profiles for user provider connections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from runtime.epistemic_orchestra.canonical import canonical_sha256, require_sha256
from runtime.providers.redaction import redact_provider_text


MODEL_PROFILE_SCHEMA_VERSION = "user-model-profile-1a"
SUPPORTED_ORCHESTRA_ROLES = ("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER")

_IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
_ROLE_ORDER = {role: index for index, role in enumerate(SUPPORTED_ORCHESTRA_ROLES)}
_MAX_TEXT_LENGTH = 512
_MAX_DECLARED_LIMIT = 10_000_000


class ModelProfileError(ValueError):
    """Raised when model-profile metadata is malformed or inconsistent."""


def normalize_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ModelProfileError(f"{field_name} must be a lowercase identifier")
    normalized = value.strip()
    if not _IDENTIFIER.fullmatch(normalized):
        raise ModelProfileError(f"{field_name} must be a lowercase identifier")
    if redact_provider_text(normalized) != normalized:
        raise ModelProfileError(f"{field_name} contains secret-like material")
    return normalized


def required_display_text(value: object, field_name: str, *, maximum: int = _MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        raise ModelProfileError(f"{field_name} must be non-empty text")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ModelProfileError(f"{field_name} must be non-empty text <= {maximum} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ModelProfileError(f"{field_name} contains forbidden control characters")
    if redact_provider_text(normalized) != normalized:
        raise ModelProfileError(f"{field_name} contains secret-like material")
    return normalized


def _normalize_roles(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ModelProfileError("allowed_roles must be a sequence")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ModelProfileError("allowed_roles must contain strings")
        role = value.strip().upper()
        if role not in _ROLE_ORDER:
            raise ModelProfileError("allowed_roles contains an unsupported role")
        normalized.append(role)
    if not normalized:
        raise ModelProfileError("allowed_roles must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ModelProfileError("allowed_roles contains duplicates")
    return tuple(sorted(normalized, key=_ROLE_ORDER.__getitem__))


def _optional_limit(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ModelProfileError(f"{field_name} must be a positive integer or null")
    if not 1 <= value <= _MAX_DECLARED_LIMIT:
        raise ModelProfileError(
            f"{field_name} must be between 1 and {_MAX_DECLARED_LIMIT} or null"
        )
    return value


@dataclass(frozen=True, slots=True)
class ModelProfile:
    model_profile_id: str
    connection_id: str
    display_name: str
    remote_model_id: str
    enabled: bool
    allowed_roles: tuple[str, ...]
    context_limit: int | None = None
    output_limit: int | None = None
    model_revision_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "model_profile_id",
            normalize_identifier(self.model_profile_id, "model_profile_id"),
        )
        object.__setattr__(
            self,
            "connection_id",
            normalize_identifier(self.connection_id, "connection_id"),
        )
        object.__setattr__(
            self,
            "display_name",
            required_display_text(self.display_name, "display_name", maximum=128),
        )
        object.__setattr__(
            self,
            "remote_model_id",
            required_display_text(self.remote_model_id, "remote_model_id", maximum=256),
        )
        if type(self.enabled) is not bool:
            raise ModelProfileError("enabled must be boolean")
        object.__setattr__(self, "allowed_roles", _normalize_roles(self.allowed_roles))
        object.__setattr__(
            self,
            "context_limit",
            _optional_limit(self.context_limit, "context_limit"),
        )
        object.__setattr__(
            self,
            "output_limit",
            _optional_limit(self.output_limit, "output_limit"),
        )
        expected = canonical_sha256(self.revision_material())
        if self.model_revision_hash:
            try:
                require_sha256("model_revision_hash", self.model_revision_hash)
            except ValueError as error:
                raise ModelProfileError(str(error)) from error
            if self.model_revision_hash != expected:
                raise ModelProfileError("model_revision_hash does not match canonical fields")
        object.__setattr__(self, "model_revision_hash", expected)

    def revision_material(self) -> dict[str, Any]:
        return {
            "schema_version": MODEL_PROFILE_SCHEMA_VERSION,
            "model_profile_id": self.model_profile_id,
            "connection_id": self.connection_id,
            "display_name": self.display_name,
            "remote_model_id": self.remote_model_id,
            "enabled": self.enabled,
            "allowed_roles": self.allowed_roles,
            "context_limit": self.context_limit,
            "output_limit": self.output_limit,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.revision_material()
        payload["allowed_roles"] = list(self.allowed_roles)
        return {**payload, "model_revision_hash": self.model_revision_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelProfile":
        if not isinstance(value, Mapping):
            raise ModelProfileError("model profile must be an object")
        expected = {
            "schema_version",
            "model_profile_id",
            "connection_id",
            "display_name",
            "remote_model_id",
            "enabled",
            "allowed_roles",
            "context_limit",
            "output_limit",
            "model_revision_hash",
        }
        if set(value) != expected:
            raise ModelProfileError("model profile fields differ")
        if value["schema_version"] != MODEL_PROFILE_SCHEMA_VERSION:
            raise ModelProfileError("model profile schema_version differs")
        roles = value["allowed_roles"]
        if not isinstance(roles, list):
            raise ModelProfileError("allowed_roles must be an array")
        return cls(
            model_profile_id=value["model_profile_id"],
            connection_id=value["connection_id"],
            display_name=value["display_name"],
            remote_model_id=value["remote_model_id"],
            enabled=value["enabled"],
            allowed_roles=tuple(roles),
            context_limit=value["context_limit"],
            output_limit=value["output_limit"],
            model_revision_hash=value["model_revision_hash"],
        )


__all__ = [
    "MODEL_PROFILE_SCHEMA_VERSION",
    "SUPPORTED_ORCHESTRA_ROLES",
    "ModelProfile",
    "ModelProfileError",
]
