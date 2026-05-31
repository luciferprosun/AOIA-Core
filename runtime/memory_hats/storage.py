"""Standalone SQLite storage for local Memory Hats advisory tags.

The store is local-only and advisory-only. It does not execute commands,
perform runtime routing, contact networks, or integrate with RHCSA grammar.
Duplicate inserts are idempotent: an existing tag with the same fingerprint is
returned unchanged instead of creating a second record.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from runtime.memory_hats.tags import PheromoneTag, ReviewStatus, TagType


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def tag_to_row(tag: PheromoneTag) -> dict[str, Any]:
    """Convert a PheromoneTag into SQLite row values."""
    return {
        "fingerprint_hash": tag.fingerprint_hash,
        "hat_id": tag.hat_id,
        "path": tag.path,
        "tag_type": tag.tag_type.value,
        "normalized_trigger": tag.normalized_trigger,
        "correction_text": tag.correction_text,
        "evidence_refs": json.dumps(list(tag.evidence_refs), sort_keys=True),
        "review_status": tag.review_status.value,
        "seen_count": tag.seen_count,
        "hat_version": tag.hat_version,
        "created_by": tag.created_by,
        "first_seen": tag.first_seen,
        "last_seen": tag.last_seen,
        "notes": tag.notes,
    }


def row_to_tag(row: sqlite3.Row | dict[str, Any]) -> PheromoneTag:
    """Convert a SQLite row into a PheromoneTag."""
    data = dict(row)
    return PheromoneTag(
        fingerprint_hash=data["fingerprint_hash"],
        hat_id=data["hat_id"],
        path=data["path"],
        tag_type=TagType(data["tag_type"]),
        normalized_trigger=data["normalized_trigger"],
        correction_text=data["correction_text"],
        evidence_refs=list(json.loads(data["evidence_refs"])),
        review_status=ReviewStatus(data["review_status"]),
        seen_count=data["seen_count"],
        hat_version=data["hat_version"],
        created_by=data["created_by"],
        first_seen=data["first_seen"],
        last_seen=data["last_seen"],
        notes=data["notes"],
    )


class SQLiteTagStore:
    """Minimal one-table SQLite store for local advisory tags."""

    def __init__(self, db_path: str):
        if not isinstance(db_path, str):
            raise TypeError("db_path must be a string")
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        self._connection.close()

    def insert_tag(self, tag: PheromoneTag) -> PheromoneTag:
        """Insert a tag, returning the existing tag on duplicate fingerprint."""
        existing = self.get_by_fingerprint(tag.fingerprint_hash)
        if existing is not None:
            return existing

        row = tag_to_row(tag)
        self._connection.execute(
            """
            INSERT INTO pheromone_tags (
                fingerprint_hash,
                hat_id,
                path,
                tag_type,
                normalized_trigger,
                correction_text,
                evidence_refs,
                review_status,
                seen_count,
                hat_version,
                created_by,
                first_seen,
                last_seen,
                notes
            )
            VALUES (
                :fingerprint_hash,
                :hat_id,
                :path,
                :tag_type,
                :normalized_trigger,
                :correction_text,
                :evidence_refs,
                :review_status,
                :seen_count,
                :hat_version,
                :created_by,
                :first_seen,
                :last_seen,
                :notes
            )
            """,
            row,
        )
        self._connection.commit()
        return tag

    def get_by_fingerprint(self, fingerprint_hash: str) -> PheromoneTag | None:
        row = self._connection.execute(
            """
            SELECT *
            FROM pheromone_tags
            WHERE fingerprint_hash = ?
            """,
            (fingerprint_hash,),
        ).fetchone()
        if row is None:
            return None
        return row_to_tag(row)

    def get_by_path(self, path: str) -> list[PheromoneTag]:
        rows = self._connection.execute(
            """
            SELECT *
            FROM pheromone_tags
            WHERE path = ?
            ORDER BY fingerprint_hash
            """,
            (path,),
        ).fetchall()
        return [row_to_tag(row) for row in rows]

    def list_by_hat(
        self,
        hat_id: str,
        review_status: str | None = None,
    ) -> list[PheromoneTag]:
        if review_status is None:
            rows = self._connection.execute(
                """
                SELECT *
                FROM pheromone_tags
                WHERE hat_id = ?
                ORDER BY fingerprint_hash
                """,
                (hat_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT *
                FROM pheromone_tags
                WHERE hat_id = ? AND review_status = ?
                ORDER BY fingerprint_hash
                """,
                (hat_id, str(review_status)),
            ).fetchall()
        return [row_to_tag(row) for row in rows]

    def update_review_status(
        self,
        fingerprint_hash: str,
        review_status: ReviewStatus,
    ) -> bool:
        result = self._connection.execute(
            """
            UPDATE pheromone_tags
            SET review_status = ?, last_seen = ?
            WHERE fingerprint_hash = ?
            """,
            (review_status.value, _utc_now(), fingerprint_hash),
        )
        self._connection.commit()
        return result.rowcount > 0

    def increment_seen_count(self, fingerprint_hash: str) -> bool:
        result = self._connection.execute(
            """
            UPDATE pheromone_tags
            SET seen_count = seen_count + 1, last_seen = ?
            WHERE fingerprint_hash = ?
            """,
            (_utc_now(), fingerprint_hash),
        )
        self._connection.commit()
        return result.rowcount > 0

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pheromone_tags (
              fingerprint_hash TEXT PRIMARY KEY,
              hat_id TEXT NOT NULL,
              path TEXT NOT NULL,
              tag_type TEXT NOT NULL,
              normalized_trigger TEXT NOT NULL,
              correction_text TEXT NOT NULL,
              evidence_refs TEXT NOT NULL DEFAULT '[]',
              review_status TEXT NOT NULL DEFAULT 'candidate',
              seen_count INTEGER NOT NULL DEFAULT 1,
              hat_version TEXT,
              created_by TEXT NOT NULL DEFAULT 'manual',
              first_seen TEXT NOT NULL,
              last_seen TEXT NOT NULL,
              notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_memory_hats_path
              ON pheromone_tags(path);

            CREATE INDEX IF NOT EXISTS idx_memory_hats_hat_status
              ON pheromone_tags(hat_id, review_status);
            """
        )
        self._connection.commit()
