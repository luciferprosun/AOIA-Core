# Enforcement Layer Design

Phase: 3 - governance preparation
Status: target architecture only

## Purpose

Define the future enforcement layer required to make AOIA memory, provenance, and contradiction boundaries real.

## L0-L5 Write Boundaries

L0 Ephemeral runtime:

- may write temporary runtime state only
- must not write evidence or provenance

L1 Operational logs:

- may write execution and event logs
- must not promote logs into evidence

L2 Reasoning traces:

- may write non-authoritative reasoning context
- must remain quarantined from retrieval-as-evidence

L3 Provenance records:

- may write source, import, and derivation records
- must reference raw or normalized artifacts

L4 Immutable evidence:

- may receive externally grounded evidence only
- must require provenance validation before write

L5 Contradiction registry:

- may record contradiction events and review status
- must not auto-resolve contradictions

## Forbidden Cross-Layer Writes

Forbidden:

- L0 -> L3/L4/L5 direct authority writes
- L1 -> L4 evidence promotion
- L2 -> L4 evidence promotion
- planner output -> provenance without external source
- provider response -> evidence without provenance record
- runtime state -> canonical authority

## Evidence Promotion Restrictions

Evidence promotion should require:

- source artifact
- provenance record
- case-study assignment
- human or policy review status
- contradiction check

## Provenance Validation Concepts

Validation should confirm:

- source exists
- source class is allowed
- case study is explicit
- chain depth is bounded or reviewed
- provider attribution is known or marked unknown

## Append-Only Principles

Future enforcement should append new events instead of rewriting old records.

Corrections should be additional events, not mutation of prior evidence.

## Runtime Isolation Concepts

Runtime systems should not read archive material as live routing authority.

Archive review material can inform future design only through approved migration or policy phases.

## Contradiction Write Rules

Contradiction writes should record:

- source A
- source B
- contradiction type
- severity
- case-study scope
- review status

No contradiction should be auto-closed by model agreement.

## Planner Inheritance Restrictions

Planner outputs must not inherit authority from:

- prompt text
- reasoning trace
- model confidence
- prior operational log

Planner outputs may reference provenance records only when explicitly supplied by a validated retrieval path.
