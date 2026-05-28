# Routing Authority Analysis

Date: 2026-05-23
Phase: AOIA Runtime Stabilization

## Scope

Compared:
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`

## Functional Relationship

### AOIAEpistemicKernel

Responsibilities:
- deterministic pre-routing
- local evidence retrieval
- provenance-aware evidence enrichment
- contradiction-aware output pressure
- confidence labeling
- manual review signaling

Dependency chain:
- `main.py`
- `adaptive_routing/deterministic_router.py`
- `tools/epistemic_registry.py`
- `tools/rhcsa_search.py`

Output style:
- returns a structured kernel decision
- can terminate the request locally with confidence and manual-review signals

### KnowledgeRouter

Responsibilities:
- older RHCSA-first local retrieval gate
- confidence thresholding
- token-savings accounting
- local answer formatting through `RHCSAKnowledgeEngine`

Dependency chain:
- `main.py`
- `knowledge/rhcsa_engine.py`
- `tools/rhcsa_search.py`

Output style:
- returns a simpler local knowledge decision
- no provenance or contradiction awareness

## Overlap

Shared scope:
- both attempt to intercept Linux/RHCSA operational queries before cloud-model planning
- both use deterministic local retrieval inputs
- both determine whether the runtime should answer locally

Shared dependency root:
- both ultimately depend on RHCSA retrieval surfaces

## Duplication

Duplicated concerns:
- Linux-operational query detection
- local-first retrieval gating
- confidence-based local response routing
- fallback to model path after local miss

This is architectural duplication, not just implementation duplication.

## Canonical Candidate

Recommended canonical routing authority:
- `AOIAEpistemicKernel`

Reason:
- it includes all strategic properties expected from AOIA proper:
  - deterministic routing pressure
  - provenance-aware retrieval
  - contradiction-aware warning logic
  - confidence labeling
  - manual review hooks

## Legacy Candidate

Recommended legacy candidate:
- `KnowledgeRouter`

Reason:
- it appears to be a pre-kernel local RHCSA gate
- it provides simpler threshold routing and token-savings bookkeeping
- it does not carry the newer epistemic authority model

## Current Runtime Reality

Current order in `main.py`:
1. `LocalRouter`
2. `AOIAEpistemicKernel`
3. `KnowledgeRouter`
4. planner / model path

Interpretation:
- the kernel is already the primary knowledge authority candidate
- `KnowledgeRouter` now acts as a second-stage compatibility fallback

## Migration Risks

### If KnowledgeRouter is removed too early

Risks:
- loss of compatibility behavior for existing RHCSA answer formatting
- loss of token-savings report generation
- possible retrieval regressions hidden in `knowledge/rhcsa_engine.py`

### If both remain canonical

Risks:
- long-term routing ambiguity
- inconsistent local-answer semantics
- duplicate maintenance surface
- harder determinism claims

## Recommendation

Boundary recommendation:
- treat `AOIAEpistemicKernel` as the canonical routing authority
- treat `KnowledgeRouter` as transitional legacy compatibility
- do not merge them in this phase
- do not delete either in this phase

## Classification

- `AOIAEpistemicKernel`: canonical candidate
- `KnowledgeRouter`: legacy candidate
- current dual-routing state: transitional
