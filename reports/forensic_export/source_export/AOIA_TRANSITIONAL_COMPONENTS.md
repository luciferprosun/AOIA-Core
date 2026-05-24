# AOIA Transitional Components

Date: 2026-05-23

## Transitional Components Inventory

### 1. Orchestrator stack

Files:
- `runtime/orchestrator/gemini_gemma.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/commands/local_commands.py` via `/orchestrator`
- `runtime/main.py` orchestrator branches

Status:
- PARTIAL

Reason:
- code is present
- command surface acknowledges worker removal
- runtime still imports and can route through orchestrator branches

### 2. Planner duplication

Files:
- `runtime/main.py:create_plan()`
- `runtime/orchestrator/gemini_gemma.py:create_plan()`

Status:
- PARTIAL

Reason:
- two planning concepts coexist
- one is direct model planner
- one is Gemini brain plus worker model planner

### 3. Adaptive routing experiment bundle

Files:
- `runtime/adaptive_routing/circadian_router.py`
- `runtime/adaptive_routing/environment/environment_router.py`
- `runtime/adaptive_routing/dvm_research.md`
- `runtime/adaptive_routing/routing_modes.json`
- `runtime/adaptive_routing/aoia_config.json`

Status:
- STUB / EXPERIMENTAL

Reason:
- present in repository
- not part of the clear canonical runtime spine
- only `epistemic_kernel.py` and `deterministic_router.py` appear central to current AOIA behavior

### 4. Missing extraction dependencies

Files referenced:
- `memory.rhcsa_context`
- `memory.gemma_worker_memory`

Status:
- BROKEN TRANSITIONAL EDGE

Reason:
- imports remain
- package is absent in current repository extraction

### 5. Dual ADR trees

Files:
- `docs/ADR/*`
- `docs/adr/*`

Status:
- LEGACY DUPLICATION

Reason:
- two architecture-record authorities coexist

### 6. Knowledge build pipeline inside runtime surface

Files:
- `runtime/knowledge/tools/*`
- `runtime/tools/build_rhcsa_library.py`
- `runtime/knowledge/source/*`
- `runtime/knowledge/raw/*`

Status:
- FUNCTIONAL BUT MIXED

Reason:
- source corpus, build scripts, generated indexes, and validator outputs share one runtime-facing tree

## Transitional Risk Zones

### Recursive orchestration remnants

- orchestrator planner and delegated worker model pattern remain embedded
- not active by default, but still structurally present

### Mixed memory/evidence systems

- `tools/memory.py` writes:
  - history
  - evidence
  - reasoning
  - browser logs
  - session logs
  - Obsidian vault notes
- this is functionally coherent but structurally broad

### State persistence ambiguity

- state is persisted inside repo-local paths rather than clearly outside canonical source

### Runtime/report contamination

- committed report artifacts appear within knowledge/runtime surfaces

## Transitional Judgment

The repository already contains the canonical AOIA runtime nucleus, but it is still wrapped by transitional scaffolding from:
- earlier orchestration experiments
- earlier knowledge-router layering
- earlier document migrations
- incomplete extraction of memory-adjacent modules
