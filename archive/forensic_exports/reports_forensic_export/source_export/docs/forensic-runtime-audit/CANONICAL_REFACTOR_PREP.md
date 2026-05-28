# Canonical Refactor Prep

Status: preparation only. No refactor implemented.

## Guiding principle

The safest refactor path is boundary-first, not feature-first.

Do not start by changing provider behavior, orchestrator behavior, or routing semantics.
Start by isolating mutable state and removing ambiguity in the runtime substrate.

## Safe migration order

### Phase 1: make memory boundaries explicit

Target:

- `runtime/tools/memory.py`
- `runtime/main.py`
- `runtime/tools/executor.py`

Goal:

- split live runtime state from append-only logs
- split evidence from reasoning
- split notebook/vault projection from canonical state
- define one authoritative write path per layer

Rollback-safe because:

- it is a data-shape and boundary split before behavior changes
- the runtime can still use the old structures temporarily through adapters

### Phase 2: choose one canonical local routing authority

Target:

- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`

Goal:

- keep one routing authority for RHCSA/local knowledge
- demote the other to compatibility or archive status
- remove split-brain routing decisions

Rollback-safe because:

- the old router can be retained behind a compatibility switch during transition

### Phase 3: separate provider configuration from provider execution

Target:

- `runtime/providers/config.py`
- `runtime/providers/*.py`

Goal:

- keep model selection/persistence separate from provider instantiation
- keep env loading separate from fallback policy
- keep provider adapters pure

Rollback-safe because:

- provider behavior stays unchanged while config handling is extracted

### Phase 4: reduce `main.py` to a thin coordinator

Target:

- `runtime/main.py`

Goal:

- leave prompt assembly and execution loop coordination
- move policy, persistence, and routing decisions behind dedicated services
- keep CLI behavior stable

Rollback-safe because:

- user-facing commands can stay unchanged while internals move behind adapters

### Phase 5: retire transitional orchestrator paths

Target:

- `runtime/orchestrator/gemini_gemma.py`
- `runtime/orchestrator/knowledge_router.py`

Goal:

- quarantine or remove legacy orchestration after canonical routing is stable

Rollback-safe because:

- orchestration can be disabled by default while still preserved for archive review

## Files/modules that must be isolated first

1. `runtime/tools/memory.py`
2. `runtime/main.py`
3. `runtime/tools/executor.py`
4. `runtime/adaptive_routing/epistemic_kernel.py`
5. `runtime/orchestrator/knowledge_router.py`
6. `runtime/providers/config.py`
7. `runtime/orchestrator/gemini_gemma.py`

## Files/modules that must not be touched before governance layer is finalized

These are the highest-risk modules because they encode policy, fallback behavior, or mutable authority:

- `runtime/providers/config.py`
- `runtime/providers/aureon_provider.py`
- `runtime/providers/gemini_provider.py`
- `runtime/providers/openai_compatible.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/orchestrator/gemini_gemma.py`
- `runtime/tools/memory.py`
- `runtime/tools/memory_hats.py`
- `runtime/tools/executor.py`
- `runtime/main.py` prompt/model loop sections

## Dependency-safe refactor sequence

1. Introduce explicit adapters around the existing memory writer methods.
2. Split durable state from append-only logs.
3. Move evidence/reasoning into separate sinks.
4. Select one local RHCSA routing authority.
5. Separate provider config and provider execution.
6. Convert `main.py` into orchestration-only coordination.
7. Only after that, implement governance-layer boundaries.

## Estimated implementation phases

- **Phase A**: boundary inventory and adapter scaffolding
- **Phase B**: memory split and state normalization
- **Phase C**: routing authority consolidation
- **Phase D**: provider/config separation
- **Phase E**: thin coordinator refactor
- **Phase F**: governance layer introduction

## Safest first refactor target

`runtime/tools/memory.py`

Reason:

- it currently carries the highest contamination density
- it is the main boundary where state, logs, evidence, reasoning, and Obsidian projection collide
- cleaning this first reduces downstream ambiguity in `main.py`, `executor.py`, and the web runtime

## What should remain untouched until governance is finalized

- cloud provider selection policy
- model fallback semantics
- orchestrator plan generation
- knowledge routing threshold semantics
- contradiction interpretation semantics
- provenance registry generation semantics
- browser/tool execution semantics

