# AOIA Runtime Boundary Recommendation

Date: 2026-05-23
Phase: AOIA Runtime Stabilization

## Canonical Runtime Boundary

Recommended canonical runtime boundary:
- `runtime/main.py`
- `runtime/webapp.py`
- `runtime/router/`
- canonical subset of `runtime/adaptive_routing/`
  - especially `epistemic_kernel.py`
  - especially `deterministic_router.py`
- `runtime/tools/executor.py`
- runtime-safe filesystem/shell/browser tools
- `runtime/providers/`
- `runtime/commands/`

Exclude from canonical runtime authority for now:
- orchestration worker remnants
- routing experiments not used by the core loop
- repo-local generated state outputs

## Canonical Routing Boundary

Recommended canonical routing boundary:
- `LocalRouter`
- `AOIAEpistemicKernel`

Treat as transitional compatibility:
- `KnowledgeRouter`

Treat as non-canonical:
- worker-style orchestrated planning

## Mutable State Boundary

Recommended mutable state boundary:
- all generated runtime outputs must be treated as non-canonical mutable state

Includes:
- `state/`
- `memory/`
- `logs/`
- `screenshots/`
- `obsidian_vault/`

Architectural rule:
- mutable runtime outputs must not define source authority

## Orchestration Boundary

Recommended orchestration boundary:
- quarantine boundary around non-essential orchestrator components

Current practical rule:
- `KnowledgeRouter` may remain reachable as legacy compatibility
- `GeminiGemmaOrchestrator` should not be treated as canonical runtime

## Future Memory Ontology Integration Boundary

Recommended integration boundary before ontology work:
- state persistence boundary
- operational logging boundary
- evidence boundary
- reasoning boundary
- overlay boundary
- vault projection boundary

These must be modeled separately before any L0-L5 ontology implementation.

## Stabilization Priorities

1. make routing authority explicit
2. isolate mutable runtime outputs conceptually from source authority
3. quarantine non-canonical orchestrator remnants
4. document memory sub-authorities before adding ontology
5. resolve missing `memory` package imports before claiming AOIA-Core is self-contained

## Final Recommendation

AOIA should proceed into memory ontology work only after these boundary decisions are accepted:
- `AOIAEpistemicKernel` is the canonical routing authority
- `KnowledgeRouter` is legacy compatibility
- generated runtime state is non-canonical
- orchestrator worker path is quarantine, not core
- memory layer must be decomposed conceptually before structural migration
