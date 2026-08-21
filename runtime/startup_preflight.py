from __future__ import annotations

"""Versioned, fail-closed startup integrity contract for the local runtime.

The verifier deliberately runs before runtime state-store constructors.  Its
read phase never creates directories, lock files, or recovery records.  A
small atomic-persistence probe is attempted only after the read phase has
found no blocking or manual-review condition.
"""

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlparse

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    atomic_write_json,
    read_json_snapshot,
    validate_lock_timeout_seconds,
)
from runtime.safety.bounded_subprocess import (
    MAX_HARD_TIMEOUT_SECONDS,
    MIN_HARD_TIMEOUT_SECONDS,
    SUBPROCESS_RESOURCE_PROFILES,
    SubprocessResourceProfileName,
    validate_hard_timeout_seconds,
)
from runtime.task_recovery import (
    DEFAULT_RECOVERY_LEASE_SECONDS,
    MAX_RECOVERY_DISCOVERY_BATCH,
    MAX_RECOVERY_DISCOVERY_LIMIT,
)
from runtime.sensitive_redaction import RUNTIME_SECRET_ENV_NAMES
from runtime.tools.idempotency import project_scope_fingerprint
from runtime.web_resource_governance import WebResourceLimits, load_web_resource_limits


STARTUP_PREFLIGHT_SCHEMA_VERSION = "AOIA_STARTUP_PREFLIGHT_1A"
MAX_STARTUP_JSON_BYTES = 2 * 1024 * 1024
MAX_STARTUP_STATE_ENTRIES = 1024
MAX_PROMPT_BYTES = 2 * 1024 * 1024
DEFAULT_WEB_PORT = 4311
DEFAULT_WEB_HOST = "127.0.0.1"
MAX_WEB_JSON_BYTES = 1024 * 1024
DEFAULT_PROVIDER_MAX_TOKENS = 1200
MAX_PROVIDER_MAX_TOKENS = 4096
_HEX_40_OR_64 = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

ANCHOR_ROOT_ENV = "AOIA_PROVENANCE_ANCHOR_ROOT"
ANCHOR_REGISTRY_ENV = "AOIA_PROVENANCE_PUBLIC_KEY_REGISTRY"
ANCHOR_ROOT_FINGERPRINT_ENV = "AOIA_PROVENANCE_TRUST_ROOT_FINGERPRINT"


class StartupMode(str, Enum):
    CLI = "CLI"
    WEB = "WEB"


class StartupStatus(str, Enum):
    READY = "READY"
    READY_DEGRADED = "READY_DEGRADED"
    BLOCKED_CONFIGURATION = "BLOCKED_CONFIGURATION"
    BLOCKED_STATE = "BLOCKED_STATE"
    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"
    BLOCKED_SECURITY_INVARIANT = "BLOCKED_SECURITY_INVARIANT"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class ConfigClassification(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    FEATURE_REQUIRED = "FEATURE_REQUIRED"
    SECRET_REFERENCE = "SECRET_REFERENCE"
    BOUNDED_TUNABLE = "BOUNDED_TUNABLE"
    DERIVED = "DERIVED"


class AnchorConfigurationStatus(str, Enum):
    ANCHOR_NOT_CONFIGURED = "ANCHOR_NOT_CONFIGURED"
    ANCHOR_VALID = "ANCHOR_VALID"
    ANCHOR_STALE = "ANCHOR_STALE"
    ANCHOR_SIGNATURE_INVALID = "ANCHOR_SIGNATURE_INVALID"
    ANCHOR_LEDGER_MISMATCH = "ANCHOR_LEDGER_MISMATCH"
    ANCHOR_UNKNOWN_KEY = "ANCHOR_UNKNOWN_KEY"
    ANCHOR_SCHEMA_UNSUPPORTED = "ANCHOR_SCHEMA_UNSUPPORTED"
    ANCHOR_CRYPTO_UNAVAILABLE = "ANCHOR_CRYPTO_UNAVAILABLE"
    ANCHOR_CONFIGURATION_INCOMPLETE = "ANCHOR_CONFIGURATION_INCOMPLETE"


@dataclass(frozen=True)
class ConfigurationObservation:
    name: str
    classification: ConfigClassification
    configured: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "classification": self.classification.value,
            "configured": self.configured,
        }


@dataclass(frozen=True)
class BoundedSetting:
    name: str
    effective_value: int | float

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "effective_value": self.effective_value}


@dataclass(frozen=True)
class StateSchemaStatus:
    resource: str
    status: str
    schema_version: str | None = None
    record_count: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "resource": self.resource,
            "status": self.status,
            "schema_version": self.schema_version,
            "record_count": self.record_count,
        }


@dataclass(frozen=True)
class CapabilityDecision:
    name: str
    enabled: bool
    reason_code: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class StartupPreflightReport:
    schema_version: str
    status: StartupStatus
    mode: StartupMode
    source_commit: str | None
    project_identity: str | None
    state_root_identity: str | None
    configuration: tuple[ConfigurationObservation, ...]
    bounded_settings: tuple[BoundedSetting, ...]
    capabilities: tuple[CapabilityDecision, ...]
    state_schemas: tuple[StateSchemaStatus, ...]
    anchor_status: AnchorConfigurationStatus
    anchor_id: str | None
    anchor_public_key_fingerprint: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != STARTUP_PREFLIGHT_SCHEMA_VERSION:
            raise ValueError("startup preflight schema is unsupported")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise ValueError("startup preflight reasons must be sorted and unique")
        capability_names = tuple(item.name for item in self.capabilities)
        if len(set(capability_names)) != len(capability_names):
            raise ValueError("startup preflight capabilities must be unique")
        configuration_names = tuple(item.name for item in self.configuration)
        if len(set(configuration_names)) != len(configuration_names):
            raise ValueError("startup preflight configuration observations must be unique")

    @property
    def state_changing_execution_enabled(self) -> bool:
        matches = tuple(
            item for item in self.capabilities
            if item.name == "state_changing_execution"
        )
        return len(matches) == 1 and matches[0].enabled

    def capability_enabled(self, name: str) -> bool:
        return any(item.name == name and item.enabled for item in self.capabilities)

    def bounded_setting_value(self, name: str) -> int | float | None:
        matches = tuple(item for item in self.bounded_settings if item.name == name)
        return matches[0].effective_value if len(matches) == 1 else None

    def to_dict(self) -> dict[str, object]:
        """Return a fixed, secret-free representation; no raw config is copied."""

        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "mode": self.mode.value,
            "source_commit": self.source_commit,
            "project_identity": self.project_identity,
            "state_root_identity": self.state_root_identity,
            "configuration": [item.to_dict() for item in self.configuration],
            "bounded_settings": [item.to_dict() for item in self.bounded_settings],
            "capabilities": [item.to_dict() for item in self.capabilities],
            "state_schemas": [item.to_dict() for item in self.state_schemas],
            "anchor": {
                "status": self.anchor_status.value,
                "anchor_id": self.anchor_id,
                "public_key_fingerprint": self.anchor_public_key_fingerprint,
            },
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _Finding:
    status: StartupStatus
    reason_code: str


@dataclass
class _Inspection:
    mode: StartupMode
    project_dir: Path | None = None
    repository_root: Path | None = None
    state_root: Path | None = None
    project_identity: str | None = None
    source_commit: str | None = None
    anchor_status: AnchorConfigurationStatus = AnchorConfigurationStatus.ANCHOR_NOT_CONFIGURED
    anchor_id: str | None = None
    anchor_public_key_fingerprint: str | None = None
    findings: list[_Finding] | None = None
    settings: list[BoundedSetting] | None = None
    schemas: list[StateSchemaStatus] | None = None

    def __post_init__(self) -> None:
        self.findings = []
        self.settings = []
        self.schemas = []

    def add(self, status: StartupStatus, reason_code: str) -> None:
        assert self.findings is not None
        self.findings.append(_Finding(status, reason_code))


_STATUS_PRIORITY = MappingProxyType(
    {
        StartupStatus.READY: 0,
        StartupStatus.READY_DEGRADED: 1,
        StartupStatus.MANUAL_REVIEW_REQUIRED: 2,
        StartupStatus.BLOCKED_CONFIGURATION: 3,
        StartupStatus.BLOCKED_STATE: 4,
        StartupStatus.BLOCKED_PROVENANCE: 5,
        StartupStatus.BLOCKED_SECURITY_INVARIANT: 6,
    }
)


def _final_status(findings: list[_Finding]) -> StartupStatus:
    if not findings:
        return StartupStatus.READY
    return max((item.status for item in findings), key=_STATUS_PRIORITY.__getitem__)


