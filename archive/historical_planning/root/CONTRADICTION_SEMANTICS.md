# Contradiction Semantics

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Principle

Contradictions are not execution errors.
They are epistemic signals that indicate competing claims, duplicate authorities, or unresolved source tension.

## Contradiction Object Model

Recommended conceptual fields:
- `contradiction_id`
- `type`
- `subject`
- `sources`
- `status`
- `detected_at`
- `lineage`
- `notes`
- `fingerprints`

## Current AOIA-Compatible Types

- duplicate command conflicts
- self references
- circular references
- future semantic claim conflicts
- future evidence disagreement records

## Status Model

Recommended statuses:
- `unresolved`
- `acknowledged`
- `superseded`
- `contextualized`

Do not use automatic deletion-oriented statuses.

## Unresolved Contradiction Handling

Rules:
1. unresolved contradictions remain visible
2. unresolved contradictions lower confidence or trigger manual review
3. unresolved contradictions do not block all retrieval by default
4. unresolved contradictions are preserved across sessions

## Contradiction Replay Semantics

Replay must preserve:
- when contradiction first appeared
- what sources triggered it
- what later status changes occurred
- whether later evidence contextualized but did not erase it

Replay must not:
- silently collapse historical contradiction into present resolution

## Contradiction Lineage

Each contradiction should preserve:
- origin sources
- derived status transitions
- linked provenance objects
- related evidence objects where applicable

This makes contradiction a lineage-bearing record, not a temporary warning.

## Persistence Rules

Rules:
- contradiction creation is append-only
- resolution is a new event, not mutation of history
- contradiction identifiers should remain stable across regenerations when source set is stable

## Runtime Role

Contradictions should influence:
- confidence labels
- manual review requirements
- output disclaimers

Contradictions should not:
- auto-delete evidence
- auto-select truth consensus
- trigger autonomous resolution loops

## Current AOIA Mapping

Current concrete form:
- `runtime/contradiction_registry.json`
- duplicate command conflicts already persisted as `unresolved`

Interpretation:
- AOIA already implements the seed of L5, but not yet a full evented contradiction ontology
