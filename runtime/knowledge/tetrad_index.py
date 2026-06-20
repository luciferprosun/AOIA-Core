from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Any, Iterable

from runtime.knowledge.tetrad import TetradRecord


class TetradIndexError(ValueError):
    pass


class InvalidTetradIndexKeyError(TetradIndexError):
    pass


class DuplicateTetradIndexKeyError(TetradIndexError):
    pass


class TetradIndexKeyNotFoundError(TetradIndexError):
    pass


@dataclass(frozen=True)
class TetradExactKeyIndex:
    entries: tuple[tuple[str, TetradRecord], ...]
    index_id: str = field(init=False)
    index_hash: str = field(init=False)
    read_only: bool = field(init=False, default=True)
    display_only: bool = field(init=False, default=True)
    non_authoritative: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        try:
            entries = tuple(self.entries)
        except TypeError as error:
            raise TypeError("entries must be an iterable of key/record pairs") from error

        normalized: list[tuple[str, TetradRecord]] = []
        seen: set[str] = set()
        for item in entries:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("entries must contain key/record pairs")
            key, record = item
            normalized_key = _valid_key(key)
            if not isinstance(record, TetradRecord) or record.read_only is not True:
                raise TypeError("index values must be read-only TetradRecord values")
            if normalized_key != record.tetrad_id:
                raise ValueError("index key must exactly match record tetrad_id")
            if normalized_key in seen:
                raise DuplicateTetradIndexKeyError(
                    "duplicate tetrad_id is not allowed"
                )
            seen.add(normalized_key)
            normalized.append((normalized_key, record))

        normalized_entries = tuple(sorted(normalized, key=lambda item: item[0]))
        keys = tuple(key for key, _ in normalized_entries)
        index_hash = _stable_hash(
            {
                "keys": keys,
                "record_count": len(normalized_entries),
            }
        )
        object.__setattr__(self, "entries", normalized_entries)
        object.__setattr__(self, "index_hash", index_hash)
        object.__setattr__(
            self,
            "index_id",
            "tetrad-exact-key-index-" + index_hash[:24],
        )

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(key for key, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclass(frozen=True)
class TetradIndexSnapshot:
    snapshot_id: str
    snapshot_hash: str
    index_id: str
    index_hash: str
    keys: tuple[str, ...]
    record_count: int
    read_only: bool = field(init=False, default=True)
    display_only: bool = field(init=False, default=True)
    non_authoritative: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        normalized_keys = tuple(_valid_key(key) for key in self.keys)
        if normalized_keys != tuple(sorted(set(normalized_keys))):
            raise ValueError("snapshot keys must be unique and sorted")
        if self.record_count != len(normalized_keys):
            raise ValueError("snapshot record_count must match keys")
        if not isinstance(self.snapshot_id, str) or not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty text")
        _valid_hash(self.snapshot_hash, "snapshot_hash")
        if not isinstance(self.index_id, str) or not self.index_id:
            raise ValueError("index_id must be non-empty text")
        _valid_hash(self.index_hash, "index_hash")
        object.__setattr__(self, "keys", normalized_keys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_hash": self.snapshot_hash,
            "index_id": self.index_id,
            "index_hash": self.index_hash,
            "keys": list(self.keys),
            "record_count": self.record_count,
            "read_only": self.read_only,
            "display_only": self.display_only,
            "non_authoritative": self.non_authoritative,
        }


def build_tetrad_exact_key_index(
    records: Iterable[TetradRecord],
) -> TetradExactKeyIndex:
    if isinstance(records, (str, bytes)):
        raise TypeError("records must be an iterable of TetradRecord values")
    try:
        values = tuple(records)
    except TypeError as error:
        raise TypeError("records must be an iterable of TetradRecord values") from error
    entries: list[tuple[str, TetradRecord]] = []
    for record in values:
        if not isinstance(record, TetradRecord) or record.read_only is not True:
            raise TypeError("records must contain only read-only TetradRecord values")
        entries.append((record.tetrad_id, record))
    return TetradExactKeyIndex(entries=tuple(entries))


def lookup_tetrad_record(
    index: TetradExactKeyIndex,
    key: str,
) -> TetradRecord:
    if not isinstance(index, TetradExactKeyIndex):
        raise TypeError("index must be a TetradExactKeyIndex")
    normalized_key = _valid_key(key)
    keys = index.keys
    position = bisect_left(keys, normalized_key)
    if position == len(keys) or keys[position] != normalized_key:
        raise TetradIndexKeyNotFoundError("tetrad key was not found")
    return index.entries[position][1]


def snapshot_tetrad_index(
    index: TetradExactKeyIndex,
) -> TetradIndexSnapshot:
    if not isinstance(index, TetradExactKeyIndex):
        raise TypeError("index must be a TetradExactKeyIndex")
    values = {
        "index_id": index.index_id,
        "index_hash": index.index_hash,
        "keys": index.keys,
        "record_count": len(index),
    }
    snapshot_hash = _stable_hash(values)
    return TetradIndexSnapshot(
        snapshot_id="tetrad-index-snapshot-" + snapshot_hash[:24],
        snapshot_hash=snapshot_hash,
        index_id=index.index_id,
        index_hash=index.index_hash,
        keys=index.keys,
        record_count=len(index),
    )


def _valid_key(value: Any) -> str:
    if not isinstance(value, str):
        raise InvalidTetradIndexKeyError("tetrad key must be text")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise InvalidTetradIndexKeyError(
            "tetrad key must be a lowercase SHA-256 identifier"
        )
    return value


def _valid_hash(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 value")
    return value


def _stable_hash(values: dict[str, Any]) -> str:
    material = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
