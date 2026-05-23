# AOIA Contamination Report

Date: 2026-05-23
Mode: read-heavy structural audit

## Confirmed Contamination Zones

### 1. Generated-state contamination risk

Severity: HIGH

Observed:
- `runtime/tools/memory.py` creates and writes:
  - `state/`
  - `memory/`
  - `logs/`
  - `screenshots/`
  - `obsidian_vault/`

Impact:
- runtime-generated state is structurally colocated with canonical source
- repository cleanliness and authority clarity degrade after normal execution

### 2. Duplicate routing logic

Severity: HIGH

Observed:
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`

Impact:
- two local knowledge gating paths coexist
- local deterministic routing claims are harder to validate because one path is kernel-centric and the other is legacy RHCSA-router-centric

### 3. Orchestration remnants inside canonical runtime

Severity: HIGH

Observed:
- `runtime/orchestrator/gemini_gemma.py`
- `runtime/main.py` still imports and conditionally enables orchestrator flow
- `/orchestrator` local command still exists even though the command text says the worker is disabled

Impact:
- runtime surface still carries transitional autonomy complexity
- canonical AOIA core is not yet strictly runtime-minimal

### 4. Transitional extraction break

Severity: HIGH

Observed:
- `runtime/main.py` imports:
  - `memory.rhcsa_context`
  - `memory.gemma_worker_memory`
- current `AOIA-Core/runtime/` has no `memory/` package
- direct import test fails with `ModuleNotFoundError: No module named 'memory'`

Impact:
- current repository extraction is structurally incomplete
- canonical runtime cannot be treated as fully self-contained

### 5. Documentation duplication

Severity: MODERATE

Observed:
- `docs/ADR/`
- `docs/adr/`

Impact:
- architecture authority is duplicated
- ADR history is harder to audit deterministically

### 6. Experimental material inside runtime paths

Severity: MODERATE

Observed:
- `runtime/adaptive_routing/dvm_research.md`
- `runtime/adaptive_routing/environment/*`
- `runtime/adaptive_routing/circadian_router.py`

Impact:
- experimental routing research shares the same surface as canonical runtime modules
- future cleanup could accidentally blur canonical vs experimental behavior

### 7. Historical artifact inside knowledge paths

Severity: LOW

Observed:
- committed `runtime/knowledge/validator/validation_report.md`
- source PDF and raw extraction files live beside canonical knowledge indexes

Impact:
- retrieval authority is still understandable
- artifact layering is mixed between source, generated derivative, and validator output

## Duplicate Authority Risks

- local epistemic route vs legacy knowledge route
- planner route vs orchestrator planner
- docs `ADR` vs `adr`

## Cloud Fallback Ambiguity

Severity: MODERATE

Observed:
- `ProviderManager` is cloud-first with fallback chain
- runtime claims local-first at architecture level, but model planning remains remote-provider-dependent when local routes miss

Impact:
- deterministic local retrieval exists
- full runtime determinism and locality do not exist end-to-end

## Self-Modifying Behavior Risk

Severity: LOW

Observed:
- no explicit self-modifying code path found
- however, runtime writes persistent state and vault content into repo-local mutable surfaces

Impact:
- not self-modification of code
- but persistent runtime mutation of repository contents is structurally real

## Contamination Summary

Blocking structural contaminants:
1. missing imported memory package
2. duplicated knowledge routing paths
3. generated-state creation inside repo root
4. orchestration remnants in canonical runtime flow

Non-blocking contaminants:
1. duplicated ADR trees
2. adaptive-routing research artifacts
3. mixed knowledge source/derivative/report layering
