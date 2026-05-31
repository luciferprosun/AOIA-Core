# AOIA-Core WhiteHat / Memory Hats - GT1 Re-Audit - 1 June 2026

## 1. Executive Verdict

Build the architecture note now. After that, implement only a minimal Linux/RHCSA Memory Hat as a dev-branch prototype.

Do not merge Memory Hats work to `main` before NLnet submission. Do not build Memory Garden, sync, global tags, Android/server split, vector search, semantic similarity, or multi-hat stacking in v0.1.

## 2. Final Architecture Decision

Leaf-Vein Routing is the actual retrieval and routing architecture for Memory Hats. SQLite, deterministic hashes, and materialized paths are the storage and retrieval foundation.

Pheromone Correction Tags are local advisory correction records. They can record repeated mistakes, unsupported command shapes, or known local corrections, but they do not prove truth or safety.

Golden Ratio, Golden Angle, and Phi ideas are future visualization only. They are not indexing, deduplication, ranking, retrieval, or truth mechanisms.

Tags are advisory. There is no command execution, no model weight modification, and no automatic prompt injection.

## 3. Minimal v0.1 Scope

Runtime package:

```text
runtime/memory_hats/
  __init__.py
  tags.py
  dedup.py
  leaf_routes.py
  storage.py
```

Tests:

```text
tests/test_memory_hats_tags.py
tests/test_memory_hats_dedup.py
tests/test_memory_hats_leaf_routes.py
tests/test_memory_hats_storage.py
```

Not in v0.1:

- `scoring.py`
- `review_queue.py`
- `sync_policy.py`
- `phi_layout.py`
- UI
- Android
- network
- global tags
- signed packs
- multi-hat stacking

## 4. Data Model v0.1

Minimal fields:

- `fingerprint_hash`
- `hat_id`
- `path`
- `tag_type`
- `normalized_trigger`
- `correction_text`
- `evidence_refs` as JSON text
- `review_status`: `candidate`, `confirmed`, or `rejected`
- `seen_count`
- `hat_version`
- `created_by`
- `first_seen`
- `last_seen`
- `notes`

## 5. SQLite Strategy

Use one table: `pheromone_tags`.

Required indexes:

- `fingerprint_hash` primary key
- `path` index
- `hat_id, review_status` index

Perplexity 2 optimization guidance:

- Prefix lookup should use path range / BETWEEN style where appropriate.
- `EXPLAIN QUERY PLAN` is debug-only.
- FTS5 is deferred.
- Partial or covering indexes can be considered only after baseline v0.1 is measured.

## 6. Leaf-Vein Routing

Example path:

```text
linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd
```

Mapping:

- central vein = hat
- primary vein = domain
- secondary vein = failure type
- micro-vein = normalized trigger or pattern
- cell = tag record

The path is a deterministic address for local advisory lookup, not a runtime command route.

## 7. Golden Ratio / Memory Garden

Golden-angle visualization is deferred.

No phi code in v0.1. No phi indexing, phi deduplication, phi ranking, or phi truth logic. The Memory Garden idea may become a future visualization layer after the local tag store is stable.

No mystical language should be used in implementation docs.

## 8. Safety Boundaries

Memory Hats v0.1 is:

- advisory only
- local-first
- deterministic on normalized inputs
- non-executing
- not executor policy
- not runtime routing
- not provider logic
- not memory/provenance/evidence write-path authority

Safety constraints:

- no raw prompt storage
- no secrets
- no absolute private paths
- no automatic model prompt injection
- no automatic blocking
- no shared or global tags in v0.1
- no recursive warning loop
- no merge to `main` before NLnet decision

## 9. NLnet Boundary

Current NLnet-safe `main` remains `d7e3448`.

Memory Hats can be mentioned only as future roadmap if needed. The RHCSA grammar dev branch remains active development and is not stable submission core unless explicitly chosen later.
