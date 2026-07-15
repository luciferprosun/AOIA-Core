from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CORPUS_SCHEMA_VERSION = "unix-corpus-ingestion-1a"
RECORD_SCHEMA_VERSION = "unix-corpus-record-1a"
SOURCE_SCHEMA_VERSION = "unix-corpus-source-1a"
QUARANTINE_SCHEMA_VERSION = "unix-corpus-quarantine-1a"
MANIFEST_FILENAME = "corpus_manifest.json"
RECORDS_DIRECTORY = "records"
QUARANTINE_DIRECTORY = "quarantine"
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()

SUPPORTED_MEDIA_TYPES = {
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".md": "text/markdown",
    ".txt": "text/plain",
}

AUTHORITY_FLAGS = {
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
    "gate_satisfied": False,
}


class UnixCorpusIngestionError(ValueError):
    """Deterministic, fail-closed corpus intake error."""


class UnixCorpusSecurityError(UnixCorpusIngestionError):
    """A path or filesystem boundary is unsafe for corpus intake."""


class UnixCorpusStoreError(UnixCorpusIngestionError):
    """Existing intake output is malformed, tampered, or inconsistent."""


@dataclass(frozen=True, slots=True)
class UnixCorpusIngestionLimits:
    max_sources: int = 4096
    max_source_bytes: int = 8 * 1024 * 1024
    max_line_bytes: int = 256 * 1024
    max_record_chars: int = 64 * 1024
    max_records: int = 100_000

    def __post_init__(self) -> None:
        for name in (
            "max_sources",
            "max_source_bytes",
            "max_line_bytes",
            "max_record_chars",
            "max_records",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise UnixCorpusIngestionError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class UnixCorpusRecord:
    record_id: str
    source_id: str
    source_path: str
    source_hash: str
    content_hash: str
    media_type: str
    locator: str
    ordinal: int
    content: str
    authority_status: str = field(default=NON_AUTHORITATIVE, init=False)
    schema_version: str = field(default=RECORD_SCHEMA_VERSION, init=False)
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "media_type": self.media_type,
            "locator": self.locator,
            "ordinal": self.ordinal,
            "content": self.content,
            "authority_status": self.authority_status,
            **AUTHORITY_FLAGS,
        }


@dataclass(frozen=True, slots=True)
class UnixCorpusQuarantineEntry:
    quarantine_id: str
    source_path: str
    source_hash: str | None
    size_bytes: int | None
    reason_code: str
    reason: str
    authority_status: str = field(default=NON_AUTHORITATIVE, init=False)
    schema_version: str = field(default=QUARANTINE_SCHEMA_VERSION, init=False)
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "quarantine_id": self.quarantine_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "size_bytes": self.size_bytes,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "authority_status": self.authority_status,
            **AUTHORITY_FLAGS,
        }


@dataclass(frozen=True, slots=True)
class UnixCorpusSourceEntry:
    source_id: str
    source_path: str
    source_hash: str | None
    size_bytes: int | None
    media_type: str | None
    status: str
    record_ids: tuple[str, ...]
    quarantine_id: str | None
    authority_status: str = field(default=NON_AUTHORITATIVE, init=False)
    schema_version: str = field(default=SOURCE_SCHEMA_VERSION, init=False)
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "status": self.status,
            "record_ids": list(self.record_ids),
            "quarantine_id": self.quarantine_id,
            "authority_status": self.authority_status,
            **AUTHORITY_FLAGS,
        }


@dataclass(frozen=True, slots=True)
class UnixCorpusManifest:
    corpus_id: str
    manifest_hash: str
    source_count: int
    accepted_source_count: int
    quarantined_source_count: int
    record_count: int
    sources: tuple[UnixCorpusSourceEntry, ...]
    record_ids: tuple[str, ...]
    quarantine_ids: tuple[str, ...]
    authority_status: str = field(default=NON_AUTHORITATIVE, init=False)
    schema_version: str = field(default=CORPUS_SCHEMA_VERSION, init=False)
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "corpus_id": self.corpus_id,
            "manifest_hash": self.manifest_hash,
            "source_count": self.source_count,
            "accepted_source_count": self.accepted_source_count,
            "quarantined_source_count": self.quarantined_source_count,
            "record_count": self.record_count,
            "sources": [source.to_dict() for source in self.sources],
            "record_ids": list(self.record_ids),
            "quarantine_ids": list(self.quarantine_ids),
            "authority_status": self.authority_status,
            **AUTHORITY_FLAGS,
        }


@dataclass(frozen=True, slots=True)
class UnixCorpusIngestionResult:
    status: str
    manifest: UnixCorpusManifest
    created_record_count: int
    existing_record_count: int
    created_quarantine_count: int
    existing_quarantine_count: int
    manifest_changed: bool
    authority_status: str = field(default=NON_AUTHORITATIVE, init=False)
    can_execute: bool = field(default=False, init=False)
    can_write: bool = field(default=False, init=False)
    can_dispatch: bool = field(default=False, init=False)
    can_approve: bool = field(default=False, init=False)
    gate_satisfied: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "manifest": self.manifest.to_dict(),
            "created_record_count": self.created_record_count,
            "existing_record_count": self.existing_record_count,
            "created_quarantine_count": self.created_quarantine_count,
            "existing_quarantine_count": self.existing_quarantine_count,
            "manifest_changed": self.manifest_changed,
            "authority_status": self.authority_status,
            **AUTHORITY_FLAGS,
        }


