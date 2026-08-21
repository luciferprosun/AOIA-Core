from __future__ import annotations

import hashlib
import json
import ctypes
import errno
import os
import re
import stat
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from runtime.safety.atomic_persistence import InterProcessFileLock
from runtime.startup_preflight import (
    ANCHOR_REGISTRY_ENV,
    ANCHOR_ROOT_ENV,
    ANCHOR_ROOT_FINGERPRINT_ENV,
    AnchorConfigurationStatus,
    StartupMode,
    StartupStatus,
    _bounded_directory_entries,
    _derive_state_root,
    _safe_read_bytes,
    run_startup_preflight,
)
from runtime.tools.idempotency import project_scope_fingerprint
BACKUP_SCHEMA_VERSION = "AOIA_STATE_BACKUP_1A"
BACKUP_CORE_DOMAIN = b"AOIA-Core/state-backup-manifest-1a\x00"
NZ_ARCHITECTURE_VERSION = "NZ_PRODUCTION_READINESS_P2_2"
MAX_BACKUP_FILES = 8_192
MAX_BACKUP_FILE_BYTES = 64 * 1024 * 1024
MAX_BACKUP_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_BACKUP_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_BACKUP_PATH_BYTES = 512
BACKUP_NAME = re.compile(r"^backup_[0-9a-f]{64}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
HEX_COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class BackupStatus(str, Enum):
    BACKUP_VALID = "BACKUP_VALID"
    BACKUP_CORRUPT = "BACKUP_CORRUPT"
    BACKUP_INCOMPLETE = "BACKUP_INCOMPLETE"
    BACKUP_SCHEMA_UNSUPPORTED = "BACKUP_SCHEMA_UNSUPPORTED"
    BACKUP_PROJECT_MISMATCH = "BACKUP_PROJECT_MISMATCH"


class RestoreStatus(str, Enum):
    RESTORE_VALIDATED = "RESTORE_VALIDATED"
    RESTORE_MANUAL_REVIEW_REQUIRED = "RESTORE_MANUAL_REVIEW_REQUIRED"
    RESTORE_REJECTED = "RESTORE_REJECTED"


class ResourceClassification(str, Enum):
    REQUIRED_FOR_RECOVERY = "REQUIRED_FOR_RECOVERY"
    OPTIONAL_REBUILDABLE = "OPTIONAL_REBUILDABLE"
    CACHE = "CACHE"
    EXCLUDED_SECRET = "EXCLUDED_SECRET"
    EXCLUDED_EPHEMERAL = "EXCLUDED_EPHEMERAL"


class StateBackupError(RuntimeError):
    reason_code = "STATE_BACKUP_ERROR"


class StateBackupSourceError(StateBackupError):
    reason_code = "STATE_BACKUP_SOURCE_INVALID"


class StateBackupDestinationError(StateBackupError):
    reason_code = "STATE_BACKUP_DESTINATION_INVALID"


class _BackupInvalid(ValueError):
    def __init__(self, status: BackupStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class BackupVerificationResult:
    status: BackupStatus
    backup_id: str | None = None
    file_count: int = 0
    total_bytes: int = 0
    provenance_entry_count: int | None = None
    provenance_tip: str | None = None
    anchor_status: str = "NOT_CONFIGURED"
    message_safe: str = "Backup verification failed."

    @property
    def valid(self) -> bool:
        return self.status is BackupStatus.BACKUP_VALID


@dataclass(frozen=True)
class BackupCreationResult:
    backup_id: str
    backup_path: Path
    verification: BackupVerificationResult
    reused_existing: bool = False


@dataclass(frozen=True)
class RestoreResult:
    status: RestoreStatus
    backup_id: str | None
    backup_status: BackupStatus
    startup_status: str | None = None
    anchor_snapshot_status: str = "NOT_CONFIGURED"
    reason_code: str = "RESTORE_REJECTED"

    @property
    def success(self) -> bool:
        return self.status is RestoreStatus.RESTORE_VALIDATED


@dataclass(frozen=True)
class DisasterRecoveryDrillResult:
    backup_status: BackupStatus
    restore_status: RestoreStatus
    startup_status: str | None
    provenance_entry_count: int | None
    passed: bool


@dataclass(frozen=True)
class _CapturedFile:
    relative_path: str
    classification: ResourceClassification
    payload: bytes


_RESOURCE_INVENTORY: tuple[tuple[str, ResourceClassification], ...] = (
    ("task_checkpoints", ResourceClassification.REQUIRED_FOR_RECOVERY),
    ("idempotency_records", ResourceClassification.REQUIRED_FOR_RECOVERY),
    ("runtime_provenance", ResourceClassification.REQUIRED_FOR_RECOVERY),
    ("provenance_outbox", ResourceClassification.REQUIRED_FOR_RECOVERY),
    ("legacy_provenance", ResourceClassification.OPTIONAL_REBUILDABLE),
    ("non_secret_configuration", ResourceClassification.OPTIONAL_REBUILDABLE),
    ("trusted_anchor_public_records", ResourceClassification.REQUIRED_FOR_RECOVERY),
    ("agent_memory", ResourceClassification.EXCLUDED_SECRET),
    ("memory_hats", ResourceClassification.EXCLUDED_SECRET),
    ("runtime_logs_and_browser_state", ResourceClassification.CACHE),
    ("recovery_claims_and_execution_locks", ResourceClassification.EXCLUDED_EPHEMERAL),
    ("state_locks", ResourceClassification.EXCLUDED_EPHEMERAL),
    ("private_signing_material", ResourceClassification.EXCLUDED_SECRET),
)

_REQUIRED_TRUST_DIRECTORIES: tuple[str, ...] = (
    "trust/anchor/anchors",
    "trust/registry/keys",
    "trust/registry/rotations",
)


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _strict_json(payload: bytes, maximum: int) -> dict[str, Any]:
    if not payload or len(payload) > maximum:
        raise ValueError("JSON record is empty or over its bound")

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
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("JSON record is malformed") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON record must be an object")
    return value


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("backup path is invalid")
    if len(value.encode("utf-8")) > MAX_BACKUP_PATH_BYTES:
        raise ValueError("backup path exceeds its bound")
    if "\\" in value or "\x00" in value or any(ord(ch) < 32 or ord(ch) > 126 for ch in value):
        raise ValueError("backup path is not portable ASCII")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix():
        raise ValueError("backup path is not canonical relative POSIX")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("backup path contains an unsafe component")
    if not path.parts or path.parts[0] not in {"runtime", "trust"}:
        raise ValueError("backup path is outside the logical allowlist")
    return value


def _absolute_lexical(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("path must be absolute")
    return Path(os.path.abspath(path))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or _is_relative_to(left, right) or _is_relative_to(right, left)


def _safe_directory(path: Path, *, create: bool, private: bool = True) -> Path:
    lexical = _absolute_lexical(Path(path))
    current = Path(lexical.anchor)
    missing = False
    for part in lexical.parts[1:]:
        current = current / part
        if missing:
            continue
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            missing = True
            continue
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("directory chain is unsafe")
    if create:
        lexical.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = lexical.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("directory is unsafe")
    if metadata.st_uid != os.getuid():
        raise ValueError("directory owner is invalid")
    if private and stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("directory is not owner-only")
    opened = os.open(
        lexical,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        pinned = os.fstat(opened)
        if (pinned.st_dev, pinned.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise ValueError("directory binding changed")
    finally:
        os.close(opened)
    return lexical


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _open_directory(path: Path) -> int:
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise ValueError("directory is unsafe")
    descriptor = os.open(path, _directory_flags())
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
        os.close(descriptor)
        raise ValueError("directory binding changed")
    return descriptor


def _open_or_create_child(parent_fd: int, name: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", name) or name in {".", ".."}:
        raise ValueError("directory component is unsafe")
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise ValueError("directory component is unsafe")
    descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
        os.close(descriptor)
        raise ValueError("directory component binding changed")
    return descriptor


def _write_internal_file_at(root: Path, relative_path: str, payload: bytes) -> None:
    if (
        not isinstance(relative_path, str)
        or not relative_path
        or relative_path.startswith("/")
        or "\\" in relative_path
        or "\x00" in relative_path
    ):
        raise ValueError("internal path is invalid")
    parsed = PurePosixPath(relative_path)
    if relative_path != parsed.as_posix() or any(
        component in {"", ".", ".."}
        or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", component) is None
        for component in parsed.parts
    ):
        raise ValueError("internal path has an unsafe component")
    relative = relative_path
    parts = parsed.parts
    descriptors = [_open_directory(root)]
    try:
        for component in parts[:-1]:
            descriptors.append(_open_or_create_child(descriptors[-1], component))
        parent_fd = descriptors[-1]
        name = parts[-1]
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("backup write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(parent_fd)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _ensure_internal_directory_at(root: Path, relative_path: str) -> None:
    """Create one exact internally allowlisted directory path via pinned descriptors."""

    if (
        not isinstance(relative_path, str)
        or not relative_path
        or relative_path.startswith("/")
        or "\\" in relative_path
        or "\x00" in relative_path
    ):
        raise ValueError("internal directory path is invalid")
    parsed = PurePosixPath(relative_path)
    if relative_path != parsed.as_posix() or any(
        component in {"", ".", ".."}
        or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", component) is None
        for component in parsed.parts
    ):
        raise ValueError("internal directory path has an unsafe component")
    descriptors = [_open_directory(root)]
    try:
        for component in parsed.parts:
            descriptors.append(_open_or_create_child(descriptors[-1], component))
        os.fsync(descriptors[-1])
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _write_private_file_at(root: Path, relative_path: str, payload: bytes) -> None:
    if relative_path.startswith("payload/"):
        _safe_relative_path(relative_path[len("payload/") :])
        relative = relative_path
    else:
        relative = _safe_relative_path(relative_path)
    _write_internal_file_at(root, relative, payload)


def _write_manifest_at(root: Path, payload: bytes) -> None:
    root_fd = _open_directory(root)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open("manifest.json", flags, 0o600, dir_fd=root_fd)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("manifest write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(root_fd)
    finally:
        os.close(root_fd)


def _write_private_file(path: Path, payload: bytes) -> None:
    """Write a controlled drill fixture, never a public backup payload."""

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("backup write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_private(path: Path, maximum: int = MAX_BACKUP_FILE_BYTES) -> bytes:
    payload = _safe_read_bytes(path, maximum, require_private=True)
    if payload is None:
        raise FileNotFoundError(path)
    return payload


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    directories = [root]
    for path in root.rglob("*"):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("backup tree contains a symbolic link")
        if stat.S_ISDIR(metadata.st_mode):
            directories.append(path)
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        _fsync_directory(path)


def _remove_staging(path: Path, root: Path, prefix: str) -> None:
    try:
        lexical = _absolute_lexical(path)
        trusted_root = _absolute_lexical(root)
    except ValueError:
        return
    if lexical.parent != trusted_root or not lexical.name.startswith(prefix):
        return
    root_fd = _open_directory(trusted_root)
    try:
        try:
            metadata = os.stat(lexical.name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            return
        _remove_directory_at(root_fd, lexical.name)
        os.fsync(root_fd)
    finally:
        os.close(root_fd)


def _remove_directory_at(parent_fd: int, name: str) -> None:
    descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
    try:
        for child in os.listdir(descriptor):
            metadata = os.stat(child, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError("controlled staging unexpectedly contains a link")
            if stat.S_ISDIR(metadata.st_mode):
                _remove_directory_at(descriptor, child)
            elif stat.S_ISREG(metadata.st_mode):
                os.unlink(child, dir_fd=descriptor)
            else:
                raise ValueError("controlled staging unexpectedly contains a special file")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.rmdir(name, dir_fd=parent_fd)


def _promote_directory(staging: Path, destination: Path, root: Path) -> None:
    root_fd = _open_directory(root)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(errno.ENOSYS, "atomic no-replace rename is unavailable")
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            root_fd,
            os.fsencode(staging.name),
            root_fd,
            os.fsencode(destination.name),
            1,  # RENAME_NOREPLACE
        )
        if result != 0:
            error = ctypes.get_errno()
            if error == errno.EEXIST:
                raise FileExistsError(destination)
            raise OSError(error, os.strerror(error))
        os.fsync(root_fd)
    finally:
        os.close(root_fd)


def _core_hash(core: Mapping[str, Any]) -> str:
    return hashlib.sha256(BACKUP_CORE_DOMAIN + _canonical_json(dict(core))).hexdigest()


def _project_identity(project_dir: Path) -> str:
    return project_scope_fingerprint(Path(project_dir).resolve(strict=True))


def _capture_file(
    values: list[_CapturedFile],
    source: Path,
    relative_path: str,
    classification: ResourceClassification,
    *,
    maximum_bytes: int = MAX_BACKUP_FILE_BYTES,
) -> None:
    relative = _safe_relative_path(relative_path)
    payload = _safe_read_bytes(source, maximum_bytes, require_private=True)
    if payload is None:
        raise StateBackupSourceError("Required backup source disappeared.")
    values.append(_CapturedFile(relative, classification, payload))
    if len(values) > MAX_BACKUP_FILES or sum(len(item.payload) for item in values) > MAX_BACKUP_TOTAL_BYTES:
        raise StateBackupSourceError("Backup source exceeds its bounded capacity.")


def _capture_runtime_state(runtime_root: Path) -> list[_CapturedFile]:
    values: list[_CapturedFile] = []
    state = runtime_root / "state"
    tasks = state / "tasks"
    for name in sorted(_bounded_directory_entries(tasks, 1024)):
        if re.fullmatch(r"[0-9a-f]{64}", name) is None:
            raise StateBackupSourceError("Task checkpoint source is invalid.")
        children = _bounded_directory_entries(tasks / name, 4)
        if set(children) != {"checkpoint.json"}:
            raise StateBackupSourceError("Task checkpoint source is incomplete.")
        _capture_file(
            values,
            tasks / name / "checkpoint.json",
            f"runtime/state/tasks/{name}/checkpoint.json",
            ResourceClassification.REQUIRED_FOR_RECOVERY,
            maximum_bytes=2 * 1024 * 1024,
        )

    idempotency = state / "idempotency"
    for name in sorted(_bounded_directory_entries(idempotency, 1024)):
        if re.fullmatch(r"[0-9a-f]{64}\.json", name) is None:
            raise StateBackupSourceError("Idempotency source is invalid.")
        _capture_file(
            values,
            idempotency / name,
            f"runtime/state/idempotency/{name}",
            ResourceClassification.REQUIRED_FOR_RECOVERY,
            maximum_bytes=64 * 1024,
        )

    provenance = state / "provenance"
    provenance_names = set(_bounded_directory_entries(provenance, 1028))
    if provenance_names - {"runtime_provenance_log.jsonl", "provenance_log.jsonl", "outbox"}:
        raise StateBackupSourceError("Provenance source has unexpected resources.")
    if "runtime_provenance_log.jsonl" in provenance_names:
        _capture_file(
            values,
            provenance / "runtime_provenance_log.jsonl",
            "runtime/state/provenance/runtime_provenance_log.jsonl",
            ResourceClassification.REQUIRED_FOR_RECOVERY,
        )
    if "provenance_log.jsonl" in provenance_names:
        _capture_file(
            values,
            provenance / "provenance_log.jsonl",
            "runtime/state/provenance/provenance_log.jsonl",
            ResourceClassification.OPTIONAL_REBUILDABLE,
        )
    if "outbox" in provenance_names:
        outbox = provenance / "outbox"
        for name in sorted(_bounded_directory_entries(outbox, 1024)):
            if re.fullmatch(r"provenance_event_[0-9a-f]{32}\.json", name) is None:
                raise StateBackupSourceError("Provenance outbox source is invalid.")
            _capture_file(
                values,
                outbox / name,
                f"runtime/state/provenance/outbox/{name}",
                ResourceClassification.REQUIRED_FOR_RECOVERY,
                maximum_bytes=64 * 1024,
            )

    for filename in ("model_config.json", "providers.json"):
        if filename in set(_bounded_directory_entries(state, 8192)):
            _capture_file(
                values,
                state / filename,
                f"runtime/state/{filename}",
                ResourceClassification.OPTIONAL_REBUILDABLE,
                maximum_bytes=256 * 1024,
            )
    return values


def _capture_public_anchor_records(
    values: list[_CapturedFile],
    anchor_root: Path,
    registry: Path,
) -> None:
    anchor_root = _safe_directory(anchor_root, create=False)
    registry = _safe_directory(registry, create=False)
    _capture_file(
        values,
        anchor_root / "latest_anchor.json",
        "trust/anchor/latest_anchor.json",
        ResourceClassification.REQUIRED_FOR_RECOVERY,
        maximum_bytes=16 * 1024,
    )
    archives = _safe_directory(anchor_root / "anchors", create=False)
    archive_names = sorted(_bounded_directory_entries(archives, 4096))
    if not archive_names:
        raise StateBackupSourceError("Configured anchor archive is empty.")
    for name in archive_names:
        if re.fullmatch(r"anchor_[0-9a-f]{32}\.json", name) is None:
            raise StateBackupSourceError("Anchor archive source is invalid.")
        _capture_file(
            values,
            archives / name,
            f"trust/anchor/anchors/{name}",
            ResourceClassification.REQUIRED_FOR_RECOVERY,
            maximum_bytes=16 * 1024,
        )

    for filename in ("trust_root.json", "latest_key.json"):
        _capture_file(
            values,
            registry / filename,
            f"trust/registry/{filename}",
            ResourceClassification.REQUIRED_FOR_RECOVERY,
            maximum_bytes=8 * 1024,
        )
    for directory, pattern, maximum in (
        ("keys", r"key_[0-9a-f]{64}\.json", 128),
        ("rotations", r"rotation_[0-9]{3}\.json", 128),
    ):
        source_dir = _safe_directory(registry / directory, create=False)
        for name in sorted(_bounded_directory_entries(source_dir, maximum)):
            if re.fullmatch(pattern, name) is None:
                raise StateBackupSourceError("Public-key registry source is invalid.")
            _capture_file(
                values,
                source_dir / name,
                f"trust/registry/{directory}/{name}",
                ResourceClassification.REQUIRED_FOR_RECOVERY,
                maximum_bytes=16 * 1024,
            )


def _materialize_verified_empty_anchored_ledger(values: list[_CapturedFile]) -> None:
    """Represent P1.3's valid zero-entry/missing-file ledger as canonical empty bytes."""

    ledger_path = "runtime/state/provenance/runtime_provenance_log.jsonl"
    if not any(item.relative_path == ledger_path for item in values):
        values.append(
            _CapturedFile(
                ledger_path,
                ResourceClassification.REQUIRED_FOR_RECOVERY,
                b"",
            )
        )


def _payload_by_path(values: Sequence[_CapturedFile]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for item in values:
        if item.relative_path in result:
            raise ValueError("duplicate captured backup path")
        result[item.relative_path] = item.payload
    return result


def _provenance_summary(payloads: Mapping[str, bytes]) -> dict[str, Any]:
    from runtime.tools.provenance import (
        RUNTIME_PROVENANCE_SCHEMA_VERSION,
        RUNTIME_PROVENANCE_SCHEMA_VERSIONS,
        _decode_lines,
        _verify_entries,
    )

    raw = payloads.get("runtime/state/provenance/runtime_provenance_log.jsonl", b"")
    entries, parse_issues = _decode_lines(raw)
    verification = _verify_entries(entries, parse_issues)
    if not verification.ok:
        raise ValueError("runtime provenance chain is invalid")
    if any(item.get("schema_version") not in RUNTIME_PROVENANCE_SCHEMA_VERSIONS for item in entries):
        raise ValueError("runtime provenance schema is unsupported")
    schema = str(entries[-1]["schema_version"]) if entries else RUNTIME_PROVENANCE_SCHEMA_VERSION
    return {
        "entry_count": verification.entry_count,
        "latest_entry_hash": verification.terminal_hash,
        "schema_generation": schema,
    }


def _inventory(values: Sequence[_CapturedFile]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {name: 0 for name, _classification in _RESOURCE_INVENTORY}
    for item in values:
        path = item.relative_path
        if path.startswith("runtime/state/tasks/"):
            counts["task_checkpoints"] += 1
        elif path.startswith("runtime/state/idempotency/"):
            counts["idempotency_records"] += 1
        elif path == "runtime/state/provenance/runtime_provenance_log.jsonl":
            counts["runtime_provenance"] += 1
        elif path.startswith("runtime/state/provenance/outbox/"):
            counts["provenance_outbox"] += 1
        elif path == "runtime/state/provenance/provenance_log.jsonl":
            counts["legacy_provenance"] += 1
        elif path in {"runtime/state/model_config.json", "runtime/state/providers.json"}:
            counts["non_secret_configuration"] += 1
        elif path.startswith("trust/"):
            counts["trusted_anchor_public_records"] += 1
    return [
        {
            "resource": name,
            "classification": classification.value,
            "included_count": counts[name],
        }
        for name, classification in _RESOURCE_INVENTORY
    ]


def _build_manifest(
    values: Sequence[_CapturedFile],
    *,
    project_identity: str,
    source_commit: str | None,
    anchor: Mapping[str, Any],
) -> dict[str, Any]:
    payloads = _payload_by_path(values)
    rows = [
        {
            "relative_path": item.relative_path,
            "classification": item.classification.value,
            "size_bytes": len(item.payload),
            "sha256": hashlib.sha256(item.payload).hexdigest(),
        }
        for item in sorted(values, key=lambda candidate: candidate.relative_path)
    ]
    core: dict[str, Any] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "project_identity": project_identity,
        "source_commit": source_commit,
        "nz_architecture_version": NZ_ARCHITECTURE_VERSION,
        "configuration_schema_version": "AOIA_STARTUP_PREFLIGHT_1A",
        "resources": rows,
        "resource_inventory": _inventory(values),
        "provenance": _provenance_summary(payloads),
        "anchor": dict(anchor),
    }
    digest = _core_hash(core)
    return {
        **core,
        "core_hash": digest,
        "backup_id": f"backup_{digest}",
    }


def _expected_directories(files: set[str], extra: Sequence[str] = ()) -> set[str]:
    directories: set[str] = set()
    for relative in (*files, *extra):
        parsed = PurePosixPath(relative)
        for index in range(1, len(parsed.parts)):
            directories.add("/".join(parsed.parts[:index]))
        if relative in extra:
            directories.add(relative)
    return directories


def _walk_backup_files(
    root: Path,
    *,
    expected_directories: set[str],
) -> tuple[str, ...]:
    root_before = root.lstat()
    root_fd = _open_directory(root)
    values: list[str] = []
    directories: set[str] = set()
    entry_count = 0

    def walk(descriptor: int, prefix: tuple[str, ...]) -> None:
        nonlocal entry_count
        if len(prefix) > 16:
            raise ValueError("backup tree depth exceeds its bound")
        names = sorted(os.listdir(descriptor))
        entry_count += len(names)
        if entry_count > MAX_BACKUP_FILES * 2 + 64:
            raise ValueError("backup tree exceeds its entry bound")
        for name in names:
            if (
                not isinstance(name, str)
                or not name
                or name in {".", ".."}
                or "\\" in name
                or any(ord(ch) < 32 or ord(ch) > 126 for ch in name)
            ):
                raise ValueError("backup tree contains an unsafe name")
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if metadata.st_uid != os.getuid():
                raise ValueError("backup resource owner is invalid")
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError("backup tree contains a symbolic link")
            if stat.S_ISDIR(metadata.st_mode):
                if stat.S_IMODE(metadata.st_mode) & 0o077:
                    raise ValueError("backup directory is not owner-only")
                child = os.open(name, _directory_flags(), dir_fd=descriptor)
                try:
                    opened = os.fstat(child)
                    if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                        raise ValueError("backup directory binding changed")
                    child_prefix = (*prefix, name)
                    directories.add("/".join(child_prefix))
                    walk(child, child_prefix)
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) & 0o077:
                    raise ValueError("backup file is not private and unique")
                relative = "/".join((*prefix, name))
                if len(relative.encode("ascii")) > MAX_BACKUP_PATH_BYTES + 16:
                    raise ValueError("backup tree path exceeds its bound")
                values.append(relative)
            else:
                raise ValueError("backup tree contains a special file")

    try:
        walk(root_fd, ())
    finally:
        os.close(root_fd)
    root_after = root.lstat()
    if (
        stat.S_ISLNK(root_after.st_mode)
        or (root_after.st_dev, root_after.st_ino) != (root_before.st_dev, root_before.st_ino)
        or root_after.st_mtime_ns != root_before.st_mtime_ns
        or root_after.st_ctime_ns != root_before.st_ctime_ns
    ):
        raise ValueError("backup root binding changed during verification")
    if directories != expected_directories:
        raise ValueError("backup directory set is not exact")
    return tuple(values)


def _expected_classification(relative: str) -> ResourceClassification:
    if relative.startswith("runtime/state/tasks/"):
        return ResourceClassification.REQUIRED_FOR_RECOVERY
    if relative.startswith("runtime/state/idempotency/"):
        return ResourceClassification.REQUIRED_FOR_RECOVERY
    if relative == "runtime/state/provenance/runtime_provenance_log.jsonl":
        return ResourceClassification.REQUIRED_FOR_RECOVERY
    if relative.startswith("runtime/state/provenance/outbox/"):
        return ResourceClassification.REQUIRED_FOR_RECOVERY
    if relative == "runtime/state/provenance/provenance_log.jsonl":
        return ResourceClassification.OPTIONAL_REBUILDABLE
    if relative in {"runtime/state/model_config.json", "runtime/state/providers.json"}:
        return ResourceClassification.OPTIONAL_REBUILDABLE
    if relative.startswith("trust/anchor/") or relative.startswith("trust/registry/"):
        return ResourceClassification.REQUIRED_FOR_RECOVERY
    raise ValueError("backup resource path is not allowlisted")


def _validate_semantic_resources(
    payloads: Mapping[str, bytes],
    project_identity: str,
) -> None:
    from runtime.task_checkpoints import TaskCheckpoint
    from runtime.tools.idempotency import IdempotencyRecord
    from runtime.tools.provenance import (
        RuntimeProvenanceEvent,
        _TERMINAL_EVENT_TYPES,
        _decode_lines,
        _event_hash,
        _verify_entries,
    )

    task_count = 0
    idempotency_count = 0
    for relative, payload in payloads.items():
        if relative.startswith("runtime/state/tasks/"):
            match = re.fullmatch(r"runtime/state/tasks/([0-9a-f]{64})/checkpoint\.json", relative)
            if match is None:
                raise ValueError("checkpoint path is invalid")
            checkpoint = TaskCheckpoint.from_payload(_strict_json(payload, 2 * 1024 * 1024))
            if checkpoint.project_scope != project_identity:
                raise ValueError("checkpoint project identity mismatch")
            if hashlib.sha256(checkpoint.task_id.encode("ascii")).hexdigest() != match.group(1):
                raise ValueError("checkpoint path identity mismatch")
            task_count += 1
        elif relative.startswith("runtime/state/idempotency/"):
            match = re.fullmatch(r"runtime/state/idempotency/([0-9a-f]{64})\.json", relative)
            if match is None:
                raise ValueError("idempotency path is invalid")
            record = IdempotencyRecord.from_payload(_strict_json(payload, 64 * 1024))
            if record.project_scope != project_identity:
                raise ValueError("idempotency project identity mismatch")
            if hashlib.sha256(record.operation_key.encode("ascii")).hexdigest() != match.group(1):
                raise ValueError("idempotency path identity mismatch")
            idempotency_count += 1
        elif relative == "runtime/state/provenance/provenance_log.jsonl":
            entries, issues = _decode_lines(payload)
            if not _verify_entries(entries, issues).ok:
                raise ValueError("legacy provenance chain is invalid")
        elif relative.startswith("runtime/state/provenance/outbox/"):
            name = PurePosixPath(relative).name
            document = _strict_json(payload, 64 * 1024)
            event_hash = document.get("event_hash")
            event_document = {key: value for key, value in document.items() if key != "event_hash"}
            event = RuntimeProvenanceEvent.from_event_document(event_document)
            if (
                event_hash != _event_hash(event_document)
                or event.event_type not in _TERMINAL_EVENT_TYPES
                or name != f"{event.event_id}.json"
            ):
                raise ValueError("provenance outbox identity is invalid")
        elif relative == "runtime/state/model_config.json":
            config = _strict_json(payload, 256 * 1024)
            if (
                set(config) != {"model"}
                or not isinstance(config["model"], str)
                or not 1 <= len(config["model"]) <= 512
                or any(ord(character) < 32 for character in config["model"])
            ):
                raise ValueError("model configuration is invalid")
        elif relative == "runtime/state/providers.json":
            config = _strict_json(payload, 256 * 1024)
            providers = config.get("providers")
            if set(config) != {"providers"} or not isinstance(providers, list) or not 1 <= len(providers) <= 32:
                raise ValueError("provider configuration is invalid")
            for item in providers:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"name", "model", "enabled"}
                    or not isinstance(item["enabled"], bool)
                    or not isinstance(item["name"], str)
                    or not isinstance(item["model"], str)
                    or not 1 <= len(item["name"]) <= 512
                    or not 1 <= len(item["model"]) <= 512
                    or any(ord(character) < 32 for character in item["name"] + item["model"])
                ):
                    raise ValueError("provider configuration entry is invalid")
    if (task_count or idempotency_count) and "runtime/state/provenance/runtime_provenance_log.jsonl" not in payloads:
        raise ValueError("durable recovery records require runtime provenance")


def _validate_anchor_snapshot(
    payload_root: Path,
    payloads: Mapping[str, bytes],
    anchor: Mapping[str, Any],
    project_identity: str,
    expected_root_fingerprint: str | None,
) -> str:
    expected_fields = {
        "status",
        "anchor_id",
        "ledger_identity",
        "root_public_key_fingerprint",
        "public_key_fingerprint",
    }
    if set(anchor) != expected_fields:
        raise ValueError("anchor manifest has an inexact schema")
    status = anchor["status"]
    trust_paths = [name for name in payloads if name.startswith("trust/")]
    if status == "NOT_CONFIGURED":
        if trust_paths or any(anchor[field] is not None for field in expected_fields - {"status"}):
            raise ValueError("unconfigured anchor manifest contains trust records")
        return "NOT_CONFIGURED"
    if status not in {"VALID", "STALE"}:
        raise ValueError("anchor status is unsupported")
    for field in (
        "ledger_identity",
        "root_public_key_fingerprint",
        "public_key_fingerprint",
    ):
        if not isinstance(anchor[field], str) or HEX_64.fullmatch(anchor[field]) is None:
            raise ValueError("anchor manifest digest is invalid")
    if (
        expected_root_fingerprint is None
        or expected_root_fingerprint != anchor["root_public_key_fingerprint"]
    ):
        raise ValueError("independent anchor trust-root fingerprint is missing or wrong")
    if not isinstance(anchor["anchor_id"], str) or re.fullmatch(r"anchor_[0-9a-f]{32}", anchor["anchor_id"]) is None:
        raise ValueError("anchor ID is invalid")

    from runtime.tools import provenance_anchor as anchor_module

    anchor_root = payload_root / "trust" / "anchor"
    registry = payload_root / "trust" / "registry"
    archive = anchor_module._validated_anchor_archive(
        anchor_root,
        registry,
        project_identity=project_identity,
        ledger_identity=anchor["ledger_identity"],
        expected_root_fingerprint=expected_root_fingerprint,
    )
    if not archive:
        raise ValueError("anchor archive is empty")
    archive_path, latest, latest_hash = archive[-1]
    active_key = anchor_module._validated_registry_tip(
        registry,
        project_identity=project_identity,
        expected_root_fingerprint=expected_root_fingerprint,
    )
    pointer_value = anchor_module._read_record(
        anchor_root / "latest_anchor.json",
        maximum_bytes=anchor_module.MAX_ANCHOR_BYTES,
    )
    if pointer_value is None:
        raise ValueError("anchor pointer is missing")
    pointer = anchor_module._validate_latest_anchor_record(
        pointer_value,
        expected_project_identity=project_identity,
        expected_ledger_identity=anchor["ledger_identity"],
    )
    if (
        pointer["anchor_id"] != latest["anchor_id"]
        or pointer["anchor_hash"] != latest_hash
        or pointer["anchor_filename"] != archive_path.name
        or pointer["entry_count"] != latest["entry_count"]
        or pointer["latest_entry_hash"] != latest["latest_entry_hash"]
        or latest["public_key_fingerprint"] != active_key["public_key_fingerprint"]
        or latest["anchor_id"] != anchor["anchor_id"]
        or latest["public_key_fingerprint"] != anchor["public_key_fingerprint"]
    ):
        raise ValueError("anchor pointer/archive/key tip mismatch")
    runtime_payload = payloads.get("runtime/state/provenance/runtime_provenance_log.jsonl")
    if runtime_payload is None:
        raise ValueError("anchored runtime ledger is missing")
    from runtime.tools.provenance import RUNTIME_PROVENANCE_SCHEMA_VERSION, _decode_lines, _verify_entries

    entries, issues = _decode_lines(runtime_payload)
    full = _verify_entries(entries, issues)
    anchored_count = latest["entry_count"]
    if not full.ok or anchored_count > full.entry_count:
        raise ValueError("anchored ledger is invalid or truncated")
    prefix = _verify_entries(entries[:anchored_count])
    prefix_schema = (
        str(entries[anchored_count - 1]["schema_version"])
        if anchored_count
        else RUNTIME_PROVENANCE_SCHEMA_VERSION
    )
    if (
        not prefix.ok
        or prefix.terminal_hash != latest["latest_entry_hash"]
        or prefix_schema != latest["provenance_schema_generation"]
    ):
        raise ValueError("signed anchor does not match ledger prefix")
    actual_status = "VALID" if anchored_count == full.entry_count else "STALE"
    if actual_status != status:
        raise ValueError("anchor freshness status is untruthful")
    return actual_status


def _verify_bundle_or_raise(
    backup_dir: Path,
    project_dir: Path,
    *,
    expected_root_fingerprint: str | None,
    allow_staging: bool,
) -> BackupVerificationResult:
    root = _safe_directory(backup_dir, create=False)
    root_identity = root.lstat()
    if not allow_staging and BACKUP_NAME.fullmatch(root.name) is None:
        raise _BackupInvalid(BackupStatus.BACKUP_INCOMPLETE, "Backup directory is not finalized.")
    try:
        manifest_bytes = _read_private(root / "manifest.json", MAX_BACKUP_MANIFEST_BYTES)
    except FileNotFoundError as exc:
        raise _BackupInvalid(BackupStatus.BACKUP_INCOMPLETE, "Backup manifest is missing.") from exc
    manifest = _strict_json(manifest_bytes, MAX_BACKUP_MANIFEST_BYTES)
    if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise _BackupInvalid(BackupStatus.BACKUP_SCHEMA_UNSUPPORTED, "Backup schema is unsupported.")
    expected_manifest_fields = {
        "schema_version",
        "backup_id",
        "core_hash",
        "project_identity",
        "source_commit",
        "nz_architecture_version",
        "configuration_schema_version",
        "resources",
        "resource_inventory",
        "provenance",
        "anchor",
    }
    if set(manifest) != expected_manifest_fields or manifest_bytes != _canonical_json(manifest):
        raise ValueError("backup manifest is not canonical exact-schema JSON")
    core = {key: value for key, value in manifest.items() if key not in {"backup_id", "core_hash"}}
    digest = _core_hash(core)
    if manifest["core_hash"] != digest or manifest["backup_id"] != f"backup_{digest}":
        raise ValueError("backup manifest core hash is invalid")
    if not allow_staging and root.name != manifest["backup_id"]:
        raise ValueError("backup directory identity does not match manifest")
    manifest_project_identity = manifest["project_identity"]
    if (
        not isinstance(manifest_project_identity, str)
        or HEX_64.fullmatch(manifest_project_identity) is None
    ):
        raise ValueError("backup project identity is invalid")
    source_commit = manifest["source_commit"]
    if source_commit is not None and (not isinstance(source_commit, str) or HEX_COMMIT.fullmatch(source_commit) is None):
        raise ValueError("source commit is invalid")
    if (
        manifest["nz_architecture_version"] != NZ_ARCHITECTURE_VERSION
        or manifest["configuration_schema_version"] != "AOIA_STARTUP_PREFLIGHT_1A"
    ):
        raise _BackupInvalid(BackupStatus.BACKUP_SCHEMA_UNSUPPORTED, "Backup architecture version is unsupported.")

    rows = manifest["resources"]
    if not isinstance(rows, list) or len(rows) > MAX_BACKUP_FILES:
        raise ValueError("backup resource list is invalid")
    payloads: dict[str, bytes] = {}
    total = 0
    prior = ""
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"relative_path", "classification", "size_bytes", "sha256"}:
            raise ValueError("backup resource row is invalid")
        relative = _safe_relative_path(row["relative_path"])
        if relative <= prior or relative in payloads:
            raise ValueError("backup resource rows are duplicate or unordered")
        prior = relative
        expected_classification = _expected_classification(relative)
        if row["classification"] != expected_classification.value:
            raise ValueError("backup resource classification is untruthful")
        size = row["size_bytes"]
        if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_BACKUP_FILE_BYTES:
            raise ValueError("backup resource size is invalid")
        if not isinstance(row["sha256"], str) or HEX_64.fullmatch(row["sha256"]) is None:
            raise ValueError("backup resource hash is invalid")
        try:
            payload = _read_private(root / "payload" / Path(*PurePosixPath(relative).parts))
        except FileNotFoundError as exc:
            if expected_classification is ResourceClassification.REQUIRED_FOR_RECOVERY:
                raise _BackupInvalid(BackupStatus.BACKUP_INCOMPLETE, "Required backup resource is missing.") from exc
            raise ValueError("listed backup resource is missing") from exc
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError("backup resource content hash is invalid")
        total += len(payload)
        if total > MAX_BACKUP_TOTAL_BYTES:
            raise ValueError("backup resource total exceeds its bound")
        payloads[relative] = payload
    expected_files = {"manifest.json", *(f"payload/{relative}" for relative in payloads)}
    extra_directories = (
        tuple(f"payload/{relative}" for relative in _REQUIRED_TRUST_DIRECTORIES)
        if manifest["anchor"]["status"] != "NOT_CONFIGURED"
        else ()
    )
    actual_files = set(
        _walk_backup_files(
            root,
            expected_directories=_expected_directories(expected_files, extra_directories),
        )
    )
    if actual_files != expected_files:
        raise ValueError("backup payload file set is not exact")

    inventory = manifest["resource_inventory"]
    if not isinstance(inventory, list) or len(inventory) != len(_RESOURCE_INVENTORY):
        raise ValueError("backup resource inventory is invalid")
    for item in inventory:
        if (
            not isinstance(item, dict)
            or set(item) != {"resource", "classification", "included_count"}
            or not isinstance(item["resource"], str)
            or not isinstance(item["classification"], str)
            or isinstance(item["included_count"], bool)
            or not isinstance(item["included_count"], int)
            or not 0 <= item["included_count"] <= MAX_BACKUP_FILES
        ):
            raise ValueError("backup resource inventory is invalid")
    expected_inventory = _inventory(
        tuple(
            _CapturedFile(path, _expected_classification(path), payload)
            for path, payload in payloads.items()
        )
    )
    if inventory != expected_inventory:
        raise ValueError("backup resource inventory is invalid")
    manifest_provenance = manifest["provenance"]
    if (
        not isinstance(manifest_provenance, dict)
        or set(manifest_provenance)
        != {"entry_count", "latest_entry_hash", "schema_generation"}
        or isinstance(manifest_provenance["entry_count"], bool)
        or not isinstance(manifest_provenance["entry_count"], int)
        or not 0 <= manifest_provenance["entry_count"] <= MAX_BACKUP_FILE_BYTES
        or not isinstance(manifest_provenance["latest_entry_hash"], str)
        or HEX_64.fullmatch(manifest_provenance["latest_entry_hash"]) is None
        or not isinstance(manifest_provenance["schema_generation"], str)
        or not 1 <= len(manifest_provenance["schema_generation"]) <= 128
    ):
        raise ValueError("backup provenance summary is invalid")
    _validate_semantic_resources(payloads, manifest_project_identity)
    provenance = _provenance_summary(payloads)
    if manifest_provenance != provenance:
        raise ValueError("backup provenance summary is untruthful")
    anchor_status = _validate_anchor_snapshot(
        root / "payload",
        payloads,
        manifest["anchor"],
        manifest_project_identity,
        expected_root_fingerprint,
    )
    root_after = root.lstat()
    if (
        stat.S_ISLNK(root_after.st_mode)
        or (root_after.st_dev, root_after.st_ino)
        != (root_identity.st_dev, root_identity.st_ino)
        or root_after.st_mtime_ns != root_identity.st_mtime_ns
        or root_after.st_ctime_ns != root_identity.st_ctime_ns
    ):
        raise ValueError("backup root changed during full verification")
    if manifest_project_identity != _project_identity(project_dir):
        raise _BackupInvalid(
            BackupStatus.BACKUP_PROJECT_MISMATCH,
            "Backup belongs to another project.",
        )
    return BackupVerificationResult(
        BackupStatus.BACKUP_VALID,
        backup_id=manifest["backup_id"],
        file_count=len(payloads),
        total_bytes=total,
        provenance_entry_count=provenance["entry_count"],
        provenance_tip=provenance["latest_entry_hash"],
        anchor_status=anchor_status,
        message_safe="Backup is complete and independently verified.",
    )


def verify_state_backup(
    backup_dir: str | Path,
    *,
    project_dir: str | Path,
    expected_root_fingerprint: str | None = None,
) -> BackupVerificationResult:
    try:
        return _verify_bundle_or_raise(
            Path(backup_dir),
            Path(project_dir),
            expected_root_fingerprint=expected_root_fingerprint,
            allow_staging=False,
        )
    except _BackupInvalid as exc:
        return BackupVerificationResult(exc.status, message_safe=str(exc))
    except FileNotFoundError:
        return BackupVerificationResult(
            BackupStatus.BACKUP_INCOMPLETE,
            message_safe="Backup directory or manifest is missing.",
        )
    except Exception:
        return BackupVerificationResult(
            BackupStatus.BACKUP_CORRUPT,
            message_safe="Backup failed integrity, path, schema, or trust verification.",
        )


def _anchor_manifest(
    report: Any,
    environment: Mapping[str, str],
    captured: Sequence[_CapturedFile],
) -> dict[str, Any]:
    if report.anchor_status is AnchorConfigurationStatus.ANCHOR_NOT_CONFIGURED:
        return {
            "status": "NOT_CONFIGURED",
            "anchor_id": None,
            "ledger_identity": None,
            "root_public_key_fingerprint": None,
            "public_key_fingerprint": None,
        }
    if report.anchor_status not in {
        AnchorConfigurationStatus.ANCHOR_VALID,
        AnchorConfigurationStatus.ANCHOR_STALE,
    }:
        raise StateBackupSourceError("Configured provenance anchor is not valid enough to back up.")
    root_fingerprint = environment.get(ANCHOR_ROOT_FINGERPRINT_ENV, "").strip()
    if HEX_64.fullmatch(root_fingerprint) is None:
        raise StateBackupSourceError("Independent anchor trust-root pin is invalid.")
    pointer_payload = _payload_by_path(captured).get("trust/anchor/latest_anchor.json")
    if pointer_payload is None:
        raise StateBackupSourceError("Configured provenance anchor pointer is missing.")
    pointer = _strict_json(pointer_payload, 16 * 1024)
    ledger_identity = pointer.get("ledger_identity")
    if not isinstance(ledger_identity, str) or HEX_64.fullmatch(ledger_identity) is None:
        raise StateBackupSourceError("Configured provenance ledger identity is invalid.")
    return {
        "status": (
            "VALID"
            if report.anchor_status is AnchorConfigurationStatus.ANCHOR_VALID
            else "STALE"
        ),
        "anchor_id": report.anchor_id,
        "ledger_identity": ledger_identity,
        "root_public_key_fingerprint": root_fingerprint,
        "public_key_fingerprint": report.anchor_public_key_fingerprint,
    }


def _create_staging(root: Path, prefix: str) -> Path:
    root_fd = _open_directory(root)
    try:
        for _attempt in range(32):
            name = f"{prefix}{uuid.uuid4().hex}"
            try:
                os.mkdir(name, mode=0o700, dir_fd=root_fd)
            except FileExistsError:
                continue
            os.fsync(root_fd)
            return root / name
    finally:
        os.close(root_fd)
    raise StateBackupDestinationError("Could not allocate a unique staging directory.")


def create_state_backup(
    project_dir: str | Path,
    backup_root: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
    repository_root: str | Path | None = None,
) -> BackupCreationResult:
    project = Path(project_dir).resolve(strict=True)
    environment = dict(os.environ if environ is None else environ)
    report = run_startup_preflight(
        project,
        mode=StartupMode.CLI,
        environ=environment,
        repository_root=repository_root,
    )
    if report.status in {
        StartupStatus.BLOCKED_CONFIGURATION,
        StartupStatus.BLOCKED_STATE,
        StartupStatus.BLOCKED_PROVENANCE,
        StartupStatus.BLOCKED_SECURITY_INVARIANT,
    }:
        raise StateBackupSourceError("Startup integrity blocked backup creation.")
    runtime_root = _derive_state_root(project, environment)
    root_lexical = _absolute_lexical(Path(backup_root))
    repository = (
        Path(repository_root).resolve(strict=True)
        if repository_root is not None
        else project.resolve(strict=True)
    )
    anchor_paths: list[Path] = []
    for name in (ANCHOR_ROOT_ENV, ANCHOR_REGISTRY_ENV):
        raw = environment.get(name, "").strip()
        if raw:
            anchor_paths.append(_absolute_lexical(Path(raw)))
    if any(_overlaps(root_lexical, forbidden) for forbidden in (runtime_root, repository, *anchor_paths)):
        raise StateBackupDestinationError("Backup root overlaps source, trust, or repository state.")
    try:
        root = _safe_directory(root_lexical, create=False)
    except (FileNotFoundError, ValueError) as exc:
        raise StateBackupDestinationError(
            "Backup root must be a pre-existing owner-only directory."
        ) from exc

    captured = _capture_runtime_state(runtime_root)
    if report.anchor_status in {
        AnchorConfigurationStatus.ANCHOR_VALID,
        AnchorConfigurationStatus.ANCHOR_STALE,
    }:
        if len(anchor_paths) != 2:
            raise StateBackupSourceError("Configured anchor paths are incomplete.")
        _capture_public_anchor_records(captured, anchor_paths[0], anchor_paths[1])
        _materialize_verified_empty_anchored_ledger(captured)
    anchor = _anchor_manifest(report, environment, captured)
    manifest = _build_manifest(
        captured,
        project_identity=report.project_identity or _project_identity(project),
        source_commit=report.source_commit,
        anchor=anchor,
    )
    backup_id = manifest["backup_id"]
    final = root / backup_id

    # Fence the snapshot against source membership/content/configuration drift.
    # A backup is finalized only when two complete independent captures agree.
    second_report = run_startup_preflight(
        project,
        mode=StartupMode.CLI,
        environ=environment,
        repository_root=repository_root,
    )
    second_captured = _capture_runtime_state(runtime_root)
    if second_report.anchor_status in {
        AnchorConfigurationStatus.ANCHOR_VALID,
        AnchorConfigurationStatus.ANCHOR_STALE,
    }:
        if len(anchor_paths) != 2:
            raise StateBackupSourceError("Configured anchor paths are incomplete.")
        _capture_public_anchor_records(second_captured, anchor_paths[0], anchor_paths[1])
        _materialize_verified_empty_anchored_ledger(second_captured)
    second_anchor = _anchor_manifest(second_report, environment, second_captured)
    first_snapshot = tuple(
        (item.relative_path, item.classification.value, item.payload)
        for item in sorted(captured, key=lambda candidate: candidate.relative_path)
    )
    second_snapshot = tuple(
        (item.relative_path, item.classification.value, item.payload)
        for item in sorted(second_captured, key=lambda candidate: candidate.relative_path)
    )
    if (
        second_report.status != report.status
        or second_report.project_identity != report.project_identity
        or second_report.source_commit != report.source_commit
        or second_report.anchor_status != report.anchor_status
        or second_report.anchor_id != report.anchor_id
        or second_report.anchor_public_key_fingerprint
        != report.anchor_public_key_fingerprint
        or second_anchor != anchor
        or second_snapshot != first_snapshot
    ):
        raise StateBackupSourceError("Backup source changed during the stability fence.")

    staging = _create_staging(root, ".aoia-backup-partial-")
    promoted = False
    try:
        for item in sorted(captured, key=lambda candidate: candidate.relative_path):
            _write_private_file_at(
                staging,
                f"payload/{item.relative_path}",
                item.payload,
            )
        if anchor["status"] != "NOT_CONFIGURED":
            for relative in _REQUIRED_TRUST_DIRECTORIES:
                _ensure_internal_directory_at(staging, f"payload/{relative}")
        _write_manifest_at(staging, _canonical_json(manifest))
        _fsync_tree(staging)
        external_pin = anchor["root_public_key_fingerprint"]
        staged = _verify_bundle_or_raise(
            staging,
            project,
            expected_root_fingerprint=external_pin,
            allow_staging=True,
        )
        if not staged.valid:
            raise StateBackupSourceError("Staged backup failed independent verification.")
        with InterProcessFileLock(root / ".backup-operation.lock"):
            try:
                _promote_directory(staging, final, root)
                promoted = True
            except FileExistsError:
                existing = verify_state_backup(
                    final,
                    project_dir=project,
                    expected_root_fingerprint=external_pin,
                )
                if not existing.valid or existing.backup_id != backup_id:
                    raise StateBackupDestinationError("Existing backup identity is conflicting or corrupt.")
                _remove_staging(staging, root, ".aoia-backup-partial-")
                return BackupCreationResult(backup_id, final, existing, reused_existing=True)
        final_verification = verify_state_backup(
            final,
            project_dir=project,
            expected_root_fingerprint=external_pin,
        )
        if not final_verification.valid:
            raise StateBackupDestinationError("Finalized backup failed independent verification.")
        return BackupCreationResult(backup_id, final, final_verification)
    finally:
        if not promoted:
            _remove_staging(staging, root, ".aoia-backup-partial-")


def _load_manifest(backup_dir: Path) -> dict[str, Any]:
    return _strict_json(
        _read_private(backup_dir / "manifest.json", MAX_BACKUP_MANIFEST_BYTES),
        MAX_BACKUP_MANIFEST_BYTES,
    )


def _restored_runtime_root(project: Path, home: Path) -> Path:
    return _derive_state_root(project, {"AOIA_HOME": str(home)})


def _copy_bundle_to_restore(
    backup_dir: Path,
    staging_home: Path,
    project: Path,
    manifest: Mapping[str, Any],
) -> None:
    staged_runtime = _restored_runtime_root(project, staging_home)
    runtime_relative = staged_runtime.relative_to(staging_home).as_posix()
    for row in manifest["resources"]:
        relative = _safe_relative_path(row["relative_path"])
        source = backup_dir / "payload" / Path(*PurePosixPath(relative).parts)
        payload = _read_private(source)
        if len(payload) != row["size_bytes"] or hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise StateBackupSourceError("Backup resource changed during restore.")
        if relative.startswith("runtime/"):
            destination_relative = f"{runtime_relative}/{relative[len('runtime/') :]}"
        else:
            destination_relative = relative
        _write_internal_file_at(staging_home, destination_relative, payload)
    if manifest["anchor"]["status"] != "NOT_CONFIGURED":
        for relative in _REQUIRED_TRUST_DIRECTORIES:
            _ensure_internal_directory_at(staging_home, relative)


def _verify_restored_hashes(
    destination_home: Path,
    project: Path,
    manifest: Mapping[str, Any],
) -> None:
    runtime_root = _restored_runtime_root(project, destination_home)
    expected_files: set[str] = set()
    for row in manifest["resources"]:
        relative = _safe_relative_path(row["relative_path"])
        if relative.startswith("runtime/"):
            path = runtime_root / Path(*PurePosixPath(relative[len("runtime/") :]).parts)
        else:
            path = destination_home / Path(*PurePosixPath(relative).parts)
        expected_files.add(path.relative_to(destination_home).as_posix())
        payload = _read_private(path)
        if len(payload) != row["size_bytes"] or hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise StateBackupDestinationError("Restored resource hash verification failed.")
    extra_directories = (
        _REQUIRED_TRUST_DIRECTORIES
        if manifest["anchor"]["status"] != "NOT_CONFIGURED"
        else ()
    )
    actual_files = set(
        _walk_backup_files(
            destination_home,
            expected_directories=_expected_directories(expected_files, extra_directories),
        )
    )
    if actual_files != expected_files:
        raise StateBackupDestinationError("Restored resource file set is not exact.")


def _restore_preflight(
    destination_home: Path,
    project: Path,
    environment: Mapping[str, str],
    repository_root: str | Path | None,
) -> Any:
    restored_environment = dict(environment)
    restored_environment["AOIA_HOME"] = str(destination_home)
    for name in (
        ANCHOR_ROOT_ENV,
        ANCHOR_REGISTRY_ENV,
        ANCHOR_ROOT_FINGERPRINT_ENV,
        "AOIA_PROVIDER_CALLS_ENABLED",
    ):
        restored_environment.pop(name, None)
    return run_startup_preflight(
        project,
        mode=StartupMode.CLI,
        environ=restored_environment,
        repository_root=repository_root,
    )


def restore_state_backup(
    backup_dir: str | Path,
    destination_home: str | Path,
    *,
    project_dir: str | Path,
    environ: Mapping[str, str] | None = None,
    repository_root: str | Path | None = None,
    expected_root_fingerprint: str | None = None,
) -> RestoreResult:
    project = Path(project_dir).resolve(strict=True)
    backup = Path(backup_dir)
    verification = verify_state_backup(
        backup,
        project_dir=project,
        expected_root_fingerprint=expected_root_fingerprint,
    )
    if not verification.valid:
        return RestoreResult(
            RestoreStatus.RESTORE_REJECTED,
            verification.backup_id,
            verification.status,
            reason_code="RESTORE_BACKUP_INVALID",
        )
    manifest = _load_manifest(backup)
    environment = dict(os.environ if environ is None else environ)
    destination = _absolute_lexical(Path(destination_home))
    if destination.exists() or destination.is_symlink():
        return RestoreResult(
            RestoreStatus.RESTORE_REJECTED,
            verification.backup_id,
            verification.status,
            reason_code="RESTORE_DESTINATION_EXISTS",
        )
    try:
        parent = _safe_directory(destination.parent, create=False)
        live_root = _derive_state_root(project, environment)
        repository = (
            Path(repository_root).resolve(strict=True)
            if repository_root is not None
            else project
        )
        backup_root = _safe_directory(backup, create=False)
        if any(
            _overlaps(destination, forbidden)
            for forbidden in (live_root, repository, project, backup_root)
        ):
            raise StateBackupDestinationError("Restore destination overlaps protected live state.")
    except Exception:
        return RestoreResult(
            RestoreStatus.RESTORE_REJECTED,
            verification.backup_id,
            verification.status,
            reason_code="RESTORE_DESTINATION_UNSAFE",
        )

    staging = _create_staging(parent, ".aoia-restore-partial-")
    promoted = False
    try:
        _copy_bundle_to_restore(backup_root, staging, project, manifest)
        _verify_restored_hashes(staging, project, manifest)
        repeated = _verify_bundle_or_raise(
            backup_root,
            project,
            expected_root_fingerprint=expected_root_fingerprint,
            allow_staging=False,
        )
        if repeated.backup_id != verification.backup_id:
            raise StateBackupSourceError("Backup identity changed during restore.")
        staged_preflight = _restore_preflight(
            staging,
            project,
            environment,
            repository_root,
        )
        if staged_preflight.status in {
            StartupStatus.BLOCKED_CONFIGURATION,
            StartupStatus.BLOCKED_STATE,
            StartupStatus.BLOCKED_PROVENANCE,
            StartupStatus.BLOCKED_SECURITY_INVARIANT,
        }:
            raise StateBackupDestinationError("Restored staging failed startup integrity.")
        if manifest["source_commit"] is not None and staged_preflight.source_commit != manifest["source_commit"]:
            raise StateBackupDestinationError("Restored source commit does not match backup.")
        _fsync_tree(staging)
        with InterProcessFileLock(parent / ".restore-operation.lock"):
            _promote_directory(staging, destination, parent)
            promoted = True
        _verify_restored_hashes(destination, project, manifest)
        final_preflight = _restore_preflight(
            destination,
            project,
            environment,
            repository_root,
        )
        if final_preflight.status in {
            StartupStatus.BLOCKED_CONFIGURATION,
            StartupStatus.BLOCKED_STATE,
            StartupStatus.BLOCKED_PROVENANCE,
            StartupStatus.BLOCKED_SECURITY_INVARIANT,
        }:
            raise StateBackupDestinationError("Final restored state failed startup integrity.")
        _verify_restored_hashes(destination, project, manifest)
        if final_preflight.status is StartupStatus.MANUAL_REVIEW_REQUIRED:
            return RestoreResult(
                RestoreStatus.RESTORE_MANUAL_REVIEW_REQUIRED,
                verification.backup_id,
                verification.status,
                startup_status=final_preflight.status.value,
                anchor_snapshot_status=verification.anchor_status,
                reason_code="RESTORE_MANUAL_REVIEW_REQUIRED",
            )
        return RestoreResult(
            RestoreStatus.RESTORE_VALIDATED,
            verification.backup_id,
            verification.status,
            startup_status=final_preflight.status.value,
            anchor_snapshot_status=verification.anchor_status,
            reason_code="RESTORE_VERIFIED",
        )
    except FileExistsError:
        return RestoreResult(
            RestoreStatus.RESTORE_REJECTED,
            verification.backup_id,
            verification.status,
            reason_code="RESTORE_DESTINATION_EXISTS",
        )
    except Exception:
        return RestoreResult(
            RestoreStatus.RESTORE_REJECTED,
            verification.backup_id,
            verification.status,
            reason_code="RESTORE_VALIDATION_FAILED",
        )
    finally:
        if not promoted:
            _remove_staging(staging, parent, ".aoia-restore-partial-")


def run_local_disaster_recovery_drill(
    project_dir: str | Path,
    scratch_root: str | Path,
    *,
    repository_root: str | Path | None = None,
) -> DisasterRecoveryDrillResult:
    project = Path(project_dir).resolve(strict=True)
    scratch_lexical = _absolute_lexical(Path(scratch_root))
    repository = (
        Path(repository_root).resolve(strict=True)
        if repository_root is not None
        else project
    )
    if _overlaps(scratch_lexical, repository):
        raise StateBackupDestinationError("DR scratch root overlaps the repository.")
    try:
        scratch = _safe_directory(scratch_lexical, create=False)
    except (FileNotFoundError, ValueError) as exc:
        raise StateBackupDestinationError(
            "DR scratch root must be a pre-existing owner-only directory."
        ) from exc
    operation = _create_staging(scratch, ".aoia-drill-")
    try:
        operation_fd = _open_directory(operation)
        try:
            for name in ("source-home", "backups"):
                descriptor = _open_or_create_child(operation_fd, name)
                os.close(descriptor)
            os.fsync(operation_fd)
        finally:
            os.close(operation_fd)
        source_home = operation / "source-home"
        source_runtime = _restored_runtime_root(project, source_home)
        source_relative = source_runtime.relative_to(operation).as_posix()
        _write_internal_file_at(
            operation,
            f"{source_relative}/state/model_config.json",
            _canonical_json({"model": "synthetic-dr-model"}),
        )
        _write_internal_file_at(
            operation,
            f"{source_relative}/state/providers.json",
            _canonical_json(
                {
                    "providers": [
                        {"name": "local", "model": "synthetic", "enabled": False}
                    ]
                }
            ),
        )
        import datetime as dt

        from runtime.tools.provenance import (
            AppendOnlyProvenanceStore,
            RuntimeProvenanceEventType,
            new_runtime_provenance_event,
        )
        from runtime.trace_context import TraceContext

        trace = TraceContext(
            request_id="request_" + "1" * 32,
            trace_id="trace_" + "2" * 32,
            task_id="task_" + "3" * 32,
        )
        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.REQUEST_STARTED,
            trace_context=trace,
            ingress="RUNTIME",
            request_length=17,
            slash_command=False,
            clock=lambda: dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        )
        event = replace(event, event_id="provenance_event_" + "4" * 32)
        store = AppendOnlyProvenanceStore(source_runtime / "state")
        store.append_runtime_event(event)
        environment = {"AOIA_HOME": str(source_home)}
        created = create_state_backup(
            project,
            operation / "backups",
            environ=environment,
            repository_root=repository_root,
        )
        verified = verify_state_backup(created.backup_path, project_dir=project)
        restored = restore_state_backup(
            created.backup_path,
            operation / "restore-home",
            project_dir=project,
            environ=environment,
            repository_root=repository_root,
        )
        return DisasterRecoveryDrillResult(
            backup_status=verified.status,
            restore_status=restored.status,
            startup_status=restored.startup_status,
            provenance_entry_count=verified.provenance_entry_count,
            passed=(
                verified.valid
                and verified.provenance_entry_count == 1
                and restored.success
            ),
        )
    finally:
        _remove_staging(operation, scratch, ".aoia-drill-")


__all__ = [
    "BACKUP_SCHEMA_VERSION",
    "NZ_ARCHITECTURE_VERSION",
    "BackupCreationResult",
    "BackupStatus",
    "BackupVerificationResult",
    "DisasterRecoveryDrillResult",
    "ResourceClassification",
    "RestoreResult",
    "RestoreStatus",
    "StateBackupDestinationError",
    "StateBackupError",
    "StateBackupSourceError",
    "create_state_backup",
    "restore_state_backup",
    "run_local_disaster_recovery_drill",
    "verify_state_backup",
]