def _strict_bool(environ: Mapping[str, str], name: str, default: bool) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise ValueError(name)
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(name)


def _configured_text(environ: Mapping[str, str], name: str) -> bool:
    value = environ.get(name)
    return isinstance(value, str) and bool(value.strip())


def _strict_port(environ: Mapping[str, str]) -> int:
    raw = environ.get("APP2_WEB_PORT", str(DEFAULT_WEB_PORT))
    if not isinstance(raw, str) or not raw.isascii() or not raw.isdigit() or len(raw) > 5:
        raise ValueError("APP2_WEB_PORT")
    port = int(raw, 10)
    if not 1 <= port <= 65535:
        raise ValueError("APP2_WEB_PORT")
    return port


def _strict_json_limit(environ: Mapping[str, str]) -> int:
    raw = environ.get("AOIA_WEB_MAX_JSON_BYTES", str(64 * 1024))
    if not isinstance(raw, str) or not raw.isascii() or not raw.isdigit() or len(raw) > 10:
        raise ValueError("AOIA_WEB_MAX_JSON_BYTES")
    value = int(raw, 10)
    if not 2 <= value <= MAX_WEB_JSON_BYTES:
        raise ValueError("AOIA_WEB_MAX_JSON_BYTES")
    return value


def _configuration_contract(environ: Mapping[str, str], mode: StartupMode) -> tuple[ConfigurationObservation, ...]:
    names: list[tuple[str, ConfigClassification, bool]] = [
        ("project_dir", ConfigClassification.REQUIRED, True),
        ("prompt_template", ConfigClassification.REQUIRED, True),
        ("AOIA_HOME", ConfigClassification.OPTIONAL, _configured_text(environ, "AOIA_HOME")),
        ("APP2_WEB_HOST", ConfigClassification.OPTIONAL, "APP2_WEB_HOST" in environ),
        ("AOIA_WEB_ALLOWED_ORIGINS", ConfigClassification.FEATURE_REQUIRED, "AOIA_WEB_ALLOWED_ORIGINS" in environ),
        ("web_boundary", ConfigClassification.FEATURE_REQUIRED, mode is StartupMode.WEB),
        ("AOIA_WEB_OPERATOR_TOKEN", ConfigClassification.SECRET_REFERENCE, _configured_text(environ, "AOIA_WEB_OPERATOR_TOKEN")),
        (ANCHOR_ROOT_ENV, ConfigClassification.FEATURE_REQUIRED, _configured_text(environ, ANCHOR_ROOT_ENV)),
        (ANCHOR_REGISTRY_ENV, ConfigClassification.FEATURE_REQUIRED, _configured_text(environ, ANCHOR_REGISTRY_ENV)),
        (ANCHOR_ROOT_FINGERPRINT_ENV, ConfigClassification.FEATURE_REQUIRED, _configured_text(environ, ANCHOR_ROOT_FINGERPRINT_ENV)),
    ]
    for name in tuple(
        sorted((set(RUNTIME_SECRET_ENV_NAMES) - {"AOIA_WEB_OPERATOR_TOKEN"}) | {"KIMI_API_KEY_FILE"})
    ):
        names.append((name, ConfigClassification.SECRET_REFERENCE, _configured_text(environ, name)))
    names.append(
        (
            "provider_secret_files",
            ConfigClassification.SECRET_REFERENCE,
            any(_path_lexists(path) for path in _provider_secret_candidates()),
        )
    )
    for name in (
        "APP2_WEB_PORT",
        "AOIA_WEB_MAX_JSON_BYTES",
        "AOIA_WEB_MAX_CONCURRENT_REQUESTS",
        "AOIA_WEB_MAX_QUEUED_REQUESTS",
        "AOIA_WEB_LISTEN_BACKLOG",
        "AOIA_WEB_MAX_CLIENT_REQUESTS",
        "AOIA_WEB_HEADER_TIMEOUT_SECONDS",
        "AOIA_WEB_BODY_TIMEOUT_SECONDS",
        "AOIA_WEB_WRITE_TIMEOUT_SECONDS",
        "AOIA_WEB_REQUEST_DEADLINE_SECONDS",
        "AOIA_WEB_RATE_WINDOW_SECONDS",
        "AOIA_WEB_HEALTH_RATE_LIMIT",
        "AOIA_WEB_READ_RATE_LIMIT",
        "AOIA_WEB_MUTATION_RATE_LIMIT",
        "AOIA_WEB_RATE_MAX_ENTRIES",
        "AOIA_WEB_RATE_TTL_SECONDS",
        "OPENAI_COMPATIBLE_MAX_TOKENS",
    ):
        names.append((name, ConfigClassification.BOUNDED_TUNABLE, name in environ))
    for name in (
        "OLLAMA_BASE_URL",
        "GEMMA_HF_MODEL",
        "GEMMA_OPENAI_BASE_URL",
        "DEEPSEEK_BASE_URL",
        "XAI_BASE_URL",
    ):
        names.append((name, ConfigClassification.OPTIONAL, name in environ))
    for name in (
        "AGENT_DEBUG",
        "EPISTEMIC_KILL_SWITCH",
        "EPISTEMIC_DISABLE_MODEL",
        "EPISTEMIC_DISABLE_KNOWLEDGE_ROUTE",
        "EPISTEMIC_DISABLE_MEMORY_HATS",
        "EPISTEMIC_DISABLE_REASONING_TRACE",
        "EPISTEMIC_DISABLE_UNKNOWN_FALLBACK",
        "AOIA_PROVIDER_CALLS_ENABLED",
        "AOIA_LEGACY_FILESYSTEM_ENABLED",
        "AOIA_SHELL_EXECUTION_ENABLED",
        "AOIA_LEGACY_BROWSER_ENABLED",
    ):
        names.append((name, ConfigClassification.OPTIONAL, name in environ))
    for name in (
        "source_commit",
        "project_identity",
        "state_root_identity",
        "model_config",
        "provider_config",
        "process_resource_profiles",
        "subprocess_hard_timeout_bounds",
        "state_lock_timeout_seconds",
        "recovery_discovery_limit",
        "recovery_lease_seconds",
        "max_agent_steps",
    ):
        names.append((name, ConfigClassification.DERIVED, True))
    return tuple(
        ConfigurationObservation(name, classification, configured)
        for name, classification, configured in names
    )


def _path_lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _provider_secret_candidates() -> tuple[Path, ...]:
    # Importing the declaration does not read files or populate os.environ.
    try:
        from runtime.providers.config import API_FILE_CANDIDATES
    except (ImportError, OSError):
        return ()
    return tuple(Path(item) for item in API_FILE_CANDIDATES)


def _absolute_lexical(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("path is not absolute")
    return Path(os.path.abspath(path))


def _require_safe_existing_directory(path: Path) -> os.stat_result:
    lexical = _absolute_lexical(path)
    current = Path(lexical.anchor)
    for component in lexical.parts[1:]:
        current = current / component
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("directory chain is unsafe")
    return lexical.lstat()


def _require_safe_directory_chain(path: Path) -> None:
    """Reject links/non-directories; a missing suffix is valid for first boot."""

    lexical = _absolute_lexical(path)
    current = Path(lexical.anchor)
    missing = False
    for component in lexical.parts[1:]:
        current = current / component
        if missing:
            continue
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            missing = True
            continue
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("directory chain is unsafe")


def _safe_read_bytes(
    path: Path,
    maximum_bytes: int,
    *,
    require_private: bool = False,
) -> bytes | None:
    if isinstance(maximum_bytes, bool) or not isinstance(maximum_bytes, int) or maximum_bytes < 1:
        raise ValueError("read bound is invalid")
    try:
        parent_expected = path.parent.lstat()
        expected = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(parent_expected.st_mode) or not stat.S_ISDIR(parent_expected.st_mode):
        raise ValueError("state resource parent is unsafe")
    if stat.S_ISLNK(expected.st_mode) or not stat.S_ISREG(expected.st_mode):
        raise ValueError("state resource is not a safe regular file")
    if expected.st_size > maximum_bytes:
        raise ValueError("state resource exceeds its bounded size")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_descriptor = os.open(path.parent, directory_flags)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        opened_parent = os.fstat(parent_descriptor)
        if (opened_parent.st_dev, opened_parent.st_ino) != (
            parent_expected.st_dev,
            parent_expected.st_ino,
        ):
            raise ValueError("state resource parent binding changed")
        descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
            or opened.st_size > maximum_bytes
            or (require_private and opened.st_uid != os.getuid())
            or (require_private and opened.st_nlink != 1)
            or (require_private and stat.S_IMODE(opened.st_mode) & 0o022)
        ):
            raise ValueError("state resource binding changed")
        remaining = opened.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("state resource changed during read")
            chunks.append(chunk)
            remaining -= len(chunk)
        final_opened = os.fstat(descriptor)
        after = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        visible_parent = path.parent.lstat()
        if (
            stat.S_ISLNK(after.st_mode)
            or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            or final_opened.st_size != opened.st_size
            or final_opened.st_mtime_ns != opened.st_mtime_ns
            or final_opened.st_ctime_ns != opened.st_ctime_ns
            or after.st_size != final_opened.st_size
            or after.st_mtime_ns != final_opened.st_mtime_ns
            or after.st_ctime_ns != final_opened.st_ctime_ns
            or stat.S_ISLNK(visible_parent.st_mode)
            or (visible_parent.st_dev, visible_parent.st_ino)
            != (opened_parent.st_dev, opened_parent.st_ino)
        ):
            raise ValueError("state resource binding changed")
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def _strict_json_bytes(path: Path, maximum_bytes: int) -> dict[str, Any] | list[Any] | None:
    payload = _safe_read_bytes(path, maximum_bytes, require_private=True)
    if payload is None:
        return None

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("non-finite JSON")),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("state JSON is malformed") from exc
    if not isinstance(value, (dict, list)):
        raise ValueError("state JSON has an unsupported top-level type")
    return value


