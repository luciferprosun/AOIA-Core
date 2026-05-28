# Phase 3 Dependency Risks

Date: 2026-05-24
Phase: AOIA governance preparation

## Purpose

Record dependency and contamination risks before future runtime stabilization.

Primary design document:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/DEPENDENCY_BOUNDARY_ANALYSIS.md`

## Runtime Dependency Risks

- routing layers may remain split-brain if old and new classifiers coexist
- provider adapters may accidentally gain authority logic
- planner fallback may bypass provenance boundaries
- local RHCSA retrieval may contaminate external review unless boundaries remain explicit

## Archive Dependency Risks

- AOIA forensic reports may be treated as live runtime policy
- Master Library summaries may be treated as evidence rather than derived review material
- provider manifests may be mistaken for source files
- archive material may influence runtime without a migration phase

## LSC/AOIA Cross-Domain Risks

- shared MHLM/MHSR terminology can blur case-study boundaries
- old `LST` references can create transitional ambiguity
- LSC scientific lineage must not validate AOIA runtime claims
- AOIA engineering lineage must not validate LSC scientific claims

## Shared Utility Risks

Future utilities become risky if they:

- read both case studies without explicit scope
- normalize prompts across domains
- write shared provenance records
- collapse provider aliases globally
- merge contradiction registries

## Dependency Creep Risks

Avoid:

- `runtime_v2`
- `memory_new`
- `kernel_final`
- duplicate runtime trees
- experimental architecture clones
- archive-to-runtime shortcut imports

## Future Requirements

Before runtime implementation:

- define allowed import directions
- define runtime/archive read boundaries
- define provenance validation API conceptually
- freeze case-study scope identifiers
- design tests for forbidden transitions

## Current Status

No dependencies were modified in Phase 3.
