from __future__ import annotations

import base64
import binascii
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Mapping

if __name__ == "runtime.tools.provenance_anchor":
    sys.modules.setdefault("tools.provenance_anchor", sys.modules[__name__])
elif __name__ == "tools.provenance_anchor":
    sys.modules.setdefault("runtime.tools.provenance_anchor", sys.modules[__name__])


from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    InterProcessFileLock,
    locked_update_json,
    read_json_snapshot,
    state_resource_lock_path,
    validate_lock_timeout_seconds,
)
from runtime.tools.idempotency import project_scope_fingerprint
from runtime.tools.provenance import (
    GENESIS_PREV_HASH,
    MAX_PROVENANCE_LOG_BYTES,
    RUNTIME_PROVENANCE_SCHEMA_VERSION,
    RUNTIME_PROVENANCE_SCHEMA_VERSIONS,
    _decode_lines,
    _public_ledger_lock_path,
    _read_safe_regular_file,
    _verify_entries,
)


ANCHOR_SCHEMA_VERSION = "AOIA_PROVENANCE_ANCHOR_1A"
PUBLIC_KEY_SCHEMA_VERSION = "AOIA_PROVENANCE_PUBLIC_KEY_1A"
ROTATION_SCHEMA_VERSION = "AOIA_PROVENANCE_KEY_ROTATION_1A"
LATEST_ANCHOR_SCHEMA_VERSION = "AOIA_PROVENANCE_ANCHOR_LATEST_1A"
TRUST_ROOT_SCHEMA_VERSION = "AOIA_PROVENANCE_TRUST_ROOT_1A"
LATEST_KEY_SCHEMA_VERSION = "AOIA_PROVENANCE_KEY_LATEST_1A"
SIGNATURE_ALGORITHM = "Ed25519"
SIGNATURE_DOMAIN = b"AOIA-Core/provenance-anchor-1a\x00"
ROTATION_DOMAIN = b"AOIA-Core/provenance-key-rotation-1a\x00"
MAX_ANCHOR_BYTES = 16 * 1024
MAX_KEY_RECORD_BYTES = 8 * 1024
MAX_ROTATION_RECORD_BYTES = 16 * 1024
MAX_ANCHORS = 4_096
MAX_KEYS = 128

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_ANCHOR_ID = re.compile(r"^anchor_[0-9a-f]{32}$")


class AnchorStatus(str, Enum):
    ANCHOR_VALID = "ANCHOR_VALID"
    ANCHOR_SIGNATURE_INVALID = "ANCHOR_SIGNATURE_INVALID"
    ANCHOR_LEDGER_MISMATCH = "ANCHOR_LEDGER_MISMATCH"
    ANCHOR_UNKNOWN_KEY = "ANCHOR_UNKNOWN_KEY"
    ANCHOR_SCHEMA_UNSUPPORTED = "ANCHOR_SCHEMA_UNSUPPORTED"
    ANCHOR_CRYPTO_UNAVAILABLE = "ANCHOR_CRYPTO_UNAVAILABLE"


class ProvenanceAnchorError(RuntimeError):
    reason_code = "PROVENANCE_ANCHOR_ERROR"


class ProvenanceAnchorConfigurationError(ProvenanceAnchorError):
    reason_code = "PROVENANCE_ANCHOR_CONFIGURATION_INVALID"


class ProvenanceAnchorCryptoUnavailable(ProvenanceAnchorError):
    reason_code = AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE.value


class _AnchorSignatureInvalid(ValueError):
    """Internal typed signal for a structurally valid bad anchor signature."""


@dataclass(frozen=True)
class AnchorCreationResult:
    anchor_id: str
    anchor_sequence: int
    anchor_path: Path
    latest_pointer_path: Path
    entry_count: int
    latest_entry_hash: str
    public_key_fingerprint: str

    def __post_init__(self) -> None:
        if not _ANCHOR_ID.fullmatch(self.anchor_id):
            raise ValueError("anchor_id is invalid")
        _bounded_int(
            self.anchor_sequence,
            minimum=1,
            maximum=MAX_ANCHORS,
            label="anchor sequence",
        )
        if isinstance(self.entry_count, bool) or not isinstance(self.entry_count, int):
            raise TypeError("entry_count must be an integer")
        if self.entry_count < 0 or self.entry_count > 10_000_000:
            raise ValueError("entry_count is outside policy bounds")
        for value in (self.latest_entry_hash, self.public_key_fingerprint):
            if not isinstance(value, str) or not _HEX_64.fullmatch(value):
                raise ValueError("anchor result contains an invalid digest")


@dataclass(frozen=True)
class AnchorVerificationResult:
    status: AnchorStatus
    anchor_id: str | None = None
    anchored_entry_count: int | None = None
    actual_entry_count: int | None = None
    is_current: bool = False
    public_key_fingerprint: str | None = None
    message_safe: str = "Provenance anchor verification failed."

    def __post_init__(self) -> None:
        if not isinstance(self.status, AnchorStatus):
            raise TypeError("status must be AnchorStatus")
        if self.anchor_id is not None and not _ANCHOR_ID.fullmatch(self.anchor_id):
            raise ValueError("anchor_id is invalid")
        for value in (self.anchored_entry_count, self.actual_entry_count):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                or value > 10_000_000
            ):
                raise ValueError("verification count is outside policy bounds")
        if not isinstance(self.is_current, bool):
            raise TypeError("is_current must be boolean")
        if self.is_current and self.status is not AnchorStatus.ANCHOR_VALID:
            raise ValueError("only a valid anchor may be current")
        if self.public_key_fingerprint is not None and not _HEX_64.fullmatch(
            self.public_key_fingerprint
        ):
            raise ValueError("public key fingerprint is invalid")
        if not isinstance(self.message_safe, str) or not self.message_safe:
            raise ValueError("message_safe must be non-empty text")
        if self.status is AnchorStatus.ANCHOR_VALID and (
            self.anchor_id is None
            or self.anchored_entry_count is None
            or self.actual_entry_count is None
            or self.public_key_fingerprint is None
        ):
            raise ValueError("valid anchor result is incomplete")

    @property
    def valid(self) -> bool:
        return self.status is AnchorStatus.ANCHOR_VALID


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _timestamp(clock: Callable[[], dt.datetime] | None = None) -> str:
    value = (clock or (lambda: dt.datetime.now(dt.UTC)))()
    if not isinstance(value, dt.datetime):
        raise ProvenanceAnchorConfigurationError("Anchor clock returned an invalid value.")
    if value.tzinfo is None:
        raise ProvenanceAnchorConfigurationError("Anchor clock must be timezone-aware.")
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _crypto() -> tuple[Any, Any, Any]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except (ImportError, OSError) as exc:
        raise ProvenanceAnchorCryptoUnavailable(
            "Local Ed25519 support is unavailable."
        ) from exc
    return (Ed25519PrivateKey, Ed25519PublicKey, (serialization, InvalidSignature))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _strict_json_loads(payload: bytes, *, maximum_bytes: int) -> dict[str, Any]:
    if not payload or len(payload) > maximum_bytes:
        raise ValueError("JSON record is empty or exceeds its size bound")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("JSON record is not UTF-8") from exc

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("JSON record is malformed") from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("JSON record must be an object with text keys")
    if payload != _stored_json(value):
        raise ValueError("JSON record is not in the canonical storage form")
    return value