def _bounded_directory_entries(path: Path, maximum: int = MAX_STARTUP_STATE_ENTRIES) -> tuple[str, ...]:
    if not _path_lexists(path):
        return ()
    before = _require_safe_existing_directory(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("state directory binding changed")
        values = tuple(os.listdir(descriptor))
        if len(values) > maximum:
            raise ValueError("state directory exceeds its bounded entry count")
        final_opened = os.fstat(descriptor)
        after = path.lstat()
        if (
            stat.S_ISLNK(after.st_mode)
            or not stat.S_ISDIR(after.st_mode)
            or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            or (final_opened.st_dev, final_opened.st_ino) != (opened.st_dev, opened.st_ino)
            or final_opened.st_mtime_ns != opened.st_mtime_ns
            or final_opened.st_ctime_ns != opened.st_ctime_ns
        ):
            raise ValueError("state directory binding changed")
        return values
    finally:
        os.close(descriptor)


def _contains_sensitive_key(value: object, *, depth: int = 0) -> bool:
    if depth > 16:
        raise ValueError("configuration nesting exceeds its bound")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return True
            folded = key.casefold().replace("-", "_")
            sensitive_exact = {
                "api_key", "apikey", "authorization", "client_secret",
                "credential", "credentials", "password", "passwd",
                "private_key", "secret", "token",
            }
            sensitive_suffixes = (
                "_api_key", "_credential", "_credentials", "_password",
                "_private_key", "_secret", "_token",
            )
            if folded in sensitive_exact or folded.endswith(sensitive_suffixes):
                return True
            if _contains_sensitive_key(item, depth=depth + 1):
                return True
    elif isinstance(value, list):
        if len(value) > MAX_STARTUP_STATE_ENTRIES:
            raise ValueError("configuration list exceeds its bound")
        return any(_contains_sensitive_key(item, depth=depth + 1) for item in value)
    return False


def _validate_web_configuration(
    inspection: _Inspection,
    environ: Mapping[str, str],
) -> None:
    assert inspection.settings is not None
    try:
        port = _strict_port(environ)
        body_limit = _strict_json_limit(environ)
        resources = load_web_resource_limits(environ)
    except (TypeError, ValueError):
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_LIMIT_INVALID")
        return
    inspection.settings.extend(
        BoundedSetting(name, value)
        for name, value in (
            ("web_port", port),
            ("web_max_json_bytes", body_limit),
            ("web_max_concurrent_requests", resources.max_concurrent_requests),
            ("web_max_queued_requests", resources.max_queued_requests),
            ("web_listen_backlog", resources.listen_backlog),
            ("web_max_client_requests", resources.max_client_requests),
            ("web_header_timeout_seconds", resources.header_timeout_seconds),
            ("web_body_timeout_seconds", resources.body_timeout_seconds),
            ("web_write_timeout_seconds", resources.write_timeout_seconds),
            ("web_request_deadline_seconds", resources.request_deadline_seconds),
            ("web_rate_window_seconds", resources.rate_window_seconds),
            ("web_health_rate_limit", resources.health_rate_limit),
            ("web_read_rate_limit", resources.read_rate_limit),
            ("web_mutation_rate_limit", resources.mutation_rate_limit),
            ("web_rate_max_entries", resources.rate_max_entries),
            ("web_rate_ttl_seconds", resources.rate_ttl_seconds),
        )
    )
    host = environ.get("APP2_WEB_HOST", DEFAULT_WEB_HOST)
    if (
        not isinstance(host, str)
        or not host
        or len(host) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in host)
    ):
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_BIND_INVALID")
        return
    if inspection.mode is not StartupMode.WEB:
        return
    token = environ.get("AOIA_WEB_OPERATOR_TOKEN", "")
    if (
        not isinstance(token, str)
        or len(token) < 16
        or len(token) > 4096
        or not token.isascii()
        or any(ord(character) < 33 or ord(character) > 126 for character in token)
    ):
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_AUTH_REQUIRED")
    origins_text = environ.get("AOIA_WEB_ALLOWED_ORIGINS", "")
    if origins_text.strip():
        origins = tuple(item.strip().rstrip("/") for item in origins_text.split(",") if item.strip())
        if not origins or len(origins) > 32:
            inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_ORIGIN_INVALID")
        for origin in origins:
            try:
                parsed = urlparse(origin)
                parsed_port = parsed.port
            except ValueError:
                inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_ORIGIN_INVALID")
                break
            if (
                "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.hostname is None
                or (parsed_port is not None and not 1 <= parsed_port <= 65535)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.params
                or parsed.query
                or parsed.fragment
                or origin != f"{parsed.scheme}://{parsed.netloc}"
            ):
                inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_ORIGIN_INVALID")
                break
    elif host not in {"127.0.0.1", "localhost", "::1"}:
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_WEB_ORIGIN_REQUIRED")


