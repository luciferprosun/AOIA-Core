# GT-HAT-7 - Memory Hats Linux/RHCSA Seed Example Tags Report - 1 June 2026

## 1. Starting branch and HEAD

- Branch: dev/rhcsa-command-grammar-layer
- Starting HEAD: 8e64e88 feat(memory-hats): add JSONL export import utilities [GT-HAT-8]
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
- Memory Hats JSONL tests: PASS
- Full unittest before GT-HAT-7 changes: Ran 264 tests, OK (skipped=4)

## 3. Files created/changed

- Updated `runtime/memory_hats/__init__.py`
- Added `runtime/memory_hats/seeds.py`
- Added `runtime/knowledge/memory_hats/linux_rhcsa_seed_tags.jsonl`
- Added `tests/test_memory_hats_seeds.py`
- Added `docs/audit/GT_HAT_7_MEMORY_HATS_SEED_TAGS_REPORT_1_JUNE_2026.md`

## 4. Seed JSONL file path

`runtime/knowledge/memory_hats/linux_rhcsa_seed_tags.jsonl`

## 5. Seed tag count

- Seed tags: 5
- Review statuses:
  - confirmed: 4
  - candidate: 1
  - rejected: 0

## 6. Seed tag examples

- `dnf status sshd` -> `systemctl status sshd`
- `dnf restart nginx` -> `systemctl restart nginx`
- `rpm status bash` -> `rpm -q bash`
- `systemctl install httpd` -> `dnf install httpd`
- `service status sshd` -> prefer `systemctl status sshd` on modern RHEL systems

These are local example correction tags only. They are not a global safety database or trusted public tag pack.

## 7. Seed loader functions implemented

- `load_linux_rhcsa_seed_tags`
- `import_seed_tags_into_store`
- `LINUX_RHCSA_SEED_TAGS_PATH`

Behavior:

- `load_linux_rhcsa_seed_tags()` reads the bundled JSONL seed file and returns `PheromoneTag` records.
- `import_seed_tags_into_store(store, tags)` inserts tags into a provided `SQLiteTagStore`.
- Import is idempotent through `SQLiteTagStore.insert_tag`.
- No seed tags are loaded automatically on import.
- No runtime state is modified unless a caller explicitly calls the import function with a store.

## 8. Tests added

Added `tests/test_memory_hats_seeds.py` covering:

- seed JSONL path existence
- seed count between 3 and 7
- all records are `PheromoneTag` instances
- all records use `hat_id == "linux_rhcsa"`
- fingerprint hash shape
- valid Leaf-Vein paths
- only candidate/confirmed review statuses
- no rejected seed tags
- required `dnf status sshd` tag
- high-confidence advisory after explicit import into `SQLiteTagStore`
- idempotent import
- no unexpected seen_count mutation
- no subprocess, command_grammar, executor, router, provider, or network imports

## 9. Validation result

- compileall: PASS
- `tests.test_memory_hats_tags`: PASS
- `tests.test_memory_hats_dedup`: PASS
- `tests.test_memory_hats_leaf_routes`: PASS
- `tests.test_memory_hats_storage`: PASS
- `tests.test_memory_hats_advisory`: PASS
- `tests.test_memory_hats_rhcsa_integration`: PASS
- `tests.test_memory_hats_jsonl`: PASS
- `tests.test_memory_hats_seeds`: PASS
- Full unittest: Ran 276 tests, OK (skipped=4)

## 10. Safety confirmations

- No command execution.
- No subprocess import.
- No command_grammar changes.
- No executor changes.
- No router changes.
- No provider changes.
- No kernel changes.
- No provenance changes.
- No TUI/web changes.
- No automatic runtime seed loading.
- No UI/CLI rendering.
- No prompt injection.
- No phi/Memory Garden code.
- No sync/global tags.
- No signed packs.
- No network code.
- No dependency added.

## 11. New HEAD if committed

- Pending at report creation time; final chat report records the committed HEAD.

## 12. Push result

- Pending at report creation time.

## 13. Tag status

- Pending at report creation time: `dev-memory-hats-gt-hat-7`

## 14. Recommended next step

GT-HAT-9 end-to-end prototype test. Keep it local-only: explicit seed load into an in-memory or local test store, lookup advisory, no executor/router/provider/runtime integration.
