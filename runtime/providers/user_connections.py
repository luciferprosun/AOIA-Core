"""User-controlled provider metadata and external credential storage.

Normal configuration contains credential references only. Secret values are
kept in a separate, permission-restricted directory and are never serialized
or included in revision hashes.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from runtime.epistemic_orchestra.canonical import canonical_sha256, require_sha256
from runtime.providers.model_profiles import (
    MODEL_PROFILE_SCHEMA_VERSION,
    ModelProfile,
    ModelProfileError,
    normalize_identifier,
    required_display_text,
)
from runtime.providers.redaction import redact_provider_text
from runtime.runtime_paths import runtime_state_dir


PROVIDER_CONNECTION_SCHEMA_VERSION = "user-provider-connection-1a"
PROVIDER_STORE_SCHEMA_VERSION = "user-provider-store-1a"
SUPPORTED_API_STYLES = ("openai_compatible",)
REVIEWED_NATIVE_ADAPTER_IDS: tuple[str, ...] = ()
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_MAX_CONFIG_BYTES = 5_000_000
_MAX_SECRET_BYTES = 16_384
_RESERVED_MASKED_OUTPUT_LITERALS = frozenset(
    {
        "configured",
        "disabled",
        "enabled",
        "failure",
        "[MASKED]",
        "NON_AUTHORITATIVE",
        "not tested",
        "[REDACTED]",
        "[REDACTED_PROVIDER_SECRET]",
        "success",
        "UNTRUSTED",
    }
)


class UserProviderStoreError(ValueError):
    """Raised when provider configuration or credential evidence is unsafe."""


def _required_text(value: object, field_name: str, *, maximum: int) -> str:
    try:
        return required_display_text(value, field_name, maximum=maximum)
    except ModelProfileError as error:
        raise UserProviderStoreError(str(error)) from error


def _normalize_reference(value: object) -> str:
    try:
        return normalize_identifier(value, "credential_reference")
    except ModelProfileError as error:
        raise UserProviderStoreError(str(error)) from error


def normalize_base_url(value: object) -> str:
    if not isinstance(value, str):
        raise UserProviderStoreError("base_url must be an HTTPS URL")
    candidate = value.strip()
    if not candidate or len(candidate) > 2048:
        raise UserProviderStoreError("base_url must be an HTTPS URL")
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in candidate):
        raise UserProviderStoreError("base_url contains unsafe text")
    if redact_provider_text(candidate) != candidate:
        raise UserProviderStoreError("base_url contains secret-like material")
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as error:
        raise UserProviderStoreError("base_url is malformed") from error
    if parsed.scheme.casefold() != "https" or not parsed.netloc or not parsed.hostname:
        raise UserProviderStoreError("base_url must use HTTPS and include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise UserProviderStoreError("base_url cannot contain credentials")
    if parsed.query or parsed.fragment:
        raise UserProviderStoreError("base_url cannot contain a query or fragment")
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host if port is None else f"{host}:{port}"
    path = parsed.path.rstrip("/")
    if path.casefold().endswith("/chat/completions"):
        raise UserProviderStoreError("base_url must not include the chat-completions resource")
    return urlunsplit(("https", netloc, path, "", ""))


@dataclass(frozen=True, slots=True)
class ProviderConnection:
    connection_id: str
    display_name: str
    api_style: str
    base_url: str | None
    native_adapter_id: str | None
    credential_reference: str
    enabled: bool
    created_at: str
    connection_revision_hash: str = ""

    def __post_init__(self) -> None:
        try:
            connection_id = normalize_identifier(self.connection_id, "connection_id")
        except ModelProfileError as error:
            raise UserProviderStoreError(str(error)) from error
        object.__setattr__(self, "connection_id", connection_id)
        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name", maximum=128),
        )
        if not isinstance(self.api_style, str) or self.api_style not in SUPPORTED_API_STYLES:
            raise UserProviderStoreError("api_style is unsupported")
        if self.api_style == "openai_compatible":
            object.__setattr__(self, "base_url", normalize_base_url(self.base_url))
            if self.native_adapter_id is not None:
                raise UserProviderStoreError(
                    "openai_compatible connections cannot select a native adapter"
                )
        object.__setattr__(
            self,
            "credential_reference",
            _normalize_reference(self.credential_reference),
        )
        if type(self.enabled) is not bool:
            raise UserProviderStoreError("enabled must be boolean")
        object.__setattr__(
            self,
            "created_at",
            _required_text(self.created_at, "created_at", maximum=128),
        )
        expected = canonical_sha256(self.revision_material())
        if self.connection_revision_hash:
            try:
                require_sha256("connection_revision_hash", self.connection_revision_hash)
            except ValueError as error:
                raise UserProviderStoreError(str(error)) from error
            if self.connection_revision_hash != expected:
                raise UserProviderStoreError(
                    "connection_revision_hash does not match canonical fields"
                )
        object.__setattr__(self, "connection_revision_hash", expected)

    def revision_material(self) -> dict[str, Any]:
        return {
            "schema_version": PROVIDER_CONNECTION_SCHEMA_VERSION,
            "connection_id": self.connection_id,
            "display_name": self.display_name,
            "api_style": self.api_style,
            "base_url": self.base_url,
            "native_adapter_id": self.native_adapter_id,
            "credential_reference": self.credential_reference,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.revision_material(),
            "connection_revision_hash": self.connection_revision_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderConnection":
        if not isinstance(value, Mapping):
            raise UserProviderStoreError("provider connection must be an object")
        expected = {
            "schema_version",
            "connection_id",
            "display_name",
            "api_style",
            "base_url",
            "native_adapter_id",
            "credential_reference",
            "enabled",
            "created_at",
            "connection_revision_hash",
        }
        if set(value) != expected:
            raise UserProviderStoreError("provider connection fields differ")
        if value["schema_version"] != PROVIDER_CONNECTION_SCHEMA_VERSION:
            raise UserProviderStoreError("provider connection schema_version differs")
        return cls(
            connection_id=value["connection_id"],
            display_name=value["display_name"],
            api_style=value["api_style"],
            base_url=value["base_url"],
            native_adapter_id=value["native_adapter_id"],
            credential_reference=value["credential_reference"],
            enabled=value["enabled"],
            created_at=value["created_at"],
            connection_revision_hash=value["connection_revision_hash"],
        )


class UserProviderStore:
    """Hot-reloaded user connection/model metadata plus external credentials."""

    def __init__(
        self,
        project_dir: Path,
        state_root: Path | None = None,
        secrets_root: Path | None = None,
    ) -> None:
        if not isinstance(project_dir, Path):
            project_dir = Path(project_dir)
        self.project_dir = project_dir
        self.state_root = (
            Path(state_root)
            if state_root is not None
            else runtime_state_dir(project_dir) / "state"
        )
        self.config_path = self.state_root / "provider_connections_1a.json"
        self.secrets_root = (
            Path(secrets_root).expanduser()
            if secrets_root is not None
            else Path.home() / ".config" / "aoia" / "secrets" / "provider-connections"
        )
        self._assert_secrets_root_outside_project()
        self.lock_path = self.state_root / ".provider_connections_1a.lock"

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        """Serialize metadata+credential mutations across services/processes."""

        self._ensure_directory(self.state_root, mode=0o700)
        if self.lock_path.is_symlink() or (
            self.lock_path.exists() and not self.lock_path.is_file()
        ):
            raise UserProviderStoreError("provider store lock must be a regular file")
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = -1
        try:
            descriptor = os.open(self.lock_path, flags, 0o600)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise UserProviderStoreError(
                    "provider store lock must be a single-link regular file"
                )
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except OSError as error:
            raise UserProviderStoreError("provider store lock could not be acquired") from error
        finally:
            if descriptor >= 0:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def create_connection(
        self,
        *,
        connection_id: str,
        display_name: str,
        api_style: str,
        base_url: str | None = None,
        native_adapter_id: str | None = None,
        credential_reference: str,
        enabled: bool = True,
        created_at: str,
        api_key: str | None = None,
    ) -> ProviderConnection:
        with self._mutation_lock():
            return self._create_connection_unlocked(
                connection_id=connection_id,
                display_name=display_name,
                api_style=api_style,
                base_url=base_url,
                native_adapter_id=native_adapter_id,
                credential_reference=credential_reference,
                enabled=enabled,
                created_at=created_at,
                api_key=api_key,
            )

    def _create_connection_unlocked(
        self,
        *,
        connection_id: str,
        display_name: str,
        api_style: str,
        base_url: str | None = None,
        native_adapter_id: str | None = None,
        credential_reference: str,
        enabled: bool = True,
        created_at: str,
        api_key: str | None = None,
    ) -> ProviderConnection:
        connections, profiles = self._load()
        reference = _normalize_reference(credential_reference)
        candidate_secrets = list(self._configured_credentials(connections))
        target_credential_path = self._credential_path(reference)
        if target_credential_path.exists() or target_credential_path.is_symlink():
            candidate_secrets.append(self.read_credential(reference))
        normalized_api_key: str | None = None
        if api_key is not None:
            normalized_api_key = self._normalize_secret(api_key)
            candidate_secrets.append(normalized_api_key)
        # Reject secret equivalence before ProviderConnection computes its
        # revision hash. Secret material must never even transiently become
        # canonical hash input.
        self._reject_secret_equivalence(
            tuple(
                value if isinstance(value, str) else None
                for value in (
                    connection_id,
                    display_name,
                    api_style,
                    base_url,
                    native_adapter_id,
                    reference,
                    created_at,
                )
            ),
            tuple(candidate_secrets),
        )
        self._reject_persisted_payload_secret_equivalence(
            {
                "schema_version": PROVIDER_CONNECTION_SCHEMA_VERSION,
                "connection_id": connection_id,
                "display_name": display_name,
                "api_style": api_style,
                "base_url": base_url,
                "native_adapter_id": native_adapter_id,
                "credential_reference": reference,
                "enabled": enabled,
                "created_at": created_at,
            },
            tuple(candidate_secrets),
        )
        connection = ProviderConnection(
            connection_id=connection_id,
            display_name=display_name,
            api_style=api_style,
            base_url=base_url,
            native_adapter_id=native_adapter_id,
            credential_reference=reference,
            enabled=enabled,
            created_at=created_at,
        )
        if any(item.connection_id == connection.connection_id for item in connections):
            raise UserProviderStoreError("duplicate connection_id")
        if any(
            item.credential_reference == connection.credential_reference
            for item in connections
        ):
            raise UserProviderStoreError("duplicate credential_reference")
        self._reject_connection_secret_equivalence(
            connection,
            tuple(candidate_secrets),
        )
        self._reject_persisted_payload_secret_equivalence(
            self._store_payload((*connections, connection), profiles),
            tuple(candidate_secrets),
        )
        if normalized_api_key is not None:
            self._save_credential_unlocked(
                connection.credential_reference,
                normalized_api_key,
            )
        self._write((*connections, connection), profiles)
        return connection

    def list_connections(self) -> tuple[ProviderConnection, ...]:
        connections, _profiles = self._load()
        return connections

    def get_connection(self, connection_id: str) -> ProviderConnection:
        normalized = self._connection_id(connection_id)
        connections, _profiles = self._load()
        for connection in connections:
            if connection.connection_id == normalized:
                return connection
        raise UserProviderStoreError("unknown connection_id")

    def disable_connection(self, connection_id: str) -> ProviderConnection:
        with self._mutation_lock():
            return self._disable_connection_unlocked(connection_id)

    def _disable_connection_unlocked(self, connection_id: str) -> ProviderConnection:
        normalized = self._connection_id(connection_id)
        connections, profiles = self._load()
        updated: list[ProviderConnection] = []
        result: ProviderConnection | None = None
        for connection in connections:
            if connection.connection_id == normalized:
                result = replace(connection, enabled=False, connection_revision_hash="")
                updated.append(result)
            else:
                updated.append(connection)
        if result is None:
            raise UserProviderStoreError("unknown connection_id")
        self._write(tuple(updated), profiles)
        return result

    def save_credential(self, credential_reference: str, api_key: str) -> str:
        with self._mutation_lock():
            return self._save_credential_unlocked(credential_reference, api_key)

    def _save_credential_unlocked(
        self,
        credential_reference: str,
        api_key: str,
    ) -> str:
        reference = _normalize_reference(credential_reference)
        secret = self._normalize_secret(api_key)
        connections, profiles = self._load()
        for connection in connections:
            self._reject_connection_secret_equivalence(connection, (secret,))
        for profile in profiles:
            self._reject_model_secret_equivalence(profile, (secret,))
        self._reject_persisted_payload_secret_equivalence(
            self._store_payload(connections, profiles),
            (secret,),
        )
        self._ensure_directory(self.secrets_root, mode=0o700)
        path = self._credential_path(reference)
        self._write_atomic_regular_file(path, secret.encode("utf-8"), mode=0o600)
        return "configured"

    def read_credential(self, credential_reference: str) -> str:
        reference = _normalize_reference(credential_reference)
        path = self._credential_path(reference)
        if not path.exists():
            raise UserProviderStoreError("credential is missing")
        payload = self._read_regular_file(
            path,
            maximum_bytes=_MAX_SECRET_BYTES,
            require_private_mode=True,
        )
        try:
            secret = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise UserProviderStoreError("credential is malformed") from error
        return self._normalize_secret(secret)

    def credential_status(self, credential_reference: str) -> str:
        reference = _normalize_reference(credential_reference)
        path = self._credential_path(reference)
        if not path.exists():
            return "missing"
        self.read_credential(reference)
        return "configured"

    def assert_text_excludes_configured_credentials(
        self,
        value: str,
        *,
        connection_ids: Sequence[str] | None = None,
    ) -> None:
        """Reject text containing configured key material without exposing it."""

        if not isinstance(value, str):
            raise UserProviderStoreError("credential-adjacent text must be a string")
        connections, _profiles = self._load()
        if connection_ids is not None:
            selected = {self._connection_id(item) for item in connection_ids}
            connections = tuple(
                connection for connection in connections if connection.connection_id in selected
            )
            if {item.connection_id for item in connections} != selected:
                raise UserProviderStoreError("selected provider connection is missing")
        self._reject_secret_equivalence(
            (value,),
            self._configured_credentials(connections),
        )

    def redact_configured_credentials(self, value: object) -> str:
        """Redact every configured user credential without returning raw key data."""

        connections, _profiles = self._load()
        return redact_provider_text(
            value,
            known_secrets=self._configured_credentials(connections),
        )

    def assert_payload_excludes_configured_credentials(self, value: object) -> None:
        """Reject configured credential material in structured evidence."""

        connections, _profiles = self._load()
        self._reject_persisted_payload_secret_equivalence(
            value,
            self._configured_credentials(connections),
        )

    def create_model_profile(
        self,
        *,
        model_profile_id: str,
        connection_id: str,
        display_name: str,
        remote_model_id: str,
        enabled: bool = True,
        allowed_roles: Sequence[str],
        context_limit: int | None = None,
        output_limit: int | None = None,
    ) -> ModelProfile:
        with self._mutation_lock():
            return self._create_model_profile_unlocked(
                model_profile_id=model_profile_id,
                connection_id=connection_id,
                display_name=display_name,
                remote_model_id=remote_model_id,
                enabled=enabled,
                allowed_roles=allowed_roles,
                context_limit=context_limit,
                output_limit=output_limit,
            )

    def _create_model_profile_unlocked(
        self,
        *,
        model_profile_id: str,
        connection_id: str,
        display_name: str,
        remote_model_id: str,
        enabled: bool = True,
        allowed_roles: Sequence[str],
        context_limit: int | None = None,
        output_limit: int | None = None,
    ) -> ModelProfile:
        connections, profiles = self._load()
        configured_credentials = self._configured_credentials(connections)
        raw_roles = (
            tuple(allowed_roles)
            if not isinstance(allowed_roles, (str, bytes))
            and isinstance(allowed_roles, Sequence)
            else (allowed_roles,)
        )
        self._reject_secret_equivalence(
            tuple(
                value if isinstance(value, str) else None
                for value in (
                    model_profile_id,
                    connection_id,
                    display_name,
                    remote_model_id,
                    *raw_roles,
                )
            ),
            configured_credentials,
        )
        self._reject_persisted_payload_secret_equivalence(
            {
                "schema_version": MODEL_PROFILE_SCHEMA_VERSION,
                "model_profile_id": model_profile_id,
                "connection_id": connection_id,
                "display_name": display_name,
                "remote_model_id": remote_model_id,
                "enabled": enabled,
                "allowed_roles": raw_roles,
                "context_limit": context_limit,
                "output_limit": output_limit,
            },
            configured_credentials,
        )
        profile = ModelProfile(
            model_profile_id=model_profile_id,
            connection_id=connection_id,
            display_name=display_name,
            remote_model_id=remote_model_id,
            enabled=enabled,
            allowed_roles=tuple(allowed_roles),
            context_limit=context_limit,
            output_limit=output_limit,
        )
        if not any(item.connection_id == profile.connection_id for item in connections):
            raise UserProviderStoreError("model profile references an unknown connection")
        if any(item.model_profile_id == profile.model_profile_id for item in profiles):
            raise UserProviderStoreError("duplicate model_profile_id")
        self._reject_model_secret_equivalence(
            profile,
            configured_credentials,
        )
        self._reject_persisted_payload_secret_equivalence(
            self._store_payload(connections, (*profiles, profile)),
            configured_credentials,
        )
        self._write(connections, (*profiles, profile))
        return profile

    def list_model_profiles(self, connection_id: str | None = None) -> tuple[ModelProfile, ...]:
        _connections, profiles = self._load()
        if connection_id is None:
            return profiles
        normalized = self._connection_id(connection_id)
        return tuple(item for item in profiles if item.connection_id == normalized)

    def get_model_profile(self, model_profile_id: str) -> ModelProfile:
        normalized = self._model_profile_id(model_profile_id)
        _connections, profiles = self._load()
        for profile in profiles:
            if profile.model_profile_id == normalized:
                return profile
        raise UserProviderStoreError("unknown model_profile_id")

    def disable_model_profile(self, model_profile_id: str) -> ModelProfile:
        with self._mutation_lock():
            return self._disable_model_profile_unlocked(model_profile_id)

    def _disable_model_profile_unlocked(self, model_profile_id: str) -> ModelProfile:
        normalized = self._model_profile_id(model_profile_id)
        connections, profiles = self._load()
        updated: list[ModelProfile] = []
        result: ModelProfile | None = None
        for profile in profiles:
            if profile.model_profile_id == normalized:
                result = replace(profile, enabled=False, model_revision_hash="")
                updated.append(result)
            else:
                updated.append(profile)
        if result is None:
            raise UserProviderStoreError("unknown model_profile_id")
        self._write(connections, tuple(updated))
        return result

    def _load(self) -> tuple[tuple[ProviderConnection, ...], tuple[ModelProfile, ...]]:
        if not self.config_path.exists():
            return (), ()
        payload = self._read_regular_file(
            self.config_path,
            maximum_bytes=_MAX_CONFIG_BYTES,
            require_private_mode=False,
        )
        try:
            value = json.loads(
                payload.decode("utf-8", errors="strict"),
                object_pairs_hook=self._strict_object,
                parse_constant=self._reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise UserProviderStoreError("provider configuration is malformed") from error
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "connections",
            "model_profiles",
        }:
            raise UserProviderStoreError("provider configuration fields differ")
        if value["schema_version"] != PROVIDER_STORE_SCHEMA_VERSION:
            raise UserProviderStoreError("provider configuration schema_version differs")
        if not isinstance(value["connections"], list) or not isinstance(
            value["model_profiles"], list
        ):
            raise UserProviderStoreError("provider configuration arrays are malformed")
        try:
            connections = tuple(ProviderConnection.from_dict(item) for item in value["connections"])
            profiles = tuple(ModelProfile.from_dict(item) for item in value["model_profiles"])
        except (ModelProfileError, UserProviderStoreError) as error:
            raise UserProviderStoreError(str(error)) from error
        connection_ids = tuple(item.connection_id for item in connections)
        credential_references = tuple(item.credential_reference for item in connections)
        profile_ids = tuple(item.model_profile_id for item in profiles)
        if len(connection_ids) != len(set(connection_ids)):
            raise UserProviderStoreError("provider configuration has duplicate connection IDs")
        if len(credential_references) != len(set(credential_references)):
            raise UserProviderStoreError(
                "provider configuration has duplicate credential references"
            )
        if len(profile_ids) != len(set(profile_ids)):
            raise UserProviderStoreError("provider configuration has duplicate model-profile IDs")
        known_connections = set(connection_ids)
        if any(item.connection_id not in known_connections for item in profiles):
            raise UserProviderStoreError("provider configuration has an orphan model profile")
        if connections != tuple(sorted(connections, key=lambda item: item.connection_id)):
            raise UserProviderStoreError("provider connections are not in canonical order")
        if profiles != tuple(sorted(profiles, key=lambda item: item.model_profile_id)):
            raise UserProviderStoreError("model profiles are not in canonical order")
        configured_credentials = self._configured_credentials(connections)
        self._reject_persisted_payload_secret_equivalence(
            value,
            configured_credentials,
        )
        for connection in connections:
            self._reject_connection_secret_equivalence(
                connection,
                configured_credentials,
            )
        for profile in profiles:
            self._reject_model_secret_equivalence(profile, configured_credentials)
        return connections, profiles

    def _write(
        self,
        connections: Sequence[ProviderConnection],
        profiles: Sequence[ModelProfile],
    ) -> None:
        ordered_connections = tuple(sorted(connections, key=lambda item: item.connection_id))
        ordered_profiles = tuple(sorted(profiles, key=lambda item: item.model_profile_id))
        payload = self._store_payload(ordered_connections, ordered_profiles)
        self._reject_persisted_payload_secret_equivalence(
            payload,
            self._configured_credentials(ordered_connections),
        )
        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        self._ensure_directory(self.state_root, mode=0o700)
        self._write_atomic_regular_file(self.config_path, encoded, mode=0o600)

    @classmethod
    def _write_atomic_regular_file(cls, path: Path, payload: bytes, *, mode: int) -> None:
        """Atomically publish canonical metadata so readers never see truncation."""

        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise UserProviderStoreError("storage file must be a regular non-symlink file")
        descriptor = -1
        temporary_path: str | None = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
            )
            os.fchmod(descriptor, mode)
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise UserProviderStoreError("storage file write was incomplete")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.replace(temporary_path, path)
            temporary_path = None
        except OSError as error:
            raise UserProviderStoreError("storage file could not be written safely") from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    @staticmethod
    def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise UserProviderStoreError("provider configuration contains duplicate JSON keys")
            result[key] = value
        return result

    @staticmethod
    def _reject_json_constant(value: str) -> None:
        raise UserProviderStoreError(f"non-finite JSON value is forbidden: {value}")

    @staticmethod
    def _ensure_directory(path: Path, *, mode: int) -> None:
        if path.is_symlink():
            raise UserProviderStoreError("storage directory cannot be a symlink")
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        if path.is_symlink() or not path.is_dir():
            raise UserProviderStoreError("storage directory must be a regular directory")
        path.chmod(mode)

    @staticmethod
    def _read_regular_file(
        path: Path,
        *,
        maximum_bytes: int,
        require_private_mode: bool,
    ) -> bytes:
        try:
            if path.is_symlink() or not path.is_file():
                raise UserProviderStoreError("storage file must be a regular non-symlink file")
            flags = os.O_RDONLY
            flags |= getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
        except OSError as error:
            raise UserProviderStoreError("storage file could not be opened safely") from error
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise UserProviderStoreError("storage file must be a regular file")
            if require_private_mode:
                if metadata.st_nlink != 1 or metadata.st_uid != os.getuid():
                    raise UserProviderStoreError(
                        "credential file ownership or link count is unsafe"
                    )
                permissions = stat.S_IMODE(metadata.st_mode)
                if permissions & 0o077 or not permissions & stat.S_IRUSR:
                    raise UserProviderStoreError("credential file permissions are unsafe")
            if metadata.st_size > maximum_bytes:
                raise UserProviderStoreError("storage file exceeds the bounded size")
            payload = os.read(descriptor, maximum_bytes + 1)
            if len(payload) > maximum_bytes:
                raise UserProviderStoreError("storage file exceeds the bounded size")
            return payload
        except OSError as error:
            raise UserProviderStoreError("storage file could not be read safely") from error
        finally:
            os.close(descriptor)

    def _credential_path(self, credential_reference: str) -> Path:
        self._assert_secrets_root_outside_project()
        return self.secrets_root / f"{credential_reference}.key"

    def _assert_secrets_root_outside_project(self) -> None:
        try:
            project_lexical = self.project_dir.expanduser().absolute()
            secrets_lexical = self.secrets_root.expanduser().absolute()
            project_resolved = self.project_dir.expanduser().resolve(strict=False)
            secrets_resolved = self.secrets_root.expanduser().resolve(strict=False)
        except (OSError, RuntimeError) as error:
            raise UserProviderStoreError(
                "credential storage location cannot be resolved safely"
            ) from error
        for project, secrets in (
            (project_lexical, secrets_lexical),
            (project_resolved, secrets_resolved),
        ):
            if secrets == project or project in secrets.parents:
                raise UserProviderStoreError(
                    "credential storage must remain outside the project repository"
                )

    def _configured_credentials(
        self,
        connections: Sequence[ProviderConnection],
    ) -> tuple[str, ...]:
        credentials: list[str] = []
        for connection in connections:
            path = self._credential_path(connection.credential_reference)
            if path.exists() or path.is_symlink():
                credentials.append(self.read_credential(connection.credential_reference))
        return tuple(credentials)

    @staticmethod
    def _reject_secret_equivalence(
        values: Sequence[str | None],
        known_credentials: Sequence[str],
    ) -> None:
        for credential in known_credentials:
            for value in values:
                if value is not None and credential in value:
                    raise UserProviderStoreError(
                        "normal provider configuration contains configured credential material"
                    )

    @staticmethod
    def _store_payload(
        connections: Sequence[ProviderConnection],
        profiles: Sequence[ModelProfile],
    ) -> dict[str, Any]:
        return {
            "schema_version": PROVIDER_STORE_SCHEMA_VERSION,
            "connections": [item.to_dict() for item in connections],
            "model_profiles": [item.to_dict() for item in profiles],
        }

    @classmethod
    def _reject_persisted_payload_secret_equivalence(
        cls,
        value: object,
        known_credentials: Sequence[str],
    ) -> None:
        strings: list[str] = []

        def collect(item: object) -> None:
            if isinstance(item, Mapping):
                for key, child in item.items():
                    if isinstance(key, str):
                        strings.append(key)
                    collect(child)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    collect(child)
            elif isinstance(item, str):
                strings.append(item)
            elif isinstance(item, (bool, int, float)):
                strings.append(str(item))

        collect(value)
        cls._reject_secret_equivalence(tuple(strings), known_credentials)

    @classmethod
    def _reject_connection_secret_equivalence(
        cls,
        connection: ProviderConnection,
        known_credentials: Sequence[str],
    ) -> None:
        cls._reject_secret_equivalence(
            (
                connection.connection_id,
                connection.display_name,
                connection.api_style,
                connection.base_url,
                connection.native_adapter_id,
                connection.credential_reference,
                connection.created_at,
            ),
            known_credentials,
        )

    @classmethod
    def _reject_model_secret_equivalence(
        cls,
        profile: ModelProfile,
        known_credentials: Sequence[str],
    ) -> None:
        cls._reject_secret_equivalence(
            (
                profile.model_profile_id,
                profile.connection_id,
                profile.display_name,
                profile.remote_model_id,
                *profile.allowed_roles,
            ),
            known_credentials,
        )

    @staticmethod
    def _normalize_secret(value: object) -> str:
        if not isinstance(value, str):
            raise UserProviderStoreError("credential must be non-empty text")
        secret = value.strip()
        if not 8 <= len(secret.encode("utf-8")) <= _MAX_SECRET_BYTES:
            raise UserProviderStoreError(
                "credential must contain between 8 and 16384 UTF-8 bytes"
            )
        if any(ord(character) < 32 or ord(character) == 127 for character in secret):
            raise UserProviderStoreError("credential contains forbidden control characters")
        if any(secret in literal for literal in _RESERVED_MASKED_OUTPUT_LITERALS):
            raise UserProviderStoreError(
                "credential collides with a masked status literal"
            )
        return secret

    @staticmethod
    def _connection_id(value: object) -> str:
        try:
            return normalize_identifier(value, "connection_id")
        except ModelProfileError as error:
            raise UserProviderStoreError(str(error)) from error

    @staticmethod
    def _model_profile_id(value: object) -> str:
        try:
            return normalize_identifier(value, "model_profile_id")
        except ModelProfileError as error:
            raise UserProviderStoreError(str(error)) from error


def openrouter_connection_preset(
    *,
    connection_id: str,
    display_name: str,
    credential_reference: str,
    created_at: str,
    enabled: bool = True,
) -> ProviderConnection:
    """Return metadata only; this helper never loads or calls OpenRouter."""

    return ProviderConnection(
        connection_id=connection_id,
        display_name=display_name,
        api_style="openai_compatible",
        base_url=OPENROUTER_BASE_URL,
        native_adapter_id=None,
        credential_reference=credential_reference,
        enabled=enabled,
        created_at=created_at,
    )


__all__ = [
    "OPENROUTER_BASE_URL",
    "PROVIDER_CONNECTION_SCHEMA_VERSION",
    "PROVIDER_STORE_SCHEMA_VERSION",
    "REVIEWED_NATIVE_ADAPTER_IDS",
    "SUPPORTED_API_STYLES",
    "ProviderConnection",
    "UserProviderStore",
    "UserProviderStoreError",
    "normalize_base_url",
    "openrouter_connection_preset",
]
