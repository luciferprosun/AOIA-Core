# Dependency Boundary Analysis

Phase: 3 - governance preparation
Status: analysis only

## Purpose

Identify future dependency risks without modifying dependencies.

## Cross-Domain Contamination Risks

- AOIA engineering documents mention LSC separation and could be mistaken for LSC scientific evidence.
- Shared archive language can blur framework authority and runtime authority.
- Provider reports can mix recommendations, audits, and claims without source boundaries.

## Runtime To Archive Risks

- Runtime may accidentally read archive material as live policy.
- Archive reports may be treated as runtime configuration.
- Review notes may be mistaken for enforced constraints.

## Archive To Runtime Risks

- Governance design could be copied into runtime without enforcement tests.
- Provider audit recommendations could be implemented as code without provenance review.
- Derived summaries could override source reports.

## LSC To AOIA Contamination Vectors

- mixed-root historical reports
- shared MHLM/MHSR terminology
- old `LST` aliases
- documents describing repository separation

## AOIA To LSC Contamination Vectors

- AOIA anti-hallucination claims used as credibility support for LSC
- model/provider consensus treated as scientific validation
- runtime provenance concepts applied to scientific evidence without domain review

## Shared Utility Risks

Future shared utilities may create risk if they:

- read both case studies without explicit case scope
- write shared provenance records
- normalize prompts across domains
- collapse provider aliases globally

## Dependency Creep Risks

- temporary bridge modules becoming permanent
- planner fallback depending on archive summaries
- retrieval code importing governance review data
- provider adapters gaining authority logic

## Split-Brain Routing Risks

Split-brain routing can occur when:

- multiple routing layers classify the same input differently
- external URLs bypass one boundary but enter another
- RHCSA local retrieval and external review share fallback paths
- old orchestration remnants remain callable

## Recommendation

Freeze dependency boundaries before implementing enforcement.

Do not modify runtime dependencies in this phase.
