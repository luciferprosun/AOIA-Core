# Runtime Safety Contracts

Phase: 3 - governance preparation
Status: design contract only

## Runtime Invariants

- Runtime state is not canonical authority.
- Runtime logs are not evidence.
- Retrieval results require provenance boundaries before use as evidence.
- External URL handling must not enter local RHCSA retrieval by default.
- Planner fallback must not expand authority.

## Provenance Invariants

- Every evidence artifact requires provenance.
- Unknown provider attribution remains `unknown`.
- Normalized artifacts must reference raw artifacts.
- Derived artifacts must reference their inputs.

## Forbidden Transitions

- reasoning trace -> immutable evidence
- operational log -> immutable evidence
- runtime state -> provenance
- provider response -> evidence without source
- archive review note -> runtime rule without migration phase
- LSC scientific artifact -> AOIA runtime validation

## Contradiction Constraints

- contradictions are first-class records
- contradiction records are not evidence by themselves
- contradictions are not auto-resolved
- review status must be explicit

## Session Isolation Principles

Sessions should remain isolated by:

- case study
- provider
- timestamp
- source system
- artifact class

AOIA sessions must not merge with LSC sessions by default.

## Replay Safety Assumptions

Replay reconstructs process, not truth.

Replay requires:

- immutable or append-only inputs
- stable provenance references
- explicit source paths
- no hidden runtime mutation

## Planner Fallback Restrictions

Planner fallback must not:

- bypass retrieval boundaries
- promote local knowledge to external review
- promote reasoning traces to evidence
- turn uncertainty into authority
- write canonical governance records

## Trust Boundary Definitions

Trusted only after validation:

- source artifacts
- provenance records
- operator-reviewed classifications

Untrusted by default:

- model output
- runtime state
- operational logs
- reasoning traces
- inferred provider attribution
