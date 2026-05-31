# AOIA-Core Memory Hats Architecture

Status: pre-implementation architecture note.

This document defines the first safe implementation boundary for Memory Hats. It is not runtime code and does not change AOIA-Core behavior.

## What Memory Hats Are

Memory Hats are local advisory memory slices for a narrow operational domain. The first target is a Linux/RHCSA hat that can remember repeated command-shape mistakes, unsupported patterns, or local correction notes.

A Memory Hat is not a global memory system. It is not model training, prompt injection, executor policy, or a truth engine.

## Pheromone Correction Tags

Pheromone Correction Tags are local correction records. They capture a normalized trigger, a correction note, review status, evidence references, and a deterministic fingerprint.

The tag can say: "this pattern has been seen and reviewed locally." It cannot say: "this command is safe" or "this answer is true."

Review status:

- `candidate`: observed but not confirmed
- `confirmed`: human-confirmed local advisory
- `rejected`: explicitly not active

## Leaf-Vein Routing

Leaf-Vein Routing is the path structure used to address tags.

Example:

```text
linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd
```

Mapping:

- central vein = hat
- primary vein = domain
- secondary vein = failure type
- micro-vein = normalized trigger
- cell = tag record

The path is for lookup and inspection only. It is not an executor route.

## Minimal v0.1 Scope

Runtime modules planned after this note:

```text
runtime/memory_hats/
  __init__.py
  tags.py
  dedup.py
  leaf_routes.py
  storage.py
```

Tests planned:

```text
tests/test_memory_hats_tags.py
tests/test_memory_hats_dedup.py
tests/test_memory_hats_leaf_routes.py
tests/test_memory_hats_storage.py
```

The first implementation should define dataclasses/enums, normalization and hashing, path building, and a local SQLite tag store. Integration with RHCSA grammar lookup comes later and must remain advisory.

## Storage Foundation

v0.1 uses SQLite with one table: `pheromone_tags`.

Required indexes:

- `fingerprint_hash` primary key
- `path` index
- `hat_id, review_status` index

Path prefix lookup should use range / BETWEEN style where appropriate. `EXPLAIN QUERY PLAN` is a debug tool only. FTS5, partial indexes, and covering indexes are deferred until measured need exists.

## Safety Boundaries

Memory Hats are:

- advisory only
- local
- deterministic on normalized inputs
- non-executing
- not executor policy
- not runtime routing
- not provider logic
- not memory/provenance/evidence write-path authority

The implementation must not store raw prompts, secrets, or absolute private paths. It must not inject model prompts automatically, block commands automatically, or create shared/global tags in v0.1.

## Deferred Features

Deferred from v0.1:

- scoring
- review queue module
- sync policy
- global tags
- signed packs
- Android/server split
- vector search
- semantic similarity
- multi-hat stacking
- UI
- Memory Garden

## Golden Ratio / Memory Garden

Golden Ratio, Golden Angle, Phi, and Memory Garden concepts are future visualization only.

There is no phi indexing, phi ranking, phi deduplication, or phi truth logic in v0.1.

## Implementation Sequence

1. GT-HAT-0: architecture note only.
2. GT-HAT-1: dataclasses and enums.
3. GT-HAT-2: normalization and fingerprint hashing.
4. GT-HAT-3: Leaf-Vein path builder.
5. GT-HAT-4: SQLite local tag store.
6. GT-HAT-5: advisory warning object.
7. GT-HAT-6: RHCSA grammar advisory lookup.
8. GT-HAT-7: local JSONL import/export.
9. GT-HAT-8: Memory Garden design note only.
