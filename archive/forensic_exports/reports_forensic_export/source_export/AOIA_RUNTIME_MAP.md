# AOIA Runtime Map

Date: 2026-05-23
Mode: structural extraction audit

## Canonical Runtime Topology

Primary runtime entrypoints:
- `runtime/main.py`: canonical CLI runtime spine
- `runtime/webapp.py`: thin HTTP wrapper around `AgentRuntime`
- `runtime/run.sh`: CLI launcher
- `runtime/run_web.sh`: web launcher

Primary execution spine:
1. user input
2. `runtime/main.py`
3. local fast route via `runtime/router/local_router.py`
4. epistemic/local knowledge route via `runtime/adaptive_routing/epistemic_kernel.py`
5. secondary local knowledge route via `runtime/orchestrator/knowledge_router.py`
6. model planning via `runtime/providers/config.py`
7. tool execution via `runtime/tools/executor.py`
8. state persistence via `runtime/tools/memory.py`

## Canonical Runtime Modules

### Runtime control

- `runtime/main.py`
  - owns request loop
  - owns safeguard loading
  - owns local route, knowledge route, planner route, and tool loop

- `runtime/webapp.py`
  - exposes status, chat, and model switching over local HTTP
  - reuses `AgentRuntime`

### Routing systems

- `runtime/router/local_router.py`
  - deterministic fast path for obvious local operations

- `runtime/adaptive_routing/epistemic_kernel.py`
  - deterministic local epistemic gate
  - joins retrieval, provenance, contradiction awareness, and confidence labeling

- `runtime/orchestrator/knowledge_router.py`
  - older RHCSA-first local router
  - overlaps functionally with the epistemic kernel

### Retrieval systems

- `runtime/tools/rhcsa_search.py`
  - deterministic search over RHCSA knowledge artifacts
  - supports keyword, tag, exact, grep, and topic filtering

- `runtime/knowledge/rhcsa_engine.py`
  - formats retrieval for local operational answers

- `runtime/knowledge/**`
  - RHCSA corpus, indexes, schema, examples, validators, and source artifacts

### Provenance and contradiction systems

- `runtime/tools/epistemic_registry.py`
  - builds provenance and contradiction registries from knowledge artifacts

- `runtime/provenance_registry.json`
  - persisted provenance snapshot

- `runtime/contradiction_registry.json`
  - persisted contradiction snapshot

### Memory and state systems

- `runtime/tools/memory.py`
  - owns runtime state, JSONL traces, browser logs, and Obsidian vault generation
  - writes state inside the repository tree

- `runtime/tools/memory_hats.py`
  - scoped instruction overlays

## Authority Boundaries

Canonical authority inside this repository:
- runtime execution
- retrieval
- provenance
- contradiction handling
- bounded memory/state handling
- provider abstraction
- local web wrapper
- tests and runtime docs

Non-canonical or unstable surfaces still present:
- orchestration remnants
- adaptive routing experiments beyond the deterministic kernel
- generated-state paths created inside the repo
- historical research notes embedded in runtime paths
- duplicated ADR/documentation trees

## Dependency Summary

Core runtime dependency chain:
- `main.py` -> `LocalRouter`
- `main.py` -> `AOIAEpistemicKernel`
- `main.py` -> `KnowledgeRouter`
- `main.py` -> `ProviderManager`
- `main.py` -> `ExecutionEngine`
- `main.py` -> `MemoryStore`

Execution dependency chain:
- `ExecutionEngine` -> filesystem tools
- `ExecutionEngine` -> shell tools
- `ExecutionEngine` -> browser tools
- `ExecutionEngine` -> project scanner
- `ExecutionEngine` -> `MemoryStore`

Epistemic dependency chain:
- `AOIAEpistemicKernel` -> deterministic router
- `AOIAEpistemicKernel` -> epistemic registry
- `AOIAEpistemicKernel` -> RHCSA search

## Unstable Zones

1. `runtime/orchestrator/`
   - present in canonical runtime flow
   - partially disabled by command surface
   - still imported and still callable from `main.py`

2. `runtime/adaptive_routing/`
   - contains canonical kernel plus non-canonical research and environment routing experiments

3. `runtime/tools/memory.py`
   - writes mutable state under repository root
   - mixes runtime code and generated artifacts structurally

4. `runtime/main.py` import boundary
   - imports `memory.rhcsa_context` and `memory.gemma_worker_memory`
   - corresponding package is absent in current `AOIA-Core` extraction
   - this is a transitional break in canonical runtime completeness

## Runtime Status Judgment

AOIA-Core currently contains the true runtime center of gravity, but not yet a fully isolated canonical runtime surface.

Classification:
- runtime spine: canonical
- runtime isolation: partial
- structural stability: partial
