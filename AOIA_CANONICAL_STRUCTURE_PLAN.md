# AOIA Canonical Structure Plan

Date: 2026-05-23
Mode: prepare structure without aggressive migration

## Target Canonical Root Structure

```text
/runtime
/provenance
/contradictions
/memory
/retrieval
/governance
/tests
/archive
/docs
```

## Current State

Already present:
- `/runtime`
- `/tests`
- `/archive`
- `/docs`

Prepared in this phase as structural targets only:
- `/provenance`
- `/contradictions`
- `/memory`
- `/retrieval`
- `/governance`

No aggressive migration has been executed.

## Planned Authority Mapping

### `/runtime`

Canonical content:
- `main.py`
- `webapp.py`
- `commands/`
- `router/`
- canonical subsets of `adaptive_routing/`
- `providers/`
- `tools/executor.py`
- browser/filesystem/shell tool surfaces

### `/provenance`

Planned target:
- provenance registries
- provenance builders
- provenance policy docs

Current source before migration:
- `runtime/provenance_registry.json`
- `runtime/tools/epistemic_registry.py`

### `/contradictions`

Planned target:
- contradiction registries
- contradiction policy docs

Current source before migration:
- `runtime/contradiction_registry.json`
- contradiction portions of `runtime/tools/epistemic_registry.py`

### `/memory`

Planned target:
- runtime state policy
- memory schema
- vault policy
- missing imported memory package once operator-approved

Current source before migration:
- `runtime/tools/memory.py`
- unresolved imports in `runtime/main.py` that expect a `memory` package

### `/retrieval`

Planned target:
- deterministic retrieval logic
- RHCSA search
- retrieval policy and indexing surfaces

Current source before migration:
- `runtime/tools/rhcsa_search.py`
- `runtime/knowledge/rhcsa_engine.py`
- selected retrieval-facing pieces of `runtime/knowledge/`

### `/governance`

Planned target:
- runtime boundary
- non-goals
- constraints
- repository constitution
- ADR canonical authority

Current source before migration:
- `docs/RUNTIME_BOUNDARY.md`
- `docs/NON_GOALS.md`
- `docs/CONSTRAINTS.md`
- `docs/REPOSITORY_CONSTITUTION.md`
- `docs/ADR/` and `docs/adr/`

## Risk Notes

1. Do not migrate orchestration remnants into canonical runtime blindly.
2. Do not migrate generated state into canonical authority roots.
3. Do not flatten `adaptive_routing/` until canonical vs experimental modules are explicitly approved.
4. Do not resolve the missing `memory` package by ad hoc copying without architecture review.

## Immediate Review Priorities

1. Decide whether `KnowledgeRouter` survives or is superseded by `AOIAEpistemicKernel`.
2. Decide whether orchestrator code remains archived or stays in runtime-adjacent staging.
3. Decide how repo-local mutable state will be isolated from canonical source.
4. Decide which ADR tree becomes canonical.