@dataclass(frozen=True, slots=True)
class _SourceCandidate:
    relative_path: str
    path: Path
    symlink: bool


class _QuarantineSource(Exception):
    def __init__(self, reason_code: str, reason: str) -> None:
        super().__init__(reason)
        self.reason_code = reason_code
        self.reason = reason


def reconcile_unix_corpus(
    source_root: str | Path,
    intake_root: str | Path,
    *,
    source_paths: Sequence[str] | None = None,
    limits: UnixCorpusIngestionLimits | None = None,
) -> UnixCorpusIngestionResult:
    """Deterministically ingest local UNIX corpus files into an inert store.

    This explicit caller action reads only local files. It never imports,
    evaluates, executes, dispatches, or interprets commands found in content.
    """

    active_limits = UnixCorpusIngestionLimits() if limits is None else limits
    if not isinstance(active_limits, UnixCorpusIngestionLimits):
        raise UnixCorpusIngestionError("limits must be UnixCorpusIngestionLimits")

    source_directory = _validated_source_root(source_root)
    output_directory = _validated_output_root(intake_root, source_directory)
    candidates = _discover_candidates(
        source_directory,
        source_paths=source_paths,
        max_sources=active_limits.max_sources,
    )

    source_entries: list[UnixCorpusSourceEntry] = []
    records: list[UnixCorpusRecord] = []
    quarantine_entries: list[UnixCorpusQuarantineEntry] = []

    for candidate in candidates:
        source_entry, candidate_records, quarantine = _ingest_candidate(
            candidate,
            active_limits,
        )
        source_entries.append(source_entry)
        records.extend(candidate_records)
        if quarantine is not None:
            quarantine_entries.append(quarantine)
        if len(records) > active_limits.max_records:
            raise UnixCorpusIngestionError("corpus record hard limit exceeded")

    ordered_sources = tuple(sorted(source_entries, key=lambda item: item.source_path))
    ordered_records = tuple(sorted(records, key=lambda item: item.record_id))
    ordered_quarantine = tuple(
        sorted(quarantine_entries, key=lambda item: item.quarantine_id)
    )
    manifest = _build_manifest(
        ordered_sources,
        ordered_records,
        ordered_quarantine,
    )

    existing_manifest_bytes = _verify_existing_store(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    records_directory = output_directory / RECORDS_DIRECTORY
    quarantine_directory = output_directory / QUARANTINE_DIRECTORY
    records_directory.mkdir(exist_ok=True)
    quarantine_directory.mkdir(exist_ok=True)
    _assert_safe_output_directory(output_directory, records_directory)
    _assert_safe_output_directory(output_directory, quarantine_directory)

    created_records = 0
    existing_records = 0
    for record in ordered_records:
        created = _write_canonical_once(
            records_directory / f"{record.record_id}.json",
            record.to_dict(),
        )
        created_records += int(created)
        existing_records += int(not created)

    created_quarantine = 0
    existing_quarantine = 0
    for quarantine in ordered_quarantine:
        created = _write_canonical_once(
            quarantine_directory / f"{quarantine.quarantine_id}.json",
            quarantine.to_dict(),
        )
        created_quarantine += int(created)
        existing_quarantine += int(not created)

    manifest_bytes = _canonical_line(manifest.to_dict())
    manifest_changed = existing_manifest_bytes != manifest_bytes
    if manifest_changed:
        _write_manifest_atomic(
            output_directory / MANIFEST_FILENAME,
            manifest_bytes,
        )

    if existing_manifest_bytes is None:
        status = "CREATED"
    elif manifest_changed or created_records or created_quarantine:
        status = "UPDATED"
    else:
        status = "UNCHANGED"
    return UnixCorpusIngestionResult(
        status=status,
        manifest=manifest,
        created_record_count=created_records,
        existing_record_count=existing_records,
        created_quarantine_count=created_quarantine,
        existing_quarantine_count=existing_quarantine,
        manifest_changed=manifest_changed,
    )


def read_unix_corpus_manifest(intake_root: str | Path) -> UnixCorpusManifest:
    root = _path_value("intake_root", intake_root)
    if root.is_symlink() or not root.is_dir():
        raise UnixCorpusStoreError("intake root must be an existing non-symlink directory")
    _verify_existing_store(root)
    payload, _raw = _read_canonical_object(root / MANIFEST_FILENAME)
    return _manifest_from_payload(payload)


def _validated_source_root(value: str | Path) -> Path:
    path = _path_value("source_root", value)
    _assert_no_symlink_components(path)
    if path.is_symlink():
        raise UnixCorpusSecurityError("source root must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise UnixCorpusSecurityError("source root does not exist") from exc
    if not resolved.is_dir():
        raise UnixCorpusSecurityError("source root must be a directory")
    return resolved


def _validated_output_root(value: str | Path, source_root: Path) -> Path:
    path = _path_value("intake_root", value)
    _assert_no_symlink_components(path)
    resolved = path.resolve(strict=False)
    if resolved == source_root or source_root in resolved.parents:
        raise UnixCorpusSecurityError("intake root must be outside the source root")
    if resolved.exists() and not resolved.is_dir():
        raise UnixCorpusSecurityError("intake root must be a directory")
    return resolved


def _path_value(name: str, value: str | Path) -> Path:
    if isinstance(value, bool) or not isinstance(value, (str, Path)):
        raise TypeError(f"{name} must be a path")
    path = Path(value)
    if not str(path):
        raise UnixCorpusSecurityError(f"{name} must not be empty")
    return path


def _assert_no_symlink_components(path: Path) -> None:
    current = path if path.is_absolute() else Path.cwd() / path
    for candidate in (current, *current.parents):
        if candidate.exists() and candidate.is_symlink():
            raise UnixCorpusSecurityError("intake path contains a symbolic link")


def _discover_candidates(
    source_root: Path,
    *,
    source_paths: Sequence[str] | None,
    max_sources: int,
) -> tuple[_SourceCandidate, ...]:
    if source_paths is not None:
        if isinstance(source_paths, (str, bytes)):
            raise TypeError("source_paths must be a sequence of relative paths")
        normalized = tuple(_validated_relative_path(item) for item in source_paths)
        if len(normalized) != len(set(normalized)):
            raise UnixCorpusIngestionError("duplicate source paths are forbidden")
        candidates = tuple(
            _explicit_candidate(source_root, relative)
            for relative in sorted(normalized)
        )
    else:
        discovered: list[_SourceCandidate] = []
        for directory, directory_names, file_names in os.walk(
            source_root,
            topdown=True,
            followlinks=False,
        ):
            directory_path = Path(directory)
            retained_directories: list[str] = []
            for name in sorted(directory_names):
                child = directory_path / name
                if child.is_symlink():
                    discovered.append(
                        _SourceCandidate(
                            relative_path=child.relative_to(source_root).as_posix(),
                            path=child,
                            symlink=True,
                        )
                    )
                else:
                    retained_directories.append(name)
            directory_names[:] = retained_directories
            for name in sorted(file_names):
                child = directory_path / name
                discovered.append(
                    _SourceCandidate(
                        relative_path=child.relative_to(source_root).as_posix(),
                        path=child,
                        symlink=child.is_symlink(),
                    )
                )
        candidates = tuple(sorted(discovered, key=lambda item: item.relative_path))

    if len(candidates) > max_sources:
        raise UnixCorpusIngestionError("corpus source hard limit exceeded")
    return candidates


def _validated_relative_path(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("source path must be text")
    relative = Path(value)
    if (
        not value
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise UnixCorpusSecurityError("source path must be a normalized relative path")
    return relative.as_posix()


def _explicit_candidate(source_root: Path, relative: str) -> _SourceCandidate:
    path = source_root / relative
    current = source_root
    contains_symlink = False
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            contains_symlink = True
            break
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise UnixCorpusSecurityError(f"source path parent does not exist: {relative}") from exc
    if parent != source_root and source_root not in parent.parents:
        raise UnixCorpusSecurityError("source path escapes source root")
    if not path.exists() and not path.is_symlink():
        raise UnixCorpusSecurityError(f"source path does not exist: {relative}")
    return _SourceCandidate(relative, path, contains_symlink or path.is_symlink())


def _ingest_candidate(
    candidate: _SourceCandidate,
    limits: UnixCorpusIngestionLimits,
) -> tuple[
    UnixCorpusSourceEntry,
    tuple[UnixCorpusRecord, ...],
    UnixCorpusQuarantineEntry | None,
]:
    source_hash: str | None = None
    size_bytes: int | None = None
    media_type = SUPPORTED_MEDIA_TYPES.get(candidate.path.suffix.casefold())
    try:
        if candidate.symlink:
            raise _QuarantineSource(
                "SYMLINK_REJECTED",
                "symbolic links are not followed during corpus intake",
            )
        file_stat = candidate.path.stat(follow_symlinks=False)
        if not stat.S_ISREG(file_stat.st_mode):
            raise _QuarantineSource(
                "NOT_REGULAR_FILE",
                "corpus source is not a regular file",
            )
        size_bytes = file_stat.st_size
        source_hash, observed_size = _hash_file(candidate.path)
        final_stat = candidate.path.stat(follow_symlinks=False)
        if (
            observed_size != size_bytes
            or final_stat.st_dev != file_stat.st_dev
            or final_stat.st_ino != file_stat.st_ino
            or final_stat.st_size != file_stat.st_size
            or final_stat.st_mtime_ns != file_stat.st_mtime_ns
        ):
            raise _QuarantineSource(
                "SOURCE_CHANGED_DURING_READ",
                "corpus source changed while its hash was calculated",
            )
        if size_bytes > limits.max_source_bytes:
            raise _QuarantineSource(
                "SOURCE_SIZE_LIMIT_EXCEEDED",
                "corpus source exceeds the configured byte limit",
            )
        if media_type is None:
            raise _QuarantineSource(
                "UNSUPPORTED_MEDIA_TYPE",
                "only .txt, .md, .json, and .jsonl sources are supported",
            )

        source_id = _source_id(candidate.relative_path, source_hash)
        if media_type in {"text/plain", "text/markdown"}:
            records = _text_records(
                candidate.path,
                candidate.relative_path,
                source_id,
                source_hash,
                media_type,
                limits,
            )
        elif media_type == "application/json":
            records = _json_records(
                candidate.path,
                candidate.relative_path,
                source_id,
                source_hash,
            )
        else:
            records = _jsonl_records(
                candidate.path,
                candidate.relative_path,
                source_id,
                source_hash,
                limits,
            )
        if not records:
            raise _QuarantineSource(
                "NO_INGESTIBLE_CONTENT",
                "corpus source contains no ingestible content",
            )
        source = UnixCorpusSourceEntry(
            source_id=source_id,
            source_path=candidate.relative_path,
            source_hash=source_hash,
            size_bytes=size_bytes,
            media_type=media_type,
            status="ACCEPTED",
            record_ids=tuple(record.record_id for record in records),
            quarantine_id=None,
        )
        return source, records, None
    except UnicodeDecodeError:
        quarantine_reason = _QuarantineSource(
            "INVALID_UTF8",
            "corpus source is not valid UTF-8",
        )
    except (json.JSONDecodeError, _DuplicateJsonKeyError):
        quarantine_reason = _QuarantineSource(
            "MALFORMED_JSON",
            "corpus JSON is malformed or contains duplicate keys",
        )
    except _QuarantineSource as exc:
        quarantine_reason = exc

    quarantine = _quarantine_entry(
        candidate.relative_path,
        source_hash,
        size_bytes,
        quarantine_reason.reason_code,
        quarantine_reason.reason,
    )
    source = UnixCorpusSourceEntry(
        source_id=_source_id(candidate.relative_path, source_hash or EMPTY_SHA256),
        source_path=candidate.relative_path,
        source_hash=source_hash,
        size_bytes=size_bytes,
        media_type=media_type,
        status="QUARANTINED",
        record_ids=(),
        quarantine_id=quarantine.quarantine_id,
    )
    return source, (), quarantine


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _text_records(
    path: Path,
    source_path: str,
    source_id: str,
    source_hash: str,
    media_type: str,
    limits: UnixCorpusIngestionLimits,
) -> tuple[UnixCorpusRecord, ...]:
    records: list[UnixCorpusRecord] = []
    lines: list[str] = []
    start_line = 1
    current_line = 0
    current_chars = 0
    heading = ""
    chunk_heading = ""

    def flush(end_line: int) -> None:
        nonlocal lines, current_chars, start_line, chunk_heading
        content = "\n".join(lines).strip("\n")
        if content.strip():
            locator = f"lines:{start_line}-{end_line}"
            if chunk_heading:
                locator += f";heading:{_slug(chunk_heading)}"
            records.append(
                _record(
                    source_id=source_id,
                    source_path=source_path,
                    source_hash=source_hash,
                    media_type=media_type,
                    locator=locator,
                    ordinal=len(records) + 1,
                    content=content,
                )
            )
        lines = []
        current_chars = 0
        start_line = end_line + 1
        chunk_heading = heading

    with path.open("rb") as stream:
        while True:
            raw_line = stream.readline(limits.max_line_bytes + 1)
            if not raw_line:
                break
            current_line += 1
            if len(raw_line) > limits.max_line_bytes:
                raise _QuarantineSource(
                    "LINE_SIZE_LIMIT_EXCEEDED",
                    "corpus source contains a line above the configured byte limit",
                )
            line = raw_line.decode("utf-8", errors="strict").rstrip("\r\n")
            if media_type == "text/markdown" and line.lstrip().startswith("#"):
                possible_heading = line.lstrip("#").strip()
                if possible_heading:
                    if lines:
                        flush(current_line - 1)
                        start_line = current_line
                    heading = possible_heading
                    chunk_heading = heading
            added_chars = len(line) + (1 if lines else 0)
            if lines and current_chars + added_chars > limits.max_record_chars:
                flush(current_line - 1)
                start_line = current_line
                added_chars = len(line)
            if len(line) > limits.max_record_chars:
                raise _QuarantineSource(
                    "RECORD_SIZE_LIMIT_EXCEEDED",
                    "corpus line cannot fit inside the configured record limit",
                )
            lines.append(line)
            current_chars += added_chars
        if lines:
            flush(current_line)
    return tuple(records)


def _json_records(
    path: Path,
    source_path: str,
    source_id: str,
    source_hash: str,
) -> tuple[UnixCorpusRecord, ...]:
    payload = _strict_json_loads(path.read_text(encoding="utf-8", errors="strict"))
    if isinstance(payload, Mapping):
        values = (("$", payload),)
    elif isinstance(payload, list):
        values = tuple((f"$[{index}]", item) for index, item in enumerate(payload))
    else:
        raise _QuarantineSource(
            "JSON_TOP_LEVEL_INVALID",
            "JSON corpus source must contain an object or array",
        )
    records = []
    for ordinal, (locator, value) in enumerate(values, start=1):
        _validate_json_value(value)
        records.append(
            _record(
                source_id=source_id,
                source_path=source_path,
                source_hash=source_hash,
                media_type="application/json",
                locator=locator,
                ordinal=ordinal,
                content=_canonical_json(value),
            )
        )
    return tuple(records)


def _jsonl_records(
    path: Path,
    source_path: str,
    source_id: str,
    source_hash: str,
    limits: UnixCorpusIngestionLimits,
) -> tuple[UnixCorpusRecord, ...]:
    records: list[UnixCorpusRecord] = []
    with path.open("rb") as stream:
        line_number = 0
        while True:
            raw_line = stream.readline(limits.max_line_bytes + 1)
            if not raw_line:
                break
            line_number += 1
            if len(raw_line) > limits.max_line_bytes:
                raise _QuarantineSource(
                    "LINE_SIZE_LIMIT_EXCEEDED",
                    "JSONL source contains a line above the configured byte limit",
                )
            text = raw_line.decode("utf-8", errors="strict").strip()
            if not text:
                raise _QuarantineSource(
                    "BLANK_JSONL_LINE",
                    "JSONL corpus sources must not contain blank lines",
                )
            value = _strict_json_loads(text)
            if not isinstance(value, Mapping):
                raise _QuarantineSource(
                    "JSONL_RECORD_INVALID",
                    "each JSONL corpus record must be an object",
                )
            _validate_json_value(value)
            records.append(
                _record(
                    source_id=source_id,
                    source_path=source_path,
                    source_hash=source_hash,
                    media_type="application/x-ndjson",
                    locator=f"line:{line_number}",
                    ordinal=line_number,
                    content=_canonical_json(value),
                )
            )
    return tuple(records)


def _record(
    *,
    source_id: str,
    source_path: str,
    source_hash: str,
    media_type: str,
    locator: str,
    ordinal: int,
    content: str,
) -> UnixCorpusRecord:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    material = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "source_id": source_id,
        "source_path": source_path,
        "source_hash": source_hash,
        "content_hash": content_hash,
        "media_type": media_type,
        "locator": locator,
        "ordinal": ordinal,
        "content": content,
        "authority_status": NON_AUTHORITATIVE,
        **AUTHORITY_FLAGS,
    }
    record_id = hashlib.sha256(_canonical_bytes(material)).hexdigest()
    return UnixCorpusRecord(
        record_id=record_id,
        source_id=source_id,
        source_path=source_path,
        source_hash=source_hash,
        content_hash=content_hash,
        media_type=media_type,
        locator=locator,
        ordinal=ordinal,
        content=content,
    )


def _source_id(source_path: str, source_hash: str) -> str:
    digest = hashlib.sha256(
        _canonical_bytes({"source_path": source_path, "source_hash": source_hash})
    ).hexdigest()
    return f"unix-source-{digest[:24]}"


def _quarantine_entry(
    source_path: str,
    source_hash: str | None,
    size_bytes: int | None,
    reason_code: str,
    reason: str,
) -> UnixCorpusQuarantineEntry:
    material = {
        "schema_version": QUARANTINE_SCHEMA_VERSION,
        "source_path": source_path,
        "source_hash": source_hash,
        "size_bytes": size_bytes,
        "reason_code": reason_code,
        "reason": reason,
        "authority_status": NON_AUTHORITATIVE,
        **AUTHORITY_FLAGS,
    }
    quarantine_id = hashlib.sha256(_canonical_bytes(material)).hexdigest()
    return UnixCorpusQuarantineEntry(
        quarantine_id=quarantine_id,
        source_path=source_path,
        source_hash=source_hash,
        size_bytes=size_bytes,
        reason_code=reason_code,
        reason=reason,
    )


def _build_manifest(
    sources: tuple[UnixCorpusSourceEntry, ...],
    records: tuple[UnixCorpusRecord, ...],
    quarantine: tuple[UnixCorpusQuarantineEntry, ...],
) -> UnixCorpusManifest:
    record_ids = tuple(record.record_id for record in records)
    quarantine_ids = tuple(item.quarantine_id for item in quarantine)
    accepted_count = sum(source.status == "ACCEPTED" for source in sources)
    quarantined_count = sum(source.status == "QUARANTINED" for source in sources)
    semantic = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "source_count": len(sources),
        "accepted_source_count": accepted_count,
        "quarantined_source_count": quarantined_count,
        "record_count": len(records),
        "sources": [source.to_dict() for source in sources],
        "record_ids": list(record_ids),
        "quarantine_ids": list(quarantine_ids),
        "authority_status": NON_AUTHORITATIVE,
        **AUTHORITY_FLAGS,
    }
    corpus_digest = hashlib.sha256(_canonical_bytes(semantic)).hexdigest()
    corpus_id = f"unix-corpus-{corpus_digest[:24]}"
    hash_material = {**semantic, "corpus_id": corpus_id}
    manifest_hash = hashlib.sha256(_canonical_bytes(hash_material)).hexdigest()
    return UnixCorpusManifest(
        corpus_id=corpus_id,
        manifest_hash=manifest_hash,
        source_count=len(sources),
        accepted_source_count=accepted_count,
        quarantined_source_count=quarantined_count,
        record_count=len(records),
        sources=sources,
        record_ids=record_ids,
        quarantine_ids=quarantine_ids,
    )


def _verify_existing_store(output_root: Path) -> bytes | None:
    if not output_root.exists():
        return None
    _assert_safe_output_directory(output_root, output_root)
    allowed_entries = {MANIFEST_FILENAME, RECORDS_DIRECTORY, QUARANTINE_DIRECTORY}
    unexpected = sorted(path.name for path in output_root.iterdir() if path.name not in allowed_entries)
    if unexpected:
        raise UnixCorpusStoreError(
            f"intake root contains unexpected entries: {', '.join(unexpected)}"
        )

    record_ids = _verify_object_directory(
        output_root,
        RECORDS_DIRECTORY,
        expected_schema=RECORD_SCHEMA_VERSION,
        id_field="record_id",
    )
    quarantine_ids = _verify_object_directory(
        output_root,
        QUARANTINE_DIRECTORY,
        expected_schema=QUARANTINE_SCHEMA_VERSION,
        id_field="quarantine_id",
    )
    manifest_path = output_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        if record_ids or quarantine_ids:
            return None
        return None
    payload, raw = _read_canonical_object(manifest_path)
    manifest = _manifest_from_payload(payload)
    if not set(manifest.record_ids).issubset(record_ids):
        raise UnixCorpusStoreError("manifest references missing corpus records")
    if not set(manifest.quarantine_ids).issubset(quarantine_ids):
        raise UnixCorpusStoreError("manifest references missing quarantine records")
    return raw


def _verify_object_directory(
    output_root: Path,
    directory_name: str,
    *,
    expected_schema: str,
    id_field: str,
) -> set[str]:
    directory = output_root / directory_name
    if not directory.exists():
        return set()
    _assert_safe_output_directory(output_root, directory)
    identifiers: set[str] = set()
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise UnixCorpusStoreError(f"invalid object-store entry: {path.name}")
        payload, _raw = _read_canonical_object(path)
        if payload.get("schema_version") != expected_schema:
            raise UnixCorpusStoreError(f"unexpected object schema in {path.name}")
        identifier = payload.get(id_field)
        if not _is_sha256(identifier) or path.name != f"{identifier}.json":
            raise UnixCorpusStoreError(f"object identifier mismatch in {path.name}")
        _assert_inert_payload(payload)
        if expected_schema == RECORD_SCHEMA_VERSION:
            _verify_record_payload(payload)
        elif expected_schema == QUARANTINE_SCHEMA_VERSION:
            _verify_quarantine_payload(payload)
        identifiers.add(identifier)
    return identifiers


def _verify_record_payload(payload: Mapping[str, Any]) -> None:
    expected_fields = {
        "schema_version",
        "record_id",
        "source_id",
        "source_path",
        "source_hash",
        "content_hash",
        "media_type",
        "locator",
        "ordinal",
        "content",
        "authority_status",
        *AUTHORITY_FLAGS,
    }
    if set(payload) != expected_fields:
        raise UnixCorpusStoreError("corpus record has an invalid field set")
    if not isinstance(payload.get("content"), str):
        raise UnixCorpusStoreError("corpus record content must be text")
    content_hash = hashlib.sha256(payload["content"].encode("utf-8")).hexdigest()
    if payload.get("content_hash") != content_hash:
        raise UnixCorpusStoreError("corpus record content hash mismatch")
    if not _is_sha256(payload.get("source_hash")):
        raise UnixCorpusStoreError("corpus record source hash is invalid")
    _validated_relative_path(payload.get("source_path"))
    if payload.get("media_type") not in SUPPORTED_MEDIA_TYPES.values():
        raise UnixCorpusStoreError("corpus record media type is invalid")
    if not isinstance(payload.get("locator"), str) or not payload["locator"]:
        raise UnixCorpusStoreError("corpus record locator is invalid")
    if type(payload.get("ordinal")) is not int or payload["ordinal"] <= 0:
        raise UnixCorpusStoreError("corpus record ordinal is invalid")
    material = dict(payload)
    recorded_id = material.pop("record_id")
    expected_id = hashlib.sha256(_canonical_bytes(material)).hexdigest()
    if recorded_id != expected_id:
        raise UnixCorpusStoreError("corpus record identifier mismatch")


def _verify_quarantine_payload(payload: Mapping[str, Any]) -> None:
    expected_fields = {
        "schema_version",
        "quarantine_id",
        "source_path",
        "source_hash",
        "size_bytes",
        "reason_code",
        "reason",
        "authority_status",
        *AUTHORITY_FLAGS,
    }
    if set(payload) != expected_fields:
        raise UnixCorpusStoreError("quarantine record has an invalid field set")
    _validated_relative_path(payload.get("source_path"))
    source_hash = payload.get("source_hash")
    if source_hash is not None and not _is_sha256(source_hash):
        raise UnixCorpusStoreError("quarantine source hash is invalid")
    size_bytes = payload.get("size_bytes")
    if size_bytes is not None and (type(size_bytes) is not int or size_bytes < 0):
        raise UnixCorpusStoreError("quarantine source size is invalid")
    for field_name in ("reason_code", "reason"):
        if not isinstance(payload.get(field_name), str) or not payload[field_name]:
            raise UnixCorpusStoreError(f"quarantine {field_name} is invalid")
    material = dict(payload)
    recorded_id = material.pop("quarantine_id")
    expected_id = hashlib.sha256(_canonical_bytes(material)).hexdigest()
    if recorded_id != expected_id:
        raise UnixCorpusStoreError("quarantine identifier mismatch")


def _manifest_from_payload(payload: Mapping[str, Any]) -> UnixCorpusManifest:
    expected_fields = {
        "schema_version",
        "corpus_id",
        "manifest_hash",
        "source_count",
        "accepted_source_count",
        "quarantined_source_count",
        "record_count",
        "sources",
        "record_ids",
        "quarantine_ids",
        "authority_status",
        *AUTHORITY_FLAGS,
    }
    if set(payload) != expected_fields:
        raise UnixCorpusStoreError("corpus manifest has an invalid field set")
    _assert_inert_payload(payload)
    if payload.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise UnixCorpusStoreError("corpus manifest schema version is invalid")
    if not isinstance(payload.get("corpus_id"), str) or not payload["corpus_id"].startswith("unix-corpus-"):
        raise UnixCorpusStoreError("corpus manifest identifier is invalid")
    manifest_hash = payload.get("manifest_hash")
    if not _is_sha256(manifest_hash):
        raise UnixCorpusStoreError("corpus manifest hash is invalid")
    hash_material = dict(payload)
    hash_material.pop("manifest_hash")
    expected_hash = hashlib.sha256(_canonical_bytes(hash_material)).hexdigest()
    if manifest_hash != expected_hash:
        raise UnixCorpusStoreError("corpus manifest hash mismatch")

    sources_payload = payload.get("sources")
    if not isinstance(sources_payload, list):
        raise UnixCorpusStoreError("corpus manifest sources must be a list")
    sources = tuple(_source_from_payload(item) for item in sources_payload)
    if tuple(source.source_path for source in sources) != tuple(
        sorted(source.source_path for source in sources)
    ):
        raise UnixCorpusStoreError("manifest sources must be sorted by path")
    record_ids = _hash_list(payload.get("record_ids"), "record_ids")
    quarantine_ids = _hash_list(payload.get("quarantine_ids"), "quarantine_ids")
    if tuple(sorted(record_ids)) != record_ids or tuple(sorted(quarantine_ids)) != quarantine_ids:
        raise UnixCorpusStoreError("manifest identifiers must be sorted")
    counts = (
        ("source_count", len(sources)),
        ("accepted_source_count", sum(item.status == "ACCEPTED" for item in sources)),
        ("quarantined_source_count", sum(item.status == "QUARANTINED" for item in sources)),
        ("record_count", len(record_ids)),
    )
    for field_name, expected in counts:
        if type(payload.get(field_name)) is not int or payload[field_name] != expected:
            raise UnixCorpusStoreError(f"manifest {field_name} is inconsistent")
    bound_record_ids = tuple(
        sorted(record_id for source in sources for record_id in source.record_ids)
    )
    bound_quarantine_ids = tuple(
        sorted(
            source.quarantine_id
            for source in sources
            if source.quarantine_id is not None
        )
    )
    if bound_record_ids != record_ids or bound_quarantine_ids != quarantine_ids:
        raise UnixCorpusStoreError("manifest source bindings are inconsistent")
    semantic = dict(payload)
    semantic.pop("manifest_hash")
    recorded_corpus_id = semantic.pop("corpus_id")
    expected_corpus_id = "unix-corpus-" + hashlib.sha256(
        _canonical_bytes(semantic)
    ).hexdigest()[:24]
    if recorded_corpus_id != expected_corpus_id:
        raise UnixCorpusStoreError("corpus identifier is not deterministic")
    return UnixCorpusManifest(
        corpus_id=payload["corpus_id"],
        manifest_hash=manifest_hash,
        source_count=payload["source_count"],
        accepted_source_count=payload["accepted_source_count"],
        quarantined_source_count=payload["quarantined_source_count"],
        record_count=payload["record_count"],
        sources=sources,
        record_ids=record_ids,
        quarantine_ids=quarantine_ids,
    )


def _source_from_payload(payload: Any) -> UnixCorpusSourceEntry:
    if not isinstance(payload, Mapping):
        raise UnixCorpusStoreError("manifest source entry must be an object")
    expected_fields = {
        "schema_version",
        "source_id",
        "source_path",
        "source_hash",
        "size_bytes",
        "media_type",
        "status",
        "record_ids",
        "quarantine_id",
        "authority_status",
        *AUTHORITY_FLAGS,
    }
    if set(payload) != expected_fields or payload.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise UnixCorpusStoreError("manifest source entry has an invalid schema")
    _assert_inert_payload(payload)
    source_path = payload.get("source_path")
    _validated_relative_path(source_path)
    source_hash = payload.get("source_hash")
    if source_hash is not None and not _is_sha256(source_hash):
        raise UnixCorpusStoreError("manifest source hash is invalid")
    size_bytes = payload.get("size_bytes")
    if size_bytes is not None and (type(size_bytes) is not int or size_bytes < 0):
        raise UnixCorpusStoreError("manifest source size is invalid")
    status_value = payload.get("status")
    if status_value not in {"ACCEPTED", "QUARANTINED"}:
        raise UnixCorpusStoreError("manifest source status is invalid")
    record_ids = _hash_list(payload.get("record_ids"), "record_ids")
    quarantine_id = payload.get("quarantine_id")
    if quarantine_id is not None and not _is_sha256(quarantine_id):
        raise UnixCorpusStoreError("manifest quarantine identifier is invalid")
    if status_value == "ACCEPTED" and (not record_ids or quarantine_id is not None):
        raise UnixCorpusStoreError("accepted source binding is invalid")
    if status_value == "QUARANTINED" and (record_ids or quarantine_id is None):
        raise UnixCorpusStoreError("quarantined source binding is invalid")
    source_id = payload.get("source_id")
    if not isinstance(source_id, str) or not source_id.startswith("unix-source-"):
        raise UnixCorpusStoreError("manifest source identifier is invalid")
    expected_source_id = _source_id(source_path, source_hash or EMPTY_SHA256)
    if source_id != expected_source_id:
        raise UnixCorpusStoreError("manifest source identifier binding is invalid")
    media_type = payload.get("media_type")
    if media_type is not None and media_type not in SUPPORTED_MEDIA_TYPES.values():
        raise UnixCorpusStoreError("manifest source media type is invalid")
    return UnixCorpusSourceEntry(
        source_id=source_id,
        source_path=source_path,
        source_hash=source_hash,
        size_bytes=size_bytes,
        media_type=media_type,
        status=status_value,
        record_ids=record_ids,
        quarantine_id=quarantine_id,
    )


def _hash_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not _is_sha256(item) for item in value):
        raise UnixCorpusStoreError(f"manifest {name} must contain SHA-256 identifiers")
    if len(value) != len(set(value)):
        raise UnixCorpusStoreError(f"manifest {name} contains duplicates")
    return tuple(value)


def _write_canonical_once(path: Path, payload: Mapping[str, Any]) -> bool:
    _assert_safe_output_directory(path.parent.parent, path.parent)
    expected = _canonical_line(payload)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise UnixCorpusStoreError("object-store target is not a regular file")
        if path.read_bytes() != expected:
            raise UnixCorpusStoreError("existing immutable corpus object does not match")
        return False
    try:
        with path.open("xb") as stream:
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise UnixCorpusStoreError("concurrent corpus object creation detected") from exc
    return True


def _write_manifest_atomic(path: Path, expected: bytes) -> None:
    if path.is_symlink():
        raise UnixCorpusStoreError("manifest target must not be a symbolic link")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="xb",
            dir=path.parent,
            prefix=".corpus_manifest.",
            suffix=".pending",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def _read_canonical_object(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise UnixCorpusStoreError(f"expected regular corpus object: {path.name}")
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise UnixCorpusStoreError(f"corpus object is not newline-canonical: {path.name}")
    try:
        text = raw[:-1].decode("utf-8", errors="strict")
        payload = _strict_json_loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKeyError) as exc:
        raise UnixCorpusStoreError(f"malformed corpus object: {path.name}") from exc
    if not isinstance(payload, dict):
        raise UnixCorpusStoreError(f"corpus object must be a JSON object: {path.name}")
    if _canonical_line(payload) != raw:
        raise UnixCorpusStoreError(f"corpus object is not canonical JSON: {path.name}")
    return payload, raw


def _assert_safe_output_directory(output_root: Path, directory: Path) -> None:
    if output_root.is_symlink() or directory.is_symlink():
        raise UnixCorpusSecurityError("intake output directories must not be symbolic links")
    try:
        root = output_root.resolve(strict=True)
        resolved = directory.resolve(strict=True)
    except OSError as exc:
        raise UnixCorpusSecurityError("intake output directory cannot be resolved") from exc
    if resolved != root and root not in resolved.parents:
        raise UnixCorpusSecurityError("intake output directory escapes intake root")
    if not resolved.is_dir():
        raise UnixCorpusSecurityError("intake output path must be a directory")


def _assert_inert_payload(payload: Mapping[str, Any]) -> None:
    if payload.get("authority_status") != NON_AUTHORITATIVE:
        raise UnixCorpusStoreError("corpus metadata authority status is invalid")
    for name, expected in AUTHORITY_FLAGS.items():
        if payload.get(name) is not expected:
            raise UnixCorpusStoreError("corpus metadata contains authority-bearing flags")


class _DuplicateJsonKeyError(ValueError):
    pass


def _strict_json_loads(text: str) -> Any:
    def reject_constant(value: str) -> None:
        raise json.JSONDecodeError(f"non-finite JSON value: {value}", text, 0)

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _DuplicateJsonKeyError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(
        text,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def _validate_json_value(value: Any, seen: set[int] | None = None) -> None:
    active = set() if seen is None else seen
    if value is None or isinstance(value, (str, bool)) or type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise _QuarantineSource(
                "NON_FINITE_JSON_VALUE",
                "non-finite JSON values are not deterministic",
            )
        return
    identity = id(value)
    if identity in active:
        raise _QuarantineSource("CYCLIC_JSON_VALUE", "cyclic JSON values are forbidden")
    active.add(identity)
    try:
        if isinstance(value, list):
            for item in value:
                _validate_json_value(item, active)
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise _QuarantineSource(
                        "NON_STRING_JSON_KEY",
                        "JSON object keys must be text",
                    )
                _validate_json_value(item, active)
            return
    finally:
        active.remove(identity)
    raise _QuarantineSource(
        "UNSUPPORTED_JSON_VALUE",
        "corpus JSON contains an unsupported value",
    )


def _canonical_json(value: Any) -> str:
    _validate_json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_bytes(value: Any) -> bytes:
    return _canonical_json(value).encode("utf-8")


def _canonical_line(value: Any) -> bytes:
    return _canonical_bytes(value) + b"\n"


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _slug(value: str) -> str:
    normalized = []
    previous_dash = False
    for character in value.casefold():
        if character.isalnum():
            normalized.append(character)
            previous_dash = False
        elif not previous_dash:
            normalized.append("-")
            previous_dash = True
    return "".join(normalized).strip("-") or "section"
