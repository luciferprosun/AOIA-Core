# AOIA Forensic Lineage Policy

Phase: 2 AOIA forensic migration

## Purpose

Prepare lineage rules for future AOIA forensic migration without synthesizing lineage yet.

## Append-Only Principle

Lineage records should be append-only.

Existing lineage records must not be rewritten to force consistency. Corrections should be added as later events.

## Replay Concept

A future lineage system should allow a reviewer to replay:

- source import
- normalization
- provider classification
- contradiction registration
- synthesis creation

Replay does not prove correctness. It documents process.

## Provenance Inheritance

Derived artifacts inherit provenance from the raw or normalized artifacts they reference.

Provider output does not become evidence without a provenance record.

## Non-Authoritative Reasoning Traces

Reasoning traces may support session reconstruction, but they are not evidence.

They must not be promoted into evidence stores without explicit source support.

## Session Isolation

Sessions should remain isolated by:

- source system
- timestamp
- provider
- case study

AOIA sessions must not be merged with LSC scientific sessions by default.

## Phase 2 Stop Rule

No lineage synthesis was performed in Phase 2.
