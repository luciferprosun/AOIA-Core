from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from runtime.git_ops.git_env import build_hardened_git_env
from runtime.safety import bounded_subprocess as bounded_subprocess_boundary
from runtime.safety.bounded_subprocess import (
    SubprocessCancelledError,
    SubprocessContainmentError,
    SubprocessResourceProfileName,
    SubprocessTimeoutPolicyError,
)
from runtime.startup_preflight import STARTUP_PREFLIGHT_SCHEMA_VERSION
from runtime.state_backup import BACKUP_SCHEMA_VERSION
from runtime.task_checkpoints import TASK_CHECKPOINT_SCHEMA_VERSION
from runtime.tools.idempotency import IDEMPOTENCY_SCHEMA_VERSION
from runtime.tools.provenance import RUNTIME_PROVENANCE_SCHEMA_VERSION
from runtime.tools.provenance_anchor import (
    ANCHOR_SCHEMA_VERSION,
    SIGNATURE_ALGORITHM,
    ProvenanceAnchorConfigurationError,
    ProvenanceAnchorCryptoUnavailable,
    _crypto,
    _load_private_key,
    _project_identity,
    _trusted_key_chain,
    _validated_registry_tip,
)


RELEASE_MANIFEST_SCHEMA_VERSION = "AOIA_RELEASE_MANIFEST_1A"
RELEASE_CORE_SCHEMA_VERSION = "AOIA_RELEASE_CORE_1A"
RELEASE_METADATA_SCHEMA_VERSION = "AOIA_RELEASE_METADATA_1A"
RELEASE_SIGNATURE_SCHEMA_VERSION = "AOIA_RELEASE_SIGNATURE_1A"
RELEASE_TEST_EVIDENCE_SCHEMA_VERSION = "AOIA_RELEASE_TEST_EVIDENCE_1A"
RELEASE_CORE_DOMAIN = b"AOIA-Core/release-manifest-core-1a\x00"
RELEASE_SCOPE_DOMAIN = b"AOIA-Core/release-source-scope-1a\x00"
RELEASE_SIGNATURE_DOMAIN = b"AOIA-Core/release-attestation-signature-1a\x00"

NZ_FOUNDATION_VERSION = "NZ_FOUNDATION_V1"
NZ_OPERATIONAL_HARDENING_VERSION = "NZ_OPERATIONAL_HARDENING_V1"
NZ_PRODUCTION_READINESS_VERSION = "NZ_PRODUCTION_READINESS_V1"

MAX_RELEASE_FILES = 8_192
MAX_RELEASE_FILE_BYTES = 64 * 1024 * 1024
MAX_RELEASE_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_RELEASE_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_RELEASE_JSON_NODES = 100_000
MAX_RELEASE_JSON_DEPTH = 20
MAX_RELEASE_JSON_STRING_BYTES = 4 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_TEST_RUNS = 10_000_000
MAX_DEPENDENCIES = 4_096
MAX_TEXT_FIELD_BYTES = 512

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_HEX_GIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_COMMAND_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_DEPENDENCY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_EXACT_PIN = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]{0,127})(?:\[[^\]]+\])?\s*==\s*"
    r"([A-Za-z0-9][A-Za-z0-9.!+_-]{0,127})\s*(?:;.*)?$"
)

_RELEASE_DIRECTORY_ROOTS = (
    "runtime",
    "tui",
    "scripts",
    "build_support",
    "tests",
    "data",
    "knowledge",
    "apps",
    "web",
)
_RELEASE_ROOT_FILES = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "run_aoia_demo.sh",
    "run_final_recording_demo.sh",
)
_RELEASE_DOCUMENTS = (
    "docs/architecture/NZ_OPERATIONAL_HARDENING_V1.md",
    "docs/architecture/NZ_PRODUCTION_READINESS_V1.md",
)
_GIT_SCOPE_ARGUMENTS = (
    *_RELEASE_DIRECTORY_ROOTS,
    "docs/architecture",
    *_RELEASE_ROOT_FILES,
)
_DEPENDENCY_DECLARATION_PATHS = (
    "pyproject.toml",
    "runtime/requirements.txt",
)
_BLOCKED_COMPONENTS = frozenset(
    {
        ".aoia_state",
        ".azure",
        ".aws",
        ".cache",
        ".docker",
        ".fleet",
        ".git",
        ".gnupg",
        ".gradle",
        ".history",
        ".hypothesis",
        ".idea",
        ".kube",
        ".local-secrets",
        ".local-history",
        ".mypy_cache",
        ".next",
        ".nox",
        ".nuxt",
        ".parcel-cache",
        ".private",
        ".pytest_cache",
        ".ruff_cache",
        ".runtime-secrets",
        ".secrets",
        ".ssh",
        ".svelte-kit",
        ".terraform",
        ".turbo",
        ".tox",
        ".venv",
        ".vite",
        ".vscode",
        "__pycache__",
        "build",
        "cache",
        "credentials",
        "coverage",
        "dist",
        "htmlcov",
        "logs",
        "node_modules",
        "out",
        "private",
        "runtime-storage",
        "screenshots",
        "site-packages",
        "secrets",
        "temp",
        "target",
        "test-results",
        "test_results",
        "thread_stores",
        "threads",
        "tmp",
        "wheelhouse",
    }
)
_BLOCKED_CONFIG_STORE_COMPONENTS = frozenset({"gcloud", "gh", "pip", "pypoetry"})
_BLOCKED_FILENAMES = frozenset(
    {
        "client_secret.json",
        ".coverage",
        ".ds_store",
        ".eslintcache",
        ".git-credentials",
        ".htpasswd",
        ".netrc",
        ".npmrc",
        ".my.cnf",
        ".pgpass",
        ".pypirc",
        ".sentryclirc",
        ".testmondata",
        ".vault-token",
        "application_default_credentials.json",
        "auth.json",
        "coverage.xml",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ecdsa_sk",
        "id_ed25519",
        "id_ed25519_sk",
        "id_rsa",
        "junit.xml",
        "kubeconfig",
        "token.json",
        "tokens.json",
        "thumbs.db",
        "wrangler.toml",
    }
)
_BLOCKED_SUFFIXES = frozenset(
    {
        ".credentials",
        ".jks",
        ".key",
        ".keystore",
        ".p12",
        ".pem",
        ".pfx",
        ".pk8",
        ".pkcs8",
        ".pkcs12",
        ".secret",
        ".token",
    }
)
_BLOCKED_TEMP_SUFFIXES = frozenset(
    {".bak", ".orig", ".prof", ".pyc", ".rej", ".swp", ".tmp"}
)


class ReleaseStatus(str, Enum):
    RELEASE_VALID = "RELEASE_VALID"
    RELEASE_UNSIGNED = "RELEASE_UNSIGNED"
    RELEASE_SOURCE_MISMATCH = "RELEASE_SOURCE_MISMATCH"
    RELEASE_FILE_MISMATCH = "RELEASE_FILE_MISMATCH"
    RELEASE_DEPENDENCY_MISMATCH = "RELEASE_DEPENDENCY_MISMATCH"
    RELEASE_SCHEMA_UNSUPPORTED = "RELEASE_SCHEMA_UNSUPPORTED"
    RELEASE_INCOMPLETE = "RELEASE_INCOMPLETE"
    RELEASE_SIGNATURE_INVALID = "RELEASE_SIGNATURE_INVALID"
    RELEASE_UNKNOWN_KEY = "RELEASE_UNKNOWN_KEY"
    RELEASE_CRYPTO_UNAVAILABLE = "RELEASE_CRYPTO_UNAVAILABLE"


class DependencyClassification(str, Enum):
    DECLARED_DEPENDENCY = "DECLARED_DEPENDENCY"
    PINNED_DEPENDENCY = "PINNED_DEPENDENCY"
    OBSERVED_INSTALLED_DEPENDENCY = "OBSERVED_INSTALLED_DEPENDENCY"


class ReleaseFileClassification(str, Enum):
    RUNTIME_SOURCE = "RUNTIME_SOURCE"
    TUI_SOURCE = "TUI_SOURCE"
    SCRIPT_SOURCE = "SCRIPT_SOURCE"
    BUILD_SOURCE = "BUILD_SOURCE"
    TEST_SOURCE = "TEST_SOURCE"
    RUNTIME_DATA = "RUNTIME_DATA"
    KNOWLEDGE_ASSET = "KNOWLEDGE_ASSET"
    APPLICATION_SOURCE = "APPLICATION_SOURCE"
    DEPENDENCY_DECLARATION = "DEPENDENCY_DECLARATION"
    DOCUMENTATION = "DOCUMENTATION"
    RELEASE_METADATA = "RELEASE_METADATA"


class TestEvidenceDisposition(str, Enum):
    VERIFIED_PASS = "VERIFIED_PASS"
    VERIFIED_WITH_KNOWN_BASELINE_FAILURES = (
        "VERIFIED_WITH_KNOWN_BASELINE_FAILURES"
    )


class ReleaseAttestationError(RuntimeError):
    reason_code = "RELEASE_ATTESTATION_ERROR"


class ReleaseSourceError(ReleaseAttestationError):
    reason_code = "RELEASE_SOURCE_INVALID"


class ReleaseSigningError(ReleaseAttestationError):
    reason_code = "RELEASE_SIGNING_FAILED"


