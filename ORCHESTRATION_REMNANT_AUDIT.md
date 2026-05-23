# Orchestration Remnant Audit

Date: 2026-05-23
Phase: AOIA Runtime Stabilization

## Scope

Analyzed:
- `runtime/orchestrator/__init__.py`
- `runtime/orchestrator/gemini_gemma.py`
- `runtime/orchestrator/knowledge_router.py`
- orchestrator references in `runtime/main.py`
- `/orchestrator` command surface in `runtime/commands/local_commands.py`

## Active Components

### KnowledgeRouter

Status:
- active in runtime flow

Evidence:
- instantiated in `main.py`
- called from `handle_knowledge_route()`

Classification:
- legacy active component

### Orchestrator branch in main runtime

Status:
- structurally active but disabled by default

Evidence:
- `main.py` contains `use_orchestrator`
- `handle_user_request()` can route into `handle_orchestrated_request()`

Classification:
- transitional active branch

## Dead or Disabled Components

### GeminiGemmaOrchestrator worker execution

Status:
- effectively disabled

Evidence:
- `gemma_provider` remains `None`
- `action_for_step()` raises when worker is unavailable
- `/orchestrator on` command explicitly says worker is disabled in this terminal build

Classification:
- legacy disabled component

### Orchestrator command enable path

Status:
- semantically dead

Evidence:
- `/orchestrator on` does not actually enable a working orchestrated worker path
- command response says the worker is disabled

Classification:
- dead control surface

## Transitional Remnants

- planner/worker split concept
- Gemini brain / Gemma worker prompt scaffolding
- worker memory dependency
- missing `memory` package imports
- delegated-step fallback logic

These remain as architectural residue from a more complex orchestration concept.

## Runtime Dependencies

`GeminiGemmaOrchestrator` depends on:
- provider manager
- worker memory
- memory hats
- RHCSA contextual injection
- validator

Dependency risk:
- missing `memory` package makes this path structurally incomplete in current AOIA-Core extraction

## Future Archival Candidates

Strong archival candidates after review:
- `runtime/orchestrator/gemini_gemma.py`
- `/orchestrator` command surface in `local_commands.py`

Conditional archival candidate:
- `runtime/orchestrator/__init__.py`

Do not archive yet:
- `runtime/orchestrator/knowledge_router.py`

Reason:
- it is still active in the current runtime path

## Classification Summary

- `KnowledgeRouter`: legacy
- `GeminiGemmaOrchestrator`: quarantine
- orchestrator enable surface: dead / quarantine
- worker-style orchestration concept: experimental legacy

## Recommendation

Short-term:
- preserve all orchestrator files
- stop treating them as canonical AOIA runtime authority

Boundary recommendation:
- only `KnowledgeRouter` remains runtime-relevant today
- the rest of `runtime/orchestrator/` should be treated as quarantine until architecture review