def _stored_json(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _read_record(path: Path, *, maximum_bytes: int) -> dict[str, Any] | None:
    """Read one atomic record without creating a directory or lock file."""

    try:
        parent = path.parent.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(parent.st_mode) or not stat.S_ISDIR(parent.st_mode):
        raise ValueError("record parent is not a safe directory")
    payload = _read_safe_regular_file(path, maximum_bytes=maximum_bytes)
    if payload is None:
        return None
    return _strict_json_loads(payload, maximum_bytes=maximum_bytes)


def _safe_directory(path: Path, *, create: bool) -> Path:
    if not path.is_absolute():
        raise ProvenanceAnchorConfigurationError("State directory must be absolute.")
    lexical = Path(os.path.abspath(path))
    current = Path(lexical.anchor)
    for component in lexical.parts[1:]:
        current = current / component
        try:
            component_metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(component_metadata.st_mode):
            raise ProvenanceAnchorConfigurationError(
                "State directory path traverses a symbolic link."
            )
    if create:
        lexical.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        metadata = lexical.lstat()
    except FileNotFoundError as exc:
        raise ProvenanceAnchorConfigurationError(
            "Required state directory is missing."
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ProvenanceAnchorConfigurationError("State directory is unsafe.")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ProvenanceAnchorConfigurationError(
            "Trusted state directory must be owner-only."
        )
    if lexical.resolve(strict=True) != lexical:
        raise ProvenanceAnchorConfigurationError(
            "State directory path is not canonical."
        )
    return lexical


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 40:
        raise ValueError("timestamp is invalid")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    canonical = parsed.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise ValueError("timestamp is not canonical UTC")
    return value


def _bounded_int(value: Any, *, minimum: int, maximum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{label} is outside policy bounds")
    return value


def _digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _HEX_64.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _b64decode(value: Any, *, expected_bytes: int, label: str) -> bytes:
    if not isinstance(value, str) or len(value) > (expected_bytes * 2 + 8):
        raise ValueError(f"{label} is invalid")
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeError, binascii.Error) as exc:
        raise ValueError(f"{label} is invalid") from exc
    if len(decoded) != expected_bytes or base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{label} is invalid")
    return decoded


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _project_identity(project_dir: Path) -> str:
    path = Path(project_dir)
    if not path.is_absolute():
        raise ProvenanceAnchorConfigurationError("Project path must be absolute.")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ProvenanceAnchorConfigurationError("Project path is not a directory.")
    return project_scope_fingerprint(resolved)


def _ledger_identity(ledger_path: Path, project_identity: str) -> str:
    path = Path(ledger_path)
    if not path.is_absolute():
        raise ProvenanceAnchorConfigurationError("Ledger path must be absolute.")
    material = {
        "domain": "AOIA_RUNTIME_PROVENANCE_LEDGER_IDENTITY_1A",
        "project_identity": project_identity,
        "resolved_ledger_path": str(path.resolve(strict=False)),
    }
    return _sha256_bytes(_canonical_json(material))


def _key_fingerprint(public_key_bytes: bytes) -> str:
    return _sha256_bytes(b"AOIA-Core/Ed25519-public-key-1a\x00" + public_key_bytes)


def _private_key_forbidden_roots(
    *,
    repository_root: Path,
    project_dir: Path,
    ledger_path: Path | None,
    anchor_root: Path | None,
    public_key_registry: Path | None,
) -> tuple[Path, ...]:
    repository = Path(repository_root).resolve(strict=True)
    project = Path(project_dir).resolve(strict=True)
    if repository != project:
        raise ProvenanceAnchorConfigurationError(
            "Repository root must match the trusted resolved project path."
        )
    roots = [repository, project]
    if ledger_path is not None:
        roots.append(Path(ledger_path).resolve(strict=False).parent)
    for value in (anchor_root, public_key_registry):
        if value is not None:
            roots.append(Path(value).resolve(strict=False))
    return tuple(roots)


def _private_key_path(
    value: Path,
    *,
    repository_root: Path,
    project_dir: Path,
    ledger_path: Path | None = None,
    anchor_root: Path | None = None,
    public_key_registry: Path | None = None,
    require_exists: bool,
) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ProvenanceAnchorConfigurationError(
            "Private signing key path must be absolute."
        )
    lexical = Path(os.path.abspath(path))
    resolved = path.resolve(strict=require_exists)
    if lexical != resolved:
        raise ProvenanceAnchorConfigurationError(
            "Private signing key path must not traverse symbolic links."
        )
    for root in _private_key_forbidden_roots(
        repository_root=repository_root,
        project_dir=project_dir,
        ledger_path=ledger_path,
        anchor_root=anchor_root,
        public_key_registry=public_key_registry,
    ):
        if _is_relative_to(lexical, root) or lexical == root:
            raise ProvenanceAnchorConfigurationError(
                "Private signing key must be outside repository and runtime records."
            )
    parent = lexical.parent
    metadata = parent.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ProvenanceAnchorConfigurationError("Private key directory is unsafe.")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ProvenanceAnchorConfigurationError(
            "Private key directory must be owner-only."
        )
    return lexical


def _load_private_key(
    private_key_path: Path,
    *,
    repository_root: Path,
    project_dir: Path,
    ledger_path: Path | None = None,
    anchor_root: Path | None = None,
    public_key_registry: Path | None = None,
) -> tuple[Any, bytes, str]:
    path = _private_key_path(
        private_key_path,
        repository_root=repository_root,
        project_dir=project_dir,
        ledger_path=ledger_path,
        anchor_root=anchor_root,
        public_key_registry=public_key_registry,
        require_exists=True,
    )
    before = path.lstat()
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
        or before.st_size < 1
        or before.st_size > 4096
    ):
        raise ProvenanceAnchorConfigurationError(
            "Private signing key is not a unique owner-only regular file."
        )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProvenanceAnchorConfigurationError(
            "Private signing key could not be opened safely."
        ) from exc
    try:
        opened = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            or opened.st_nlink != 1
            or opened.st_uid != os.getuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise ProvenanceAnchorConfigurationError(
                "Private signing key changed during open."
            )
        payload = os.read(descriptor, 4097)
        if len(payload) < 1 or len(payload) > 4096:
            raise ProvenanceAnchorConfigurationError(
                "Private signing key exceeds its size bound."
            )
    finally:
        os.close(descriptor)
    Ed25519PrivateKey, _Ed25519PublicKey, crypto_support = _crypto()
    serialization, _InvalidSignature = crypto_support
    try:
        key = serialization.load_pem_private_key(payload, password=None)
    except (TypeError, ValueError) as exc:
        raise ProvenanceAnchorConfigurationError(
            "Private signing key is not valid unencrypted PKCS8 PEM."
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise ProvenanceAnchorConfigurationError("Signing key must be Ed25519.")
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return key, public_bytes, _key_fingerprint(public_bytes)


def provision_external_signing_key(
    private_key_path: Path,
    *,
    repository_root: Path,
    project_dir: Path,
    ledger_path: Path | None = None,
    anchor_root: Path | None = None,
    public_key_registry: Path | None = None,
) -> str:
    """Create one owner-only external Ed25519 key without overwriting a path."""

    requested = Path(private_key_path)
    if not requested.is_absolute():
        raise ProvenanceAnchorConfigurationError(
            "Private signing key path must be absolute."
        )
    lexical = Path(os.path.abspath(requested))
    resolved_candidate = requested.resolve(strict=False)
    if resolved_candidate != lexical:
        raise ProvenanceAnchorConfigurationError(
            "Private signing key path must not traverse symbolic links."
        )
    for root in _private_key_forbidden_roots(
        repository_root=repository_root,
        project_dir=project_dir,
        ledger_path=ledger_path,
        anchor_root=anchor_root,
        public_key_registry=public_key_registry,
    ):
        if _is_relative_to(lexical, root) or lexical == root:
            raise ProvenanceAnchorConfigurationError(
                "Private signing key must be outside repository and runtime records."
            )
    target = lexical
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = _private_key_path(
        target,
        repository_root=repository_root,
        project_dir=project_dir,
        ledger_path=ledger_path,
        anchor_root=anchor_root,
        public_key_registry=public_key_registry,
        require_exists=False,
    )
    Ed25519PrivateKey, _Ed25519PublicKey, crypto_support = _crypto()
    serialization, _InvalidSignature = crypto_support
    # Avoid the generic ``.generate()`` spelling reserved by the runtime's
    # live-model callsite fence.  A fresh 32-byte OS CSPRNG seed is the native
    # Ed25519 private-key input accepted by cryptography.
    key = Ed25519PrivateKey.from_private_bytes(os.urandom(32))
    payload = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    lock_path = target.parent / f".{target.name}.provision.lock"
    with InterProcessFileLock(lock_path) as lock:
        if target.exists() or target.is_symlink():
            raise ProvenanceAnchorConfigurationError(
                "Private signing key path already exists."
            )
        parent_fd = os.open(
            target.parent,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        temp_name = f".{target.name}.{uuid.uuid4().hex}.tmp"
        temp_fd: int | None = None
        linked = False
        try:
            temp_fd = os.open(
                temp_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            view = memoryview(payload)
            while view:
                written = os.write(temp_fd, view)
                if written <= 0:
                    raise OSError("short private key write")
                view = view[written:]
            os.fsync(temp_fd)
            os.close(temp_fd)
            temp_fd = None
            os.link(
                temp_name,
                target.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            linked = True
            os.unlink(temp_name, dir_fd=parent_fd)
            os.fsync(parent_fd)
            lock.validate_binding()
        finally:
            if temp_fd is not None:
                os.close(temp_fd)
            if not linked:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)
    _key, public_bytes, fingerprint = _load_private_key(
        target,
        repository_root=repository_root,
        project_dir=project_dir,
        ledger_path=ledger_path,
        anchor_root=anchor_root,
        public_key_registry=public_key_registry,
    )
    return fingerprint


_PUBLIC_KEY_FIELDS = frozenset(
    {
        "schema_version",
        "project_identity",
        "public_key_fingerprint",
        "signature_algorithm",
        "public_key_b64",
        "generation",
        "activated_at_utc",
        "previous_public_key_fingerprint",
        "rotation_signature_b64",
        "new_key_proof_b64",
    }
)
_ROTATION_FIELDS = frozenset(
    {
        "schema_version",
        "project_identity",
        "generation",
        "previous_public_key_fingerprint",
        "new_public_key_fingerprint",
        "activated_at_utc",
        "signature_algorithm",
    }
)
_ROTATION_RECORD_FIELDS = frozenset(
    {*_ROTATION_FIELDS, "rotation_signature_b64", "new_key_proof_b64"}
)
_TRUST_ROOT_FIELDS = frozenset(
    {"schema_version", "project_identity", "root_public_key_fingerprint"}
)
_LATEST_KEY_FIELDS = frozenset(
    {
        "schema_version",
        "project_identity",
        "generation",
        "public_key_fingerprint",
    }
)


def _rotation_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ROTATION_SCHEMA_VERSION,
        "project_identity": record["project_identity"],
        "generation": record["generation"],
        "previous_public_key_fingerprint": record[
            "previous_public_key_fingerprint"
        ],
        "new_public_key_fingerprint": record["public_key_fingerprint"],
        "activated_at_utc": record["activated_at_utc"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
    }


def _validate_public_key_record(
    value: Mapping[str, Any], *, expected_project_identity: str
) -> dict[str, Any]:
    if frozenset(value) != _PUBLIC_KEY_FIELDS:
        raise ValueError("public key record has an inexact schema")
    record = dict(value)
    if record["schema_version"] != PUBLIC_KEY_SCHEMA_VERSION:
        raise ValueError("public key schema is unsupported")
    if record["project_identity"] != expected_project_identity:
        raise ValueError("public key project identity mismatch")
    if record["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise ValueError("public key algorithm is unsupported")
    fingerprint = _digest(
        record["public_key_fingerprint"], label="public key fingerprint"
    )
    public_bytes = _b64decode(
        record["public_key_b64"], expected_bytes=32, label="public key"
    )
    if _key_fingerprint(public_bytes) != fingerprint:
        raise ValueError("public key fingerprint mismatch")
    generation = _bounded_int(
        record["generation"], minimum=1, maximum=MAX_KEYS, label="key generation"
    )
    _validate_timestamp(record["activated_at_utc"])
    previous = record["previous_public_key_fingerprint"]
    rotation_signature = record["rotation_signature_b64"]
    new_key_proof = record["new_key_proof_b64"]
    if generation == 1:
        if previous is not None or rotation_signature is not None or new_key_proof is not None:
            raise ValueError("root public key contains rotation metadata")
    else:
        _digest(previous, label="previous public key fingerprint")
        _b64decode(rotation_signature, expected_bytes=64, label="rotation signature")
        _b64decode(new_key_proof, expected_bytes=64, label="new key proof")
        if previous == fingerprint:
            raise ValueError("public key rotation cannot point to itself")
    return record


def _validate_root_record(
    value: Mapping[str, Any], *, expected_project_identity: str
) -> dict[str, Any]:
    if frozenset(value) != _TRUST_ROOT_FIELDS:
        raise ValueError("trust root record has an inexact schema")
    record = dict(value)
    if record["schema_version"] != TRUST_ROOT_SCHEMA_VERSION:
        raise ValueError("trust root schema is unsupported")
    if record["project_identity"] != expected_project_identity:
        raise ValueError("trust root project identity mismatch")
    _digest(record["root_public_key_fingerprint"], label="root fingerprint")
    return record


def _validate_latest_key_record(
    value: Mapping[str, Any], *, expected_project_identity: str
) -> dict[str, Any]:
    if frozenset(value) != _LATEST_KEY_FIELDS:
        raise ValueError("latest key record has an inexact schema")
    record = dict(value)
    if record["schema_version"] != LATEST_KEY_SCHEMA_VERSION:
        raise ValueError("latest key schema is unsupported")
    if record["project_identity"] != expected_project_identity:
        raise ValueError("latest key project identity mismatch")
    _bounded_int(record["generation"], minimum=1, maximum=MAX_KEYS, label="generation")
    _digest(record["public_key_fingerprint"], label="public key fingerprint")
    return record


def _public_key_record_path(registry: Path, fingerprint: str) -> Path:
    return registry / "keys" / f"key_{fingerprint}.json"


def _rotation_record_path(registry: Path, generation: int) -> Path:
    return registry / "rotations" / f"rotation_{generation:03d}.json"


def _count_bounded(directory: Path, *, suffix: str, maximum: int) -> int:
    count = 0
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name.endswith(suffix):
                count += 1
                if count > maximum:
                    raise ProvenanceAnchorConfigurationError(
                        "Trusted record directory exceeds its bounded capacity."
                    )
    return count


class _PinnedDirectory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.descriptor: int | None = None
        self.identity: tuple[int, int] | None = None

    def __enter__(self) -> "_PinnedDirectory":
        before = self.path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
            raise ProvenanceAnchorConfigurationError("Pinned directory is unsafe.")
        descriptor = os.open(
            self.path,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if identity != (before.st_dev, before.st_ino):
            os.close(descriptor)
            raise ProvenanceAnchorConfigurationError(
                "Pinned directory changed during open."
            )
        self.descriptor = descriptor
        self.identity = identity
        self.validate()
        return self

    def validate(self) -> None:
        if self.descriptor is None or self.identity is None:
            raise ProvenanceAnchorConfigurationError("Directory pin is not held.")
        opened = os.fstat(self.descriptor)
        visible = self.path.lstat()
        if (
            (opened.st_dev, opened.st_ino) != self.identity
            or (visible.st_dev, visible.st_ino) != self.identity
            or stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISDIR(visible.st_mode)
        ):
            raise ProvenanceAnchorConfigurationError(
                "Pinned directory binding changed."
            )

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        descriptor = self.descriptor
        self.descriptor = None
        self.identity = None
        if descriptor is not None:
            os.close(descriptor)


def _write_immutable_record(
    path: Path,
    record: Mapping[str, Any],
    *,
    state_root: Path,
    maximum_bytes: int,
    lock_timeout_seconds: float,
    parent_pin: _PinnedDirectory | None = None,
    lock_parent_pin: _PinnedDirectory | None = None,
    precomputed_lock_path: Path | None = None,
    allow_existing_exact: bool = False,
) -> None:
    if len(_stored_json(record)) > maximum_bytes:
        raise ProvenanceAnchorConfigurationError("Record exceeds its size bound.")

    existing = (
        read_json_snapshot(
            path,
            reject_duplicate_keys=True,
            maximum_bytes=maximum_bytes,
            expected_parent_identity=parent_pin.identity,
            parent_directory_descriptor=parent_pin.descriptor,
            directory_identity_validator=parent_pin.validate,
        )
        if parent_pin is not None
        else _read_record(path, maximum_bytes=maximum_bytes)
    )
    if existing is not None:
        if allow_existing_exact and existing == dict(record):
            return
        raise ProvenanceAnchorConfigurationError(
            "Immutable record path contains conflicting content."
        )

    def create(current: Any | None) -> tuple[dict[str, Any], None]:
        if current is not None:
            raise ProvenanceAnchorConfigurationError(
                "Immutable record path already exists."
            )
        return dict(record), None

    locked_update_json(
        path,
        create,
        lock_path=precomputed_lock_path or state_resource_lock_path(state_root, path),
        lock_timeout_seconds=lock_timeout_seconds,
        indent=None,
        sort_keys=True,
        trailing_newline=True,
        maximum_bytes=maximum_bytes,
        expected_parent_identity=(parent_pin.identity if parent_pin else None),
        parent_directory_descriptor=(parent_pin.descriptor if parent_pin else None),
        directory_identity_validator=(parent_pin.validate if parent_pin else None),
        lock_parent_directory_descriptor=(
            lock_parent_pin.descriptor if lock_parent_pin else None
        ),
        lock_directory_identity_validator=(
            lock_parent_pin.validate if lock_parent_pin else None
        ),
    )
    stored = (
        read_json_snapshot(
            path,
            reject_duplicate_keys=True,
            maximum_bytes=maximum_bytes,
            expected_parent_identity=parent_pin.identity,
            parent_directory_descriptor=parent_pin.descriptor,
            directory_identity_validator=parent_pin.validate,
        )
        if parent_pin is not None
        else _read_record(path, maximum_bytes=maximum_bytes)
    )
    if stored != dict(record):
        raise ProvenanceAnchorConfigurationError(
            "Persisted immutable record failed exact read-back."
        )


def _write_pointer_record(
    path: Path,
    record: Mapping[str, Any],
    *,
    state_root: Path,
    maximum_bytes: int,
    lock_timeout_seconds: float,
    parent_pin: _PinnedDirectory | None = None,
    lock_parent_pin: _PinnedDirectory | None = None,
    precomputed_lock_path: Path | None = None,
) -> None:
    if len(_stored_json(record)) > maximum_bytes:
        raise ProvenanceAnchorConfigurationError("Pointer exceeds its size bound.")

    def replace(_current: Any | None) -> tuple[dict[str, Any], None]:
        return dict(record), None

    locked_update_json(
        path,
        replace,
        lock_path=precomputed_lock_path or state_resource_lock_path(state_root, path),
        lock_timeout_seconds=lock_timeout_seconds,
        indent=None,
        sort_keys=True,
        trailing_newline=True,
        maximum_bytes=maximum_bytes,
        expected_parent_identity=(parent_pin.identity if parent_pin else None),
        parent_directory_descriptor=(parent_pin.descriptor if parent_pin else None),
        directory_identity_validator=(parent_pin.validate if parent_pin else None),
        lock_parent_directory_descriptor=(
            lock_parent_pin.descriptor if lock_parent_pin else None
        ),
        lock_directory_identity_validator=(
            lock_parent_pin.validate if lock_parent_pin else None
        ),
    )
    stored = (
        read_json_snapshot(
            path,
            reject_duplicate_keys=True,
            maximum_bytes=maximum_bytes,
            expected_parent_identity=parent_pin.identity,
            parent_directory_descriptor=parent_pin.descriptor,
            directory_identity_validator=parent_pin.validate,
        )
        if parent_pin is not None
        else _read_record(path, maximum_bytes=maximum_bytes)
    )
    if stored != dict(record):
        raise ProvenanceAnchorConfigurationError(
            "Persisted pointer failed exact read-back."
        )


def _write_registry_pointer_pinned(
    registry: Path,
    record: Mapping[str, Any],
    *,
    lock_timeout_seconds: float,
) -> None:
    locks_dir = _safe_directory(registry / ".locks", create=False)
    path = registry / "latest_key.json"
    lock_path = state_resource_lock_path(registry, path)
    with (
        _PinnedDirectory(registry) as registry_pin,
        _PinnedDirectory(locks_dir) as locks_pin,
    ):
        _write_pointer_record(
            path,
            record,
            state_root=registry,
            maximum_bytes=MAX_KEY_RECORD_BYTES,
            lock_timeout_seconds=lock_timeout_seconds,
            parent_pin=registry_pin,
            lock_parent_pin=locks_pin,
            precomputed_lock_path=lock_path,
        )


def _trusted_key_chain(
    registry: Path,
    *,
    project_identity: str,
    target_fingerprint: str,
    expected_root_fingerprint: str,
) -> tuple[dict[str, Any], Any]:
    _digest(expected_root_fingerprint, label="expected root fingerprint")
    root_value = _read_record(registry / "trust_root.json", maximum_bytes=MAX_KEY_RECORD_BYTES)
    if root_value is None:
        raise KeyError("trusted public-key root is missing")
    root = _validate_root_record(root_value, expected_project_identity=project_identity)
    root_fingerprint = root["root_public_key_fingerprint"]
    if root_fingerprint != expected_root_fingerprint:
        raise KeyError("trusted public-key root does not match the external pin")
    current_fingerprint = target_fingerprint
    seen: set[str] = set()
    chain: list[dict[str, Any]] = []
    while True:
        if current_fingerprint in seen or len(chain) >= MAX_KEYS:
            raise ValueError("public key trust chain is cyclic or overlong")
        seen.add(current_fingerprint)
        value = _read_record(
            _public_key_record_path(registry, current_fingerprint),
            maximum_bytes=MAX_KEY_RECORD_BYTES,
        )
        if value is None:
            raise KeyError("trusted public key is missing")
        record = _validate_public_key_record(
            value, expected_project_identity=project_identity
        )
        if record["public_key_fingerprint"] != current_fingerprint:
            raise KeyError("public key record does not match its registry identity")
        chain.append(record)
        if current_fingerprint == root_fingerprint:
            break
        previous = record["previous_public_key_fingerprint"]
        if previous is None:
            raise KeyError("public key chain does not reach the trusted root")
        current_fingerprint = previous
    if chain[-1]["generation"] != 1:
        raise ValueError("trusted root generation is invalid")
    _Private, Ed25519PublicKey, crypto_support = _crypto()
    _serialization, InvalidSignature = crypto_support
    for index in range(len(chain) - 2, -1, -1):
        newer = chain[index]
        previous = chain[index + 1]
        if newer["generation"] != previous["generation"] + 1:
            raise ValueError("public key generation is not monotonic")
        if newer["previous_public_key_fingerprint"] != previous[
            "public_key_fingerprint"
        ]:
            raise ValueError("public key rotation link mismatch")
        rotation_bytes = ROTATION_DOMAIN + _canonical_json(_rotation_payload(newer))
        previous_public = Ed25519PublicKey.from_public_bytes(
            _b64decode(previous["public_key_b64"], expected_bytes=32, label="public key")
        )
        new_public = Ed25519PublicKey.from_public_bytes(
            _b64decode(newer["public_key_b64"], expected_bytes=32, label="public key")
        )
        try:
            previous_public.verify(
                _b64decode(
                    newer["rotation_signature_b64"],
                    expected_bytes=64,
                    label="rotation signature",
                ),
                rotation_bytes,
            )
            new_public.verify(
                _b64decode(
                    newer["new_key_proof_b64"],
                    expected_bytes=64,
                    label="new key proof",
                ),
                rotation_bytes,
            )
        except InvalidSignature as exc:
            raise ValueError("public key rotation signature is invalid") from exc
        rotation_value = _read_record(
            _rotation_record_path(
                registry,
                newer["generation"],
            ),
            maximum_bytes=MAX_ROTATION_RECORD_BYTES,
        )
        if rotation_value is None:
            raise ValueError("public key rotation record is missing")
        rotation_record = _validate_rotation_record(
            rotation_value, expected_project_identity=project_identity
        )
        expected_rotation_record = {
            **_rotation_payload(newer),
            "rotation_signature_b64": newer["rotation_signature_b64"],
            "new_key_proof_b64": newer["new_key_proof_b64"],
        }
        if rotation_record != expected_rotation_record:
            raise ValueError("public key rotation record conflicts with key metadata")
    target = chain[0]
    public = Ed25519PublicKey.from_public_bytes(
        _b64decode(target["public_key_b64"], expected_bytes=32, label="public key")
    )
    return target, public


def _derived_registry_tip(
    registry: Path,
    *,
    project_identity: str,
    expected_root_fingerprint: str,
) -> dict[str, Any]:
    rotations_dir = _safe_directory(registry / "rotations", create=False)
    rotations: list[dict[str, Any]] = []
    names: list[str] = []
    with os.scandir(rotations_dir) as entries:
        for entry in entries:
            names.append(entry.name)
            if len(names) > MAX_KEYS:
                raise ProvenanceAnchorConfigurationError(
                    "Key-rotation registry exceeds its bounded capacity."
                )
    for name in sorted(names):
        match = re.fullmatch(r"rotation_([0-9]{3})\.json", name)
        if match is None:
            raise ProvenanceAnchorConfigurationError(
                "Key-rotation registry contains an unexpected entry."
            )
        generation = int(match.group(1))
        value = _read_record(
            rotations_dir / name, maximum_bytes=MAX_ROTATION_RECORD_BYTES
        )
        if value is None:
            raise ProvenanceAnchorConfigurationError(
                "Key-rotation record disappeared during validation."
            )
        record = _validate_rotation_record(
            value, expected_project_identity=project_identity
        )
        if record["generation"] != generation:
            raise ProvenanceAnchorConfigurationError(
                "Key-rotation filename and generation disagree."
            )
        rotations.append(record)
    expected_generation = 1
    expected_fingerprint = expected_root_fingerprint
    for record in rotations:
        expected_generation += 1
        if (
            record["generation"] != expected_generation
            or record["previous_public_key_fingerprint"] != expected_fingerprint
        ):
            raise ProvenanceAnchorConfigurationError(
                "Key-rotation history is not one contiguous chain."
            )
        expected_fingerprint = record["new_public_key_fingerprint"]
    _trusted_key_chain(
        registry,
        project_identity=project_identity,
        target_fingerprint=expected_fingerprint,
        expected_root_fingerprint=expected_root_fingerprint,
    )
    return {
        "schema_version": LATEST_KEY_SCHEMA_VERSION,
        "project_identity": project_identity,
        "generation": expected_generation,
        "public_key_fingerprint": expected_fingerprint,
    }


def _validated_registry_tip(
    registry: Path,
    *,
    project_identity: str,
    expected_root_fingerprint: str,
) -> dict[str, Any]:
    derived = _derived_registry_tip(
        registry,
        project_identity=project_identity,
        expected_root_fingerprint=expected_root_fingerprint,
    )
    latest_value = _read_record(
        registry / "latest_key.json", maximum_bytes=MAX_KEY_RECORD_BYTES
    )
    if latest_value is None:
        raise ProvenanceAnchorConfigurationError(
            "Trusted key registry has no active key."
        )
    latest = _validate_latest_key_record(
        latest_value, expected_project_identity=project_identity
    )
    if latest != derived:
        raise ProvenanceAnchorConfigurationError(
            "Active-key pointer is stale or conflicts with rotation history."
        )
    return latest


def register_initial_verification_key(
    public_key_registry: Path,
    *,
    private_key_path: Path,
    repository_root: Path,
    project_dir: Path,
    clock: Callable[[], dt.datetime] | None = None,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
) -> str:
    """Explicitly establish the operator-trusted root; verification never does this."""

    timeout = validate_lock_timeout_seconds(lock_timeout_seconds)
    registry = _safe_directory(Path(public_key_registry), create=True)
    keys_dir = _safe_directory(registry / "keys", create=True)
    _safe_directory(registry / "rotations", create=True)
    registry_locks = _safe_directory(registry / ".locks", create=True)
    project_identity = _project_identity(project_dir)
    key, public_bytes, fingerprint = _load_private_key(
        private_key_path,
        repository_root=repository_root,
        project_dir=project_dir,
        public_key_registry=registry,
    )
    del key
    timestamp = _timestamp(clock)
    record = {
        "schema_version": PUBLIC_KEY_SCHEMA_VERSION,
        "project_identity": project_identity,
        "public_key_fingerprint": fingerprint,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "public_key_b64": _b64encode(public_bytes),
        "generation": 1,
        "activated_at_utc": timestamp,
        "previous_public_key_fingerprint": None,
        "rotation_signature_b64": None,
        "new_key_proof_b64": None,
    }
    _validate_public_key_record(record, expected_project_identity=project_identity)
    with InterProcessFileLock(
        registry / ".registry.lock", timeout_seconds=timeout
    ) as registry_lock:
        if _read_record(registry / "trust_root.json", maximum_bytes=MAX_KEY_RECORD_BYTES) is not None:
            raise ProvenanceAnchorConfigurationError(
                "Trusted public-key root is already established."
            )
        if _count_bounded(keys_dir, suffix=".json", maximum=MAX_KEYS) >= MAX_KEYS:
            raise ProvenanceAnchorConfigurationError("Public-key registry is full.")
        key_path = _public_key_record_path(registry, fingerprint)
        root = {
            "schema_version": TRUST_ROOT_SCHEMA_VERSION,
            "project_identity": project_identity,
            "root_public_key_fingerprint": fingerprint,
        }
        root_path = registry / "trust_root.json"
        latest = {
            "schema_version": LATEST_KEY_SCHEMA_VERSION,
            "project_identity": project_identity,
            "generation": 1,
            "public_key_fingerprint": fingerprint,
        }
        latest_path = registry / "latest_key.json"
        key_lock_path = state_resource_lock_path(registry, key_path)
        root_lock_path = state_resource_lock_path(registry, root_path)
        latest_lock_path = state_resource_lock_path(registry, latest_path)
        with (
            _PinnedDirectory(registry) as registry_pin,
            _PinnedDirectory(keys_dir) as keys_pin,
            _PinnedDirectory(registry_locks) as locks_pin,
        ):
            _write_immutable_record(
                key_path,
                record,
                state_root=registry,
                maximum_bytes=MAX_KEY_RECORD_BYTES,
                lock_timeout_seconds=timeout,
                parent_pin=keys_pin,
                lock_parent_pin=locks_pin,
                precomputed_lock_path=key_lock_path,
                allow_existing_exact=True,
            )
            _write_immutable_record(
                root_path,
                root,
                state_root=registry,
                maximum_bytes=MAX_KEY_RECORD_BYTES,
                lock_timeout_seconds=timeout,
                parent_pin=registry_pin,
                lock_parent_pin=locks_pin,
                precomputed_lock_path=root_lock_path,
            )
            _write_pointer_record(
                latest_path,
                latest,
                state_root=registry,
                maximum_bytes=MAX_KEY_RECORD_BYTES,
                lock_timeout_seconds=timeout,
                parent_pin=registry_pin,
                lock_parent_pin=locks_pin,
                precomputed_lock_path=latest_lock_path,
            )
        registry_lock.validate_binding()
    return fingerprint


def _validate_rotation_record(
    value: Mapping[str, Any], *, expected_project_identity: str
) -> dict[str, Any]:
    if frozenset(value) != _ROTATION_RECORD_FIELDS:
        raise ValueError("rotation record has an inexact schema")
    record = dict(value)
    if record["schema_version"] != ROTATION_SCHEMA_VERSION:
        raise ValueError("rotation schema is unsupported")
    if record["project_identity"] != expected_project_identity:
        raise ValueError("rotation project identity mismatch")
    if record["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise ValueError("rotation algorithm is unsupported")
    _bounded_int(record["generation"], minimum=2, maximum=MAX_KEYS, label="generation")
    _digest(
        record["previous_public_key_fingerprint"],
        label="previous public key fingerprint",
    )
    _digest(record["new_public_key_fingerprint"], label="new public key fingerprint")
    _validate_timestamp(record["activated_at_utc"])
    _b64decode(record["rotation_signature_b64"], expected_bytes=64, label="rotation signature")
    _b64decode(record["new_key_proof_b64"], expected_bytes=64, label="new key proof")
    return record


def rotate_verification_key(
    public_key_registry: Path,
    *,
    current_private_key_path: Path,
    new_private_key_path: Path,
    repository_root: Path,
    project_dir: Path,
    expected_root_fingerprint: str,
    clock: Callable[[], dt.datetime] | None = None,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
) -> str:
    """Authorize one new key with both old-key authorization and new-key proof."""

    timeout = validate_lock_timeout_seconds(lock_timeout_seconds)
    registry = _safe_directory(Path(public_key_registry), create=False)
    keys_dir = _safe_directory(registry / "keys", create=False)
    rotations_dir = _safe_directory(registry / "rotations", create=False)
    registry_locks = _safe_directory(registry / ".locks", create=False)
    project_identity = _project_identity(project_dir)
    current_key, _current_public_bytes, current_fingerprint = _load_private_key(
        current_private_key_path,
        repository_root=repository_root,
        project_dir=project_dir,
        public_key_registry=registry,
    )
    new_key, new_public_bytes, new_fingerprint = _load_private_key(
        new_private_key_path,
        repository_root=repository_root,
        project_dir=project_dir,
        public_key_registry=registry,
    )
    if current_fingerprint == new_fingerprint:
        raise ProvenanceAnchorConfigurationError(
            "Key rotation requires a distinct new Ed25519 key."
        )
    with InterProcessFileLock(
        registry / ".registry.lock", timeout_seconds=timeout
    ) as registry_lock:
        derived = _derived_registry_tip(
            registry,
            project_identity=project_identity,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        latest_value = _read_record(
            registry / "latest_key.json", maximum_bytes=MAX_KEY_RECORD_BYTES
        )
        if latest_value is None:
            raise ProvenanceAnchorConfigurationError(
                "Trusted key registry has no active-key pointer."
            )
        latest = _validate_latest_key_record(
            latest_value, expected_project_identity=project_identity
        )
        if latest != derived:
            if (
                latest["public_key_fingerprint"] == current_fingerprint
                and derived["public_key_fingerprint"] == new_fingerprint
                and derived["generation"] == latest["generation"] + 1
            ):
                _write_registry_pointer_pinned(
                    registry, derived, lock_timeout_seconds=timeout
                )
                registry_lock.validate_binding()
                return new_fingerprint
            raise ProvenanceAnchorConfigurationError(
                "Active-key pointer conflicts with signed rotation history."
            )
        if latest["public_key_fingerprint"] != current_fingerprint:
            raise ProvenanceAnchorConfigurationError(
                "Rotation authorization key is not the active trusted key."
            )
        generation = _bounded_int(
            latest["generation"] + 1,
            minimum=2,
            maximum=MAX_KEYS,
            label="generation",
        )
        key_path = _public_key_record_path(registry, new_fingerprint)
        rotation_path = _rotation_record_path(registry, generation)
        existing_key = _read_record(key_path, maximum_bytes=MAX_KEY_RECORD_BYTES)
        existing_rotation = _read_record(
            rotation_path, maximum_bytes=MAX_ROTATION_RECORD_BYTES
        )
        if (
            existing_key is None
            and _count_bounded(keys_dir, suffix=".json", maximum=MAX_KEYS) >= MAX_KEYS
        ):
            raise ProvenanceAnchorConfigurationError("Public-key registry is full.")
        if (
            existing_rotation is None
            and _count_bounded(rotations_dir, suffix=".json", maximum=MAX_KEYS)
            >= MAX_KEYS - 1
        ):
            raise ProvenanceAnchorConfigurationError("Key-rotation registry is full.")
        if existing_key is None:
            unsigned_record = {
                "schema_version": PUBLIC_KEY_SCHEMA_VERSION,
                "project_identity": project_identity,
                "public_key_fingerprint": new_fingerprint,
                "signature_algorithm": SIGNATURE_ALGORITHM,
                "public_key_b64": _b64encode(new_public_bytes),
                "generation": generation,
                "activated_at_utc": _timestamp(clock),
                "previous_public_key_fingerprint": current_fingerprint,
                "rotation_signature_b64": None,
                "new_key_proof_b64": None,
            }
            rotation_payload = _rotation_payload(unsigned_record)
            rotation_bytes = ROTATION_DOMAIN + _canonical_json(rotation_payload)
            record = {
                **unsigned_record,
                "rotation_signature_b64": _b64encode(
                    current_key.sign(rotation_bytes)
                ),
                "new_key_proof_b64": _b64encode(new_key.sign(rotation_bytes)),
            }
        else:
            record = _validate_public_key_record(
                existing_key, expected_project_identity=project_identity
            )
            if (
                record["generation"] != generation
                or record["previous_public_key_fingerprint"] != current_fingerprint
                or record["public_key_fingerprint"] != new_fingerprint
                or record["public_key_b64"] != _b64encode(new_public_bytes)
            ):
                raise ProvenanceAnchorConfigurationError(
                    "Existing orphan key record conflicts with requested rotation."
                )
            rotation_payload = _rotation_payload(record)
        rotation_record = {
            **rotation_payload,
            "rotation_signature_b64": record["rotation_signature_b64"],
            "new_key_proof_b64": record["new_key_proof_b64"],
        }
        _validate_rotation_record(
            rotation_record, expected_project_identity=project_identity
        )
        new_latest = {
            "schema_version": LATEST_KEY_SCHEMA_VERSION,
            "project_identity": project_identity,
            "generation": generation,
            "public_key_fingerprint": new_fingerprint,
        }
        latest_path = registry / "latest_key.json"
        key_lock_path = state_resource_lock_path(registry, key_path)
        rotation_lock_path = state_resource_lock_path(registry, rotation_path)
        latest_lock_path = state_resource_lock_path(registry, latest_path)
        with (
            _PinnedDirectory(registry) as registry_pin,
            _PinnedDirectory(keys_dir) as keys_pin,
            _PinnedDirectory(rotations_dir) as rotations_pin,
            _PinnedDirectory(registry_locks) as locks_pin,
        ):
            _write_immutable_record(
                key_path,
                record,
                state_root=registry,
                maximum_bytes=MAX_KEY_RECORD_BYTES,
                lock_timeout_seconds=timeout,
                parent_pin=keys_pin,
                lock_parent_pin=locks_pin,
                precomputed_lock_path=key_lock_path,
                allow_existing_exact=True,
            )
            _write_immutable_record(
                rotation_path,
                rotation_record,
                state_root=registry,
                maximum_bytes=MAX_ROTATION_RECORD_BYTES,
                lock_timeout_seconds=timeout,
                parent_pin=rotations_pin,
                lock_parent_pin=locks_pin,
                precomputed_lock_path=rotation_lock_path,
                allow_existing_exact=True,
            )
            # Rebuild persisted signatures before activating the new key.
            _trusted_key_chain(
                registry,
                project_identity=project_identity,
                target_fingerprint=new_fingerprint,
                expected_root_fingerprint=expected_root_fingerprint,
            )
            _write_pointer_record(
                latest_path,
                new_latest,
                state_root=registry,
                maximum_bytes=MAX_KEY_RECORD_BYTES,
                lock_timeout_seconds=timeout,
                parent_pin=registry_pin,
                lock_parent_pin=locks_pin,
                precomputed_lock_path=latest_lock_path,
            )
        registry_lock.validate_binding()
    return new_fingerprint


_ANCHOR_FIELDS = frozenset(
    {
        "schema_version",
        "anchor_id",
        "anchor_sequence",
        "previous_anchor_hash",
        "timestamp_utc",
        "project_identity",
        "ledger_identity",
        "latest_entry_hash",
        "entry_count",
        "provenance_schema_generation",
        "signature_algorithm",
        "public_key_fingerprint",
        "signature_b64",
    }
)
_ANCHOR_PAYLOAD_FIELDS = _ANCHOR_FIELDS - {"signature_b64"}
_LATEST_ANCHOR_FIELDS = frozenset(
    {
        "schema_version",
        "project_identity",
        "ledger_identity",
        "anchor_id",
        "anchor_sequence",
        "anchor_hash",
        "anchor_filename",
        "entry_count",
        "latest_entry_hash",
    }
)


def _anchor_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {field: record[field] for field in sorted(_ANCHOR_PAYLOAD_FIELDS)}


def _validate_anchor_record(
    value: Mapping[str, Any],
    *,
    expected_project_identity: str,
    expected_ledger_identity: str,
) -> dict[str, Any]:
    if frozenset(value) != _ANCHOR_FIELDS:
        raise ValueError("anchor record has an inexact schema")
    record = dict(value)
    if record["schema_version"] != ANCHOR_SCHEMA_VERSION:
        raise ValueError("anchor schema is unsupported")
    if not isinstance(record["anchor_id"], str) or not _ANCHOR_ID.fullmatch(
        record["anchor_id"]
    ):
        raise ValueError("anchor ID is invalid")
    _bounded_int(
        record["anchor_sequence"],
        minimum=1,
        maximum=MAX_ANCHORS,
        label="anchor sequence",
    )
    _digest(record["previous_anchor_hash"], label="previous anchor hash")
    _validate_timestamp(record["timestamp_utc"])
    if record["project_identity"] != expected_project_identity:
        raise ValueError("anchor project identity mismatch")
    if record["ledger_identity"] != expected_ledger_identity:
        raise ValueError("anchor ledger identity mismatch")
    _digest(record["latest_entry_hash"], label="latest entry hash")
    _bounded_int(
        record["entry_count"],
        minimum=0,
        maximum=10_000_000,
        label="entry count",
    )
    if record["provenance_schema_generation"] not in RUNTIME_PROVENANCE_SCHEMA_VERSIONS:
        raise ValueError("anchored provenance schema generation is unsupported")
    if record["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise ValueError("anchor signature algorithm is unsupported")
    _digest(record["public_key_fingerprint"], label="public key fingerprint")
    _b64decode(record["signature_b64"], expected_bytes=64, label="anchor signature")
    return record


def _validate_latest_anchor_record(
    value: Mapping[str, Any],
    *,
    expected_project_identity: str,
    expected_ledger_identity: str,
) -> dict[str, Any]:
    if frozenset(value) != _LATEST_ANCHOR_FIELDS:
        raise ValueError("latest anchor pointer has an inexact schema")
    record = dict(value)
    if record["schema_version"] != LATEST_ANCHOR_SCHEMA_VERSION:
        raise ValueError("latest anchor pointer schema is unsupported")
    if record["project_identity"] != expected_project_identity:
        raise ValueError("latest anchor project identity mismatch")
    if record["ledger_identity"] != expected_ledger_identity:
        raise ValueError("latest anchor ledger identity mismatch")
    anchor_id = record["anchor_id"]
    if not isinstance(anchor_id, str) or not _ANCHOR_ID.fullmatch(anchor_id):
        raise ValueError("latest anchor ID is invalid")
    if record["anchor_filename"] != f"{anchor_id}.json":
        raise ValueError("latest anchor filename is invalid")
    _bounded_int(
        record["anchor_sequence"],
        minimum=1,
        maximum=MAX_ANCHORS,
        label="anchor sequence",
    )
    _digest(record["anchor_hash"], label="anchor hash")
    _bounded_int(
        record["entry_count"],
        minimum=0,
        maximum=10_000_000,
        label="entry count",
    )
    _digest(record["latest_entry_hash"], label="latest entry hash")
    return record


def _verify_anchor_signature(record: Mapping[str, Any], public_key: Any) -> None:
    _Private, _Public, crypto_support = _crypto()
    _serialization, InvalidSignature = crypto_support
    try:
        public_key.verify(
            _b64decode(
                record["signature_b64"],
                expected_bytes=64,
                label="anchor signature",
            ),
            SIGNATURE_DOMAIN + _canonical_json(_anchor_payload(record)),
        )
    except InvalidSignature as exc:
        raise _AnchorSignatureInvalid("anchor signature is invalid") from exc


def _anchor_hash(record: Mapping[str, Any]) -> str:
    return _sha256_bytes(
        b"AOIA-Core/provenance-anchor-record-1a\x00" + _canonical_json(record)
    )


def _validated_anchor_archive(
    anchor_root: Path,
    registry: Path,
    *,
    project_identity: str,
    ledger_identity: str,
    expected_root_fingerprint: str,
) -> list[tuple[Path, dict[str, Any], str]]:
    archives = _safe_directory(anchor_root / "anchors", create=False)
    names: list[str] = []
    with os.scandir(archives) as entries:
        for entry in entries:
            names.append(entry.name)
            if len(names) > MAX_ANCHORS:
                raise ProvenanceAnchorConfigurationError(
                    "Anchor archive exceeds its bounded capacity."
                )
    by_sequence: dict[int, tuple[Path, dict[str, Any], str]] = {}
    public_keys: dict[str, tuple[dict[str, Any], Any]] = {}
    for name in names:
        if re.fullmatch(r"anchor_[0-9a-f]{32}\.json", name) is None:
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive contains an unexpected entry."
            )
        path = archives / name
        value = _read_record(path, maximum_bytes=MAX_ANCHOR_BYTES)
        if value is None:
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive entry disappeared during validation."
            )
        record = _validate_anchor_record(
            value,
            expected_project_identity=project_identity,
            expected_ledger_identity=ledger_identity,
        )
        if name != f"{record['anchor_id']}.json":
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive filename conflicts with signed identity."
            )
        fingerprint = record["public_key_fingerprint"]
        trusted = public_keys.get(fingerprint)
        if trusted is None:
            key_record, public = _trusted_key_chain(
                registry,
                project_identity=project_identity,
                target_fingerprint=fingerprint,
                expected_root_fingerprint=expected_root_fingerprint,
            )
            trusted = (key_record, public)
            public_keys[fingerprint] = trusted
        key_record, public = trusted
        _verify_anchor_signature(record, public)
        sequence = record["anchor_sequence"]
        if sequence in by_sequence:
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive contains a duplicate sequence."
            )
        record["_trusted_key_generation"] = key_record["generation"]
        by_sequence[sequence] = (path, record, _anchor_hash({
            key: value for key, value in record.items()
            if key != "_trusted_key_generation"
        }))
    ordered: list[tuple[Path, dict[str, Any], str]] = []
    previous_hash = GENESIS_PREV_HASH
    previous_count = 0
    previous_ledger_hash = GENESIS_PREV_HASH
    previous_key_generation = 1
    for sequence in range(1, len(by_sequence) + 1):
        item = by_sequence.get(sequence)
        if item is None:
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive sequence has a gap."
            )
        record = dict(item[1])
        key_generation = record.pop("_trusted_key_generation")
        item = (item[0], record, item[2])
        if item[1]["previous_anchor_hash"] != previous_hash:
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive hash chain is invalid."
            )
        current_count = item[1]["entry_count"]
        current_ledger_hash = item[1]["latest_entry_hash"]
        if current_count < previous_count or (
            current_count == previous_count
            and current_ledger_hash != previous_ledger_hash
        ):
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive ledger checkpoints are not monotonic."
            )
        if key_generation < previous_key_generation:
            raise ProvenanceAnchorConfigurationError(
                "Anchor archive re-enters a retired signing generation."
            )
        ordered.append(item)
        previous_hash = item[2]
        previous_count = current_count
        previous_ledger_hash = current_ledger_hash
        previous_key_generation = key_generation
    return ordered


def _ledger_snapshot_unlocked(
    ledger_path: Path,
) -> tuple[list[dict[str, Any]], Any, str]:
    payload = _read_safe_regular_file(
        ledger_path, maximum_bytes=MAX_PROVENANCE_LOG_BYTES
    )
    entries, parse_issues = _decode_lines(payload or b"")
    verification = _verify_entries(entries, parse_issues)
    if not verification.ok:
        raise ProvenanceAnchorConfigurationError(
            "Runtime provenance ledger failed closed verification."
        )
    if any(
        entry.get("schema_version") not in RUNTIME_PROVENANCE_SCHEMA_VERSIONS
        for entry in entries
    ):
        raise ProvenanceAnchorConfigurationError(
            "Only the typed P0.8 runtime provenance ledger may be anchored."
        )
    schema_generation = (
        str(entries[-1]["schema_version"])
        if entries
        else RUNTIME_PROVENANCE_SCHEMA_VERSION
    )
    return entries, verification, schema_generation


def _anchor_path(anchor_root: Path, anchor_id: str) -> Path:
    if not _ANCHOR_ID.fullmatch(anchor_id):
        raise ValueError("anchor ID is invalid")
    return anchor_root / "anchors" / f"{anchor_id}.json"


def _persist_anchor_then_pointer(
    *,
    anchor_root: Path,
    archives: Path,
    locks_dir: Path,
    archive_path: Path,
    record: Mapping[str, Any],
    latest_pointer: Mapping[str, Any],
    public_key: Any,
    lock_timeout_seconds: float,
) -> None:
    archive_lock_path = state_resource_lock_path(anchor_root, archive_path)
    pointer_path = anchor_root / "latest_anchor.json"
    pointer_lock_path = state_resource_lock_path(anchor_root, pointer_path)
    with (
        _PinnedDirectory(anchor_root) as root_pin,
        _PinnedDirectory(archives) as archive_pin,
        _PinnedDirectory(locks_dir) as locks_pin,
    ):
        _write_immutable_record(
            archive_path,
            record,
            state_root=anchor_root,
            maximum_bytes=MAX_ANCHOR_BYTES,
            lock_timeout_seconds=lock_timeout_seconds,
            parent_pin=archive_pin,
            lock_parent_pin=locks_pin,
            precomputed_lock_path=archive_lock_path,
        )
        persisted = read_json_snapshot(
            archive_path,
            reject_duplicate_keys=True,
            maximum_bytes=MAX_ANCHOR_BYTES,
            expected_parent_identity=archive_pin.identity,
            parent_directory_descriptor=archive_pin.descriptor,
            directory_identity_validator=archive_pin.validate,
        )
        if not isinstance(persisted, dict) or persisted != dict(record):
            raise ProvenanceAnchorConfigurationError(
                "Persisted anchor archive failed exact pinned read-back."
            )
        _verify_anchor_signature(persisted, public_key)
        _write_pointer_record(
            pointer_path,
            latest_pointer,
            state_root=anchor_root,
            maximum_bytes=MAX_ANCHOR_BYTES,
            lock_timeout_seconds=lock_timeout_seconds,
            parent_pin=root_pin,
            lock_parent_pin=locks_pin,
            precomputed_lock_path=pointer_lock_path,
        )
        archive_pin.validate()
        root_pin.validate()
        locks_pin.validate()


def create_provenance_anchor(
    ledger_path: Path,
    anchor_root: Path,
    public_key_registry: Path,
    *,
    private_key_path: Path,
    expected_root_fingerprint: str,
    repository_root: Path,
    project_dir: Path,
    clock: Callable[[], dt.datetime] | None = None,
    lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
) -> AnchorCreationResult:
    """Verify the P0.8 ledger, sign its exact tip, archive, then promote latest."""

    timeout = validate_lock_timeout_seconds(lock_timeout_seconds)
    ledger = Path(ledger_path)
    if not ledger.is_absolute() or ledger.name != "runtime_provenance_log.jsonl":
        raise ProvenanceAnchorConfigurationError(
            "P1.3 anchors require the explicit runtime provenance ledger path."
        )
    anchors_root = _safe_directory(Path(anchor_root), create=True)
    archives = _safe_directory(anchors_root / "anchors", create=True)
    anchor_locks = _safe_directory(anchors_root / ".locks", create=True)
    registry = _safe_directory(Path(public_key_registry), create=False)
    _safe_directory(registry / "keys", create=False)
    _safe_directory(registry / "rotations", create=False)
    project_identity = _project_identity(project_dir)
    ledger_identity = _ledger_identity(ledger, project_identity)
    _digest(expected_root_fingerprint, label="expected root fingerprint")
    private_key, _public_bytes, signer_fingerprint = _load_private_key(
        private_key_path,
        repository_root=repository_root,
        project_dir=project_dir,
        ledger_path=ledger,
        anchor_root=anchors_root,
        public_key_registry=registry,
    )
    with InterProcessFileLock(
        registry / ".registry.lock", timeout_seconds=timeout
    ) as registry_lock:
        latest_key = _validated_registry_tip(
            registry,
            project_identity=project_identity,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        if latest_key["public_key_fingerprint"] != signer_fingerprint:
            raise ProvenanceAnchorConfigurationError(
                "Anchor signer is not the active trusted key."
            )
        _key_record, public_key = _trusted_key_chain(
            registry,
            project_identity=project_identity,
            target_fingerprint=signer_fingerprint,
            expected_root_fingerprint=expected_root_fingerprint,
        )
        with InterProcessFileLock(
            anchors_root / ".anchor-create.lock", timeout_seconds=timeout
        ) as anchor_lock:
            archive_chain = _validated_anchor_archive(
                anchors_root,
                registry,
                project_identity=project_identity,
                ledger_identity=ledger_identity,
                expected_root_fingerprint=expected_root_fingerprint,
            )
            if len(archive_chain) >= MAX_ANCHORS:
                raise ProvenanceAnchorConfigurationError(
                    "Anchor archive reached its bounded capacity."
                )
            with InterProcessFileLock(
                _public_ledger_lock_path(ledger), timeout_seconds=timeout
            ) as ledger_lock:
                entries, verification, schema_generation = _ledger_snapshot_unlocked(
                    ledger
                )
                ledger_lock.validate_binding()
                previous_anchor_hash = GENESIS_PREV_HASH
                if archive_chain:
                    _previous_path, previous_anchor, previous_anchor_hash = (
                        archive_chain[-1]
                    )
                    previous_count = previous_anchor["entry_count"]
                    if verification.entry_count < previous_count:
                        raise ProvenanceAnchorConfigurationError(
                            "Ledger rollback or replacement detected by latest anchor."
                        )
                    current_prefix_hash = (
                        GENESIS_PREV_HASH
                        if previous_count == 0
                        else str(entries[previous_count - 1].get("entry_hash", ""))
                    )
                    if current_prefix_hash != previous_anchor["latest_entry_hash"]:
                        raise ProvenanceAnchorConfigurationError(
                            "Ledger history diverges from the latest signed prefix."
                        )
                anchor_sequence = len(archive_chain) + 1
                anchor_id = f"anchor_{uuid.uuid4().hex}"
                archive_path = _anchor_path(anchors_root, anchor_id)
                unsigned = {
                    "schema_version": ANCHOR_SCHEMA_VERSION,
                    "anchor_id": anchor_id,
                    "anchor_sequence": anchor_sequence,
                    "previous_anchor_hash": previous_anchor_hash,
                    "timestamp_utc": _timestamp(clock),
                    "project_identity": project_identity,
                    "ledger_identity": ledger_identity,
                    "latest_entry_hash": verification.terminal_hash,
                    "entry_count": verification.entry_count,
                    "provenance_schema_generation": schema_generation,
                    "signature_algorithm": SIGNATURE_ALGORITHM,
                    "public_key_fingerprint": signer_fingerprint,
                }
                record = {
                    **unsigned,
                    "signature_b64": _b64encode(
                        private_key.sign(
                            SIGNATURE_DOMAIN + _canonical_json(unsigned)
                        )
                    ),
                }
                _validate_anchor_record(
                    record,
                    expected_project_identity=project_identity,
                    expected_ledger_identity=ledger_identity,
                )
                persisted = record
                latest_pointer = {
                    "schema_version": LATEST_ANCHOR_SCHEMA_VERSION,
                    "project_identity": project_identity,
                    "ledger_identity": ledger_identity,
                    "anchor_id": anchor_id,
                    "anchor_sequence": anchor_sequence,
                    "anchor_hash": _anchor_hash(persisted),
                    "anchor_filename": archive_path.name,
                    "entry_count": verification.entry_count,
                    "latest_entry_hash": verification.terminal_hash,
                }
                _persist_anchor_then_pointer(
                    anchor_root=anchors_root,
                    archives=archives,
                    locks_dir=anchor_locks,
                    archive_path=archive_path,
                    record=record,
                    latest_pointer=latest_pointer,
                    public_key=public_key,
                    lock_timeout_seconds=timeout,
                )
                ledger_lock.validate_binding()
            anchor_lock.validate_binding()
        registry_lock.validate_binding()
    return AnchorCreationResult(
        anchor_id=anchor_id,
        anchor_sequence=anchor_sequence,
        anchor_path=archive_path,
        latest_pointer_path=anchors_root / "latest_anchor.json",
        entry_count=verification.entry_count,
        latest_entry_hash=verification.terminal_hash,
        public_key_fingerprint=signer_fingerprint,
    )


def _verification_result(
    status: AnchorStatus,
    *,
    anchor_id: str | None = None,
    anchored_entry_count: int | None = None,
    actual_entry_count: int | None = None,
    is_current: bool = False,
    public_key_fingerprint: str | None = None,
    message_safe: str,
) -> AnchorVerificationResult:
    return AnchorVerificationResult(
        status=status,
        anchor_id=anchor_id,
        anchored_entry_count=anchored_entry_count,
        actual_entry_count=actual_entry_count,
        is_current=is_current,
        public_key_fingerprint=public_key_fingerprint,
        message_safe=message_safe,
    )


class _ReadOnlyExistingFileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.descriptor: int | None = None
        self.identity: tuple[int, int] | None = None

    def __enter__(self) -> "_ReadOnlyExistingFileLock":
        before = self.path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise ProvenanceAnchorConfigurationError("Existing state lock is unsafe.")
        try:
            descriptor = os.open(
                self.path,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
        except OSError as exc:
            raise ProvenanceAnchorConfigurationError(
                "Existing state lock could not be opened read-only."
            ) from exc
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if identity != (before.st_dev, before.st_ino):
            os.close(descriptor)
            raise ProvenanceAnchorConfigurationError(
                "Existing state lock changed during open."
            )
        deadline = time.monotonic() + DEFAULT_STATE_LOCK_TIMEOUT_SECONDS
        try:
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise ProvenanceAnchorConfigurationError(
                            "Existing state lock timed out."
                        ) from exc
                    time.sleep(0.01)
        except BaseException:
            os.close(descriptor)
            raise
        self.descriptor = descriptor
        self.identity = identity
        self.validate_binding()
        return self

    def validate_binding(self) -> None:
        if self.descriptor is None or self.identity is None:
            raise ProvenanceAnchorConfigurationError("Read-only state lock is not held.")
        opened = os.fstat(self.descriptor)
        visible = self.path.lstat()
        if (
            (opened.st_dev, opened.st_ino) != self.identity
            or (visible.st_dev, visible.st_ino) != self.identity
            or stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISREG(visible.st_mode)
        ):
            raise ProvenanceAnchorConfigurationError(
                "Read-only state lock binding changed."
            )

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        descriptor = self.descriptor
        self.descriptor = None
        self.identity = None
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _existing_lock(path: Path) -> Any:
    """Use an existing canonical lock without creating or opening it writable."""

    try:
        path.lstat()
    except FileNotFoundError:
        return nullcontext(None)
    return _ReadOnlyExistingFileLock(path)


def verify_provenance_anchor(
    ledger_path: Path,
    anchor_path: Path,
    public_key_registry: Path,
    *,
    expected_root_fingerprint: str,
    project_dir: Path,
) -> AnchorVerificationResult:
    """Offline read-only verification against a separately retained root pin."""

    anchor_id: str | None = None
    anchored_count: int | None = None
    fingerprint: str | None = None
    try:
        project_identity = _project_identity(project_dir)
        ledger = Path(ledger_path)
        if not ledger.is_absolute() or ledger.name != "runtime_provenance_log.jsonl":
            raise ProvenanceAnchorConfigurationError(
                "P1.3 verification requires the explicit runtime provenance ledger."
            )
        ledger_identity = _ledger_identity(ledger, project_identity)
        registry = _safe_directory(Path(public_key_registry), create=False)
        _safe_directory(registry / "keys", create=False)
        _safe_directory(registry / "rotations", create=False)
        _digest(expected_root_fingerprint, label="expected root fingerprint")
        path = Path(anchor_path)
        if not path.is_absolute():
            raise ValueError("anchor path must be absolute")
        value = _read_record(path, maximum_bytes=MAX_ANCHOR_BYTES)
        if value is None:
            raise ValueError("anchor record is missing")
        if value.get("project_identity") != project_identity or value.get(
            "ledger_identity"
        ) != ledger_identity:
            return _verification_result(
                AnchorStatus.ANCHOR_LEDGER_MISMATCH,
                message_safe="Anchor belongs to a different project or ledger.",
            )
        record = _validate_anchor_record(
            value,
            expected_project_identity=project_identity,
            expected_ledger_identity=ledger_identity,
        )
        anchor_id = record["anchor_id"]
        anchored_count = record["entry_count"]
        fingerprint = record["public_key_fingerprint"]
        if path.name != f"{anchor_id}.json":
            raise ValueError("anchor filename does not match its runtime ID")
    except ProvenanceAnchorCryptoUnavailable:
        return _verification_result(
            AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE,
            message_safe="Local Ed25519 verification support is unavailable.",
        )
    except Exception:
        return _verification_result(
            AnchorStatus.ANCHOR_SCHEMA_UNSUPPORTED,
            anchor_id=anchor_id,
            anchored_entry_count=anchored_count,
            public_key_fingerprint=fingerprint,
            message_safe="Anchor record is missing, malformed, or unsupported.",
        )

    try:
        with _existing_lock(registry / ".registry.lock") as registry_lock:
            active_key = _derived_registry_tip(
                registry,
                project_identity=project_identity,
                expected_root_fingerprint=expected_root_fingerprint,
            )
            _key_record, public_key = _trusted_key_chain(
                registry,
                project_identity=project_identity,
                target_fingerprint=fingerprint,
                expected_root_fingerprint=expected_root_fingerprint,
            )
            if registry_lock is not None:
                registry_lock.validate_binding()
    except ProvenanceAnchorCryptoUnavailable:
        return _verification_result(
            AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE,
            anchor_id=anchor_id,
            anchored_entry_count=anchored_count,
            public_key_fingerprint=fingerprint,
            message_safe="Local Ed25519 verification support is unavailable.",
        )
    except Exception:
        return _verification_result(
            AnchorStatus.ANCHOR_UNKNOWN_KEY,
            anchor_id=anchor_id,
            anchored_entry_count=anchored_count,
            public_key_fingerprint=fingerprint,
            message_safe="Anchor signing key is not in the externally pinned trust chain.",
        )
    try:
        _verify_anchor_signature(record, public_key)
    except ProvenanceAnchorCryptoUnavailable:
        return _verification_result(
            AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE,
            anchor_id=anchor_id,
            anchored_entry_count=anchored_count,
            public_key_fingerprint=fingerprint,
            message_safe="Local Ed25519 verification support is unavailable.",
        )
    except Exception:
        return _verification_result(
            AnchorStatus.ANCHOR_SIGNATURE_INVALID,
            anchor_id=anchor_id,
            anchored_entry_count=anchored_count,
            public_key_fingerprint=fingerprint,
            message_safe="Anchor signature is invalid.",
        )

    actual_count: int | None = None
    try:
        with _existing_lock(_public_ledger_lock_path(ledger)) as ledger_lock:
            entries, full_verification, _current_schema = _ledger_snapshot_unlocked(
                ledger
            )
            if ledger_lock is not None:
                ledger_lock.validate_binding()
        actual_count = full_verification.entry_count
        if anchored_count > actual_count:
            raise ValueError("ledger is shorter than the signed checkpoint")
        prefix_verification = _verify_entries(entries[:anchored_count])
        if not prefix_verification.ok:
            raise ValueError("anchored ledger prefix is invalid")
        anchored_schema = (
            str(entries[anchored_count - 1]["schema_version"])
            if anchored_count
            else RUNTIME_PROVENANCE_SCHEMA_VERSION
        )
        if (
            prefix_verification.terminal_hash != record["latest_entry_hash"]
            or anchored_schema != record["provenance_schema_generation"]
        ):
            raise ValueError("signed anchor does not match the ledger prefix")
        is_current = (
            anchored_count == actual_count
            and record["latest_entry_hash"] == full_verification.terminal_hash
            and fingerprint == active_key["public_key_fingerprint"]
        )
    except Exception:
        return _verification_result(
            AnchorStatus.ANCHOR_LEDGER_MISMATCH,
            anchor_id=anchor_id,
            anchored_entry_count=anchored_count,
            actual_entry_count=actual_count,
            public_key_fingerprint=fingerprint,
            message_safe="Provenance ledger does not match the signed checkpoint.",
        )
    return _verification_result(
        AnchorStatus.ANCHOR_VALID,
        anchor_id=anchor_id,
        anchored_entry_count=anchored_count,
        actual_entry_count=actual_count,
        is_current=is_current,
        public_key_fingerprint=fingerprint,
        message_safe=(
            "Anchor is valid for the current ledger tip."
            if is_current
            else "Anchor is a valid historical ledger checkpoint."
        ),
    )


def verify_latest_provenance_anchor(
    ledger_path: Path,
    anchor_root: Path,
    public_key_registry: Path,
    *,
    expected_root_fingerprint: str,
    project_dir: Path,
) -> AnchorVerificationResult:
    """Verify the promoted latest pointer and require it to cover current truth."""

    try:
        project_identity = _project_identity(project_dir)
        ledger_identity = _ledger_identity(Path(ledger_path), project_identity)
        root = _safe_directory(Path(anchor_root), create=False)
        archives = _safe_directory(root / "anchors", create=False)
        registry = _safe_directory(Path(public_key_registry), create=False)
        with _existing_lock(registry / ".registry.lock") as registry_lock:
            active_key = _derived_registry_tip(
                registry,
                project_identity=project_identity,
                expected_root_fingerprint=expected_root_fingerprint,
            )
            with _existing_lock(root / ".anchor-create.lock") as anchor_lock:
                archive_chain = _validated_anchor_archive(
                    root,
                    registry,
                    project_identity=project_identity,
                    ledger_identity=ledger_identity,
                    expected_root_fingerprint=expected_root_fingerprint,
                )
                if not archive_chain:
                    raise ValueError("anchor archive is empty")
                archive_path, archive, archive_hash = archive_chain[-1]
                if archive["public_key_fingerprint"] != active_key[
                    "public_key_fingerprint"
                ]:
                    return _verification_result(
                        AnchorStatus.ANCHOR_UNKNOWN_KEY,
                        anchor_id=archive["anchor_id"],
                        anchored_entry_count=archive["entry_count"],
                        public_key_fingerprint=archive[
                            "public_key_fingerprint"
                        ],
                        message_safe=(
                            "Latest anchor was not signed by the active rotated key."
                        ),
                    )
                pointer_value = _read_record(
                    root / "latest_anchor.json", maximum_bytes=MAX_ANCHOR_BYTES
                )
                if pointer_value is None:
                    raise ValueError("latest anchor pointer is missing")
                pointer = _validate_latest_anchor_record(
                    pointer_value,
                    expected_project_identity=project_identity,
                    expected_ledger_identity=ledger_identity,
                )
                if (
                    pointer["anchor_id"] != archive["anchor_id"]
                    or pointer["anchor_sequence"] != archive["anchor_sequence"]
                    or pointer["anchor_hash"] != archive_hash
                    or pointer["anchor_filename"] != archive_path.name
                    or pointer["entry_count"] != archive["entry_count"]
                    or pointer["latest_entry_hash"]
                    != archive["latest_entry_hash"]
                ):
                    return _verification_result(
                        AnchorStatus.ANCHOR_LEDGER_MISMATCH,
                        anchor_id=pointer["anchor_id"],
                        anchored_entry_count=pointer["entry_count"],
                        public_key_fingerprint=archive[
                            "public_key_fingerprint"
                        ],
                        message_safe=(
                            "Latest anchor pointer is stale or rolled back from "
                            "the signed archive-chain tip."
                        ),
                    )
                if anchor_lock is not None:
                    anchor_lock.validate_binding()
            if registry_lock is not None:
                registry_lock.validate_binding()
    except ProvenanceAnchorCryptoUnavailable:
        return _verification_result(
            AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE,
            message_safe="Local Ed25519 verification support is unavailable.",
        )
    except _AnchorSignatureInvalid:
        return _verification_result(
            AnchorStatus.ANCHOR_SIGNATURE_INVALID,
            message_safe="Latest archived anchor signature is invalid.",
        )
    except KeyError:
        return _verification_result(
            AnchorStatus.ANCHOR_UNKNOWN_KEY,
            message_safe="Latest anchor key is not in the externally pinned trust chain.",
        )
    except Exception:
        return _verification_result(
            AnchorStatus.ANCHOR_SCHEMA_UNSUPPORTED,
            message_safe="Latest anchor pointer is missing, malformed, or unsupported.",
        )
    result = verify_provenance_anchor(
        Path(ledger_path),
        archive_path,
        Path(public_key_registry),
        expected_root_fingerprint=expected_root_fingerprint,
        project_dir=project_dir,
    )
    if not result.valid:
        return result
    try:
        if (
            archive["anchor_id"] != pointer["anchor_id"]
            or archive["anchor_sequence"] != pointer["anchor_sequence"]
            or _anchor_hash(archive) != pointer["anchor_hash"]
            or archive["entry_count"] != pointer["entry_count"]
            or archive["latest_entry_hash"] != pointer["latest_entry_hash"]
            or not result.is_current
        ):
            raise ValueError("latest pointer is stale or conflicts with archive")
    except Exception:
        return _verification_result(
            AnchorStatus.ANCHOR_LEDGER_MISMATCH,
            anchor_id=result.anchor_id,
            anchored_entry_count=result.anchored_entry_count,
            actual_entry_count=result.actual_entry_count,
            public_key_fingerprint=result.public_key_fingerprint,
            message_safe="Latest anchor pointer does not cover the current ledger tip.",
        )
    return result


__all__ = [
    "ANCHOR_SCHEMA_VERSION",
    "LATEST_ANCHOR_SCHEMA_VERSION",
    "LATEST_KEY_SCHEMA_VERSION",
    "PUBLIC_KEY_SCHEMA_VERSION",
    "ROTATION_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "TRUST_ROOT_SCHEMA_VERSION",
    "AnchorCreationResult",
    "AnchorStatus",
    "AnchorVerificationResult",
    "ProvenanceAnchorConfigurationError",
    "ProvenanceAnchorCryptoUnavailable",
    "ProvenanceAnchorError",
    "create_provenance_anchor",
    "provision_external_signing_key",
    "register_initial_verification_key",
    "rotate_verification_key",
    "verify_latest_provenance_anchor",
    "verify_provenance_anchor",
]