class _ReleasePathExcluded(ValueError):
    pass


@dataclass(frozen=True)
class TestEvidence:
    command_id: str
    source_commit: str
    git_tree_identity: str
    run_count: int
    pass_count: int
    failure_count: int
    error_count: int
    skip_count: int
    failure_names_sha256: str
    error_names_sha256: str
    skip_names_sha256: str
    output_log_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, str) or not _COMMAND_ID.fullmatch(
            self.command_id
        ):
            raise ValueError("test command identity is invalid")
        _git_digest(self.source_commit, label="test evidence source commit")
        _git_digest(self.git_tree_identity, label="test evidence source tree")
        counts = (
            self.run_count,
            self.pass_count,
            self.failure_count,
            self.error_count,
            self.skip_count,
        )
        if any(type(value) is not int for value in counts):
            raise ValueError("test evidence counts must be exact integers")
        if any(value < 0 or value > MAX_TEST_RUNS for value in counts):
            raise ValueError("test evidence counts exceed their bound")
        if self.run_count != sum(counts[1:]):
            raise ValueError("test evidence counts are incoherent")
        if self.run_count == 0 or self.pass_count == 0:
            raise ValueError("test evidence must include at least one passing test")
        for value in (
            self.failure_names_sha256,
            self.error_names_sha256,
            self.skip_names_sha256,
            self.output_log_sha256,
        ):
            if not isinstance(value, str) or not _HEX_64.fullmatch(value):
                raise ValueError("test evidence digest is invalid")

    @property
    def disposition(self) -> TestEvidenceDisposition:
        if self.failure_count == 0 and self.error_count == 0:
            return TestEvidenceDisposition.VERIFIED_PASS
        return TestEvidenceDisposition.VERIFIED_WITH_KNOWN_BASELINE_FAILURES

    def to_core(self) -> dict[str, object]:
        return {
            "schema_version": RELEASE_TEST_EVIDENCE_SCHEMA_VERSION,
            "command_id": self.command_id,
            "source_commit": self.source_commit,
            "git_tree_identity": self.git_tree_identity,
            "run_count": self.run_count,
            "pass_count": self.pass_count,
            "failure_count": self.failure_count,
            "error_count": self.error_count,
            "skip_count": self.skip_count,
            "failure_names_sha256": self.failure_names_sha256,
            "error_names_sha256": self.error_names_sha256,
            "skip_names_sha256": self.skip_names_sha256,
            "output_log_sha256": self.output_log_sha256,
            "disposition": self.disposition.value,
        }


@dataclass(frozen=True)
class ReleaseBuildResult:
    manifest: dict[str, object]
    release_id: str
    core_hash: str
    signed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, dict):
            raise ValueError("release manifest result is invalid")
        if (
            not isinstance(self.release_id, str)
            or self.release_id != f"release_{self.core_hash}"
        ):
            raise ValueError("release identity is invalid")
        _digest(self.core_hash, label="release core hash")
        if type(self.signed) is not bool:
            raise ValueError("release signature state must be boolean")
        if (
            self.manifest.get("release_id") != self.release_id
            or self.manifest.get("core_hash") != self.core_hash
        ):
            raise ValueError("release build result conflicts with its manifest identity")
        try:
            envelope, core, _metadata, signature = _validate_envelope(self.manifest)
            _validate_core(core)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("release build result contains an invalid manifest") from exc
        if (
            envelope["release_id"] != self.release_id
            or envelope["core_hash"] != self.core_hash
        ):
            raise ValueError("release build identity is not bound to its validated core")
        if self.signed != (signature is not None):
            raise ValueError("release build signature state conflicts with its manifest")


@dataclass(frozen=True)
class ReleaseVerificationResult:
    status: ReleaseStatus
    release_id: str | None = None
    core_hash: str | None = None
    source_commit: str | None = None
    signed: bool = False
    test_disposition: str | None = None
    message_safe: str = "Release verification failed."

    def __post_init__(self) -> None:
        if not isinstance(self.status, ReleaseStatus):
            object.__setattr__(self, "status", ReleaseStatus(self.status))
        if self.release_id is not None:
            if not isinstance(self.release_id, str) or not self.release_id.startswith(
                "release_"
            ):
                raise ValueError("verified release identity is invalid")
        if self.core_hash is not None:
            _digest(self.core_hash, label="verified release core hash")
            if self.release_id is not None and self.release_id != f"release_{self.core_hash}":
                raise ValueError("verified release identity conflicts with its core")
        if self.source_commit is not None:
            _git_digest(self.source_commit, label="verified source commit")
        if type(self.signed) is not bool:
            raise ValueError("verified signature state must be boolean")
        if self.test_disposition is not None:
            TestEvidenceDisposition(self.test_disposition)
        _bounded_text(self.message_safe, label="release verification message", maximum=1024)
        if self.status in {
            ReleaseStatus.RELEASE_VALID,
            ReleaseStatus.RELEASE_UNSIGNED,
        }:
            if (
                self.release_id is None
                or self.core_hash is None
                or self.source_commit is None
                or self.test_disposition is None
            ):
                raise ValueError("successful release result is incomplete")
            if self.status is ReleaseStatus.RELEASE_VALID and not self.signed:
                raise ValueError("valid signed release result must be signed")
            if self.status is ReleaseStatus.RELEASE_UNSIGNED and self.signed:
                raise ValueError("unsigned release result cannot be signed")

    @property
    def valid(self) -> bool:
        return self.status is ReleaseStatus.RELEASE_VALID

    @property
    def content_valid(self) -> bool:
        return self.status in {
            ReleaseStatus.RELEASE_VALID,
            ReleaseStatus.RELEASE_UNSIGNED,
        }


@dataclass(frozen=True)
class _SourceSnapshot:
    source_commit: str
    git_tree_identity: str
    release_scope_identity: str
    files: tuple[dict[str, object], ...]
    file_count: int
    total_bytes: int
    index_entries: tuple[tuple[str, str, str], ...]


def _bounded_json_shape(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    seen_containers: set[int] = set()
    node_count = 0
    string_bytes = 0
    while stack:
        current, depth = stack.pop()
        node_count += 1
        if node_count > MAX_RELEASE_JSON_NODES or depth > MAX_RELEASE_JSON_DEPTH:
            raise ValueError("release JSON shape exceeds its bound")
        if current is None or type(current) in {bool, int}:
            continue
        if isinstance(current, str):
            string_bytes += len(current.encode("utf-8"))
            if string_bytes > MAX_RELEASE_JSON_STRING_BYTES:
                raise ValueError("release JSON string content exceeds its bound")
            continue
        if isinstance(current, dict):
            identity = id(current)
            if identity in seen_containers:
                raise ValueError("release JSON contains a cycle or shared container")
            seen_containers.add(identity)
            for key, item in current.items():
                if not isinstance(key, str):
                    raise ValueError("release JSON object key is not text")
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))
            continue
        if isinstance(current, list):
            identity = id(current)
            if identity in seen_containers:
                raise ValueError("release JSON contains a cycle or shared container")
            seen_containers.add(identity)
            stack.extend((item, depth + 1) for item in current)
            continue
        raise ValueError("release JSON contains an unsupported value type")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def encode_release_manifest(manifest: object) -> bytes:
    _bounded_json_shape(manifest)
    try:
        payload = _canonical_json(manifest) + b"\n"
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("release manifest cannot be encoded canonically") from exc
    if len(payload) > MAX_RELEASE_MANIFEST_BYTES:
        raise ValueError("release manifest exceeds its serialized bound")
    return payload


def decode_release_manifest(payload: bytes) -> dict[str, Any]:
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_RELEASE_MANIFEST_BYTES:
        raise ValueError("release manifest bytes are empty or over their bound")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("release manifest contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("release manifest contains a non-finite number")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("release manifest bytes are malformed") from exc
    if not isinstance(value, dict):
        raise ValueError("release manifest root must be an object")
    _bounded_json_shape(value)
    if encode_release_manifest(value) != payload:
        raise ValueError("release manifest bytes are not canonical")
    return value


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _core_hash(core: Mapping[str, object]) -> str:
    _bounded_json_shape(core)
    encoded = _canonical_json(core)
    if len(encoded) > MAX_RELEASE_MANIFEST_BYTES:
        raise ValueError("release core exceeds its serialized bound")
    return _sha256(RELEASE_CORE_DOMAIN + encoded)


def _scope_hash(rows: Sequence[Mapping[str, object]]) -> str:
    return _sha256(RELEASE_SCOPE_DOMAIN + _canonical_json(list(rows)))


def _exact_keys(value: object, expected: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} schema is incomplete or has unknown fields")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} keys are invalid")
    return value


def _exact_int(value: object, *, label: str, maximum: int) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise ValueError(f"{label} is not an exact bounded integer")
    return value


def _bounded_text(value: object, *, label: str, maximum: int = MAX_TEXT_FIELD_BYTES) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{label} is invalid")
    if any(ord(character) < 32 or ord(character) > 126 for character in value):
        raise ValueError(f"{label} contains non-portable characters")
    return value


