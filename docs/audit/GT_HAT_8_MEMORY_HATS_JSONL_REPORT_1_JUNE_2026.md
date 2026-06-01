# GT-HAT-8 - Memory Hats JSONL Export/Import Report - 1 June 2026

## 1. Starting branch and HEAD

- Branch: dev/rhcsa-command-grammar-layer
- Starting HEAD: 970fbf5 feat(memory-hats): add RHCSA advisory lookup integration [GT-HAT-6]
- Protected main: d7e3448
- Protected origin/main: d7e3448

## 2. Baseline validation

- compileall: PASS
- Memory Hats tag tests: PASS
- Memory Hats dedup tests: PASS
- Memory Hats leaf route tests: PASS
- Memory Hats storage tests: PASS
- Memory Hats advisory tests: PASS
- Memory Hats RHCSA integration tests: PASS
- Full unittest before GT-HAT-8 changes: Ran 252 tests, OK (skipped=4)

## 3. Files created/changed

- Updated `runtime/memory_hats/__init__.py`
- Added `runtime/memory_hats/jsonl.py`
- Added `tests/test_memory_hats_jsonl.py`
- Added `docs/audit/GT_HAT_8_MEMORY_HATS_JSONL_REPORT_1_JUNE_2026.md`

## 4. JSONL functions implemented

- `tag_to_jsonl_record`
- `tag_from_jsonl_record`
- `export_tags_to_jsonl`
- `import_tags_from_jsonl`

## 5. Serialization behavior

- Converts `PheromoneTag` records to plain JSON-compatible dictionaries.
- Serializes enum fields as stable enum values.
- Copies `evidence_refs` so exported/imported records do not share mutable lists.
- Exports one JSON object per line.
- Preserves input order during export.
- Performs no file I/O; callers provide and receive strings only.

## 6. Import validation behavior

- Ignores blank lines.
- Raises `ValueError` for malformed JSONL.
- Raises `ValueError` for invalid tag records.
- Raises `ValueError` for missing required serialized fields.
- Raises `ValueError` for invalid `tag_type` or `review_status` enum strings.
- Reconstructs independent `PheromoneTag` objects.

## 7. Tests added

Added `tests/test_memory_hats_jsonl.py` covering:

- JSON-compatible record export
- confirmed tag round-trip
- independent `evidence_refs`
- one JSON object per line
- multiple tag import
- blank line handling
- malformed JSONL rejection
- missing required field rejection
- invalid enum rejection
- preservation of core tag fields
- no SQLite/storage dependency inside JSONL import
- no subprocess, RHCSA command grammar, network, executor, router, or provider imports

## 8. Validation result

- compileall: PASS
- `tests.test_memory_hats_tags`: PASS
- `tests.test_memory_hats_dedup`: PASS
- `tests.test_memory_hats_leaf_routes`: PASS
- `tests.test_memory_hats_storage`: PASS
- `tests.test_memory_hats_advisory`: PASS
- `tests.test_memory_hats_rhcsa_integration`: PASS
- `tests.test_memory_hats_jsonl`: PASS
- Full unittest: Ran 264 tests, OK (skipped=4)

## 9. Safety confirmations

- No SQLite/storage dependency inside `jsonl.py`.
- No RHCSA command grammar integration changes.
- No command execution.
- No subprocess import.
- No executor changes.
- No router changes.
- No provider changes.
- No kernel changes.
- No provenance changes.
- No TUI/web changes.
- No UI/CLI rendering.
- No prompt injection.
- No phi/Memory Garden code.
- No sync/global tags.
- No signatures or signed packs.
- No network code.
- No dependency added.

## 10. New HEAD if committed

- Pending at report creation time; final chat report records the committed HEAD.

## 11. Push result

- Pending at report creation time.

## 12. Tag status

- Pending at report creation time: `dev-memory-hats-gt-hat-8`

## 13. Recommended next step

GT-HAT-7 seed/example local Linux/RHCSA tags using JSONL utilities. Keep it local-only and do not wire seed tags into executor/router/provider/runtime behavior.
