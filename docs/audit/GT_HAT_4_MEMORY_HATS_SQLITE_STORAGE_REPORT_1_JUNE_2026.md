# GT-HAT-4 — Memory Hats SQLite Local Tag Store Report — 1 June 2026

## 1. Starting Branch And HEAD

- Branch: `dev/rhcsa-command-grammar-layer`
- Starting HEAD: `b3f579c`
- Protected main: `d7e3448`
- Protected origin/main: `d7e3448`

## 2. Baseline Validation

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_tags -v`: PASS, 10 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_dedup -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_leaf_routes -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 218 tests, skipped=4

## 3. Files Created/Changed

- `runtime/memory_hats/__init__.py`
- `runtime/memory_hats/storage.py`
- `tests/test_memory_hats_storage.py`
- `docs/audit/GT_HAT_4_MEMORY_HATS_SQLITE_STORAGE_REPORT_1_JUNE_2026.md`

## 4. SQLite Schema Created

Created one local table:

- `pheromone_tags`

Columns:

- `fingerprint_hash TEXT PRIMARY KEY`
- `hat_id TEXT NOT NULL`
- `path TEXT NOT NULL`
- `tag_type TEXT NOT NULL`
- `normalized_trigger TEXT NOT NULL`
- `correction_text TEXT NOT NULL`
- `evidence_refs TEXT NOT NULL DEFAULT '[]'`
- `review_status TEXT NOT NULL DEFAULT 'candidate'`
- `seen_count INTEGER NOT NULL DEFAULT 1`
- `hat_version TEXT`
- `created_by TEXT NOT NULL DEFAULT 'manual'`
- `first_seen TEXT NOT NULL`
- `last_seen TEXT NOT NULL`
- `notes TEXT`

## 5. Indexes Created

- `idx_memory_hats_path` on `pheromone_tags(path)`
- `idx_memory_hats_hat_status` on `pheromone_tags(hat_id, review_status)`

No partial indexes, covering indexes, FTS5, EXPLAIN helper, or BETWEEN helper were added.

## 6. Store Methods Implemented

- `SQLiteTagStore(db_path: str)`
- `close() -> None`
- `insert_tag(tag: PheromoneTag) -> PheromoneTag`
- `get_by_fingerprint(fingerprint_hash: str) -> PheromoneTag | None`
- `get_by_path(path: str) -> list[PheromoneTag]`
- `list_by_hat(hat_id: str, review_status: str | None = None) -> list[PheromoneTag]`
- `update_review_status(fingerprint_hash: str, review_status: ReviewStatus) -> bool`
- `increment_seen_count(fingerprint_hash: str) -> bool`
- `tag_to_row(tag: PheromoneTag)`
- `row_to_tag(row)`

Duplicate inserts are idempotent and return the existing tag.

## 7. Tests Added

- In-memory DB initialization.
- Insert/get round trip by fingerprint.
- Evidence refs JSON round trip.
- Missing fingerprint returns `None`.
- Duplicate insert does not create duplicate rows.
- Path lookup returns matching tags.
- Hat lookup and review-status filtering.
- Review-status update.
- Seen-count increment.
- Missing updates return `False`.
- Independent restored tags do not share `evidence_refs`.
- Import guard for no network, subprocess, RHCSA, router, provider, or knowledge integration imports.

## 8. Validation Result

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_tags -v`: PASS, 10 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_dedup -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_leaf_routes -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_storage -v`: PASS, 14 tests
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 232 tests, skipped=4

## 9. Safety Confirmations

- No RHCSA command grammar integration.
- No command execution.
- No executor/router/provider/kernel/provenance/TUI/web changes.
- No phi or Memory Garden code.
- No sync or global tags.
- No network code.
- No dependency added.

## 10. New HEAD If Committed

- Pending at report creation; recorded in final chat report after commit.

## 11. Push Result

- Pending at report creation; recorded in final chat report after push.

## 12. Tag Status

- Pending at report creation; recorded in final chat report after tag push.

## 13. Recommended Next Step

- GT-HAT-5: advisory warning object.