def _digest(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _HEX_64.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _git_digest(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _HEX_GIT.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _safe_repository_root(repository_root: Path) -> Path:
    path = Path(repository_root)
    if not path.is_absolute():
        raise ReleaseSourceError("Repository root must be absolute.")
    lexical = Path(os.path.abspath(path))
    try:
        resolved = path.resolve(strict=True)
        metadata = path.lstat()
    except OSError as exc:
        raise ReleaseSourceError("Repository root is unavailable.") from exc
    if lexical != resolved or stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(
        metadata.st_mode
    ):
        raise ReleaseSourceError("Repository root is not a canonical directory.")
    return resolved


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("release path is invalid")
    if len(value.encode("utf-8")) > MAX_TEXT_FIELD_BYTES:
        raise ValueError("release path exceeds its bound")
    if "\\" in value or "\x00" in value or any(
        ord(character) < 32 or ord(character) > 126 for character in value
    ):
        raise ValueError("release path is not portable ASCII")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix():
        raise ValueError("release path is not canonical relative POSIX")
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("release path contains an unsafe component")
    folded = [part.casefold() for part in path.parts]
    if any(
        part in _BLOCKED_COMPONENTS or part.endswith(".egg-info")
        for part in folded
    ):
        raise _ReleasePathExcluded("release path is an excluded runtime resource")
    if any(
        folded[index] == ".config"
        and folded[index + 1] in _BLOCKED_CONFIG_STORE_COMPONENTS
        for index in range(len(folded) - 1)
    ):
        raise _ReleasePathExcluded("release path is an excluded credential store")
    if len(folded) >= 2 and folded[0] == "runtime" and folded[1] in {
        "logs",
        "screenshots",
        "state",
    }:
        raise _ReleasePathExcluded("release path is an excluded mutable runtime resource")
    filename = folded[-1]
    if filename.startswith(".env") or filename in _BLOCKED_FILENAMES:
        raise _ReleasePathExcluded("release path is an excluded credential resource")
    if filename.startswith(".coverage."):
        raise _ReleasePathExcluded("release path is excluded local test output")
    if filename.endswith(".local.env"):
        raise _ReleasePathExcluded("release path is an excluded secret resource")
    suffix = PurePosixPath(filename).suffix
    normalized_stem = re.sub(r"[-_.\s]+", "_", PurePosixPath(filename).stem)
    data_like = suffix in {
        "",
        ".cfg",
        ".env",
        ".ini",
        ".json",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    if data_like and (
        normalized_stem.startswith(
            ("client_secret", "service_account", "firebase")
        )
        or any(
            marker in normalized_stem
            for marker in (
                "access_token",
                "api_key",
                "credential",
                "operator_token",
                "password",
                "private_key",
                "refresh_token",
                "secret",
                "signing_key",
            )
        )
    ):
        raise _ReleasePathExcluded("release path is an excluded secret resource")
    if suffix in _BLOCKED_SUFFIXES:
        raise _ReleasePathExcluded("release path is an excluded key resource")
    if filename.endswith("~") or PurePosixPath(filename).suffix in _BLOCKED_TEMP_SUFFIXES:
        raise _ReleasePathExcluded("release path is an excluded temporary resource")
    allowed = (
        path.parts[0] in _RELEASE_DIRECTORY_ROOTS
        or value in _RELEASE_ROOT_FILES
        or value in _RELEASE_DOCUMENTS
    )
    if not allowed:
        raise _ReleasePathExcluded("release path is outside the explicit allowlist")
    return value


def _classify_path(path: str) -> ReleaseFileClassification:
    if path in _DEPENDENCY_DECLARATION_PATHS:
        return ReleaseFileClassification.DEPENDENCY_DECLARATION
    if path in _RELEASE_DOCUMENTS:
        return ReleaseFileClassification.DOCUMENTATION
    first = PurePosixPath(path).parts[0]
    if first == "runtime":
        return ReleaseFileClassification.RUNTIME_SOURCE
    if first == "tui":
        return ReleaseFileClassification.TUI_SOURCE
    if first == "scripts":
        return ReleaseFileClassification.SCRIPT_SOURCE
    if first == "build_support":
        return ReleaseFileClassification.BUILD_SOURCE
    if first == "tests":
        return ReleaseFileClassification.TEST_SOURCE
    if first == "data":
        return ReleaseFileClassification.RUNTIME_DATA
    if first == "knowledge":
        return ReleaseFileClassification.KNOWLEDGE_ASSET
    if first == "apps":
        return ReleaseFileClassification.APPLICATION_SOURCE
    if first == "web":
        return ReleaseFileClassification.APPLICATION_SOURCE
    if path in {"run_aoia_demo.sh", "run_final_recording_demo.sh"}:
        return ReleaseFileClassification.SCRIPT_SOURCE
    return ReleaseFileClassification.RELEASE_METADATA


def _binding(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_tracked_file(repository_root: Path, relative_path: str) -> tuple[bytes, int]:
    relative = _safe_relative_path(relative_path)
    parts = PurePosixPath(relative).parts
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptors: list[int] = []
    directory_bindings: list[tuple[int, ...]] = []
    descriptor: int | None = None
    try:
        root_descriptor = os.open(repository_root, directory_flags)
        directory_descriptors.append(root_descriptor)
        root_metadata = os.fstat(root_descriptor)
        if not stat.S_ISDIR(root_metadata.st_mode):
            raise ReleaseSourceError("Release source root binding is unsafe.")
        directory_bindings.append(_binding(root_metadata))
        for part in parts[:-1]:
            parent_descriptor = directory_descriptors[-1]
            visible = os.stat(part, dir_fd=parent_descriptor, follow_symlinks=False)
            child_descriptor = os.open(part, directory_flags, dir_fd=parent_descriptor)
            opened = os.fstat(child_descriptor)
            if (
                stat.S_ISLNK(visible.st_mode)
                or not stat.S_ISDIR(visible.st_mode)
                or _binding(visible) != _binding(opened)
            ):
                os.close(child_descriptor)
                raise ReleaseSourceError("Release source parent binding is unsafe.")
            directory_descriptors.append(child_descriptor)
            directory_bindings.append(_binding(opened))
        parent_descriptor = directory_descriptors[-1]
        before = os.stat(parts[-1], dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 0
            or before.st_size > MAX_RELEASE_FILE_BYTES
        ):
            raise ReleaseSourceError("Release source file is not a bounded unique regular file.")
        descriptor = os.open(parts[-1], file_flags, dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        if (
            _binding(opened) != _binding(before)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
        ):
            raise ReleaseSourceError("Release source binding changed during open.")
        payload = bytearray()
        while len(payload) <= MAX_RELEASE_FILE_BYTES:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_RELEASE_FILE_BYTES + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != opened.st_size or len(payload) > MAX_RELEASE_FILE_BYTES:
            raise ReleaseSourceError("Release source changed or exceeded its bound while read.")
        after = os.fstat(descriptor)
        visible_file = os.stat(
            parts[-1], dir_fd=parent_descriptor, follow_symlinks=False
        )
        if (
            _binding(after) != _binding(opened)
            or _binding(visible_file) != _binding(opened)
        ):
            raise ReleaseSourceError("Release source binding changed while read.")
        for index, directory_descriptor in enumerate(directory_descriptors):
            if _binding(os.fstat(directory_descriptor)) != directory_bindings[index]:
                raise ReleaseSourceError("Release source parent changed while read.")
            if index:
                parent_descriptor = directory_descriptors[index - 1]
                visible_parent = os.stat(
                    parts[index - 1],
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if _binding(visible_parent) != directory_bindings[index]:
                    raise ReleaseSourceError("Release source parent binding changed.")
        return bytes(payload), opened.st_mode
    except OSError as exc:
        raise ReleaseSourceError("Release source file could not be read safely.") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)


def _git_output(repository_root: Path, arguments: Sequence[str]) -> bytes:
    argv = ("git", *arguments)
    try:
        result = bounded_subprocess_boundary.run_bounded_subprocess(
            argv,
            cwd=repository_root,
            env=build_hardened_git_env(),
            shell=False,
            capture_output=True,
            text=False,
            timeout=30,
            resource_profile=SubprocessResourceProfileName.GIT,
        )
    except (
        OSError,
        ValueError,
        subprocess.SubprocessError,
        SubprocessCancelledError,
        SubprocessContainmentError,
        SubprocessTimeoutPolicyError,
    ) as exc:
        raise ReleaseSourceError("Bounded local Git inspection failed.") from exc
    stdout = bytes(result.stdout or b"")
    stderr = bytes(result.stderr or b"")
    if (
        result.returncode != 0
        or getattr(result, "stdout_truncated", False)
        or getattr(result, "stderr_truncated", False)
        or len(stdout) > MAX_GIT_OUTPUT_BYTES
        or len(stderr) > MAX_GIT_OUTPUT_BYTES
    ):
        raise ReleaseSourceError("Bounded local Git inspection was incomplete.")
    return stdout


def _single_git_line(payload: bytes, *, label: str) -> str:
    try:
        value = payload.decode("ascii", errors="strict").strip()
    except UnicodeError as exc:
        raise ReleaseSourceError(f"{label} is not ASCII.") from exc
    if not value or "\n" in value or "\r" in value:
        raise ReleaseSourceError(f"{label} is malformed.")
    return value


def _git_metadata(
    repository_root: Path,
) -> tuple[
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, str, str], ...],
]:
    toplevel = _single_git_line(
        _git_output(repository_root, ("rev-parse", "--show-toplevel")),
        label="Git repository root",
    )
    try:
        resolved_toplevel = Path(toplevel).resolve(strict=True)
    except OSError as exc:
        raise ReleaseSourceError("Git repository root is unavailable.") from exc
    if resolved_toplevel != repository_root:
        raise ReleaseSourceError("Git repository root does not match the release root.")
    head = _single_git_line(
        _git_output(repository_root, ("rev-parse", "--verify", "HEAD")),
        label="Git source commit",
    )
    tree = _single_git_line(
        _git_output(repository_root, ("rev-parse", "--verify", "HEAD^{tree}")),
        label="Git source tree",
    )
    _git_digest(head, label="Git source commit")
    _git_digest(tree, label="Git source tree")
    tracked_raw = _git_output(
        repository_root,
        ("ls-files", "-z", "--cached", "--", *_GIT_SCOPE_ARGUMENTS),
    )
    dirty_raw = _git_output(
        repository_root,
        ("diff", "--name-only", "-z", "HEAD", "--"),
    )
    untracked_raw = _git_output(
        repository_root,
        (
            "ls-files",
            "--others",
            "-z",
            "--",
            *_GIT_SCOPE_ARGUMENTS,
        ),
    )
    stage_raw = _git_output(
        repository_root,
        ("ls-files", "--stage", "-z", "--", *_GIT_SCOPE_ARGUMENTS),
    )
    flags_raw = _git_output(
        repository_root,
        ("ls-files", "-v", "-z", "--", *_GIT_SCOPE_ARGUMENTS),
    )
    try:
        tracked_values = [part.decode("utf-8", errors="strict") for part in tracked_raw.split(b"\0") if part]
        dirty_values = [part.decode("utf-8", errors="strict") for part in dirty_raw.split(b"\0") if part]
        untracked_values = [part.decode("utf-8", errors="strict") for part in untracked_raw.split(b"\0") if part]
    except UnicodeError as exc:
        raise ReleaseSourceError("Git release paths are not valid UTF-8.") from exc
    tracked: list[str] = []
    folded: set[str] = set()
    seen: set[str] = set()
    for value in tracked_values:
        try:
            safe = _safe_relative_path(value)
        except _ReleasePathExcluded as exc:
            if value.startswith("web/"):
                raise ReleaseSourceError(
                    "A served web path is excluded from the release policy."
                ) from exc
            # A tracked credential/cache path is outside the release candidate,
            # not evidence that it was included.
            continue
        except ValueError as exc:
            raise ReleaseSourceError("Tracked release path is malformed.") from exc
        if safe in seen or safe.casefold() in folded:
            raise ReleaseSourceError("Release source paths collide or are duplicated.")
        seen.add(safe)
        folded.add(safe.casefold())
        tracked.append(safe)
    dirty: list[str] = []
    for value in dirty_values:
        try:
            dirty.append(_safe_relative_path(value))
        except ValueError:
            dirty.append("<tracked-change-outside-release-scope>")
    untracked: list[str] = []
    for value in untracked_values:
        try:
            untracked.append(_safe_relative_path(value))
        except _ReleasePathExcluded as exc:
            if value.startswith("web/"):
                raise ReleaseSourceError(
                    "A served web path is excluded from the release policy."
                ) from exc
            continue
        except ValueError as exc:
            raise ReleaseSourceError("Untracked release path is malformed.") from exc
    index_entries: list[tuple[str, str, str]] = []
    for raw in stage_raw.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, raw_path = raw.split(b"\t", 1)
            mode_bytes, blob_bytes, stage_bytes = metadata.split(b" ")
            path = raw_path.decode("utf-8", errors="strict")
            mode = mode_bytes.decode("ascii", errors="strict")
            blob = blob_bytes.decode("ascii", errors="strict")
            stage = stage_bytes.decode("ascii", errors="strict")
        except (UnicodeError, ValueError) as exc:
            raise ReleaseSourceError("Git index entry is malformed.") from exc
        try:
            safe = _safe_relative_path(path)
        except _ReleasePathExcluded as exc:
            if path.startswith("web/"):
                raise ReleaseSourceError(
                    "A served web path is excluded from the release policy."
                ) from exc
            continue
        except ValueError as exc:
            raise ReleaseSourceError("Git index release path is malformed.") from exc
        if stage != "0" or mode not in {"100644", "100755"}:
            raise ReleaseSourceError("Git index contains an unsupported release entry.")
        _git_digest(blob, label="Git release blob")
        index_entries.append((safe, mode, blob))
    flag_paths: list[str] = []
    for raw in flags_raw.split(b"\0"):
        if not raw:
            continue
        if len(raw) < 3 or raw[1:2] != b" ":
            raise ReleaseSourceError("Git index flag entry is malformed.")
        try:
            path = raw[2:].decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise ReleaseSourceError("Git index flag path is malformed.") from exc
        try:
            safe = _safe_relative_path(path)
        except _ReleasePathExcluded as exc:
            if path.startswith("web/"):
                raise ReleaseSourceError(
                    "A served web path is excluded from the release policy."
                ) from exc
            continue
        except ValueError as exc:
            raise ReleaseSourceError("Git index flag path is malformed.") from exc
        if raw[:1] != b"H":
            raise ReleaseSourceError("Git index release entry has unsafe state flags.")
        flag_paths.append(safe)
    canonical_index = tuple(sorted(index_entries))
    if (
        tuple(sorted(flag_paths)) != tuple(sorted(tracked))
        or tuple(path for path, _mode, _blob in canonical_index)
        != tuple(sorted(tracked))
    ):
        raise ReleaseSourceError("Git index and release file inventory disagree.")
    return (
        head,
        tree,
        tuple(sorted(tracked)),
        tuple(sorted(set(dirty))),
        tuple(sorted(set(untracked))),
        canonical_index,
    )


def _capture_source(repository_root: Path) -> _SourceSnapshot:
    root = _safe_repository_root(repository_root)
    first = _git_metadata(root)
    head, tree, tracked, dirty, untracked, index_entries = first
    if dirty or untracked:
        raise ReleaseSourceError("Release-scoped source is not clean.")
    if not tracked or len(tracked) > MAX_RELEASE_FILES:
        raise ReleaseSourceError("Release file set is empty or exceeds its bound.")
    rows: list[dict[str, object]] = []
    total = 0
    index_by_path = {
        path: (mode, blob) for path, mode, blob in index_entries
    }
    for relative in tracked:
        payload, file_mode = _read_tracked_file(root, relative)
        index_mode, index_blob = index_by_path[relative]
        expected_mode = "100755" if stat.S_IMODE(file_mode) & 0o111 else "100644"
        algorithm = "sha1" if len(index_blob) == 40 else "sha256"
        blob_material = f"blob {len(payload)}\0".encode("ascii") + payload
        actual_blob = hashlib.new(algorithm, blob_material).hexdigest()
        if index_mode != expected_mode or actual_blob != index_blob:
            raise ReleaseSourceError(
                "Release source bytes or mode do not match the committed Git object."
            )
        total += len(payload)
        if total > MAX_RELEASE_TOTAL_BYTES:
            raise ReleaseSourceError("Release source exceeds its total size bound.")
        rows.append(
            {
                "path": relative,
                "classification": _classify_path(relative).value,
                "size_bytes": len(payload),
                "sha256": _sha256(payload),
            }
        )
    second = _git_metadata(root)
    if second != first:
        raise ReleaseSourceError("Release source changed during capture.")
    canonical_rows = tuple(sorted(rows, key=lambda row: str(row["path"])))
    return _SourceSnapshot(
        source_commit=head,
        git_tree_identity=tree,
        release_scope_identity=_scope_hash(canonical_rows),
        files=canonical_rows,
        file_count=len(canonical_rows),
        total_bytes=total,
        index_entries=index_entries,
    )


def _normalize_dependency_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _dependency_requirement_row(
    requirement: object,
    *,
    declaration_path: str,
) -> dict[str, object]:
    text = _bounded_text(
        requirement,
        label="dependency requirement",
        maximum=2_048,
    ).strip()
    match = _DEPENDENCY_NAME.match(text)
    if match is None:
        raise ReleaseSourceError("Dependency declaration is unsupported.")
    name = _normalize_dependency_name(match.group(0))
    pinned = _EXACT_PIN.fullmatch(text)
    classification = (
        DependencyClassification.PINNED_DEPENDENCY
        if pinned is not None
        else DependencyClassification.DECLARED_DEPENDENCY
    )
    version = None if pinned is None else pinned.group(2)
    return {
        "classification": classification.value,
        "name": name,
        "declaration_path": declaration_path,
        "requirement_sha256": _sha256(text.encode("utf-8")),
        "version": version,
    }


def _requirements_file_entries(payload: bytes, *, path: str) -> list[dict[str, object]]:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ReleaseSourceError("Dependency declaration is not valid UTF-8.") from exc
    entries: list[dict[str, object]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-", "--")):
            raise ReleaseSourceError("Dependency declaration directives are unsupported offline.")
        entries.append(_dependency_requirement_row(line, declaration_path=path))
    return entries


def _pyproject_entries(
    payload: bytes,
) -> tuple[str, list[dict[str, object]]]:
    try:
        value = tomllib.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseSourceError("pyproject.toml is malformed.") from exc
    if not isinstance(value, dict):
        raise ReleaseSourceError("pyproject.toml root is invalid.")
    project = value.get("project")
    if not isinstance(project, dict):
        raise ReleaseSourceError("pyproject.toml project table is missing.")
    requires_python = _bounded_text(
        project.get("requires-python"),
        label="Python compatibility declaration",
    )
    dynamic = project.get("dynamic", [])
    if not isinstance(dynamic, list) or any(
        not isinstance(item, str) for item in dynamic
    ):
        raise ReleaseSourceError("Dynamic project metadata is malformed.")
    if {item.casefold() for item in dynamic} & {
        "dependencies",
        "optional-dependencies",
    }:
        raise ReleaseSourceError(
            "Dynamic dependencies cannot be inventoried reproducibly offline."
        )
    requirement_sources: list[tuple[str, object]] = []
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ReleaseSourceError("Project dependency declarations are malformed.")
    requirement_sources.extend(("pyproject.toml", item) for item in dependencies)
    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, dict) or any(
        not isinstance(group, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", group) is None
        or not isinstance(items, list)
        for group, items in optional.items()
    ):
        raise ReleaseSourceError("Optional dependency declarations are malformed.")
    for group in sorted(optional):
        requirement_sources.extend(
            (f"pyproject.toml#optional:{group}", item) for item in optional[group]
        )
    build_system = value.get("build-system", {})
    if not isinstance(build_system, dict):
        raise ReleaseSourceError("Build dependency declarations are malformed.")
    build_requires = build_system.get("requires", [])
    if not isinstance(build_requires, list):
        raise ReleaseSourceError("Build dependency declarations are malformed.")
    requirement_sources.extend(
        ("pyproject.toml#build-system", item) for item in build_requires
    )
    rows = [
        _dependency_requirement_row(item, declaration_path=source)
        for source, item in requirement_sources
    ]
    return requires_python, rows


def _observed_dependency_rows(
    observed_installed: Sequence[tuple[str, str]] | None,
) -> list[dict[str, object]]:
    if observed_installed is None:
        observations: list[tuple[str, str]] = []
        try:
            for distribution in importlib.metadata.distributions():
                name = distribution.metadata.get("Name")
                version = distribution.version
                if isinstance(name, str) and isinstance(version, str):
                    observations.append((name, version))
        except Exception as exc:
            raise ReleaseSourceError(
                "Installed dependency inventory could not be read offline."
            ) from exc
    else:
        if isinstance(observed_installed, (str, bytes)) or not isinstance(
            observed_installed, Sequence
        ):
            raise ValueError("observed dependency inventory must be a sequence")
        observations = list(observed_installed)
    if len(observations) > MAX_DEPENDENCIES:
        raise ReleaseSourceError("Installed dependency inventory exceeds its bound.")
    unique: set[tuple[str, str]] = set()
    for observation in observations:
        if (
            not isinstance(observation, tuple)
            or len(observation) != 2
            or not all(isinstance(item, str) for item in observation)
        ):
            raise ValueError("observed dependency entry is invalid")
        raw_name, raw_version = observation
        name_text = _bounded_text(raw_name, label="observed dependency name").strip()
        version = _bounded_text(raw_version, label="observed dependency version").strip()
        if _DEPENDENCY_NAME.fullmatch(name_text) is None:
            raise ValueError("observed dependency name is invalid")
        unique.add((_normalize_dependency_name(name_text), version))
    return [
        {
            "classification": DependencyClassification.OBSERVED_INSTALLED_DEPENDENCY.value,
            "name": name,
            "version": version,
        }
        for name, version in sorted(unique)
    ]


def _dependency_facts(
    repository_root: Path,
    *,
    observed_installed: Sequence[tuple[str, str]] | None,
) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...], str]:
    file_rows: list[dict[str, object]] = []
    payloads: dict[str, bytes] = {}
    for path in _DEPENDENCY_DECLARATION_PATHS:
        payload, _file_mode = _read_tracked_file(repository_root, path)
        payloads[path] = payload
        file_rows.append(
            {
                "path": path,
                "size_bytes": len(payload),
                "sha256": _sha256(payload),
            }
        )
    requires_python, inventory = _pyproject_entries(payloads["pyproject.toml"])
    inventory.extend(
        _requirements_file_entries(
            payloads["runtime/requirements.txt"],
            path="runtime/requirements.txt",
        )
    )
    inventory.extend(_observed_dependency_rows(observed_installed))
    if len(inventory) > MAX_DEPENDENCIES:
        raise ReleaseSourceError("Dependency inventory exceeds its bound.")
    canonical_inventory: list[dict[str, object]] = []
    seen: set[bytes] = set()
    for row in sorted(inventory, key=lambda item: _canonical_json(item)):
        encoded = _canonical_json(row)
        if encoded not in seen:
            seen.add(encoded)
            canonical_inventory.append(row)
    return (
        tuple(sorted(file_rows, key=lambda row: str(row["path"]))),
        tuple(canonical_inventory),
        requires_python,
    )


def _schema_versions() -> dict[str, str]:
    return {
        "configuration": STARTUP_PREFLIGHT_SCHEMA_VERSION,
        "checkpoint": TASK_CHECKPOINT_SCHEMA_VERSION,
        "idempotency": IDEMPOTENCY_SCHEMA_VERSION,
        "provenance": RUNTIME_PROVENANCE_SCHEMA_VERSION,
        "anchor": ANCHOR_SCHEMA_VERSION,
        "backup": BACKUP_SCHEMA_VERSION,
        "release": RELEASE_MANIFEST_SCHEMA_VERSION,
    }


def _canonical_timestamp(clock: Callable[[], dt.datetime] | None) -> str:
    value = (clock or (lambda: dt.datetime.now(dt.UTC)))()
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise ValueError("release metadata clock must return an aware datetime")
    return value.astimezone(dt.UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _expected_git_metadata(snapshot: _SourceSnapshot) -> tuple[
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, str, str], ...],
]:
    return (
        snapshot.source_commit,
        snapshot.git_tree_identity,
        tuple(str(row["path"]) for row in snapshot.files),
        (),
        (),
        snapshot.index_entries,
    )


def build_release_manifest(
    repository_root: Path,
    *,
    test_evidence: TestEvidence,
    clock: Callable[[], dt.datetime] | None = None,
) -> ReleaseBuildResult:
    """Build one deterministic release core and unsigned local envelope."""

    if not isinstance(test_evidence, TestEvidence):
        raise ValueError("release test evidence must use the validated contract")
    root = _safe_repository_root(repository_root)
    snapshot = _capture_source(root)
    if (
        test_evidence.source_commit != snapshot.source_commit
        or test_evidence.git_tree_identity != snapshot.git_tree_identity
    ):
        raise ReleaseSourceError("Test evidence does not cover this exact source tree.")
    dependency_rows, dependency_inventory, requires_python = _dependency_facts(
        root,
        observed_installed=None,
    )
    if _git_metadata(root) != _expected_git_metadata(snapshot):
        raise ReleaseSourceError("Release source changed while dependencies were inspected.")
    source_rows_by_path = {str(row["path"]): row for row in snapshot.files}
    for row in dependency_rows:
        source = source_rows_by_path.get(str(row["path"]))
        if (
            source is None
            or source["size_bytes"] != row["size_bytes"]
            or source["sha256"] != row["sha256"]
        ):
            raise ReleaseSourceError("Dependency declarations changed during capture.")
    documentation = tuple(
        {
            "path": row["path"],
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
        }
        for row in snapshot.files
        if row["classification"] == ReleaseFileClassification.DOCUMENTATION.value
    )
    core: dict[str, object] = {
        "schema_version": RELEASE_CORE_SCHEMA_VERSION,
        "source": {
            "source_commit": snapshot.source_commit,
            "git_tree_identity": snapshot.git_tree_identity,
            "release_scope_identity": snapshot.release_scope_identity,
            "file_count": snapshot.file_count,
            "total_bytes": snapshot.total_bytes,
        },
        "nz_architecture": {
            "foundation": NZ_FOUNDATION_VERSION,
            "operational_hardening": NZ_OPERATIONAL_HARDENING_VERSION,
            "production_readiness": NZ_PRODUCTION_READINESS_VERSION,
        },
        "python_compatibility": {
            "requires_python": requires_python,
            "implementation": sys.implementation.name,
            "observed_python_version": (
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
            "bytecode_in_scope": False,
        },
        "schemas": _schema_versions(),
        "dependency_declarations": list(dependency_rows),
        "dependency_inventory": list(dependency_inventory),
        "critical_files": list(snapshot.files),
        "documentation": list(documentation),
        "test_evidence": test_evidence.to_core(),
    }
    digest = _core_hash(core)
    release_id = f"release_{digest}"
    manifest: dict[str, object] = {
        "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
        "release_id": release_id,
        "core_hash": digest,
        "core": core,
        "metadata": {
            "schema_version": RELEASE_METADATA_SCHEMA_VERSION,
            "created_at": _canonical_timestamp(clock),
            "builder_python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "signature": None,
        },
    }
    return ReleaseBuildResult(
        manifest=manifest,
        release_id=release_id,
        core_hash=digest,
        signed=False,
    )


class _ReleaseSchemaUnsupported(ValueError):
    pass


class _ReleaseIncomplete(ValueError):
    pass


def _manifest_object(
    value: object,
    expected: set[str],
    *,
    label: str,
) -> dict[str, Any]:
    try:
        return _exact_keys(value, expected, label=label)
    except ValueError as exc:
        raise _ReleaseIncomplete(f"{label} is incomplete") from exc


def _schema(value: object, expected: str, *, label: str) -> None:
    if not isinstance(value, str) or value != expected:
        raise _ReleaseSchemaUnsupported(f"{label} schema is unsupported")


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
        value,
    ) is None:
        raise _ReleaseIncomplete("release timestamp is malformed")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _ReleaseIncomplete("release timestamp is malformed") from exc
    if (
        parsed.tzinfo is None
        or parsed.astimezone(dt.UTC).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        != value
    ):
        raise _ReleaseIncomplete("release timestamp is not canonical UTC")
    return value


def _validate_signature_record(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    record = _manifest_object(
        value,
        {
            "schema_version",
            "algorithm",
            "public_key_fingerprint",
            "signature_b64",
        },
        label="release signature",
    )
    _schema(
        record["schema_version"],
        RELEASE_SIGNATURE_SCHEMA_VERSION,
        label="release signature",
    )
    if record["algorithm"] != SIGNATURE_ALGORITHM:
        raise _ReleaseSchemaUnsupported("release signature algorithm is unsupported")
    _digest(record["public_key_fingerprint"], label="release signing key fingerprint")
    encoded = record["signature_b64"]
    if not isinstance(encoded, str) or len(encoded) > 128:
        raise _ReleaseIncomplete("release signature encoding is invalid")
    try:
        decoded = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeError, binascii.Error) as exc:
        raise _ReleaseIncomplete("release signature encoding is invalid") from exc
    if len(decoded) != 64 or base64.b64encode(decoded).decode("ascii") != encoded:
        raise _ReleaseIncomplete("release signature encoding is invalid")
    return record


def _validate_envelope(
    manifest: object,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    try:
        _bounded_json_shape(manifest)
    except (TypeError, ValueError, RecursionError) as exc:
        raise _ReleaseIncomplete("release manifest shape exceeds its bound") from exc
    envelope = _manifest_object(
        manifest,
        {"schema_version", "release_id", "core_hash", "core", "metadata"},
        label="release manifest",
    )
    _schema(
        envelope["schema_version"],
        RELEASE_MANIFEST_SCHEMA_VERSION,
        label="release manifest",
    )
    if not isinstance(envelope["core"], dict):
        raise _ReleaseIncomplete("release core is missing")
    core = envelope["core"]
    try:
        calculated = _core_hash(core)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _ReleaseIncomplete("release core is not canonical JSON") from exc
    supplied_hash = _digest(envelope["core_hash"], label="release core hash")
    release_id = envelope["release_id"]
    if (
        supplied_hash != calculated
        or not isinstance(release_id, str)
        or release_id != f"release_{calculated}"
    ):
        raise _ReleaseIncomplete("release identity does not bind its core")
    metadata = _manifest_object(
        envelope["metadata"],
        {"schema_version", "created_at", "builder_python", "signature"},
        label="release metadata",
    )
    _schema(
        metadata["schema_version"],
        RELEASE_METADATA_SCHEMA_VERSION,
        label="release metadata",
    )
    _validate_timestamp(metadata["created_at"])
    if not isinstance(metadata["builder_python"], str) or re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+", metadata["builder_python"]
    ) is None:
        raise _ReleaseIncomplete("release builder Python version is invalid")
    signature = _validate_signature_record(metadata["signature"])
    return envelope, core, metadata, signature


def _validate_file_rows(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not value or len(value) > MAX_RELEASE_FILES:
        raise _ReleaseIncomplete("release file inventory is empty or over its bound")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    folded: set[str] = set()
    total = 0
    for item in value:
        row = _manifest_object(
            item,
            {"path", "classification", "size_bytes", "sha256"},
            label="release file",
        )
        try:
            path = _safe_relative_path(row["path"])
            classification = ReleaseFileClassification(row["classification"])
        except (TypeError, ValueError) as exc:
            raise _ReleaseIncomplete("release file path or classification is invalid") from exc
        if classification is not _classify_path(path):
            raise _ReleaseIncomplete("release file classification conflicts with policy")
        size = _exact_int(
            row["size_bytes"],
            label="release file size",
            maximum=MAX_RELEASE_FILE_BYTES,
        )
        digest = _digest(row["sha256"], label="release file hash")
        if path in seen or path.casefold() in folded:
            raise _ReleaseIncomplete("release file inventory has duplicate paths")
        seen.add(path)
        folded.add(path.casefold())
        total += size
        if total > MAX_RELEASE_TOTAL_BYTES:
            raise _ReleaseIncomplete("release file inventory exceeds its total bound")
        rows.append(
            {
                "path": path,
                "classification": classification.value,
                "size_bytes": size,
                "sha256": digest,
            }
        )
    canonical = tuple(sorted(rows, key=lambda row: str(row["path"])))
    if list(canonical) != rows:
        raise _ReleaseIncomplete("release file inventory is not canonically ordered")
    return canonical


def _validate_hash_rows(
    value: object,
    *,
    label: str,
    allowed_paths: frozenset[str] | None = None,
) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or len(value) > MAX_RELEASE_FILES:
        raise _ReleaseIncomplete(f"{label} inventory exceeds its bound")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in value:
        row = _manifest_object(
            item,
            {"path", "size_bytes", "sha256"},
            label=label,
        )
        try:
            path = _safe_relative_path(row["path"])
        except ValueError as exc:
            raise _ReleaseIncomplete(f"{label} path is invalid") from exc
        if allowed_paths is not None and path not in allowed_paths:
            raise _ReleaseIncomplete(f"{label} path is outside its fixed set")
        if path in seen:
            raise _ReleaseIncomplete(f"{label} path is duplicated")
        seen.add(path)
        rows.append(
            {
                "path": path,
                "size_bytes": _exact_int(
                    row["size_bytes"],
                    label=f"{label} size",
                    maximum=MAX_RELEASE_FILE_BYTES,
                ),
                "sha256": _digest(row["sha256"], label=f"{label} hash"),
            }
        )
    canonical = tuple(sorted(rows, key=lambda row: str(row["path"])))
    if list(canonical) != rows:
        raise _ReleaseIncomplete(f"{label} inventory is not canonically ordered")
    return canonical


def _validate_dependency_inventory(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or len(value) > MAX_DEPENDENCIES:
        raise _ReleaseIncomplete("dependency inventory exceeds its bound")
    rows: list[dict[str, object]] = []
    encoded_seen: set[bytes] = set()
    for item in value:
        if not isinstance(item, dict):
            raise _ReleaseIncomplete("dependency inventory entry is not an object")
        try:
            classification = DependencyClassification(item.get("classification"))
        except (TypeError, ValueError) as exc:
            raise _ReleaseIncomplete("dependency classification is invalid") from exc
        if classification is DependencyClassification.OBSERVED_INSTALLED_DEPENDENCY:
            row = _manifest_object(
                item,
                {"classification", "name", "version"},
                label="observed dependency",
            )
            name = _bounded_text(row["name"], label="observed dependency name")
            version = _bounded_text(row["version"], label="observed dependency version")
            if (
                _DEPENDENCY_NAME.fullmatch(name) is None
                or _normalize_dependency_name(name) != name
            ):
                raise _ReleaseIncomplete("observed dependency name is not canonical")
            canonical_row: dict[str, object] = {
                "classification": classification.value,
                "name": name,
                "version": version,
            }
        else:
            row = _manifest_object(
                item,
                {
                    "classification",
                    "name",
                    "declaration_path",
                    "requirement_sha256",
                    "version",
                },
                label="declared dependency",
            )
            name = _bounded_text(row["name"], label="declared dependency name")
            if (
                _DEPENDENCY_NAME.fullmatch(name) is None
                or _normalize_dependency_name(name) != name
            ):
                raise _ReleaseIncomplete("declared dependency name is not canonical")
            declaration_path = _bounded_text(
                row["declaration_path"],
                label="dependency declaration source",
            )
            if not (
                declaration_path in _DEPENDENCY_DECLARATION_PATHS
                or re.fullmatch(
                    r"pyproject\.toml#(?:build-system|optional:[A-Za-z0-9][A-Za-z0-9._-]{0,63})",
                    declaration_path,
                )
            ):
                raise _ReleaseIncomplete("dependency declaration source is invalid")
            version_value = row["version"]
            if classification is DependencyClassification.PINNED_DEPENDENCY:
                version: str | None = _bounded_text(
                    version_value,
                    label="pinned dependency version",
                )
            elif version_value is None:
                version = None
            else:
                raise _ReleaseIncomplete("declared dependency falsely claims a pin")
            canonical_row = {
                "classification": classification.value,
                "name": name,
                "declaration_path": declaration_path,
                "requirement_sha256": _digest(
                    row["requirement_sha256"],
                    label="dependency requirement hash",
                ),
                "version": version,
            }
        encoded = _canonical_json(canonical_row)
        if encoded in encoded_seen:
            raise _ReleaseIncomplete("dependency inventory has duplicate entries")
        encoded_seen.add(encoded)
        rows.append(canonical_row)
    canonical = tuple(sorted(rows, key=_canonical_json))
    if list(canonical) != rows:
        raise _ReleaseIncomplete("dependency inventory is not canonically ordered")
    return canonical


def _validate_test_evidence(value: object) -> TestEvidence:
    row = _manifest_object(
        value,
        {
            "schema_version",
            "command_id",
            "source_commit",
            "git_tree_identity",
            "run_count",
            "pass_count",
            "failure_count",
            "error_count",
            "skip_count",
            "failure_names_sha256",
            "error_names_sha256",
            "skip_names_sha256",
            "output_log_sha256",
            "disposition",
        },
        label="release test evidence",
    )
    _schema(
        row["schema_version"],
        RELEASE_TEST_EVIDENCE_SCHEMA_VERSION,
        label="release test evidence",
    )
    try:
        evidence = TestEvidence(
            command_id=row["command_id"],
            source_commit=row["source_commit"],
            git_tree_identity=row["git_tree_identity"],
            run_count=row["run_count"],
            pass_count=row["pass_count"],
            failure_count=row["failure_count"],
            error_count=row["error_count"],
            skip_count=row["skip_count"],
            failure_names_sha256=row["failure_names_sha256"],
            error_names_sha256=row["error_names_sha256"],
            skip_names_sha256=row["skip_names_sha256"],
            output_log_sha256=row["output_log_sha256"],
        )
        disposition = TestEvidenceDisposition(row["disposition"])
    except (TypeError, ValueError) as exc:
        raise _ReleaseIncomplete("release test evidence is invalid") from exc
    if disposition is not evidence.disposition:
        raise _ReleaseIncomplete("release test disposition conflicts with exact counts")
    return evidence


def _validate_core(core: object) -> tuple[
    dict[str, Any],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
    TestEvidence,
]:
    value = _manifest_object(
        core,
        {
            "schema_version",
            "source",
            "nz_architecture",
            "python_compatibility",
            "schemas",
            "dependency_declarations",
            "dependency_inventory",
            "critical_files",
            "documentation",
            "test_evidence",
        },
        label="release core",
    )
    _schema(value["schema_version"], RELEASE_CORE_SCHEMA_VERSION, label="release core")
    source = _manifest_object(
        value["source"],
        {
            "source_commit",
            "git_tree_identity",
            "release_scope_identity",
            "file_count",
            "total_bytes",
        },
        label="release source",
    )
    source_commit = _git_digest(source["source_commit"], label="release source commit")
    git_tree = _git_digest(source["git_tree_identity"], label="release source tree")
    scope_identity = _digest(source["release_scope_identity"], label="release scope identity")
    file_count = _exact_int(
        source["file_count"], label="release file count", maximum=MAX_RELEASE_FILES
    )
    total_bytes = _exact_int(
        source["total_bytes"],
        label="release total bytes",
        maximum=MAX_RELEASE_TOTAL_BYTES,
    )
    files = _validate_file_rows(value["critical_files"])
    if (
        file_count != len(files)
        or total_bytes != sum(int(row["size_bytes"]) for row in files)
        or scope_identity != _scope_hash(files)
    ):
        raise _ReleaseIncomplete("release source summary conflicts with its files")
    architecture = _manifest_object(
        value["nz_architecture"],
        {"foundation", "operational_hardening", "production_readiness"},
        label="NZ architecture",
    )
    if architecture != {
        "foundation": NZ_FOUNDATION_VERSION,
        "operational_hardening": NZ_OPERATIONAL_HARDENING_VERSION,
        "production_readiness": NZ_PRODUCTION_READINESS_VERSION,
    }:
        raise _ReleaseSchemaUnsupported("NZ architecture generation is unsupported")
    compatibility = _manifest_object(
        value["python_compatibility"],
        {
            "requires_python",
            "implementation",
            "observed_python_version",
            "bytecode_in_scope",
        },
        label="Python compatibility",
    )
    _bounded_text(compatibility["requires_python"], label="Python requirement")
    _bounded_text(compatibility["implementation"], label="Python implementation")
    if not isinstance(compatibility["observed_python_version"], str) or re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+", compatibility["observed_python_version"]
    ) is None:
        raise _ReleaseIncomplete("observed Python version is invalid")
    if type(compatibility["bytecode_in_scope"]) is not bool or compatibility[
        "bytecode_in_scope"
    ]:
        raise _ReleaseIncomplete("release bytecode scope is invalid")
    schemas = _manifest_object(
        value["schemas"],
        {
            "configuration",
            "checkpoint",
            "idempotency",
            "provenance",
            "anchor",
            "backup",
            "release",
        },
        label="release schemas",
    )
    if schemas != _schema_versions():
        raise _ReleaseSchemaUnsupported("release schema relationships are unsupported")
    dependency_declarations = _validate_hash_rows(
        value["dependency_declarations"],
        label="dependency declaration",
        allowed_paths=frozenset(_DEPENDENCY_DECLARATION_PATHS),
    )
    if {str(row["path"]) for row in dependency_declarations} != set(
        _DEPENDENCY_DECLARATION_PATHS
    ):
        raise _ReleaseIncomplete("dependency declaration inventory is incomplete")
    inventory = _validate_dependency_inventory(value["dependency_inventory"])
    documentation = _validate_hash_rows(
        value["documentation"],
        label="release documentation",
        allowed_paths=frozenset(_RELEASE_DOCUMENTS),
    )
    by_path = {str(row["path"]): row for row in files}
    expected_dependency_rows = tuple(
        {
            "path": path,
            "size_bytes": by_path[path]["size_bytes"],
            "sha256": by_path[path]["sha256"],
        }
        for path in sorted(_DEPENDENCY_DECLARATION_PATHS)
        if path in by_path
    )
    if dependency_declarations != expected_dependency_rows:
        raise _ReleaseIncomplete("dependency declarations conflict with source hashes")
    expected_docs = tuple(
        {
            "path": str(row["path"]),
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
        }
        for row in files
        if row["classification"] == ReleaseFileClassification.DOCUMENTATION.value
    )
    if documentation != expected_docs:
        raise _ReleaseIncomplete("documentation hashes conflict with source hashes")
    evidence = _validate_test_evidence(value["test_evidence"])
    if evidence.source_commit != source_commit or evidence.git_tree_identity != git_tree:
        raise _ReleaseIncomplete("test evidence does not bind the release source")
    return source, files, dependency_declarations, inventory, evidence


def _signature_payload(core: Mapping[str, object]) -> bytes:
    return RELEASE_SIGNATURE_DOMAIN + _canonical_json(core)


def _verification_result(
    status: ReleaseStatus,
    *,
    envelope: Mapping[str, object] | None = None,
    source_commit: str | None = None,
    signed: bool = False,
    test_disposition: str | None = None,
    message_safe: str,
) -> ReleaseVerificationResult:
    release_id: str | None = None
    core_hash: str | None = None
    if envelope is not None:
        candidate_id = envelope.get("release_id")
        candidate_hash = envelope.get("core_hash")
        if (
            isinstance(candidate_id, str)
            and isinstance(candidate_hash, str)
            and _HEX_64.fullmatch(candidate_hash)
            and candidate_id == f"release_{candidate_hash}"
        ):
            release_id = candidate_id
            core_hash = candidate_hash
    return ReleaseVerificationResult(
        status=status,
        release_id=release_id,
        core_hash=core_hash,
        source_commit=source_commit,
        signed=signed,
        test_disposition=test_disposition,
        message_safe=message_safe,
    )


def _verify_signature(
    core: Mapping[str, object],
    signature: Mapping[str, object],
    *,
    repository_root: Path,
    public_key_registry: Path | None,
    expected_root_fingerprint: str | None,
) -> ReleaseStatus | None:
    if public_key_registry is None or expected_root_fingerprint is None:
        return ReleaseStatus.RELEASE_UNKNOWN_KEY
    try:
        _digest(expected_root_fingerprint, label="expected release trust root")
        project_identity = _project_identity(repository_root)
        target_fingerprint = str(signature["public_key_fingerprint"])
        _validated_registry_tip(
            Path(public_key_registry),
            project_identity=project_identity,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        trusted_record, public_key = _trusted_key_chain(
            Path(public_key_registry),
            project_identity=project_identity,
            target_fingerprint=target_fingerprint,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        if trusted_record["public_key_fingerprint"] != target_fingerprint:
            return ReleaseStatus.RELEASE_UNKNOWN_KEY
        encoded = signature["signature_b64"]
        signature_bytes = base64.b64decode(str(encoded).encode("ascii"), validate=True)
        _Private, _Public, crypto_support = _crypto()
        _serialization, InvalidSignature = crypto_support
        try:
            public_key.verify(signature_bytes, _signature_payload(core))
        except InvalidSignature:
            return ReleaseStatus.RELEASE_SIGNATURE_INVALID
    except ProvenanceAnchorCryptoUnavailable:
        return ReleaseStatus.RELEASE_CRYPTO_UNAVAILABLE
    except (KeyError, OSError, TypeError, ValueError, ProvenanceAnchorConfigurationError):
        return ReleaseStatus.RELEASE_UNKNOWN_KEY
    return None


def verify_release_manifest(
    manifest: object,
    repository_root: Path,
    *,
    public_key_registry: Path | None = None,
    expected_root_fingerprint: str | None = None,
) -> ReleaseVerificationResult:
    """Verify a release envelope, signature, and current offline source facts."""

    envelope: dict[str, Any] | None = None
    signature: dict[str, Any] | None = None
    if isinstance(manifest, bytes):
        try:
            manifest = decode_release_manifest(manifest)
        except ValueError:
            return _verification_result(
                ReleaseStatus.RELEASE_INCOMPLETE,
                message_safe="Release manifest bytes are malformed, noncanonical, or over their bound.",
            )
    try:
        envelope, core, _metadata, signature = _validate_envelope(manifest)
    except _ReleaseSchemaUnsupported:
        return _verification_result(
            ReleaseStatus.RELEASE_SCHEMA_UNSUPPORTED,
            envelope=envelope,
            message_safe="Release manifest schema or algorithm is unsupported.",
        )
    except (KeyError, TypeError, ValueError, _ReleaseIncomplete):
        return _verification_result(
            ReleaseStatus.RELEASE_INCOMPLETE,
            envelope=envelope,
            message_safe="Release manifest is missing, malformed, or internally inconsistent.",
        )
    try:
        root = _safe_repository_root(repository_root)
    except ReleaseSourceError:
        return _verification_result(
            ReleaseStatus.RELEASE_INCOMPLETE,
            envelope=envelope,
            signed=signature is not None,
            message_safe="Release repository root is unavailable or unsafe.",
        )
    if signature is not None:
        signature_status = _verify_signature(
            core,
            signature,
            repository_root=root,
            public_key_registry=public_key_registry,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        if signature_status is not None:
            messages = {
                ReleaseStatus.RELEASE_SIGNATURE_INVALID: "Release signature is invalid.",
                ReleaseStatus.RELEASE_UNKNOWN_KEY: "Release signing key is not independently trusted.",
                ReleaseStatus.RELEASE_CRYPTO_UNAVAILABLE: "Local Ed25519 verification support is unavailable.",
            }
            return _verification_result(
                signature_status,
                envelope=envelope,
                signed=True,
                message_safe=messages[signature_status],
            )
    try:
        source, files, dependency_declarations, inventory, evidence = _validate_core(core)
    except _ReleaseSchemaUnsupported:
        return _verification_result(
            ReleaseStatus.RELEASE_SCHEMA_UNSUPPORTED,
            envelope=envelope,
            signed=signature is not None,
            message_safe="Release core schema relationships are unsupported.",
        )
    except (KeyError, TypeError, ValueError, _ReleaseIncomplete):
        return _verification_result(
            ReleaseStatus.RELEASE_INCOMPLETE,
            envelope=envelope,
            signed=signature is not None,
            message_safe="Release core is missing, malformed, or internally inconsistent.",
        )
    source_commit = str(source["source_commit"])
    disposition = evidence.disposition.value
    try:
        current_declarations, current_inventory, requires_python = _dependency_facts(
            root,
            observed_installed=None,
        )
    except (OSError, TypeError, ValueError, ReleaseSourceError):
        return _verification_result(
            ReleaseStatus.RELEASE_DEPENDENCY_MISMATCH,
            envelope=envelope,
            source_commit=source_commit,
            signed=signature is not None,
            test_disposition=disposition,
            message_safe="Dependency declarations or offline inventory cannot be reproduced.",
        )
    compatibility = core["python_compatibility"]
    current_python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if (
        dependency_declarations != current_declarations
        or inventory != current_inventory
        or not isinstance(compatibility, dict)
        or compatibility.get("requires_python") != requires_python
        or compatibility.get("implementation") != sys.implementation.name
        or compatibility.get("observed_python_version") != current_python
    ):
        return _verification_result(
            ReleaseStatus.RELEASE_DEPENDENCY_MISMATCH,
            envelope=envelope,
            source_commit=source_commit,
            signed=signature is not None,
            test_disposition=disposition,
            message_safe="Release dependency or Python compatibility evidence does not match.",
        )
    try:
        snapshot = _capture_source(root)
    except ReleaseSourceError:
        return _verification_result(
            ReleaseStatus.RELEASE_FILE_MISMATCH,
            envelope=envelope,
            source_commit=source_commit,
            signed=signature is not None,
            test_disposition=disposition,
            message_safe="Release-scoped source is missing, changed, unsafe, or not clean.",
        )
    if (
        snapshot.source_commit != source_commit
        or snapshot.git_tree_identity != source["git_tree_identity"]
    ):
        return _verification_result(
            ReleaseStatus.RELEASE_SOURCE_MISMATCH,
            envelope=envelope,
            source_commit=source_commit,
            signed=signature is not None,
            test_disposition=disposition,
            message_safe="Release source commit or Git tree identity does not match.",
        )
    if (
        snapshot.files != files
        or snapshot.release_scope_identity != source["release_scope_identity"]
        or snapshot.file_count != source["file_count"]
        or snapshot.total_bytes != source["total_bytes"]
    ):
        return _verification_result(
            ReleaseStatus.RELEASE_FILE_MISMATCH,
            envelope=envelope,
            source_commit=source_commit,
            signed=signature is not None,
            test_disposition=disposition,
            message_safe="Release source file set or content hashes do not match.",
        )
    if signature is None:
        return _verification_result(
            ReleaseStatus.RELEASE_UNSIGNED,
            envelope=envelope,
            source_commit=source_commit,
            signed=False,
            test_disposition=disposition,
            message_safe="Release content is valid but has no local signature.",
        )
    return _verification_result(
        ReleaseStatus.RELEASE_VALID,
        envelope=envelope,
        source_commit=source_commit,
        signed=True,
        test_disposition=disposition,
        message_safe="Release source, dependencies, schemas, evidence, and signature are valid.",
    )


def sign_release_manifest(
    manifest: object,
    repository_root: Path,
    *,
    private_key_path: Path,
    public_key_registry: Path,
    expected_root_fingerprint: str,
) -> ReleaseBuildResult:
    """Sign a currently valid deterministic core with the active P1.3 key."""

    root = _safe_repository_root(repository_root)
    unsigned = verify_release_manifest(manifest, root)
    if unsigned.status is not ReleaseStatus.RELEASE_UNSIGNED:
        raise ReleaseSigningError("Only a current valid unsigned release can be signed.")
    try:
        envelope, core, metadata, signature = _validate_envelope(manifest)
        if signature is not None:
            raise ReleaseSigningError("Release manifest is already signed.")
        _validate_core(core)
        _digest(expected_root_fingerprint, label="expected release trust root")
        project_identity = _project_identity(root)
        private_key, _public_bytes, signer_fingerprint = _load_private_key(
            Path(private_key_path),
            repository_root=root,
            project_dir=root,
            public_key_registry=Path(public_key_registry),
        )
        active = _validated_registry_tip(
            Path(public_key_registry),
            project_identity=project_identity,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        if active["public_key_fingerprint"] != signer_fingerprint:
            raise ReleaseSigningError(
                "Release signing key is not the active trusted key."
            )
        signature_bytes = private_key.sign(_signature_payload(core))
    except ReleaseSigningError:
        raise
    except ProvenanceAnchorCryptoUnavailable as exc:
        raise ReleaseSigningError("Local Ed25519 signing support is unavailable.") from exc
    except (KeyError, OSError, TypeError, ValueError, ProvenanceAnchorConfigurationError) as exc:
        raise ReleaseSigningError("Release signing key or trust registry is invalid.") from exc
    cloned = json.loads(_canonical_json(envelope).decode("utf-8"))
    cloned_metadata = dict(metadata)
    cloned_metadata["signature"] = {
        "schema_version": RELEASE_SIGNATURE_SCHEMA_VERSION,
        "algorithm": SIGNATURE_ALGORITHM,
        "public_key_fingerprint": signer_fingerprint,
        "signature_b64": base64.b64encode(signature_bytes).decode("ascii"),
    }
    cloned["metadata"] = cloned_metadata
    result = ReleaseBuildResult(
        manifest=cloned,
        release_id=str(cloned["release_id"]),
        core_hash=str(cloned["core_hash"]),
        signed=True,
    )
    verification = verify_release_manifest(
        result.manifest,
        root,
        public_key_registry=Path(public_key_registry),
        expected_root_fingerprint=expected_root_fingerprint,
    )
    if verification.status is not ReleaseStatus.RELEASE_VALID:
        raise ReleaseSigningError("Release signature did not verify after creation.")
    return result


__all__ = [
    "DependencyClassification",
    "NZ_FOUNDATION_VERSION",
    "NZ_OPERATIONAL_HARDENING_VERSION",
    "NZ_PRODUCTION_READINESS_VERSION",
    "RELEASE_CORE_SCHEMA_VERSION",
    "RELEASE_MANIFEST_SCHEMA_VERSION",
    "RELEASE_METADATA_SCHEMA_VERSION",
    "RELEASE_SIGNATURE_SCHEMA_VERSION",
    "RELEASE_TEST_EVIDENCE_SCHEMA_VERSION",
    "ReleaseAttestationError",
    "ReleaseBuildResult",
    "ReleaseFileClassification",
    "ReleaseSigningError",
    "ReleaseSourceError",
    "ReleaseStatus",
    "ReleaseVerificationResult",
    "TestEvidence",
    "TestEvidenceDisposition",
    "build_release_manifest",
    "decode_release_manifest",
    "encode_release_manifest",
    "sign_release_manifest",
    "verify_release_manifest",
]
