# Memory Layer Decomposition

Date: 2026-05-23
Phase: AOIA Runtime Stabilization

## Scope

Analyzed:
- `runtime/tools/memory.py`
- `runtime/tools/memory_hats.py`
- direct usage from `runtime/main.py`
- direct usage from `runtime/tools/executor.py`

## Responsibility Decomposition

### 1. Runtime state persistence

Owned by:
- `build_runtime_paths()`
- `MemoryStore.save()`
- `MemoryStore.update_cwd()`
- `MemoryStore.set_current_task()`
- `MemoryStore.record_command()`
- `MemoryStore.record_result()`

Role:
- persist session identity and compact runtime continuity state

### 2. Event logging

Owned by:
- `append_history()`
- `append_browser_event()`
- JSONL log files under `memory/` and `logs/`

Role:
- record operational trace and session activity

### 3. Evidence logging

Owned by:
- `append_evidence()`

Role:
- create a distinct evidence channel
- currently still colocated with general mutable runtime state

### 4. Reasoning trace logging

Owned by:
- `append_reasoning()`

Role:
- store epistemic / reasoning traces separately from evidence

### 5. Vault generation

Owned by:
- `build_obsidian_vault_paths()`
- `append_vault_note()`
- `_append_channel_note()`

Role:
- generate human-readable Obsidian-compatible continuity notes

### 6. Browser/session capture support

Owned by:
- browser log path setup
- screenshot path plumbing through executor

Role:
- support browser operations and inspection persistence

### 7. Memory overlays

Owned outside `memory.py` by:
- `runtime/tools/memory_hats.py`

Role:
- persistent instruction overlays
- semi-adjacent to memory layer, but not integrated cleanly into a single ontology

## Mixed Authority Problems

`memory.py` currently combines:
- runtime state store
- operational logging
- evidence channel
- reasoning channel
- user-facing vault generation
- browser trace persistence

This is too many authority classes in one module.

## Entropy Hotspots

### Hotspot 1: path creation

Issue:
- one module decides and creates all mutable directories
- source and runtime data are tightly coupled

### Hotspot 2: dual-format persistence

Issue:
- same events are written as:
  - machine-readable JSONL
  - human-readable vault notes

Risk:
- semantic drift between channels

### Hotspot 3: mixed evidence and operations

Issue:
- `append_history()` and `append_evidence()` are both called during normal action execution
- operational artifacts can blur with epistemic evidence

### Hotspot 4: vault as default side effect

Issue:
- ordinary runtime actions generate Obsidian notes automatically
- vault generation is not isolated as a separate concern

## Future L0-L5 Mapping Potential

Preliminary mapping potential:

- L0: raw runtime state
  - current `state/agent_state.json`

- L1: operational trace
  - current logs and command/browser/session traces

- L2: evidence memory
  - current `evidence_memory.jsonl`

- L3: reasoning trace
  - current `reasoning_trace.jsonl`

- L4: contextual overlays
  - current memory hats

- L5: human-readable continuity / vault projection
  - current `obsidian_vault/`

This mapping is feasible, but not yet encoded structurally.

## Stabilization Recommendation

Before ontology implementation:
1. treat `memory.py` as a monolithic transitional adapter
2. document separate memory authorities explicitly
3. avoid adding more responsibilities to this module
4. isolate overlay logic, vault projection, and state persistence conceptually before code migration

## Classification

- current memory layer: functional but overcompressed
- ontology readiness: partial
- authority separation inside memory layer: not yet stable
