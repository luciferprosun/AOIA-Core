# AOIA-Core WhiteHat / Memory Hats - Implementation Phase Plan - 1 June 2026

## GT-HAT-0 - Architecture Note Only

Objective:
Create `docs/architecture/MEMORY_HATS_ARCHITECTURE.md` based on the GT1 re-audit.

Allowed files:
- `docs/architecture/MEMORY_HATS_ARCHITECTURE.md`
- tests not required

Do not:
- no runtime code
- no tests
- no integration
- no main merge

Commit:
`docs: add Memory Hats architecture note [GT-HAT-0]`

## GT-HAT-1 - Dataclasses and Enums

Objective:
Define minimal `PheromoneTag`, `TagType`, `ReviewStatus`, and `AdvisoryWarning` if needed.

Allowed files:
- `runtime/memory_hats/__init__.py`
- `runtime/memory_hats/tags.py`
- `tests/test_memory_hats_tags.py`

Tests:
- instantiate tag
- enum validation
- dict/json serialization if supported
- defaults safe

Do not:
- no storage
- no routing
- no hashing
- no RHCSA integration

Commit:
`feat(memory-hats): define tag dataclasses and enums [GT-HAT-1]`

## GT-HAT-2 - Normalization and Hashing

Objective:
Implement `normalize_trigger` and `compute_fingerprint`.

Allowed files:
- `runtime/memory_hats/dedup.py`
- `tests/test_memory_hats_dedup.py`

Tests:
- whitespace normalization
- lowercase normalization
- stable SHA-256 output
- duplicate normalized inputs yield same hash

Do not:
- no storage
- no routing
- no command execution

Commit:
`feat(memory-hats): add trigger normalization and fingerprint hashing [GT-HAT-2]`

## GT-HAT-3 - Leaf-Vein Path Builder

Objective:
Implement path builder and parser.

Allowed files:
- `runtime/memory_hats/leaf_routes.py`
- `tests/test_memory_hats_leaf_routes.py`

Tests:
- path construction
- slug normalization
- round-trip path parse
- reject unsafe path components

Do not:
- no SQLite
- no retrieval logic beyond path construction
- no phi layout

Commit:
`feat(memory-hats): add leaf-vein path builder [GT-HAT-3]`

## GT-HAT-4 - SQLite Local Tag Store

Objective:
Implement one-table SQLite local tag store.

Allowed files:
- `runtime/memory_hats/storage.py`
- `tests/test_memory_hats_storage.py`

Tests:
- init in-memory DB
- insert tag
- query by fingerprint
- query by path
- duplicate fingerprint rejected or returns existing tag
- empty query returns None
- no network

Do not:
- no sync
- no global tags
- no review queue module
- no phi layout
- no RHCSA integration yet

Commit:
`feat(memory-hats): add SQLite local tag storage [GT-HAT-4]`

## GT-HAT-5 - Advisory Warning Object

Objective:
Return structured advisory warning object from a found tag.

Allowed files:
- `runtime/memory_hats/tags.py`, or `runtime/memory_hats/advisory.py` if justified
- `tests/test_memory_hats_advisory.py`

Tests:
- confirmed tag returns high confidence advisory
- candidate tag returns low confidence advisory
- rejected tag returns no active advisory, or rejected advisory depending design

Do not:
- no UI
- no CLI formatting
- no model prompt injection

Commit:
`feat(memory-hats): add advisory warning object [GT-HAT-5]`

## GT-HAT-6 - RHCSA Grammar Lookup Integration

Objective:
Integrate existing command grammar output with local Memory Hat lookup.

Allowed files:
- minimal integration file only
- existing command grammar tests may be extended only if necessary

Tests:
- `dnf status sshd` example
- confirmed tag found returns advisory object
- no tag returns None unless `auto_candidate` is enabled
- `auto_candidate` default is False
- no command execution

Do not:
- no executor integration
- no shell execution
- no router/provider/kernel changes
- no main merge

Commit:
`feat(memory-hats): integrate RHCSA grammar advisory lookup [GT-HAT-6]`

## GT-HAT-7 - JSONL Export / Import

Objective:
Local backup/import only.

Allowed files:
- `runtime/memory_hats/storage.py`, or `runtime/memory_hats/jsonl.py`
- `tests/test_memory_hats_jsonl.py`

Tests:
- export exact records
- import records
- duplicate import is idempotent
- no private absolute paths if sanitizer exists

Do not:
- no network
- no sync
- no signed packs yet

Commit:
`feat(memory-hats): add local JSONL import export [GT-HAT-7]`

## GT-HAT-8 - Memory Garden Design Note Only

Objective:
Document future phyllotaxis visualization.

Allowed files:
- `docs/architecture/MEMORY_GARDEN_DESIGN_NOTE.md`

Do not:
- no `phi_layout.py`
- no UI code
- no D3
- no frontend

Commit:
`docs: add Memory Garden visualization design note [GT-HAT-8]`