def _strict_provider_url(
    environ: Mapping[str, str],
    name: str,
    default: str,
    *,
    allow_empty: bool = False,
) -> None:
    raw = environ.get(name, default)
    if not isinstance(raw, str):
        raise ValueError(name)
    value = raw.strip()
    if allow_empty and not value:
        return
    if (
        not value
        or len(value) > 2048
        or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(name)
    try:
        parsed = urlparse(value)
        parsed_port = parsed.port
    except ValueError as exc:
        raise ValueError(name) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or (parsed_port is not None and not 1 <= parsed_port <= 65535)
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(name)


def _validate_provider_environment_configuration(
    inspection: _Inspection,
    environ: Mapping[str, str],
) -> None:
    assert inspection.settings is not None
    try:
        raw_tokens = environ.get(
            "OPENAI_COMPATIBLE_MAX_TOKENS",
            str(DEFAULT_PROVIDER_MAX_TOKENS),
        )
        if (
            not isinstance(raw_tokens, str)
            or not raw_tokens.isascii()
            or not raw_tokens.isdigit()
            or len(raw_tokens) > 5
        ):
            raise ValueError("OPENAI_COMPATIBLE_MAX_TOKENS")
        max_tokens = int(raw_tokens, 10)
        if not 1 <= max_tokens <= MAX_PROVIDER_MAX_TOKENS:
            raise ValueError("OPENAI_COMPATIBLE_MAX_TOKENS")
        _strict_provider_url(
            environ,
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434",
        )
        _strict_provider_url(
            environ,
            "GEMMA_OPENAI_BASE_URL",
            "",
            allow_empty=True,
        )
        _strict_provider_url(
            environ,
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com/v1",
        )
        _strict_provider_url(
            environ,
            "XAI_BASE_URL",
            "https://api.x.ai/v1",
        )
        hf_model = environ.get("GEMMA_HF_MODEL", "google/gemma-2-2b-it")
        if (
            not isinstance(hf_model, str)
            or not 1 <= len(hf_model) <= 512
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", hf_model)
            or any(component in {"", ".", ".."} for component in hf_model.split("/"))
        ):
            raise ValueError("GEMMA_HF_MODEL")
    except (TypeError, ValueError):
        inspection.add(
            StartupStatus.BLOCKED_CONFIGURATION,
            "STARTUP_PROVIDER_SETTING_INVALID",
        )
        return
    inspection.settings.append(
        BoundedSetting("provider_max_tokens", max_tokens)
    )


def _validate_runtime_owned_bounds(inspection: _Inspection) -> None:
    assert inspection.settings is not None
    try:
        lock_timeout = validate_lock_timeout_seconds(DEFAULT_STATE_LOCK_TIMEOUT_SECONDS)
        validate_hard_timeout_seconds(MIN_HARD_TIMEOUT_SECONDS)
        validate_hard_timeout_seconds(MAX_HARD_TIMEOUT_SECONDS)
        if not 1 <= MAX_RECOVERY_DISCOVERY_BATCH <= MAX_RECOVERY_DISCOVERY_LIMIT <= 256:
            raise ValueError("recovery discovery bounds are invalid")
        if not 1.0 <= DEFAULT_RECOVERY_LEASE_SECONDS <= 300.0:
            raise ValueError("recovery lease is invalid")
        names = set()
        for key, profile in SUBPROCESS_RESOURCE_PROFILES.items():
            if profile.name != key or profile.name.value in names:
                raise ValueError("process profile identity is invalid")
            names.add(profile.name.value)
            values = (
                profile.cpu_seconds,
                profile.address_space_bytes,
                profile.tree_memory_bytes,
                profile.open_files,
                profile.max_tasks,
                profile.max_capture_bytes,
            )
            if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
                raise ValueError("process profile bound is invalid")
            if (
                profile.cpu_seconds > 600
                or profile.address_space_bytes > 8 * 1024 * 1024 * 1024
                or profile.tree_memory_bytes > 8 * 1024 * 1024 * 1024
                or profile.tree_memory_bytes > 2 * profile.address_space_bytes
                or profile.open_files > 4096
                or profile.max_tasks > 256
                or profile.max_capture_bytes > 16 * 1024 * 1024
            ):
                raise ValueError("process profile exceeds the reviewed startup ceiling")
            if profile.file_size_bytes is not None and (
                isinstance(profile.file_size_bytes, bool)
                or not isinstance(profile.file_size_bytes, int)
                or profile.file_size_bytes <= 0
                or profile.file_size_bytes > 8 * 1024 * 1024 * 1024
            ):
                raise ValueError("process file bound is invalid")
        if names != {item.value for item in SubprocessResourceProfileName}:
            raise ValueError("process profile set is incomplete")
    except (TypeError, ValueError):
        inspection.add(StartupStatus.BLOCKED_SECURITY_INVARIANT, "STARTUP_RUNTIME_BOUND_INVALID")
        return
    inspection.settings.extend(
        (
            BoundedSetting("state_lock_timeout_seconds", lock_timeout),
            BoundedSetting("recovery_discovery_limit", MAX_RECOVERY_DISCOVERY_BATCH),
            BoundedSetting("recovery_lease_seconds", DEFAULT_RECOVERY_LEASE_SECONDS),
            BoundedSetting("subprocess_hard_timeout_min_seconds", MIN_HARD_TIMEOUT_SECONDS),
            BoundedSetting("subprocess_hard_timeout_max_seconds", MAX_HARD_TIMEOUT_SECONDS),
            BoundedSetting("subprocess_resource_profile_count", len(SUBPROCESS_RESOURCE_PROFILES)),
            BoundedSetting("max_agent_steps", 8),
        )
    )


def _validate_boolean_and_security_flags(inspection: _Inspection, environ: Mapping[str, str]) -> None:
    flags = (
        "AGENT_DEBUG",
        "EPISTEMIC_KILL_SWITCH",
        "EPISTEMIC_DISABLE_MODEL",
        "EPISTEMIC_DISABLE_KNOWLEDGE_ROUTE",
        "EPISTEMIC_DISABLE_MEMORY_HATS",
        "EPISTEMIC_DISABLE_REASONING_TRACE",
        "EPISTEMIC_DISABLE_UNKNOWN_FALLBACK",
        "AOIA_PROVIDER_CALLS_ENABLED",
        "AOIA_LEGACY_FILESYSTEM_ENABLED",
        "AOIA_SHELL_EXECUTION_ENABLED",
        "AOIA_LEGACY_BROWSER_ENABLED",
    )
    parsed: dict[str, bool] = {}
    for name in flags:
        try:
            parsed[name] = _strict_bool(environ, name, False)
        except ValueError:
            inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_BOOLEAN_SETTING_INVALID")
            return
    if any(
        parsed[name]
        for name in (
            "AOIA_LEGACY_FILESYSTEM_ENABLED",
            "AOIA_SHELL_EXECUTION_ENABLED",
            "AOIA_LEGACY_BROWSER_ENABLED",
            "EPISTEMIC_DISABLE_UNKNOWN_FALLBACK",
        )
    ):
        inspection.add(
            StartupStatus.BLOCKED_SECURITY_INVARIANT,
            "STARTUP_SECURITY_INVARIANT_OVERRIDE_REJECTED",
        )
    if parsed.get("AOIA_PROVIDER_CALLS_ENABLED") is True:
        inspection.add(
            StartupStatus.MANUAL_REVIEW_REQUIRED,
            "STARTUP_PROVIDER_ACTIVATION_REVIEW_REQUIRED",
        )


def _validate_state_path_privacy(state_root: Path) -> None:
    """Require an operator-owned private ancestor fencing the state subtree."""

    lexical = _absolute_lexical(state_root)
    state_home = lexical.parents[1]
    current = Path(lexical.anchor)
    private_fence = False
    inside_state_home = False
    for component in lexical.parts[1:]:
        current = current / component
        if current == state_home:
            inside_state_home = True
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("state path is unsafe")
        if metadata.st_uid == os.getuid() and not (stat.S_IMODE(metadata.st_mode) & 0o077):
            private_fence = True
        if inside_state_home and metadata.st_uid != os.getuid():
            raise ValueError("state path is not operator-owned")
    if not private_fence:
        raise ValueError("state path lacks an owner-only ancestor")


def _validate_state_layout(inspection: _Inspection, runtime_root: Path) -> None:
    assert inspection.schemas is not None
    try:
        _validate_state_path_privacy(runtime_root)
        for path in (
            runtime_root,
            runtime_root / "state",
            runtime_root / "memory",
            runtime_root / "state" / "provenance",
            runtime_root / "state" / "tasks",
            runtime_root / "state" / "idempotency",
            runtime_root / "state" / "recovery",
        ):
            if not _path_lexists(path):
                continue
            metadata = _require_safe_existing_directory(path)
            if metadata.st_uid != os.getuid():
                raise ValueError("state directory is not operator-owned")
        inspection.schemas.append(StateSchemaStatus("state_layout", "VALID"))
    except (OSError, ValueError):
        inspection.schemas.append(StateSchemaStatus("state_layout", "INVALID"))
        inspection.add(
            StartupStatus.BLOCKED_SECURITY_INVARIANT,
            "STARTUP_STATE_LAYOUT_UNSAFE",
        )


def _validate_state_locks(inspection: _Inspection, state_dir: Path) -> None:
    assert inspection.schemas is not None
    locks = state_dir / ".locks"
    try:
        names = _bounded_directory_entries(locks, 4096)
        for name in names:
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}\.[0-9a-f]{16}\.lock", name):
                raise ValueError("state lock filename is invalid")
            path = locks / name
            metadata = path.lstat()
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1
                or metadata.st_size > 4096
                or stat.S_IMODE(metadata.st_mode) & 0o077
            ):
                raise ValueError("state lock resource is unsafe")
        if names:
            _rescan_unchanged(locks, names)
        inspection.schemas.append(
            StateSchemaStatus("state_locks", "VALID" if names else "NOT_PRESENT", "AOIA_STATE_LOCK_1A", len(names))
        )
    except (OSError, ValueError):
        inspection.schemas.append(StateSchemaStatus("state_locks", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_STATE_LOCK_INVALID")


def _rescan_unchanged(path: Path, expected_names: tuple[str, ...]) -> None:
    if tuple(sorted(_bounded_directory_entries(path))) != tuple(sorted(expected_names)):
        raise ValueError("state directory changed during validation")


def _derive_state_root(project_dir: Path, environ: Mapping[str, str]) -> Path:
    raw_home = environ.get("AOIA_HOME", "")
    if not isinstance(raw_home, str) or "\x00" in raw_home:
        raise ValueError("AOIA_HOME is invalid")
    if raw_home.strip():
        home = Path(raw_home.strip()).expanduser()
        if not home.is_absolute():
            raise ValueError("AOIA_HOME must be absolute")
    else:
        home = Path.home() / ".local" / "state" / "aoia"
    resolved_project = project_dir.resolve(strict=True)
    name = resolved_project.name or "AOIA-Core"
    digest = hashlib.sha256(str(resolved_project).encode("utf-8")).hexdigest()[:12]
    return _absolute_lexical(home) / f"{name}-{digest}" / "runtime"


def _discover_repository_root(project_dir: Path, supplied: Path | None) -> Path | None:
    if supplied is not None:
        candidate = Path(supplied)
        if not candidate.is_absolute():
            return None
        resolved = candidate.resolve(strict=True)
        try:
            project_dir.relative_to(resolved)
        except ValueError:
            return None
        return resolved
    current = project_dir
    for _index in range(8):
        if _path_lexists(current / ".git"):
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _read_source_commit(repository_root: Path | None) -> str | None:
    if repository_root is None:
        return None
    git_dir = repository_root / ".git"
    try:
        metadata = git_dir.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        # Linked-worktree indirection is intentionally not trusted by this
        # narrow startup reader; release attestation handles it separately.
        return None
    try:
        head_raw = _safe_read_bytes(git_dir / "HEAD", 4096)
        if head_raw is None:
            return None
        head = head_raw.decode("ascii", errors="strict").strip()
        if _HEX_40_OR_64.fullmatch(head):
            return head.lower()
        if not head.startswith("ref: "):
            return None
        ref_name = head[5:]
        if (
            not ref_name.startswith("refs/")
            or ".." in ref_name.split("/")
            or not re.fullmatch(r"refs/[A-Za-z0-9._/-]{1,512}", ref_name)
        ):
            return None
        loose = _safe_read_bytes(git_dir / Path(ref_name), 4096)
        if loose is not None:
            value = loose.decode("ascii", errors="strict").strip().lower()
            return value if _HEX_40_OR_64.fullmatch(value) else None
        packed = _safe_read_bytes(git_dir / "packed-refs", 8 * 1024 * 1024)
        if packed is None:
            return None
        for raw_line in packed.decode("ascii", errors="strict").splitlines():
            if not raw_line or raw_line.startswith(("#", "^")):
                continue
            parts = raw_line.split(" ", 1)
            if len(parts) == 2 and parts[1] == ref_name:
                value = parts[0].lower()
                return value if _HEX_40_OR_64.fullmatch(value) else None
    except (OSError, UnicodeError, ValueError):
        return None
    return None


def _validate_required_inputs(
    inspection: _Inspection,
    project_dir: Path,
    repository_root: Path | None,
    expected_source_commit: str | None,
) -> None:
    try:
        if not project_dir.is_absolute():
            raise ValueError("project path must be absolute")
        resolved = project_dir.resolve(strict=True)
        _require_safe_existing_directory(resolved)
        inspection.project_dir = resolved
        inspection.project_identity = project_scope_fingerprint(resolved)
        prompt = _safe_read_bytes(resolved / "prompts" / "system_prompt.txt", MAX_PROMPT_BYTES)
        if prompt is None or not prompt.strip():
            raise ValueError("prompt is missing")
        prompt.decode("utf-8", errors="strict")
    except (OSError, UnicodeError, ValueError):
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_REQUIRED_CONFIGURATION_INVALID")
        return
    inspection.repository_root = _discover_repository_root(resolved, repository_root)
    if repository_root is not None and inspection.repository_root is None:
        inspection.add(
            StartupStatus.BLOCKED_CONFIGURATION,
            "STARTUP_REPOSITORY_ROOT_INVALID",
        )
    inspection.source_commit = _read_source_commit(inspection.repository_root)
    if expected_source_commit is not None:
        expected = expected_source_commit.lower()
        if (
            not _HEX_40_OR_64.fullmatch(expected)
            or inspection.source_commit is None
            or expected != inspection.source_commit
        ):
            inspection.add(
                StartupStatus.BLOCKED_SECURITY_INVARIANT,
                "STARTUP_SOURCE_COMMIT_MISMATCH",
            )
    if inspection.source_commit is None:
        inspection.add(StartupStatus.READY_DEGRADED, "STARTUP_SOURCE_COMMIT_UNAVAILABLE")


def _validate_provider_secret_files(inspection: _Inspection) -> None:
    configured = 0
    try:
        for path in _provider_secret_candidates():
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                continue
            configured += 1
            _require_safe_directory_chain(path.parent)
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
                or metadata.st_size > 64 * 1024
            ):
                raise ValueError("provider secret reference is unsafe")
        assert inspection.schemas is not None
        inspection.schemas.append(
            StateSchemaStatus(
                "provider_secret_references",
                "CONFIGURED" if configured else "NOT_CONFIGURED",
                record_count=configured,
            )
        )
    except (OSError, ValueError):
        inspection.add(
            StartupStatus.BLOCKED_SECURITY_INVARIANT,
            "STARTUP_SECRET_REFERENCE_UNSAFE",
        )


def _validate_model_and_provider_config(inspection: _Inspection, state_dir: Path) -> None:
    assert inspection.schemas is not None
    for resource, filename in (("model_config", "model_config.json"), ("provider_config", "providers.json")):
        try:
            payload = _strict_json_bytes(state_dir / filename, 256 * 1024)
            if payload is None:
                inspection.schemas.append(StateSchemaStatus(resource, "NOT_PRESENT"))
                continue
            if not isinstance(payload, dict) or _contains_sensitive_key(payload):
                raise ValueError("configuration shape is invalid")
            if resource == "model_config":
                if set(payload) != {"model"}:
                    raise ValueError("model config has an inexact schema")
                model = payload["model"]
                if (
                    not isinstance(model, str)
                    or not 1 <= len(model) <= 512
                    or any(ord(character) < 32 for character in model)
                ):
                    raise ValueError("model config is invalid")
            else:
                if set(payload) != {"providers"} or not isinstance(payload["providers"], list):
                    raise ValueError("provider config has an inexact schema")
                providers = payload["providers"]
                if not 1 <= len(providers) <= 32:
                    raise ValueError("provider config list is invalid")
                for item in providers:
                    if not isinstance(item, dict) or set(item) != {"name", "model", "enabled"}:
                        raise ValueError("provider config entry is invalid")
                    if not isinstance(item["enabled"], bool):
                        raise ValueError("provider enabled flag is invalid")
                    for key in ("name", "model"):
                        if not isinstance(item[key], str) or not 1 <= len(item[key]) <= 512:
                            raise ValueError("provider text is invalid")
            inspection.schemas.append(StateSchemaStatus(resource, "VALID", "AOIA_PROVIDER_CONFIG_1A"))
        except (OSError, ValueError):
            inspection.schemas.append(StateSchemaStatus(resource, "INVALID"))
            inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_PROVIDER_CONFIGURATION_INVALID")


def _validate_agent_memory(inspection: _Inspection, state_dir: Path) -> None:
    assert inspection.schemas is not None
    try:
        payload = _strict_json_bytes(state_dir / "agent_state.json", MAX_STARTUP_JSON_BYTES)
        if payload is None:
            inspection.schemas.append(StateSchemaStatus("agent_memory", "NOT_PRESENT"))
            return
        if not isinstance(payload, dict):
            raise ValueError("memory state is not an object")
        from runtime.tools.memory import AgentMemory, MemoryStore

        memory = AgentMemory(**payload)
        MemoryStore._validate_loaded_memory(memory)
        inspection.schemas.append(StateSchemaStatus("agent_memory", "VALID", "AOIA_AGENT_MEMORY_1A", 1))
    except (OSError, TypeError, ValueError):
        inspection.schemas.append(StateSchemaStatus("agent_memory", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_AGENT_MEMORY_INVALID")


def _validate_memory_hats(inspection: _Inspection, runtime_root: Path, state_dir: Path) -> None:
    assert inspection.schemas is not None
    hats_dir = runtime_root / "memory" / "hats"
    try:
        names = _bounded_directory_entries(hats_dir, 128)
        known: set[str] = set()
        for name in names:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}\.json", name):
                raise ValueError("memory hat filename is invalid")
            payload = _strict_json_bytes(hats_dir / name, 256 * 1024)
            if not isinstance(payload, dict) or set(payload) != {
                "name", "role", "instructions", "project_path", "persistent"
            }:
                raise ValueError("memory hat schema is invalid")
            if payload["name"] != name[:-5] or not isinstance(payload["persistent"], bool):
                raise ValueError("memory hat identity is invalid")
            if any(not isinstance(payload[key], str) for key in ("name", "role", "instructions", "project_path")):
                raise ValueError("memory hat field type is invalid")
            known.add(name[:-5])
        if names:
            _rescan_unchanged(hats_dir, names)
        active = _strict_json_bytes(state_dir / "active_hat.json", 64 * 1024)
        if active is not None:
            if not isinstance(active, dict) or set(active) != {"name"} or active["name"] not in known:
                raise ValueError("active memory hat is invalid")
        status = "VALID" if names or active is not None else "NOT_PRESENT"
        inspection.schemas.append(StateSchemaStatus("memory_hats", status, "AOIA_MEMORY_HAT_1A", len(names)))
    except (OSError, ValueError):
        inspection.schemas.append(StateSchemaStatus("memory_hats", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_MEMORY_HATS_INVALID")


def _validate_task_checkpoints(inspection: _Inspection, state_dir: Path) -> None:
    assert inspection.schemas is not None
    root = state_dir / "tasks"
    try:
        names = _bounded_directory_entries(root)
        pending = 0
        from runtime.task_checkpoints import (
            TASK_CHECKPOINT_SCHEMA_VERSION,
            TERMINAL_TASK_STATES,
            TaskCheckpoint,
        )

        for name in names:
            if not re.fullmatch(r"[0-9a-f]{64}", name):
                raise ValueError("checkpoint resource name is invalid")
            task_dir = root / name
            _require_safe_existing_directory(task_dir)
            children = _bounded_directory_entries(task_dir, 4)
            if set(children) != {"checkpoint.json"}:
                raise ValueError("checkpoint resource has unexpected contents")
            payload = _strict_json_bytes(task_dir / "checkpoint.json", MAX_STARTUP_JSON_BYTES)
            if not isinstance(payload, dict):
                raise ValueError("checkpoint is missing")
            checkpoint = TaskCheckpoint.from_payload(payload)
            if checkpoint.project_scope != inspection.project_identity:
                raise ValueError("checkpoint project identity mismatch")
            digest = hashlib.sha256(checkpoint.task_id.encode("ascii")).hexdigest()
            if digest != name:
                raise ValueError("checkpoint filename identity mismatch")
            if checkpoint.state not in TERMINAL_TASK_STATES:
                pending += 1
            _rescan_unchanged(task_dir, children)
        if names:
            _rescan_unchanged(root, names)
        inspection.schemas.append(
            StateSchemaStatus(
                "task_checkpoints",
                "VALID" if names else "NOT_PRESENT",
                TASK_CHECKPOINT_SCHEMA_VERSION,
                len(names),
            )
        )
        if pending:
            inspection.add(
                StartupStatus.MANUAL_REVIEW_REQUIRED,
                "STARTUP_TASK_RECOVERY_REVIEW_REQUIRED",
            )
    except Exception:
        inspection.schemas.append(StateSchemaStatus("task_checkpoints", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_TASK_CHECKPOINT_INVALID")


def _validate_idempotency(inspection: _Inspection, state_dir: Path) -> None:
    assert inspection.schemas is not None
    root = state_dir / "idempotency"
    try:
        names = _bounded_directory_entries(root)
        pending = 0
        from runtime.tools.idempotency import (
            IDEMPOTENCY_SCHEMA_VERSION,
            LEGACY_IDEMPOTENCY_SCHEMA_VERSION,
            MAX_IDEMPOTENCY_RECORD_BYTES,
            TERMINAL_STATES,
            IdempotencyRecord,
        )

        schemas: set[str] = set()
        for name in names:
            if not re.fullmatch(r"[0-9a-f]{64}\.json", name):
                raise ValueError("idempotency resource name is invalid")
            payload = _strict_json_bytes(root / name, MAX_IDEMPOTENCY_RECORD_BYTES)
            if not isinstance(payload, dict):
                raise ValueError("idempotency record is missing")
            record = IdempotencyRecord.from_payload(payload)
            if record.project_scope != inspection.project_identity:
                raise ValueError("idempotency project identity mismatch")
            digest = hashlib.sha256(record.operation_key.encode("ascii")).hexdigest()
            if name != f"{digest}.json":
                raise ValueError("idempotency filename identity mismatch")
            schemas.add(record.schema_version)
            if record.state not in TERMINAL_STATES:
                pending += 1
        if names:
            _rescan_unchanged(root, names)
        schema_text = (
            IDEMPOTENCY_SCHEMA_VERSION
            if schemas <= {IDEMPOTENCY_SCHEMA_VERSION}
            else LEGACY_IDEMPOTENCY_SCHEMA_VERSION + "+" + IDEMPOTENCY_SCHEMA_VERSION
        )
        inspection.schemas.append(
            StateSchemaStatus(
                "idempotency",
                "VALID" if names else "NOT_PRESENT",
                schema_text,
                len(names),
            )
        )
        if pending:
            inspection.add(
                StartupStatus.MANUAL_REVIEW_REQUIRED,
                "STARTUP_IDEMPOTENCY_REVIEW_REQUIRED",
            )
    except Exception:
        inspection.schemas.append(StateSchemaStatus("idempotency", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_IDEMPOTENCY_INVALID")


def _validate_recovery_state(inspection: _Inspection, state_dir: Path) -> None:
    assert inspection.schemas is not None
    root = state_dir / "recovery"
    try:
        root_names = _bounded_directory_entries(root, 8)
        if not root_names:
            inspection.schemas.append(StateSchemaStatus("recovery", "NOT_PRESENT"))
            return
        if set(root_names) != {"claims", "execution"}:
            raise ValueError("recovery root has unexpected contents")
        claims_parent = root / "claims"
        execution_parent = root / "execution"
        expected_scope = inspection.project_identity
        assert expected_scope is not None
        if set(_bounded_directory_entries(claims_parent, 4)) != {expected_scope}:
            raise ValueError("recovery claim scope is invalid")
        if set(_bounded_directory_entries(execution_parent, 4)) != {expected_scope}:
            raise ValueError("recovery execution scope is invalid")
        claims_root = claims_parent / expected_scope
        execution_root = execution_parent / expected_scope
        claim_names = _bounded_directory_entries(claims_root)
        execution_names = _bounded_directory_entries(execution_root)
        from runtime.task_recovery import (
            MAX_RECOVERY_CLAIM_BYTES,
            RECOVERY_CLAIM_SCHEMA_VERSION,
            RecoveryClaim,
            RecoveryClaimStatus,
        )

        active = 0
        claims_by_resource: dict[str, Any] = {}
        for name in claim_names:
            if not re.fullmatch(r"[0-9a-f]{64}\.json", name):
                raise ValueError("recovery claim filename is invalid")
            payload = _strict_json_bytes(claims_root / name, MAX_RECOVERY_CLAIM_BYTES)
            if not isinstance(payload, dict):
                raise ValueError("recovery claim is missing")
            claim = RecoveryClaim.from_payload(payload)
            if claim.project_scope != expected_scope:
                raise ValueError("recovery claim project mismatch")
            digest = hashlib.sha256(claim.task_id.encode("ascii")).hexdigest()
            if name != f"{digest}.json":
                raise ValueError("recovery claim filename mismatch")
            claims_by_resource[digest] = claim
            if claim.status is RecoveryClaimStatus.ACTIVE:
                active += 1
            if claim.checkpoint_version is not None:
                checkpoint_payload = _strict_json_bytes(
                    state_dir / "tasks" / digest / "checkpoint.json",
                    MAX_STARTUP_JSON_BYTES,
                )
                if not isinstance(checkpoint_payload, dict):
                    raise ValueError("recovery-bound checkpoint is missing")
                from runtime.task_checkpoints import TaskCheckpoint

                checkpoint = TaskCheckpoint.from_payload(checkpoint_payload)
                if (
                    checkpoint.checkpoint_version != claim.checkpoint_version
                    or checkpoint.checkpoint_hash != claim.checkpoint_hash
                ):
                    raise ValueError("recovery claim checkpoint binding mismatch")
        execution_resources: dict[str, os.stat_result] = {}
        for name in execution_names:
            if not re.fullmatch(r"[0-9a-f]{64}\.lock", name):
                raise ValueError("recovery execution lock filename is invalid")
            metadata = (execution_root / name).lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ValueError("recovery execution lock is unsafe")
            execution_resources[name[:-5]] = metadata
        if set(execution_resources) != set(claims_by_resource):
            raise ValueError("recovery claim and execution lock sets differ")
        for resource, claim in claims_by_resource.items():
            metadata = execution_resources[resource]
            if (metadata.st_dev, metadata.st_ino) != (
                claim.execution_lock_device,
                claim.execution_lock_inode,
            ):
                raise ValueError("recovery execution lock binding mismatch")
        _rescan_unchanged(claims_root, claim_names)
        _rescan_unchanged(execution_root, execution_names)
        _rescan_unchanged(root, root_names)
        inspection.schemas.append(
            StateSchemaStatus("recovery", "VALID", RECOVERY_CLAIM_SCHEMA_VERSION, len(claim_names))
        )
        if active:
            inspection.add(
                StartupStatus.MANUAL_REVIEW_REQUIRED,
                "STARTUP_ACTIVE_RECOVERY_CLAIM_REVIEW_REQUIRED",
            )
    except Exception:
        inspection.schemas.append(StateSchemaStatus("recovery", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_RECOVERY_STATE_INVALID")


def _validate_provenance(inspection: _Inspection, state_dir: Path) -> Path:
    assert inspection.schemas is not None
    provenance_dir = state_dir / "provenance"
    runtime_ledger = provenance_dir / "runtime_provenance_log.jsonl"
    try:
        names = _bounded_directory_entries(provenance_dir, MAX_STARTUP_STATE_ENTRIES + 4)
        allowed = {"provenance_log.jsonl", "runtime_provenance_log.jsonl", "outbox"}
        if any(name not in allowed for name in names):
            raise ValueError("provenance directory has unexpected contents")
        from runtime.tools.provenance import (
            MAX_PROVENANCE_LOG_BYTES,
            MAX_PROVENANCE_OUTBOX_ENTRIES,
            MAX_PROVENANCE_RECORD_BYTES,
            RUNTIME_PROVENANCE_SCHEMA_VERSION,
            RUNTIME_PROVENANCE_SCHEMA_VERSIONS,
            RuntimeProvenanceEvent,
            _TERMINAL_EVENT_TYPES,
            _decode_lines,
            _event_hash,
            _verify_entries,
        )

        runtime_count = 0
        runtime_schema = RUNTIME_PROVENANCE_SCHEMA_VERSION
        for filename, resource in (
            ("provenance_log.jsonl", "legacy_provenance"),
            ("runtime_provenance_log.jsonl", "runtime_provenance"),
        ):
            payload = _safe_read_bytes(
                provenance_dir / filename,
                MAX_PROVENANCE_LOG_BYTES,
                require_private=True,
            )
            if payload is None:
                inspection.schemas.append(StateSchemaStatus(resource, "NOT_PRESENT"))
                continue
            entries, parse_issues = _decode_lines(payload)
            verification = _verify_entries(entries, parse_issues)
            if not verification.ok:
                raise ValueError("provenance chain is invalid")
            if resource == "runtime_provenance":
                if any(item.get("schema_version") not in RUNTIME_PROVENANCE_SCHEMA_VERSIONS for item in entries):
                    raise ValueError("runtime provenance schema is invalid")
                runtime_count = verification.entry_count
                if entries:
                    runtime_schema = str(entries[-1]["schema_version"])
            inspection.schemas.append(
                StateSchemaStatus(resource, "VALID", runtime_schema if resource == "runtime_provenance" else "AOIA_PROVENANCE_LEGACY", verification.entry_count)
            )
        outbox = provenance_dir / "outbox"
        outbox_names = _bounded_directory_entries(outbox, MAX_PROVENANCE_OUTBOX_ENTRIES)
        for name in outbox_names:
            if not re.fullmatch(r"provenance_event_[0-9a-f]{32}\.json", name):
                raise ValueError("provenance outbox filename is invalid")
            document = _strict_json_bytes(outbox / name, MAX_PROVENANCE_RECORD_BYTES)
            if not isinstance(document, dict):
                raise ValueError("provenance outbox record is missing")
            event_hash = document.get("event_hash")
            event_document = {key: value for key, value in document.items() if key != "event_hash"}
            event = RuntimeProvenanceEvent.from_event_document(event_document)
            if event_hash != _event_hash(event_document):
                raise ValueError("provenance outbox event hash is invalid")
            if event.event_type not in _TERMINAL_EVENT_TYPES or name != f"{event.event_id}.json":
                raise ValueError("provenance outbox event identity is invalid")
        if outbox_names:
            _rescan_unchanged(outbox, outbox_names)
            inspection.add(
                StartupStatus.READY_DEGRADED,
                "STARTUP_PROVENANCE_RECOVERY_REQUIRED",
            )
        inspection.schemas.append(
            StateSchemaStatus("provenance_outbox", "PENDING" if outbox_names else "CLEAR", RUNTIME_PROVENANCE_SCHEMA_VERSION, len(outbox_names))
        )
        if names:
            _rescan_unchanged(provenance_dir, names)
        dependent_state = any(
            item.resource in {"task_checkpoints", "idempotency", "recovery"}
            and item.record_count is not None
            and item.record_count > 0
            for item in inspection.schemas
        )
        if dependent_state and runtime_count == 0:
            inspection.add(
                StartupStatus.BLOCKED_PROVENANCE,
                "STARTUP_RUNTIME_PROVENANCE_REQUIRED",
            )
    except Exception:
        inspection.schemas.append(StateSchemaStatus("provenance_integrity", "INVALID"))
        inspection.add(StartupStatus.BLOCKED_PROVENANCE, "STARTUP_PROVENANCE_INVALID")
    return runtime_ledger


def _validate_anchor_configuration(
    inspection: _Inspection,
    environ: Mapping[str, str],
    runtime_ledger: Path,
) -> None:
    values = tuple(environ.get(name, "") for name in (
        ANCHOR_ROOT_ENV,
        ANCHOR_REGISTRY_ENV,
        ANCHOR_ROOT_FINGERPRINT_ENV,
    ))
    if any(not isinstance(value, str) for value in values):
        inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_CONFIGURATION_INCOMPLETE
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_ANCHOR_CONFIGURATION_INCOMPLETE")
        return
    configured = tuple(bool(value.strip()) for value in values)
    if not any(configured):
        inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_NOT_CONFIGURED
        inspection.add(StartupStatus.READY_DEGRADED, "STARTUP_ANCHOR_NOT_CONFIGURED")
        return
    if not all(configured):
        inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_CONFIGURATION_INCOMPLETE
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_ANCHOR_CONFIGURATION_INCOMPLETE")
        return
    anchor_text, registry_text, fingerprint = (value.strip() for value in values)
    if (
        not re.fullmatch(r"[0-9a-f]{64}", fingerprint)
        or not Path(anchor_text).is_absolute()
        or not Path(registry_text).is_absolute()
        or inspection.project_dir is None
    ):
        inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_CONFIGURATION_INCOMPLETE
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_ANCHOR_CONFIGURATION_INVALID")
        return
    try:
        _require_safe_directory_chain(Path(anchor_text))
        _require_safe_directory_chain(Path(registry_text))
        from runtime.tools.provenance_anchor import AnchorStatus, verify_latest_provenance_anchor

        result = verify_latest_provenance_anchor(
            runtime_ledger,
            Path(anchor_text),
            Path(registry_text),
            expected_root_fingerprint=fingerprint,
            project_dir=inspection.project_dir,
        )
        inspection.anchor_id = result.anchor_id
        inspection.anchor_public_key_fingerprint = result.public_key_fingerprint
        if result.status is AnchorStatus.ANCHOR_VALID and result.is_current:
            inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_VALID
            return
        if (
            result.status is AnchorStatus.ANCHOR_LEDGER_MISMATCH
            and result.anchored_entry_count is not None
            and result.actual_entry_count is not None
            and result.anchored_entry_count < result.actual_entry_count
        ):
            # verify_latest reaches this shape only after the canonical archive,
            # pointer, signature, key chain, and anchored ledger prefix passed.
            inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_STALE
            inspection.add(StartupStatus.READY_DEGRADED, "STARTUP_ANCHOR_STALE")
            return
        mapping = {
            AnchorStatus.ANCHOR_SIGNATURE_INVALID: AnchorConfigurationStatus.ANCHOR_SIGNATURE_INVALID,
            AnchorStatus.ANCHOR_LEDGER_MISMATCH: AnchorConfigurationStatus.ANCHOR_LEDGER_MISMATCH,
            AnchorStatus.ANCHOR_UNKNOWN_KEY: AnchorConfigurationStatus.ANCHOR_UNKNOWN_KEY,
            AnchorStatus.ANCHOR_SCHEMA_UNSUPPORTED: AnchorConfigurationStatus.ANCHOR_SCHEMA_UNSUPPORTED,
            AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE: AnchorConfigurationStatus.ANCHOR_CRYPTO_UNAVAILABLE,
        }
        inspection.anchor_status = mapping.get(
            result.status,
            AnchorConfigurationStatus.ANCHOR_SCHEMA_UNSUPPORTED,
        )
        inspection.add(StartupStatus.BLOCKED_PROVENANCE, "STARTUP_ANCHOR_INVALID")
    except Exception:
        inspection.anchor_status = AnchorConfigurationStatus.ANCHOR_SCHEMA_UNSUPPORTED
        inspection.add(StartupStatus.BLOCKED_PROVENANCE, "STARTUP_ANCHOR_INVALID")


def _create_missing_directories(path: Path) -> list[Path]:
    lexical = _absolute_lexical(path)
    missing: list[Path] = []
    current = lexical
    while not _path_lexists(current):
        missing.append(current)
        if current.parent == current:
            raise ValueError("no safe persistence parent exists")
        current = current.parent
    _require_safe_existing_directory(current)
    created: list[Path] = []
    for candidate in reversed(missing):
        try:
            candidate.mkdir(mode=0o700)
            created.append(candidate)
        except FileExistsError:
            _require_safe_existing_directory(candidate)
    _require_safe_existing_directory(lexical)
    return created


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_persistence_probe(inspection: _Inspection) -> None:
    state_root = inspection.state_root
    if state_root is None:
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_PERSISTENCE_PROBE_FAILED")
        return
    created: list[Path] = []
    probe_dir: Path | None = None
    cleanup_failed = False
    try:
        created = _create_missing_directories(state_root)
        probe_dir = Path(tempfile.mkdtemp(prefix=".aoia-startup-probe-", dir=state_root))
        if stat.S_IMODE(probe_dir.lstat().st_mode) & 0o077:
            raise ValueError("persistence probe directory is not private")
        target = probe_dir / "probe.json"
        lock_path = probe_dir / ".locks" / "probe.lock"
        payload = {
            "schema_version": "AOIA_STARTUP_PERSISTENCE_PROBE_1A",
            "probe_nonce": os.urandom(16).hex(),
        }
        atomic_write_json(
            target,
            payload,
            lock_path=lock_path,
            lock_timeout_seconds=DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
            sort_keys=True,
            trailing_newline=True,
            mode=0o600,
        )
        if read_json_snapshot(target, reject_duplicate_keys=True, maximum_bytes=4096) != payload:
            raise ValueError("persistence probe readback failed")
        _fsync_directory(probe_dir)
    except Exception:
        inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_PERSISTENCE_PROBE_FAILED")
    finally:
        if probe_dir is not None:
            for candidate in (
                probe_dir / "probe.json",
                probe_dir / ".locks" / "probe.lock",
            ):
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    cleanup_failed = True
            for candidate in (probe_dir / ".locks", probe_dir):
                try:
                    candidate.rmdir()
                except FileNotFoundError:
                    pass
                except OSError:
                    cleanup_failed = True
        for candidate in reversed(created):
            try:
                candidate.rmdir()
            except FileNotFoundError:
                pass
            except OSError:
                cleanup_failed = True
        if probe_dir is not None and _path_lexists(probe_dir):
            cleanup_failed = True
        if cleanup_failed:
            inspection.add(StartupStatus.BLOCKED_STATE, "STARTUP_PERSISTENCE_PROBE_CLEANUP_FAILED")


def _capabilities(status: StartupStatus, mode: StartupMode) -> tuple[CapabilityDecision, ...]:
    activation = status in {StartupStatus.READY, StartupStatus.READY_DEGRADED}
    activation_reason = "STARTUP_ACTIVATION_ALLOWED" if activation else "STARTUP_ACTIVATION_BLOCKED"
    return (
        CapabilityDecision("diagnostics", True, "STARTUP_DIAGNOSTICS_AVAILABLE"),
        CapabilityDecision("read_only_runtime", activation, activation_reason),
        CapabilityDecision("state_changing_execution", activation, activation_reason),
        CapabilityDecision(
            "provider_calls",
            False,
            "STARTUP_PROVIDER_ADDITIONAL_AUTHORITY_REQUIRED",
        ),
        CapabilityDecision(
            "web_listener",
            activation and mode is StartupMode.WEB,
            "STARTUP_WEB_LISTENER_ALLOWED"
            if activation and mode is StartupMode.WEB
            else "STARTUP_WEB_LISTENER_BLOCKED",
        ),
    )


def run_startup_preflight(
    project_dir: str | Path,
    *,
    mode: StartupMode | str = StartupMode.CLI,
    environ: Mapping[str, str] | None = None,
    repository_root: str | Path | None = None,
    expected_source_commit: str | None = None,
) -> StartupPreflightReport:
    """Inspect startup configuration/state and return only bounded safe facts."""

    source = os.environ if environ is None else environ
    try:
        selected_mode = mode if isinstance(mode, StartupMode) else StartupMode(mode)
    except (TypeError, ValueError):
        selected_mode = StartupMode.CLI
        inspection = _Inspection(selected_mode)
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_MODE_INVALID")
        return _build_report(inspection, source)

    inspection = _Inspection(selected_mode)
    try:
        environment_items = tuple(source.items())
    except AttributeError:
        environment_items = ()
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_ENVIRONMENT_INVALID")
        return _build_report(inspection, {})
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in environment_items):
        inspection.add(StartupStatus.BLOCKED_CONFIGURATION, "STARTUP_ENVIRONMENT_INVALID")
        return _build_report(inspection, source)
    _validate_boolean_and_security_flags(inspection, source)
    _validate_runtime_owned_bounds(inspection)
    _validate_web_configuration(inspection, source)
    _validate_provider_environment_configuration(inspection, source)
    supplied_root = None if repository_root is None else Path(repository_root)
    _validate_required_inputs(
        inspection,
        Path(project_dir),
        supplied_root,
        expected_source_commit,
    )
    _validate_provider_secret_files(inspection)
    if inspection.project_dir is not None:
        try:
            inspection.state_root = _derive_state_root(inspection.project_dir, source)
            _require_safe_directory_chain(inspection.state_root)
            inspection.state_root_identity = hashlib.sha256(
                (
                    "AOIA_STARTUP_STATE_ROOT_IDENTITY_1A\x00"
                    + str(inspection.state_root)
                ).encode("utf-8")
            ).hexdigest()
        except (OSError, ValueError):
            inspection.add(StartupStatus.BLOCKED_SECURITY_INVARIANT, "STARTUP_STATE_ROOT_UNSAFE")
    if inspection.state_root is not None:
        state_dir = inspection.state_root / "state"
        _validate_state_layout(inspection, inspection.state_root)
        _validate_state_locks(inspection, state_dir)
        _validate_model_and_provider_config(inspection, state_dir)
        _validate_agent_memory(inspection, state_dir)
        _validate_memory_hats(inspection, inspection.state_root, state_dir)
        _validate_task_checkpoints(inspection, state_dir)
        _validate_idempotency(inspection, state_dir)
        _validate_recovery_state(inspection, state_dir)
        runtime_ledger = _validate_provenance(inspection, state_dir)
        _validate_anchor_configuration(inspection, source, runtime_ledger)
    else:
        _validate_anchor_configuration(
            inspection,
            source,
            Path("/invalid/runtime_provenance_log.jsonl"),
        )
    current = _final_status(inspection.findings or [])
    if current in {StartupStatus.READY, StartupStatus.READY_DEGRADED}:
        _atomic_persistence_probe(inspection)
    return _build_report(inspection, source)


def _build_report(
    inspection: _Inspection,
    environ: Mapping[str, str],
) -> StartupPreflightReport:
    findings = inspection.findings or []
    status = _final_status(findings)
    settings = tuple(sorted(inspection.settings or [], key=lambda item: item.name))
    schemas = tuple(sorted(inspection.schemas or [], key=lambda item: item.resource))
    return StartupPreflightReport(
        schema_version=STARTUP_PREFLIGHT_SCHEMA_VERSION,
        status=status,
        mode=inspection.mode,
        source_commit=inspection.source_commit,
        project_identity=inspection.project_identity,
        state_root_identity=(
            hashlib.sha256(
                ("AOIA_STARTUP_STATE_ROOT_IDENTITY_1A\x00" + str(inspection.state_root)).encode("utf-8")
            ).hexdigest()
            if inspection.state_root is not None
            else None
        ),
        configuration=_configuration_contract(environ, inspection.mode),
        bounded_settings=settings,
        capabilities=_capabilities(status, inspection.mode),
        state_schemas=schemas,
        anchor_status=inspection.anchor_status,
        anchor_id=inspection.anchor_id,
        anchor_public_key_fingerprint=inspection.anchor_public_key_fingerprint,
        reason_codes=tuple(sorted({item.reason_code for item in findings})),
    )


__all__ = [
    "ANCHOR_REGISTRY_ENV",
    "ANCHOR_ROOT_ENV",
    "ANCHOR_ROOT_FINGERPRINT_ENV",
    "AnchorConfigurationStatus",
    "BoundedSetting",
    "CapabilityDecision",
    "ConfigClassification",
    "ConfigurationObservation",
    "STARTUP_PREFLIGHT_SCHEMA_VERSION",
    "StartupMode",
    "StartupPreflightReport",
    "StartupStatus",
    "StateSchemaStatus",
    "run_startup_preflight",
]
